"""Benchmark harness for the algorithm zoo.

Two kinds of workloads:

- ``throughput``: wall-clock tight loop of ``allow(1)`` against a real
  monotonic clock, optionally from multiple threads sharing one limiter.
  5 repetitions, median ops/sec reported.
- burst workloads (``steady``, ``spike``, ``ramp``): fully deterministic
  simulations on :class:`~ratezoo.core.FakeClock`, recording the complete
  ``[[t, granted], ...]`` trace.

Every result is a record with the schema::

    {"algorithm", "workload", "params": {"capacity", "rate", "threads"},
     "ops_per_sec", "allowed", "denied", "duration_s", "trace"}

``trace`` is null for throughput workloads; ``ops_per_sec`` is null for
burst workloads (their time axis is simulated).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time

from ratezoo import ALGORITHMS, FakeClock

BURST_WORKLOADS = ("steady", "spike", "ramp")


def _record(algorithm, workload, capacity, rate, threads, *, ops_per_sec, allowed,
            denied, duration_s, trace):
    return {
        "algorithm": algorithm,
        "workload": workload,
        "params": {"capacity": capacity, "rate": rate, "threads": threads},
        "ops_per_sec": ops_per_sec,
        "allowed": allowed,
        "denied": denied,
        "duration_s": duration_s,
        "trace": trace,
    }


def run_throughput(name, cls, capacity, rate, *, threads=1, duration=1.0, reps=5):
    """Median-of-reps wall-clock throughput of allow(1) on a shared limiter."""
    reps_data = []  # (ops_per_sec, allowed, denied, duration)
    for _ in range(reps):
        limiter = cls(capacity, rate)
        calls = [0] * threads
        allowed = [0] * threads
        barrier = threading.Barrier(threads)

        def worker(tid):
            barrier.wait()
            n_calls = 0
            n_allowed = 0
            deadline = time.perf_counter() + duration
            while time.perf_counter() < deadline:
                if limiter.allow(1):
                    n_allowed += 1
                n_calls += 1
            calls[tid] = n_calls
            allowed[tid] = n_allowed

        pool = [threading.Thread(target=worker, args=(i,)) for i in range(threads)]
        t0 = time.perf_counter()
        for t in pool:
            t.start()
        for t in pool:
            t.join()
        elapsed = time.perf_counter() - t0
        total_calls = sum(calls)
        total_allowed = sum(allowed)
        reps_data.append(
            (total_calls / elapsed, total_allowed, total_calls - total_allowed, elapsed)
        )

    reps_data.sort(key=lambda r: r[0])
    ops_median = statistics.median(r[0] for r in reps_data)
    median_rep = reps_data[len(reps_data) // 2]
    rec = _record(
        name, "throughput", capacity, rate, threads,
        ops_per_sec=ops_median,
        allowed=median_rep[1],
        denied=median_rep[2],
        duration_s=median_rep[3],
        trace=None,
    )
    rec["ops_per_sec_min"] = reps_data[0][0]
    rec["ops_per_sec_max"] = reps_data[-1][0]
    return rec


def _burst_schedule(workload, capacity, rate):
    """Yield (advance_seconds, n) ops for a deterministic burst workload."""
    window = capacity / rate
    if workload == "steady":
        # one request every 1/rate seconds for three windows
        return [(1.0 / rate, 1)] * (3 * capacity)
    if workload == "spike":
        # idle two windows, then 2*capacity requests at the same instant
        return [(2 * window, 1)] + [(0.0, 1)] * (2 * capacity - 1)
    if workload == "ramp":
        # linearly increasing request rate: gaps shrink from 2/rate to 0
        total = 3 * capacity
        return [
            ((2.0 / rate) * (1.0 - i / (total - 1)), 1) for i in range(total)
        ]
    raise ValueError(f"unknown workload: {workload}")


def run_burst(name, cls, workload, capacity, rate):
    """Replay a deterministic burst schedule on a FakeClock; keep the trace."""
    clock = FakeClock()
    limiter = cls(capacity, rate, clock=clock)
    trace = []
    allowed = 0
    for advance_s, n in _burst_schedule(workload, capacity, rate):
        clock.advance(advance_s)
        granted = limiter.allow(n)
        allowed += n if granted else 0
        trace.append([clock(), granted])
    return _record(
        name, workload, capacity, rate, 1,
        ops_per_sec=None,
        allowed=allowed,
        denied=len(trace) - allowed,
        duration_s=clock(),
        trace=trace,
    )


def run_all(capacity, rate, *, threads=1, duration=1.0):
    records = []
    for name, cls in sorted(ALGORITHMS.items()):
        records.append(
            run_throughput(name, cls, capacity, rate, threads=threads, duration=duration)
        )
        for workload in BURST_WORKLOADS:
            records.append(run_burst(name, cls, workload, capacity, rate))
    return records


def format_table(records):
    """Algorithm x workload comparison table (ops/sec or allowed/denied)."""
    workloads = ["throughput", *BURST_WORKLOADS]
    algorithms = sorted({r["algorithm"] for r in records})
    by_key = {(r["algorithm"], r["workload"]): r for r in records}

    def cell(name, workload):
        r = by_key.get((name, workload))
        if r is None:
            return "-"
        if workload == "throughput":
            return f"{r['ops_per_sec']:,.0f} ops/s"
        return f"{r['allowed']}/{r['denied']} ok/deny"

    rows = [[name, *(cell(name, w) for w in workloads)] for name in algorithms]
    header = ["algorithm", *workloads]
    widths = [
        max(len(header[c]), *(len(row[c]) for row in rows))
        for c in range(len(header))
    ]
    lines = [
        "  ".join(header[c].ljust(widths[c]) for c in range(len(header))),
        "  ".join("-" * widths[c] for c in range(len(header))),
    ]
    lines += [
        "  ".join(row[c].ljust(widths[c]) for c in range(len(header)))
        for row in rows
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m ratezoo.bench")
    parser.add_argument("--capacity", type=int, default=100)
    parser.add_argument("--rate", type=float, default=100.0)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--duration", type=float, default=1.0,
                        help="seconds per throughput repetition")
    parser.add_argument("--json", dest="json_path", metavar="PATH",
                        help="write full result records to this JSON file")
    args = parser.parse_args(argv)

    records = run_all(
        args.capacity, args.rate, threads=args.threads, duration=args.duration
    )
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2)
        print(f"wrote {len(records)} records to {args.json_path}", file=sys.stderr)
    print(format_table(records))
    return 0
