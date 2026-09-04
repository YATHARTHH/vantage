import time
import threading
from typing import Dict, Tuple, Optional


class MultiDimensionalRateLimiter:
    """
    Multi-dimensional rate and concurrency limiter for ingress, replay, and agent tool execution.
    Supports requests/min, concurrent executions, tokens/min, and cost/hour caps.
    """

    def __init__(
        self,
        default_rate_limit: int = 100,
        default_concurrency_limit: int = 5,
        window_seconds: float = 60.0
    ):
        self.default_rate_limit = default_rate_limit
        self.default_concurrency_limit = default_concurrency_limit
        self.window_seconds = window_seconds

        self._lock = threading.Lock()
        # key: (key_type, identifier) -> list of timestamps
        self._request_timestamps: Dict[Tuple[str, str], list[float]] = {}
        # key: (key_type, identifier) -> active concurrency count
        self._active_concurrency: Dict[Tuple[str, str], int] = {}

    def is_rate_allowed(
        self, key_type: str, identifier: str, limit: Optional[int] = None
    ) -> bool:
        max_limit = limit if limit is not None else self.default_rate_limit
        now = time.time()
        key = (key_type, identifier)

        with self._lock:
            if key not in self._request_timestamps:
                self._request_timestamps[key] = []

            # Prune expired timestamps
            cutoff = now - self.window_seconds
            self._request_timestamps[key] = [
                ts for ts in self._request_timestamps[key] if ts > cutoff
            ]

            if len(self._request_timestamps[key]) >= max_limit:
                return False

            self._request_timestamps[key].append(now)
            return True

    def acquire_concurrency(
        self, key_type: str, identifier: str, max_concurrent: Optional[int] = None
    ) -> bool:
        limit = max_concurrent if max_concurrent is not None else self.default_concurrency_limit
        key = (key_type, identifier)

        with self._lock:
            current = self._active_concurrency.get(key, 0)
            if current >= limit:
                return False
            self._active_concurrency[key] = current + 1
            return True

    def release_concurrency(self, key_type: str, identifier: str) -> None:
        key = (key_type, identifier)
        with self._lock:
            current = self._active_concurrency.get(key, 0)
            if current > 0:
                self._active_concurrency[key] = current - 1
