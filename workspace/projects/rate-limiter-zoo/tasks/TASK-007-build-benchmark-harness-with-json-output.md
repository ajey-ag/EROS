---
id: TASK-007
title: Build benchmark harness with JSON output
status: done
depends_on:
- TASK-005
runs:
- RUN-007
created: '2026-07-07T12:26:06Z'
---

## Description

Create `ratezoo/bench/__init__.py` and `ratezoo/bench/__main__.py`.
- Throughput workload: for each algorithm, tight loop of `allow(1)` for a fixed
  duration (default 1.0s) measured with `time.perf_counter`; run 5 repetitions,
  report median `ops_per_sec` via `statistics.median` plus min/max spread.
  `--threads N` (default 1) runs N threads hammering one shared limiter.
- Burst workloads on `FakeClock` (fully deterministic): three scripted patterns —
  `steady` (1 request every 1/rate seconds), `spike` (idle 2 windows then
  2*capacity requests at once), `ramp` (linearly increasing request rate) —
  recording the full `[[t, granted], ...]` trace.
- Common params: capacity=100, rate=100.0, overridable via `--capacity`/`--rate`.
- Output: list of records matching the architecture's schema
  `{"algorithm", "workload", "params": {"capacity", "rate", "threads"},
  "ops_per_sec", "allowed", "denied", "duration_s", "trace"}` (trace null for
  throughput workloads). `--json PATH` writes the JSON file; always prints a
  stdlib-formatted comparison table (algorithm x workload, ops/sec and
  allowed/denied) to stdout.

## Acceptance criteria

- `python -m ratezoo.bench --json results.json` exits 0, prints a table containing all five algorithm names, and writes valid JSON
- `python -c "import json; r=json.load(open('results.json')); assert {x['algorithm'] for x in r} == {'token_bucket','leaky_bucket','fixed_window','sliding_log','sliding_counter'}; assert all(set(x) >= {'algorithm','workload','params','ops_per_sec','allowed','denied','duration_s','trace'} for x in r)"` exits 0
- Running the burst workloads twice produces byte-identical trace data (deterministic FakeClock): compare the spike-workload records across two runs
- `python -m ratezoo.bench --threads 4 --json r4.json` exits 0 and records params.threads == 4
