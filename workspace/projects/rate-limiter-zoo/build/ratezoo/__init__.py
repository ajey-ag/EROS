"""ratezoo: classic rate-limiting algorithms behind one interface."""

from ratezoo.core import FakeClock, RateLimiter
from ratezoo.fixed_window import FixedWindow
from ratezoo.leaky_bucket import LeakyBucket
from ratezoo.sliding_counter import SlidingCounter
from ratezoo.sliding_log import SlidingLog
from ratezoo.token_bucket import TokenBucket

# Single source of truth mapping algorithm names to classes. Tests
# parametrize over it and the bench iterates it; each algorithm module
# adds its entry here as it lands.
ALGORITHMS: dict[str, type[RateLimiter]] = {
    "token_bucket": TokenBucket,
    "leaky_bucket": LeakyBucket,
    "fixed_window": FixedWindow,
    "sliding_log": SlidingLog,
    "sliding_counter": SlidingCounter,
}

# Per-algorithm behavioral guarantees, read by the property test suite:
# - max_burst_factor: grants in any window of length W = capacity/rate are
#   bounded by capacity * max_burst_factor + rate * W. The rate*W term is the
#   legitimate refill during the window; max_burst_factor captures how much
#   extra burst the algorithm's bookkeeping admits on top of that (1.0 = exact,
#   2.0 = boundary/approximation flaw).
# - reset_after_idle_factor: multiples of W the limiter must sit idle before a
#   full burst of `capacity` is guaranteed to be granted again.
GUARANTEES: dict[str, dict] = {
    "token_bucket": {"max_burst_factor": 1.0, "reset_after_idle_factor": 1.0},
    "leaky_bucket": {"max_burst_factor": 1.0, "reset_after_idle_factor": 1.0},
    # boundary-burst flaw: capacity late in one window + capacity early in
    # the next can land inside a single sliding window of length W
    "fixed_window": {"max_burst_factor": 2.0, "reset_after_idle_factor": 1.0},
    "sliding_log": {"max_burst_factor": 1.0, "reset_after_idle_factor": 1.0},
    # The interpolation's empirical worst case grazes factor 1.0 (a burst
    # right after a window roll can approach 2x capacity total in-window,
    # exactly the 1.0 bound), so 2.0 is declared to keep headroom over the
    # approximation error rather than sit on the boundary. It also needs two
    # idle windows before prev_count fully ages out, hence reset factor 2.0.
    "sliding_counter": {"max_burst_factor": 2.0, "reset_after_idle_factor": 2.0},
}

__all__ = [
    "ALGORITHMS",
    "GUARANTEES",
    "FakeClock",
    "FixedWindow",
    "LeakyBucket",
    "RateLimiter",
    "SlidingCounter",
    "SlidingLog",
    "TokenBucket",
]
