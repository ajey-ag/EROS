"""Leaky bucket rate limiter (as a meter).

Requests pour into a bucket that drains at ``rate`` per second; a request
is admitted only if it fits under ``capacity``. Equivalent in admission
behavior to a token bucket, but tracked as fill level rather than tokens.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from ratezoo.core import RateLimiter


class LeakyBucket(RateLimiter):
    """Leaky bucket meter: continuous drain, admit while under capacity."""

    def __init__(
        self,
        capacity: int,
        rate: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(capacity, rate, clock=clock)
        self._lock = threading.Lock()
        self._level: float = 0.0
        self._last_leak: float = clock()

    def _drain(self) -> None:
        # Caller must hold self._lock.
        now = self._clock()
        self._level = max(0.0, self._level - (now - self._last_leak) * self._rate)
        self._level = min(self._level, float(self._capacity))
        self._last_leak = now

    @property
    def available(self) -> float:
        """Remaining headroom (permits that would be admitted right now)."""
        with self._lock:
            self._drain()
            return float(self._capacity) - self._level

    def allow(self, n: int = 1) -> bool:
        if n <= 0 or n > self._capacity:
            return False
        with self._lock:
            self._drain()
            if self._level + n <= self._capacity:
                self._level += n
                return True
            return False
