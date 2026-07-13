---
id: TASK-003
title: ModelClient protocol with deterministic fake
status: todo
depends_on:
- TASK-001
runs: []
created: '2026-07-13T17:27:09Z'
---

## Description

Implement `tracedbg/model.py`:
- `ModelClient` as a `typing.Protocol` with `complete(prompt: str, model: str) -> str`.
- `FakeModelClient(script: list[str] | dict[str, str])`: returns scripted
  responses — either sequentially from a list, or keyed by exact prompt from a
  dict; raises `RuntimeError` when the list script is exhausted. Records every
  `(prompt, model)` call in a `.calls` list for test assertions.
- `AnthropicModelClient(api_key=None)`: thin wrapper that imports `anthropic`
  lazily inside `complete` and raises `ImportError` with a message pointing to
  the `demo` extra if the SDK is absent. No tests hit the network.

Tests in `tests/test_model.py`: FakeModelClient list-mode returns responses in
order and raises when exhausted; dict-mode returns by prompt; `.calls` records
inputs; importing `tracedbg.model` works without the `anthropic` package
installed.

## Acceptance criteria

- `pytest tests/test_model.py` passes
- FakeModelClient satisfies the ModelClient protocol (isinstance check with runtime_checkable or a mypy-style assignment test)
- `python -c "import tracedbg.model"` succeeds in an environment without the anthropic SDK
