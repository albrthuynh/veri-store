"""
rate_limit.py -- Simple in-memory per-client rate limiting for iver-store.

This module provides a small, self-contained rate limiter that can be used by the FastAPI server middleware. The limiter tracks recent request timestamps for each client and decides whether the next request should be allowed.

Design notes:
    - In-memory only: State is lost when the server process restarts.
    - Per-process only: In a multi-process / multi-instance deployment, each process would enforce its own independent limit unless a shared backend is introduced.
    - Sliding-window policy: A client may make at most `max_requests` within the last `window_seconds` seconds.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
import time

@dataclass(frozen=True)
class RateLimitDecision:
    """
    Result of evaluating a request against the rate limiter.

    Attributes:
        allowed (bool): Whether the request should be accepted.
        remaining (int): Number of requests still available in the current window after this decision is applied. Bottoms out at 0.
        retry_after_seconds (int | None): If the request is rejected, how many seconds the client should wait before retrying. `None` when the request is allowed.
    """

    allowed: bool
    remaining: int
    retry_after_seconds: int | None = None



class SlidingWindowRateLimiter:
    """
    In-memory per-client sliding-window rate limiter.

    A client is identified by a caller-provided string key, such as an IP address, bearer token, or some combined identity.

    Example:
        limiter = SlidingWindowRateLimiter(max_requests=60, window_seconds=60)
        decision = limiter.check("127.0.0.1")
        if not decision.allowed:
            ...
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        """
        Initialize the limiter.

        Args:
            max_requests (int): Maximum number of allowed requests per client within the window.
            window_seconds (float): Length of the sliding window in seconds.

        Raises:
            ValueError: If either argument is non-positive.
        """
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
        """
        Evaluate and record a request for the given client.

        This method both checks the current budget and, if allowed, records the new request in the client's sliding window.

        Args:
            client_key (str): Stable identifier for the client being limited.
            now (float | None): Optional monotonic timestamp override, useful for tests.

        Returns:
            A RateLimitDecision describing whether the request is allowed.

        Raises:
            ValueError: If `client_key` is empty.
        """
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
        """
        Forget all recorded requests for a single client.
        
        This is mostly useful in tests.
        """
        with self._lock:
            self._requests.pop(client_key, None)
    
    def _clear(self) -> None:
        """
        Forget all recorded requests for all clients.
        
        This is mainly useful in tests or server reconfiguration paths.
        """
        with self._lock:
            self._requests.clear()
    
    def _prune(self, timestamps: deque[float], window_start: float) -> None:
        """
        Remove timestamps that are older than the active window.
        """
        while (timestamps) and (timestamps[0] <= window_start):
            timestamps.popleft()