"""plan: architecture.md -> ordered TASK-*.md files via an LLM."""

from __future__ import annotations

import re

import yaml

from ..models import Task
from ..providers.base import Provider
from ..store import Store

SYSTEM = """\
You are a tech lead turning an architecture document into a dependency-ordered task
list for a coding agent. Tasks must be small, independently verifiable, and specific.
"""

PROMPT = """\
Read the charter and architecture below and produce the implementation task list.

Output ONLY a fenced yaml block (```yaml ... ```) containing a list of 4-10 tasks:

```yaml
- title: short imperative title
  description: |
    What to build, precisely. File names, function signatures, behaviors.
  depends_on: []        # list of task NUMBERS (1-based) this depends on
  acceptance_criteria:
    - a concrete, checkable criterion
    - another one
```

Rules:
- Order tasks so dependencies always come earlier.
- Task 1 must scaffold the project (package layout, deps, entry point).
- Every task must be completable by a coding agent in one session.
- Acceptance criteria must be checkable by running code, not vibes.

CHARTER:
---
{charter}
---

ARCHITECTURE:
---
{architecture}
---
"""


def _extract_yaml(text: str) -> list[dict]:
    m = re.search(r"```ya?ml\s*\n(.*?)```", text, re.DOTALL)
    payload = m.group(1) if m else text
    data = yaml.safe_load(payload)
    if not isinstance(data, list) or not all(isinstance(t, dict) and "title" in t for t in data):
        raise ValueError("model did not return a valid yaml task list")
    return data


def plan(store: Store, slug: str, provider: Provider) -> list[Task]:
    pdir = store.project_dir(slug)
    charter = (pdir / "charter.md").read_text(encoding="utf-8")
    arch_file = pdir / "architecture.md"
    if not arch_file.exists():
        raise FileNotFoundError(f"architecture.md missing — run `eros decompose {slug}` first")
    architecture = arch_file.read_text(encoding="utf-8")

    raw = provider.generate(
        PROMPT.format(charter=charter, architecture=architecture), system=SYSTEM
    )
    try:
        items = _extract_yaml(raw)
    except Exception:
        # keep the raw output so a human can salvage it
        salvage = pdir / "tasks" / "_unparsed_plan.md"
        salvage.parent.mkdir(exist_ok=True)
        salvage.write_text(raw, encoding="utf-8")
        raise

    start = int(store.next_id(slug, "TASK").split("-")[1])
    tasks: list[Task] = []
    for offset, item in enumerate(items):
        num = start + offset
        deps = [f"TASK-{start + int(d) - 1:03d}" for d in item.get("depends_on") or []]
        task = Task(id=f"TASK-{num:03d}", title=str(item["title"]), depends_on=deps)
        criteria = "\n".join(f"- {c}" for c in item.get("acceptance_criteria") or [])
        body = (
            f"## Description\n\n{str(item.get('description', '')).strip()}\n\n"
            f"## Acceptance criteria\n\n{criteria}\n"
        )
        store.save_task(slug, task, body)
        tasks.append(task)
    return tasks
