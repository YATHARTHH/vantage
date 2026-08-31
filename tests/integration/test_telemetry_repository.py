from datetime import datetime, timezone
from pathlib import Path
import pytest

from vantage.domain.events import (
    EventStatus,
    LLMCallData,
    SourceTool,
    SpanIdentity,
    TelemetryEnvelope,
)
from vantage.storage.duckdb.telemetry_repository import DuckDBTelemetryRepository


@pytest.fixture
async def duckdb_repo(tmp_path: Path):
    db_file = tmp_path / "test_vantage.duckdb"
    repo = DuckDBTelemetryRepository(db_file)
    yield repo
    await repo.close()


def _make_envelope(trace_id="t1", span_id="s1", ext_id="t1:s1", cost=0.01):
    identity = SpanIdentity(trace_id=trace_id, span_id=span_id)
    payload = LLMCallData(
        model_name="gpt-4o",
        model_provider="openai",
        tokens_input=100,
        tokens_output=50,
        cost_usd=cost,
    )
    return TelemetryEnvelope(
        external_event_id=ext_id,
        project_id="test-proj",
        source_tool=SourceTool.OTEL_GENERIC,
        span=identity,
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        status=EventStatus.SUCCESS,
        payload=payload,
    )


@pytest.mark.asyncio
async def test_insert_and_deduplication(duckdb_repo):
    env1 = _make_envelope("t1", "s1", "t1:s1")

    # First insert -> True
    inserted = await duckdb_repo.insert(env1)
    assert inserted is True

    # Duplicate insert -> False (RETURNING * dedup logic)
    inserted_again = await duckdb_repo.insert(env1)
    assert inserted_again is False


@pytest.mark.asyncio
async def test_query_metrics(duckdb_repo):
    env1 = _make_envelope("t1", "s1", "t1:s1", cost=0.02)
    env2 = _make_envelope("t2", "s2", "t2:s2", cost=0.03)
    await duckdb_repo.insert(env1)
    await duckdb_repo.insert(env2)

    from_dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
    to_dt = datetime(2030, 1, 1, tzinfo=timezone.utc)

    metrics = await duckdb_repo.query_metrics("test-proj", from_dt, to_dt)
    assert len(metrics) == 1
    assert metrics[0]["total_events"] == 2
    assert abs(metrics[0]["total_cost_usd"] - 0.05) < 1e-5


@pytest.mark.asyncio
async def test_rolling_stats_and_error_rate(duckdb_repo):
    env = _make_envelope("t1", "s1", "t1:s1", cost=0.10)
    await duckdb_repo.insert(env)

    stats = await duckdb_repo.get_rolling_stats("test-proj", "cost_usd")
    assert stats["current"] == 0.10
    assert stats["mean"] == 0.10

    err_stats = await duckdb_repo.get_error_rate("test-proj")
    assert err_stats["total_count"] == 1
    assert err_stats["error_count"] == 0
    assert err_stats["error_rate_pct"] == 0.0
