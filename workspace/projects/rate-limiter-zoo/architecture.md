# Architecture: Rate Limiter Zoo

## Overview

Rate Limiter Zoo is a single Python package (`ratezoo`) containing five classic rate-limiting algorithms behind one shared interface, plus the test and benchmark tooling needed to compare them rigorously. The core design decision is to make **time injectable**: every limiter takes a `clock: Callable[[], float]` parameter defaulting to `time.monotonic`. This one choice makes property-based testing deterministic (tests drive a fake clock through arbitrary schedules), makes burst behavior reproducible in benchmarks, and costs nothing at runtime. Everything else follows from it.

The system is deliberately flat: one package, five small implementation modules, a benchmark module runnable as `python -m ratezoo.bench`, and a test suite. There is no persistence, no networking, no concurrency framework — limiters are in-process objects, and thread safety is provided by a plain `threading.Lock` per limiter so the benchmark can exercise contended scenarios honestly. Runtime dependencies are zero (stdlib only); pytest and hypothesis are test-only, exactly as the charter demands.

The comparison writeup — the actual deliverable of the project — is fed by the benchmark's JSON output. The bench module emits structured results (throughput, allow/deny counts, burst-response traces) so the writeup's tables and claims are regenerable from a single command rather than hand-collected numbers.

## Components

1. **Core interface & clock (`ratezoo/core.py`)**
   Responsibility: define the `RateLimiter` abstract base class and the shared vocabulary all other components depend on.
   Key interfaces: `RateLimiter.allow(n: int = 1) -> bool` (try to consume `n` permits now), properties `capacity` and `rate` (permits/second), constructor contract `__init__(capacity, rate, *, clock=time.monotonic)`. Also a `FakeClock` class (`advance(seconds)`, callable to read time) used by tests and burst simulations.

2. **Bucket limiters (`ratezoo/token_bucket.py`, `ratezoo/leaky_bucket.py`)**
   Responsibility: the two continuous-refill algorithms. Token bucket refills lazily on each `allow()` call from elapsed clock time; leaky bucket tracks queue level draining at `rate`. Both are ~40 lines each, guarded by a `threading.Lock`.
   Key interfaces: implement `RateLimiter`; expose `available` (current tokens / remaining queue headroom) for test assertions.

3. **Window limiters (`ratezoo/fixed_window.py`, `ratezoo/sliding_log.py`, `ratezoo/sliding_counter.py`)**
   Responsibility: the three windowed algorithms. Fixed window resets a counter at window boundaries; sliding window log keeps a `collections.deque` of timestamps pruned on access; sliding window counter interpolates between the current and previous window counts.
   Key interfaces: implement `RateLimiter`; each exposes its internal state read-only (`current_count`, `log_size`, etc.) so property tests can assert invariants without reaching into private fields.

4. **Registry (`ratezoo/__init__.py`)**
   Responsibility: single source of truth mapping algorithm names to classes: `ALGORITHMS: dict[str, type[RateLimiter]]`. Tests parametrize over it; the bench iterates it; adding a sixth algorithm later means adding one entry.
   Key interfaces: `ALGORITHMS`, plus re-exports of the five classes and `RateLimiter`.

5. **Property test suite (`tests/test_properties.py`, `tests/test_units.py`)**
   Responsibility: prove the invariants. Hypothesis generates arbitrary schedules of `(advance_dt, request_n)` operations against a `FakeClock` and asserts, for every algorithm in the registry: (a) permits granted in any window of length `W` never exceed the algorithm's stated bound, (b) after full refill time with no requests, capacity is fully available, (c) `allow()` never raises and never returns permits when `n > capacity`. Per-algorithm unit tests pin down boundary semantics (e.g., fixed-window edge burst is *allowed* — that's the algorithm's known flaw, and the test documents it).
   Key interfaces: pytest parametrization over `ratezoo.ALGORITHMS`; a shared `run_schedule(limiter, clock, ops)` helper.

6. **Benchmark harness (`ratezoo/bench/__init__.py` + `__main__.py`)**
   Responsibility: run each algorithm through identical workloads and emit results. Two workload types: **throughput** (tight loop of `allow()` calls with real clock, single- and multi-threaded via `threading`) and **burst behavior** (fake clock, scripted traffic patterns — steady, spike, ramp — recording the allow/deny decision sequence).
   Key interfaces: `python -m ratezoo.bench [--json results.json] [--threads N]`; writes JSON (`{algorithm, workload, ops_per_sec, allowed, denied, trace}`) and prints a comparison table with stdlib string formatting.

