"""Fixed window counter rate limiter.

Time is divided into fixed windows of ``capacity / rate`` seconds anchored
at construction time; up to ``capacity`` permits are granted per window.
Simple and cheap, but famously allows a 2x burst straddling a window
boundary — documented and tested rather than hidden.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Callable

from ratezoo.core import RateLimiter


class FixedWindow(RateLimiter):
    """Fixed window counter: per-window quota, resets on the boundary grid."""

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
        self._anchor: float = clock()
        self._window_start: float = self._anchor
        self._count: int = 0

    def _roll(self) -> None:
        # Caller must hold self._lock. Align window_start to the boundary
        # grid anchored at construction, not to `now`, so boundaries are
        # stable regardless of when requests arrive.
        now = self._clock()
        if now >= self._window_start + self._window_len:
            idx = math.floor((now - self._anchor) / self._window_len)
            self._window_start = self._anchor + idx * self._window_len
            self._count = 0

    @property
    def current_count(self) -> int:
        """Permits granted in the current window."""
        with self._lock:
            self._roll()
            return self._count

    def allow(self, n: int = 1) -> bool:
        if n <= 0 or n > self._capacity:
            return False
        with self._lock:
            self._roll()
            if self._count + n <= self._capacity:
                self._count += n
                return True
            return False
