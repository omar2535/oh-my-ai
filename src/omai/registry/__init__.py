"""Harness registry: every harness-specific fact lives in ``harnesses.toml``."""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

LATEST_KINDS = {"npm", "github_release", "github_tag", "pypi", "url_text", "url_json"}
LOGIN_MODES = {"command", "manual", "none"}
AUTH_PARSERS = {"exit_code", "json_path", "regex"}
SKILL_DIR_KINDS = {"canonical", "symlink", "external_dirs", "none"}
KINDS = {"harness", "tool", "self"}


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class Requirement:
    runtime: str
    min: str


@dataclass(frozen=True)
class ChannelDef:
    id: str
    install: list[str]
    uninstall: list[str]
    detect: list[str] = field(default_factory=list)
    markers: list[str] = field(default_factory=list)
    locate: list[str] = field(default_factory=list)
    runtime_bound_if: list[str] = field(default_factory=list)
    requires: list[Requirement] = field(default_factory=list)


@dataclass(frozen=True)
class VersionProbe:
    cmd: list[str]
    regex: str


@dataclass(frozen=True)
class LatestSource:
    kind: str
    ref: str
    field: str | None = None
    regex: str | None = None


@dataclass(frozen=True)
class LoginSpec:
    mode: str = "none"
    argv: list[str] = field(default_factory=list)
    hint: str = ""
    revokes_existing: bool = False


@dataclass(frozen=True)
class AuthStatusSpec:
    argv: list[str]
    parse: str
    expr: str = ""
    timeout: float = 30


@dataclass(frozen=True)
class ConfigPatch:
    key: str
    value: str


@dataclass(frozen=True)
class SkillsDirSpec:
    kind: str = "none"
    path: str = ""
    key: str = ""


@dataclass(frozen=True)
class SystemPrereq:
    bin: str
    hint: str
    os: list[str] = field(default_factory=lambda: ["linux", "wsl", "macos"])


@dataclass(frozen=True)
class HarnessDef:
    id: str
    name: str
    kind: str
    bin: str
    version: VersionProbe
    latest: LatestSource
    update: list[str]
    channels: list[ChannelDef]
    login: LoginSpec = LoginSpec()
    auth_status: AuthStatusSpec | None = None
    default_provider: str = ""
    config_get: list[str] = field(default_factory=list)
    config_set: list[str] = field(default_factory=list)
    config_patches: list[ConfigPatch] = field(default_factory=list)
    skills_dir: SkillsDirSpec = SkillsDirSpec()
    config_dirs: list[str] = field(default_factory=list)
    system_prereqs: list[SystemPrereq] = field(default_factory=list)

    def channel(self, channel_id: str) -> ChannelDef:
        for channel in self.channels:
            if channel.id == channel_id:
                return channel
        raise RegistryError(f"{self.id}: unknown channel {channel_id!r}")


@dataclass(frozen=True)
class Registry:
    harnesses: dict[str, HarnessDef]

    def __getitem__(self, harness_id: str) -> HarnessDef:
        return self.harnesses[harness_id]

    def __iter__(self):
        return iter(self.harnesses.values())

    def __contains__(self, harness_id: str) -> bool:
        return harness_id in self.harnesses


def _parse_harness(hid: str, raw: dict) -> HarnessDef:
    def need(key: str):
        if key not in raw:
            raise RegistryError(f"{hid}: missing {key!r}")
        return raw[key]

    channels = [
        ChannelDef(
            **{k: v for k, v in c.items() if k != "requires"},
            requires=[Requirement(**r) for r in c.get("requires", [])],
        )
        for c in raw.get("channels", [])
    ]
    auth = raw.get("auth_status")
    return HarnessDef(
        id=hid,
        name=raw.get("name", hid),
        kind=raw.get("kind", "harness"),
        bin=need("bin"),
        version=VersionProbe(**need("version")),
        latest=LatestSource(**need("latest")),
        update=need("update"),
        channels=channels,
        login=LoginSpec(**raw.get("login", {})),
        auth_status=AuthStatusSpec(**auth) if auth else None,
        default_provider=raw.get("default_provider", ""),
        config_get=raw.get("config_get", []),
        config_set=raw.get("config_set", []),
        config_patches=[ConfigPatch(**p) for p in raw.get("config_patches", [])],
        skills_dir=SkillsDirSpec(**raw.get("skills_dir", {})),
        config_dirs=raw.get("config_dirs", []),
        system_prereqs=[SystemPrereq(**p) for p in raw.get("system_prereqs", [])],
    )


def validate(harness: HarnessDef) -> None:
    hid = harness.id
    if harness.kind not in KINDS:
        raise RegistryError(f"{hid}: kind must be one of {sorted(KINDS)}")
    if not harness.channels:
        raise RegistryError(f"{hid}: needs at least one channel")
    ids = [c.id for c in harness.channels]
    if len(ids) != len(set(ids)):
        raise RegistryError(f"{hid}: duplicate channel ids")
    try:
        re.compile(harness.version.regex)
        if harness.latest.regex:
            re.compile(harness.latest.regex)
    except re.error as exc:
        raise RegistryError(f"{hid}: bad regex: {exc}") from exc
    if harness.latest.kind not in LATEST_KINDS:
        raise RegistryError(f"{hid}: latest.kind must be one of {sorted(LATEST_KINDS)}")
    if harness.login.mode not in LOGIN_MODES:
        raise RegistryError(f"{hid}: login.mode must be one of {sorted(LOGIN_MODES)}")
    if harness.login.mode == "command" and not harness.login.argv:
        raise RegistryError(f"{hid}: login.mode=command requires argv")
    if harness.login.mode == "manual" and not harness.login.hint:
        raise RegistryError(f"{hid}: login.mode=manual requires hint")
    if harness.auth_status and harness.auth_status.parse not in AUTH_PARSERS:
        raise RegistryError(f"{hid}: auth_status.parse must be one of {sorted(AUTH_PARSERS)}")
    if harness.skills_dir.kind not in SKILL_DIR_KINDS:
        raise RegistryError(f"{hid}: skills_dir.kind must be one of {sorted(SKILL_DIR_KINDS)}")
    if harness.skills_dir.kind in {"symlink", "external_dirs"} and not harness.skills_dir.path:
        raise RegistryError(f"{hid}: skills_dir.kind={harness.skills_dir.kind} requires path")
    if (harness.config_patches or harness.skills_dir.kind == "external_dirs") and not (
        harness.config_get and harness.config_set
    ):
        raise RegistryError(f"{hid}: config changes require config_get and config_set")
    argvs = [harness.update, harness.login.argv, *(c.install for c in harness.channels)]
    argvs += [c.uninstall for c in harness.channels]
    for argv in argvs:
        if any(re.search(r"\bsudo\b", arg) for arg in argv):
            raise RegistryError(f"{hid}: commands must never use sudo")


def load_registry(path: str | Path | None = None) -> Registry:
    """Load the packaged registry, or ``path`` / ``$OMAI_REGISTRY`` when given."""
    path = path or os.environ.get("OMAI_REGISTRY")
    if path:
        data = tomllib.loads(Path(path).read_text())
    else:
        data = tomllib.loads(resources.files("omai.registry").joinpath("harnesses.toml").read_text())
    try:
        harnesses = {hid: _parse_harness(hid, raw) for hid, raw in data.items()}
    except TypeError as exc:
        raise RegistryError(f"invalid registry entry: {exc}") from exc
    for harness in harnesses.values():
        validate(harness)
    return Registry(harnesses)
