"""User config (`~/.config/omai/config.toml`): the desired state `omai up` converges to."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import tomlkit

from omai.platform import config_dir
from omai.registry import Registry

MATTPOCOCK_PIN = "c55ee46073ed923f86ce59a5eb3b6d895095d1b7"
# Skills that do nothing without a companion skill.
IMPLIED_SKILLS = {"grill-me": ["grilling"]}

DEFAULT_CONFIG = f"""\
# omai desired state. Edit freely; `omai up` converges the machine to it.

[harnesses.claude]
enabled = true
release_channel = "latest"   # latest | stable

[harnesses.codex]
enabled = true

[harnesses.hermes]
enabled = true
provider = "openai-codex"

[harnesses.pi]
enabled = true
provider = "openai-codex"    # pi logs in only inside its TUI: run `pi`, then /login

[harnesses.omp]
enabled = true
provider = "openai-codex"

[harnesses.speckit]
enabled = true

[[skills.sources]]
repo = "mattpocock/skills"
ref = "{MATTPOCOCK_PIN}"
track = "main"
skills = ["grill-me", "grilling"]

[[skills.sources]]
bundled = true
skills = ["grill-speckit"]

[check]
ttl_hours = 6
"""


class ConfigError(ValueError):
    pass


@dataclass
class HarnessConfig:
    enabled: bool = True
    provider: str = ""
    channel: str | None = None
    release_channel: str = "latest"


@dataclass
class SkillSource:
    skills: list[str]
    repo: str = ""
    ref: str = ""
    track: str = "main"
    bundled: bool = False

    @property
    def label(self) -> str:
        return "bundled" if self.bundled else self.repo


@dataclass
class Config:
    harnesses: dict[str, HarnessConfig]
    skill_sources: list[SkillSource] = field(default_factory=list)
    ttl_hours: float = 6
    warnings: list[str] = field(default_factory=list)

    def enabled(self) -> list[str]:
        return [hid for hid, hc in self.harnesses.items() if hc.enabled]

    def desired_skills(self) -> dict[str, SkillSource]:
        """Map skill name to its source, adding implied companion skills."""
        out: dict[str, SkillSource] = {}
        for source in self.skill_sources:
            for name in source.skills:
                out.setdefault(name, source)
                for implied in IMPLIED_SKILLS.get(name, []):
                    out.setdefault(implied, source)
        return out


def default_path() -> Path:
    return config_dir() / "config.toml"


def write_default_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG)


def load_config(path: Path, registry: Registry) -> Config:
    if not path.exists():
        write_default_config(path)
    try:
        doc = tomlkit.parse(path.read_text()).unwrap()
    except Exception as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    known_top = {"harnesses", "skills", "check"}
    warnings = [f"unknown config key {k!r} ignored" for k in doc if k not in known_top]

    harnesses: dict[str, HarnessConfig] = {}
    for hid, raw in doc.get("harnesses", {}).items():
        if hid not in registry or registry[hid].kind == "self":
            raise ConfigError(f"{path}: unknown harness {hid!r}")
        spec = registry[hid]
        hc = HarnessConfig(
            enabled=bool(raw.get("enabled", True)),
            provider=raw.get("provider") or spec.default_provider,
            channel=raw.get("channel"),
            release_channel=raw.get("release_channel", "latest"),
        )
        if hc.release_channel not in {"latest", "stable"}:
            raise ConfigError(f"{path}: harnesses.{hid}.release_channel must be latest or stable")
        if hc.channel:
            spec.channel(hc.channel)  # validates
        harnesses[hid] = hc

    sources = []
    for raw in doc.get("skills", {}).get("sources", []):
        source = SkillSource(
            skills=list(raw.get("skills", [])),
            repo=raw.get("repo", ""),
            ref=raw.get("ref", ""),
            track=raw.get("track", "main"),
            bundled=bool(raw.get("bundled", False)),
        )
        if not source.bundled and not (source.repo and source.ref):
            raise ConfigError(f"{path}: skill sources need repo and ref (or bundled = true)")
        sources.append(source)
    ttl = float(doc.get("check", {}).get("ttl_hours", 6))
    return Config(harnesses=harnesses, skill_sources=sources, ttl_hours=ttl, warnings=warnings)


def _edit(path: Path, mutate) -> None:
    doc = tomlkit.parse(path.read_text()) if path.exists() else tomlkit.parse(DEFAULT_CONFIG)
    mutate(doc)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomlkit.dumps(doc))


def set_harness_enabled(path: Path, harness_id: str, enabled: bool) -> None:
    def mutate(doc):
        harnesses = doc.setdefault("harnesses", tomlkit.table(is_super_table=True))
        harnesses.setdefault(harness_id, tomlkit.table())["enabled"] = enabled

    _edit(path, mutate)


def _sources(doc):
    skills = doc.setdefault("skills", tomlkit.table())
    if "sources" not in skills:
        skills["sources"] = tomlkit.aot()
    return skills["sources"]


def add_skill_source(path: Path, repo: str, ref: str, skills: list[str], track: str = "main") -> None:
    def mutate(doc):
        sources = _sources(doc)
        for source in sources:
            if source.get("repo") == repo:
                source["ref"] = ref
                for name in skills:
                    if name not in source["skills"]:
                        source["skills"].append(name)
                return
        table = tomlkit.table()
        table.update({"repo": repo, "ref": ref, "track": track, "skills": skills})
        sources.append(table)

    _edit(path, mutate)


def remove_skill(path: Path, name: str) -> bool:
    removed = False

    def mutate(doc):
        nonlocal removed
        sources = _sources(doc)
        for source in list(sources):
            if name in source.get("skills", []):
                source["skills"].remove(name)
                removed = True
            if not source.get("skills"):
                sources.remove(source)

    _edit(path, mutate)
    return removed


def set_source_ref(path: Path, repo: str, ref: str) -> None:
    def mutate(doc):
        for source in _sources(doc):
            if source.get("repo") == repo:
                source["ref"] = ref

    _edit(path, mutate)
