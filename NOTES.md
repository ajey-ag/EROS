# EROS Project Notes

Running log of the EROS build. One entry per work session lives in `docs/notes/`;
this file is the index and the current state of the world.

## Current state

- **Stage:** 3 (working pipeline) — in progress this session
- **Next up:** Stage 4 — use EROS to produce the first flagship project from the idea map shortlist

## Roadmap position

| Stage | What | Status |
|---|---|---|
| 1 | Idea map: ~100 original ideas, scored across 5 axes | in progress |
| 2 | Shared infrastructure design (`docs/ARCHITECTURE.md`) | in progress |
| 3 | EROS orchestration pipeline (CLI, providers, dispatch) | in progress |
| 4 | First 3 flagship projects built *through* EROS | not started |
| 5 | Portfolio polish: blogs, demos, papers; web dashboard + desktop app | not started |

## Session journal

- [2026-07-07 — Session 1: bootstrap](docs/notes/2026-07-07-session-1.md) — repo scaffold, idea map, architecture doc, Stage 3 pipeline

## Decisions log

- **2026-07-07** — CLI + file-based core first; web dashboard and personal desktop app deferred to Stage 5. All state is plain markdown/YAML in git.
- **2026-07-07** — Agent dispatch defaults to Claude Code headless (no extra billing); provider layer also supports Anthropic API, Ollama (local open-source), and OpenAI-compatible endpoints so the system is never locked to one vendor.
- **2026-07-07** — API keys only ever referenced by env-var name in config, never stored in the repo.

## Publishing to GitHub

```bash
# once `gh` is installed and authenticated:
gh repo create eros --private --source . --push
# or manually:
git remote add origin https://github.com/<you>/eros.git
git push -u origin main
```
