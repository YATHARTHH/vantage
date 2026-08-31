from abc import ABC, abstractmethod
from typing import Any
from vantage.domain.events import TelemetryEnvelope


class AbstractConnector(ABC):
    """Abstract connector for incoming webhooks and telemetry payloads."""

    @abstractmethod
    def parse(self, raw_payload: Any) -> list[TelemetryEnvelope]:
        """Parses a raw payload into a list of TelemetryEnvelopes."""
        ...
