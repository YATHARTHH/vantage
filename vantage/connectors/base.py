from abc import ABC, abstractmethod
from typing import Any
from vantage.domain.events import TelemetryEnvelope


class AbstractConnector(ABC):
    """Abstract interface for ingestion connectors converting raw payloads to TelemetryEnvelopes."""

    @abstractmethod
    def parse(self, raw_payload: dict[str, Any] | list[dict[str, Any]]) -> list[TelemetryEnvelope]:
        """Parses incoming raw JSON payload into normalized TelemetryEnvelope domain models."""
        pass
