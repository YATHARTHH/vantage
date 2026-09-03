"""Unit tests for Real-Time Circuit Breaker Policy Engine."""
import asyncio
import pytest
from vantage.policy.circuit_breaker import (
    CircuitBreakerEngine,
    PolicyRules,
)


@pytest.mark.asyncio
async def test_sequential_cost_accumulation_and_tripping():
    engine = CircuitBreakerEngine()
    rules = PolicyRules(project_id="test-proj", max_cost_per_trace_usd=0.50)
    trace_id = "seq-trace-001"

    # Step 1: Authorize $0.20 -> Allowed
    res1 = await engine.authorize(trace_id, "test-proj", rules, estimated_cost=0.20)
    assert res1.allowed is True
    assert res1.status == "ACTIVE"
    assert res1.authorization_id is not None

    # Record actual $0.20
    await engine.record_usage(trace_id, "test-proj", actual_cost=0.20, actual_tokens=100, authorization_id=res1.authorization_id)

    # Step 2: Authorize $0.25 -> Allowed (Cumulative: $0.45 <= $0.50)
    res2 = await engine.authorize(trace_id, "test-proj", rules, estimated_cost=0.25)
    assert res2.allowed is True
    assert res2.status == "ACTIVE"
    assert res2.authorization_id is not None

    # Record actual $0.25
    await engine.record_usage(trace_id, "test-proj", actual_cost=0.25, actual_tokens=150, authorization_id=res2.authorization_id)

    # Step 3: Authorize $0.10 -> Breaker TRIPPED ($0.45 + $0.10 = $0.55 > $0.50)
    res3 = await engine.authorize(trace_id, "test-proj", rules, estimated_cost=0.10)
    assert res3.allowed is False
    assert res3.status == "TRIPPED"
    assert res3.tripped_rule == "max_cost_per_trace_usd"


@pytest.mark.asyncio
async def test_parallel_atomic_reservation_concurrency():
    engine = CircuitBreakerEngine()
    rules = PolicyRules(project_id="test-proj", max_cost_per_trace_usd=0.50)
    trace_id = "parallel-trace-002"

    # Pre-fill actual cost to $0.45
    await engine.record_usage(trace_id, "test-proj", actual_cost=0.45, actual_tokens=200)

    # Two concurrent calls estimating $0.04 each (Budget left: $0.05)
    # Call A ($0.04) + Call B ($0.04) = $0.53 > $0.50
    # Only ONE call must be authorized; the second MUST be blocked by atomic reservation!
    task_a = engine.authorize(trace_id, "test-proj", rules, estimated_cost=0.04)
    task_b = engine.authorize(trace_id, "test-proj", rules, estimated_cost=0.04)

    res_a, res_b = await asyncio.gather(task_a, task_b)

    allowed_count = sum(1 for r in (res_a, res_b) if r.allowed)
    blocked_count = sum(1 for r in (res_a, res_b) if not r.allowed)

    assert allowed_count == 1
    assert blocked_count == 1


@pytest.mark.asyncio
async def test_retry_loop_limit_enforcement():
    engine = CircuitBreakerEngine()
    rules = PolicyRules(project_id="test-proj", max_retry_loops=2)
    trace_id = "retry-trace-003"

    # Attempt 1 (normal) -> Allowed
    r1 = await engine.authorize(trace_id, "test-proj", rules, is_retry=False)
    assert r1.allowed is True

    # Attempt 2 (Retry #1) -> Allowed
    r2 = await engine.authorize(trace_id, "test-proj", rules, is_retry=True)
    assert r2.allowed is True

    # Attempt 3 (Retry #2) -> Allowed
    r3 = await engine.authorize(trace_id, "test-proj", rules, is_retry=True)
    assert r3.allowed is True

    # Attempt 4 (Retry #3) -> Exceeds max_retry_loops=2 -> TRIPPED
    r4 = await engine.authorize(trace_id, "test-proj", rules, is_retry=True)
    assert r4.allowed is False
    assert r4.status == "TRIPPED"
    assert r4.tripped_rule == "max_retry_loops"
