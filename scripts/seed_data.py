import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from vantage.domain.alerts import AlertRule, DetectorType
from vantage.domain.events import (
    AgentRunData,
    BuildData,
    DeployData,
    EventStatus,
    LLMCallData,
    SourceTool,
    SpanIdentity,
    TelemetryEnvelope,
    ToolCallData,
)
from vantage.domain.experiments import (
    Experiment,
    ExperimentOutcome,
    ExperimentResult,
    ExperimentStatus,
    ModelConfiguration,
)
from vantage.domain.projects import Project, ProjectType, SourceToolMapping
from vantage.storage.duckdb.telemetry_repository import DuckDBTelemetryRepository
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository
from vantage.storage.sqlalchemy.session import get_session_factory, init_db


async def main():
    print("🌱 Starting Vantage seed script...")

    # 1. Initialize SQLite Database & Repositories
    db_factory = get_session_factory()
    await init_db()
    metadata_repo = SQLiteMetadataRepository(db_factory)

    duckdb_path = Path("./data/vantage.duckdb")
    telemetry_repo = DuckDBTelemetryRepository(duckdb_path)

    # 2. Seed Projects
    p1 = Project(
        id="search-v2",
        display_name="LLM Search & RAG Assistant V2",
        project_type=ProjectType.AI_LLM,
        owner_team="AI Search Engineering",
        owner_email="ai-search@company.com",
        description="Production LangChain + LangFuse agent pipeline powering enterprise search.",
        log_prompts=False,
    )
    p2 = Project(
        id="order-service",
        display_name="Order Processing Microservice",
        project_type=ProjectType.SOFTWARE,
        owner_team="Core Platform",
        owner_email="platform@company.com",
        description="Core ordering pipeline and GitHub CI/CD build actions.",
        log_prompts=False,
    )
    await metadata_repo.save_project(p1)
    await metadata_repo.save_project(p2)
    print("  ✅ Seeded 2 Projects (search-v2, order-service)")

    # 3. Seed Source Mappings
    m1 = SourceToolMapping(
        project_id="search-v2",
        source_tool="langfuse",
        source_identifier="search-agent-prod",
        display_label="LangFuse Production Traces",
    )
    m2 = SourceToolMapping(
        project_id="order-service",
        source_tool="github_actions",
        source_identifier="company/order-repo",
        display_label="GitHub Actions CI/CD",
    )
    await metadata_repo.save_source_mapping(m1)
    await metadata_repo.save_source_mapping(m2)
    print("  ✅ Seeded Source Mappings")

    # 4. Seed Experiments
    exp1 = Experiment(
        id="exp-rag-eval-01",
        title="RAG Context Window Expansion Evaluation",
        slug="rag-context-expansion-eval",
        project_id="search-v2",
        status=ExperimentStatus.COMPLETED,
        hypothesis="Expanding chunk retrieval size from 512 to 1024 tokens will improve answer accuracy by 15% without exceeding budget.",
        objective="Measure answer quality vs token cost across Claude 3.5 Sonnet and GPT-4o.",
        owner_name="Alice Engineer",
        owner_team="AI Search",
        owner_email="alice@company.com",
        start_date=date(2026, 8, 1),
        expected_end=date(2026, 8, 15),
        actual_end=date(2026, 8, 14),
        model_configurations=[
            ModelConfiguration(model_name="claude-3-5-sonnet-20241022", model_provider="anthropic", temperature=0.2),
            ModelConfiguration(model_name="gpt-4o", model_provider="openai", temperature=0.3),
        ],
        result=ExperimentResult(
            outcome=ExperimentOutcome.SUCCESS,
            summary="Claude 3.5 Sonnet achieved 94.2% accuracy (+18%) with acceptable 12% cost increase.",
            metrics={"accuracy_pct": 94.2, "latency_p95_ms": 1450.0, "cost_per_query_usd": 0.0042},
            learnings="1024 chunk size reduced hallucination rates significantly on complex tabular documents.",
            recommendations="Promote Claude 3.5 Sonnet with 1024 chunk size to production.",
        ),
    )
    exp2 = Experiment(
        id="exp-haiku-fallback-02",
        title="Claude 3 Haiku Fallback Routing",
        slug="claude-3-haiku-fallback-routing",
        project_id="search-v2",
        status=ExperimentStatus.ACTIVE,
        hypothesis="Routing simple classification queries to Claude 3 Haiku will reduce total AI spend by 35%.",
        objective="Evaluate cost reduction and latency improvement for low-complexity intent classification.",
        owner_name="Bob Developer",
        owner_team="AI Platform",
        owner_email="bob@company.com",
        start_date=date(2026, 8, 20),
        expected_end=date(2026, 9, 5),
    )
    await metadata_repo.save_experiment(exp1)
    await metadata_repo.save_experiment(exp2)
    print("  ✅ Seeded 2 Experiments in Registry")

    # 5. Seed Alert Rules
    rule1 = AlertRule(
        project_id="search-v2",
        detector_type=DetectorType.Z_SCORE,
        metric_name="cost_usd",
        warn_z=2.0,
        crit_z=3.0,
    )
    rule2 = AlertRule(
        project_id="search-v2",
        detector_type=DetectorType.THRESHOLD,
        metric_name="cost_usd",
        absolute_threshold=0.05,
    )
    await metadata_repo.save_alert_rule(rule1)
    await metadata_repo.save_alert_rule(rule2)
    print("  ✅ Seeded Alert Rules")

    # 6. Seed Telemetry Spans into DuckDB
    now = datetime.now(timezone.utc)
    span_count = 0

    for i in range(40):
        t_offset = timedelta(minutes=i * 15)
        dt = now - t_offset
        trace_id = f"trace-seed-{i:03d}"

        # Root Agent Run span
        agent_env = TelemetryEnvelope(
            external_event_id=f"seed-{i}-root",
            project_id="search-v2",
            source_tool=SourceTool.LANGCHAIN,
            span=SpanIdentity(trace_id=trace_id, span_id=f"span-{i}-0", parent_span_id=None),
            started_at=dt,
            ended_at=dt + timedelta(seconds=2),
            status=EventStatus.SUCCESS,
            payload=AgentRunData(agent_name="SearchAgentRunner"),
        )
        await telemetry_repo.insert(agent_env)
        span_count += 1

        # Child LLM span
        cost = 0.005 if i % 10 != 0 else 0.08  # Occasional spike for anomaly testing
        llm_env = TelemetryEnvelope(
            external_event_id=f"seed-{i}-llm",
            project_id="search-v2",
            source_tool=SourceTool.LANGCHAIN,
            span=SpanIdentity(trace_id=trace_id, span_id=f"span-{i}-1", parent_span_id=f"span-{i}-0"),
            started_at=dt + timedelta(milliseconds=100),
            ended_at=dt + timedelta(milliseconds=1800),
            status=EventStatus.ERROR if i % 15 == 0 else EventStatus.SUCCESS,
            payload=LLMCallData(
                model_name="gpt-4o" if i % 2 == 0 else "claude-3-5-sonnet-20241022",
                model_provider="openai" if i % 2 == 0 else "anthropic",
                tokens_input=400 + (i * 10),
                tokens_output=150 + (i * 5),
                cost_usd=cost,
            ),
        )
        await telemetry_repo.insert(llm_env)
        span_count += 1

    # Add GitHub Build/Deploy Spans for order-service
    for j in range(10):
        dt = now - timedelta(hours=j * 2)
        gh_env = TelemetryEnvelope(
            external_event_id=f"seed-gh-{j}",
            project_id="order-service",
            source_tool=SourceTool.GITHUB_ACTIONS,
            span=SpanIdentity(trace_id=f"gh-trace-{j}", span_id=f"gh-span-{j}"),
            started_at=dt,
            ended_at=dt + timedelta(minutes=3),
            status=EventStatus.SUCCESS if j != 3 else EventStatus.ERROR,
            payload=BuildData(
                repo_name="company/order-repo",
                branch="main",
                commit_sha=f"c0mm1t{j}",
                pipeline_name="CI Pipeline",
            ),
        )
        await telemetry_repo.insert(gh_env)
        span_count += 1

    print(f"  ✅ Seeded {span_count} Telemetry Spans into DuckDB")
    await telemetry_repo.close()

    print("🎉 Vantage seed completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
