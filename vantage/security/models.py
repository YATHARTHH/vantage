from enum import Enum
from pydantic import BaseModel, Field


class SecurityThreatType(str, Enum):
    INSTRUCTION_OVERRIDE = "instruction_override"
    PROMPT_LEAK = "prompt_leak"
    ROLEPLAY_BYPASS = "roleplay_bypass"
    INDIRECT_INJECTION = "indirect_injection"
    ENCODED_PAYLOAD = "encoded_payload"
    TOOL_MANIPULATION = "tool_manipulation"
    UNKNOWN = "unknown"


class SecurityRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityScanResult(BaseModel):
    is_threat: bool = False
    threat_types: list[SecurityThreatType] = Field(default_factory=list)
    threat_score: float = 0.0
    risk_level: SecurityRiskLevel = SecurityRiskLevel.LOW
    matched_rules: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    scanner_version: str = "v1.0.0"
