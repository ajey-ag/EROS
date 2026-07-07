"""dispatch: hand a task to a coding agent inside the project's build/ directory.

Records a RUN-*.md with what happened; captures a git snapshot of build/ before
and after so `eros review` can see exactly what the agent changed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..models import Run, RunStatus, Task, TaskStatus, now_iso
from ..providers.base import Provider
from ..store import Store

SPEC_TEMPLATE = """\
You are implementing one task of a larger project. Work ONLY inside the current
directory (the project's build/ folder). Do not modify anything outside it.

# Project charter
{charter}

# Architecture (relevant context)
{architecture}

# Your task: {task_id} — {title}
{body}

# Rules
- Implement the task completely, including any files it requires.
- Follow the architecture document's technology choices.
- If the acceptance criteria mention tests or runnable checks, make them pass.
- Finish with a short summary of what you created or changed.
"""


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return proc.stdout.strip()


def build_spec(store: Store, slug: str, task: Task, body: str) -> str:
    pdir = store.project_dir(slug)
    charter = (pdir / "charter.md").read_text(encoding="utf-8")
    arch = pdir / "architecture.md"
    architecture = arch.read_text(encoding="utf-8") if arch.exists() else "(not written yet)"
    return SPEC_TEMPLATE.format(
        charter=charter, architecture=architecture,
        task_id=task.id, title=task.title, body=body,
    )


def snapshot_changes(store: Store, slug: str) -> str:
    """Uncommitted changes (tracked + untracked) under this project's build/ dir."""
    rel = f"workspace/projects/{slug}/build"
    status = _git(store.root, "status", "--porcelain", "--", rel)
    diff = _git(store.root, "diff", "--stat", "--", rel)
    return f"### git status\n```\n{status or '(clean)'}\n```\n\n### diff stat\n```\n{diff or '(none)'}\n```"


def dispatch(store: Store, slug: str, task_id: str, provider: Provider) -> Run:
    task, body = store.get_task(slug, task_id)

    # dependency gate
    done = {t.id for t, _ in store.list_tasks(slug) if t.status == TaskStatus.done}
    unmet = [d for d in task.depends_on if d not in done]
    if unmet:
        raise RuntimeError(f"{task.id} has unmet dependencies: {', '.join(unmet)}")

    run = Run(
        id=store.next_id(slug, "RUN"),
        task_id=task.id,
        provider=provider.name,
        model=provider.model,
    )
    build_dir = store.project_dir(slug) / "build"
    spec = build_spec(store, slug, task, body)

    task.status = TaskStatus.in_progress
    task.runs.append(run.id)
    store.save_task(slug, task, body)

    result = provider.agent_run(spec, cwd=build_dir)

    run.status = RunStatus.succeeded if result.success else RunStatus.failed
    run.finished = now_iso()
    run.cost_usd = result.cost_usd
    run.num_turns = result.num_turns
    run.agent_mode = result.agent_mode

    sections = [f"# {run.id} — {task.id}: {task.title}", ""]
    if result.agent_mode:
        sections += ["## Agent summary", "", result.output, "", "## Changes", "",
                     snapshot_changes(store, slug)]
    else:
        sections += [
            "## Generated patch (degraded mode — provider cannot edit files)", "",
            "Apply the file blocks below to `build/` manually, then re-check acceptance criteria.",
            "", result.output,
        ]
    store.save_run(slug, run, "\n".join(sections) + "\n")

    task.status = TaskStatus.needs_review if result.success else TaskStatus.blocked
    store.save_task(slug, task, body)
    return run
