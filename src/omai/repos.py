"""Per-repo spec-kit setup (`omai init`) and tracked-repo refresh."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from omai import runner
from omai.context import Ctx
from omai.detect import detect, version_ok
from omai.install import Outcome
from omai.state import now_iso

INTEGRATIONS = ["omp", "claude", "codex", "pi"]  # first = default
DEFAULT_INTEGRATION = "omp"
MIN_SPECKIT = "1.0"
HERMES_HINT = (
    "Hermes: spec-kit's Hermes integration is skipped (not multi-install safe). "
    "Run `hermes skills trust` in this repo so Hermes reads the shared .agents/skills."
)


@dataclass
class RepoReport:
    path: str
    ok: bool
    steps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _specify(args: list[str], cwd: str, timeout: float = 300) -> runner.Result:
    return runner.run(["specify", *args], timeout=timeout, cwd=cwd)


def integration_status(path: str) -> dict | None:
    result = _specify(["integration", "status", "--json"], path, timeout=60)
    try:
        return json.loads(result.stdout)
    except ValueError:
        return None


def speckit_version_problem(ctx: Ctx) -> str | None:
    installed = detect(ctx.registry["speckit"])
    if installed is None:
        return "spec-kit is not installed; run `omai install speckit`"
    if not version_ok(installed.version, MIN_SPECKIT):
        return f"spec-kit {installed.version} is too old (need >= {MIN_SPECKIT}); run `omai update speckit`"
    return None


def init(ctx: Ctx, path: str) -> RepoReport:
    path = os.path.abspath(path)
    report = RepoReport(path, ok=False)
    problem = speckit_version_problem(ctx)
    if problem:
        report.notes.append(problem)
        return report
    if not os.path.isdir(os.path.join(path, ".specify")):
        result = _specify(
            ["init", "--here", "--force", "--integration", DEFAULT_INTEGRATION, "--script", "sh", "--non-interactive"],
            path,
        )
        if not result.ok:
            report.notes.append(f"specify init failed: {result.output[-500:]}")
            return report
        report.steps.append(f"specify init ({DEFAULT_INTEGRATION})")
    status = integration_status(path) or {}
    installed = set(status.get("installed_integrations", []))
    for key in INTEGRATIONS:
        if key in installed:
            continue
        result = _specify(["integration", "install", key], path)
        if not result.ok:
            report.notes.append(f"integration install {key} failed: {result.output[-300:]}")
            return report
        report.steps.append(f"integration install {key}")
    if status.get("default_integration") != DEFAULT_INTEGRATION:
        _specify(["integration", "use", DEFAULT_INTEGRATION], path)
        report.steps.append(f"integration use {DEFAULT_INTEGRATION}")
    final = integration_status(path) or {}
    if "hermes" in final.get("installed_integrations", []):
        report.notes.append("hermes integration is installed here; spec-kit reports it as not multi-install safe")
    report.notes.append(HERMES_HINT)
    report.ok = final.get("status") == "ok"
    if not report.ok:
        report.notes.append(f"integration status: {final.get('status', 'unreadable')}")
    track(ctx, path, final)
    return report


def track(ctx: Ctx, path: str, status: dict) -> None:
    installed = detect(ctx.registry["speckit"])
    entry = {
        "path": path,
        "integrations": status.get("installed_integrations", []),
        "default": status.get("default_integration"),
        "speckit_version": installed.version if installed else None,
        "added_at": now_iso(),
    }
    ctx.state.data["repos"] = [r for r in ctx.state.repos if r["path"] != path] + [entry]
    ctx.state.save()


def untrack(ctx: Ctx, path: str) -> bool:
    path = os.path.abspath(path)
    before = len(ctx.state.repos)
    ctx.state.data["repos"] = [r for r in ctx.state.repos if r["path"] != path]
    ctx.state.save()
    return len(ctx.state.repos) != before


def repo_health(ctx: Ctx, repo: dict) -> str:
    if not os.path.isdir(repo["path"]):
        return "missing"
    installed = detect(ctx.registry["speckit"])
    if installed and repo.get("speckit_version") != installed.version:
        return "stale"
    return "healthy"


def refresh_all(ctx: Ctx) -> list[RepoReport]:
    """Upgrade every tracked repo's integrations to the installed spec-kit."""
    reports = []
    problem = speckit_version_problem(ctx)
    for repo in list(ctx.state.repos):
        report = RepoReport(repo["path"], ok=False)
        if not os.path.isdir(repo["path"]):
            report.notes.append("repo path no longer exists; skipped (remove with `omai repos remove`)")
            reports.append(report)
            continue
        if problem:
            report.notes.append(problem)
            reports.append(report)
            continue
        status = integration_status(repo["path"]) or {}
        failures = []
        for key in status.get("installed_integrations", []):
            result = _specify(["integration", "upgrade", key], repo["path"])
            (report.steps if result.ok else failures).append(f"integration upgrade {key}")
        report.notes += [f"{f} failed" for f in failures]
        report.ok = not failures
        track(ctx, repo["path"], integration_status(repo["path"]) or status)
        reports.append(report)
    return reports


def outcome(report: RepoReport) -> Outcome:
    return Outcome(report.ok, "; ".join(report.steps + report.notes) or "nothing to do")
