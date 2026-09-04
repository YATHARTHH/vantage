import re
from typing import Dict, Any, Tuple, List, Optional
from pydantic import BaseModel


class DataClassification:
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"


class DestinationTrust:
    TRUSTED_INTERNAL = "TRUSTED_INTERNAL"
    APPROVED_EXTERNAL = "APPROVED_EXTERNAL"
    UNKNOWN_EXTERNAL = "UNKNOWN_EXTERNAL"
    BLOCKED = "BLOCKED"


class OutputInspectionResult(BaseModel):
    is_safe: bool = True
    data_sensitivity: str = DataClassification.PUBLIC
    destination_trust: str = DestinationTrust.TRUSTED_INTERNAL
    sanitized_arguments: Dict[str, Any] = {}
    violations: List[str] = []
    reason_code: str = "INSPECTION_PASSED"


class OutputInspector:
    """
    Defense-In-Depth Argument & Output Inspector.
    Provides formal data classification, destination trust validation,
    parameterization sanitization, and exfiltration prevention.
    """

    def __init__(self, project_allowlist: Optional[List[str]] = None):
        self.project_allowlist = set(project_allowlist or [
            "api.company.com",
            "analytics.company.com",
            "internal.services"
        ])

    def classify_destination(self, destination: str) -> str:
        if not destination or destination in ["internal", "localhost", "127.0.0.1"]:
            return DestinationTrust.TRUSTED_INTERNAL
        for allowed in self.project_allowlist:
            if destination == allowed or destination.endswith(f".{allowed}"):
                return DestinationTrust.APPROVED_EXTERNAL
        if "malicious" in destination or "blocked" in destination:
            return DestinationTrust.BLOCKED
        return DestinationTrust.UNKNOWN_EXTERNAL

    def inspect_and_sanitize(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        destination: Optional[str] = None,
        data_payload: Optional[str] = None
    ) -> OutputInspectionResult:
        violations: List[str] = []
        sanitized_args = dict(arguments)
        
        # 1. Data Classification
        sensitivity = DataClassification.PUBLIC
        payload_str = (data_payload or "") + " " + str(arguments)

        if re.search(r"\b(RESTRICTED|top_secret|private_key|ssn_full)\b", payload_str, re.IGNORECASE):
            sensitivity = DataClassification.RESTRICTED
        elif re.search(r"\b(SENSITIVE|credit_card|api_key|password|bearer)\b", payload_str, re.IGNORECASE):
            sensitivity = DataClassification.SENSITIVE
        elif re.search(r"\b(CONFIDENTIAL|internal_memo|financial_report)\b", payload_str, re.IGNORECASE):
            sensitivity = DataClassification.CONFIDENTIAL
        elif re.search(r"\b(INTERNAL|employee_id)\b", payload_str, re.IGNORECASE):
            sensitivity = DataClassification.INTERNAL

        # 2. Destination Trust
        dest_trust = self.classify_destination(destination or "")

        # 3. Exfiltration Protection Check
        if sensitivity in [DataClassification.RESTRICTED, DataClassification.SENSITIVE] and dest_trust in [DestinationTrust.UNKNOWN_EXTERNAL, DestinationTrust.BLOCKED]:
            violations.append(f"Exfiltration attempt: {sensitivity} data routed to {dest_trust} destination")
            return OutputInspectionResult(
                is_safe=False,
                data_sensitivity=sensitivity,
                destination_trust=dest_trust,
                sanitized_arguments=arguments,
                violations=violations,
                reason_code="DATA_EXFILTRATION_PREVENTED"
            )

        # 4. Dangerous Pattern Inspection & Parameterization (Defense-In-Depth)
        for key, val in arguments.items():
            if isinstance(val, str):
                # Path traversal check
                if "../" in val or "..\\" in val or val.startswith("/etc/") or val.startswith("C:\\Windows"):
                    violations.append(f"Path traversal detected in argument '{key}'")
                    sanitized_args[key] = re.sub(r"\.\.[/\\]", "", val)

                # SQL Injection pattern check
                if re.search(r"(\bUNION\b|\bSELECT\b.*\bFROM\b|--;|\bDROP\b\s+\bTABLE\b)", val, re.IGNORECASE):
                    violations.append(f"SQL injection syntax detected in argument '{key}'")

        if violations:
            return OutputInspectionResult(
                is_safe=False,
                data_sensitivity=sensitivity,
                destination_trust=dest_trust,
                sanitized_arguments=sanitized_args,
                violations=violations,
                reason_code="DANGEROUS_ARGUMENT_PATTERN_DETECTED"
            )

        return OutputInspectionResult(
            is_safe=True,
            data_sensitivity=sensitivity,
            destination_trust=dest_trust,
            sanitized_arguments=sanitized_args,
            violations=[],
            reason_code="INSPECTION_PASSED"
        )
