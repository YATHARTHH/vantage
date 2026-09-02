"""Cache API endpoints.

POST /api/v1/cache/check  - 2-tier cache lookup (exact hash → TF-IDF fuzzy)
GET  /api/v1/cache/stats  - aggregate savings: tokens_saved, cost_saved_usd, hit_rate_pct
POST /api/v1/cache/store  - store a cache entry (called after a real LLM response)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from vantage.api.dependencies import get_db, verify_api_key
from vantage.cache.semantic_cache import LocalSimilarityCache, build_exact_hash
from vantage.storage.sqlalchemy.models import LocalCacheRecordModel

router = APIRouter(prefix="/cache", tags=["Cache"])

# Module-level cache singleton (populated at first use)
_cache = LocalSimilarityCache()
_cache_loaded: dict[str, bool] = {}  # project_id → loaded


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CacheCheckRequest(BaseModel):
    project_id: str
    model_name: str
    prompt_text: str
    prompt_template_version: str = "v1"
    context_fingerprint: str = ""


class CacheCheckResponse(BaseModel):
    hit: bool
    hit_type: Optional[str] = None   # "exact" | "fuzzy" | None
    similarity: Optional[float] = None
    response_text: Optional[str] = None
    cache_id: Optional[str] = None
    tokens_saved: Optional[int] = None
    cost_saved_usd: Optional[float] = None


class CacheStoreRequest(BaseModel):
    project_id: str
    model_name: str
    prompt_text: str
    response_text: str
    prompt_template_version: str = "v1"
    context_fingerprint: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    original_cost_usd: float = 0.0
    ttl_hours: Optional[int] = None   # None = no expiry
    log_prompts: bool = True          # from project settings


class CacheStoreResponse(BaseModel):
    cache_id: str
    exact_hash: str


class CacheStatsResponse(BaseModel):
    total_entries: int
    total_hits: int
    hit_rate_pct: float
    tokens_saved: int
    cost_saved_usd: float
    latency_note: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_project_cache(project_id: str, db: AsyncSession) -> None:
    """Load all active cache entries for this project into the in-memory index."""
    if _cache_loaded.get(project_id):
        return
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(LocalCacheRecordModel).where(
            LocalCacheRecordModel.project_id == project_id,
        )
    )
    rows = result.scalars().all()
    for row in rows:
        if row.expires_at and row.expires_at.replace(tzinfo=timezone.utc) < now:
            continue
        _cache.load_entry(
            cache_id=row.cache_id,
            exact_hash=row.exact_hash,
            project_id=row.project_id,
            prompt_text=row.prompt_text or "",
            response_text=row.response_text or "",
            tokens_input=row.tokens_input,
            tokens_output=row.tokens_output,
            original_cost_usd=row.original_cost_usd,
            expires_at=row.expires_at,
        )
    _cache_loaded[project_id] = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/check", response_model=CacheCheckResponse)
async def check_cache(
    body: CacheCheckRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> CacheCheckResponse:
    """2-tier cache lookup. Returns MISS if no entry found."""
    await _load_project_cache(body.project_id, db)

    hit = _cache.get(
        project_id=body.project_id,
        model_name=body.model_name,
        prompt_template_version=body.prompt_template_version,
        context_fingerprint=body.context_fingerprint,
        prompt_text=body.prompt_text,
    )

    if not hit:
        return CacheCheckResponse(hit=False)

    # Increment hit_count in DB
    result = await db.execute(
        select(LocalCacheRecordModel).where(
            LocalCacheRecordModel.cache_id == hit.cache_id
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.hit_count += 1
        row.last_hit_at = datetime.utcnow()
        await db.commit()

    return CacheCheckResponse(
        hit=True,
        hit_type=hit.hit_type,
        similarity=hit.similarity,
        response_text=hit.response_text,
        cache_id=hit.cache_id,
        tokens_saved=hit.tokens_input + hit.tokens_output,
        cost_saved_usd=hit.original_cost_usd,
    )


@router.post("/store", response_model=CacheStoreResponse, status_code=status.HTTP_201_CREATED)
async def store_cache(
    body: CacheStoreRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> CacheStoreResponse:
    """Store a new cache entry. Respects log_prompts privacy policy."""
    exact_hash = build_exact_hash(
        project_id=body.project_id,
        model_name=body.model_name,
        prompt_template_version=body.prompt_template_version,
        context_fingerprint=body.context_fingerprint,
        prompt_text=body.prompt_text,
    )

    # Privacy: only store text if project allows prompt logging
    stored_prompt = body.prompt_text if body.log_prompts else None
    stored_response = body.response_text if body.log_prompts else None

    expires_at: Optional[datetime] = None
    if body.ttl_hours:
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(hours=body.ttl_hours)

    cache_id = str(uuid.uuid4())
    record = LocalCacheRecordModel(
        cache_id=cache_id,
        project_id=body.project_id,
        model_name=body.model_name,
        exact_hash=exact_hash,
        prompt_template_version=body.prompt_template_version,
        context_fingerprint=body.context_fingerprint,
        prompt_text=stored_prompt,
        response_text=stored_response,
        tokens_input=body.tokens_input,
        tokens_output=body.tokens_output,
        original_cost_usd=body.original_cost_usd,
        hit_count=0,
        expires_at=expires_at,
    )
    db.add(record)
    await db.commit()

    # Populate in-memory index immediately
    _cache.load_entry(
        cache_id=cache_id,
        exact_hash=exact_hash,
        project_id=body.project_id,
        prompt_text=body.prompt_text,  # always use full text for fuzzy index
        response_text=body.response_text,
        tokens_input=body.tokens_input,
        tokens_output=body.tokens_output,
        original_cost_usd=body.original_cost_usd,
        expires_at=expires_at,
    )

    return CacheStoreResponse(cache_id=cache_id, exact_hash=exact_hash)


@router.get("/stats", response_model=CacheStatsResponse)
async def cache_stats(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> CacheStatsResponse:
    """Aggregate cache savings across all projects."""
    total_q = await db.execute(select(func.count()).select_from(LocalCacheRecordModel))
    total_entries = total_q.scalar() or 0

    hits_q = await db.execute(select(func.sum(LocalCacheRecordModel.hit_count)))
    total_hits = int(hits_q.scalar() or 0)

    hit_rate = (total_hits / max(total_hits + total_entries, 1)) * 100

    tokens_q = await db.execute(
        select(
            func.sum(
                (LocalCacheRecordModel.tokens_input + LocalCacheRecordModel.tokens_output)
                * LocalCacheRecordModel.hit_count
            )
        )
    )
    tokens_saved = int(tokens_q.scalar() or 0)

    cost_q = await db.execute(
        select(
            func.sum(
                LocalCacheRecordModel.original_cost_usd * LocalCacheRecordModel.hit_count
            )
        )
    )
    cost_saved = float(cost_q.scalar() or 0.0)

    return CacheStatsResponse(
        total_entries=total_entries,
        total_hits=total_hits,
        hit_rate_pct=round(hit_rate, 2),
        tokens_saved=tokens_saved,
        cost_saved_usd=round(cost_saved, 6),
        latency_note="Exact-match target <1ms; fuzzy-match target <5ms at POC scale.",
    )
