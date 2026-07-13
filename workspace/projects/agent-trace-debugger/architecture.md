# Architecture: Agent Trace Debugger

## Overview

The system is a single Python package, `tracedbg`, organized around one central artifact: a versioned JSONL trace file. Everything else — recording, replaying, diffing, rerunning — is a small module that either produces or consumes that file. The trace format is defined first and treated as the public contract: any tool (or a human with a text editor) can read a trace without `tracedbg` installed. This keeps the modules decoupled: the differ never imports the recorder; both just speak "trace."

Recording works by instrumentation, not inference. The reference agent (and any future agent) calls an explicit `Recorder` API at step boundaries (`begin_step`, `log_tool_call`, `end_step`), and the recorder appends one JSON object per step to disk immediately, so a crash mid-run still leaves a valid partial trace. Replay and diff are pure functions over parsed traces — no LLM, no I/O beyond reading files — which makes them trivially testable with fixture files. Rerun is the only component that touches execution: it reconstructs agent state from steps `0..n-1` verbatim, then hands control back to the agent loop with optional prompt/model overrides.

The design deliberately avoids a plugin system, a database, or async execution. One laptop, one process, files on disk, and a `cmd`-style REPL for the interactive replayer. The LLM boundary is a single `ModelClient` protocol with a deterministic fake implementation, so the entire test suite runs offline; a real API-backed client is a demo-only extra.

## Components

1. **Trace schema & store (`tracedbg/trace.py`)**
   Responsibility: define the versioned step record (dataclasses), serialize/deserialize to JSONL, validate on load, and provide append-only writing.
   Key interfaces: `Step` dataclass (index, input/prompt, model, `list[ToolCall]` with args + results, output, timestamps), `TraceWriter.append(step)`, `load_trace(path) -> Trace`, `SCHEMA_VERSION` constant, plus a `docs/trace-format.md` documenting the schema.

2. **Recorder (`tracedbg/recorder.py`)**
   Responsibility: instrumentation API an agent calls to record its execution; flushes each completed step to the `TraceWriter` immediately.
   Key interfaces: `Recorder(path)` context manager; `begin_step(prompt, model)`, `log_tool_call(name, args, result)`, `end_step(output)`.

3. **Model client abstraction (`tracedbg/model.py`)**
   Responsibility: isolate the LLM boundary so core logic never needs a live API.
   Key interfaces: `ModelClient` protocol with `complete(prompt, model) -> str`; `FakeModelClient` (scripted/deterministic responses for tests); `AnthropicModelClient` (thin, demo-only).

4. **Reference agent (`tracedbg/refagent.py`)**
   Responsibility: a toy multi-step tool-using loop (2–3 built-in tools like calculator and word-count) that takes a `ModelClient` and a `Recorder`, demonstrating end-to-end recording. Crucially, it exposes a "resume" entry point: given a list of prior `Step`s as fixed context plus a starting step spec, continue the loop.
   Key interfaces: `run(task, model_client, recorder)`, `resume(prior_steps, start_input, model_client, recorder)`.

5. **Replayer (`tracedbg/replay.py`)**
   Responsibility: interactive step-through of a stored trace.
   Key interfaces: `ReplaySession(trace)` with `step()`, `back()`, `goto(n)`, `current() -> Step`; a `cmd.Cmd`-based REPL wrapping it; a pure `format_step(step) -> str` renderer shared with the differ.

6. **Differ (`tracedbg/diff.py`)**
   Responsibility: compare two traces; find the first divergent step and render a side-by-side of changed fields (prompt, model, tool calls, output) from that point.
   Key interfaces: `diff_traces(a, b) -> DiffResult` (pure, returns structured result: `first_divergence: int | None`, per-step field deltas); `render_diff(result) -> str`.

7. **Rerunner (`tracedbg/rerun.py`)**
   Responsibility: pin step `n`, copy steps `0..n-1` byte-identically into a new trace file, apply prompt/model overrides to step `n`'s input, and invoke `refagent.resume` with a fresh `Recorder` appending to the new trace.
   Key interfaces: `rerun(trace_path, pin, prompt_override, model_override, model_client) -> new_trace_path`.

