"""EROS CLI — `eros --help`."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__, ideas as ideas_mod
from .config import load_config
from .models import Experiment, TaskStatus
from .providers import get_provider
from .store import Store

app = typer.Typer(
    help="EROS — Engineer's Research Operating System. The factory that builds the next 20 projects.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
idea_app = typer.Typer(help="Browse, extend, and promote the idea map.", no_args_is_help=True)
exp_app = typer.Typer(help="Track experiments and benchmarks.", no_args_is_help=True)
app.add_typer(idea_app, name="idea")
app.add_typer(exp_app, name="exp")

console = Console()

STATUS_STYLE = {
    "todo": "dim",
    "in_progress": "yellow",
    "needs_review": "cyan",
    "needs_revision": "red",
    "done": "green",
    "blocked": "red bold",
}


def _store() -> Store:
    try:
        return Store()
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


def _provider(store: Store, provider: str | None, model: str | None):
    try:
        return get_provider(store.root, provider, model)
    except Exception as e:
        console.print(f"[red]provider error: {e}[/red]")
        raise typer.Exit(1)


@app.callback()
def _version_callback():
    pass


@app.command()
def version():
    """Show EROS version."""
    console.print(f"eros {__version__}")


# ── ideas ───────────────────────────────────────────────────────────────────

@idea_app.command("list")
def idea_list(
    domain: str = typer.Option(None, "--domain", "-d", help="filter by domain key"),
    top: int = typer.Option(0, "--top", "-t", help="show only the top N by total score"),
    flagship: bool = typer.Option(False, "--flagship", help="only flagship candidates"),
):
    """List ideas ranked by total score."""
    store = _store()
    items = ideas_mod.rank(store.load_ideas())
    domains = store.domains()
    if domain:
        items = [i for i in items if i.domain == domain]
    if flagship:
        items = [i for i in items if i.flagship_candidate]
    if top:
        items = items[:top]

    table = Table(title=f"Idea map ({len(items)} ideas)", header_style="bold")
    for col in ["ID", "Title", "Domain", "O", "D", "I", "S", "R", "Total", ""]:
        table.add_column(col)
    for i in items:
        s = i.scores
        table.add_row(
            i.id, i.title, domains.get(i.domain, i.domain),
            str(s.originality), str(s.technical_depth), str(s.interview_value),
            str(s.startup_potential), str(s.reuse), f"[bold]{i.total}[/bold]",
            ("[red]FLAG[/red]" if i.flagship_candidate else "")
            + (" [magenta]PROM[/magenta]" if i.status == "promoted" else ""),
        )
    console.print(table)
    console.print("[dim]FLAG = flagship candidate, PROM = promoted | axes: Originality, Depth, Interview, Startup, Reuse[/dim]")


@idea_app.command("show")
def idea_show(idea_id: str):
    """Show one idea in full."""
    store = _store()
    i = store.get_idea(idea_id)
    s = i.scores
    console.print(Panel(
        f"[bold]{i.title}[/bold]\n\n{i.pitch}\n\n"
        f"domain: {store.domains().get(i.domain, i.domain)}   status: {i.status}"
        + ("   [red]FLAGSHIP CANDIDATE[/red]" if i.flagship_candidate else "")
        + f"\nscores: originality {s.originality} | depth {s.technical_depth} | "
          f"interview {s.interview_value} | startup {s.startup_potential} | reuse {s.reuse}"
          f"  ->  [bold]{i.total}/25[/bold]",
        title=i.id,
    ))


@idea_app.command("render")
def idea_render():
    """Regenerate docs/IDEA_MAP.md from the yaml source of truth."""
    store = _store()
    out = store.root / "docs" / "IDEA_MAP.md"
    out.write_text(ideas_mod.render_markdown(store), encoding="utf-8")
    console.print(f"[green]wrote[/green] {out}")


@idea_app.command("new")
def idea_new(
    title: str = typer.Option(..., prompt=True),
    domain: str = typer.Option(..., prompt=True),
    pitch: str = typer.Option(..., prompt=True),
    originality: int = typer.Option(3, prompt=True, min=1, max=5),
    technical_depth: int = typer.Option(3, prompt=True, min=1, max=5),
    interview_value: int = typer.Option(3, prompt=True, min=1, max=5),
    startup_potential: int = typer.Option(3, prompt=True, min=1, max=5),
    reuse: int = typer.Option(3, prompt=True, min=1, max=5),
):
    """Add a new idea to the map (prompts for fields)."""
    store = _store()
    if domain not in store.domains():
        console.print(f"[red]unknown domain '{domain}'. Known: {', '.join(store.domains())}[/red]")
        raise typer.Exit(1)
    data = store.load_idea_map()
    next_num = max(int(i["id"].split("-")[1]) for i in data["ideas"]) + 1
    from .models import Idea, Scores
    idea = Idea(
        id=f"IDEA-{next_num:03d}", title=title, domain=domain, pitch=pitch,
        scores=Scores(
            originality=originality, technical_depth=technical_depth,
            interview_value=interview_value, startup_potential=startup_potential, reuse=reuse,
        ),
    )
    store.update_idea(idea)
    console.print(f"[green]added[/green] {idea.id} — {idea.title} ({idea.total}/25)")


@idea_app.command("promote")
def idea_promote(idea_id: str):
    """Create a project workspace from an idea."""
    store = _store()
    project = ideas_mod.promote(store, idea_id)
    pdir = store.project_dir(project.slug)
    console.print(f"[green]promoted[/green] {idea_id} -> workspace/projects/{project.slug}/")
    console.print(f"Next: edit [bold]{pdir / 'charter.md'}[/bold] (goals + success criteria), "
                  f"then run [bold]eros decompose {project.slug}[/bold]")


# ── pipeline ────────────────────────────────────────────────────────────────

@app.command()
def decompose(
    slug: str,
    provider: str = typer.Option(None, "--provider", "-p"),
    model: str = typer.Option(None, "--model", "-m"),
):
    """Generate architecture.md from the project charter (LLM)."""
    store = _store()
    prov = _provider(store, provider, model)
    from .pipeline.decompose import decompose as run_decompose
    with console.status(f"[cyan]{prov.name}[/cyan] designing architecture for {slug}..."):
        out = run_decompose(store, slug, prov)
    console.print(f"[green]wrote[/green] {out}")
    console.print(f"Next: review it, then run [bold]eros plan {slug}[/bold]")


@app.command()
def plan(
    slug: str,
    provider: str = typer.Option(None, "--provider", "-p"),
    model: str = typer.Option(None, "--model", "-m"),
):
    """Generate ordered TASK-*.md files from architecture.md (LLM)."""
    store = _store()
    prov = _provider(store, provider, model)
    from .pipeline.plan import plan as run_plan
    with console.status(f"[cyan]{prov.name}[/cyan] planning tasks for {slug}..."):
        tasks = run_plan(store, slug, prov)
    for t in tasks:
        deps = f"  (after {', '.join(t.depends_on)})" if t.depends_on else ""
        console.print(f"[green]{t.id}[/green] {t.title}{deps}")
    console.print(f"\nNext: [bold]eros dispatch {slug} {tasks[0].id}[/bold]")


@app.command()
def dispatch(
    slug: str,
    task_id: str,
    provider: str = typer.Option(None, "--provider", "-p"),
    model: str = typer.Option(None, "--model", "-m"),
):
    """Send a task to a coding agent working in the project's build/ directory."""
    store = _store()
    prov = _provider(store, provider, model)
    from .pipeline.dispatch import dispatch as run_dispatch
    console.print(f"dispatching [bold]{task_id}[/bold] to [cyan]{prov.name}[/cyan]"
                  + (f" ({prov.model})" if prov.model else "") + " ...")
    run = run_dispatch(store, slug, task_id, prov)
    color = "green" if run.status.value == "succeeded" else "red"
    console.print(f"[{color}]{run.id} {run.status.value}[/{color}]"
                  + (f" · ${run.cost_usd:.4f}" if run.cost_usd else "")
                  + (f" · {run.num_turns} turns" if run.num_turns else "")
                  + ("" if run.agent_mode else " · [yellow]degraded mode: patch generated, apply manually[/yellow]"))
    console.print(f"Next: [bold]eros review {slug} {run.id}[/bold]")


