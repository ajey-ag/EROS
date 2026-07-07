# EROS — Engineer's Research Operating System

> Most people build applications. EROS is the factory that builds the next 20 projects.

EROS is a personal, file-based operating system for research-grade side projects. One workspace where you can:

1. **Capture** a research idea into a scored idea map (~100 ideas across 8 domains)
2. **Promote** the best ideas into project workspaces with charters
3. **Decompose** an idea into architecture automatically (LLM-driven)
4. **Plan** the architecture into ordered, dependency-aware implementation tasks
5. **Dispatch** those tasks to coding agents (Claude Code headless by default; Ollama / OpenAI-compatible / Anthropic API as alternatives)
6. **Review** the resulting code diffs with an LLM reviewer
7. **Track** experiments and benchmarks per project
8. **Document** everything continuously — every artifact is a markdown/YAML file in git

Everything lives in plain files under `workspace/`, so the entire state of every project — ideas, architectures, tasks, agent runs, reviews, experiments — is versioned, diffable, and readable without EROS installed.

## Quickstart

```bash
# from the eros/ repo root
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e .

eros --help
eros idea list                   # browse the idea map
eros idea show IDEA-001
eros idea promote IDEA-001       # create a project workspace
eros decompose <project-slug>    # LLM writes architecture.md
eros plan <project-slug>         # LLM writes TASK-*.md files
eros dispatch <project-slug> TASK-001   # agent implements the task
eros review <project-slug> RUN-001      # LLM reviews the diff
eros status                      # lifecycle dashboard
```

## Configuration

Provider settings live in `.eros/config.toml` (committed, no secrets) with machine-local
overrides in `.eros/config.local.toml` (gitignored). API keys are always referenced via
environment variables, never stored in files.

```toml
[provider]
default = "claude_code"          # claude_code | anthropic | ollama | openai_compat

[provider.claude_code]
binary = "claude"                # or full path to claude.exe

[provider.ollama]
base_url = "http://localhost:11434"
model = "qwen2.5-coder:7b"

[provider.openai_compat]
base_url = "https://api.groq.com/openai/v1"
model = "llama-3.3-70b-versatile"
api_key_env = "GROQ_API_KEY"

[provider.anthropic]
model = "claude-sonnet-5"
api_key_env = "ANTHROPIC_API_KEY"
```

## Repository map

| Path | What it is |
|---|---|
| `docs/VISION.md` | The concept and 5-stage roadmap |
| `docs/ARCHITECTURE.md` | Shared infrastructure design (memory, knowledge, orchestration, experiments, visualization) |
| `docs/IDEA_MAP.md` | Rendered master table of the idea map |
| `docs/notes/` | Dated session journals |
| `NOTES.md` | Running project log — start here |
| `src/eros/` | The CLI and engine |
| `workspace/ideas/idea_map.yaml` | Source of truth for all ideas |
| `workspace/projects/<slug>/` | One directory per promoted project: charter, architecture, tasks, runs, experiments |

## Lifecycle

```
IDEA ──promote──▶ PROJECT ──decompose──▶ ARCHITECTURE ──plan──▶ TASKS
                                                                  │
        REVIEW ◀──review── RUN ◀──────────dispatch────────────────┘
          │
          └──▶ approve / revise ──▶ EXPERIMENTS ──▶ docs, benchmarks
```
