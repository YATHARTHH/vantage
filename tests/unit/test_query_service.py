from datetime import datetime, timezone
from pathlib import Path
import pytest

from vantage.domain.events import EventStatus, LLMCallData, AgentRunData, SourceTool, SpanIdentity, TelemetryEnvelope
from vantage.services.query_service import QueryService
from vantage.storage.duckdb.telemetry_repository import DuckDBTelemetryRepository


@pytest.fixture
async def query_svc(tmp_path: Path):
    db_file = tmp_path / "query_test.duckdb"
    repo = DuckDBTelemetryRepository(db_file)
    svc = QueryService(repo)

    # Ingest Agent Run (root span, parent_span_id = None)
    agent_env = TelemetryEnvelope(
        external_event_id="q-root",
        project_id="search-v2",
        source_tool=SourceTool.LANGCHAIN,
        span=SpanIdentity(trace_id="t-100", span_id="s-100", parent_span_id=None),
        started_at=datetime.now(timezone.utc),
        status=EventStatus.SUCCESS,
        payload=AgentRunData(agent_name="SearchAgent"),
    )
    await repo.insert(agent_env)

    # Ingest Child LLM Call 1
    llm1 = TelemetryEnvelope(
        external_event_id="q-child-1",
        project_id="search-v2",
        source_tool=SourceTool.LANGCHAIN,
        span=SpanIdentity(trace_id="t-100", span_id="s-101", parent_span_id="s-100"),
        started_at=datetime.now(timezone.utc),
        status=EventStatus.SUCCESS,
        payload=LLMCallData(model_name="gpt-4o", model_provider="openai", tokens_input=100, tokens_output=50, cost_usd=0.02),
    )
    await repo.insert(llm1)

    # Ingest Child LLM Call 2
    llm2 = TelemetryEnvelope(
        external_event_id="q-child-2",
        project_id="search-v2",
        source_tool=SourceTool.LANGCHAIN,
        span=SpanIdentity(trace_id="t-100", span_id="s-102", parent_span_id="s-100"),
        started_at=datetime.now(timezone.utc),
        status=EventStatus.SUCCESS,
        payload=LLMCallData(model_name="gpt-4o", model_provider="openai", tokens_input=200, tokens_output=100, cost_usd=0.03),
    )
    await repo.insert(llm2)

    yield svc
    await repo.close()


@pytest.mark.asyncio
async def test_get_metrics(query_svc):
    metrics = await query_svc.get_metrics("search-v2", hours=24)
    assert len(metrics) >= 1


@pytest.mark.asyncio
async def test_agent_cost_aggregation(query_svc):
    runs = await query_svc.get_agent_runs_aggregated("search-v2", hours=24)
    assert len(runs) == 1
    run = runs[0]
    assert run["trace_id"] == "t-100"
    assert run["llm_call_count"] == 2
    assert run["total_cost_usd"] == pytest.approx(0.05)
    assert run["tokens_input"] == 300
    assert run["tokens_output"] == 150
