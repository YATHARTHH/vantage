from __future__ import annotations
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DetectorType(str, Enum):
    THRESHOLD = "threshold"
    Z_SCORE = "z_score"
    RATE_CHANGE = "rate_change"
    ERROR_RATE = "error_rate"
    VOLUME = "volume"


class DetectorResult(BaseModel):
    detector_type: DetectorType
    metric_name: str
    severity: AlertSeverity
    message: str
    current_value: float
    baseline_value: float | None = None
    threshold: float | None = None
    z_score: float | None = None


class AlertRecord(BaseModel):
    """
    Represents one active incident.
    Field(default_factory=uuid4) ensures a unique UUID per instantiation.
    """
    alert_id: UUID = Field(default_factory=uuid4)
    project_id: str
    detector_type: DetectorType
    metric_name: str
    severity: AlertSeverity
    message: str
    current_value: float
    baseline_value: float | None = None
    fired_at: datetime
    resolved_at: datetime | None = None
    notified: bool = False

    @property
    def incident_key(self) -> str:
        return f"{self.project_id}:{self.detector_type}:{self.metric_name}"


class AlertRule(BaseModel):
    id: int | None = None
    project_id: str
    detector_type: DetectorType
    metric_name: str
    warn_z: float = 2.0
    crit_z: float = 3.0
    absolute_threshold: float | None = None
    rate_change_factor: float = 1.5
    error_rate_pct: float = 5.0
    enabled: bool = True
