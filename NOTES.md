# EROS Project Notes

Running log of the EROS build. One entry per work session lives in `docs/notes/`;
this file is the index and the current state of the world.

## Current state

- **Stage:** 5 — dashboard + desktop app shipped; portfolio index started.
  rate-limiter-zoo remains the only fully shipped flagship; agent-trace-debugger
  and forecast-backtesting-engine are mid-build (see `eros status` or `eros
  dashboard` for live task/run state — both are being worked in parallel
  sessions, don't assume the counts here stay current).
- **Next up:** finish agent-trace-debugger and forecast-backtesting-engine
  (TASK-003 onward on both), then backfill their `docs/portfolio/` entries.

## Roadmap position

| Stage | What | Status |
|---|---|---|
| 1 | Idea map: ~100 original ideas, scored across 5 axes | done (rescore committed 2026-07-07) |
| 2 | Shared infrastructure design (`docs/ARCHITECTURE.md`) | done |
| 3 | EROS orchestration pipeline (CLI, providers, dispatch) | working end to end |
| 4 | First 3 flagship projects built *through* EROS | 1/3 shipped (rate-limiter-zoo); 2 in progress |
| 5 | Portfolio polish: blogs, demos, papers; web dashboard + desktop app | dashboard + desktop shipped; writeups partial |

## Session journal

- [2026-07-07 — Session 1: bootstrap](docs/notes/2026-07-07-session-1.md) — repo scaffold, idea map, architecture doc, Stage 3 pipeline
- [2026-07-07 — Session 2: rate-limiter-zoo built end to end](docs/notes/2026-07-07-session-2.md) — TASK-001 verified, tasks 2–8 implemented, bench + report, gitignore fix
- [2026-07-13 — Session 3: binary fix, dashboard + desktop app](docs/notes/2026-07-13-session-3.md) — claude.exe auto-discovery, forecast-backtesting-engine started, FastAPI dashboard + pywebview desktop shell, portfolio index

## Decisions log

- **2026-07-07** — CLI + file-based core first; web dashboard and personal desktop app deferred to Stage 5. All state is plain markdown/YAML in git.
- **2026-07-07** — Agent dispatch defaults to Claude Code headless (no extra billing); provider layer also supports Anthropic API, Ollama (local open-source), and OpenAI-compatible endpoints so the system is never locked to one vendor.
- **2026-07-07** — API keys only ever referenced by env-var name in config, never stored in the repo.
- **2026-07-08** — Headless dispatch pre-authorizes `python`/`pip`/`pytest` (`allowed_tools` in `.eros/config.toml`): an agent that cannot run its own verification produces unreviewable work (the RUN-001 lesson).
- **2026-07-13** — `claude_code` provider auto-discovers the newest installed VS Code extension's bundled `claude.exe` instead of relying on a version-pinned path in `config.local.toml` — the extension auto-updates in place, so a pinned path goes stale (broke decompose on agent-trace-debugger). `binary = "claude"` (default) now triggers discovery; an explicit path in config still overrides it.
- **2026-07-13** — Dashboard and desktop app are read-only views over `Store`, not a separate write path — they can never drift from `eros status`/CLI state, and no new persistence format was introduced for Stage 5.

## GitHub

Published 2026-07-08: https://github.com/ajey-ag/EROS (`origin`, `main` tracking).