@app.command()
def review(
    slug: str,
    run_id: str,
    provider: str = typer.Option(None, "--provider", "-p"),
    model: str = typer.Option(None, "--model", "-m"),
):
    """LLM code review of a run's changes; APPROVE marks the task done."""
    store = _store()
    prov = _provider(store, provider, model)
    from .pipeline.review import review as run_review
    with console.status(f"[cyan]{prov.name}[/cyan] reviewing {run_id}..."):
        verdict = run_review(store, slug, run_id, prov)
    color = "green" if verdict.value == "approve" else "yellow"
    console.print(f"verdict: [{color} bold]{verdict.value.upper()}[/{color} bold] "
                  f"(details appended to runs/{run_id.upper()}.md)")


@app.command()
def status(slug: str = typer.Argument(None)):
    """Lifecycle dashboard for all projects, or task detail for one."""
    store = _store()
    projects = store.list_projects()
    if not projects:
        console.print("no projects yet — start with [bold]eros idea list[/bold] "
                      "and [bold]eros idea promote IDEA-xxx[/bold]")
        return

    if slug:
        proj = store.get_project(slug)
        console.print(Panel(f"[bold]{proj.title}[/bold] · from {proj.idea_id} · created {proj.created}",
                            title=slug))
        table = Table(header_style="bold")
        for col in ["Task", "Title", "Status", "Depends on", "Runs"]:
            table.add_column(col)
        for t, _ in store.list_tasks(slug):
            style = STATUS_STYLE.get(t.status.value, "")
            table.add_row(t.id, t.title, f"[{style}]{t.status.value}[/{style}]",
                          ", ".join(t.depends_on) or "—", ", ".join(t.runs) or "—")
        console.print(table)
        runs = store.list_runs(slug)
        if runs:
            rt = Table(title="Runs", header_style="bold")
            for col in ["Run", "Task", "Provider", "Status", "Review", "Cost"]:
                rt.add_column(col)
            for r, _ in runs:
                rt.add_row(r.id, r.task_id, r.provider + (f" ({r.model})" if r.model else ""),
                           r.status.value, r.review.value,
                           f"${r.cost_usd:.4f}" if r.cost_usd else "—")
            console.print(rt)
        return

    table = Table(title="EROS projects", header_style="bold")
    for col in ["Project", "From", "Stage", "Tasks (done/total)", "Last run"]:
        table.add_column(col)
    for proj in projects:
        tasks = store.list_tasks(proj.slug)
        runs = store.list_runs(proj.slug)
        done = sum(1 for t, _ in tasks if t.status == TaskStatus.done)
        if not (store.project_dir(proj.slug) / "architecture.md").exists():
            stage = "chartered"
        elif not tasks:
            stage = "decomposed"
        elif done == len(tasks):
            stage = "[green]complete[/green]"
        else:
            stage = "building"
        last = runs[-1][0] if runs else None
        table.add_row(
            proj.slug, proj.idea_id, stage, f"{done}/{len(tasks)}",
            f"{last.id} ({last.status.value}, review: {last.review.value})" if last else "—",
        )
    console.print(table)


