"""`omai` command line."""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import Annotated

import typer

import omai
from omai import auth, converge, install, repos, skills, update
from omai import config as config_mod
from omai.config import ConfigError
from omai.context import Ctx, load_ctx
from omai.report import (
    check_table,
    console,
    emit_json,
    outcomes_table,
    summary_json,
    summary_table,
)

EXIT_OK, EXIT_FAIL, EXIT_NETWORK, EXIT_CONFIG = 0, 1, 2, 3

app = typer.Typer(help="Install, log in, update and equip your coding-agent harnesses.", no_args_is_help=False)
skills_app = typer.Typer(help="Manage skill sources (installed to ~/.agents/skills).")
repos_app = typer.Typer(help="Repos initialized with `omai init`.")
app.add_typer(skills_app, name="skills")
app.add_typer(repos_app, name="repos")

JsonOpt = Annotated[bool, typer.Option("--json", help="Machine-readable output.")]
_config_path: Path | None = None


def ctx() -> Ctx:
    try:
        loaded = load_ctx(_config_path)
    except ConfigError as exc:
        console.print(f"[red]config error:[/] {exc}")
        raise typer.Exit(EXIT_CONFIG) from exc
    for warning in loaded.config.warnings:
        console.print(f"[yellow]warning:[/] {warning}")
    return loaded


def harness_or_exit(c: Ctx, harness_id: str, allow_self: bool = False):
    if harness_id not in c.registry or (c.registry[harness_id].kind == "self" and not allow_self):
        known = ", ".join(h.id for h in c.registry if h.kind != "self")
        console.print(f"[red]unknown item {harness_id!r}[/] (known: {known})")
        raise typer.Exit(EXIT_FAIL)
    return c.registry[harness_id]


def version_callback(value: bool):
    if value:
        print(f"omai {omai.__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def root(
    typer_ctx: typer.Context,
    config: Annotated[Path | None, typer.Option("--config", help="Config file path.")] = None,
    version: Annotated[bool, typer.Option("--version", callback=version_callback, is_eager=True)] = False,
):
    global _config_path
    _config_path = config
    if typer_ctx.invoked_subcommand is None:
        tui()


@app.command()
def up(
    no_login: Annotated[bool, typer.Option("--no-login", help="Skip login steps.")] = False,
    only: Annotated[list[str] | None, typer.Option("--only", help="Limit to these harness ids.")] = None,
    json_out: JsonOpt = False,
):
    """Converge the machine to your config: runtimes, installs, config, skills, logins."""
    c = ctx()
    plan = converge.plan(c, only=only, with_login=not no_login)
    if not plan.steps:
        if json_out:
            emit_json({"ok": True, "steps": [], "notes": plan.notes})
        else:
            for note in plan.notes:
                console.print(f"[yellow]•[/] {note}")
            console.print("[green]✓ nothing to do[/] — everything matches your config")
        return
    if json_out:  # keep stdout pure JSON: child installer/login output goes to stderr
        with contextlib.redirect_stdout(sys.stderr):
            summary = converge.execute(plan)
    else:
        summary = converge.execute(plan, on_step=lambda s: console.rule(s.description))
    if json_out:
        emit_json(summary_json(summary))
    else:
        console.print(summary_table(summary))
        for note in summary.notes:
            console.print(f"[yellow]•[/] {note}")
    raise typer.Exit(EXIT_OK if summary.ok else EXIT_FAIL)


@app.command()
def check(
    json_out: JsonOpt = False,
    exit_code: Annotated[bool, typer.Option("--exit-code", help="Exit 1 when updates are available.")] = False,
    cached: Annotated[bool, typer.Option("--cached", help="Use cached latest versions (no network).")] = False,
):
    """Show installed vs latest versions. Read-only."""
    c = ctx()
    rows = update.check_rows(c, refresh=not cached)
    fetched_at = c.state.checks.get("fetched_at")
    if json_out:
        emit_json({"checked_at": fetched_at, "items": rows})
    else:
        console.print(check_table(rows, fetched_at))
    if any(r.get("error") and not r.get("latest") and r["id"] != "omai" for r in rows):
        raise typer.Exit(EXIT_NETWORK)
    if exit_code and any(r["update_available"] for r in rows):
        raise typer.Exit(EXIT_FAIL)


