---
id: TASK-002
title: Recorder instrumentation API
status: done
depends_on:
- TASK-001
runs:
- RUN-002
created: '2026-07-13T17:27:09Z'
---

## Description

Implement `tracedbg/recorder.py` with a `Recorder(path, agent="", task="")`
context manager wrapping `TraceWriter`:
- `begin_step(prompt: str, model: str)` — starts a step, records `started_at`
  (ISO 8601), assigns the next index; raises `RuntimeError` if a step is
  already open.
- `log_tool_call(name: str, args: dict, result)` — appends a ToolCall to the
  open step; raises `RuntimeError` if no step is open.
- `end_step(output: str)` — sets `ended_at`, writes the completed Step to disk
  immediately (flushed), closes the step.
- Exiting the context manager closes the underlying file; an unclosed open
  step is discarded (the trace on disk contains only completed steps).

Tests in `tests/test_recorder.py`: record two steps with tool calls, then
`load_trace` shows both with correct indices, tool calls, and outputs;
a step that was begun but not ended does not appear on disk; calling
`log_tool_call` outside a step raises.

## Acceptance criteria

- `pytest tests/test_recorder.py` passes
- After begin_step/log_tool_call/end_step twice, load_trace returns 2 steps with indices 0 and 1
- Simulating a crash (begin_step then closing without end_step) leaves a trace that load_trace parses successfully with only the completed steps
