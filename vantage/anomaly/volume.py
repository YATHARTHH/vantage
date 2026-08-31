from vantage.anomaly.base import AbstractDetector
from vantage.domain.alerts import AlertRule, AlertSeverity, DetectorResult, DetectorType
from vantage.storage.base import AbstractTelemetryRepository


class VolumeDetector(AbstractDetector):
    """Detects unusual drops or spikes in hourly event volume."""

    detector_type = DetectorType.VOLUME

    def __init__(self):
        super().__init__(metric_name="event_volume")

    async def detect(
        self,
        project_id: str,
        telemetry_repo: AbstractTelemetryRepository,
        rule: AlertRule,
    ) -> DetectorResult | None:
        stats = await telemetry_repo.get_volume_stats(project_id, window_days=7)

        mean = stats.get("hourly_mean", 0.0)
        current = stats.get("current_hour_count", 0)

        if mean == 0:
            return None

        ratio = current / mean

        # Volume Spike (runaway loop / flood)
        if ratio >= rule.rate_change_factor * 2.0:
            return DetectorResult(
                detector_type=self.detector_type,
                metric_name="event_volume",
                severity=AlertSeverity.CRITICAL,
                message=f"Event volume spike: {current} events/hr vs baseline {mean:.1f}/hr ({ratio:.1f}x)",
                current_value=float(current),
                baseline_value=mean,
            )
        if ratio >= rule.rate_change_factor:
            return DetectorResult(
                detector_type=self.detector_type,
                metric_name="event_volume",
                severity=AlertSeverity.WARNING,
                message=f"Event volume elevated: {current} events/hr vs baseline {mean:.1f}/hr ({ratio:.1f}x)",
                current_value=float(current),
                baseline_value=mean,
            )

        # Volume Drop (service died silently / network partition)
        if mean >= 10.0 and current < mean * 0.2:
            return DetectorResult(
                detector_type=self.detector_type,
                metric_name="event_volume",
                severity=AlertSeverity.WARNING,
                message=f"Event volume drop: {current} events/hr vs baseline {mean:.1f}/hr (possible outage)",
                current_value=float(current),
                baseline_value=mean,
            )

        return None