@app.command()
def status(json_out: JsonOpt = False):
    """Installs and login status (no network)."""
    c = ctx()
    rows = []
    for harness in c.managed():
        install_ = install.record(c, harness)
        state = auth.auth_status(c, harness) if install_ and install_.on_path else "-"
        hint = auth.manual_hint(c, harness) if harness.login.mode == "manual" and state != auth.OK else ""
        rows.append(
            {
                "id": harness.id,
                "installed": install_.version if install_ else None,
                "channel": install_.channel if install_ else None,
                "auth": state,
                "hint": hint,
                "warnings": install_.warnings if install_ else [],
            }
        )
    if json_out:
        emit_json(rows)
        return
    from rich.table import Table

    table = Table(title="omai status")
    for col in ("item", "installed", "channel", "auth", "notes"):
        table.add_column(col)
    for row in rows:
        notes = "\n".join(filter(None, [row["hint"], *row["warnings"]]))
        table.add_row(row["id"], row["installed"] or "-", row["channel"] or "-", row["auth"], notes)
    console.print(table)


@app.command("update")
def update_cmd(
    ids: Annotated[list[str] | None, typer.Argument(help="Items to update (harness ids, 'skills', 'omai').")] = None,
    all_: Annotated[bool, typer.Option("--all", help="Update everything.")] = False,
    repos_: Annotated[bool, typer.Option("--repos", help="Also refresh tracked repos' spec-kit files.")] = False,
):
    """Update via each item's native updater."""
    c = ctx()
    if not ids and not all_ and not repos_:
        console.print("Specify items, --all, or --repos (see `omai check`).")
        raise typer.Exit(EXIT_FAIL)
    try:
        targets = update.resolve_targets(c, ids or [], all_)
    except KeyError as exc:
        console.print(f"[red]unknown item(s):[/] {exc}")
        raise typer.Exit(EXIT_FAIL) from exc
    results = update.update(c, targets)
    if repos_:
        results += [(r.path, repos.outcome(r)) for r in repos.refresh_all(c)]
    console.print(outcomes_table("omai update", results))
    raise typer.Exit(EXIT_OK if all(o.ok for _, o in results) else EXIT_FAIL)


@app.command("install")
def install_cmd(
    harness_id: str,
    channel: Annotated[str | None, typer.Option("--channel", help="Install channel.")] = None,
):
    """Install one harness (adopts it if already installed)."""
    c = ctx()
    harness = harness_or_exit(c, harness_id)
    existing = install.record(c, harness)
    if existing is not None:
        console.print(f"{harness.name} already installed ({existing.version} via {existing.channel})")
        return
    outcome = install.install(c, harness, install.choose_channel(harness, channel))
    console.print(outcomes_table("omai install", [(harness_id, outcome)]))
    raise typer.Exit(EXIT_OK if outcome.ok else EXIT_FAIL)


