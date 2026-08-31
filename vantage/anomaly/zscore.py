from vantage.anomaly.base import AbstractDetector
from vantage.domain.alerts import AlertRule, AlertSeverity, DetectorResult, DetectorType
from vantage.storage.base import AbstractTelemetryRepository


class ZScoreDetector(AbstractDetector):
    """Z-score statistical anomaly detector."""

    detector_type = DetectorType.Z_SCORE

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
        std = stats.get("std")
        current = stats.get("current")

        if mean is None or std is None or current is None or std == 0:
            return None

        z = (current - mean) / std

        if z >= rule.crit_z:
            severity = AlertSeverity.CRITICAL
        elif z >= rule.warn_z:
            severity = AlertSeverity.WARNING
        else:
            return None

        return DetectorResult(
            detector_type=self.detector_type,
            metric_name=metric,
            severity=severity,
            message=f"{metric} z-score anomaly: z={z:.2f} (current={current:.4f}, mean={mean:.4f}, std={std:.4f})",
            current_value=current,
            baseline_value=mean,
            z_score=round(z, 2),
        )
