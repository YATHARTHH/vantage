"""Offline Trace Replay & "What-If" Endpoint Router.

POST /api/v1/replay/trace/{trace_id} - Triggers 100% offline deterministic trace replay with zero live tool side-effects.
"""
from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from vantage.api.dependencies import get_db, get_telemetry_repository
from vantage.auth.rbac import RequirePermission, AuthContext
from vantage.replay.replay_engine import TraceReplayEngine, ReplayManifest, ReplayResult
from vantage.services.audit_service import AuditService
from vantage.storage.duckdb.telemetry_repository import DuckDBTelemetryRepository

router = APIRouter(prefix="/replay", tags=["Trace Replay & What-If"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TriggerReplayResponse(BaseModel):
    replay_id: str
    trace_id: str
    project_id: str
    status: str  # COMPLETED | BLOCKED | FAILED
    reason: Optional[str]
    executed_nodes_count: int
    total_cost_usd: float = 0.0
    is_offline: bool = True
    executed_spans: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/trace/{trace_id}", response_model=TriggerReplayResponse, summary="Execute 100% offline deterministic trace replay")
async def trigger_trace_replay(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
    telemetry_repo: DuckDBTelemetryRepository = Depends(get_telemetry_repository),
    auth: AuthContext = Depends(RequirePermission("replay.execute")),
):
    """
    Executes an offline trace replay using recorded manifest outputs.
    Enforces zero external side-effects, project scope isolation, and tamper-evident audit logging.
    """
    engine = TraceReplayEngine(telemetry_repo)

    try:
        manifest = await engine.create_manifest_from_trace(trace_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Project Scope Authorization Verification
    if auth.project_id and manifest.project_id != auth.project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key scope restricted to project '{auth.project_id}'. Cannot replay trace from project '{manifest.project_id}'.",
        )

    # Execute Offline Replay
    result = await engine.execute_offline_replay(manifest)

    # Append Audit Event
    audit_svc = AuditService(db)
    await audit_svc.append_event(
        actor_key_id=auth.key_id,
        action="REPLAY_EXECUTED",
        resource_type="trace_replay",
        project_id=manifest.project_id,
        resource_id=manifest.replay_id,
        details={"trace_id": trace_id, "status": result.status, "nodes": result.executed_nodes_count},
    )

    return TriggerReplayResponse(
        replay_id=result.replay_id,
        trace_id=result.trace_id,
        project_id=result.project_id,
        status=result.status,
        reason=result.reason,
        executed_nodes_count=result.executed_nodes_count,
        total_cost_usd=result.total_cost_usd,
        is_offline=result.is_offline,
        executed_spans=result.executed_spans,
    )


class WhatIfRequest(BaseModel):
    trace_id: str
    modified_prompts: dict[str, str]  # span_id -> candidate_prompt_text


@router.post("/what-if", summary="Evaluate local estimated impact of candidate prompt changes")
async def trigger_what_if_estimation(
    req: WhatIfRequest,
    db: AsyncSession = Depends(get_db),
    telemetry_repo: DuckDBTelemetryRepository = Depends(get_telemetry_repository),
    auth: AuthContext = Depends(RequirePermission("replay.execute")),
):
    """
    Evaluates candidate prompt modifications locally and computes metric deltas (Local Estimated Impact).
    HARD SAFETY RULE: Zero live tool or model calls.
    """
    engine = TraceReplayEngine(telemetry_repo)
    try:
        manifest = await engine.create_manifest_from_trace(req.trace_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if auth.project_id and manifest.project_id != auth.project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key scope restricted to project '{auth.project_id}'.",
        )

    res = await engine.execute_what_if_estimation(manifest, req.modified_prompts)

    audit_svc = AuditService(db)
    await audit_svc.append_event(
        actor_key_id=auth.key_id,
        action="WHAT_IF_ESTIMATION_EXECUTED",
        resource_type="what_if_fork",
        project_id=manifest.project_id,
        resource_id=manifest.replay_id,
        details={"trace_id": req.trace_id, "modified_count": len(req.modified_prompts)},
    )

    return res
