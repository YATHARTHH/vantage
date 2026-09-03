"""Compliance Audit Query Endpoint.

GET /api/v1/audit/logs - Admin-only query for tamper-evident audit logs with hash chain integrity check
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vantage.api.dependencies import get_db
from vantage.auth.rbac import RequirePermission, AuthContext
from vantage.services.audit_service import AuditService
from vantage.storage.sqlalchemy.models import AuditLogModel

router = APIRouter(prefix="/audit", tags=["Compliance Audit"])


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class AuditLogItem(BaseModel):
    id: int
    timestamp: str
    actor_key_id: str
    project_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details_json: Optional[str]
    previous_hash: str
    record_hash: str


class AuditLogQueryResponse(BaseModel):
    total_logs: int
    chain_valid: bool
    chain_errors: list[str]
    logs: list[AuditLogItem]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/logs", response_model=AuditLogQueryResponse, summary="Query tamper-evident compliance audit log")
async def get_audit_logs(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(RequirePermission("audit.read")),
):
    """
    Returns audit records for compliance auditing and performs a pure read-only SHA-256 hash chain verification.
    """
    audit_svc = AuditService(db)
    is_valid, errors = await audit_svc.verify_integrity(project_id=project_id)

    stmt = select(AuditLogModel)
    if project_id:
        stmt = stmt.where(AuditLogModel.project_id == project_id)
    stmt = stmt.order_by(AuditLogModel.timestamp.desc(), AuditLogModel.id.desc()).limit(limit)

    res = await db.execute(stmt)
    logs = list(res.scalars().all())

    items = [
        AuditLogItem(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            actor_key_id=log.actor_key_id,
            project_id=log.project_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details_json=log.details_json,
            previous_hash=log.previous_hash,
            record_hash=log.record_hash,
        )
        for log in logs
    ]

    return AuditLogQueryResponse(
        total_logs=len(items),
        chain_valid=is_valid,
        chain_errors=errors,
        logs=items,
    )
