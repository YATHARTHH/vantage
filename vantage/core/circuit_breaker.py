import threading
from typing import Dict, Optional, Tuple


class TraceActionCircuitBreaker:
    """
    Circuit breaker tracking action budgets per trace/span sequence.
    Prevents agent loops and unbounded consumption attacks even when individual actions are authorized.
    """

    def __init__(
        self,
        max_tool_calls_per_trace: int = 50,
        max_high_risk_actions_per_trace: int = 5,
        max_external_calls_per_trace: int = 10,
    ):
        self.max_tool_calls_per_trace = max_tool_calls_per_trace
        self.max_high_risk_actions_per_trace = max_high_risk_actions_per_trace
        self.max_external_calls_per_trace = max_external_calls_per_trace

        self._lock = threading.Lock()
        # key: trace_id -> count dict
        self._trace_counts: Dict[str, Dict[str, int]] = {}

    def record_and_check(
        self,
        trace_id: str,
        is_high_risk: bool = False,
        is_external: bool = False
    ) -> Tuple[bool, str]:
        """
        Records an action against the trace budget and checks if limits are exceeded.
        Returns (is_allowed: bool, violation_reason_code: str).
        """
        with self._lock:
            if trace_id not in self._trace_counts:
                self._trace_counts[trace_id] = {
                    "total_tool_calls": 0,
                    "high_risk_calls": 0,
                    "external_calls": 0,
                }

            counts = self._trace_counts[trace_id]
            counts["total_tool_calls"] += 1
            if is_high_risk:
                counts["high_risk_calls"] += 1
            if is_external:
                counts["external_calls"] += 1

            if counts["total_tool_calls"] > self.max_tool_calls_per_trace:
                return False, "CIRCUIT_BREAKER_TOTAL_TOOL_LIMIT_EXCEEDED"

            if counts["high_risk_calls"] > self.max_high_risk_actions_per_trace:
                return False, "CIRCUIT_BREAKER_HIGH_RISK_ACTION_LIMIT_EXCEEDED"

            if counts["external_calls"] > self.max_external_calls_per_trace:
                return False, "CIRCUIT_BREAKER_EXTERNAL_CALL_LIMIT_EXCEEDED"

            return True, "CIRCUIT_CLOSED"

    def reset_trace(self, trace_id: str) -> None:
        with self._lock:
            self._trace_counts.pop(trace_id, None)
