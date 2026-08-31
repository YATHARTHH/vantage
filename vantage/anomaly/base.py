from abc import ABC, abstractmethod
from vantage.domain.alerts import AlertRule, DetectorResult, DetectorType
from vantage.storage.base import AbstractTelemetryRepository


class AbstractDetector(ABC):
    """Abstract strategy interface for all anomaly detectors."""

    detector_type: DetectorType

    def __init__(self, metric_name: str | None = None):
        self.metric_name = metric_name

    @abstractmethod
    async def detect(
        self,
        project_id: str,
        telemetry_repo: AbstractTelemetryRepository,
        rule: AlertRule,
    ) -> DetectorResult | None:
        ...
