"""File-based persistence over the workspace/ data plane.

Layout:
    workspace/ideas/idea_map.yaml
    workspace/projects/<slug>/
        project.yaml
        charter.md
        architecture.md
        tasks/TASK-001-slug.md      (YAML frontmatter + markdown body)
        runs/RUN-001.md
        experiments/log.jsonl
        build/                      (working directory for dispatched agents)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .models import Experiment, Idea, Project, Run, Task

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def find_root(start: Path | None = None) -> Path:
    """Walk upward from cwd to find the repo root (contains workspace/ideas)."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "workspace" / "ideas" / "idea_map.yaml").exists():
            return candidate
    raise FileNotFoundError(
        "Not inside an EROS workspace (no workspace/ideas/idea_map.yaml found "
        "in this directory or any parent). Run from the eros repo."
    )


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:48]


# ── markdown + frontmatter ──────────────────────────────────────────────────

def read_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    return meta, text[m.end():]


def write_frontmatter(path: Path, meta: dict, body: str) -> None:
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{fm}\n---\n\n{body.lstrip()}", encoding="utf-8")


class Store:
    def __init__(self, root: Path | None = None):
        self.root = root or find_root()
        self.workspace = self.root / "workspace"
        self.ideas_file = self.workspace / "ideas" / "idea_map.yaml"
        self.projects_dir = self.workspace / "projects"

    # ── ideas ───────────────────────────────────────────────────────────

    def load_idea_map(self) -> dict:
        return yaml.safe_load(self.ideas_file.read_text(encoding="utf-8"))

    def save_idea_map(self, data: dict) -> None:
        header = (
            "# EROS Idea Map — source of truth "
            "(rendered to docs/IDEA_MAP.md via `eros idea render`)\n"
        )
        body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
        self.ideas_file.write_text(header + body, encoding="utf-8")

    def load_ideas(self) -> list[Idea]:
        return [Idea(**raw) for raw in self.load_idea_map()["ideas"]]

    def domains(self) -> dict[str, str]:
        return {d["key"]: d["name"] for d in self.load_idea_map()["domains"]}

    def get_idea(self, idea_id: str) -> Idea:
        for idea in self.load_ideas():
            if idea.id.lower() == idea_id.lower():
                return idea
        raise KeyError(f"{idea_id} not found in idea map")

    def update_idea(self, idea: Idea) -> None:
        data = self.load_idea_map()
        for i, raw in enumerate(data["ideas"]):
            if raw["id"] == idea.id:
                data["ideas"][i] = idea.model_dump(exclude_defaults=False)
                break
        else:
            data["ideas"].append(idea.model_dump())
        self.save_idea_map(data)

    # ── projects ────────────────────────────────────────────────────────

    def project_dir(self, slug: str) -> Path:
        d = self.projects_dir / slug
        if not (d / "project.yaml").exists():
            raise KeyError(f"project '{slug}' not found under workspace/projects/")
        return d

    def list_projects(self) -> list[Project]:
        out = []
        if self.projects_dir.exists():
            for pf in sorted(self.projects_dir.glob("*/project.yaml")):
                out.append(Project(**yaml.safe_load(pf.read_text(encoding="utf-8"))))
        return out

    def get_project(self, slug: str) -> Project:
        pf = self.project_dir(slug) / "project.yaml"
        return Project(**yaml.safe_load(pf.read_text(encoding="utf-8")))

    def create_project(self, project: Project, charter_body: str) -> Path:
        d = self.projects_dir / project.slug
        if d.exists():
            raise FileExistsError(f"project '{project.slug}' already exists")
        for sub in ["tasks", "runs", "experiments", "build"]:
            (d / sub).mkdir(parents=True)
        (d / "project.yaml").write_text(
            yaml.safe_dump(project.model_dump(), sort_keys=False), encoding="utf-8"
        )
        (d / "charter.md").write_text(charter_body, encoding="utf-8")
        (d / "build" / ".gitkeep").write_text("", encoding="utf-8")
        return d

    # ── tasks ───────────────────────────────────────────────────────────

    def _task_path(self, slug: str, task_id: str) -> Path:
        matches = list((self.project_dir(slug) / "tasks").glob(f"{task_id.upper()}*.md"))
        if not matches:
            raise KeyError(f"{task_id} not found in project '{slug}'")
        return matches[0]

    def list_tasks(self, slug: str) -> list[tuple[Task, str]]:
        out = []
        for tf in sorted((self.project_dir(slug) / "tasks").glob("TASK-*.md")):
            meta, body = read_frontmatter(tf)
            out.append((Task(**meta), body))
        return out

    def get_task(self, slug: str, task_id: str) -> tuple[Task, str]:
        meta, body = read_frontmatter(self._task_path(slug, task_id))
        return Task(**meta), body

    def next_id(self, slug: str, kind: str) -> str:
        """kind: 'TASK' or 'RUN' — next sequential id within a project."""
        sub = "tasks" if kind == "TASK" else "runs"
        nums = [
            int(m.group(1))
            for f in (self.project_dir(slug) / sub).glob(f"{kind}-*.md")
            if (m := re.match(rf"{kind}-(\d+)", f.name))
        ]
        return f"{kind}-{(max(nums) + 1) if nums else 1:03d}"

    def save_task(self, slug: str, task: Task, body: str) -> Path:
        path = self.project_dir(slug) / "tasks" / f"{task.id}-{slugify(task.title)}.md"
        # if the task already exists under this id, reuse its filename
        existing = list((self.project_dir(slug) / "tasks").glob(f"{task.id}*.md"))
        if existing:
            path = existing[0]
        write_frontmatter(path, task.model_dump(mode="json"), body)
        return path

    # ── runs ────────────────────────────────────────────────────────────

    def list_runs(self, slug: str) -> list[tuple[Run, str]]:
        out = []
        for rf in sorted((self.project_dir(slug) / "runs").glob("RUN-*.md")):
            meta, body = read_frontmatter(rf)
            out.append((Run(**meta), body))
        return out

    def get_run(self, slug: str, run_id: str) -> tuple[Run, str]:
        path = self.project_dir(slug) / "runs" / f"{run_id.upper()}.md"
        if not path.exists():
            raise KeyError(f"{run_id} not found in project '{slug}'")
        meta, body = read_frontmatter(path)
        return Run(**meta), body

    def save_run(self, slug: str, run: Run, body: str) -> Path:
        path = self.project_dir(slug) / "runs" / f"{run.id}.md"
        write_frontmatter(path, run.model_dump(mode="json"), body)
        return path

    # ── experiments ─────────────────────────────────────────────────────

    def log_experiment(self, slug: str, exp: Experiment) -> None:
        path = self.project_dir(slug) / "experiments" / "log.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(exp.model_dump()) + "\n")

    def list_experiments(self, slug: str) -> list[Experiment]:
        path = self.project_dir(slug) / "experiments" / "log.jsonl"
        if not path.exists():
            return []
        return [
            Experiment(**json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
