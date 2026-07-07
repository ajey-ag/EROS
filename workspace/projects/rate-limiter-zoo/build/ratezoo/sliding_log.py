"""Sliding window log rate limiter.

Keeps an exact log of grant timestamps (one entry per permit) and admits a
request only if the trailing window of ``capacity / rate`` seconds holds
fewer than ``capacity`` permits. Exact — no boundary burst — at the cost
of O(capacity) memory.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable

from ratezoo.core import RateLimiter


class SlidingLog(RateLimiter):
    """Exact sliding window via a timestamp log."""

    def __init__(
        self,
        capacity: int,
        rate: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(capacity, rate, clock=clock)
        self._lock = threading.Lock()
        self._window_len: float = capacity / rate
        self._log: deque[float] = deque()

    def _prune(self) -> None:
        # Caller must hold self._lock. Entries exactly one window old are
        # pruned (<=) so that after exactly W idle seconds a full burst is
        # admissible again.
        cutoff = self._clock() - self._window_len
        while self._log and self._log[0] <= cutoff:
            self._log.popleft()

    @property
    def log_size(self) -> int:
        """Permits currently counted in the trailing window."""
        with self._lock:
            self._prune()
            return len(self._log)

    def allow(self, n: int = 1) -> bool:
        if n <= 0 or n > self._capacity:
            return False
        with self._lock:
            self._prune()
            if len(self._log) + n <= self._capacity:
                now = self._clock()
                self._log.extend([now] * n)
                return True
            return False
