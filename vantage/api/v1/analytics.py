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

from vantage.api.dependencies import get_db, verify_api_key, get_telemetry_repository
from vantage.analytics.vector_drift import compute_vector_drift
from vantage.storage.duckdb.telemetry_repository import DuckDBTelemetryRepository
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