7. **Report generator (`ratezoo/bench/report.py`)**
   Responsibility: turn one or more JSON result files into the markdown tables and burst-behavior summaries used in the writeup, so the comparison document is regenerable.
   Key interfaces: `python -m ratezoo.bench.report results.json > comparison.md`.

## Data model

There is no stored state between runs; the data model is in-memory objects and one JSON file format.

- **Limiter state** (in-memory, per instance): token bucket — `tokens: float`, `last_refill: float`; leaky bucket — `level: float`, `last_leak: float`; fixed window — `window_start: float`, `count: int`; sliding log — `deque[float]` of grant timestamps; sliding counter — `prev_count: int`, `curr_count: int`, `window_start: float`. All timestamps come from the injected clock.
- **Benchmark result** (JSON, list of records): `{"algorithm": str, "workload": str, "params": {"capacity": int, "rate": float, "threads": int}, "ops_per_sec": float, "allowed": int, "denied": int, "duration_s": float, "trace": [[t, granted], ...] | null}`. The `trace` field is populated only for burst workloads and drives the burst-behavior plots/tables in the writeup.
- **Schedule** (test-internal): a list of `(advance_seconds: float, request_n: int)` tuples generated by hypothesis and replayed against a `FakeClock`.

## Technology choices

- **Python 3.11+** — charter mandates Python; 3.11+ for modern typing (`Self`, `dict[str, ...]`) without `typing_extensions`.
- **stdlib only at runtime** (`time`, `threading`, `collections`, `json`, `argparse`, `statistics`) — hard charter constraint, and nothing here needs more.
- **pytest** — the charter's success criterion is literally "`pytest` green"; industry-standard test runner.
- **hypothesis** — charter-specified for property tests; its stateful/schedule generation is exactly the right tool for proving rate-limit invariants.
- **`time.monotonic` as default clock** — immune to wall-clock adjustments; injectable-clock pattern keeps tests deterministic on a laptop with no infrastructure.
- **JSON for bench output** — stdlib-writable, diffable, and directly consumable by the report generator; no plotting or dataframe library needed for a comparison table.

## Build order

1. **Core interface & clock (component 1)** — everything else imports it; `FakeClock` must exist before any test can be written.
2. **Token bucket (component 2, first half) + its unit tests** — the simplest, best-understood algorithm; building it end-to-end validates the interface and clock design before four more implementations commit to it.
3. **Property test suite skeleton (component 5)** — write the schedule-driven invariant tests against token bucket alone, parametrized over the (currently one-entry) registry. Getting the invariant *statements* right early is the project's core intellectual work; every subsequent algorithm then gets tested for free.
4. **Remaining four limiters (components 2–3) with registry (component 4)** — add each algorithm one at a time; each lands with its registry entry and immediately runs the full property suite. Expect the sliding-window-counter interpolation to need an invariant tolerance — discover that here, not later.
5. **Benchmark harness (component 6)** — needs all five algorithms and the registry; burst workloads reuse `FakeClock` from step 1.
6. **Report generator (component 7)** — needs real JSON output to develop against; last because it's pure formatting.

## Risks

1. **Invariant statements that are wrong or too strict.** The five algorithms have genuinely different guarantees — fixed window permits 2× bursts at boundaries; the sliding counter is an approximation that can over- or under-admit. A naive "never exceed capacity per window" property will fail *correctly* for some algorithms. Mitigation: define per-algorithm bounds in the registry entry (e.g., `max_burst_factor`) and have the property test assert against each algorithm's own declared guarantee; document the differences in the writeup — they're the interesting result, not a bug.
2. **Timer resolution and noise on Windows skews benchmarks.** `time.monotonic` granularity and background load on a laptop can make throughput numbers unstable. Mitigation: use `time.perf_counter` inside the bench for measurement, run multiple repetitions reporting median and spread via `statistics`, and keep burst-behavior comparisons on the `FakeClock` where they're fully deterministic.
3. **Float drift in lazy-refill arithmetic.** Accumulating `elapsed * rate` over long hypothesis-generated schedules can drift enough to violate a strict invariant assertion. Mitigation: clamp state to `[0, capacity]` on every update, compare with an explicit epsilon in tests, and add a hypothesis regression test with very long schedules to catch drift early.
