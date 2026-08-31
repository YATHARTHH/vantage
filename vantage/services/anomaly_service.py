from datetime import datetime, timezone
from vantage.anomaly.error_rate import ErrorRateDetector
from vantage.anomaly.rate_change import RateChangeDetector
from vantage.anomaly.threshold import ThresholdDetector
from vantage.anomaly.volume import VolumeDetector
from vantage.anomaly.zscore import ZScoreDetector
from vantage.core.logging import get_logger
from vantage.domain.alerts import AlertRecord, AlertRule, DetectorType
from vantage.services.notification_service import NotificationService
from vantage.storage.base import AbstractMetadataRepository, AbstractTelemetryRepository

logger = get_logger(__name__)

DETECTORS = [
    ZScoreDetector("cost_usd"),
    ZScoreDetector("duration_ms"),
    ThresholdDetector("cost_usd"),
    RateChangeDetector("cost_usd"),
    RateChangeDetector("duration_ms"),
    ErrorRateDetector(),
    VolumeDetector(),
]


class AnomalyService:
    """
    Orchestrates anomaly detection across 5 detector strategies covering 4 signals
    (cost, latency, error rate, volume) instantiated as 7 detector configurations.

    Incident suppression:
    Checks has_active_alert(incident_key) before creating a new alert record.
    Suppresses new alerts until the open incident is explicitly resolved.
    """

    def __init__(
        self,
        telemetry_repo: AbstractTelemetryRepository,
        metadata_repo: AbstractMetadataRepository,
        notifier: NotificationService,
    ):
        self._telemetry = telemetry_repo
        self._metadata = metadata_repo
        self._notifier = notifier

    async def run_detection_cycle(self) -> int:
        projects = await self._telemetry.list_active_project_ids()
        alerts_fired = 0

        for project_id in projects:
            for detector in DETECTORS:
                d_type_val = (
                    detector.detector_type.value
                    if isinstance(detector.detector_type, DetectorType)
                    else str(detector.detector_type)
                )
                rule = await self._metadata.get_alert_rule(
                    project_id, d_type_val, detector.metric_name
                )
                if rule and not rule.enabled:
                    continue

                if not rule:
                    rule = AlertRule(
                        project_id=project_id,
                        detector_type=detector.detector_type,
                        metric_name=detector.metric_name or "cost_usd",
                    )

                try:
                    result = await detector.detect(project_id, self._telemetry, rule)
                    if result is None:
                        continue

                    # Active incident suppression check
                    incident_key = f"{project_id}:{d_type_val}:{result.metric_name}"
                    if await self._metadata.has_active_alert(incident_key):
                        logger.debug("alert_suppressed_open_incident", incident_key=incident_key)
                        continue

                    alert = AlertRecord(
                        project_id=project_id,
                        detector_type=result.detector_type,
                        metric_name=result.metric_name,
                        severity=result.severity,
                        message=result.message,
                        current_value=result.current_value,
                        baseline_value=result.baseline_value,
                        fired_at=datetime.now(timezone.utc),
                    )
                    saved = await self._metadata.insert_alert(alert)
                    sent = await self._notifier.send(saved)
                    if sent:
                        saved.notified = True
                    alerts_fired += 1

                    logger.warning(
                        "anomaly_fired",
                        project_id=project_id,
                        detector=d_type_val,
                        severity=result.severity.value,
                    )

                except Exception as exc:
                    logger.error("detector_error", detector=d_type_val, project_id=project_id, error=str(exc))

        logger.info("detection_cycle_completed", alerts_fired=alerts_fired, projects_evaluated=len(projects))
        return alerts_fired
