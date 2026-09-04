from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class SecurityContext:
    """
    Immutable security context passed across the entire Vantage security pipeline.
    Frozen dataclass ensures context identity cannot be mutated between components.
    Any modified field requires a new security authorization decision.
    """
    request_id: str
    trace_id: str
    span_id: str
    principal_id: str
    agent_id: str
    project_id: str
    environment: str
    tool_name: str
    action: str
    resource: str
    threat_score: float = 0.0
    confidence: float = 1.0
    tool_risk: str = "LOW"            # LOW, MEDIUM, HIGH, CRITICAL
    data_sensitivity: str = "PUBLIC"  # PUBLIC, INTERNAL, CONFIDENTIAL, SENSITIVE, RESTRICTED
    destination_trust: str = "TRUSTED_INTERNAL" # TRUSTED_INTERNAL, APPROVED_EXTERNAL, UNKNOWN_EXTERNAL, BLOCKED
    policy_version: str = "v1.2.0"
    detector_version: str = "v1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "principal_id": self.principal_id,
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "environment": self.environment,
            "tool_name": self.tool_name,
            "action": self.action,
            "resource": self.resource,
            "threat_score": self.threat_score,
            "confidence": self.confidence,
            "tool_risk": self.tool_risk,
            "data_sensitivity": self.data_sensitivity,
            "destination_trust": self.destination_trust,
            "policy_version": self.policy_version,
            "detector_version": self.detector_version,
        }
