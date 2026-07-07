---
id: TASK-008
title: Build markdown report generator
status: done
depends_on:
- TASK-007
runs:
- RUN-008
created: '2026-07-07T12:26:06Z'
---

## Description

Create `ratezoo/bench/report.py` runnable as `python -m ratezoo.bench.report results.json`.
- Reads one or more JSON result files (positional args), merges records.
- Emits markdown to stdout: (1) a throughput table (rows = algorithms, columns =
  ops/sec per thread count found in the data); (2) per-burst-workload tables
  showing allowed/denied counts per algorithm; (3) for the spike workload, a
  short per-algorithm summary line derived from the trace (e.g., how many of the
  2*capacity spike requests were granted), which surfaces the fixed-window
  boundary-burst and sliding-counter approximation differences.
- Exits with code 2 and a message on missing/invalid input files.
Add `tests/test_report.py`: feed a small hand-written JSON fixture and assert the
output contains a markdown table header row, all algorithm names from the fixture,
and correct allowed/denied numbers; assert exit code 2 for a nonexistent file
(via subprocess).

## Acceptance criteria

- `python -m ratezoo.bench --json results.json && python -m ratezoo.bench.report results.json > comparison.md` exits 0 and comparison.md contains a markdown table (a line starting with '|') and all five algorithm names
- `pytest tests/test_report.py` passes
- `pytest` (entire suite) is green
