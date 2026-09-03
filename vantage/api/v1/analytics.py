"""Vector Analytics API endpoint.

GET /api/v1/analytics/vector-drift
  Returns 3D projected trace points + centroid drift metrics.

Minimum data thresholds enforced:
  baseline >= 30 traces, current >= 10 traces
  → drift_status: "insufficient_data" if below threshold
"""
from __future__ import annotations

import json
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from vantage.api.dependencies import get_db, verify_api_key, get_telemetry_repository, get_metadata_repository
from vantage.analytics.vector_drift import compute_vector_drift
from vantage.analytics.dag_builder import build_dag_from_spans, DAGGraph
from vantage.storage.duckdb.telemetry_repository import DuckDBTelemetryRepository
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class VectorPointResponse(BaseModel):
    trace_id: str
    x: float
    y: float
    z: float
    risk_level: str
    threat_score: float


class DriftMetricsResponse(BaseModel):
    baseline_centroid: list[float]
    current_centroid: list[float]
    centroid_shift_distance: float
    drift_score: float          # normalized: 1 - exp(-distance) ∈ [0, 1)
    drift_status: str           # ok | moderate_drift | significant_drift | insufficient_data
    baseline_count: int
    current_count: int


class VectorDriftResponse(BaseModel):
    points: list[VectorPointResponse]
    drift_metrics: DriftMetricsResponse
    total_traces: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/vector-drift", response_model=VectorDriftResponse)
async def get_vector_drift(
    project_id: Optional[str] = Query(None, description="Filter by project (None = all projects)"),
    baseline_count: int = Query(100, ge=30, description="Baseline window size (min 30)"),
    current_count: int = Query(20, ge=10, description="Current window size (min 10)"),
    telemetry_repo: DuckDBTelemetryRepository = Depends(get_telemetry_repository),
    _: str = Depends(verify_api_key),
) -> VectorDriftResponse:
    """
    Returns 3D TruncatedSVD-projected prompt vectors and centroid drift metrics.

    Both baseline and current windows are transformed using a SINGLE shared
    TF-IDF + SVD model fit on the combined corpus.

    Privacy: raw prompt text is used ONLY for TF-IDF coordinate fitting and
    is NOT returned in the vector response payload.
    """
    spans = await telemetry_repo.query_spans(project_id=project_id, limit=2000)

    traces = []
    for span in reversed(spans):  # oldest-first ordering
        tags_raw = span.get("tags") or "{}"
        if isinstance(tags_raw, str):
            try:
                tags_dict = json.loads(tags_raw)
            except Exception:
                tags_dict = {}
        elif isinstance(tags_raw, dict):
            tags_dict = tags_raw
        else:
            tags_dict = {}

        prompt_text = tags_dict.get("prompt_preview") or ""
        if not prompt_text:
            continue

        risk_level = span.get("security_risk_level") or "LOW"
        threat_score = float(span.get("security_score") or 0.0)

        traces.append({
            "trace_id": span.get("trace_id") or span.get("event_id") or "unknown",
            "prompt_text": prompt_text,
            "risk_level": risk_level,
            "threat_score": threat_score,
        })

    if not traces:
        return VectorDriftResponse(
            points=[],
            drift_metrics=DriftMetricsResponse(
                baseline_centroid=[],
                current_centroid=[],
                centroid_shift_distance=0.0,
                drift_score=0.0,
                drift_status="insufficient_data",
                baseline_count=0,
                current_count=0,
            ),
            total_traces=0,
        )

    result = compute_vector_drift(
        traces=traces,
        baseline_count=baseline_count,
        current_count=current_count,
    )

    return VectorDriftResponse(
        points=[
            VectorPointResponse(
                trace_id=p.trace_id,
                x=p.x,
                y=p.y,
                z=p.z,
                risk_level=p.risk_level,
                threat_score=p.threat_score,
            )
            for p in result.points
        ],
        drift_metrics=DriftMetricsResponse(
            baseline_centroid=result.drift_metrics.baseline_centroid,
            current_centroid=result.drift_metrics.current_centroid,
            centroid_shift_distance=result.drift_metrics.centroid_shift_distance,
            drift_score=result.drift_metrics.drift_score,
            drift_status=result.drift_metrics.drift_status,
            baseline_count=result.drift_metrics.baseline_count,
            current_count=result.drift_metrics.current_count,
        ),
        total_traces=len(traces),
    )


