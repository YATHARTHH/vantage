"""Local Similarity & Fuzzy Prompt Cache.

Architecture: 2-Tier fast-path
  Level 1: SHA-256 exact hash → O(1) lookup
  Level 2: TF-IDF cosine similarity ≥ 0.88 → fuzzy hit

Performance targets (NOT guarantees):
  Exact-match lookup: < 1 ms locally
  Fuzzy lookup:       < 5 ms for POC cache-size benchmark

Privacy: when project.log_prompts = false, prompt_text/response_text are not persisted.
"""
from __future__ import annotations

import hashlib
import math
from collections import Counter
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# TF-IDF helpers (no external dependency — pure Python)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    import re
    return re.findall(r"[a-z0-9]+", text.lower())


def _tf(tokens: list[str]) -> dict[str, float]:
    count = Counter(tokens)
    total = len(tokens) or 1
    return {t: c / total for t, c in count.items()}


def _cosine(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Cosine similarity between two TF dicts."""
    keys = set(vec_a) & set(vec_b)
    if not keys:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# Cache key builder
# ---------------------------------------------------------------------------

def build_exact_hash(
    project_id: str,
    model_name: str,
    prompt_template_version: str,
    context_fingerprint: str,
    prompt_text: str,
) -> str:
    """SHA-256 exact-match cache key.

    Includes prompt_template_version so that system-prompt changes
    invalidate stale cached responses automatically.
    """
    raw = "|".join([
        project_id,
        model_name,
        prompt_template_version,
        context_fingerprint,
        prompt_text.strip(),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# In-memory cache record (mirrors SQLAlchemy model; used for fuzzy search)
# ---------------------------------------------------------------------------

class _CacheEntry:
    __slots__ = (
        "cache_id", "exact_hash", "tf_vec",
        "response_text", "tokens_input", "tokens_output",
        "original_cost_usd", "expires_at",
    )

    def __init__(
        self,
        cache_id: str,
        exact_hash: str,
        prompt_text: str,
        response_text: str,
        tokens_input: int,
        tokens_output: int,
        original_cost_usd: float,
        expires_at: Optional[datetime],
    ) -> None:
        self.cache_id = cache_id
        self.exact_hash = exact_hash
        self.tf_vec = _tf(_tokenize(prompt_text))
        self.response_text = response_text
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.original_cost_usd = original_cost_usd
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Cache hit result
# ---------------------------------------------------------------------------

class CacheHit:
    def __init__(
        self,
        cache_id: str,
        response_text: str,
        hit_type: str,  # "exact" | "fuzzy"
        similarity: float,
        tokens_input: int,
        tokens_output: int,
        original_cost_usd: float,
    ) -> None:
        self.cache_id = cache_id
        self.response_text = response_text
        self.hit_type = hit_type
        self.similarity = similarity
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.original_cost_usd = original_cost_usd


# ---------------------------------------------------------------------------
# Main cache manager
# ---------------------------------------------------------------------------

FUZZY_SIMILARITY_THRESHOLD = 0.88


class LocalSimilarityCache:
    """2-Tier local similarity cache.

    This is backed by an in-memory index for fuzzy search and an
    async SQLAlchemy session for persistence (injected at runtime).
    """

    def __init__(self) -> None:
        # project_id → list[_CacheEntry]
        self._index: dict[str, list[_CacheEntry]] = {}
        # exact_hash → _CacheEntry
        self._hash_index: dict[str, _CacheEntry] = {}

    # ------------------------------------------------------------------
    # Load / populate in-memory index from DB records
    # ------------------------------------------------------------------

    def load_entry(
        self,
        cache_id: str,
        exact_hash: str,
        project_id: str,
        prompt_text: str,
        response_text: str,
        tokens_input: int,
        tokens_output: int,
        original_cost_usd: float,
        expires_at: Optional[datetime],
    ) -> None:
        """Called during startup or after set() to populate in-memory index."""
        entry = _CacheEntry(
            cache_id=cache_id,
            exact_hash=exact_hash,
            prompt_text=prompt_text,
            response_text=response_text,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            original_cost_usd=original_cost_usd,
            expires_at=expires_at,
        )
        self._hash_index[exact_hash] = entry
        self._index.setdefault(project_id, []).append(entry)

    # ------------------------------------------------------------------
    # Tier 1: exact hash lookup (O(1))
    # ------------------------------------------------------------------

    def _exact_lookup(self, exact_hash: str) -> Optional[CacheHit]:
        entry = self._hash_index.get(exact_hash)
        if entry and not entry.is_expired():
            return CacheHit(
                cache_id=entry.cache_id,
                response_text=entry.response_text,
                hit_type="exact",
                similarity=1.0,
                tokens_input=entry.tokens_input,
                tokens_output=entry.tokens_output,
                original_cost_usd=entry.original_cost_usd,
            )
        return None

    # ------------------------------------------------------------------
    # Tier 2: TF-IDF fuzzy lookup
    # ------------------------------------------------------------------

    def _fuzzy_lookup(self, project_id: str, prompt_text: str) -> Optional[CacheHit]:
        entries = self._index.get(project_id, [])
        if not entries:
            return None
        query_vec = _tf(_tokenize(prompt_text))
        best: Optional[tuple[float, _CacheEntry]] = None
        for entry in entries:
            if entry.is_expired():
                continue
            sim = _cosine(query_vec, entry.tf_vec)
            if sim >= FUZZY_SIMILARITY_THRESHOLD:
                if best is None or sim > best[0]:
                    best = (sim, entry)
        if best:
            sim, entry = best
            return CacheHit(
                cache_id=entry.cache_id,
                response_text=entry.response_text,
                hit_type="fuzzy",
                similarity=round(sim, 4),
                tokens_input=entry.tokens_input,
                tokens_output=entry.tokens_output,
                original_cost_usd=entry.original_cost_usd,
            )
        return None

    # ------------------------------------------------------------------
    # Public get — runs both tiers
    # ------------------------------------------------------------------

    def get(
        self,
        project_id: str,
        model_name: str,
        prompt_template_version: str,
        context_fingerprint: str,
        prompt_text: str,
    ) -> Optional[CacheHit]:
        """Try exact hash first, then fuzzy similarity. Returns None on miss."""
        exact_hash = build_exact_hash(
            project_id, model_name, prompt_template_version,
            context_fingerprint, prompt_text
        )
        # Tier 1
        hit = self._exact_lookup(exact_hash)
        if hit:
            return hit
        # Tier 2
        return self._fuzzy_lookup(project_id, prompt_text)
