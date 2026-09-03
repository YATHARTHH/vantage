"""API Key Management Endpoints.

POST /api/v1/api-keys           - Create new high-entropy API Key (returns plaintext once)
GET  /api/v1/api-keys           - List API Keys (hashes only, no secrets exposed)
DELETE /api/v1/api-keys/{key_id}- Soft revoke API Key
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vantage.api.dependencies import get_db
from vantage.auth.rbac import RequirePermission, AuthContext, hash_api_key
from vantage.services.audit_service import AuditService
from vantage.storage.sqlalchemy.models import ApiKeyModel

router = APIRouter(prefix="/api-keys", tags=["API Key Management"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateApiKeyRequest(BaseModel):
    display_name: str = Field(..., min_length=3, max_length=100)
    role: str = Field("developer", description="admin | developer | viewer")
    project_id: Optional[str] = Field(None, description="Optional project scope restriction")
    expires_in_days: Optional[int] = Field(365, ge=1, le=3650)


class CreateApiKeyResponse(BaseModel):
    key_id: str
    plaintext_key: str  # Shown ONCE at creation time
    display_name: str
    role: str
    project_id: Optional[str]
    created_at: str
    expires_at: Optional[str]
    notice: str = "Store this plaintext key securely. It will NEVER be shown again."


class ApiKeyListItem(BaseModel):
    key_id: str
    display_name: str
    role: str
    project_id: Optional[str]
    status: str
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=CreateApiKeyResponse, summary="Create new enterprise API Key")
async def create_api_key(
    req: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(RequirePermission("api_key.manage")),
):
    """Generates a high-entropy API key. Returns plaintext secret ONCE."""
    if req.role not in ("admin", "developer", "viewer"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: 'admin', 'developer', 'viewer'",
        )

    key_id = f"key_{uuid.uuid4().hex[:12]}"
    secret = secrets.token_urlsafe(32)
    plaintext = f"vg_live_{secret}"
    k_hash = hash_api_key(plaintext)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    exp = now + timedelta(days=req.expires_in_days) if req.expires_in_days else None

    key_model = ApiKeyModel(
        key_id=key_id,
        key_hash=k_hash,
        display_name=req.display_name,
        role=req.role,
        project_id=req.project_id,
        status="active",
        created_at=now,
        expires_at=exp,
    )

    db.add(key_model)
    await db.commit()

    # Append to tamper-evident audit log
    audit_svc = AuditService(db)
    await audit_svc.append_event(
        actor_key_id=auth.key_id,
        action="API_KEY_CREATED",
        resource_type="api_key",
        project_id=req.project_id,
        resource_id=key_id,
        details={"display_name": req.display_name, "role": req.role},
    )

    return CreateApiKeyResponse(
        key_id=key_id,
        plaintext_key=plaintext,
        display_name=req.display_name,
        role=req.role,
        project_id=req.project_id,
        created_at=now.isoformat(),
        expires_at=exp.isoformat() if exp else None,
    )


@router.get("", response_model=list[ApiKeyListItem], summary="List enterprise API Keys")
async def list_api_keys(
    project_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(RequirePermission("api_key.manage")),
):
    """Lists API keys for project or system. Exposes hashes only, no secrets."""
    stmt = select(ApiKeyModel)
    if project_id:
        stmt = stmt.where(ApiKeyModel.project_id == project_id)
    stmt = stmt.order_by(ApiKeyModel.created_at.desc())

    res = await db.execute(stmt)
    keys = res.scalars().all()

    return [
        ApiKeyListItem(
            key_id=k.key_id,
            display_name=k.display_name,
            role=k.role,
            project_id=k.project_id,
            status=k.status,
            created_at=k.created_at.isoformat(),
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        )
        for k in keys
    ]


@router.delete("/{key_id}", summary="Soft revoke enterprise API Key")
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(RequirePermission("api_key.manage")),
):
    """Soft revokes API key (status = 'revoked') to maintain compliance audit history."""
    stmt = select(ApiKeyModel).where(ApiKeyModel.key_id == key_id)
    res = await db.execute(stmt)
    key_model = res.scalar_one_or_none()

    if not key_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"API key '{key_id}' not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    key_model.status = "revoked"
    key_model.revoked_at = now
    await db.commit()

    # Append to tamper-evident audit log
    audit_svc = AuditService(db)
    await audit_svc.append_event(
        actor_key_id=auth.key_id,
        action="API_KEY_REVOKED",
        resource_type="api_key",
        project_id=key_model.project_id,
        resource_id=key_id,
        details={"display_name": key_model.display_name, "revoked_at": now.isoformat()},
    )

    return {"status": "revoked", "key_id": key_id, "revoked_at": now.isoformat()}
