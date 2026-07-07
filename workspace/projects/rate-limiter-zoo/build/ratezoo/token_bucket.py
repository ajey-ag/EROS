"""Token bucket rate limiter.

Permits accumulate continuously at ``rate`` per second up to ``capacity``;
each granted request consumes tokens. Refill is computed lazily on access,
so idle limiters cost nothing.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from ratezoo.core import RateLimiter


class TokenBucket(RateLimiter):
    """Classic token bucket: continuous refill, burst up to capacity."""

    def __init__(
        self,
        capacity: int,
        rate: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(capacity, rate, clock=clock)
        self._lock = threading.Lock()
        self._tokens: float = float(capacity)
        self._last_refill: float = clock()

    def _refill(self) -> None:
        # Caller must hold self._lock.
        now = self._clock()
        self._tokens = min(
            float(self._capacity),
            self._tokens + (now - self._last_refill) * self._rate,
        )
        self._tokens = max(0.0, self._tokens)
        self._last_refill = now

    @property
    def available(self) -> float:
        """Current token count after a lazy refill."""
        with self._lock:
            self._refill()
            return self._tokens

    def allow(self, n: int = 1) -> bool:
        if n <= 0 or n > self._capacity:
            return False
        with self._lock:
            self._refill()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False