@app.command()
def uninstall(
    harness_id: str,
    purge: Annotated[bool, typer.Option("--purge", help="Also delete config and credentials.")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Don't ask for confirmation.")] = False,
):
    """Remove a harness program. Config and credentials are kept unless --purge."""
    c = ctx()
    harness = harness_or_exit(c, harness_id)
    if purge and not yes:
        typer.confirm(f"Delete {', '.join(harness.config_dirs)} (config and credentials)?", abort=True)
    outcome = install.uninstall(c, harness, purge=purge)
    console.print(outcomes_table("omai uninstall", [(harness_id, outcome)]))
    raise typer.Exit(EXIT_OK if outcome.ok else EXIT_FAIL)


@app.command()
def migrate(
    harness_id: str,
    to: Annotated[str, typer.Option("--to", help="Target channel.")],
):
    """Reinstall a harness through another channel, then remove the old install."""
    c = ctx()
    harness = harness_or_exit(c, harness_id)
    outcome = install.migrate(c, harness, to)
    console.print(outcomes_table("omai migrate", [(harness_id, outcome)]))
    raise typer.Exit(EXIT_OK if outcome.ok else EXIT_FAIL)


@app.command()
def login(
    ids: Annotated[list[str] | None, typer.Argument(help="Harness ids.")] = None,
    all_: Annotated[bool, typer.Option("--all")] = False,
    force: Annotated[bool, typer.Option("--force", help="Log in even if already logged in.")] = False,
):
    """Run each harness's own login, one at a time, skipping ones already logged in."""
    c = ctx()
    targets = [h for h in c.managed() if h.login.mode != "none"] if all_ or not ids else []
    targets += [harness_or_exit(c, i) for i in ids or []]
    results = []
    for harness in targets:
        result = auth.login(c, harness, force=force, echo=console.print)
        results.append((harness.id, install.Outcome(result.ok, result.message)))
    console.print(outcomes_table("omai login", results))
    raise typer.Exit(EXIT_OK if all(o.ok for _, o in results) else EXIT_FAIL)


@app.command()
def init(path: Annotated[Path, typer.Argument(help="Repository path.")] = Path(".")):
    """Set up spec-kit in a repo (claude, codex, pi, omp; default omp) and track it."""
    c = ctx()
    report = repos.init(c, str(path))
    for step in report.steps:
        console.print(f"[green]✓[/] {step}")
    for note in report.notes:
        console.print(f"[yellow]•[/] {note}")
    raise typer.Exit(EXIT_OK if report.ok else EXIT_FAIL)


@repos_app.command("list")
def repos_list(json_out: JsonOpt = False):
    c = ctx()
    rows = [r | {"health": repos.repo_health(c, r)} for r in c.state.repos]
    if json_out:
        emit_json(rows)
        return
    for row in rows:
        console.print(f"{row['health']:>8}  {row['path']}  ({', '.join(row['integrations'])})")
    if not rows:
        console.print("no tracked repos — run `omai init` inside a repo")


@repos_app.command("remove")
def repos_remove(path: Path):
    c = ctx()
    if not repos.untrack(c, str(path)):
        console.print(f"{path} is not tracked")
        raise typer.Exit(EXIT_FAIL)
    console.print(f"untracked {path}")


@skills_app.command("list")
def skills_list(json_out: JsonOpt = False):
    c = ctx()
    lock = skills.load_lock()["skills"]
    rows = [
        {"name": name, "source": src.label, "installed": name in lock, "ref": lock.get(name, {}).get("ref")}
        for name, src in c.config.desired_skills().items()
    ]
    if json_out:
        emit_json(rows)
        return
    for row in rows:
        mark = "[green]✓[/]" if row["installed"] else "[yellow]…[/]"
        console.print(f"{mark} {row['name']:<20} {row['source']}")


@skills_app.command("add")
def skills_add(
    source: Annotated[str, typer.Argument(help="owner/repo[@ref]")],
    skill: Annotated[list[str], typer.Option("--skill", help="Skill name (repeatable).")],
    track: Annotated[str, typer.Option(help="Branch to watch for updates.")] = "main",
):
    """Add skills from a GitHub repo, pinned to a commit."""
    c = ctx()
    repo, _, ref = source.partition("@")
    if not ref:
        from omai.config import SkillSource

        ref = skills.upstream_head(c, SkillSource(skills=skill, repo=repo, ref="", track=track))
    config_mod.add_skill_source(c.config_path, repo, ref, skill, track)
    c.reload_config()
    _print_sync(skills.sync(c))


@skills_app.command("remove")
def skills_remove(name: str):
    c = ctx()
    if not config_mod.remove_skill(c.config_path, name):
        console.print(f"{name} is not in your config")
        raise typer.Exit(EXIT_FAIL)
    c.reload_config()
    _print_sync(skills.sync(c))


@skills_app.command("sync")
def skills_sync():
    """Install/link skills to match your config."""
    _print_sync(skills.sync(ctx()))


def _print_sync(results) -> None:
    if not results:
        console.print("[green]✓ skills up to date[/]")
        return
    console.print(outcomes_table("skills", [(f"{a.kind} {a.name}", o) for a, o in results]))
    if not all(o.ok for _, o in results):
        raise typer.Exit(EXIT_FAIL)


@app.command()
def tui():
    """Open the dashboard."""
    from omai.tui.app import OmaiApp

    c = ctx()
    OmaiApp(c).run()


def main() -> None:
    app()
