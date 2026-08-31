from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, model_validator


class EventStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RUNNING = "running"


class SourceTool(str, Enum):
    LANGFUSE = "langfuse"
    LANGSMITH = "langsmith"
    LANGCHAIN = "langchain"
    CUSTOM_AGENT = "custom_agent"
    GITHUB_ACTIONS = "github_actions"
    JENKINS = "jenkins"
    OTEL_GENERIC = "otel_generic"


class SpanIdentity(BaseModel):
    """
    Span execution hierarchy.
    """
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    source_span_id: str | None = None
    source_trace_id: str | None = None


class LLMCallData(BaseModel):
    kind: Literal["llm_call"] = "llm_call"
    model_name: str
    model_provider: str
    tokens_input: int
    tokens_output: int
    cost_usd: float | None = None
    prompt_preview: str | None = None
    completion_preview: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class AgentRunData(BaseModel):
    """
    Agent run root span.
    Note: total_cost_usd derived at query time from child LLM spans (parent_span_id IS NULL filter).
    """
    kind: Literal["agent_run"] = "agent_run"
    agent_name: str
    total_llm_calls: int | None = None
    total_tool_calls: int | None = None


class ToolCallData(BaseModel):
    kind: Literal["tool_call"] = "tool_call"
    tool_name: str
    tool_input: str | None = None
    tool_output: str | None = None
    is_error: bool = False


class ChainRunData(BaseModel):
    kind: Literal["chain_run"] = "chain_run"
    chain_type: str
    total_steps: int | None = None


class BuildData(BaseModel):
    kind: Literal["build"] = "build"
    repo_name: str
    branch: str
    commit_sha: str | None = None
    pipeline_name: str
    triggered_by: str | None = None


class DeployData(BaseModel):
    kind: Literal["deploy"] = "deploy"
    repo_name: str
    environment: str
    version: str | None = None
    commit_sha: str | None = None
    pipeline_name: str | None = None
    deployed_by: str | None = None


class TestRunData(BaseModel):
    kind: Literal["test_run"] = "test_run"
    repo_name: str
    suite_name: str
    total_tests: int | None = None
    passed: int | None = None
    failed: int | None = None
    coverage_pct: float | None = None


class UnclassifiedData(BaseModel):
    """
    Fallback for unknown/unclassified telemetry spans.
    Prevents silent dropping of spans while enforcing PII safety via a strict attribute allowlist.
    """
    kind: Literal["unclassified"] = "unclassified"
    raw_span_name: str
    safe_attributes: dict[str, str] = Field(default_factory=dict)


EventPayload = Annotated[
    Union[
        LLMCallData,
        AgentRunData,
        ToolCallData,
        ChainRunData,
        BuildData,
        DeployData,
        TestRunData,
        UnclassifiedData,
    ],
    Field(discriminator="kind"),
]


class TelemetryEnvelope(BaseModel):
    """
    Universal event container.

    Identity:
      - event_id: Vantage internal unique event UUID
      - external_event_id: Stable deduplication key (e.g. "trace_id:span_id" or GitHub delivery ID)
    """
    event_id: UUID = Field(default_factory=uuid4)
    external_event_id: str | None = Field(
        default=None, description="External deduplication key"
    )
    project_id: str = Field(...)
    source_tool: SourceTool
    span: SpanIdentity

    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: float | None = None

    status: EventStatus
    error_message: str | None = None
    error_type: str | None = None

    owner_team: str | None = None
    environment: str = "production"
    tags: dict[str, str] = Field(default_factory=dict)

    payload: EventPayload

    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def compute_duration(self) -> "TelemetryEnvelope":
        if self.ended_at and self.started_at and self.duration_ms is None:
            delta = (self.ended_at - self.started_at).total_seconds() * 1000
            object.__setattr__(self, "duration_ms", round(delta, 2))
        return self

    @property
    def event_kind(self) -> str:
        return self.payload.kind

    @property
    def is_error(self) -> bool:
        return self.status == EventStatus.ERROR

    @property
    def cost_usd(self) -> float | None:
        if isinstance(self.payload, LLMCallData):
            return self.payload.cost_usd
        return None
