from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
import time

@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int | None = None



class SlidingWindowRateLimiter:
    """In-memory per-client sliding-window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be positive.")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive.")
        
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        # Maps client key -> deque of request timestamps (monotonic seconds)
        self._requests: dict[str, deque[float]] = {}

        # FastAPI may handle overlapping requests, so access to shared limiter state should be synchronized.
        self._lock = Lock()
    
    def check(self, client_key: str, *, now: float | None = None) -> RateLimitDecision:
        if not client_key:
            raise ValueError("client_key must be non-empty.")
        
        current_time = time.monotonic() if now is None else now
        window_start = current_time - self.window_seconds

        with self._lock:
            timestamps = self._requests.setdefault(client_key, deque())

            # Drop requests that have fallen out of the active window before computing the current budget.
            self._prune(timestamps, window_start)

            if len(timestamps) >= self.max_requests:
                oldest_in_window = timestamps[0]
                retry_after = max(1, int((oldest_in_window + self.window_seconds) - current_time))
                return RateLimitDecision(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )

            timestamps.append(current_time)
            remaining = self.max_requests - len(timestamps)

            return RateLimitDecision(
                allowed=True,
                remaining=remaining,
                retry_after_seconds=None,
            )
    
    def _reset(self, client_key: str) -> None:
        with self._lock:
            self._requests.pop(client_key, None)
    
    def _clear(self) -> None:
        with self._lock:
            self._requests.clear()
    
    def _prune(self, timestamps: deque[float], window_start: float) -> None:
        while (timestamps) and (timestamps[0] <= window_start):
            timestamps.popleft()
