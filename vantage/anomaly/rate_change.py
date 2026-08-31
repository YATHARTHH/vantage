from vantage.anomaly.base import AbstractDetector
from vantage.domain.alerts import AlertRule, AlertSeverity, DetectorResult, DetectorType
from vantage.storage.base import AbstractTelemetryRepository


class RateChangeDetector(AbstractDetector):
    """Detects rapid relative multiplier spikes compared to baseline average."""

    detector_type = DetectorType.RATE_CHANGE

    def __init__(self, metric_name: str = "cost_usd"):
        super().__init__(metric_name=metric_name)

    async def detect(
        self,
        project_id: str,
        telemetry_repo: AbstractTelemetryRepository,
        rule: AlertRule,
    ) -> DetectorResult | None:
        metric = self.metric_name or rule.metric_name
        stats = await telemetry_repo.get_rolling_stats(project_id, metric, window_days=7)

        mean = stats.get("mean")
        current = stats.get("current")

        if mean is None or current is None or mean == 0:
            return None

        ratio = current / mean
        factor = rule.rate_change_factor

        if ratio < factor:
            return None

        severity = AlertSeverity.CRITICAL if ratio >= factor * 2.0 else AlertSeverity.WARNING

        return DetectorResult(
            detector_type=self.detector_type,
            metric_name=metric,
            severity=severity,
            message=f"{metric} rate-change spike: current={current:.4f} is {ratio:.1f}x higher than baseline {mean:.4f}",
            current_value=current,
            baseline_value=mean,
        )
