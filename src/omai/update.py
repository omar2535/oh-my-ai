"""Updates through each item's native updater, plus the `omai check` report."""

from __future__ import annotations

import httpx

from omai import config as config_mod
from omai import runner, skills, versions
from omai.context import Ctx
from omai.detect import detect
from omai.install import Outcome, record
from omai.registry import HarnessDef

SKILLS_ID = "skills"


def check_targets(ctx: Ctx) -> list[HarnessDef]:
    return [*ctx.managed(), ctx.registry["omai"]]


def check_rows(ctx: Ctx, refresh: bool = True, include_skills: bool = True) -> list[dict]:
    """Installed vs latest for every managed item. Writes only omai's own cache."""
    targets = check_targets(ctx)
    latest = versions.refresh(ctx, targets) if refresh else versions.cached(ctx)
    rows = []
    for harness in targets:
        install = detect(harness)
        if harness.kind != "self":
            if install:
                ctx.state.installs[harness.id] = install.to_state()
            else:
                ctx.state.installs.pop(harness.id, None)
        found = latest.get(harness.id, versions.Latest(None, "not checked yet"))
        installed = install.version if install else None
        rows.append(
            {
                "id": harness.id,
                "kind": harness.kind,
                "installed": installed,
                "latest": found.version,
                "channel": install.channel if install else None,
                "update_available": versions.is_newer(found.version, installed),
                "warnings": install.warnings if install else ["not installed"],
                "error": found.error,
            }
        )
    ctx.state.save()
    if include_skills and refresh:
        rows += skills.drift(ctx)
    return rows


def update_one(ctx: Ctx, harness: HarnessDef) -> Outcome:
    before = detect(harness)
    if before is None:
        return Outcome(False, "not installed (use `omai install`)")
    code = runner.run_interactive(runner.fill(harness.update, ctx.vars(harness)))
    after = record(ctx, harness) if harness.kind != "self" else before
    if code != 0:
        return Outcome(False, f"updater exited {code}")
    if after is None:
        return Outcome(False, "updater finished but the command is gone from PATH")
    if harness.kind == "self":
        return Outcome(True, "updated (restart omai to use the new version)")
    return Outcome(True, f"{before.version} → {after.version}")


def update_skills(ctx: Ctx) -> Outcome:
    """Move every pinned source to its tracked branch head, then re-sync."""
    moved = []
    for source in ctx.config.skill_sources:
        if source.bundled:
            continue
        head = skills.upstream_head(ctx, source)
        if head != source.ref:
            config_mod.set_source_ref(ctx.config_path, source.repo, head)
            moved.append(f"{source.repo} {source.ref[:7]}→{head[:7]}")
    ctx.reload_config()
    results = skills.sync(ctx)
    failed = [f"{a.name}: {o.message}" for a, o in results if not o.ok]
    if failed:
        return Outcome(False, "; ".join(failed))
    return Outcome(True, "; ".join(moved) or "skills already at upstream")


def resolve_targets(ctx: Ctx, ids: list[str], all_: bool) -> list[str]:
    if all_:
        return [h.id for h in ctx.managed()] + [SKILLS_ID, "omai"]
    unknown = [i for i in ids if i != SKILLS_ID and i not in ctx.registry]
    if unknown:
        raise KeyError(", ".join(unknown))
    return ids


def update(ctx: Ctx, ids: list[str]) -> list[tuple[str, Outcome]]:
    results = []
    for item in ids:
        if item == SKILLS_ID:
            try:
                results.append((item, update_skills(ctx)))
            except httpx.HTTPError as exc:
                results.append((item, Outcome(False, f"{type(exc).__name__}: {exc}")))
        else:
            results.append((item, update_one(ctx, ctx.registry[item])))
    return results
