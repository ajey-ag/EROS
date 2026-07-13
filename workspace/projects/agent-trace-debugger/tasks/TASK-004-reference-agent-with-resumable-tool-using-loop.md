---
id: TASK-004
title: Reference agent with resumable tool-using loop
status: todo
depends_on:
- TASK-002
- TASK-003
runs: []
created: '2026-07-13T17:27:09Z'
---

## Description

Implement `tracedbg/refagent.py` — a toy multi-step agent whose entire
inter-step state is derivable from recorded Steps (steps ARE the state):
- Built-in tools: `calculator(expression)` (safe arithmetic eval of + - * / on
  numbers, no `eval` of arbitrary code) and `word_count(text)`.
- `run(task: str, model_client, recorder, model="fake-1", max_steps=5)`:
  loop — build the step prompt from the task plus prior step outputs, call
  `model_client.complete`, parse the response for a tool directive (a simple
  line format like `TOOL calculator 2+2` or `FINAL <answer>`), execute the
  tool and log it via `recorder.log_tool_call`, record the step. Stop on
  `FINAL` or `max_steps`.
- `resume(prior_steps: list[Step], start_input: str, model_client, recorder,
  model, max_steps)`: reconstructs the prompt context purely from
  `prior_steps` and continues the loop starting with `start_input`, recording
  only the new steps.

Tests in `tests/test_refagent.py` using FakeModelClient: a scripted 3-step run
(two tool steps then FINAL) produces a 3-step trace with correct tool calls
and results; `resume` given the first 2 recorded steps produces steps that
continue with correct context (assert the prompt passed to the fake client
contains the prior outputs); commit resulting trace files under
`tests/fixtures/` for downstream tests.

## Acceptance criteria

- `pytest tests/test_refagent.py` passes
- Running run() with a scripted FakeModelClient produces a trace file with 3 steps whose tool_calls contain the calculator call with args and numeric result
- resume() with 2 prior steps records only the continuation steps and its first prompt (captured via FakeModelClient.calls) includes prior step outputs
- At least two fixture trace files exist under tests/fixtures/