8. **CLI (`tracedbg/__main__.py`)**
   Responsibility: `argparse`-based entry point wiring the four subcommands (`record`, `replay`, `diff`, `rerun`) to the modules above; selects fake vs. real model client via a flag/env var.
   Key interfaces: `python -m tracedbg <subcommand> ...` exactly as specified in the charter.

## Data model

**Trace file** — one file per execution, JSONL, append-only:

- Line 1: header record — `{"type": "header", "schema_version": 1, "created_at": ..., "agent": ..., "task": ...}`.
- Subsequent lines: step records — `{"type": "step", "index": n, "prompt": str, "model": str, "tool_calls": [{"name": str, "args": {...}, "result": ...}], "output": str, "started_at": ..., "ended_at": ...}`.

**In-memory entities** — plain dataclasses mirroring the JSON: `TraceHeader`, `Step`, `ToolCall`, and `Trace` (header + `list[Step]`). `DiffResult` holds `first_divergence` and a list of `StepDelta` (step index + changed-field map). No database; traces live wherever the user points the CLI (default `./traces/`). The byte-identical rerun guarantee is met by copying the original file's raw lines `0..n-1` (header + steps) rather than re-serializing parsed objects.

## Technology choices

- **Python 3.11+** — charter mandate; dataclasses and `typing.Protocol` cover all modeling needs.
- **Standard library only for core** (`json`, `argparse`, `cmd`, `dataclasses`, `difflib`) — every core feature maps to a stdlib module; zero-dependency core keeps the Windows laptop install trivial.
- **JSONL trace format** — human-readable, append-only-friendly (crash-safe partial traces), line-per-step diffs cleanly with any tool.
- **`pytest`** — the charter's stated test runner; fixtures make offline trace tests natural.
- **`anthropic` SDK (optional extra)** — only for the live demo of the reference agent; installed via `pip install tracedbg[demo]`-style extra so tests never need it.

## Build order

1. **Trace schema & store** — everything else consumes or produces traces; freezing the format first prevents rework, and the fixture files for all later tests come from here.
2. **Recorder** — thin layer over the writer; unblocks producing real traces.
3. **Model client abstraction** — the `FakeModelClient` must exist before the agent so the agent is testable from day one.
4. **Reference agent** — with recorder + fake model in hand, generates realistic end-to-end traces that seed fixtures for replay/diff/rerun tests.
5. **Replayer** — pure consumer of traces; its `format_step` renderer is reused by the differ, so it comes first of the two.
6. **Differ** — pure function over two traces; straightforward once fixtures exist for the three required divergence cases.
7. **Rerunner** — depends on nearly everything (trace copy, agent resume, model client, recorder), so it goes last among core modules.
8. **CLI** — pure wiring; built incrementally as each subcommand's backing module lands, finalized last.

## Risks

1. **Byte-identical prefix guarantee breaks under re-serialization.** JSON key ordering, float formatting, or Unicode escaping can silently alter bytes. *Mitigation:* the rerunner copies raw lines from the original file for steps `0..n-1` instead of parsing and re-dumping; a dedicated test asserts `original_bytes[:cut] == new_bytes[:cut]`.

2. **Resume semantics are ambiguous — the agent's hidden state may not be fully captured in steps.** If the reference agent keeps conversation state beyond what's recorded, `resume` can't faithfully reconstruct step `n`'s context. *Mitigation:* design the reference agent so its entire inter-step state is derivable from recorded steps (steps are the state), and document this as a requirement for any agent wanting rerun support.

3. **Schema evolution stranding old traces.** Adding fields later (e.g., token counts, errors) could break loaders or diffs. *Mitigation:* version field in the header from day one, loader tolerates unknown fields, differ compares only schema-defined fields; `docs/trace-format.md` records each version's changes.
