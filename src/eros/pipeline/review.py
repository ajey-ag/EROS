"""review: LLM code review of what a run changed in build/.

Verdict APPROVE marks the task done; REVISE marks it needs_revision with notes
appended to the run record.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..models import ReviewVerdict, TaskStatus
from ..providers.base import Provider
from ..store import Store

SYSTEM = """\
You are a rigorous but pragmatic code reviewer. You review a coding agent's changes
against a task's acceptance criteria. You care about: correctness, whether the
acceptance criteria are actually met, and glaring design problems. You do not
nitpick style.
"""

PROMPT = """\
Review this change set.

# Task ({task_id}: {title})
{task_body}

# What changed (git diff of tracked files)
```diff
{diff}
```

# New untracked files
{untracked}

Respond in EXACTLY this format:

VERDICT: APPROVE or REVISE
SUMMARY: one sentence
FINDINGS:
- finding 1 (or "none")
- finding 2
"""

MAX_DIFF_CHARS = 60_000
MAX_FILE_CHARS = 6_000


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return proc.stdout


def collect_changes(store: Store, slug: str) -> tuple[str, str]:
    rel = f"workspace/projects/{slug}/build"
    diff = _git(store.root, "diff", "--", rel)[:MAX_DIFF_CHARS]
    untracked_list = _git(
        store.root, "ls-files", "--others", "--exclude-standard", "--", rel
    ).splitlines()
    parts = []
    for f in untracked_list[:40]:
        path = store.root / f
        try:
            content = path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_CHARS]
        except OSError:
            content = "(unreadable)"
        parts.append(f"FILE: {f}\n```\n{content}\n```")
    return diff, "\n\n".join(parts) or "(none)"


def review(store: Store, slug: str, run_id: str, provider: Provider) -> ReviewVerdict:
    run, run_body = store.get_run(slug, run_id)
    task, task_body = store.get_task(slug, run.task_id)
    diff, untracked = collect_changes(store, slug)

    reply = provider.generate(
        PROMPT.format(
            task_id=task.id, title=task.title, task_body=task_body,
            diff=diff or "(no tracked-file changes)", untracked=untracked,
        ),
        system=SYSTEM,
    )
    verdict = (
        ReviewVerdict.approve
        if "VERDICT: APPROVE" in reply.upper().replace("**", "")
        else ReviewVerdict.revise
    )

    run.review = verdict
    store.save_run(slug, run, run_body + f"\n## Review ({provider.name})\n\n{reply.strip()}\n")

    task.status = TaskStatus.done if verdict == ReviewVerdict.approve else TaskStatus.needs_revision
    store.save_task(slug, task, task_body)
    return verdict
