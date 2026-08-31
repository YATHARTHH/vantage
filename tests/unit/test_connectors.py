import pytest
from vantage.connectors.custom_run import CustomRunConnector
from vantage.connectors.github import GitHubWebhookConnector
from vantage.connectors.jenkins import JenkinsWebhookConnector
from vantage.connectors.otel_batch import OTLPBatchConnector
from vantage.domain.events import EventStatus, SourceTool


def test_otlp_batch_connector_llm_span():
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "search-agent"}},
                        {"key": "vantage.source_tool", "value": {"stringValue": "langchain"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "langchain.tracer"},
                        "spans": [
                            {
                                "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
                                "spanId": "00f067aa0ba902b7",
                                "name": "ChatOpenAI",
                                "startTimeUnixNano": "1723000000000000000",
                                "endTimeUnixNano": "1723000001500000000",
                                "attributes": [
                                    {"key": "gen_ai.system", "value": {"stringValue": "openai"}},
                                    {"key": "gen_ai.request.model", "value": {"stringValue": "gpt-4o"}},
                                    {"key": "gen_ai.usage.input_tokens", "value": {"intValue": 512}},
                                    {"key": "gen_ai.usage.output_tokens", "value": {"intValue": 128}},
                                ],
                                "status": {"code": 1},
                            }
                        ],
                    }
                ],
            }
        ]
    }

    connector = OTLPBatchConnector()
    envelopes = connector.parse(payload)

    assert len(envelopes) == 1
    env = envelopes[0]
    assert env.source_tool == SourceTool.LANGCHAIN
    assert env.event_kind == "llm_call"
    assert env.payload.model_name == "gpt-4o"
    assert env.payload.tokens_input == 512
    assert env.payload.tokens_output == 128


def test_github_webhook_connector():
    payload = {
        "action": "completed",
        "workflow_run": {
            "id": 123456789,
            "name": "CI Build",
            "head_branch": "main",
            "head_sha": "a1b2c3d4e5",
            "event": "push",
            "conclusion": "success",
            "created_at": "2026-08-31T12:00:00Z",
            "updated_at": "2026-08-31T12:05:00Z",
        },
        "repository": {"full_name": "company/search-repo"},
    }

    connector = GitHubWebhookConnector()
    envelopes = connector.parse(payload)

    assert len(envelopes) == 1
    env = envelopes[0]
    assert env.source_tool == SourceTool.GITHUB_ACTIONS
    assert env.external_event_id == "github-company/search-repo-123456789"
    assert env.event_kind == "build"
    assert env.status == EventStatus.SUCCESS


def test_jenkins_webhook_connector():
    payload = {
        "name": "search-pipeline",
        "build": {
            "number": 42,
            "phase": "COMPLETED",
            "status": "SUCCESS",
            "duration": 45000,
        },
    }

    connector = JenkinsWebhookConnector()
    envelopes = connector.parse(payload)

    assert len(envelopes) == 1
    env = envelopes[0]
    assert env.source_tool == SourceTool.JENKINS
    assert env.external_event_id == "jenkins-search-pipeline-42"
    assert env.event_kind == "build"


def test_custom_run_connector():
    payload = {
        "project_id": "search-v2",
        "run_name": "custom-eval-run",
        "model_name": "claude-3-5-sonnet-20241022",
        "tokens_input": 200,
        "tokens_output": 100,
        "status": "success",
    }

    connector = CustomRunConnector()
    envelopes = connector.parse(payload)

    assert len(envelopes) == 1
    env = envelopes[0]
    assert env.project_id == "search-v2"
    assert env.source_tool == SourceTool.CUSTOM_AGENT
    assert env.event_kind == "llm_call"
    assert env.payload.model_name == "claude-3-5-sonnet-20241022"
