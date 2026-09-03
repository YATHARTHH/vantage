"""Telemetry Normalizer for Vantage.

Parses OTLP/HTTP Protobuf JSON and custom REST JSON span payloads into a unified
CanonicalVantageSpan structure. Normalizes GenAI OTel semantic conventions.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CanonicalVantageSpan(BaseModel):
    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    project_id: str = "default"
    span_type: str = "llm_call"  # llm_call | agent_run | tool_call | vector_search
    name: str
    agent_name: Optional[str] = None
    model_name: Optional[str] = None
    model_provider: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    start_time: str
    end_time: str
    status: str = "success"  # success | error
    error_message: Optional[str] = None
    prompt: Optional[str] = None
    completion: Optional[str] = None
    system_prompt: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[str] = None
    tool_output: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    pii_scrubbed: bool = False
    pii_types: List[str] = Field(default_factory=list)


# Mapping of OpenTelemetry GenAI Semantic Conventions -> CanonicalVantageSpan fields
OTEL_GENAI_MAPPINGS = {
    "gen_ai.provider.name": "model_provider",
    "gen_ai.system": "model_provider",
    "gen_ai.request.model": "model_name",
    "gen_ai.response.model": "model_name",
    "gen_ai.usage.input_tokens": "tokens_input",
    "gen_ai.usage.prompt_tokens": "tokens_input",
    "gen_ai.usage.output_tokens": "tokens_output",
    "gen_ai.usage.completion_tokens": "tokens_output",
    "gen_ai.input.messages": "prompt",
    "gen_ai.output.messages": "completion",
    "gen_ai.system_instructions": "system_prompt",
    "gen_ai.prompt": "prompt",
    "gen_ai.completion": "completion",
}


def _extract_key_value(kv: Dict[str, Any]) -> Any:
    """Helper to extract values from OTel KeyValue JSON structure."""
    val = kv.get("value", {})
    if "stringValue" in val:
        return val["stringValue"]
    if "intValue" in val:
        return int(val["intValue"])
    if "doubleValue" in val:
        return float(val["doubleValue"])
    if "boolValue" in val:
        return bool(val["boolValue"])
    if "arrayValue" in val:
        values = val["arrayValue"].get("values", [])
        return [_extract_key_value({"value": v}) for v in values]
    if "kvlistValue" in val:
        values = val["kvlistValue"].get("values", [])
        return {item["key"]: _extract_key_value(item) for item in values}
    return str(val)


def normalize_otlp_span(otel_span: Dict[str, Any], project_id: str) -> CanonicalVantageSpan:
    """Translates an OTLP JSON span object into a CanonicalVantageSpan."""
    span_id = otel_span.get("spanId", otel_span.get("span_id", ""))
    trace_id = otel_span.get("traceId", otel_span.get("trace_id", ""))
    parent_span_id = otel_span.get("parentSpanId", otel_span.get("parent_span_id", None))
    name = otel_span.get("name", "unnamed_span")

    # Attributes extraction
    raw_attrs = otel_span.get("attributes", [])
    attr_dict: Dict[str, Any] = {}
    if isinstance(raw_attrs, list):
        for kv in raw_attrs:
            if isinstance(kv, dict) and "key" in kv:
                attr_dict[kv["key"]] = _extract_key_value(kv)
    elif isinstance(raw_attrs, dict):
        attr_dict = raw_attrs

    # Map standard GenAI fields
    model_provider = attr_dict.get("gen_ai.provider.name", attr_dict.get("gen_ai.system"))
    model_name = attr_dict.get("gen_ai.request.model", attr_dict.get("gen_ai.response.model"))
    tokens_input = int(attr_dict.get("gen_ai.usage.input_tokens", attr_dict.get("gen_ai.usage.prompt_tokens", 0)))
    tokens_output = int(attr_dict.get("gen_ai.usage.output_tokens", attr_dict.get("gen_ai.usage.completion_tokens", 0)))
    
    prompt = attr_dict.get("gen_ai.input.messages", attr_dict.get("gen_ai.prompt"))
    if isinstance(prompt, (dict, list)):
        prompt = json.dumps(prompt)
        
    completion = attr_dict.get("gen_ai.output.messages", attr_dict.get("gen_ai.completion"))
    if isinstance(completion, (dict, list)):
        completion = json.dumps(completion)

    system_prompt = attr_dict.get("gen_ai.system_instructions")
    if isinstance(system_prompt, (dict, list)):
        system_prompt = json.dumps(system_prompt)

    # Calculate latency from start/end unix nano timestamps
    start_nano = int(otel_span.get("startTimeUnixNano", 0))
    end_nano = int(otel_span.get("endTimeUnixNano", 0))
    latency_ms = (end_nano - start_nano) / 1e6 if end_nano > start_nano else 0.0

    now_iso = datetime.now(timezone.utc).isoformat()
    start_time = datetime.fromtimestamp(start_nano / 1e9, tz=timezone.utc).isoformat() if start_nano else now_iso
    end_time = datetime.fromtimestamp(end_nano / 1e9, tz=timezone.utc).isoformat() if end_nano else now_iso

    # Status evaluation
    status = "success"
    status_obj = otel_span.get("status", {})
    if status_obj.get("code") in ("STATUS_CODE_ERROR", "ERROR", 2):
        status = "error"

    span_type = attr_dict.get("vantage.span_type", "llm_call" if tokens_input or tokens_output else "agent_run")

    return CanonicalVantageSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        project_id=project_id,
        span_type=span_type,
        name=name,
        agent_name=attr_dict.get("vantage.agent_name", name),
        model_name=model_name,
        model_provider=model_provider,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        cost_usd=float(attr_dict.get("vantage.cost_usd", 0.0)),
        latency_ms=latency_ms,
        start_time=start_time,
        end_time=end_time,
        status=status,
        error_message=status_obj.get("message"),
        prompt=prompt,
        completion=completion,
        system_prompt=system_prompt,
        tool_name=attr_dict.get("tool.name"),
        tool_input=str(attr_dict.get("tool.input")) if "tool.input" in attr_dict else None,
        tool_output=str(attr_dict.get("tool.output")) if "tool.output" in attr_dict else None,
        attributes=attr_dict,
    )
