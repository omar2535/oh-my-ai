"""omai-owned machine state (`$XDG_STATE_HOME/omai/state.json`)."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from omai.platform import state_dir


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def age_hours(iso: str | None) -> float | None:
    if not iso:
        return None
    return (datetime.now(UTC) - datetime.fromisoformat(iso)).total_seconds() / 3600


class State:
    """Detected installs, cached check results, auth status and tracked repos."""

    def __init__(self, path: Path | None = None):
        self.path = path or state_dir() / "state.json"
        try:
            self.data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.data = {}
        for key in ("installs", "auth"):
            self.data.setdefault(key, {})
        self.data.setdefault("checks", {"fetched_at": None, "items": {}})
        self.data.setdefault("repos", [])

    @property
    def installs(self) -> dict:
        return self.data["installs"]

    @property
    def auth(self) -> dict:
        return self.data["auth"]

    @property
    def checks(self) -> dict:
        return self.data["checks"]

    @property
    def repos(self) -> list[dict]:
        return self.data["repos"]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".state-")
        with os.fdopen(fd, "w") as fh:
            json.dump(self.data, fh, indent=2)
        os.replace(tmp, self.path)
