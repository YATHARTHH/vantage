import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from vantage.security.context import SecurityContext


class SecurityPolicyDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:12]}")
    decision: str  # ALLOW, WARN, REQUIRE_APPROVAL, BLOCK
    reason_code: str
    reason: str
    matched_rules: List[str] = Field(default_factory=list)
    policy_version: str = "v1.2.0"
    detector_version: str = "v1.0.0"
    request_id: str
    trace_id: str
    span_id: str
    tool_risk: str
    data_sensitivity: str
    destination_trust: str
    circuit_state: str = "CLOSED"


class MultiSignalPolicyGate:
    """
    Deterministic multi-signal security policy engine.
    Precedence order: BLOCK > REQUIRE_APPROVAL > WARN > ALLOW.
    Negative security signals always override positive signals.
    Fail-closed: returns BLOCK on scanner/engine internal error for tool enforcement.
    """

    def __init__(self, policy_version: str = "v1.2.0"):
        self.policy_version = policy_version

    def evaluate(
        self,
        ctx: SecurityContext,
        capability_granted: bool = True,
        circuit_open: bool = False,
        extra_rules: Optional[List[str]] = None
    ) -> SecurityPolicyDecision:
        matched_rules: List[str] = list(extra_rules or [])
        circuit_state = "OPEN" if circuit_open else "CLOSED"

        try:
            # 1. Circuit Breaker Check
            if circuit_open:
                matched_rules.append("CIRCUIT_BREAKER_OPEN")
                return SecurityPolicyDecision(
                    decision="BLOCK",
                    reason_code="CIRCUIT_BREAKER_EXCEEDED",
                    reason="Circuit breaker limit exceeded for agent trace",
                    matched_rules=matched_rules,
                    policy_version=self.policy_version,
                    detector_version=ctx.detector_version,
                    request_id=ctx.request_id,
                    trace_id=ctx.trace_id,
                    span_id=ctx.span_id,
                    tool_risk=ctx.tool_risk,
                    data_sensitivity=ctx.data_sensitivity,
                    destination_trust=ctx.destination_trust,
                    circuit_state=circuit_state,
                )

            # 2. Capability Authorization Check (Deny-by-Default)
            if not capability_granted:
                matched_rules.append("TOOL_CAPABILITY_DENIED")
                return SecurityPolicyDecision(
                    decision="BLOCK",
                    reason_code="TOOL_CAPABILITY_DENIED",
                    reason=f"Action '{ctx.action}' on resource '{ctx.resource}' denied for agent '{ctx.agent_id}' in '{ctx.environment}'",
                    matched_rules=matched_rules,
                    policy_version=self.policy_version,
                    detector_version=ctx.detector_version,
                    request_id=ctx.request_id,
                    trace_id=ctx.trace_id,
                    span_id=ctx.span_id,
                    tool_risk=ctx.tool_risk,
                    data_sensitivity=ctx.data_sensitivity,
                    destination_trust=ctx.destination_trust,
                    circuit_state=circuit_state,
                )

            # 3. Data Exfiltration Guard Check
            if ctx.destination_trust == "BLOCKED":
                matched_rules.append("DESTINATION_BLOCKED")
                return SecurityPolicyDecision(
                    decision="BLOCK",
                    reason_code="DATA_EXFILTRATION_PREVENTED",
                    reason=f"Destination trust state 'BLOCKED' for tool '{ctx.tool_name}'",
                    matched_rules=matched_rules,
                    policy_version=self.policy_version,
                    detector_version=ctx.detector_version,
                    request_id=ctx.request_id,
                    trace_id=ctx.trace_id,
                    span_id=ctx.span_id,
                    tool_risk=ctx.tool_risk,
                    data_sensitivity=ctx.data_sensitivity,
                    destination_trust=ctx.destination_trust,
                    circuit_state=circuit_state,
                )

            if ctx.data_sensitivity in ["RESTRICTED", "SENSITIVE"] and ctx.destination_trust == "UNKNOWN_EXTERNAL":
                matched_rules.append("DATA_EXFILTRATION_UNKNOWN_EXTERNAL")
                return SecurityPolicyDecision(
                    decision="BLOCK",
                    reason_code="DATA_EXFILTRATION_PREVENTED",
                    reason=f"Data sensitivity '{ctx.data_sensitivity}' cannot be routed to 'UNKNOWN_EXTERNAL' destination",
                    matched_rules=matched_rules,
                    policy_version=self.policy_version,
                    detector_version=ctx.detector_version,
                    request_id=ctx.request_id,
                    trace_id=ctx.trace_id,
                    span_id=ctx.span_id,
                    tool_risk=ctx.tool_risk,
                    data_sensitivity=ctx.data_sensitivity,
                    destination_trust=ctx.destination_trust,
                    circuit_state=circuit_state,
                )

            # 4. Critical Tool / Threat Score HARD DENY
            if ctx.threat_score >= 0.8:
                matched_rules.append("PROMPT_INJECTION_HIGH_CONFIDENCE")
                return SecurityPolicyDecision(
                    decision="BLOCK",
                    reason_code="HIGH_THREAT_DETECTED",
                    reason=f"Threat score {ctx.threat_score:.2f} exceeds high confidence block threshold 0.80",
                    matched_rules=matched_rules,
                    policy_version=self.policy_version,
                    detector_version=ctx.detector_version,
                    request_id=ctx.request_id,
                    trace_id=ctx.trace_id,
                    span_id=ctx.span_id,
                    tool_risk=ctx.tool_risk,
                    data_sensitivity=ctx.data_sensitivity,
                    destination_trust=ctx.destination_trust,
                    circuit_state=circuit_state,
                )

            if ctx.tool_risk == "CRITICAL" and ctx.environment == "production":
                matched_rules.append("CRITICAL_TOOL_PRODUCTION_ENV")
                return SecurityPolicyDecision(
                    decision="BLOCK",
                    reason_code="CRITICAL_TOOL_BLOCKED",
                    reason="Critical tool execution blocked in production environment by policy",
                    matched_rules=matched_rules,
                    policy_version=self.policy_version,
                    detector_version=ctx.detector_version,
                    request_id=ctx.request_id,
                    trace_id=ctx.trace_id,
                    span_id=ctx.span_id,
                    tool_risk=ctx.tool_risk,
                    data_sensitivity=ctx.data_sensitivity,
                    destination_trust=ctx.destination_trust,
                    circuit_state=circuit_state,
                )

            # 5. REQUIRE_APPROVAL Check
            if ctx.tool_risk in ["HIGH", "CRITICAL"] or ctx.threat_score >= 0.5:
                if ctx.tool_risk == "HIGH":
                    matched_rules.append("HIGH_RISK_TOOL_APPROVAL")
                if ctx.threat_score >= 0.5:
                    matched_rules.append("THREAT_MEDIUM_CONFIDENCE_APPROVAL")

                return SecurityPolicyDecision(
                    decision="REQUIRE_APPROVAL",
                    reason_code="HUMAN_APPROVAL_REQUIRED",
                    reason="Action requires explicit human approval before execution",
                    matched_rules=matched_rules,
                    policy_version=self.policy_version,
                    detector_version=ctx.detector_version,
                    request_id=ctx.request_id,
                    trace_id=ctx.trace_id,
                    span_id=ctx.span_id,
                    tool_risk=ctx.tool_risk,
                    data_sensitivity=ctx.data_sensitivity,
                    destination_trust=ctx.destination_trust,
                    circuit_state=circuit_state,
                )

            # 6. WARN Check
            if ctx.threat_score >= 0.2 or ctx.tool_risk == "MEDIUM":
                if ctx.threat_score >= 0.2:
                    matched_rules.append("LOW_CONFIDENCE_THREAT_WARN")
                if ctx.tool_risk == "MEDIUM":
                    matched_rules.append("MEDIUM_RISK_TOOL_WARN")

                return SecurityPolicyDecision(
                    decision="WARN",
                    reason_code="SECURITY_WARNING",
                    reason="Execution permitted with enhanced security event logging",
                    matched_rules=matched_rules,
                    policy_version=self.policy_version,
                    detector_version=ctx.detector_version,
                    request_id=ctx.request_id,
                    trace_id=ctx.trace_id,
                    span_id=ctx.span_id,
                    tool_risk=ctx.tool_risk,
                    data_sensitivity=ctx.data_sensitivity,
                    destination_trust=ctx.destination_trust,
                    circuit_state=circuit_state,
                )

            # 7. ALLOW Default
            matched_rules.append("DEFAULT_ALLOW_POLICY")
            return SecurityPolicyDecision(
                decision="ALLOW",
                reason_code="POLICY_EVALUATION_SUCCESS",
                reason="Operation evaluated and authorized by policy engine",
                matched_rules=matched_rules,
                policy_version=self.policy_version,
                detector_version=ctx.detector_version,
                request_id=ctx.request_id,
                trace_id=ctx.trace_id,
                span_id=ctx.span_id,
                tool_risk=ctx.tool_risk,
                data_sensitivity=ctx.data_sensitivity,
                destination_trust=ctx.destination_trust,
                circuit_state=circuit_state,
            )

        except Exception as exc:
            # Fail-closed for tool enforcement path
            matched_rules.append("POLICY_ENGINE_INTERNAL_ERROR")
            return SecurityPolicyDecision(
                decision="BLOCK",
                reason_code="SECURITY_ENGINE_FAILURE",
                reason=f"Security policy engine internal failure: {str(exc)}",
                matched_rules=matched_rules,
                policy_version=self.policy_version,
                detector_version=ctx.detector_version,
                request_id=ctx.request_id,
                trace_id=ctx.trace_id,
                span_id=ctx.span_id,
                tool_risk=ctx.tool_risk,
                data_sensitivity=ctx.data_sensitivity,
                destination_trust=ctx.destination_trust,
                circuit_state="ERROR",
            )
