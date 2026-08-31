from vantage.anomaly.base import AbstractDetector
from vantage.domain.alerts import AlertRule, AlertSeverity, DetectorResult, DetectorType
from vantage.storage.base import AbstractTelemetryRepository


class ThresholdDetector(AbstractDetector):
    """Absolute upper-bound threshold detector."""

    detector_type = DetectorType.THRESHOLD

    def __init__(self, metric_name: str = "cost_usd"):
        super().__init__(metric_name=metric_name)

    async def detect(
        self,
        project_id: str,
        telemetry_repo: AbstractTelemetryRepository,
        rule: AlertRule,
    ) -> DetectorResult | None:
        metric = self.metric_name or rule.metric_name
        threshold = rule.absolute_threshold
        if threshold is None:
            return None

        stats = await telemetry_repo.get_rolling_stats(project_id, metric, window_days=1)
        current = stats.get("current")

        if current is None or current <= threshold:
            return None

        return DetectorResult(
            detector_type=self.detector_type,
            metric_name=metric,
            severity=AlertSeverity.CRITICAL if current >= threshold * 1.5 else AlertSeverity.WARNING,
            message=f"{metric} absolute threshold exceeded: {current:.4f} > limit {threshold:.4f}",
            current_value=current,
            threshold=threshold,
        )
