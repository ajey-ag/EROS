---
id: TASK-003
title: Build property test suite parametrized over the registry
status: done
depends_on:
- TASK-002
runs:
- RUN-003
created: '2026-07-07T12:26:06Z'
---

## Description

Create `tests/test_properties.py` driven by hypothesis, parametrized with
`@pytest.mark.parametrize` over `ratezoo.ALGORITHMS.items()` so future algorithms
are covered automatically.
- Add per-algorithm guarantee metadata: in `ratezoo/__init__.py` define
  `GUARANTEES: dict[str, dict]` with at least `max_burst_factor: float` per algorithm
  (token_bucket: 1.0). Property tests read the bound from here, not a hardcoded constant.
- Shared helper `run_schedule(limiter, clock, ops) -> list[tuple[float, int, bool]]`
  that replays a schedule of `(advance_seconds, request_n)` tuples, returning
  `(timestamp, n, granted)` records.
- Hypothesis strategy: lists (up to ~200 entries) of
  `(advance_seconds in [0, 10] floats, request_n in [1, 2*capacity] ints)`.
- Properties asserted for every registered algorithm:
  (a) total permits granted in any window of length `W = capacity / rate` never
  exceeds `capacity * max_burst_factor + epsilon` (epsilon = 1e-6 * capacity, checked
  by a sliding scan over the grant records);
  (b) after advancing `capacity / rate` seconds with no requests, a burst of
  `capacity` single-permit calls is fully granted;
  (c) `allow(n)` never raises for any n in the schedule, and `allow(capacity + 1)`
  always returns False.
- Include one long-schedule regression test (>= 2000 ops, `@settings(max_examples=10)`)
  to catch float drift.

## Acceptance criteria

- `pytest tests/test_properties.py` passes with token_bucket as the only registry entry
- Temporarily setting max_burst_factor for token_bucket to 0.5 makes property (a) fail (verifies the test has teeth), then restore
- `pytest` (full suite) passes
