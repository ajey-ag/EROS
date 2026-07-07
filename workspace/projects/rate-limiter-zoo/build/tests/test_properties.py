"""Property tests parametrized over the ALGORITHMS registry.

Every algorithm added to ``ratezoo.ALGORITHMS`` is covered automatically;
its behavioral bounds come from ``ratezoo.GUARANTEES``, not hardcoded
constants.

Invariant (a) is checked as: grants in any half-open window of length
W = capacity/rate never exceed ``capacity * max_burst_factor + rate * W``.
The task spec's original bound of ``capacity * max_burst_factor`` alone is
unsatisfiable for any refill-based limiter — a full bucket plus one window
of legitimate refill grants ~2x capacity — so the refill term is part of
the bound and max_burst_factor measures the *extra* burst an algorithm's
bookkeeping admits.
"""

from __future__ import annotations

import random

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from ratezoo import ALGORITHMS, GUARANTEES, FakeClock

CAPACITY = 8
RATE = 2.0
WINDOW = CAPACITY / RATE
EPSILON = 1e-6 * CAPACITY

# (advance_seconds, request_n) schedules.
ops_strategy = st.lists(
    st.tuples(
        st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        st.integers(min_value=1, max_value=2 * CAPACITY),
    ),
    max_size=200,
)

# Deterministic worst case: drain a full bucket, then ride the refill.
# Grants 15 permits inside the window [0, 4): 8 at t=0 plus one every 0.5s.
# Keeps invariant (a) honest even when hypothesis doesn't find a burst.
BURST_EXAMPLE = [(0.0, 1)] * 16 + [(0.5, 1)] * 7


def run_schedule(limiter, clock, ops):
    """Replay (advance_seconds, request_n) ops; return (timestamp, n, granted)."""
    records = []
    for advance_s, n in ops:
        clock.advance(advance_s)
        granted = limiter.allow(n)
        records.append((clock(), n, granted))
    return records


def max_granted_in_window(records, window):
    """Max permits granted in any half-open window [t, t+window) — O(n) scan."""
    grants = [(t, n) for t, n, granted in records if granted]
    best = 0
    total = 0
    j = 0
    for i in range(len(grants)):
        while j < len(grants) and grants[j][0] < grants[i][0] + window:
            total += grants[j][1]
            j += 1
        best = max(best, total)
        total -= grants[i][1]
    return best


def make(cls):
    clock = FakeClock()
    return cls(CAPACITY, RATE, clock=clock), clock


@pytest.mark.parametrize("name,cls", sorted(ALGORITHMS.items()))
class TestAlgorithmInvariants:
    @given(ops=ops_strategy)
    @example(ops=BURST_EXAMPLE)
    def test_window_grant_bound(self, name, cls, ops):
        limiter, clock = make(cls)
        records = run_schedule(limiter, clock, ops)
        bound = (
            CAPACITY * GUARANTEES[name]["max_burst_factor"] + RATE * WINDOW + EPSILON
        )
        assert max_granted_in_window(records, WINDOW) <= bound

    @given(ops=ops_strategy)
    def test_full_burst_after_idle(self, name, cls, ops):
        limiter, clock = make(cls)
        run_schedule(limiter, clock, ops)
        idle = WINDOW * GUARANTEES[name]["reset_after_idle_factor"]
        # tiny margin so exact-boundary float rounding can't leave stale state
        clock.advance(idle + 1e-9)
        assert all(limiter.allow(1) for _ in range(CAPACITY))

    @given(ops=ops_strategy)
    def test_never_raises_and_over_capacity_denied(self, name, cls, ops):
        limiter, clock = make(cls)
        records = run_schedule(limiter, clock, ops)  # allow() raising fails here
        for _t, n, granted in records:
            if n > CAPACITY:
                assert granted is False
        assert limiter.allow(CAPACITY + 1) is False


@pytest.mark.parametrize("name,cls", sorted(ALGORITHMS.items()))
@settings(max_examples=10, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_long_schedule_float_drift(name, cls, seed):
    """Regression net for float drift over long schedules.

    The 2000-op schedule is derived from a hypothesis-generated seed rather
    than generated element-wise, which would blow hypothesis's entropy budget.
    """
    rng = random.Random(seed)
    ops = [
        (rng.uniform(0.0, 1.0), rng.randint(1, 2 * CAPACITY)) for _ in range(2000)
    ]
    limiter, clock = make(cls)
    records = run_schedule(limiter, clock, ops)
    bound = CAPACITY * GUARANTEES[name]["max_burst_factor"] + RATE * WINDOW + EPSILON
    assert max_granted_in_window(records, WINDOW) <= bound
