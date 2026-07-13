"""Read-only JSON API over the EROS workspace, backing the local dashboard.

Deliberately thin: every endpoint reuses Store as-is (the same engine the CLI
uses), so the dashboard can never drift from what `eros status` shows.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from ..ideas import rank
from ..models import TaskStatus
from ..store import Store

STATIC_DIR = Path(__file__).parent / "static"


def create_app(store: Store | None = None) -> FastAPI:
    store = store or Store()
    app = FastAPI(title="EROS Dashboard")

    @app.get("/api/ideas")
    def list_ideas(domain: str | None = None, flagship: bool = False):
        items = rank(store.load_ideas())
        if domain:
            items = [i for i in items if i.domain == domain]
        if flagship:
            items = [i for i in items if i.flagship_candidate]
        domains = store.domains()
        return [
            {**i.model_dump(), "total": i.total, "domain_name": domains.get(i.domain, i.domain)}
            for i in items
        ]

    @app.get("/api/domains")
    def list_domains():
        return store.domains()

    @app.get("/api/projects")
    def list_projects():
        out = []
        for proj in store.list_projects():
            tasks = store.list_tasks(proj.slug)
            runs = store.list_runs(proj.slug)
            done = sum(1 for t, _ in tasks if t.status == TaskStatus.done)
            has_arch = (store.project_dir(proj.slug) / "architecture.md").exists()
            if not has_arch:
                stage = "chartered"
            elif not tasks:
                stage = "decomposed"
            elif done == len(tasks) and tasks:
                stage = "complete"
            else:
                stage = "building"
            total_cost = sum(r.cost_usd or 0 for r, _ in runs)
            out.append({
                "slug": proj.slug, "title": proj.title, "idea_id": proj.idea_id,
                "created": proj.created, "stage": stage,
                "tasks_done": done, "tasks_total": len(tasks),
                "runs_total": len(runs), "total_cost_usd": round(total_cost, 4),
            })
        return out

    @app.get("/api/projects/{slug}")
    def project_detail(slug: str):
        try:
            proj = store.get_project(slug)
        except KeyError:
            raise HTTPException(404, f"project '{slug}' not found")
        tasks = [
            {**t.model_dump(mode="json"), "body": body}
            for t, body in store.list_tasks(slug)
        ]
        runs = [
            {**r.model_dump(mode="json")} for r, _ in store.list_runs(slug)
        ]
        experiments = [e.model_dump(mode="json") for e in store.list_experiments(slug)]
        return {"project": proj.model_dump(mode="json"), "tasks": tasks,
                "runs": runs, "experiments": experiments}

    @app.get("/api/projects/{slug}/runs/{run_id}")
    def run_detail(slug: str, run_id: str):
        try:
            run, body = store.get_run(slug, run_id)
        except KeyError:
            raise HTTPException(404, f"run '{run_id}' not found in '{slug}'")
        return {**run.model_dump(mode="json"), "body": body}

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
