"""Real-Time Token & Cost Circuit Breaker Policy Engine.

Enforces pre-flight authorization and post-flight usage reconciliation.
Features:
 - Atomic reservation with asyncio.Lock for parallel tool branches
 - authorization_id UUID tracking for precise reservation reconciliation
 - Model token pricing cost calculation fallback via CostEnricher
 - Strict 0-indexed retry loop semantics (max_retry_loops)
 - Isolated in-memory runtime TraceState management
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

from vantage.enrichment.cost_enricher import CostEnricher


@dataclass
class PolicyRules:
    """Project-level policy limits."""
    project_id: str
    max_cost_per_trace_usd: float = 0.50
    max_tokens_per_trace: int = 30000
    max_retry_loops: int = 3
    enabled: bool = True


@dataclass
class TraceReservation:
    """Active in-flight resource reservation for a pre-authorized call."""
    authorization_id: str
    trace_id: str
    reserved_cost_usd: float
    reserved_tokens: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TraceState:
    """Runtime execution state for an active trace."""
    trace_id: str
    project_id: str
    actual_cost_usd: float = 0.0
    actual_tokens: int = 0
    retry_count: int = 0
    status: Literal["ACTIVE", "TRIPPED"] = "ACTIVE"
    tripped_rule: Optional[str] = None
    tripped_reason: Optional[str] = None
    reservations: dict[str, TraceReservation] = field(default_factory=dict)

    @property
    def reserved_cost_usd(self) -> float:
        return sum(r.reserved_cost_usd for r in self.reservations.values())

    @property
    def reserved_tokens(self) -> int:
        return sum(r.reserved_tokens for r in self.reservations.values())


@dataclass
class PolicyCheckResult:
    """Structured decision payload returned by circuit breaker checks."""
    allowed: bool
    authorization_id: Optional[str]
    status: Literal["ACTIVE", "TRIPPED"]
    tripped_rule: Optional[str]
    current_cost_usd: float
    limit_cost_usd: float
    current_tokens: int
    limit_tokens: int
    current_retry_count: int
    limit_retry_count: int
    reason: Optional[str] = None


class CircuitBreakerEngine:
    """In-memory thread-safe circuit breaker policy engine."""

    def __init__(self) -> None:
        self._states: dict[str, TraceState] = {}
        self._lock = asyncio.Lock()
        self._cost_enricher = CostEnricher()

    def get_state(self, trace_id: str) -> Optional[TraceState]:
        return self._states.get(trace_id)

    def reset_trace(self, trace_id: str) -> None:
        """Clears only in-memory runtime trace state (telemetry database untouched)."""
        self._states.pop(trace_id, None)

    async def authorize(
        self,
        trace_id: str,
        project_id: str,
        rules: PolicyRules,
        estimated_cost: Optional[float] = None,
        estimated_tokens: Optional[int] = None,
        model_name: Optional[str] = None,
        is_retry: bool = False,
    ) -> PolicyCheckResult:
        """
        Pre-flight check with atomic reservation.
        Derives cost estimate from model token pricing if estimated_cost is unprovided.
        """
        async with self._lock:
            if not rules.enabled:
                auth_id = str(uuid.uuid4())
                return PolicyCheckResult(
                    allowed=True,
                    authorization_id=auth_id,
                    status="ACTIVE",
                    tripped_rule=None,
                    current_cost_usd=0.0,
                    limit_cost_usd=rules.max_cost_per_trace_usd,
                    current_tokens=0,
                    limit_tokens=rules.max_tokens_per_trace,
                    current_retry_count=0,
                    limit_retry_count=rules.max_retry_loops,
                    reason="Policy engine disabled for project",
                )

            # Retrieve or initialize trace state
            if trace_id not in self._states:
                self._states[trace_id] = TraceState(trace_id=trace_id, project_id=project_id)
            
            state = self._states[trace_id]

            # If already tripped, block immediately
            if state.status == "TRIPPED":
                return PolicyCheckResult(
                    allowed=False,
                    authorization_id=None,
                    status="TRIPPED",
                    tripped_rule=state.tripped_rule,
                    current_cost_usd=round(state.actual_cost_usd + state.reserved_cost_usd, 6),
                    limit_cost_usd=rules.max_cost_per_trace_usd,
                    current_tokens=state.actual_tokens + state.reserved_tokens,
                    limit_tokens=rules.max_tokens_per_trace,
                    current_retry_count=state.retry_count,
                    limit_retry_count=rules.max_retry_loops,
                    reason=state.tripped_reason or "Circuit breaker previously tripped",
                )

            # Derive token and cost estimates safely
            est_tokens = estimated_tokens or 0
            est_cost = estimated_cost if estimated_cost is not None else 0.0

            if est_cost == 0.0 and est_tokens > 0:
                est_cost = self._cost_enricher.calculate_cost(
                    model_name=model_name or "gpt-4o",
                    prompt_tokens=int(est_tokens * 0.7),
                    completion_tokens=int(est_tokens * 0.3),
                )

            # Check 1: Retry limit (Attempt 1 = normal, Attempt 2+ = retries)
            if is_retry and state.retry_count >= rules.max_retry_loops:
                state.status = "TRIPPED"
                state.tripped_rule = "max_retry_loops"
                state.tripped_reason = f"Max retry limit exceeded ({state.retry_count}/{rules.max_retry_loops})"
                return PolicyCheckResult(
                    allowed=False,
                    authorization_id=None,
                    status="TRIPPED",
                    tripped_rule="max_retry_loops",
                    current_cost_usd=round(state.actual_cost_usd + state.reserved_cost_usd, 6),
                    limit_cost_usd=rules.max_cost_per_trace_usd,
                    current_tokens=state.actual_tokens + state.reserved_tokens,
                    limit_tokens=rules.max_tokens_per_trace,
                    current_retry_count=state.retry_count,
                    limit_retry_count=rules.max_retry_loops,
                    reason=state.tripped_reason,
                )

            # Check 2: Cost limit
            proj_cost = state.actual_cost_usd + state.reserved_cost_usd + est_cost
            if proj_cost > rules.max_cost_per_trace_usd:
                state.status = "TRIPPED"
                state.tripped_rule = "max_cost_per_trace_usd"
                state.tripped_reason = (
                    f"Cost limit breach: projected ${proj_cost:.4f} > limit ${rules.max_cost_per_trace_usd:.4f}"
                )
                return PolicyCheckResult(
                    allowed=False,
                    authorization_id=None,
                    status="TRIPPED",
                    tripped_rule="max_cost_per_trace_usd",
                    current_cost_usd=round(proj_cost, 6),
                    limit_cost_usd=rules.max_cost_per_trace_usd,
                    current_tokens=state.actual_tokens + state.reserved_tokens + est_tokens,
                    limit_tokens=rules.max_tokens_per_trace,
                    current_retry_count=state.retry_count,
                    limit_retry_count=rules.max_retry_loops,
                    reason=state.tripped_reason,
                )

            # Check 3: Token limit
            proj_tokens = state.actual_tokens + state.reserved_tokens + est_tokens
            if proj_tokens > rules.max_tokens_per_trace:
                state.status = "TRIPPED"
                state.tripped_rule = "max_tokens_per_trace"
                state.tripped_reason = (
                    f"Token limit breach: projected {proj_tokens} tokens > limit {rules.max_tokens_per_trace}"
                )
                return PolicyCheckResult(
                    allowed=False,
                    authorization_id=None,
                    status="TRIPPED",
                    tripped_rule="max_tokens_per_trace",
                    current_cost_usd=round(proj_cost, 6),
                    limit_cost_usd=rules.max_cost_per_trace_usd,
                    current_tokens=proj_tokens,
                    limit_tokens=rules.max_tokens_per_trace,
                    current_retry_count=state.retry_count,
                    limit_retry_count=rules.max_retry_loops,
                    reason=state.tripped_reason,
                )

            # Authorization passed: Atomic reservation
            auth_id = str(uuid.uuid4())
            if is_retry:
                state.retry_count += 1

            state.reservations[auth_id] = TraceReservation(
                authorization_id=auth_id,
                trace_id=trace_id,
                reserved_cost_usd=round(est_cost, 6),
                reserved_tokens=est_tokens,
            )

            return PolicyCheckResult(
                allowed=True,
                authorization_id=auth_id,
                status="ACTIVE",
                tripped_rule=None,
                current_cost_usd=round(proj_cost, 6),
                limit_cost_usd=rules.max_cost_per_trace_usd,
                current_tokens=proj_tokens,
                limit_tokens=rules.max_tokens_per_trace,
                current_retry_count=state.retry_count,
                limit_retry_count=rules.max_retry_loops,
                reason="Pre-flight check authorized",
            )

    async def record_usage(
        self,
        trace_id: str,
        project_id: str,
        actual_cost: float,
        actual_tokens: int,
        authorization_id: Optional[str] = None,
        is_error: bool = False,
    ) -> PolicyCheckResult:
        """
        Post-flight usage reconciliation.
        Atomically releases reserved budget using authorization_id and records actuals.
        """
        async with self._lock:
            if trace_id not in self._states:
                self._states[trace_id] = TraceState(trace_id=trace_id, project_id=project_id)

            state = self._states[trace_id]

            # Reconcile specific reservation if authorization_id was passed
            if authorization_id and authorization_id in state.reservations:
                state.reservations.pop(authorization_id, None)

            # Record actual usage
            state.actual_cost_usd = round(state.actual_cost_usd + float(actual_cost), 6)
            state.actual_tokens += int(actual_tokens)

            return PolicyCheckResult(
                allowed=(state.status == "ACTIVE"),
                authorization_id=authorization_id,
                status=state.status,
                tripped_rule=state.tripped_rule,
                current_cost_usd=round(state.actual_cost_usd + state.reserved_cost_usd, 6),
                limit_cost_usd=0.50,
                current_tokens=state.actual_tokens + state.reserved_tokens,
                limit_tokens=30000,
                current_retry_count=state.retry_count,
                limit_retry_count=3,
                reason="Usage recorded & reservation reconciled",
            )


# Global singleton instance
circuit_breaker_engine = CircuitBreakerEngine()
