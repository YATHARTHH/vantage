"""Unit tests for Bounded Ingestion Queue, Backpressure and DLQ."""
import pytest
import asyncio
from vantage.ingest.buffer import BoundedIngestionBuffer, BufferCapacityExceeded
from vantage.ingest.normalizer import CanonicalVantageSpan


@pytest.mark.asyncio
async def test_bounded_buffer_capacity_backpressure():
    buf = BoundedIngestionBuffer(capacity=2)
    s1 = CanonicalVantageSpan(span_id="s1", trace_id="t1", name="n1", start_time="2026-09-03T00:00:00Z", end_time="2026-09-03T00:00:01Z")
    s2 = CanonicalVantageSpan(span_id="s2", trace_id="t2", name="n2", start_time="2026-09-03T00:00:00Z", end_time="2026-09-03T00:00:01Z")
    s3 = CanonicalVantageSpan(span_id="s3", trace_id="t3", name="n3", start_time="2026-09-03T00:00:00Z", end_time="2026-09-03T00:00:01Z")

    await buf.enqueue_span(s1)
    await buf.enqueue_span(s2)

    with pytest.raises(BufferCapacityExceeded):
        await buf.enqueue_span(s3)


@pytest.mark.asyncio
async def test_buffer_flush():
    buf = BoundedIngestionBuffer(capacity=10)
    s1 = CanonicalVantageSpan(span_id="s1", trace_id="t1", name="n1", start_time="2026-09-03T00:00:00Z", end_time="2026-09-03T00:00:01Z")
    await buf.enqueue_span(s1)
    assert buf.size() == 1
    await buf.flush_batch()
    assert buf.size() == 0
