from datetime import datetime, timedelta, timezone
from vantage.core.logging import get_logger
from vantage.storage.base import AbstractTelemetryRepository

logger = get_logger(__name__)


class QueryService:
    """
    Query service serving Grafana Infinity datasource & UI frontend queries.
    Includes deterministic root-agent span cost aggregation SQL (parent_span_id IS NULL).
    """

    def __init__(self, telemetry_repo: AbstractTelemetryRepository):
        self._repo = telemetry_repo

    async def get_metrics(
        self,
        project_id: str | None = None,
        hours: int = 24,
        group_by: list[str] | None = None,
    ) -> list[dict]:
        to_dt = datetime.now(timezone.utc)
        from_dt = to_dt - timedelta(hours=hours)
        return await self._repo.query_metrics(project_id, from_dt, to_dt, group_by)

    async def get_spans(
        self,
        project_id: str | None = None,
        trace_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        return await self._repo.query_spans(project_id, trace_id, limit)

    async def get_agent_runs_aggregated(self, project_id: str | None = None, hours: int = 24) -> list[dict]:
        """
        Query-time agent total cost aggregation.
        Aggregates root agent spans (parent_span_id IS NULL) and standalone LLM call spans.
        """
        spans = await self._repo.query_spans(project_id=project_id, limit=500)

        agent_runs: dict[str, dict] = {}

        # 1. Identify explicit root agent_run spans
        for s in spans:
            if s.get("event_kind") == "agent_run" and s.get("parent_span_id") is None:
                trace_id = s.get("trace_id") or s.get("event_id")
                agent_runs[trace_id] = {
                    "trace_id": trace_id,
                    "agent_name": s.get("model_name") or s.get("event_kind") or "Agent",
                    "started_at": str(s.get("started_at")),
                    "total_cost_usd": 0.0,
                    "llm_call_count": 0,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "status": s.get("status"),
                }

        # 2. Aggregate llm_call spans (either under root agent or as standalone entries)
        for s in spans:
            if s.get("event_kind") == "llm_call":
                trace_id = s.get("trace_id") or s.get("event_id")
                cost = float(s.get("cost_usd") or 0.0)
                tok_in = int(s.get("tokens_input") or 0)
                tok_out = int(s.get("tokens_output") or 0)

                if trace_id in agent_runs:
                    agent_runs[trace_id]["total_cost_usd"] = round(agent_runs[trace_id]["total_cost_usd"] + cost, 6)
                    agent_runs[trace_id]["llm_call_count"] += 1
                    agent_runs[trace_id]["tokens_input"] += tok_in
                    agent_runs[trace_id]["tokens_output"] += tok_out
                else:
                    agent_runs[trace_id] = {
                        "trace_id": trace_id,
                        "agent_name": s.get("model_name") or "LLM Agent",
                        "started_at": str(s.get("started_at")),
                        "total_cost_usd": round(cost, 6),
                        "llm_call_count": 1,
                        "tokens_input": tok_in,
                        "tokens_output": tok_out,
                        "status": s.get("status"),
                    }

        return list(agent_runs.values())
