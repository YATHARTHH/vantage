from datetime import datetime, timezone
from typing import Any
from vantage.connectors.base import AbstractConnector
from vantage.core.logging import get_logger
from vantage.domain.events import (
    AgentRunData,
    ChainRunData,
    EventStatus,
    LLMCallData,
    SourceTool,
    SpanIdentity,
    TelemetryEnvelope,
    ToolCallData,
    UnclassifiedData,
)

logger = get_logger(__name__)

SAFE_ATTRIBUTE_ALLOWLIST = {
    "service.name",
    "service.version",
    "service.instance.id",
    "telemetry.sdk.name",
    "telemetry.sdk.version",
    "telemetry.sdk.language",
    "span.kind",
    "http.status_code",
    "rpc.method",
}


def _attr(attributes: list[dict], key: str, default: Any = None) -> Any:
    for attr in attributes:
        if attr.get("key") == key:
            val = attr.get("value", {})
            return (
                val.get("stringValue")
                or val.get("intValue")
                or val.get("doubleValue")
                or val.get("boolValue")
                or default
            )
    return default


def _nano_to_dt(nano_str: str | None) -> datetime | None:
    if not nano_str:
        return None
    try:
        return datetime.fromtimestamp(int(nano_str) / 1e9, tz=timezone.utc)
    except (ValueError, OSError):
        return None


def _status_code_to_event_status(otlp_code: int) -> EventStatus:
    return EventStatus.ERROR if otlp_code == 2 else EventStatus.SUCCESS


class OTLPBatchConnector(AbstractConnector):
    """
    Parses OTLP/HTTP JSON export payloads produced by the OpenTelemetry Collector's
    otlp_http exporter (encoding: json).
    """

    def parse(self, raw_payload: dict[str, Any]) -> list[TelemetryEnvelope]:
        envelopes: list[TelemetryEnvelope] = []
        resource_spans = raw_payload.get("resourceSpans", [])

        for resource_span in resource_spans:
            resource_attrs = resource_span.get("resource", {}).get("attributes", [])
            service_name = _attr(resource_attrs, "service.name", "unknown")
            source_id = _attr(resource_attrs, "vantage.project") or service_name

            source_tool_str = (
                _attr(resource_attrs, "vantage.source_tool")
                or _attr(resource_attrs, "telemetry.sdk.name")
                or ""
            ).lower()

            if "langfuse" in source_tool_str:
                source_tool = SourceTool.LANGFUSE
            elif "langsmith" in source_tool_str:
                source_tool = SourceTool.LANGSMITH
            elif "langchain" in source_tool_str:
                source_tool = SourceTool.LANGCHAIN
            else:
                source_tool = SourceTool.OTEL_GENERIC

            for scope_span in resource_span.get("scopeSpans", []):
                scope_name = scope_span.get("scope", {}).get("name", "")

                for span in scope_span.get("spans", []):
                    try:
                        envelope = self._parse_span(span, source_id, source_tool, scope_name)
                        if envelope:
                            envelopes.append(envelope)
                    except Exception as exc:
                        logger.warning(
                            "otlp_span_parse_error",
                            span_id=span.get("spanId"),
                            error=str(exc),
                        )

        return envelopes

    def _parse_span(
        self, span: dict, source_identifier: str, source_tool: SourceTool, scope_name: str
    ) -> TelemetryEnvelope | None:
        attrs = span.get("attributes", [])
        span_name = span.get("name", "")

        trace_id = span.get("traceId", "")
        span_id = span.get("spanId", "")
        parent_span_id = span.get("parentSpanId") or None

        started_at = _nano_to_dt(span.get("startTimeUnixNano"))
        ended_at = _nano_to_dt(span.get("endTimeUnixNano"))
        if not started_at:
            return None

        status_code = span.get("status", {}).get("code", 0)
        status = _status_code_to_event_status(status_code)
        error_msg = span.get("status", {}).get("message") if status == EventStatus.ERROR else None

        identity = SpanIdentity(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            source_trace_id=trace_id,
            source_span_id=span_id,
        )

        ext_event_id = f"{trace_id}:{span_id}"
        payload = self._classify_span(span_name, attrs, scope_name)

        return TelemetryEnvelope(
            external_event_id=ext_event_id,
            project_id="__unmapped__",
            source_tool=source_tool,
            span=identity,
            started_at=started_at,
            ended_at=ended_at,
            status=status,
            error_message=error_msg,
            payload=payload,
        )

    def _classify_span(self, name: str, attrs: list, scope: str):
        model = _attr(attrs, "gen_ai.request.model")
        if model:
            provider = _attr(attrs, "gen_ai.system", "unknown")
            tokens_in = int(_attr(attrs, "gen_ai.usage.input_tokens", 0) or 0)
            tokens_out = int(_attr(attrs, "gen_ai.usage.output_tokens", 0) or 0)
            return LLMCallData(
                model_name=model,
                model_provider=provider,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
            )

        if "agent" in name.lower() or "run" in name.lower():
            return AgentRunData(agent_name=name)

        tool_name = _attr(attrs, "gen_ai.tool.name") or _attr(attrs, "tool.name")
        if tool_name:
            return ToolCallData(tool_name=tool_name)

        if "chain" in name.lower() or "retrieval" in name.lower():
            return ChainRunData(chain_type=name)

        safe_attrs = {}
        for a in attrs:
            k = a.get("key")
            if k in SAFE_ATTRIBUTE_ALLOWLIST:
                safe_attrs[k] = str(a.get("value", {}))

        return UnclassifiedData(raw_span_name=name, safe_attributes=safe_attrs)
