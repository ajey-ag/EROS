"""Sliding window counter rate limiter.

Approximates a sliding window with two fixed-window counters: the estimate
is ``prev_count * overlap_fraction + curr_count``, where overlap_fraction
is the portion of the previous window still inside the sliding window.
O(1) memory, but the uniform-spread assumption misestimates when traffic
inside the previous window was concentrated — see tests for a documented
over-admission case.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Callable

from ratezoo.core import RateLimiter


class SlidingCounter(RateLimiter):
    """Two-bucket sliding window approximation."""

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
        self._idx: int = 0  # index of the current window on the boundary grid
        self._prev_count: int = 0
        self._curr_count: int = 0

    def _roll(self) -> None:
        # Caller must hold self._lock. Windows are grid-aligned to the
        # construction-time anchor, like FixedWindow.
        now = self._clock()
        idx = math.floor((now - self._anchor) / self._window_len)
        if idx > self._idx:
            # Adjacent window: current counts become "previous". A gap of
            # more than one window means the previous window saw nothing.
            self._prev_count = self._curr_count if idx == self._idx + 1 else 0
            self._curr_count = 0
            self._idx = idx

    def _estimate(self) -> float:
        # Caller must hold self._lock, after _roll().
        now = self._clock()
        window_start = self._anchor + self._idx * self._window_len
        overlap = 1.0 - (now - window_start) / self._window_len
        overlap = min(1.0, max(0.0, overlap))
        return self._prev_count * overlap + self._curr_count

    @property
    def current_count(self) -> int:
        """Permits granted in the current fixed window."""
        with self._lock:
            self._roll()
            return self._curr_count

    def allow(self, n: int = 1) -> bool:
        if n <= 0 or n > self._capacity:
            return False
        with self._lock:
            self._roll()
            if self._estimate() + n <= self._capacity:
                self._curr_count += n
                return True
            return False
