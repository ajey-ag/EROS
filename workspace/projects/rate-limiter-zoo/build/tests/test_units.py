"""Per-algorithm unit tests driven by FakeClock."""

from __future__ import annotations

from ratezoo import (
    FakeClock,
    FixedWindow,
    LeakyBucket,
    SlidingCounter,
    SlidingLog,
    TokenBucket,
)


class TestTokenBucket:
    def test_burst_of_capacity_allowed_then_denied(self):
        clock = FakeClock()
        tb = TokenBucket(capacity=5, rate=1.0, clock=clock)
        for _ in range(5):
            assert tb.allow()
        assert not tb.allow()

    def test_full_refill_after_capacity_over_rate_seconds(self):
        clock = FakeClock()
        tb = TokenBucket(capacity=10, rate=2.0, clock=clock)
        for _ in range(10):
            assert tb.allow()
        assert tb.available == 0.0
        clock.advance(10 / 2.0)
        assert tb.available == 10.0

    def test_partial_refill_grants_proportionally(self):
        clock = FakeClock()
        tb = TokenBucket(capacity=4, rate=2.0, clock=clock)
        for _ in range(4):
            assert tb.allow()
        assert not tb.allow()
        clock.advance(1.0)  # 1s at rate=2 -> 2 more permits
        assert tb.allow()
        assert tb.allow()
        assert not tb.allow()

    def test_over_capacity_request_denied_without_mutation(self):
        clock = FakeClock()
        tb = TokenBucket(capacity=3, rate=1.0, clock=clock)
        before = tb.available
        assert not tb.allow(4)
        assert tb.available == before

    def test_nonpositive_n_denied_without_mutation(self):
        clock = FakeClock()
        tb = TokenBucket(capacity=3, rate=1.0, clock=clock)
        before = tb.available
        assert not tb.allow(0)
        assert not tb.allow(-1)
        assert tb.available == before

    def test_refill_never_exceeds_capacity(self):
        clock = FakeClock()
        tb = TokenBucket(capacity=2, rate=100.0, clock=clock)
        clock.advance(60.0)
        assert tb.available == 2.0


class TestLeakyBucket:
    def test_denies_when_full(self):
        clock = FakeClock()
        lb = LeakyBucket(capacity=5, rate=1.0, clock=clock)
        assert lb.allow(5)
        assert not lb.allow()
        assert lb.available == 0.0

    def test_drains_at_rate(self):
        clock = FakeClock()
        lb = LeakyBucket(capacity=6, rate=2.0, clock=clock)
        assert lb.allow(6)
        clock.advance(1.0)  # drains rate * 1s = 2
        assert lb.available == 2.0
        assert lb.allow(2)
        assert not lb.allow()
        clock.advance(3.0)  # full drain
        assert lb.available == 6.0

    def test_over_capacity_and_nonpositive_denied(self):
        clock = FakeClock()
        lb = LeakyBucket(capacity=3, rate=1.0, clock=clock)
        assert not lb.allow(4)
        assert not lb.allow(0)
        assert lb.available == 3.0


class TestFixedWindow:
    def test_denies_over_quota_within_window(self):
        clock = FakeClock()
        fw = FixedWindow(capacity=4, rate=2.0, clock=clock)  # window = 2s
        for _ in range(4):
            assert fw.allow()
        assert not fw.allow()
        clock.advance(1.9)  # still inside the same window
        assert not fw.allow()

    def test_resets_exactly_at_boundary(self):
        clock = FakeClock()
        fw = FixedWindow(capacity=4, rate=2.0, clock=clock)  # window = 2s
        assert fw.allow(4)
        clock.advance(2.0)  # exactly on the boundary -> new window
        assert fw.current_count == 0
        assert fw.allow(4)

    def test_window_grid_is_anchored_not_sliding(self):
        clock = FakeClock()
        fw = FixedWindow(capacity=4, rate=2.0, clock=clock)  # boundaries 2,4,6..
        clock.advance(1.5)
        assert fw.allow(4)  # granted at t=1.5, window [0, 2)
        clock.advance(0.5)  # t=2.0: boundary is grid-aligned, not 1.5+2
        assert fw.allow(4)


def test_fixed_window_boundary_double_burst():
    """Documents the known fixed-window flaw: capacity grants late in one
    window plus capacity grants early in the next all succeed within a
    span shorter than one window length."""
    clock = FakeClock()
    fw = FixedWindow(capacity=10, rate=10.0, clock=clock)  # window = 1s
    clock.advance(0.9)  # late in window [0, 1)
    for _ in range(10):
        assert fw.allow()
    clock.advance(0.2)  # early in window [1, 2); only 0.2s later
    for _ in range(10):
        assert fw.allow()
    # 20 permits granted inside 0.2s, twice the nominal capacity per window


class TestSlidingLog:
    def test_exactly_capacity_per_rolling_window_no_boundary_burst(self):
        # Same schedule as the fixed-window double burst: sliding log
        # denies the second burst because the window truly slides.
        clock = FakeClock()
        sl = SlidingLog(capacity=10, rate=10.0, clock=clock)  # window = 1s
        clock.advance(0.9)
        for _ in range(10):
            assert sl.allow()
        clock.advance(0.2)  # t=1.1: grants at t=0.9 still in trailing 1s
        assert not sl.allow()
        assert sl.log_size == 10

    def test_permits_free_up_as_entries_age_out(self):
        clock = FakeClock()
        sl = SlidingLog(capacity=10, rate=10.0, clock=clock)
        # binary-exact timestamps so "exactly one window later" is exact
        clock.advance(0.5)
        assert sl.allow(10)
        clock.advance(1.0)  # exactly one window after the grants
        assert sl.log_size == 0
        assert sl.allow(10)

    def test_over_capacity_denied_without_mutation(self):
        clock = FakeClock()
        sl = SlidingLog(capacity=3, rate=1.0, clock=clock)
        assert not sl.allow(4)
        assert sl.log_size == 0


class TestSlidingCounter:
    def test_matches_exact_behavior_under_steady_traffic(self):
        # 1 request/second at rate 2/s, capacity 4: an exact sliding
        # window grants everything, and so does the interpolation.
        clock = FakeClock()
        sc = SlidingCounter(capacity=4, rate=2.0, clock=clock)
        for _ in range(20):
            assert sc.allow()
            clock.advance(1.0)

    def test_documented_over_admission_of_interpolation(self):
        # 10 grants at t=0.99, late in window [0, 1). At t=1.1 the exact
        # trailing-1s window still holds all 10 permits (SlidingLog denies),
        # but the interpolation assumes they were spread uniformly:
        # estimate = 10 * 0.9 = 9, so SlidingCounter over-admits one.
        clock = FakeClock()
        sc = SlidingCounter(capacity=10, rate=10.0, clock=clock)
        exact = SlidingLog(capacity=10, rate=10.0, clock=clock)
        clock.advance(0.99)
        assert sc.allow(10)
        assert exact.allow(10)
        clock.advance(0.11)  # t = 1.1
        assert not exact.allow()  # exact: still 10 in the trailing window
        assert sc.allow()  # approximation: over-admits here

    def test_needs_two_idle_windows_for_full_reset(self):
        clock = FakeClock()
        sc = SlidingCounter(capacity=4, rate=2.0, clock=clock)  # window = 2s
        assert sc.allow(4)
        clock.advance(2.0)  # prev_count = 4, overlap starts at 1.0
        assert not sc.allow()
        clock.advance(2.0)  # two windows elapsed since the burst: fully clear
        assert sc.allow(4)
