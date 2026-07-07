# Vision

## The problem

Building portfolio projects one at a time is linear: every project starts from zero —
new repo, new conventions, new glue code, new documentation debt. The knowledge gained
in project N barely transfers to project N+1, and the *process* (idea → design → tasks →
code → evaluation → writeup) is re-improvised every time.

## The bet

Build the **factory first**. EROS (Engineer's Research Operating System) is a single
workspace that owns the whole lifecycle of a research project:

1. Create a research idea
2. Have it decomposed into architecture automatically
3. Generate implementation tasks
4. Dispatch those tasks to coding agents
5. Review the resulting code
6. Track experiments and benchmarks
7. Visualize project evolution
8. Generate documentation continuously

Two compounding advantages:

- **Every subsequent project gets faster**, because the tooling, prompts, and accumulated
  knowledge improve with each one.
- **The system itself is the strongest portfolio artifact** — it demonstrates systems
  thinking, agent orchestration, and process design rather than isolated feature coding.

## The five stages

### Stage 1 — Idea map
A map of ~100 original project ideas, grouped into research domains, each scored 1–5 on
**originality, technical depth, interview value, startup potential, and reuse**.
Lives in `workspace/ideas/idea_map.yaml`; rendered to `docs/IDEA_MAP.md`.
Output: a ranked shortlist and 3 flagship candidates.

### Stage 2 — Shared infrastructure design
Design (not necessarily build) the engines every project will share: memory engine,
knowledge engine, agent orchestration, experiment runtime, visualization layer.
Lives in `docs/ARCHITECTURE.md`, with explicit "ships now" vs "ships later" boundaries.

### Stage 3 — The operating system
The working EROS pipeline: a Python CLI over a file-based data plane that orchestrates
LLM agents through the idea → architecture → tasks → dispatch → review → experiment
lifecycle. Provider-agnostic: Claude Code headless by default, with Anthropic API,
Ollama (local open-source models), and OpenAI-compatible endpoints as first-class options.

### Stage 4 — First flagship projects
Use EROS end-to-end to produce the first 3 flagship projects from the Stage 1 shortlist.
Each one stress-tests and improves the factory.

### Stage 5 — Compounding outputs
Refine flagships into portfolio-quality work: technical blogs, demos, possibly papers.
Build the visualization layer — a local web dashboard, then a personal desktop app
(the same engine behind CLI, web, and desktop; the desktop app is a thin shell over
the local server, tailored to a single user's workflow).

## Design principles

- **Files are the database.** Every artifact is markdown or YAML in git. EROS can be
  deleted and the state of every project remains readable.
- **The LLM is a component, not the system.** Prompts, providers, and models are
  swappable; the lifecycle and data model are the invariant.
- **Human on the promote/approve edges.** Agents decompose, implement, and review;
  the human decides what gets promoted and what ships.
- **Build the factory with the factory.** EROS's own future features become projects
  inside EROS as soon as the pipeline works.
