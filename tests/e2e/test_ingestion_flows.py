import pytest
from datetime import date


@pytest.mark.asyncio
async def test_full_e2e_observability_flow(async_client):
    headers = {"X-API-Key": "dev-local-key"}

    # Proof Point 1: Create Project & Source Mapping
    proj_payload = {
        "id": "e2e-search-v1",
        "display_name": "E2E Search Assistant",
        "project_type": "ai_llm",
        "owner_team": "e2e-team",
        "owner_email": "e2e@company.com",
        "log_prompts": False,
    }
    create_proj_res = await async_client.post("/api/v1/projects", json=proj_payload, headers=headers)
    assert create_proj_res.status_code == 201

    mapping_payload = {
        "source_tool": "langchain",
        "source_identifier": "e2e-service",
    }
    await async_client.post("/api/v1/projects/e2e-search-v1/mappings", json=mapping_payload, headers=headers)

    # Proof Point 2: Ingest OTLP/HTTP JSON Batch (Root Agent Span + Child LLM Span)
    otlp_payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "e2e-service"}},
                        {"key": "vantage.source_tool", "value": {"stringValue": "langchain"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "langchain"},
                        "spans": [
                            # Root Agent Run span (parent_span_id IS NULL)
                            {
                                "traceId": "e2e00000000000000000000000000001",
                                "spanId": "e2e0000000000001",
                                "name": "AgentRunner",
                                "startTimeUnixNano": "1725148800000000000",
                                "endTimeUnixNano": "1725148805000000000",
                                "attributes": [],
                                "status": {"code": 1},
                            },
                            # Child LLM span
                            {
                                "traceId": "e2e00000000000000000000000000001",
                                "spanId": "e2e0000000000002",
                                "parentSpanId": "e2e0000000000001",
                                "name": "ChatOpenAI",
                                "startTimeUnixNano": "1725148800500000000",
                                "endTimeUnixNano": "1725148804500000000",
                                "attributes": [
                                    {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                                    {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o"}},
                                    {"key": "gen_ai.usage.input_tokens", "value": {"intValue": 1000}},
                                    {"key": "gen_ai.usage.output_tokens", "value": {"intValue": 500}},
                                ],
                                "status": {"code": 1},
                            },
                        ],
                    }
                ],
            }
        ]
    }

    ingest_res = await async_client.post(
        "/api/v1/ingest/otel-batch", json=otlp_payload, headers=headers
    )
    assert ingest_res.status_code == 202
    ingest_data = ingest_res.json()
    assert ingest_data["accepted"] is True
    assert ingest_data["stored"] == 2

    # Duplicate ingestion check -> deduplicated=2
    dup_res = await async_client.post(
        "/api/v1/ingest/otel-batch", json=otlp_payload, headers=headers
    )
    assert dup_res.status_code == 202
    assert dup_res.json()["deduplicated"] == 2

    # Proof Point 3: Query Agent Cost Aggregation (root agent span filter)
    cost_res = await async_client.get("/api/v1/query/agent-cost?project_id=e2e-search-v1")
    assert cost_res.status_code == 200
    cost_data = cost_res.json()
    assert len(cost_data) == 1
    assert cost_data[0]["trace_id"] == "e2e00000000000000000000000000001"
    # Cost computed from 1000 input tokens ($0.0025) + 500 output tokens ($0.005) = $0.0075
    assert cost_data[0]["total_cost_usd"] == pytest.approx(0.0075)

    # Proof Point 4: Experiment Registry Integration
    exp_payload = {
        "id": "e2e-exp-01",
        "title": "E2E Accuracy Test",
        "slug": "e2e-accuracy-test",
        "project_id": "e2e-search-v1",
        "hypothesis": "Testing E2E experiment registration.",
        "objective": "Verify registry endpoints.",
        "owner_name": "E2E Tester",
        "owner_team": "QA",
        "owner_email": "qa@company.com",
        "start_date": str(date.today()),
        "expected_end": str(date.today()),
    }
    exp_res = await async_client.post("/api/v1/experiments", json=exp_payload, headers=headers)
    assert exp_res.status_code == 201
    assert exp_res.json()["id"] == "e2e-exp-01"
