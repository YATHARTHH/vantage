from vantage.anomaly.base import AbstractDetector
from vantage.domain.alerts import AlertRule, AlertSeverity, DetectorResult, DetectorType
from vantage.storage.base import AbstractTelemetryRepository


class ErrorRateDetector(AbstractDetector):
    """Detects elevated error rate percentage over rolling 1-hour window."""

    detector_type = DetectorType.ERROR_RATE

    def __init__(self):
        super().__init__(metric_name="error_rate_pct")

    async def detect(
        self,
        project_id: str,
        telemetry_repo: AbstractTelemetryRepository,
        rule: AlertRule,
    ) -> DetectorResult | None:
        stats = await telemetry_repo.get_error_rate(project_id, window_hours=1)

        total = stats.get("total_count", 0)
        error_rate = stats.get("error_rate_pct", 0.0)

        if total < 5:  # Require minimum 5 events for statistical relevance
            return None

        if error_rate < rule.error_rate_pct:
            return None

        severity = AlertSeverity.CRITICAL if error_rate >= rule.error_rate_pct * 2.0 else AlertSeverity.WARNING

        return DetectorResult(
            detector_type=self.detector_type,
            metric_name="error_rate_pct",
            severity=severity,
            message=f"Elevated error rate: {error_rate:.1f}% ({stats.get('error_count')} errors in {total} events, limit: {rule.error_rate_pct}%)",
            current_value=error_rate,
            threshold=rule.error_rate_pct,
        )
