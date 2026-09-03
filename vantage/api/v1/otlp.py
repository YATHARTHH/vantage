"""OTLP/HTTP Standard Ingestion Adapter.

POST /v1/traces - W3C OpenTelemetry OTLP/HTTP compliant receiver.
Supports gzip decompression, 10MB request limits, project authentication,
and deduplication based on (trace_id, span_id).
"""
from __future__ import annotations

import gzip
import json
from typing import Dict, Set
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from vantage.api.dependencies import get_db
from vantage.auth.rbac import AuthContext, RequirePermission
from vantage.ingest.normalizer import normalize_otlp_span, CanonicalVantageSpan

router = APIRouter(tags=["OTLP Telemetry Receiver"])

MAX_REQUEST_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_SPANS_PER_BATCH = 2500

# In-memory deduplication bloom filter / set for trace_id + span_id
DEDUP_CACHE: Set[str] = set()
MAX_DEDUP_CACHE_SIZE = 100000


def _is_duplicate(trace_id: str, span_id: str) -> bool:
    """Check if (trace_id, span_id) has already been processed."""
    key = f"{trace_id}:{span_id}"
    if key in DEDUP_CACHE:
        return True
    if len(DEDUP_CACHE) >= MAX_DEDUP_CACHE_SIZE:
        DEDUP_CACHE.clear()  # Evict cache on capacity
    DEDUP_CACHE.add(key)
    return False


@router.post("/v1/traces", summary="OTLP/HTTP Standard Trace Ingestion Endpoint")
@router.post("/api/v1/otlp/v1/traces", include_in_schema=False)
async def ingest_otlp_traces(
    request: Request,
    content_encoding: str = Header(None),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(RequirePermission("span.ingest")),
):
    """OpenTelemetry OTLP/HTTP standard trace ingestion endpoint."""
    # Check request body size limit prior to heavy decompression/parsing
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request size exceeds maximum limit of {MAX_REQUEST_SIZE_BYTES} bytes",
        )

    raw_body = await request.body()
    if len(raw_body) > MAX_REQUEST_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Decompressed request payload exceeds {MAX_REQUEST_SIZE_BYTES} bytes",
        )

    # Decompress gzip if header is specified
    if content_encoding == "gzip":
        try:
            raw_body = gzip.decompress(raw_body)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to decompress gzip payload: {str(e)}",
            )

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTLP JSON payload format: {str(e)}",
        )

    resource_spans = data.get("resourceSpans", [])
    if not isinstance(resource_spans, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'resourceSpans' must be an array",
        )

    project_id = auth.project_id or "default"
    canonical_spans = []

    for r_span in resource_spans:
        scope_spans = r_span.get("scopeSpans", r_span.get("instrumentationLibrarySpans", []))
        for s_span in scope_spans:
            spans = s_span.get("spans", [])
            for otel_span in spans:
                trace_id = otel_span.get("traceId", otel_span.get("trace_id", ""))
                span_id = otel_span.get("spanId", otel_span.get("span_id", ""))

                if _is_duplicate(trace_id, span_id):
                    continue  # Deduplicate on (trace_id, span_id)

                c_span = normalize_otlp_span(otel_span, project_id=project_id)
                canonical_spans.append(c_span)

                if len(canonical_spans) >= MAX_SPANS_PER_BATCH:
                    break

    # Return normalized count response
    return {
        "status": "partial_success" if len(canonical_spans) == MAX_SPANS_PER_BATCH else "success",
        "ingested_spans": len(canonical_spans),
        "project_id": project_id,
        "spans": [s.model_dump() for s in canonical_spans],
    }
