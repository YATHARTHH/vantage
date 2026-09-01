from datetime import datetime, timezone
from vantage.core.logging import get_logger
from vantage.domain.events import TelemetryEnvelope
from vantage.domain.alerts import AlertRecord, AlertCategory, AlertSeverity, DetectorType
from vantage.storage.base import AbstractMetadataRepository
from vantage.security.models import SecurityRiskLevel

logger = get_logger(__name__)


class SecurityAlertService:
    """
    Orchestrates creation and persistence of security alerts for flagged prompt threats.
    
    Alert Policy:
    - LOW / MEDIUM risk levels: Telemetry flag only (no alert).
    - HIGH / CRITICAL risk levels: Triggers security alert titled 'Potential Prompt Injection Detected'.
    
    Deduplication:
    - Derived security_incident_key: security:{project_id}:{trace_id}:{span_id}:{first_threat_type}
    - Prevents duplicate alerts from concurrent workers or retries.
    """
    def __init__(self, metadata_repo: AbstractMetadataRepository):
        self._metadata_repo = metadata_repo

    async def process_security_envelope(self, envelope: TelemetryEnvelope) -> AlertRecord | None:
        sec = envelope.security
        if not sec or not sec.is_threat or not sec.risk_level:
            return None

        # Alert trigger policy check: Only HIGH or CRITICAL risk levels fire alerts
        if sec.risk_level not in (SecurityRiskLevel.HIGH.value, SecurityRiskLevel.CRITICAL.value, SecurityRiskLevel.HIGH, SecurityRiskLevel.CRITICAL):
            return None

        primary_threat = sec.threat_types[0] if sec.threat_types else "unknown"
        incident_key = f"security:{envelope.project_id}:{envelope.span.trace_id}:{envelope.span.span_id}:{primary_threat}"

        # Deduplication check
        has_active = await self._metadata_repo.has_active_alert(incident_key)
        if has_active:
            logger.info(f"Suppressed duplicate security alert for incident key: {incident_key}")
            return None

        # Operator false-positive suppression check
        if hasattr(self._metadata_repo, "is_suppressed"):
            suppressed = await self._metadata_repo.is_suppressed(envelope.project_id, incident_key, threat_type=primary_threat)
            if suppressed:
                logger.info(f"Suppressed security alert per operator rule: {incident_key}")
                return None

        severity = (
            AlertSeverity.CRITICAL
            if sec.risk_level in (SecurityRiskLevel.CRITICAL.value, SecurityRiskLevel.CRITICAL)
            else AlertSeverity.WARNING
        )

        threat_summary = ", ".join(sec.threat_types) if sec.threat_types else primary_threat
        message = (
            f"Potential Prompt Injection Detected in project '{envelope.project_id}' "
            f"(Trace ID: {envelope.span.trace_id}). Threat categories: [{threat_summary}]. "
            f"Score: {sec.threat_score:.2f}."
        )

        alert_record = AlertRecord(
            project_id=envelope.project_id,
            detector_type=DetectorType.JAILBREAK_SECURITY,
            metric_name="jailbreak_threat_score",
            severity=severity,
            message=message,
            current_value=sec.threat_score or 1.0,
            baseline_value=0.0,
            fired_at=datetime.now(timezone.utc),
            category=AlertCategory.SECURITY,
            security_incident_key=incident_key,
            trace_id=envelope.span.trace_id,
            span_id=envelope.span.span_id,
            threat_types=[str(t) for t in sec.threat_types],
        )

        try:
            saved_alert = await self._metadata_repo.insert_alert(alert_record)
            logger.warn(f"SECURITY ALERT CREATED: [{incident_key}] - {message}")
            return saved_alert
        except Exception as e:
            logger.error(f"Failed to persist security alert [{incident_key}]: {e}")
            return None
