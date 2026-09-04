import json
import hashlib
import time
import uuid
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from vantage.security.context import SecurityContext


def compute_action_fingerprint(
    tool: str, action: str, resource: str, environment: str, arguments: Dict[str, Any]
) -> str:
    """
    Computes SHA-256 fingerprint over complete action context using canonical JSON formatting (sorted keys).
    Binds approval to exact tool, action, resource, environment, and arguments.
    """
    canonical_payload = {
        "action": action,
        "arguments": arguments,
        "environment": environment,
        "resource": resource,
        "tool": tool,
    }
    canonical_str = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


class ApprovalRecord(BaseModel):
    approval_id: str = Field(default_factory=lambda: f"appr_{uuid.uuid4().hex[:12]}")
    request_id: str
    trace_id: str
    span_id: str
    project_id: str
    agent_id: str
    tool_name: str
    action: str
    resource: str
    environment: str
    arguments_hash: str
    approval_fingerprint: str
    approved_policy_version: str
    status: str = "PENDING_APPROVAL"  # PENDING_APPROVAL, APPROVED, DENIED, EXPIRED
    requested_at: float = Field(default_factory=time.time)
    expires_at: float
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None
    consumed_at: Optional[float] = None


class HumanApprovalWorkflow:
    """
    Manages human approval requests with TOCTOU protection, action fingerprinting,
    single-use consumption semantics, and stale-policy invalidation.
    """

    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl_seconds = ttl_seconds
        self._approvals: Dict[str, ApprovalRecord] = {}

    def create_approval_request(
        self, ctx: SecurityContext, arguments: Dict[str, Any]
    ) -> ApprovalRecord:
        now = time.time()
        fingerprint = compute_action_fingerprint(
            tool=ctx.tool_name,
            action=ctx.action,
            resource=ctx.resource,
            environment=ctx.environment,
            arguments=arguments,
        )
        arg_str = json.dumps(arguments, sort_keys=True)
        arg_hash = hashlib.sha256(arg_str.encode("utf-8")).hexdigest()

        record = ApprovalRecord(
            request_id=ctx.request_id,
            trace_id=ctx.trace_id,
            span_id=ctx.span_id,
            project_id=ctx.project_id,
            agent_id=ctx.agent_id,
            tool_name=ctx.tool_name,
            action=ctx.action,
            resource=ctx.resource,
            environment=ctx.environment,
            arguments_hash=arg_hash,
            approval_fingerprint=fingerprint,
            approved_policy_version=ctx.policy_version,
            status="PENDING_APPROVAL",
            requested_at=now,
            expires_at=now + self.ttl_seconds,
        )
        self._approvals[record.approval_id] = record
        return record

    def approve(self, approval_id: str, approved_by: str) -> Optional[ApprovalRecord]:
        record = self._approvals.get(approval_id)
        if not record:
            return None
        if time.time() > record.expires_at:
            record.status = "EXPIRED"
            return record

        if record.status == "PENDING_APPROVAL":
            record.status = "APPROVED"
            record.approved_by = approved_by
            record.approved_at = time.time()
        return record

    def deny(self, approval_id: str, denied_by: str) -> Optional[ApprovalRecord]:
        record = self._approvals.get(approval_id)
        if not record:
            return None
        record.status = "DENIED"
        record.approved_by = denied_by
        record.approved_at = time.time()
        return record

    def consume_approval(
        self,
        approval_id: str,
        ctx: SecurityContext,
        arguments: Dict[str, Any],
        current_policy_version: str,
    ) -> Tuple[bool, str]:
        """
        Atomically verifies and consumes a single-use human approval.
        Returns (success: bool, error_reason_code: str).
        """
        record = self._approvals.get(approval_id)
        if not record:
            return False, "APPROVAL_NOT_FOUND"

        now = time.time()
        if now > record.expires_at:
            record.status = "EXPIRED"
            return False, "APPROVAL_EXPIRED"

        if record.status != "APPROVED":
            return False, f"APPROVAL_STATUS_{record.status}"

        # Single-use check: must not have been consumed previously
        if record.consumed_at is not None:
            return False, "APPROVAL_ALREADY_CONSUMED"

        # Stale policy version check
        if record.approved_policy_version != current_policy_version:
            return False, "APPROVAL_POLICY_STALE"

        # TOCTOU Fingerprint verification
        current_fingerprint = compute_action_fingerprint(
            tool=ctx.tool_name,
            action=ctx.action,
            resource=ctx.resource,
            environment=ctx.environment,
            arguments=arguments,
        )
        if current_fingerprint != record.approval_fingerprint:
            return False, "APPROVAL_FINGERPRINT_MISMATCH"

        # Atomic consume
        record.consumed_at = now
        return True, "SUCCESS"

    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        return self._approvals.get(approval_id)
