---
id: TASK-004
title: Implement leaky bucket and fixed window limiters
status: done
depends_on:
- TASK-003
runs:
- RUN-004
created: '2026-07-07T12:26:06Z'
---

## Description

Create `ratezoo/leaky_bucket.py` with `class LeakyBucket(RateLimiter)`:
state `level: float`, `last_leak: float`; on `allow(n)`, drain
`level = max(0, level - (now - last_leak) * rate)`, grant iff `level + n <= capacity`
(add n on grant); property `available: float` = remaining headroom. Lock-guarded.
Create `ratezoo/fixed_window.py` with `class FixedWindow(RateLimiter)`:
window length `capacity / rate` seconds; state `window_start: float`, `count: int`;
reset count when `now >= window_start + window_len` (align window_start to the
boundary grid, not to `now`); grant iff `count + n <= capacity`; property
`current_count: int`. Lock-guarded.
Register both in `ALGORITHMS` with `GUARANTEES` entries: leaky_bucket
max_burst_factor 1.0; fixed_window max_burst_factor 2.0 (boundary-burst flaw).
Add unit tests to `tests/test_units.py`: leaky bucket denies when full and drains
at `rate`; fixed window resets exactly at the boundary; a dedicated test named
`test_fixed_window_boundary_double_burst` demonstrating that `capacity` grants
late in one window plus `capacity` grants early in the next (within one window
length total) all succeed — documenting the known flaw.

## Acceptance criteria

- `pytest tests/test_properties.py` passes with three algorithms in the registry
- `pytest tests/test_units.py::test_fixed_window_boundary_double_burst` passes
- `python -c "from ratezoo import ALGORITHMS; assert set(ALGORITHMS) >= {'token_bucket','leaky_bucket','fixed_window'}"` exits 0
