"""OS detection, user directories, browser opening and runtime probing."""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

from omai import runner

URL_RE = re.compile(r"https?://[^\s'\"<>\x1b]+")
_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


def home() -> Path:
    return Path(os.path.expanduser("~"))


def expand(path: str) -> str:
    return os.path.expanduser(path)


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(home() / ".config")
    return Path(base) / "omai"


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(home() / ".local" / "state")
    return Path(base) / "omai"


def os_kind(osrelease: Path = Path("/proc/sys/kernel/osrelease")) -> str:
    """Return ``macos``, ``wsl`` or ``linux``."""
    if sys.platform == "darwin":
        return "macos"
    try:
        if "microsoft" in osrelease.read_text().lower():
            return "wsl"
    except OSError:
        pass
    return "linux"


def opener_argvs(url: str, kind: str) -> list[list[str]]:
    """Candidate commands (in order) that open ``url`` in the user's browser."""
    if kind == "macos":
        return [["open", url]]
    if kind == "wsl":
        return [
            ["cmd.exe", "/c", "start", "", url.replace("&", "^&")],
            ["powershell.exe", "-NoProfile", "-Command", "Start-Process", url],
            ["xdg-open", url],
        ]
    return [["xdg-open", url]]


def open_url(url: str, kind: str | None = None, echo=print) -> bool:
    """Print ``url`` and try to open it; return True if an opener succeeded."""
    echo(f"🔗 Open this URL to continue: {url}")
    for argv in opener_argvs(url, kind or os_kind()):
        if shutil.which(argv[0]) is None:
            continue
        if runner.run(argv, timeout=15).ok:
            return True
    return False


def find_urls(text: str) -> list[str]:
    return [u.rstrip(".,);]") for u in URL_RE.findall(text)]


def which_real(binary: str) -> tuple[str, str] | None:
    """Resolve ``binary`` on PATH, returning (path, realpath)."""
    path = shutil.which(binary)
    if path is None:
        return None
    return path, os.path.realpath(path)


def runtime_version(name: str) -> str | None:
    if shutil.which(name) is None:
        return None
    result = runner.run([name, "--version"], timeout=15)
    if not result.ok:
        return None
    match = _VERSION_RE.search(result.stdout + result.stderr)
    return match.group(1) if match else None
