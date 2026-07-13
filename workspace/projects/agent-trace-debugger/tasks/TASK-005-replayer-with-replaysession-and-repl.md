---
id: TASK-005
title: Replayer with ReplaySession and REPL
status: todo
depends_on:
- TASK-004
runs: []
created: '2026-07-13T17:27:09Z'
---

## Description

Implement `tracedbg/replay.py`:
- `format_step(step: Step) -> str`: pure renderer showing index, prompt,
  model, each tool call (name, args, result), and output.
- `ReplaySession(trace: Trace)`: cursor starting at step 0; `step()` advances
  (clamped at last step), `back()` retreats (clamped at 0), `goto(n)` jumps
  (raises `IndexError` if out of range), `current() -> Step`.
- `ReplayREPL(cmd.Cmd)`: commands `step`, `back`, `goto <n>`, `print`, `quit`;
  `print` outputs `format_step(session.current())`.

Tests in `tests/test_replay.py` on a fixture trace: step/back/goto/current
return the expected Steps; goto out of range raises; format_step output
contains the step's prompt, tool name, and output; drive the REPL via
`cmd.Cmd.onecmd` calls and assert printed content matches recorded step
contents exactly.

## Acceptance criteria

- `pytest tests/test_replay.py` passes
- ReplaySession on a 3-step fixture returns step 0, then step 1 after step(), then step 0 after back(), and goto(2) returns step index 2
- goto(99) on a 3-step trace raises IndexError
- REPL `print` output includes the exact recorded prompt and output strings