# ── experiments ─────────────────────────────────────────────────────────────

@exp_app.command("log")
def exp_log(
    slug: str,
    name: str,
    metric: list[str] = typer.Option([], "--metric", "-m", help="name=value, repeatable"),
    param: list[str] = typer.Option([], "--param", "-p", help="name=value, repeatable"),
    notes: str = typer.Option("", "--notes", "-n"),
):
    """Log an experiment result: eros exp log <slug> baseline -m rmse=0.42 -p model=xgb"""
    store = _store()
    try:
        metrics = {k: float(v) for k, v in (m.split("=", 1) for m in metric)}
        params = {k: v for k, v in (p.split("=", 1) for p in param)}
    except ValueError:
        console.print("[red]metrics/params must be name=value (metrics numeric)[/red]")
        raise typer.Exit(1)
    exp = Experiment(name=name, metrics=metrics, params=params, notes=notes)
    store.log_experiment(slug, exp)
    console.print(f"[green]logged[/green] {name} -> workspace/projects/{slug}/experiments/log.jsonl")


@exp_app.command("list")
def exp_list(slug: str):
    """List experiments for a project."""
    store = _store()
    exps = store.list_experiments(slug)
    if not exps:
        console.print("no experiments logged yet")
        return
    metric_names = sorted({k for e in exps for k in e.metrics})
    table = Table(title=f"Experiments — {slug}", header_style="bold")
    for col in ["When", "Name", *metric_names, "Params", "Notes"]:
        table.add_column(col)
    for e in exps:
        table.add_row(
            e.ts, e.name,
            *[f"{e.metrics[m]:g}" if m in e.metrics else "—" for m in metric_names],
            " ".join(f"{k}={v}" for k, v in e.params.items()) or "—",
            e.notes or "—",
        )
    console.print(table)


