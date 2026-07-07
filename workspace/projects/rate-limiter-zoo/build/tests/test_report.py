"""Tests for the markdown report generator."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from ratezoo.bench.report import main, render

FIXTURE = [
    {
        "algorithm": "token_bucket",
        "workload": "throughput",
        "params": {"capacity": 100, "rate": 100.0, "threads": 1},
        "ops_per_sec": 500000.0,
        "allowed": 120,
        "denied": 499880,
        "duration_s": 1.0,
        "trace": None,
    },
    {
        "algorithm": "fixed_window",
        "workload": "throughput",
        "params": {"capacity": 100, "rate": 100.0, "threads": 1},
        "ops_per_sec": 800000.0,
        "allowed": 130,
        "denied": 799870,
        "duration_s": 1.0,
        "trace": None,
    },
    {
        "algorithm": "token_bucket",
        "workload": "spike",
        "params": {"capacity": 2, "rate": 2.0, "threads": 1},
        "ops_per_sec": None,
        "allowed": 2,
        "denied": 2,
        "duration_s": 2.0,
        "trace": [[2.0, True], [2.0, True], [2.0, False], [2.0, False]],
    },
    {
        "algorithm": "fixed_window",
        "workload": "spike",
        "params": {"capacity": 2, "rate": 2.0, "threads": 1},
        "ops_per_sec": None,
        "allowed": 2,
        "denied": 2,
        "duration_s": 2.0,
        "trace": [[2.0, True], [2.0, True], [2.0, False], [2.0, False]],
    },
]


@pytest.fixture
def fixture_path(tmp_path):
    path = tmp_path / "results.json"
    path.write_text(json.dumps(FIXTURE), encoding="utf-8")
    return path


def test_report_contains_tables_and_numbers(fixture_path, capsys):
    assert main([str(fixture_path)]) == 0
    out = capsys.readouterr().out
    # markdown table header row + separator
    assert "| algorithm |" in out
    assert "| --- |" in out
    for name in ("token_bucket", "fixed_window"):
        assert name in out
    # throughput numbers
    assert "500,000" in out
    assert "800,000" in out
    # spike allowed/denied from the fixture
    assert "| token_bucket | 2 | 2 |" in out
    # spike summary derived from the trace
    assert "granted 2 of the 4 spike requests" in out


def test_render_merges_multiple_files(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps(FIXTURE[:2]), encoding="utf-8")
    b.write_text(json.dumps(FIXTURE[2:]), encoding="utf-8")
    from ratezoo.bench.report import load_records

    out = render(load_records([str(a), str(b)]))
    assert "Throughput" in out
    assert "spike" in out


def test_merge_deduplicates_identical_burst_records(tmp_path):
    # Two result files from runs differing only in throughput settings
    # contain byte-identical deterministic burst records.
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps(FIXTURE), encoding="utf-8")
    b.write_text(json.dumps(FIXTURE[2:]), encoding="utf-8")  # same spike records
    from ratezoo.bench.report import load_records

    records = load_records([str(a), str(b)])
    spikes = [r for r in records if r["workload"] == "spike"]
    assert len(spikes) == 2  # one per algorithm, not doubled


def test_exit_code_2_for_missing_file(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "ratezoo.bench.report", str(tmp_path / "nope.json")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "error" in proc.stderr.lower()


def test_exit_code_2_for_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "ratezoo.bench.report", str(bad)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
