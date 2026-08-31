from datetime import date, datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from vantage.domain.alerts import AlertRecord, AlertRule, AlertSeverity, DetectorType
from vantage.domain.experiments import Experiment, ExperimentStatus
from vantage.domain.projects import Project, ProjectType, SourceToolMapping
from vantage.storage.sqlalchemy.models import Base
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository


@pytest.fixture
async def sqlite_repo():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    repo = SQLiteMetadataRepository(session_factory)
    yield repo
    await engine.dispose()


@pytest.mark.asyncio
async def test_project_and_source_mapping_crud(sqlite_repo):
    proj = Project(
        id="search-v2",
        display_name="Search Agent V2",
        project_type=ProjectType.AI_LLM,
        owner_team="search-team",
        owner_email="search@company.com",
    )
    saved_proj = await sqlite_repo.save_project(proj)
    assert saved_proj.id == "search-v2"

    mapping = SourceToolMapping(
        project_id="search-v2",
        source_tool="langfuse",
        source_identifier="search-agent-prod",
    )
    saved_mapping = await sqlite_repo.save_source_mapping(mapping)
    assert saved_mapping.project_id == "search-v2"

    fetched = await sqlite_repo.get_source_mapping("langfuse", "search-agent-prod")
    assert fetched is not None
    assert fetched.project_id == "search-v2"


@pytest.mark.asyncio
async def test_alert_rule_unique_constraint(sqlite_repo):
    rule1 = AlertRule(
        project_id="proj1",
        detector_type=DetectorType.Z_SCORE,
        metric_name="cost_usd",
        warn_z=2.5,
    )
    saved1 = await sqlite_repo.save_alert_rule(rule1)
    assert saved1.warn_z == 2.5

    # Update existing rule (same signal)
    rule2 = AlertRule(
        project_id="proj1",
        detector_type=DetectorType.Z_SCORE,
        metric_name="cost_usd",
        warn_z=3.0,
    )
    saved2 = await sqlite_repo.save_alert_rule(rule2)
    assert saved2.warn_z == 3.0

    # Ensure only 1 rule exists
    rules = await sqlite_repo.get_alert_rule("proj1", "z_score", "cost_usd")
    assert rules is not None
    assert rules.warn_z == 3.0


@pytest.mark.asyncio
async def test_active_incident_suppression(sqlite_repo):
    key = "proj1:z_score:cost_usd"

    # Initially no active alert
    assert await sqlite_repo.has_active_alert(key) is False

    alert = AlertRecord(
        project_id="proj1",
        detector_type=DetectorType.Z_SCORE,
        metric_name="cost_usd",
        severity=AlertSeverity.CRITICAL,
        message="Cost anomaly detected",
        current_value=5.0,
        fired_at=datetime.now(timezone.utc),
    )
    inserted = await sqlite_repo.insert_alert(alert)

    # Active alert exists now
    assert await sqlite_repo.has_active_alert(key) is True

    # Resolve alert
    ok = await sqlite_repo.resolve_alert(str(inserted.alert_id))
    assert ok is True

    # Active alert suppressed -> False after resolution
    assert await sqlite_repo.has_active_alert(key) is False
