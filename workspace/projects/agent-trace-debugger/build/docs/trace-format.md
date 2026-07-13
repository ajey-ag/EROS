# Trace file format

A tracedbg trace is a single [JSON Lines](https://jsonlines.org/) file: one
JSON object per line, UTF-8 encoded. The file is **append-only** — records are
written in order and never rewritten, so a crash mid-run leaves a valid
partial trace that any consumer can still load.

Traces are the public contract of tracedbg. They are designed to be readable
without the tool installed: any JSON-capable program (or a human with a text
editor) can inspect one.

Current schema version: **1**.

## File layout

- **Line 1** must be a `header` record.
- **Every subsequent line** is a `step` record, one per completed agent step,
  in execution order.

## Header record (version 1)

```json
{"type": "header", "schema_version": 1, "created_at": "2026-07-13T10:00:00+00:00", "agent": "refagent", "task": "summarize report.txt"}
```

| Field            | Type   | Description                                        |
|------------------|--------|----------------------------------------------------|
| `type`           | string | Always `"header"`.                                 |
| `schema_version` | int    | Trace format version. This document describes `1`. |
| `created_at`     | string | ISO 8601 timestamp when recording started.         |
| `agent`          | string | Name of the agent that produced the trace.         |
| `task`           | string | The task/goal the agent was given.                 |

## Step record (version 1)

```json
{"type": "step", "index": 0, "prompt": "What is 2+2?", "model": "fake-model", "tool_calls": [{"name": "calculator", "args": {"expression": "2+2"}, "result": 4}], "output": "The answer is 4.", "started_at": "2026-07-13T10:00:01+00:00", "ended_at": "2026-07-13T10:00:02+00:00"}
```

| Field        | Type   | Description                                             |
|--------------|--------|---------------------------------------------------------|
| `type`       | string | Always `"step"`.                                        |
| `index`      | int    | Zero-based step number within the trace.                |
| `prompt`     | string | The input/prompt given to the model for this step.      |
| `model`      | string | Identifier of the model used for this step.             |
| `tool_calls` | array  | Tool invocations made during this step, in order.       |
| `output`     | string | The model's resulting output for this step.             |
| `started_at` | string | ISO 8601 timestamp when the step began.                 |
| `ended_at`   | string | ISO 8601 timestamp when the step completed.             |

### Tool call object

| Field    | Type   | Description                                    |
|----------|--------|------------------------------------------------|
| `name`   | string | Tool name (e.g. `"calculator"`).               |
| `args`   | object | Arguments the tool was invoked with.           |
| `result` | any    | The value the tool returned (any JSON value).  |

## Compatibility rules

- **Append-only.** Writers only ever add lines; existing lines are never
  modified. This is what makes the rerunner's byte-identical-prefix guarantee
  possible: it copies raw lines rather than re-serializing.
- **Unknown fields are tolerated.** Loaders must ignore fields they don't
  recognize on any record. Future versions may add fields (e.g. token counts,
  errors) without breaking version-1 consumers.
- **Unknown record types are skipped.** A loader encountering a `type` other
  than `header` or `step` (after the header) skips the line.
- **Version changes.** Any change that removes or reinterprets a version-1
  field requires bumping `schema_version` and documenting the new version
  here. Loaders reject files whose `schema_version` they don't know.
