"""Core interface and clock abstractions for ratezoo.

Every limiter takes an injectable ``clock: Callable[[], float]`` defaulting to
``time.monotonic``, so tests and burst simulations can drive time
deterministically via :class:`FakeClock`.
"""

from __future__ import annotations

import abc
import time
from typing import Callable


class RateLimiter(abc.ABC):
    """Abstract base class for all rate-limiting algorithms.

    Contract:
    - ``capacity`` is the maximum burst size (permits), > 0.
    - ``rate`` is the sustained refill rate in permits/second, > 0.
    - ``allow(n)`` attempts to consume ``n`` permits now; it returns a bool
      and never raises. Requests with ``n > capacity`` must return False.
    """

    def __init__(
        self,
        capacity: int,
        rate: float,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be > 0, got {capacity}")
        if rate <= 0:
            raise ValueError(f"rate must be > 0, got {rate}")
        self._capacity = capacity
        self._rate = rate
        self._clock = clock

    @property
    def capacity(self) -> int:
        """Maximum permits available at once."""
        return self._capacity

    @property
    def rate(self) -> float:
        """Sustained permit refill rate, in permits per second."""
        return self._rate

    @abc.abstractmethod
    def allow(self, n: int = 1) -> bool:
        """Try to consume ``n`` permits now.

        Returns True if granted, False otherwise. Must not raise; must
        return False when ``n > capacity``.
        """


class FakeClock:
    """Deterministic clock for tests and burst simulations.

    Call the instance to read the current time; ``advance`` moves it forward.
    """

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError(f"cannot advance by negative seconds: {seconds}")
        self._now += seconds

    def __call__(self) -> float:
        return self._now
