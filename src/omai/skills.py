"""Pinned skill sources → one canonical dir (`~/.agents/skills`) fanned out to every harness."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import httpx

from omai import platform
from omai.config import SkillSource
from omai.context import Ctx
from omai.detect import detect
from omai.install import Outcome, config_get, config_set, parse_list
from omai.state import now_iso
from omai.versions import describe_error

CANONICAL = "~/.agents/skills"


def canonical_dir() -> Path:
    return Path(platform.expand(CANONICAL))


def lock_path() -> Path:
    return platform.config_dir() / "skills.lock.json"


def load_lock() -> dict:
    try:
        return json.loads(lock_path().read_text())
    except (OSError, ValueError):
        return {"version": 1, "skills": {}}


def save_lock(lock: dict) -> None:
    lock_path().parent.mkdir(parents=True, exist_ok=True)
    lock_path().write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def bundled_root():
    return resources.files("omai").joinpath("bundled_skills")


def source_ref(source: SkillSource, name: str) -> str:
    if source.bundled:
        with resources.as_file(bundled_root().joinpath(name)) as path:
            return "bundled:" + tree_hash(Path(path))[:12]
    return source.ref


@dataclass
class Action:
    kind: str  # fetch | link | external_dir | remove | conflict
    name: str
    detail: str = ""
    harness: str = ""


def _linked_harnesses(ctx: Ctx):
    return [h for h in ctx.managed() if h.skills_dir.kind == "symlink"]


def _external_harnesses(ctx: Ctx):
    return [h for h in ctx.managed() if h.skills_dir.kind == "external_dirs"]


def plan(ctx: Ctx) -> list[Action]:
    """Diff desired skills against disk and lock. Read-only."""
    lock = load_lock()["skills"]
    desired = ctx.config.desired_skills()
    root = canonical_dir()
    actions: list[Action] = []
    for name, source in desired.items():
        target = root / name
        entry = lock.get(name)
        want = source_ref(source, name)
        if entry is None and target.exists():
            actions.append(Action("conflict", name, f"{target} exists but is not managed by omai; left untouched"))
            continue
        if entry is None or entry["ref"] != want or not target.exists():
            actions.append(Action("fetch", name, f"{source.label}@{want[:12]}"))
        elif tree_hash(target) != entry["hash"]:
            actions.append(Action("conflict", name, f"{target} was modified locally; left untouched"))
    for harness in _linked_harnesses(ctx):
        base = Path(platform.expand(harness.skills_dir.path))
        for name in desired:
            link = base / name
            if link.is_symlink():
                if os.path.realpath(link) != os.path.realpath(root / name):
                    actions.append(Action("conflict", name, f"{link} points elsewhere", harness.id))
            elif link.exists():
                actions.append(Action("conflict", name, f"{link} exists and is not a symlink", harness.id))
            else:
                actions.append(Action("link", name, str(link), harness.id))
    for harness in _external_harnesses(ctx):
        if detect(harness) is None:
            continue
        current = parse_list(config_get(ctx, harness, harness.skills_dir.key))
        wanted = harness.skills_dir.path
        if not any(platform.expand(d) == platform.expand(wanted) for d in current):
            actions.append(Action("external_dir", "*", wanted, harness.id))
    for name in lock:
        if name not in desired:
            actions.append(Action("remove", name))
    return actions


def _fetch_tarball(ctx: Ctx, repo: str, ref: str) -> tarfile.TarFile:
    with ctx.http() as client:
        response = client.get(f"https://codeload.github.com/{repo}/tar.gz/{ref}", timeout=60)
        response.raise_for_status()
    return tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz")


def _extract_skill(archive: tarfile.TarFile, name: str, dest: Path) -> None:
    candidates = sorted(
        (m.name.rsplit("/", 1)[0] for m in archive.getmembers() if m.name.endswith(f"/{name}/SKILL.md")),
        key=len,
    )
    if not candidates:
        raise FileNotFoundError(f"skill {name!r} not found in source")
    prefix = candidates[0] + "/"
    with tempfile.TemporaryDirectory() as tmp:
        members = [
            m.replace(name=m.name[len(prefix) :])
            for m in archive.getmembers()
            if m.name.startswith(prefix) and (m.isfile() or m.isdir())
        ]
        archive.extractall(tmp, members=members, filter="data")
        _replace_dir(Path(tmp), dest)


def _replace_dir(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    staging = dest.with_name(f".{dest.name}.omai-new")
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(src, staging)
    shutil.rmtree(dest, ignore_errors=True)
    staging.rename(dest)


def apply(ctx: Ctx, actions: list[Action]) -> list[tuple[Action, Outcome]]:
    lock = load_lock()
    desired = ctx.config.desired_skills()
    root = canonical_dir()
    results: list[tuple[Action, Outcome]] = []
    archives: dict[tuple[str, str], tarfile.TarFile] = {}
    registry = ctx.registry
    for action in actions:
        try:
            if action.kind == "fetch":
                source = desired[action.name]
                if source.bundled:
                    with resources.as_file(bundled_root().joinpath(action.name)) as path:
                        _replace_dir(Path(path), root / action.name)
                else:
                    key = (source.repo, source.ref)
                    if key not in archives:
                        archives[key] = _fetch_tarball(ctx, *key)
                    _extract_skill(archives[key], action.name, root / action.name)
                lock["skills"][action.name] = {
                    "source": source.label,
                    "ref": source_ref(source, action.name),
                    "hash": tree_hash(root / action.name),
                    "installed_at": now_iso(),
                }
                outcome = Outcome(True, f"installed from {action.detail}")
            elif action.kind == "link":
                link = Path(action.detail)
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(root / action.name)
                outcome = Outcome(True, f"linked {link}")
            elif action.kind == "external_dir":
                harness = registry[action.harness]
                key = harness.skills_dir.key
                current = parse_list(config_get(ctx, harness, key))
                outcome = config_set(ctx, harness, key, json.dumps([*current, action.detail]))
            elif action.kind == "remove":
                _remove(ctx, action.name, root)
                lock["skills"].pop(action.name, None)
                outcome = Outcome(True, "removed")
            else:
                outcome = Outcome(False, action.detail)
        except (OSError, httpx.HTTPError, tarfile.TarError) as exc:
            outcome = Outcome(False, f"{type(exc).__name__}: {exc}")
        results.append((action, outcome))
    save_lock(lock)
    return results


def _remove(ctx: Ctx, name: str, root: Path) -> None:
    target = root / name
    for harness in ctx.registry:
        if harness.skills_dir.kind == "symlink":
            link = Path(platform.expand(harness.skills_dir.path)) / name
            if link.is_symlink() and os.path.realpath(link) == os.path.realpath(target):
                link.unlink()
    shutil.rmtree(target, ignore_errors=True)


def sync(ctx: Ctx) -> list[tuple[Action, Outcome]]:
    return apply(ctx, plan(ctx))


def upstream_head(ctx: Ctx, source: SkillSource) -> str:
    with ctx.http() as client:
        response = client.get(f"https://api.github.com/repos/{source.repo}/commits/{source.track}")
        return response.raise_for_status().json()["sha"]


def drift(ctx: Ctx) -> list[dict]:
    """Compare each pinned source with its tracked branch. Read-only."""
    rows = []
    for source in ctx.config.skill_sources:
        if source.bundled:
            continue
        row = {"id": f"skills:{source.repo}", "kind": "skills", "installed": source.ref[:7], "channel": "github"}
        try:
            head = upstream_head(ctx, source)
            row |= {"latest": head[:7], "update_available": head != source.ref, "error": None}
        except (httpx.HTTPError, KeyError) as exc:
            row |= {"latest": None, "update_available": False, "error": describe_error(exc)}
        rows.append(row | {"warnings": []})
    return rows
