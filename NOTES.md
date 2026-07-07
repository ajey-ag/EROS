# EROS Project Notes

Running log of the EROS build. One entry per work session lives in `docs/notes/`;
this file is the index and the current state of the world.

## Current state

- **Stage:** 4 — first project (rate-limiter-zoo) **shipped**: 8/8 tasks, 63 tests
  green, benchmark data + `WRITEUP.md` (the charter deliverable) done
- **Next up:** flagship #2 from the shortlist (IDEA-002 Prompt Regression CI or
  IDEA-026 Model Card Autogenerator); push repo to GitHub once the remote URL
  is provided (gh CLI not installed — user creating the repo manually)

## Roadmap position

| Stage | What | Status |
|---|---|---|
| 1 | Idea map: ~100 original ideas, scored across 5 axes | done (rescore committed 2026-07-07) |
| 2 | Shared infrastructure design (`docs/ARCHITECTURE.md`) | done |
| 3 | EROS orchestration pipeline (CLI, providers, dispatch) | working end to end |
| 4 | First 3 flagship projects built *through* EROS | 1/3 — rate-limiter-zoo shipped |
| 5 | Portfolio polish: blogs, demos, papers; web dashboard + desktop app | not started |

## Session journal

- [2026-07-07 — Session 1: bootstrap](docs/notes/2026-07-07-session-1.md) — repo scaffold, idea map, architecture doc, Stage 3 pipeline
- [2026-07-07 — Session 2: rate-limiter-zoo built end to end](docs/notes/2026-07-07-session-2.md) — TASK-001 verified, tasks 2–8 implemented, bench + report, gitignore fix

## Decisions log

- **2026-07-07** — CLI + file-based core first; web dashboard and personal desktop app deferred to Stage 5. All state is plain markdown/YAML in git.
- **2026-07-07** — Agent dispatch defaults to Claude Code headless (no extra billing); provider layer also supports Anthropic API, Ollama (local open-source), and OpenAI-compatible endpoints so the system is never locked to one vendor.
- **2026-07-07** — API keys only ever referenced by env-var name in config, never stored in the repo.
- **2026-07-08** — Headless dispatch pre-authorizes `python`/`pip`/`pytest` (`allowed_tools` in `.eros/config.toml`): an agent that cannot run its own verification produces unreviewable work (the RUN-001 lesson).

## Publishing to GitHub

```bash
# once `gh` is installed and authenticated:
gh repo create eros --private --source . --push
# or manually:
git remote add origin https://github.com/<you>/eros.git
git push -u origin main
```
