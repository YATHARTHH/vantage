"""Tamper-Evident Append-Only Audit Logging Service.

Implements deterministic SHA-256 hash chaining (with 'GENESIS' seed) and pure read-only integrity verification.
Protects audit logs against unauthorized modification or deletion.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from vantage.storage.sqlalchemy.models import AuditLogModel
from vantage.core.logging import get_logger

import asyncio

logger = get_logger(__name__)

# Global lock to serialize audit chain insertion across concurrent async calls
_audit_chain_lock = asyncio.Lock()


def compute_audit_hash(
    prev_hash: str,
    ts_str: str,
    actor_key_id: str,
    project_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details_json: str,
) -> str:
    """Computes SHA-256 hash for an audit record chain entry."""
    payload = f"{prev_hash}|{ts_str}|{actor_key_id}|{project_id}|{action}|{resource_type}|{resource_id}|{details_json}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditService:
    """Append-only audit service with cryptographic hash chaining."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def append_event(
        self,
        actor_key_id: str,
        action: str,
        resource_type: str,
        project_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> AuditLogModel:
        """
        Appends an immutable audit event to the hash chain atomically.
        """
        async with _audit_chain_lock:
            details_str = json.dumps(details, sort_keys=True) if details else ""
            
            # 1. Fetch previous record in the chain ordered deterministically by ID
            stmt = select(AuditLogModel).order_by(desc(AuditLogModel.id)).limit(1)
            res = await self._db.execute(stmt)
            latest_entry = res.scalar_one_or_none()

            prev_hash = latest_entry.record_hash if latest_entry else "GENESIS"
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            ts_str = now.strftime("%Y-%m-%dT%H:%M:%S.%f")

            # 2. Compute SHA-256 hash for current record
            rec_hash = compute_audit_hash(
                prev_hash=prev_hash,
                ts_str=ts_str,
                actor_key_id=actor_key_id,
                project_id=project_id or "",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id or "",
                details_json=details_str,
            )

            entry = AuditLogModel(
                timestamp=now,
                actor_key_id=actor_key_id,
                project_id=project_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details_json=details_str if details_str else None,
                previous_hash=prev_hash,
                record_hash=rec_hash,
            )

            self._db.add(entry)
            await self._db.commit()
            await self._db.refresh(entry)

            logger.info("audit_event_appended", action=action, actor=actor_key_id, hash=rec_hash[:10])
            return entry

    async def verify_integrity(self, project_id: Optional[str] = None) -> tuple[bool, list[str]]:
        """
        Pure read-only verification of the SHA-256 audit hash chain.
        Ordered deterministically by id ASC.
        Does NOT mutate or append rows during verification.
        """
        query = select(AuditLogModel)
        if project_id:
            query = query.where(AuditLogModel.project_id == project_id)
        query = query.order_by(AuditLogModel.id.asc())

        res = await self._db.execute(query)
        logs = list(res.scalars().all())

        if not logs:
            return True, []

        errors: list[str] = []
        expected_prev = "GENESIS"

        for i, log in enumerate(logs):
            # Check 1: Chain linkage (for global log series)
            if not project_id and log.previous_hash != expected_prev:
                errors.append(
                    f"Chain break at record ID {log.id}: previous_hash '{log.previous_hash[:8]}' != expected '{expected_prev[:8]}'"
                )

            # Check 2: Hash recalculation verification
            ts_str = log.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f") if isinstance(log.timestamp, datetime) else str(log.timestamp)
            recomputed = compute_audit_hash(
                prev_hash=log.previous_hash,
                ts_str=ts_str,
                actor_key_id=log.actor_key_id,
                project_id=log.project_id or "",
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id or "",
                details_json=log.details_json or "",
            )

            if recomputed != log.record_hash:
                errors.append(
                    f"Hash corruption at record ID {log.id} ({log.action}): computed '{recomputed[:8]}' != stored '{log.record_hash[:8]}'"
                )

            expected_prev = log.record_hash

        is_valid = len(errors) == 0
        return is_valid, errors
