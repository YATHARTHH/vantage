from abc import ABC, abstractmethod
from vantage.domain.events import TelemetryEnvelope
from vantage.security.models import SecurityScanResult


class AbstractSecurityScanner(ABC):
    """
    Abstract Strategy interface for all security scanners in Vantage.
    """
    @abstractmethod
    def scan_text(self, text: str) -> SecurityScanResult:
        """Scan raw prompt text and return SecurityScanResult."""
        ...

    @abstractmethod
    def scan_envelope(self, envelope: TelemetryEnvelope) -> SecurityScanResult:
        """Extract target prompt fields from TelemetryEnvelope and perform security scan."""
        ...
