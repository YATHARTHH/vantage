"""Enterprise Role-Based Access Control (RBAC) & Scope Authorization Engine.

Supports permission-based authorization, Bearer token header authentication,
SHA-256 API key hash lookups, project scope isolation, and development-key safeguards.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Set

from fastapi import Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vantage.api.dependencies import get_db
from vantage.storage.sqlalchemy.models import ApiKeyModel

# ---------------------------------------------------------------------------
# Role Permission Maps
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, Set[str]] = {
    "viewer": {
        "telemetry.read",
        "dag.read",
        "metrics.read",
        "projects.read",
    },
    "developer": {
        "telemetry.read",
        "dag.read",
        "metrics.read",
        "projects.read",
        "replay.execute",
        "cache.read",
        "cache.write",
        "policy.check",
        "ingest.write",
    },
    "admin": {
        "telemetry.read",
        "dag.read",
        "metrics.read",
        "projects.read",
        "replay.execute",
        "cache.read",
        "cache.write",
        "policy.check",
        "ingest.write",
        "policy.write",
        "api_key.manage",
        "audit.read",
        "alerts.resolve",
        "dpo.export",
    },
}


def hash_api_key(key: str) -> str:
    """Generates SHA-256 hash of plaintext API key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass
class AuthContext:
    """Authenticated actor identity and authorization scope."""
    key_id: str
    display_name: str
    role: str
    project_id: Optional[str] = None


class RequirePermission:
    """FastAPI dependency enforcing permission level and project scope isolation."""

    def __init__(self, permission: str, project_scope: bool = True) -> None:
        self.permission = permission
        self.project_scope = project_scope

    async def __call__(
        self,
        request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization"),
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
        project_id: Optional[str] = Query(None),
        db: AsyncSession = Depends(get_db),
    ) -> AuthContext:
        # Extract raw API key from Authorization Bearer or X-API-Key header
        raw_key = None
        if authorization and authorization.startswith("Bearer "):
            raw_key = authorization.split("Bearer ", 1)[1].strip()
        elif x_api_key:
            raw_key = x_api_key.strip()

        if not raw_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key credentials in Authorization Bearer or X-API-Key header",
            )

        # Development Fallback Key Gate
        if raw_key == "dev-local-key":
            allow_dev = os.getenv("ALLOW_DEV_LOCAL_KEY", "true").lower() == "true"
            if not allow_dev:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Development local key disabled in production environment",
                )
            return AuthContext(
                key_id="dev-local-key",
                display_name="Dev Local Key",
                role="admin",
                project_id=None,
            )

        # Standard Hashed Key Verification
        k_hash = hash_api_key(raw_key)
        stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == k_hash)
        res = await db.execute(stmt)
        key_model = res.scalar_one_or_none()

        if not key_model or key_model.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, missing, or revoked API key",
            )

        # Check Expiry
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if key_model.expires_at and key_model.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
            )

        # Permission Hierarchy Verification
        role = key_model.role
        allowed_perms = ROLE_PERMISSIONS.get(role, set())
        if self.permission not in allowed_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' lacks required permission '{self.permission}'",
            )

        # Project Scope Verification
        if self.project_scope and key_model.project_id:
            if project_id and project_id != key_model.project_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key restricted to project scope '{key_model.project_id}'",
                )

        # Update last used timestamp
        key_model.last_used_at = now
        await db.commit()

        return AuthContext(
            key_id=key_model.key_id,
            display_name=key_model.display_name,
            role=key_model.role,
            project_id=key_model.project_id,
        )
