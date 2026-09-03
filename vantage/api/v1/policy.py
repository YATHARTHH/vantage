"""Real-Time Policy Circuit Breaker Endpoints.

POST /api/v1/policy/authorize - Pre-flight authorization check with atomic resource reservation
POST /api/v1/policy/usage     - Post-flight usage recording & reservation reconciliation
GET  /api/v1/policy/rules     - Get per-project policy rules
POST /api/v1/policy/rules     - Set per-project policy rules
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from vantage.api.dependencies import get_db, verify_api_key
from vantage.policy.circuit_breaker import (
    circuit_breaker_engine,
    PolicyRules,
    PolicyCheckResult,
)
from vantage.storage.sqlalchemy.models import ProjectPolicyModel

router = APIRouter(prefix="/policy", tags=["Policy Circuit Breaker"])


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class AuthorizeRequest(BaseModel):
    trace_id: str
    project_id: str
    estimated_cost: Optional[float] = Field(None, ge=0.0)
    estimated_tokens: Optional[int] = Field(None, ge=0)
    model_name: Optional[str] = "gpt-4o"
    is_retry: bool = False


class UsageRecordRequest(BaseModel):
    trace_id: str
    project_id: str
    actual_cost: float = Field(0.0, ge=0.0)
    actual_tokens: int = Field(0, ge=0)
    authorization_id: Optional[str] = None
    is_error: bool = False


class SetPolicyRulesRequest(BaseModel):
    project_id: str
    max_cost_per_trace_usd: float = Field(0.50, gt=0.0)
    max_tokens_per_trace: int = Field(30000, gt=0)
    max_retry_loops: int = Field(3, ge=0)
    enabled: bool = True


# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------

async def _get_project_policy_rules(db: AsyncSession, project_id: str) -> PolicyRules:
    stmt = select(ProjectPolicyModel).where(ProjectPolicyModel.project_id == project_id)
    res = await db.execute(stmt)
    model = res.scalar_one_or_none()

    if model:
        return PolicyRules(
            project_id=model.project_id,
            max_cost_per_trace_usd=model.max_cost_per_trace_usd,
            max_tokens_per_trace=model.max_tokens_per_trace,
            max_retry_loops=model.max_retry_loops,
            enabled=model.enabled,
        )
    return PolicyRules(project_id=project_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/authorize", response_model=PolicyCheckResult, summary="Pre-flight circuit breaker authorization check")
async def authorize_execution(
    req: AuthorizeRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Pre-flight check. Atomically reserves resources if authorized, or returns TRIPPED status."""
    rules = await _get_project_policy_rules(db, req.project_id)
    result = await circuit_breaker_engine.authorize(
        trace_id=req.trace_id,
        project_id=req.project_id,
        rules=rules,
        estimated_cost=req.estimated_cost,
        estimated_tokens=req.estimated_tokens,
        model_name=req.model_name,
        is_retry=req.is_retry,
    )
    return result


@router.post("/usage", response_model=PolicyCheckResult, summary="Post-flight usage reconciliation")
async def record_execution_usage(
    req: UsageRecordRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Post-flight usage record. Reconciles atomic reservation using authorization_id."""
    result = await circuit_breaker_engine.record_usage(
        trace_id=req.trace_id,
        project_id=req.project_id,
        actual_cost=req.actual_cost,
        actual_tokens=req.actual_tokens,
        authorization_id=req.authorization_id,
        is_error=req.is_error,
    )
    return result


@router.get("/rules", response_model=PolicyRules, summary="Get policy rules for project")
async def get_policy_rules(
    project_id: str = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Returns project-level policy rules."""
    return await _get_project_policy_rules(db, project_id)


@router.post("/rules", response_model=PolicyRules, summary="Set policy rules for project")
async def set_policy_rules(
    req: SetPolicyRulesRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Creates or updates project-level policy configuration."""
    stmt = select(ProjectPolicyModel).where(ProjectPolicyModel.project_id == req.project_id)
    res = await db.execute(stmt)
    model = res.scalar_one_or_none()

    if not model:
        model = ProjectPolicyModel(project_id=req.project_id)
        db.add(model)

    model.max_cost_per_trace_usd = req.max_cost_per_trace_usd
    model.max_tokens_per_trace = req.max_tokens_per_trace
    model.max_retry_loops = req.max_retry_loops
    model.enabled = req.enabled

    await db.commit()
    await db.refresh(model)

    return PolicyRules(
        project_id=model.project_id,
        max_cost_per_trace_usd=model.max_cost_per_trace_usd,
        max_tokens_per_trace=model.max_tokens_per_trace,
        max_retry_loops=model.max_retry_loops,
        enabled=model.enabled,
    )
