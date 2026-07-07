---
id: TASK-005
title: Implement sliding window log and sliding window counter limiters
status: done
depends_on:
- TASK-003
runs:
- RUN-005
created: '2026-07-07T12:26:06Z'
---

## Description

Create `ratezoo/sliding_log.py` with `class SlidingLog(RateLimiter)`:
a `collections.deque[float]` of grant timestamps (one entry per permit); on
`allow(n)`, prune entries older than `now - capacity/rate`, grant iff
`len(log) + n <= capacity`, appending n timestamps on grant; property
`log_size: int`. Lock-guarded.
Create `ratezoo/sliding_counter.py` with `class SlidingCounter(RateLimiter)`:
state `prev_count: int`, `curr_count: int`, `window_start: float`; on window roll,
shift curr -> prev (zero prev if more than one window elapsed); estimated count =
`prev_count * overlap_fraction + curr_count` where overlap_fraction is the portion
of the previous window still inside the sliding window; grant iff
`estimate + n <= capacity`; property `current_count: int`. Lock-guarded.
Register both with GUARANTEES: sliding_log max_burst_factor 1.0; sliding_counter
max_burst_factor 2.0 (interpolation approximation over-admits after an idle
previous window — set the bound to what the property suite empirically requires,
document the chosen value in a comment).
Add unit tests: sliding log allows exactly `capacity` per rolling window with no
boundary burst; sliding counter matches exact behavior under steady traffic and
a test documenting one specific over-admission case of the interpolation.

## Acceptance criteria

- `pytest` (full suite) passes with all five algorithms registered
- `python -c "from ratezoo import ALGORITHMS; assert len(ALGORITHMS) == 5"` exits 0
- Property suite runs invariant (a) for sliding_counter against its declared max_burst_factor without failures across 100 hypothesis examples
