---
id: TASK-008
title: CLI wiring and end-to-end verification
status: todo
depends_on:
- TASK-005
- TASK-006
- TASK-007
runs: []
created: '2026-07-13T17:27:09Z'
---

## Description

Implement `tracedbg/__main__.py` with `argparse` subcommands, using the
FakeModelClient by default and the Anthropic client when `--live` is passed
or `TRACEDBG_LIVE=1` is set:
- `record <task> [--out PATH] [--model NAME] [--script FILE]`: runs the
  reference agent on the task, recording to PATH (default under `./traces/`);
  `--script` supplies a JSON list of fake responses so demos are offline.
- `replay <trace>`: launches the ReplayREPL.
- `diff <traceA> <traceB>`: prints `render_diff`; exit code 0 if identical,
  1 if divergent.
- `rerun <trace> --pin N [--prompt TEXT] [--model NAME] [--out PATH]`: calls
  `rerun.rerun` and prints the new trace path.

Tests in `tests/test_cli.py` invoking `python -m tracedbg ...` via
`subprocess` with fixture traces and a script file: record produces a
loadable trace; diff of identical traces exits 0 and of divergent traces
exits 1 with divergence info on stdout; rerun prints the new path and the
file passes the byte-prefix check; replay REPL accepts `print` then `quit`
when fed via stdin. Update the project README with usage examples for all
four subcommands and run the full suite.

## Acceptance criteria

- `pytest` (full suite) passes
- `python -m tracedbg record "add 2 and 2" --script <file> --out t.jsonl` exits 0 and t.jsonl loads via load_trace
- `python -m tracedbg diff a.jsonl a.jsonl` exits 0; diff of two divergent fixtures exits 1 and prints the first divergent step index
- `python -m tracedbg rerun <fixture> --pin 2 --prompt "new"` produces a file whose prefix bytes match the original
- Piping "print\nquit\n" into `python -m tracedbg replay <fixture>` prints the recorded step 0 prompt and exits 0
