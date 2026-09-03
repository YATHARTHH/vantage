from fastapi import APIRouter, Depends
from vantage.api.dependencies import get_telemetry_repository
from vantage.services.query_service import QueryService
from vantage.storage.duckdb.telemetry_repository import DuckDBTelemetryRepository

router = APIRouter(prefix="/query", tags=["Query & Grafana"])


def get_query_service(
    repo: DuckDBTelemetryRepository = Depends(get_telemetry_repository),
) -> QueryService:
    return QueryService(repo)


@router.get("/metrics", summary="Query aggregated metrics for Grafana panels")
async def query_metrics(
    project_id: str | None = None,
    hours: int = 24,
    group_by: str | None = None,
    query_svc: QueryService = Depends(get_query_service),
):
    groups = group_by.split(",") if group_by else None
    return await query_svc.get_metrics(project_id=project_id, hours=hours, group_by=groups)


@router.get("/traces", summary="Query telemetry spans and trace list")
async def query_traces(
    project_id: str | None = None,
    trace_id: str | None = None,
    limit: int = 100,
    query_svc: QueryService = Depends(get_query_service),
):
    return await query_svc.get_spans(project_id=project_id, trace_id=trace_id, limit=limit)


@router.get("/spans/{trace_id}", summary="Get full span execution tree for trace ID")
async def query_trace_tree(
    trace_id: str,
    query_svc: QueryService = Depends(get_query_service),
):
    return await query_svc.get_spans(trace_id=trace_id, limit=500)


@router.get("/agent-cost", summary="Query aggregated agent run cost from child LLM spans")
async def query_agent_cost(
    project_id: str | None = None,
    hours: int = 24,
    query_svc: QueryService = Depends(get_query_service),
):
    return await query_svc.get_agent_runs_aggregated(project_id=project_id, hours=hours)
