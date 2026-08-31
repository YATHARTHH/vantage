from datetime import datetime, timezone
import pytest
from vantage.domain.events import (
    TelemetryEnvelope,
    SpanIdentity,
    SourceTool,
    EventStatus,
    LLMCallData,
    UnclassifiedData,
    AlertRecord,
    DetectorType,
    AlertSeverity,
)


def test_telemetry_envelope_llm_call():
    identity = SpanIdentity(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
    )
    payload = LLMCallData(
        model_name="gpt-4o",
        model_provider="openai",
        tokens_input=100,
        tokens_output=50,
        cost_usd=0.001,
    )
    started = datetime.now(timezone.utc)
    ended = datetime.now(timezone.utc)

    envelope = TelemetryEnvelope(
        external_event_id="4bf92f3577b34da6a3ce929d0e0e4736:00f067aa0ba902b7",
        project_id="test-project",
        source_tool=SourceTool.OTEL_GENERIC,
        span=identity,
        started_at=started,
        ended_at=ended,
        status=EventStatus.SUCCESS,
        payload=payload,
    )

    assert envelope.project_id == "test-project"
    assert envelope.event_kind == "llm_call"
    assert envelope.cost_usd == 0.001
    assert envelope.external_event_id == "4bf92f3577b34da6a3ce929d0e0e4736:00f067aa0ba902b7"


def test_unclassified_data_safe_attributes():
    payload = UnclassifiedData(
        raw_span_name="unknown_span",
        safe_attributes={"service.name": "search_service", "span.kind": "CLIENT"},
    )
    assert payload.kind == "unclassified"
    assert payload.safe_attributes["service.name"] == "search_service"


def test_alert_record_unique_uuid():
    alert1 = AlertRecord(
        project_id="p1",
        detector_type=DetectorType.Z_SCORE,
        metric_name="cost_usd",
        severity=AlertSeverity.WARNING,
        message="Cost anomaly",
        current_value=1.5,
        fired_at=datetime.now(timezone.utc),
    )
    alert2 = AlertRecord(
        project_id="p1",
        detector_type=DetectorType.Z_SCORE,
        metric_name="cost_usd",
        severity=AlertSeverity.WARNING,
        message="Cost anomaly",
        current_value=1.5,
        fired_at=datetime.now(timezone.utc),
    )
    assert alert1.alert_id != alert2.alert_id
