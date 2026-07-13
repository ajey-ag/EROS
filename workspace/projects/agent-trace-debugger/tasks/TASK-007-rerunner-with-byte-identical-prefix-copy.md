---
id: TASK-007
title: Rerunner with byte-identical prefix copy
status: todo
depends_on:
- TASK-004
- TASK-006
runs: []
created: '2026-07-13T17:27:09Z'
---

## Description

Implement `tracedbg/rerun.py`:
- `rerun(trace_path, pin: int, prompt_override: str | None = None,
  model_override: str | None = None, model_client=None,
  out_path=None) -> Path`:
  1. Validate `pin` is a valid step index in the trace; raise `ValueError`
     otherwise.
  2. Copy the raw bytes of the original file's lines for the header and steps
     `0..pin-1` into the new trace file — no parse/re-serialize, preserving
     bytes exactly.
  3. Load steps `0..pin-1` as `prior_steps`; take step `pin`'s recorded prompt
     (or `prompt_override`) and model (or `model_override`) as the start input.
  4. Open a `Recorder` in append mode on the new file (add an append mode to
     Recorder/TraceWriter that skips writing a header and continues indices
     from the existing steps) and call `refagent.resume`.
  5. Default `out_path`: original name with a `.rerun` suffix before the
     extension.

Tests in `tests/test_rerun.py` using FakeModelClient: rerun a 3-step fixture
with `pin=2` and a prompt override — assert the new file's leading bytes equal
the original file's bytes up through step 1's line
(`original_bytes[:cut] == new_bytes[:cut]`); the new trace's step 2 prompt is
the override; step indices in the new trace are contiguous; pin out of range
raises ValueError.

## Acceptance criteria

- `pytest tests/test_rerun.py` passes
- The byte-prefix test asserting original_bytes[:cut] == new_bytes[:cut] passes for a rerun pinned at step 2
- The rerun trace loads via load_trace with contiguous step indices and its pinned step uses the overridden prompt
- rerun with pin >= number of steps raises ValueError
