from vantage.connectors.otel_batch import OTLPBatchConnector
from vantage.domain.events import SourceTool


def test_otlp_http_json_export_fixture():
    """
    Fixture test validating the exact OTLP/HTTP JSON export contract
    sent by OpenTelemetry Collector (otlp_http exporter with encoding: json).
    """
    otlp_fixture = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "recommendation-service"}},
                        {"key": "vantage.project", "value": {"stringValue": "recs-v1"}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": "langchain-python"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "langchain.chains"},
                        "spans": [
                            {
                                "traceId": "7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c",
                                "spanId": "1a2b3c4d5e6f7a8b",
                                "parentSpanId": "",
                                "name": "LLMChain",
                                "kind": 1,
                                "startTimeUnixNano": "1725148800000000000",
                                "endTimeUnixNano": "1725148802500000000",
                                "attributes": [
                                    {"key": "span.kind", "value": {"stringValue": "INTERNAL"}}
                                ],
                                "status": {"code": 1},
                            },
                            {
                                "traceId": "7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c",
                                "spanId": "8b7a6f5e4d3c2b1a",
                                "parentSpanId": "1a2b3c4d5e6f7a8b",
                                "name": "ChatAnthropic",
                                "kind": 3,
                                "startTimeUnixNano": "1725148800500000000",
                                "endTimeUnixNano": "1725148802400000000",
                                "attributes": [
                                    {"key": "gen_ai.system", "value": {"stringValue": "anthropic"}},
                                    {"key": "gen_ai.request.model", "value": {"stringValue": "claude-3-5-sonnet-20241022"}},
                                    {"key": "gen_ai.usage.input_tokens", "value": {"intValue": 1024}},
                                    {"key": "gen_ai.usage.output_tokens", "value": {"intValue": 256}},
                                ],
                                "status": {"code": 1},
                            },
                        ],
                    }
                ],
            }
        ]
    }

    connector = OTLPBatchConnector()
    envelopes = connector.parse(otlp_fixture)

    assert len(envelopes) == 2

    # Root chain span
    chain_env = envelopes[0]
    assert chain_env.span.trace_id == "7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c"
    assert chain_env.span.span_id == "1a2b3c4d5e6f7a8b"
    assert chain_env.span.parent_span_id is None
    assert chain_env.event_kind == "chain_run"
    assert chain_env.source_tool == SourceTool.LANGCHAIN

    # Child LLM span
    llm_env = envelopes[1]
    assert llm_env.span.trace_id == "7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c"
    assert llm_env.span.span_id == "8b7a6f5e4d3c2b1a"
    assert llm_env.span.parent_span_id == "1a2b3c4d5e6f7a8b"
    assert llm_env.event_kind == "llm_call"
    assert llm_env.payload.model_name == "claude-3-5-sonnet-20241022"
    assert llm_env.payload.tokens_input == 1024
    assert llm_env.payload.tokens_output == 256
