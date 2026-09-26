"""Install, uninstall and migrate harnesses; user-local runtimes; config patches."""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass

from omai import platform, runner
from omai.context import Ctx
from omai.detect import Install, detect, unmet_requirements
from omai.registry import ChannelDef, HarnessDef, Requirement

# Runtimes omai may install itself: official user-local installers only, never sudo.
RUNTIME_INSTALLERS = {
    "uv": ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
    "bun": ["sh", "-c", "curl -fsSL https://bun.sh/install | bash"],
}


@dataclass
class Outcome:
    ok: bool
    message: str


def runtime_hint(req: Requirement, found: str | None) -> str:
    have = f"found {found}" if found else "not found"
    return (
        f"{req.runtime} >= {req.min} required ({have}). Install or upgrade it yourself "
        f"(e.g. `nvm install {req.min}` for node); omai never uses sudo."
    )


def choose_channel(harness: HarnessDef, preferred: str | None = None) -> ChannelDef:
    """Configured channel, else the first channel whose tools are present or installable."""
    if preferred:
        return harness.channel(preferred)
    for channel in harness.channels:
        tool = channel.install[0]
        if tool != "sh" and shutil.which(tool) is None and tool not in RUNTIME_INSTALLERS:
            continue
        if all(req.runtime in RUNTIME_INSTALLERS for req, _ in unmet_requirements(channel)):
            return channel
    return harness.channels[0]


def ensure_runtime(req: Requirement) -> Outcome:
    argv = RUNTIME_INSTALLERS.get(req.runtime)
    if argv is None:
        return Outcome(False, runtime_hint(req, platform.runtime_version(req.runtime)))
    code = runner.run_interactive(argv)
    return Outcome(code == 0, f"installed {req.runtime}" if code == 0 else f"{req.runtime} installer failed")


def system_prereq_hints(harness: HarnessDef, os_kind: str) -> list[str]:
    return [p.hint for p in harness.system_prereqs if os_kind in p.os and shutil.which(p.bin) is None]


def record(ctx: Ctx, harness: HarnessDef) -> Install | None:
    install = detect(harness)
    if install is None:
        ctx.state.installs.pop(harness.id, None)
    else:
        ctx.state.installs[harness.id] = install.to_state()
    ctx.state.save()
    return install


def install(ctx: Ctx, harness: HarnessDef, channel: ChannelDef) -> Outcome:
    code = runner.run_interactive(runner.fill(channel.install))
    if code != 0:
        return Outcome(False, f"{channel.id} installer exited {code}")
    found = record(ctx, harness)
    if found is None:
        return Outcome(False, f"installed via {channel.id} but `{harness.bin}` is not on PATH (open a new shell?)")
    return Outcome(True, f"installed {found.version or '?'} via {channel.id}")


def uninstall(ctx: Ctx, harness: HarnessDef, purge: bool = False) -> Outcome:
    current = detect(harness)
    if current is None:
        return Outcome(True, "not installed")
    if current.channel == "unknown":
        return Outcome(False, f"cannot tell how {current.path} was installed; remove it manually")
    code = runner.run_interactive(runner.fill(harness.channel(current.channel).uninstall))
    if code != 0:
        return Outcome(False, f"uninstall exited {code}")
    purged = []
    if purge:
        for entry in harness.config_dirs:
            target = platform.expand(entry)
            if os.path.isdir(target) and not os.path.islink(target):
                shutil.rmtree(target)
                purged.append(entry)
            elif os.path.lexists(target):
                os.remove(target)
                purged.append(entry)
    record(ctx, harness)
    kept = "" if purge else f"; kept {', '.join(harness.config_dirs) or 'config'}"
    return Outcome(True, f"removed {current.channel} install" + (f"; purged {purged}" if purged else kept))


def migrate(ctx: Ctx, harness: HarnessDef, to: str) -> Outcome:
    target = harness.channel(to)
    current = detect(harness)
    if current and current.channel == to:
        return Outcome(True, f"already on {to}")
    installed = install(ctx, harness, target)
    if not installed.ok:
        return installed
    if current and current.channel != "unknown":
        runner.run_interactive(runner.fill(harness.channel(current.channel).uninstall))
    final = record(ctx, harness)
    if final is None or final.channel != to:
        where = final.real if final else "nothing on PATH"
        return Outcome(False, f"after migration `{harness.bin}` resolves to {where}; check PATH order")
    return Outcome(True, f"migrated {current.channel if current else 'none'} → {to} ({final.version})")


# --- harness config patches via the harness's own config command -----------------


def config_get(ctx: Ctx, harness: HarnessDef, key: str) -> str | None:
    result = runner.run(runner.fill(harness.config_get, ctx.vars(harness) | {"key": key}), timeout=30)
    return result.stdout.strip() if result.ok else None


def config_set(ctx: Ctx, harness: HarnessDef, key: str, value: str) -> Outcome:
    argv = runner.fill(harness.config_set, ctx.vars(harness) | {"key": key, "value": value})
    result = runner.run(argv, timeout=30)
    return Outcome(result.ok, f"set {key}" if result.ok else result.output)


def pending_patches(ctx: Ctx, harness: HarnessDef) -> list:
    return [p for p in harness.config_patches if (config_get(ctx, harness, p.key) or "").lower() != p.value.lower()]


def parse_list(text: str | None) -> list[str]:
    """Parse a list printed by a harness config command (JSON or YAML block style)."""
    if not text:
        return []
    text = text.strip()
    if text.startswith("["):
        try:
            return [str(x) for x in json.loads(text.replace("'", '"'))]
        except ValueError:
            return []
    return [m.group(1).strip() for m in re.finditer(r"^\s*-\s+(.+)$", text, re.MULTILINE)]
