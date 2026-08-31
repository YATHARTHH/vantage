from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from vantage.connectors.base import AbstractConnector
from vantage.domain.events import (
    AgentRunData,
    EventStatus,
    LLMCallData,
    SourceTool,
    SpanIdentity,
    TelemetryEnvelope,
)


class CustomRunConnector(AbstractConnector):
    """Parses custom agent run payloads (POST /api/v1/ingest/run)."""

    def parse(self, raw_payload: dict[str, Any]) -> list[TelemetryEnvelope]:
        project_id = raw_payload.get("project_id", "__unmapped__")
        run_name = raw_payload.get("run_name", "custom_agent_run")
        trace_id = raw_payload.get("trace_id", str(uuid4()).replace("-", ""))
        span_id = raw_payload.get("span_id", str(uuid4())[:16].replace("-", ""))
        parent_span_id = raw_payload.get("parent_span_id")
        idempotency_key = raw_payload.get("idempotency_key") or f"custom-{trace_id}-{span_id}"

        status_str = raw_payload.get("status", "success").lower()
        status = EventStatus.SUCCESS if status_str == "success" else EventStatus.ERROR
        error_msg = raw_payload.get("error_message")

        started_at = datetime.now(timezone.utc)
        duration_ms = raw_payload.get("duration_ms")

        identity = SpanIdentity(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            source_trace_id=trace_id,
            source_span_id=span_id,
        )

        model = raw_payload.get("model_name")
        if model:
            payload = LLMCallData(
                model_name=model,
                model_provider=raw_payload.get("model_provider", "custom"),
                tokens_input=raw_payload.get("tokens_input", 0),
                tokens_output=raw_payload.get("tokens_output", 0),
                cost_usd=raw_payload.get("cost_usd"),
                prompt_preview=raw_payload.get("prompt_preview"),
                completion_preview=raw_payload.get("completion_preview"),
            )
        else:
            payload = AgentRunData(agent_name=run_name)

        envelope = TelemetryEnvelope(
            external_event_id=idempotency_key,
            project_id=project_id,
            source_tool=SourceTool.CUSTOM_AGENT,
            span=identity,
            started_at=started_at,
            duration_ms=float(duration_ms) if duration_ms else None,
            status=status,
            error_message=error_msg,
            payload=payload,
        )
        return [envelope]
