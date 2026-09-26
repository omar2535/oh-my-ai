"""Shared runtime context passed to every service."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import httpx

from omai.config import Config, default_path, load_config
from omai.platform import os_kind
from omai.registry import HarnessDef, Registry, load_registry
from omai.state import State

# Tests swap this for an httpx.MockTransport; None means real network.
TRANSPORT: httpx.BaseTransport | None = None
HTTP_TIMEOUT = 5.0


@dataclass
class Ctx:
    registry: Registry
    config: Config
    config_path: Path
    state: State
    os_kind: str = field(default_factory=os_kind)

    def http(self) -> httpx.Client:
        return httpx.Client(
            transport=TRANSPORT,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "omai"},
        )

    def vars(self, harness: HarnessDef) -> dict[str, str]:
        """Placeholder values for a harness's registry commands."""
        hc = self.config.harnesses.get(harness.id)
        return {
            "provider": (hc.provider if hc else "") or harness.default_provider,
            "release_channel": hc.release_channel if hc else "latest",
        }

    def managed(self) -> list[HarnessDef]:
        """Enabled harnesses and tools (not omai itself), in registry order."""
        enabled = set(self.config.enabled())
        return [h for h in self.registry if h.id in enabled and h.kind != "self"]

    def reload_config(self) -> None:
        self.config = load_config(self.config_path, self.registry)


def load_ctx(config_path: Path | None = None) -> Ctx:
    registry = load_registry()
    path = config_path or default_path()
    return Ctx(registry=registry, config=load_config(path, registry), config_path=path, state=State())
