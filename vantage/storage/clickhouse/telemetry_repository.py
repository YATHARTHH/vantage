from datetime import datetime
from vantage.domain.events import TelemetryEnvelope
from vantage.storage.base import AbstractTelemetryRepository


class ClickHouseTelemetryRepository(AbstractTelemetryRepository):
    """
    Production ClickHouse storage implementation.
    STUB: Raises NotImplementedError.

    To migrate from local DuckDB → production ClickHouse:
      1. Install clickhouse-driver dependency (`pip install clickhouse-driver`)
      2. Implement insert() using clickhouse ReplacingMergeTree table
      3. Implement query methods using ClickHouse SQL dialect
      4. Set `OLAP_BACKEND=clickhouse` in .env
    """

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password

    async def insert(self, envelope: TelemetryEnvelope) -> bool:
        raise NotImplementedError("ClickHouse production backend is not implemented in POC.")

    async def insert_batch(self, envelopes: list[TelemetryEnvelope]) -> dict:
        raise NotImplementedError("ClickHouse production backend is not implemented in POC.")

    async def query_metrics(
        self,
        project_id: str | None,
        from_dt: datetime,
        to_dt: datetime,
        group_by: list[str] | None = None,
    ) -> list[dict]:
        raise NotImplementedError("ClickHouse production backend is not implemented in POC.")

    async def query_spans(
        self,
        project_id: str | None = None,
        trace_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        raise NotImplementedError("ClickHouse production backend is not implemented in POC.")

    async def get_rolling_stats(
        self,
        project_id: str,
        metric: str,
        window_days: int = 7,
    ) -> dict:
        raise NotImplementedError("ClickHouse production backend is not implemented in POC.")

    async def get_error_rate(
        self,
        project_id: str,
        window_hours: int = 1,
    ) -> dict:
        raise NotImplementedError("ClickHouse production backend is not implemented in POC.")

    async def get_volume_stats(
        self,
        project_id: str,
        window_days: int = 7,
    ) -> dict:
        raise NotImplementedError("ClickHouse production backend is not implemented in POC.")

    async def list_active_project_ids(self) -> list[str]:
        raise NotImplementedError("ClickHouse production backend is not implemented in POC.")

    async def close(self) -> None:
        pass
