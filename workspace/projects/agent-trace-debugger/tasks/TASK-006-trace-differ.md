---
id: TASK-006
title: Trace differ
status: todo
depends_on:
- TASK-005
runs: []
created: '2026-07-13T17:27:09Z'
---

## Description

Implement `tracedbg/diff.py`:
- `StepDelta` dataclass: `index: int`, `changed_fields: dict[str, tuple]`
  mapping field name (prompt, model, tool_calls, output) to `(a_value, b_value)`.
- `DiffResult` dataclass: `first_divergence: int | None` (None when traces are
  identical; also handles differing lengths — the first index present in only
  one trace counts as divergence), `deltas: list[StepDelta]`.
- `diff_traces(a: Trace, b: Trace) -> DiffResult`: pure, compares only
  schema-defined step fields.
- `render_diff(result: DiffResult) -> str`: human-readable side-by-side of
  changed fields from the first divergence, reusing `format_step` conventions.

Tests in `tests/test_diff.py` covering the charter's three required cases with
constructed fixture pairs: identical traces (first_divergence is None,
deltas empty); traces diverging at step 0; traces diverging at a later step
(identical prefix, then changed output). Plus: trace A being a strict prefix
of trace B reports divergence at len(A).

## Acceptance criteria

- `pytest tests/test_diff.py` passes
- diff_traces on identical traces returns first_divergence None and no deltas
- diff_traces on the step-0 and later-step pairs returns the correct first_divergence index and the delta's changed_fields names exactly the fields that differ
- render_diff output contains both the old and new values of a changed output field
