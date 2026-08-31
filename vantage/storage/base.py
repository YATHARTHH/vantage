from abc import ABC, abstractmethod
from datetime import datetime
from vantage.domain.events import TelemetryEnvelope
from vantage.domain.projects import Project, SourceToolMapping
from vantage.domain.experiments import Experiment
from vantage.domain.alerts import AlertRecord, AlertRule


class AbstractTelemetryRepository(ABC):
    """All OLAP backends (DuckDB local, ClickHouse production) implement this interface."""

    @abstractmethod
    async def insert(self, envelope: TelemetryEnvelope) -> bool:
        """Insert a single envelope. Returns True if inserted, False if deduplicated."""
        ...

    @abstractmethod
    async def insert_batch(self, envelopes: list[TelemetryEnvelope]) -> dict:
        """Insert multiple envelopes. Returns {"stored": int, "deduplicated": int}."""
        ...

    @abstractmethod
    async def query_metrics(
        self,
        project_id: str | None,
        from_dt: datetime,
        to_dt: datetime,
        group_by: list[str] | None = None,
    ) -> list[dict]: ...

    @abstractmethod
    async def query_spans(
        self,
        project_id: str | None = None,
        trace_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]: ...

    @abstractmethod
    async def get_rolling_stats(
        self,
        project_id: str,
        metric: str,
        window_days: int = 7,
    ) -> dict: ...

    @abstractmethod
    async def get_error_rate(
        self,
        project_id: str,
        window_hours: int = 1,
    ) -> dict: ...

    @abstractmethod
    async def get_volume_stats(
        self,
        project_id: str,
        window_days: int = 7,
    ) -> dict: ...

    @abstractmethod
    async def list_active_project_ids(self) -> list[str]: ...

    @abstractmethod
    async def close(self) -> None: ...


class AbstractMetadataRepository(ABC):
    """All OLTP backends (SQLite local, PostgreSQL production) implement this interface."""

    # Projects & Mappings
    @abstractmethod
    async def get_project(self, project_id: str) -> Project | None: ...

    @abstractmethod
    async def save_project(self, project: Project) -> Project: ...

    @abstractmethod
    async def list_projects(self) -> list[Project]: ...

    @abstractmethod
    async def get_source_mapping(
        self, source_tool: str, source_identifier: str
    ) -> SourceToolMapping | None: ...

    @abstractmethod
    async def save_source_mapping(
        self, mapping: SourceToolMapping
    ) -> SourceToolMapping: ...

    # Experiments
    @abstractmethod
    async def get_experiment(self, experiment_id: str) -> Experiment | None: ...

    @abstractmethod
    async def save_experiment(self, experiment: Experiment) -> Experiment: ...

    @abstractmethod
    async def list_experiments(
        self,
        project_id: str | None = None,
        status: str | None = None,
    ) -> list[Experiment]: ...

    # Alerts & Rules
    @abstractmethod
    async def get_alert_rule(
        self, project_id: str, detector_type: str | None = None, metric_name: str | None = None
    ) -> AlertRule | None: ...

    @abstractmethod
    async def save_alert_rule(self, rule: AlertRule) -> AlertRule: ...

    @abstractmethod
    async def has_active_alert(self, incident_key: str) -> bool: ...

    @abstractmethod
    async def insert_alert(self, alert: AlertRecord) -> AlertRecord: ...

    @abstractmethod
    async def resolve_alert(self, alert_id: str) -> bool: ...

    @abstractmethod
    async def list_alerts(
        self, project_id: str | None = None, unresolved_only: bool = False
    ) -> list[AlertRecord]: ...