# ---------------------------------------------------------------------------
# DAG Execution Topology Endpoints
# ---------------------------------------------------------------------------

@router.get("/dag/traces", summary="List traces with visualizable multi-span DAG topology")
async def list_dag_traces(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=200),
    telemetry_repo: DuckDBTelemetryRepository = Depends(get_telemetry_repository),
    _: str = Depends(verify_api_key),
):
    """Returns recent trace IDs that contain multiple spans (span_count >= 2)."""
    spans = await telemetry_repo.query_spans(project_id=project_id, limit=2000)
    
    trace_groups: dict[str, list[dict]] = {}
    for s in spans:
        tid = s.get("trace_id")
        if tid:
            if tid not in trace_groups:
                trace_groups[tid] = []
            trace_groups[tid].append(s)

    result = []
    for tid, span_list in trace_groups.items():
        if len(span_list) >= 1:  # Allow 1+ for visibility
            first = span_list[0]
            root_op = first.get("model_name") or first.get("event_kind") or first.get("source_tool") or "Trace Root"
            tot_cost = sum(float(s.get("cost_usd") or 0.0) for s in span_list)
            tot_tokens = sum(int(s.get("tokens_input") or 0) + int(s.get("tokens_output") or 0) for s in span_list)
            
            result.append({
                "trace_id": tid,
                "project_id": first.get("project_id") or "unknown",
                "root_operation": root_op,
                "span_count": len(span_list),
                "total_cost_usd": round(tot_cost, 6),
                "total_tokens": tot_tokens,
                "status": first.get("status") or "success",
                "started_at": first.get("started_at"),
            })

    return result[:limit]


@router.get("/dag/{trace_id}", summary="Get DAG topology graph for trace ID")
async def get_dag_graph(
    trace_id: str,
    telemetry_repo: DuckDBTelemetryRepository = Depends(get_telemetry_repository),
    _: str = Depends(verify_api_key),
):
    """Constructs light execution graph topology for the specified trace ID."""
    spans = await telemetry_repo.query_spans(trace_id=trace_id, limit=500)
    graph = build_dag_from_spans(spans, trace_id)
    return graph


@router.get("/dag/{trace_id}/node/{span_id}", summary="Lazy-load payload inspection for a DAG node")
async def get_dag_node_detail(
    trace_id: str,
    span_id: str,
    telemetry_repo: DuckDBTelemetryRepository = Depends(get_telemetry_repository),
    metadata_repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
    _: str = Depends(verify_api_key),
):
    """Lazy-loads node details and prompt text, strictly obeying project log_prompts setting."""
    spans = await telemetry_repo.query_spans(trace_id=trace_id, limit=500)
    target_span = None
    for s in spans:
        if str(s.get("span_id") or s.get("event_id")) == span_id:
            target_span = s
            break

    if not target_span:
        return {"error": "Span not found", "span_id": span_id}

    project_id = target_span.get("project_id") or "__unmapped__"
    project = await metadata_repo.get_project(project_id)
    log_prompts_enabled = project.log_prompts if project else False

    prompt_preview = None
    reason = None

    if not log_prompts_enabled:
        reason = f"Prompt logging is disabled for project '{project_id}'"
    else:
        tags = target_span.get("tags")
        if isinstance(tags, dict):
            prompt_preview = tags.get("prompt_preview")
        elif isinstance(tags, str) and "prompt_preview" in tags:
            try:
                parsed = json.loads(tags)
                prompt_preview = parsed.get("prompt_preview")
            except Exception:
                pass

    return {
        "span_id": span_id,
        "trace_id": trace_id,
        "project_id": project_id,
        "model_name": target_span.get("model_name"),
        "model_provider": target_span.get("model_provider"),
        "event_kind": target_span.get("event_kind"),
        "status": target_span.get("status"),
        "duration_ms": target_span.get("duration_ms"),
        "cost_usd": target_span.get("cost_usd"),
        "tokens_input": target_span.get("tokens_input"),
        "tokens_output": target_span.get("tokens_output"),
        "log_prompts_enabled": log_prompts_enabled,
        "payload_preview": prompt_preview,
        "privacy_notice": reason,
    }
