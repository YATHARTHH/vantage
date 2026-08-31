from datetime import datetime, timezone
from pathlib import Path
import pytest

from vantage.domain.events import (
    EventStatus,
    LLMCallData,
    SourceTool,
    SpanIdentity,
    TelemetryEnvelope,
)
from vantage.enrichment.cost_enricher import CostEnricher
from vantage.enrichment.pii_filter import PIIFilter
from vantage.enrichment.project_mapper import ProjectMapper
from vantage.storage.base import AbstractMetadataRepository
from vantage.domain.projects import Project, ProjectType, SourceToolMapping


class MockMetadataRepo(AbstractMetadataRepository):
    def __init__(self, log_prompts: bool = False):
        self._log_prompts = log_prompts
        self._mappings = {("langfuse", "search-agent"): "search-v2"}

    async def get_project(self, project_id: str) -> Project | None:
        if project_id == "search-v2":
            return Project(
                id="search-v2",
                display_name="Search V2",
                project_type=ProjectType.AI_LLM,
                owner_team="team",
                owner_email="a@b.com",
                log_prompts=self._log_prompts,
            )
        return None

    async def save_project(self, project: Project) -> Project:
        return project

    async def list_projects(self) -> list[Project]:
        return []

    async def get_source_mapping(self, source_tool: str, source_identifier: str) -> SourceToolMapping | None:
        proj_id = self._mappings.get((source_tool, source_identifier))
        if proj_id:
            return SourceToolMapping(
                project_id=proj_id,
                source_tool=source_tool,
                source_identifier=source_identifier,
            )
        return None

    async def save_source_mapping(self, mapping: SourceToolMapping) -> SourceToolMapping:
        return mapping

    async def get_experiment(self, experiment_id: str): return None
    async def save_experiment(self, experiment): return experiment
    async def list_experiments(self, project_id=None, status=None): return []
    async def get_alert_rule(self, project_id, detector_type=None, metric_name=None): return None
    async def save_alert_rule(self, rule): return rule
    async def has_active_alert(self, incident_key: str): return False
    async def insert_alert(self, alert): return alert
    async def resolve_alert(self, alert_id: str): return True
    async def list_alerts(self, project_id=None, unresolved_only=False): return []


def _make_envelope(project_id="search-v2", prompt="secret prompt"):
    identity = SpanIdentity(trace_id="t1", span_id="s1")
    payload = LLMCallData(
        model_name="gpt-4o",
        model_provider="openai",
        tokens_input=100,
        tokens_output=50,
        prompt_preview=prompt,
        completion_preview="secret answer",
    )
    return TelemetryEnvelope(
        project_id=project_id,
        source_tool=SourceTool.LANGFUSE,
        span=identity,
        started_at=datetime.now(timezone.utc),
        status=EventStatus.SUCCESS,
        payload=payload,
    )


@pytest.mark.asyncio
async def test_cost_enricher(tmp_path: Path):
    prices_file = tmp_path / "model_prices.json"
    prices_file.write_text(
        '{"gpt-4o": {"input_per_token": 0.0000025, "output_per_token": 0.000010}}'
    )
    enricher = CostEnricher(prices_file)

    env = _make_envelope()

    enriched = await enricher.apply(env)
    # (100 * 0.0000025) + (50 * 0.000010) = 0.00025 + 0.00050 = 0.00075
    assert enriched.payload.cost_usd == pytest.approx(0.00075)


@pytest.mark.asyncio
async def test_project_mapper_cache():
    repo = MockMetadataRepo()
    mapper = ProjectMapper(repo, cache_ttl_seconds=60)

    proj_id = await mapper.resolve_project_id("langfuse", "search-agent")
    assert proj_id == "search-v2"

    # From cache
    cached_id = await mapper.resolve_project_id("langfuse", "search-agent")
    assert cached_id == "search-v2"

    unmapped = await mapper.resolve_project_id("unknown_tool", "unknown_id")
    assert unmapped == "__unmapped__"


@pytest.mark.asyncio
async def test_pii_filter_stripping():
    # log_prompts=False -> should strip prompts
    repo_no_log = MockMetadataRepo(log_prompts=False)
    pii_filter = PIIFilter(repo_no_log)

    env = _make_envelope()
    filtered = await pii_filter.apply(env)
    assert filtered.payload.prompt_preview is None
    assert filtered.payload.completion_preview is None

    # log_prompts=True -> should keep prompts
    repo_log = MockMetadataRepo(log_prompts=True)
    pii_filter_allowed = PIIFilter(repo_log)

    env_allowed = _make_envelope()
    allowed = await pii_filter_allowed.apply(env_allowed)
    assert allowed.payload.prompt_preview == "secret prompt"
