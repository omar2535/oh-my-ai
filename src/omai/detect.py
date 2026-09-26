"""Detect installed harnesses, their install channel and runtime warnings."""

from __future__ import annotations

import glob
import os
import re
from dataclasses import asdict, dataclass, field
from fnmatch import fnmatch

from packaging.version import InvalidVersion, Version

import omai
from omai import platform, runner
from omai.registry import ChannelDef, HarnessDef, Requirement
from omai.state import now_iso


@dataclass
class Install:
    id: str
    version: str | None
    channel: str
    path: str
    real: str
    on_path: bool = True
    runtime_bound: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_state(self) -> dict:
        return asdict(self) | {"detected_at": now_iso()}


def _matches(value: str, patterns: list[str]) -> bool:
    return any(fnmatch(value, platform.expand(p)) for p in patterns)


def infer_channel(harness: HarnessDef, path: str, real: str) -> str:
    """Resolved location wins over the PATH entry (a ~/.local/bin symlink may point anywhere)."""
    for channel in harness.channels:
        if _matches(real, channel.detect):
            return channel.id
    for channel in harness.channels:
        if any(os.path.exists(platform.expand(m)) for m in channel.markers):
            return channel.id
    for channel in harness.channels:
        if _matches(path, channel.detect):
            return channel.id
    return "unknown"


def parse_version(harness: HarnessDef, output: str) -> str | None:
    match = re.search(harness.version.regex, output, re.MULTILINE)
    return match.group(1) if match else None


def version_ok(found: str | None, minimum: str) -> bool:
    if found is None:
        return False
    try:
        return Version(found) >= Version(minimum)
    except InvalidVersion:
        return False


def unmet_requirements(channel: ChannelDef) -> list[tuple[Requirement, str | None]]:
    unmet = []
    for req in channel.requires:
        found = platform.runtime_version(req.runtime)
        if not version_ok(found, req.min):
            unmet.append((req, found))
    return unmet


def detect(harness: HarnessDef) -> Install | None:
    """Return the current install of ``harness`` or None when absent."""
    if harness.kind == "self":
        return Install(harness.id, omai.__version__, "uv", "", "")
    found = platform.which_real(harness.bin)
    if found is None:
        return _locate_off_path(harness)
    path, real = found
    channel_id = infer_channel(harness, path, real)
    result = runner.run(harness.version.cmd, timeout=30)
    install = Install(harness.id, parse_version(harness, result.output), channel_id, path, real)
    if channel_id == "unknown":
        return install
    channel = harness.channel(channel_id)
    if _matches(real, channel.runtime_bound_if) or _matches(path, channel.runtime_bound_if):
        install.runtime_bound = True
        preferred = harness.channels[0].id
        install.warnings.append(
            f"runtime-bound (version-managed runtime; switching versions hides it) → "
            f"`omai migrate {harness.id} --to {preferred}`"
        )
    for req, have in unmet_requirements(channel):
        install.warnings.append(f"needs {req.runtime} >= {req.min} (found {have or 'none'})")
    return install


def _locate_off_path(harness: HarnessDef) -> Install | None:
    for channel in harness.channels:
        for pattern in channel.locate:
            hits = sorted(glob.glob(platform.expand(pattern)))
            if hits:
                return Install(
                    harness.id,
                    None,
                    channel.id,
                    hits[-1],
                    os.path.realpath(hits[-1]),
                    on_path=False,
                    runtime_bound=True,
                    warnings=[
                        f"not on PATH but installed at {hits[-1]} (runtime-bound); "
                        "activate that runtime or `omai migrate` — not reinstalling"
                    ],
                )
    return None
