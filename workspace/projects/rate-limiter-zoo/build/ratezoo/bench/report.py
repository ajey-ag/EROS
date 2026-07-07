"""Markdown report generator for benchmark results.

Usage: ``python -m ratezoo.bench.report results.json [more.json ...]``

Reads one or more JSON result files produced by ``python -m ratezoo.bench``,
merges the records, and writes a markdown comparison to stdout. Exits with
code 2 on missing or invalid input files.
"""

from __future__ import annotations

import argparse
import json
import sys


def load_records(paths):
    records = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except OSError as exc:
            raise SystemExit(f"error: cannot read {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise SystemExit(f"error: {path} is not valid JSON: {exc}") from exc
        if not isinstance(data, list) or not all(
            isinstance(r, dict) and "algorithm" in r and "workload" in r
            for r in data
        ):
            raise SystemExit(
                f"error: {path} does not look like a ratezoo.bench result file"
            )
        records.extend(data)
    return records


def _md_table(header, rows):
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def throughput_section(records):
    tp = [r for r in records if r["workload"] == "throughput"]
    if not tp:
        return ""
    thread_counts = sorted({r["params"]["threads"] for r in tp})
    algorithms = sorted({r["algorithm"] for r in tp})
    by_key = {(r["algorithm"], r["params"]["threads"]): r for r in tp}
    header = ["algorithm", *(f"ops/sec ({t} thread{'s' if t != 1 else ''})"
                             for t in thread_counts)]
    rows = []
    for name in algorithms:
        row = [name]
        for t in thread_counts:
            r = by_key.get((name, t))
            row.append(f"{r['ops_per_sec']:,.0f}" if r else "-")
        rows.append(row)
    return "## Throughput\n\n" + _md_table(header, rows)


def burst_sections(records):
    sections = []
    workloads = sorted({r["workload"] for r in records if r["workload"] != "throughput"})
    for workload in workloads:
        recs = sorted(
            (r for r in records if r["workload"] == workload),
            key=lambda r: r["algorithm"],
        )
        rows = [
            [r["algorithm"], r["allowed"], r["denied"],
             f"{r['duration_s']:.2f}"]
            for r in recs
        ]
        table = _md_table(["algorithm", "allowed", "denied", "sim duration (s)"], rows)
        sections.append(f"## Burst workload: {workload}\n\n{table}")
    return sections


def spike_summary(records):
    spikes = sorted(
        (r for r in records if r["workload"] == "spike" and r.get("trace")),
        key=lambda r: r["algorithm"],
    )
    if not spikes:
        return ""
    lines = ["## Spike behavior", ""]
    for r in spikes:
        capacity = r["params"]["capacity"]
        spike_size = len(r["trace"])  # the whole trace is the spike burst
        granted = sum(1 for _t, ok in r["trace"] if ok)
        lines.append(
            f"- **{r['algorithm']}**: granted {granted} of the {spike_size} "
            f"spike requests (capacity {capacity}) after two idle windows "
            f"({granted / spike_size:.0%} admitted)."
        )
    lines += [
        "",
        "Algorithms that track burst state exactly admit precisely `capacity` "
        "here; deviations expose the fixed-window boundary burst and the "
        "sliding-counter interpolation approximation.",
    ]
    return "\n".join(lines)


def render(records):
    parts = ["# ratezoo benchmark comparison"]
    section = throughput_section(records)
    if section:
        parts.append(section)
    parts.extend(burst_sections(records))
    section = spike_summary(records)
    if section:
        parts.append(section)
    return "\n\n".join(parts) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m ratezoo.bench.report")
    parser.add_argument("paths", nargs="+", metavar="RESULTS_JSON")
    args = parser.parse_args(argv)
    try:
        records = load_records(args.paths)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2
    sys.stdout.write(render(records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
