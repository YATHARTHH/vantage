class VantageException(Exception):
    """Base exception for all Vantage application errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class StorageError(VantageException):
    """Raised when DuckDB or SQLite storage operations fail."""
    pass


class ProjectNotFoundError(VantageException):
    """Raised when a project slug cannot be resolved."""
    pass


class InvalidEventPayloadError(VantageException):
    """Raised when raw telemetry or webhook fails normalization."""
    pass


class AnomalyEngineError(VantageException):
    """Raised when detection cycles fail."""
    pass
