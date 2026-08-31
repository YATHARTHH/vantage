from datetime import datetime, timezone
from pathlib import Path
import pytest

from vantage.anomaly.error_rate import ErrorRateDetector
from vantage.anomaly.rate_change import RateChangeDetector
from vantage.anomaly.threshold import ThresholdDetector
from vantage.anomaly.volume import VolumeDetector
from vantage.anomaly.zscore import ZScoreDetector
from vantage.domain.alerts import AlertRecord, AlertRule, AlertSeverity, DetectorType
from vantage.domain.events import EventStatus, LLMCallData, SourceTool, SpanIdentity, TelemetryEnvelope
from vantage.services.anomaly_service import AnomalyService
from vantage.services.notification_service import NotificationService
from vantage.storage.duckdb.telemetry_repository import DuckDBTelemetryRepository
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository
from vantage.storage.sqlalchemy.models import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
async def anomaly_repos(tmp_path: Path):
    duck_file = tmp_path / "anomaly_test.duckdb"
    telemetry_repo = DuckDBTelemetryRepository(duck_file)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    metadata_repo = SQLiteMetadataRepository(session_factory)

    yield telemetry_repo, metadata_repo
    await telemetry_repo.close()
    await engine.dispose()


@pytest.mark.asyncio
async def test_zscore_detector(anomaly_repos):
    telemetry, _ = anomaly_repos
    detector = ZScoreDetector("cost_usd")
    rule = AlertRule(project_id="proj1", detector_type=DetectorType.Z_SCORE, metric_name="cost_usd", warn_z=2.0, crit_z=3.0)

    # Baseline events (cost = 0.01)
    for i in range(10):
        env = TelemetryEnvelope(
            external_event_id=f"z-{i}",
            project_id="proj1",
            source_tool=SourceTool.OTEL_GENERIC,
            span=SpanIdentity(trace_id=f"t-{i}", span_id=f"s-{i}"),
            started_at=datetime.now(timezone.utc),
            status=EventStatus.SUCCESS,
            payload=LLMCallData(model_name="gpt-4o", model_provider="openai", tokens_input=100, tokens_output=50, cost_usd=0.01),
        )
        await telemetry.insert(env)

    # Spike event (cost = 1.0)
    spike_env = TelemetryEnvelope(
        external_event_id="z-spike",
        project_id="proj1",
        source_tool=SourceTool.OTEL_GENERIC,
        span=SpanIdentity(trace_id="t-spike", span_id="s-spike"),
        started_at=datetime.now(timezone.utc),
        status=EventStatus.SUCCESS,
        payload=LLMCallData(model_name="gpt-4o", model_provider="openai", tokens_input=100, tokens_output=50, cost_usd=1.00),
    )
    await telemetry.insert(spike_env)

    res = await detector.detect("proj1", telemetry, rule)
    assert res is not None
    assert res.detector_type == DetectorType.Z_SCORE
    assert res.severity in (AlertSeverity.WARNING, AlertSeverity.CRITICAL)


@pytest.mark.asyncio
async def test_threshold_detector(anomaly_repos):
    telemetry, _ = anomaly_repos
    detector = ThresholdDetector("cost_usd")
    rule = AlertRule(project_id="proj1", detector_type=DetectorType.THRESHOLD, metric_name="cost_usd", absolute_threshold=0.05)

    env = TelemetryEnvelope(
        external_event_id="th-1",
        project_id="proj1",
        source_tool=SourceTool.OTEL_GENERIC,
        span=SpanIdentity(trace_id="t1", span_id="s1"),
        started_at=datetime.now(timezone.utc),
        status=EventStatus.SUCCESS,
        payload=LLMCallData(model_name="gpt-4o", model_provider="openai", tokens_input=100, tokens_output=50, cost_usd=0.10),
    )
    await telemetry.insert(env)

    res = await detector.detect("proj1", telemetry, rule)
    assert res is not None
    assert res.detector_type == DetectorType.THRESHOLD
    assert res.current_value == 0.10


@pytest.mark.asyncio
async def test_rate_change_detector(anomaly_repos):
    telemetry, _ = anomaly_repos
    detector = RateChangeDetector("cost_usd")
    rule = AlertRule(project_id="proj1", detector_type=DetectorType.RATE_CHANGE, metric_name="cost_usd", rate_change_factor=1.5)

    for i in range(5):
        env = TelemetryEnvelope(
            external_event_id=f"rc-{i}",
            project_id="proj1",
            source_tool=SourceTool.OTEL_GENERIC,
            span=SpanIdentity(trace_id=f"t-{i}", span_id=f"s-{i}"),
            started_at=datetime.now(timezone.utc),
            status=EventStatus.SUCCESS,
            payload=LLMCallData(model_name="gpt-4o", model_provider="openai", tokens_input=100, tokens_output=50, cost_usd=0.01),
        )
        await telemetry.insert(env)

    spike = TelemetryEnvelope(
        external_event_id="rc-spike",
        project_id="proj1",
        source_tool=SourceTool.OTEL_GENERIC,
        span=SpanIdentity(trace_id="tsp", span_id="ssp"),
        started_at=datetime.now(timezone.utc),
        status=EventStatus.SUCCESS,
        payload=LLMCallData(model_name="gpt-4o", model_provider="openai", tokens_input=100, tokens_output=50, cost_usd=0.05),
    )
    await telemetry.insert(spike)

    res = await detector.detect("proj1", telemetry, rule)
    assert res is not None
    assert res.detector_type == DetectorType.RATE_CHANGE


@pytest.mark.asyncio
async def test_incident_suppression_flow(anomaly_repos):
    telemetry, metadata = anomaly_repos
    notifier = NotificationService()
    service = AnomalyService(telemetry, metadata, notifier)

    # Insert a threshold-exceeding event
    env = TelemetryEnvelope(
        external_event_id="inc-1",
        project_id="search-v2",
        source_tool=SourceTool.OTEL_GENERIC,
        span=SpanIdentity(trace_id="t1", span_id="s1"),
        started_at=datetime.now(timezone.utc),
        status=EventStatus.SUCCESS,
        payload=LLMCallData(model_name="gpt-4o", model_provider="openai", tokens_input=100, tokens_output=50, cost_usd=5.00),
    )
    await telemetry.insert(env)

    rule = AlertRule(
        project_id="search-v2",
        detector_type=DetectorType.THRESHOLD,
        metric_name="cost_usd",
        absolute_threshold=1.00,
    )
    await metadata.save_alert_rule(rule)

    # First cycle -> fires 1 alert
    fired_1 = await service.run_detection_cycle()
    assert fired_1 >= 1

    # Second cycle immediately after -> suppressed (0 new alerts)
    fired_2 = await service.run_detection_cycle()
    assert fired_2 == 0

    # Resolve alert
    alerts = await metadata.list_alerts("search-v2", unresolved_only=True)
    assert len(alerts) >= 1
    await metadata.resolve_alert(str(alerts[0].alert_id))

    # Third cycle after resolution -> fires new alert
    fired_3 = await service.run_detection_cycle()
    assert fired_3 >= 1
