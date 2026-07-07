---
id: TASK-006
title: Add multi-threaded safety test
status: done
depends_on:
- TASK-005
runs:
- RUN-006
created: '2026-07-07T12:26:06Z'
---

## Description

Add `tests/test_threading.py`: for each algorithm in `ALGORITHMS`, spawn 8 threads
each calling `allow(1)` in a loop (e.g., 5000 calls each) against a limiter with
a real `time.monotonic` clock, capacity 100, rate 100. Assert: no exceptions
propagate from any thread; total granted permits over the run never exceeds
`capacity * max_burst_factor + rate * duration + slack` (compute duration with
`time.perf_counter`, slack = capacity to absorb timing jitter); internal state
properties (`available`, `current_count`, `log_size`) remain within
`[0, capacity]` after the run.

## Acceptance criteria

- `pytest tests/test_threading.py` passes
- `pytest tests/test_threading.py` passes 5 consecutive runs (no flakes): `for /l %i in (1,1,5) do pytest tests/test_threading.py -q` or PowerShell loop exits 0 each time