# ── config ──────────────────────────────────────────────────────────────────

@app.command("config")
def config_show(
    set_default: str = typer.Option(None, "--set-default",
                                    help="set default provider: claude_code|anthropic|ollama|openai_compat"),
):
    """Show effective provider config, or set the default provider."""
    store = _store()
    if set_default:
        if set_default not in ("claude_code", "anthropic", "ollama", "openai_compat"):
            console.print(f"[red]unknown provider '{set_default}'[/red]")
            raise typer.Exit(1)
        import tomli_w
        local = store.root / ".eros" / "config.local.toml"
        local.parent.mkdir(exist_ok=True)
        existing: dict = {}
        if local.exists():
            import tomllib
            existing = tomllib.loads(local.read_text(encoding="utf-8"))
        existing.setdefault("provider", {})["default"] = set_default
        local.write_text(tomli_w.dumps(existing), encoding="utf-8")
        console.print(f"[green]default provider -> {set_default}[/green] (in .eros/config.local.toml)")
        return

    cfg = load_config(store.root)["provider"]
    console.print(f"default provider: [bold cyan]{cfg['default']}[/bold cyan]\n")
    table = Table(header_style="bold")
    for col in ["Provider", "Key settings", "Agent dispatch"]:
        table.add_column(col)
    rows = [
        ("claude_code", f"binary={cfg['claude_code'].get('binary')}", "native (edits files)"),
        ("anthropic", f"model={cfg['anthropic'].get('model')} key=${cfg['anthropic'].get('api_key_env')}", "degraded (patch)"),
        ("ollama", f"{cfg['ollama'].get('base_url')} model={cfg['ollama'].get('model')}", "degraded (patch)"),
        ("openai_compat", f"{cfg['openai_compat'].get('base_url')} model={cfg['openai_compat'].get('model') or '(unset)'}", "degraded (patch)"),
    ]
    for name, settings, mode in rows:
        marker = " <-" if name == cfg["default"] else ""
        table.add_row(name + marker, settings, mode)
    console.print(table)
    console.print("[dim]override per command with --provider/-p and --model/-m; "
                  "edit .eros/config.toml (shared) or .eros/config.local.toml (this machine)[/dim]")


if __name__ == "__main__":
    app()
