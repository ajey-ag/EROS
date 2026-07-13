---
id: TASK-001
title: Scaffold tracedbg package with trace schema and JSONL store
status: in_progress
depends_on: []
runs:
- RUN-001
- RUN-003
created: '2026-07-13T17:27:09Z'
---

## Description

Create the project layout: `tracedbg/` package (`__init__.py`, `__main__.py` stub
that prints usage and exits 1), `tests/`, `docs/`, `pyproject.toml` (Python 3.11+,
no runtime deps, `pytest` as dev dep, optional `demo` extra for `anthropic`).

Implement `tracedbg/trace.py`:
- `SCHEMA_VERSION = 1`
- Dataclasses: `ToolCall(name: str, args: dict, result: object)`,
  `Step(index: int, prompt: str, model: str, tool_calls: list[ToolCall],
  output: str, started_at: str, ended_at: str)`,
  `TraceHeader(schema_version: int, created_at: str, agent: str, task: str)`,
  `Trace(header: TraceHeader, steps: list[Step])`.
- `TraceWriter(path)`: writes the header line on open, `append(step)` serializes
  one step per JSONL line and flushes immediately; usable as a context manager.
- `load_trace(path) -> Trace`: parses JSONL, validates the header has
  `type == "header"` and a known `schema_version`, tolerates unknown fields on
  records, raises `ValueError` on malformed lines or missing header.
- JSON records use `"type": "header"` / `"type": "step"` exactly as in the
  architecture's data model.

Write `docs/trace-format.md` documenting the JSONL schema, version 1 fields,
and the append-only / unknown-fields-tolerated rules.

Tests in `tests/test_trace.py`: round-trip write-then-load equals the original
steps; loading a file with an unknown extra field succeeds; loading a file with
no header raises `ValueError`; a partially written trace (header + 1 step, no
further lines) loads as a valid 1-step trace.

## Acceptance criteria

- `pip install -e .` succeeds and `python -c "import tracedbg.trace"` works
- `pytest tests/test_trace.py` passes
- Writing 3 steps via TraceWriter then load_trace returns a Trace with 3 Steps whose fields match what was written
- A trace file with an extra unknown key on a step line still loads without error
- docs/trace-format.md exists and documents the header and step record fields
