import time
import uuid
import logging
from typing import Dict, Any, Callable, Optional, Tuple
from pydantic import BaseModel, Field

from vantage.security.context import SecurityContext
from vantage.security.policy_gate import MultiSignalPolicyGate, SecurityPolicyDecision
from vantage.security.tool_authorizer import ToolAuthorizer
from vantage.security.approval_workflow import HumanApprovalWorkflow
from vantage.security.output_inspector import OutputInspector, DataClassification, DestinationTrust

logger = logging.getLogger("vantage.security.execution_controller")


class ExecutionResult(BaseModel):
    status: str  # EXECUTED, BLOCKED, PENDING_APPROVAL, ERROR
    decision_id: str
    request_id: str
    trace_id: str
    span_id: str
    approval_id: Optional[str] = None
    audit_event_id: str = Field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:12]}")
    reason_code: str
    reason: str
    tool_output: Optional[Any] = None
    policy_decision: Optional[Dict[str, Any]] = None


class ExecutionController:
    """
    Mandatory Execution Controller Choke Point.
    ALL tool invocations in Vantage MUST pass strictly through ExecutionController.execute().
    Guarantees untrusted LLM/agent code cannot bypass authorization, policy evaluation,
    TOCTOU fingerprint checks, or human approval verification.
    """

    def __init__(
        self,
        policy_gate: Optional[MultiSignalPolicyGate] = None,
        authorizer: Optional[ToolAuthorizer] = None,
        approval_workflow: Optional[HumanApprovalWorkflow] = None,
        output_inspector: Optional[OutputInspector] = None,
    ):
        self.policy_gate = policy_gate or MultiSignalPolicyGate()
        self.authorizer = authorizer or ToolAuthorizer()
        self.approval_workflow = approval_workflow or HumanApprovalWorkflow()
        self.output_inspector = output_inspector or OutputInspector()

    def execute(
        self,
        ctx: SecurityContext,
        tool_func: Callable[[Dict[str, Any]], Any],
        arguments: Dict[str, Any],
        approval_id: Optional[str] = None,
        authenticated_principal_id: Optional[str] = None,
        authenticated_agent_id: Optional[str] = None,
        circuit_open: bool = False,
        destination: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Sole choke point executing tools after complete context, capability, policy,
        exfiltration, and human approval verification.
        """
        # 1. Identity & Capability Scoping Check
        capability_granted = self.authorizer.is_authorized(
            ctx,
            authenticated_principal_id=authenticated_principal_id,
            authenticated_agent_id=authenticated_agent_id,
        )

        # 2. Argument & Exfiltration Inspection
        inspection = self.output_inspector.inspect_and_sanitize(
            tool_name=ctx.tool_name,
            arguments=arguments,
            destination=destination,
        )

        # Re-verify context data sensitivity & destination trust from inspection
        ctx_data_sens = inspection.data_sensitivity if inspection.data_sensitivity != DataClassification.PUBLIC else ctx.data_sensitivity
        ctx_dest_trust = inspection.destination_trust if inspection.destination_trust != DestinationTrust.TRUSTED_INTERNAL else ctx.destination_trust

        updated_ctx = SecurityContext(
            request_id=ctx.request_id,
            trace_id=ctx.trace_id,
            span_id=ctx.span_id,
            principal_id=ctx.principal_id,
            agent_id=ctx.agent_id,
            project_id=ctx.project_id,
            environment=ctx.environment,
            tool_name=ctx.tool_name,
            action=ctx.action,
            resource=ctx.resource,
            threat_score=ctx.threat_score,
            confidence=ctx.confidence,
            tool_risk=ctx.tool_risk,
            data_sensitivity=ctx_data_sens,
            destination_trust=ctx_dest_trust,
            policy_version=ctx.policy_version,
            detector_version=ctx.detector_version,
        )

        # 3. Policy Gate Precedence Evaluation
        extra_rules = inspection.violations
        try:
            policy_decision = self.policy_gate.evaluate(
                ctx=updated_ctx,
                capability_granted=capability_granted,
                circuit_open=circuit_open,
                extra_rules=extra_rules,
            )
        except Exception as exc:
            logger.error(f"[SECURITY_ENGINE_FAILURE] Policy evaluation exception: {exc}")
            return ExecutionResult(
                status="BLOCKED",
                decision_id=f"dec_fail_{uuid.uuid4().hex[:8]}",
                request_id=updated_ctx.request_id,
                trace_id=updated_ctx.trace_id,
                span_id=updated_ctx.span_id,
                approval_id=approval_id,
                reason_code="SECURITY_ENGINE_FAILURE",
                reason=f"Security policy evaluation failed: {str(exc)}",
                policy_decision=None,
            )

        # 4. Handle Decision: BLOCK
        if policy_decision.decision == "BLOCK":
            logger.warning(
                f"[SECURITY_BLOCK] Tool '{updated_ctx.tool_name}' blocked. Reason: {policy_decision.reason_code}"
            )
            return ExecutionResult(
                status="BLOCKED",
                decision_id=policy_decision.decision_id,
                request_id=updated_ctx.request_id,
                trace_id=updated_ctx.trace_id,
                span_id=updated_ctx.span_id,
                approval_id=approval_id,
                reason_code=policy_decision.reason_code,
                reason=policy_decision.reason,
                policy_decision=policy_decision.model_dump(),
            )

        # 5. Handle Decision: REQUIRE_APPROVAL
        if policy_decision.decision == "REQUIRE_APPROVAL":
            if not approval_id:
                # Create pending approval request record
                record = self.approval_workflow.create_approval_request(updated_ctx, arguments)
                logger.info(f"[APPROVAL_PENDING] Action requires human approval. Created approval_id: {record.approval_id}")
                return ExecutionResult(
                    status="PENDING_APPROVAL",
                    decision_id=policy_decision.decision_id,
                    request_id=updated_ctx.request_id,
                    trace_id=updated_ctx.trace_id,
                    span_id=updated_ctx.span_id,
                    approval_id=record.approval_id,
                    reason_code=policy_decision.reason_code,
                    reason="Execution paused pending human approval",
                    policy_decision=policy_decision.model_dump(),
                )
            else:
                # Verify and atomically consume single-use approval
                consumed, err_reason = self.approval_workflow.consume_approval(
                    approval_id=approval_id,
                    ctx=updated_ctx,
                    arguments=arguments,
                    current_policy_version=self.policy_gate.policy_version,
                )
                if not consumed:
                    logger.error(f"[APPROVAL_FAILED] Failed approval consumption for ID {approval_id}. Code: {err_reason}")
                    return ExecutionResult(
                        status="BLOCKED",
                        decision_id=policy_decision.decision_id,
                        request_id=updated_ctx.request_id,
                        trace_id=updated_ctx.trace_id,
                        span_id=updated_ctx.span_id,
                        approval_id=approval_id,
                        reason_code=err_reason,
                        reason=f"Human approval verification failed: {err_reason}",
                        policy_decision=policy_decision.model_dump(),
                    )

        # 6. Execute Tool (ALLOW or WARN or Verified Approval)
        try:
            if policy_decision.decision == "WARN":
                logger.warning(f"[SECURITY_WARN] Executing tool '{updated_ctx.tool_name}' under WARN decision. Matched rules: {policy_decision.matched_rules}")

            tool_output = tool_func(inspection.sanitized_arguments)
            return ExecutionResult(
                status="EXECUTED",
                decision_id=policy_decision.decision_id,
                request_id=updated_ctx.request_id,
                trace_id=updated_ctx.trace_id,
                span_id=updated_ctx.span_id,
                approval_id=approval_id,
                reason_code=policy_decision.reason_code,
                reason="Tool executed successfully through ExecutionController",
                tool_output=tool_output,
                policy_decision=policy_decision.model_dump(),
            )
        except Exception as exc:
            logger.error(f"[TOOL_EXECUTION_ERROR] Error executing tool '{updated_ctx.tool_name}': {exc}")
            return ExecutionResult(
                status="ERROR",
                decision_id=policy_decision.decision_id,
                request_id=updated_ctx.request_id,
                trace_id=updated_ctx.trace_id,
                span_id=updated_ctx.span_id,
                approval_id=approval_id,
                reason_code="TOOL_EXECUTION_EXCEPTION",
                reason=f"Runtime error executing tool: {str(exc)}",
                policy_decision=policy_decision.model_dump(),
            )
