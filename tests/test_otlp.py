"""Unit tests for OTLP/HTTP standard ingestion adapter and telemetry normalizer."""
import gzip
import json
import pytest
from vantage.ingest.normalizer import normalize_otlp_span, CanonicalVantageSpan
from vantage.api.v1.otlp import _is_duplicate, DEDUP_CACHE


def test_normalize_otlp_span():
    otel_span = {
        "traceId": "trace-101",
        "spanId": "span-202",
        "parentSpanId": "span-100",
        "name": "llm_completion",
        "startTimeUnixNano": 1700000000000000000,
        "endTimeUnixNano": 1700000001500000000,
        "attributes": [
            {"key": "gen_ai.provider.name", "value": {"stringValue": "openai"}},
            {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o"}},
            {"key": "gen_ai.usage.input_tokens", "value": {"intValue": 150}},
            {"key": "gen_ai.usage.output_tokens", "value": {"intValue": 45}},
            {"key": "gen_ai.input.messages", "value": {"stringValue": "Hello AI"}},
            {"key": "gen_ai.output.messages", "value": {"stringValue": "Hello human"}},
        ],
        "status": {"code": "STATUS_CODE_OK"},
    }

    c_span = normalize_otlp_span(otel_span, project_id="search-v2")

    assert c_span.span_id == "span-202"
    assert c_span.trace_id == "trace-101"
    assert c_span.model_provider == "openai"
    assert c_span.model_name == "gpt-4o"
    assert c_span.tokens_input == 150
    assert c_span.tokens_output == 45
    assert c_span.prompt == "Hello AI"
    assert c_span.completion == "Hello human"
    assert c_span.latency_ms == 1500.0


def test_otlp_deduplication():
    DEDUP_CACHE.clear()
    assert _is_duplicate("t-1", "s-1") is False
    assert _is_duplicate("t-1", "s-1") is True  # Duplicate
    assert _is_duplicate("t-1", "s-2") is False
