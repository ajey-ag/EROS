# EROS Architecture

Stage 2 design document: the shared infrastructure every EROS-built project rides on.
Each engine is marked **[ships now]** (implemented in Stage 3) or **[ships later]**
(designed here, built in a future stage — usually *as an EROS project itself*).

## Design invariants

1. **Files are the database.** All state is markdown/YAML/JSONL in `workspace/`,
   versioned by git. Any tool (or human) can read and write it; EROS is just the
   convenient interface. This is the API contract between every engine below.
2. **The LLM is a component.** Providers, models, and prompts are swappable; the
   data model and lifecycle are the invariants.
3. **Human on the edges.** Agents decompose, implement, and review. The human
   promotes ideas, approves architectures, and accepts reviews.

## Data model

```
Idea (idea_map.yaml)
 └─ promote ──▶ Project (project.yaml + charter.md)
                 ├─ decompose ─▶ architecture.md
                 ├─ plan ──────▶ Task*  (tasks/TASK-nnn-slug.md, frontmatter = state)
                 │                └─ dispatch ─▶ Run* (runs/RUN-nnn.md)
                 │                                └─ review ─▶ verdict on Run,
                 │                                             status on Task
                 └─ experiments/log.jsonl  (Experiment*)
```

State machines:

- **Idea:** `mapped → promoted`
- **Task:** `todo → in_progress → needs_review → (done | needs_revision → in_progress …)`,
  plus `blocked` on failed runs or unmet dependencies.
- **Run:** `running → (succeeded | failed)`, review verdict `pending → (approve | revise)`.

File formats are the schema: task/run files are YAML frontmatter (machine state)
above a markdown body (human/agent content). Pydantic models in `src/eros/models.py`
validate the frontmatter on every read/write.

## Engines

### 1. Memory engine — [ships now: file store] / [later: recall]

**Now:** `store.py` — typed CRUD over the workspace tree. Sequential IDs per project
(`TASK-001`, `RUN-001`), frontmatter round-tripping, JSONL appends. Git provides
history, blame, and time-travel for free.

**Later:** a recall layer — embeddings over past architectures, reviews, and run
outcomes so decompose/plan prompts can cite precedent ("last time we chose httpx
over requests because…"). Candidate flagship tie-in: IDEA-006 (Decaying Memory Engine).

### 2. Knowledge engine — [ships now: idea map] / [later: cross-project retrieval]

**Now:** the idea map (scored YAML, rendered to markdown) plus per-project charters
and architecture docs. `eros idea render` keeps human-readable views derived, never
hand-edited.

**Later:** cross-project knowledge graph — which components were reused where, which
tech choices recurred, which review findings repeat. Feeds IDEA-096 (Knowledge Graph
Notebook) and the Stage 5 writeup generator.

### 3. Agent orchestration — [ships now]

The provider layer (`src/eros/providers/`) exposes two capabilities:

| Capability | Signature | Who implements it |
|---|---|---|
| `generate` | prompt → text | all providers |
| `agent_run` | task spec + cwd → AgentResult | claude_code natively; others degrade |

- **claude_code** (default): shells out to `claude -p --output-format json
  --permission-mode acceptEdits` inside the project's `build/` directory. Uses the
  existing Claude Code login — zero extra billing setup. Captures cost and turn count
  from the JSON envelope into the run record.
- **anthropic**: direct Messages API via env-var key. Text generation.
- **ollama**: local open-source models (qwen2.5-coder, llama3.x) via localhost REST.
- **openai_compat**: any `/v1/chat/completions` server — Groq, Together, LM Studio, vLLM.

**Degraded mode contract:** text-only providers can't edit files, so `agent_run`
falls back to generating a full-file patch with apply instructions; the run is
recorded with `agent_mode: false` so the ledger never lies about what happened.
This keeps the pipeline runnable offline on a laptop with only Ollama installed.

The pipeline stages (`src/eros/pipeline/`) are deliberately thin: each is
*prompt template + parser + file writes*, so improving EROS mostly means improving
prompts — which are visible in the repo and therefore reviewable like code.

Dispatch safety rails: dependency gate (a task with unmet `depends_on` won't
dispatch), agents are instructed to work only inside `build/`, and every run
snapshots `git status`/`diff --stat` scoped to that directory before/after.

### 4. Experiment runtime — [ships now: ledger] / [later: simulation runtime]

**Now:** `eros exp log/list` — append-only JSONL per project (timestamp, name,
numeric metrics, string params, notes). Enough to track benchmarks and compare
champion/challenger results.

**Later:** a runner that executes declared experiment commands, captures metrics
automatically, and diffs runs — plus the simulation runtime shared by the
simulation-domain ideas (IDEA-039..050). This should be built *through* EROS as an
early flagship exercise.

### 5. Visualization layer — [ships now: Phases A & B] / [later: richer views]

Every view renders from files the other engines already write — no
re-architecting was needed to add this layer on top of Stage 3.

1. **Phase A — local web dashboard [shipped]:** `src/eros/dashboard/api.py` is a
   FastAPI app exposing `workspace/` read-only as JSON (`/api/ideas`,
   `/api/projects`, `/api/projects/{slug}`, `/api/projects/{slug}/runs/{id}`),
   reusing `Store` untouched — the dashboard can never drift from what the CLI
   reports. `src/eros/dashboard/static/index.html` is a single self-contained
   page (no build step) with a project lifecycle board (stat tiles + status
   badges + run table) and an idea-map browser. Launch with `eros dashboard`
   (opens `http://127.0.0.1:8756`).
2. **Phase B — personal desktop app [shipped]:** `eros desktop` runs the same
   FastAPI app in a background thread and opens it in a native window via
   pywebview (`pip install -e .[desktop]`) — one window, no browser chrome, CLI
   and desktop share one engine and one static UI.
3. **Later:** run timelines/experiment charts beyond the current table view,
   project-evolution animation (IDEA-089), and a tray-icon/always-running mode
   for the desktop app graduate into this layer as needed.

## Directory contract (normative)

```
workspace/ideas/idea_map.yaml           # Idea[] + domains + scoring meta
workspace/projects/<slug>/project.yaml  # Project
workspace/projects/<slug>/charter.md    # human-owned: goals, success criteria
workspace/projects/<slug>/architecture.md
workspace/projects/<slug>/tasks/TASK-nnn-<slug>.md
workspace/projects/<slug>/runs/RUN-nnn.md
workspace/projects/<slug>/experiments/log.jsonl
workspace/projects/<slug>/build/        # agent working directory (the actual code)
```

A project graduates out of EROS by copying `build/` into its own repository; its
EROS directory stays behind as the permanent design-and-decision record.

## Security posture

- API keys only via environment variables named in config; `.eros/config.local.toml`
  (machine paths) is gitignored.
- Dispatched agents run with `acceptEdits` inside `build/` and are instructed not to
  leave it; run records make every change auditable via git.
- Nothing in `workspace/` is executed by EROS itself; it only reads/writes files and
  invokes the configured provider.
