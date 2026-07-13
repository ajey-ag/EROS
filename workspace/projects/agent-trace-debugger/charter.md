# Agent Trace Debugger

**Promoted from:** IDEA-001 · **Domain:** LLM & Agent Infrastructure · **Score:** 23/25

## Pitch

Record, replay, and diff multi-step agent executions — step through tool calls like a debugger, pin a failing step, and re-run from it with a modified prompt or model.

## Goals

- Record a multi-step agent execution (sequence of steps, each with a prompt/input,
  model used, tool calls made with their arguments and results, and the resulting
  output) to a structured, append-only trace file on disk.
- Provide a CLI to **replay** a stored trace step-by-step like a debugger: step
  forward/back, jump to a step index, print the full state (prompt, tool calls,
  output) at that step.
- Provide a **diff** command that compares two traces (e.g. before/after a prompt
  edit or model swap) and highlights where their step sequences diverge — first
  differing step, and a side-by-side of what changed in inputs/outputs from there.
- Provide a **pin + rerun** command: pin a specific step in a trace, optionally
  override its prompt text or model, and re-execute the agent from that step
  forward using the recorded prior steps as fixed context — without redoing
  earlier (already-correct) steps.
- Ship a small reference "agent" (a toy multi-step tool-using loop) purely so the
  recorder/replayer/differ/rerunner can be demonstrated and tested end-to-end
  without depending on a live LLM API for every test.

## Success criteria

- `python -m tracedbg record <script>` produces a trace file capturing every step
  (input, tool calls + results, output) for the reference agent.
- `python -m tracedbg replay <trace>` supports step/back/goto/print and matches the
  recorded step contents exactly.
- `python -m tracedbg diff <traceA> <traceB>` correctly identifies the first
  divergent step on at least 3 constructed test-case pairs (identical traces,
  traces diverging at step 1, traces diverging at a later step).
- `python -m tracedbg rerun <trace> --pin <n> [--prompt ...] [--model ...]`
  reruns only from step `n` onward and produces a new trace whose steps 0..n-1
  are byte-identical to the original.
- `pytest` green covering record/replay/diff/rerun on the reference agent.
- Real LLM calls are only required for the reference agent demo, not for the core
  record/replay/diff/rerun logic, which must be fully testable with fixtures.

## Constraints

- Python-first; runs on a single Windows laptop without cloud infrastructure.
- Keep external dependencies minimal and justified.
- Trace format must be a documented, versioned, human-readable schema (e.g. JSONL)
  so traces remain inspectable without this tool.
