"""Hermetic fixtures: temp HOME, fake executables, mocked HTTP, credential canaries."""

from __future__ import annotations

import io
import json
import os
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest

FAKES = Path(__file__).parent / "fakes"
CANARIES = [".claude/.credentials.json", ".codex/auth.json", ".hermes/auth.json", ".pi/agent/auth.json"]
_FORBIDDEN: set[str] = set()
_VIOLATIONS: list[str] = []


def _audit(event: str, args) -> None:
    if event == "open" and _FORBIDDEN and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.fsdecode(args[0])
        if os.path.realpath(path) in _FORBIDDEN:
            _VIOLATIONS.append(path)


sys.addaudithook(_audit)


@dataclass
class FakeHome:
    root: Path
    bin: Path
    staged: Path
    log: Path
    specs: Path

    def path(self, rel: str) -> Path:
        return self.root / rel

    def invocations(self, name: str | None = None) -> list[dict]:
        if not self.log.exists():
            return []
        rows = [json.loads(line) for line in self.log.read_text().splitlines()]
        return [r for r in rows if name is None or r["bin"] == name]

    def calls(self, name: str) -> list[list[str]]:
        return [r["argv"] for r in self.invocations(name)]

    def state(self, name: str) -> dict:
        path = self.specs / f"{name}.state.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def write_fake(
        self,
        name: str,
        responses: list[dict],
        state: dict | None = None,
        at: str | None = None,
        staged: bool = False,
    ) -> Path:
        """Create fake executable ``name``; at=relative real location (symlinked from bin)."""
        spec = self.specs / f"{name}.json"
        state_file = self.specs / f"{name}.state.json"
        spec.write_text(
            json.dumps({"name": name, "responses": responses, "state": str(state_file), "log": str(self.log)})
        )
        if state is not None and not state_file.exists():
            state_file.write_text(json.dumps(state))
        script = f"#!{sys.executable}\nimport sys\nsys.path.insert(0, {str(FAKES)!r})\n"
        script += f"from fake_harness import main\nmain({str(spec)!r})\n"
        target = (self.staged / name) if staged else (self.root / at if at else self.bin / name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(script)
        target.chmod(0o755)
        if at and not staged:
            link = self.bin / name
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(target)
        return target


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    root = tmp_path / "home"
    fh = FakeHome(
        root, root / ".local" / "bin", tmp_path / "staged", tmp_path / "invocations.jsonl", tmp_path / "specs"
    )
    for d in (fh.bin, fh.staged, fh.specs):
        d.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(root))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.delenv("OMAI_REGISTRY", raising=False)
    monkeypatch.setenv("PATH", f"{fh.bin}:/usr/bin:/bin")
    for rel in CANARIES:
        canary = root / rel
        canary.parent.mkdir(parents=True, exist_ok=True)
        canary.write_text('{"secret": "canary"}')
        _FORBIDDEN.add(os.path.realpath(canary))
    # Browser openers: never launch a real browser.
    for opener in ("xdg-open", "cmd.exe", "powershell.exe", "open"):
        fh.write_fake(opener, [{"args": []}])
    _VIOLATIONS.clear()
    yield fh
    violations = list(_VIOLATIONS)
    _FORBIDDEN.clear()
    _VIOLATIONS.clear()
    assert not violations, f"omai opened harness credential files: {violations}"


# --- canned harness behaviour ---------------------------------------------------------

LOGIN_URL = "https://auth.example.test/authorize?client=fake"


def harness_responses(hid: str) -> list[dict]:
    login_set = {"set": {"logged_in": True}, "stdout": f"Open this URL: {LOGIN_URL}\n"}
    common_update = {"args": ["update"], "set": {"version": "$latest"}, "stdout": "updated\n"}
    table = {
        "claude": [
            {"args": ["--version"], "stdout": "$version (Claude Code)\n"},
            {"args": ["auth", "status", "--json"], "when": {"logged_in": True}, "stdout": '{"loggedIn": true}'},
            {"args": ["auth", "status", "--json"], "stdout": '{"loggedIn": false}', "exit": 1},
            {"args": ["auth", "login"], **login_set},
        ],
        "codex": [
            {"args": ["--version"], "stdout": "codex-cli $version\n"},
            {"args": ["login", "status"], "when": {"logged_in": True}, "stderr": "Logged in using ChatGPT\n"},
            {"args": ["login", "status"], "stderr": "Not logged in\n", "exit": 1},
            {"args": ["login"], **login_set},
        ],
        "hermes": [
            {"args": ["--version"], "stdout": "Hermes Agent v$version (2026.9.21)\n"},
            {
                "args": ["auth", "status", "openai-codex"],
                "when": {"logged_in": True},
                "stdout": "openai-codex: logged in\n",
            },
            {"args": ["auth", "status", "openai-codex"], "stdout": "openai-codex: logged out\n"},
            {"args": ["auth", "add", "openai-codex"], **login_set},
            {"args": ["config", "get", "auth.adopt_external_logins"], "stdout_state": "adopt", "default": "true"},
            {"args": ["config", "set", "auth.adopt_external_logins"], "set_argv": {"adopt": 3}},
            {"args": ["config", "get", "skills.external_dirs"], "stdout_state": "external_dirs", "default": "[]"},
            {"args": ["config", "set", "skills.external_dirs"], "set_argv": {"external_dirs": 3}},
        ],
        "pi": [
            {"args": ["--version"], "stdout": "$version\n"},
            {"args": ["auth", "check"], "when": {"logged_in": True}, "stdout": '{"status":"ready"}'},
            {"args": ["auth", "check"], "stdout": '{"status":"not_ready"}', "exit": 1},
        ],
        "omp": [
            {"args": ["--version"], "stdout": "omp/$version\n"},
            {
                "args": ["models", "openai-codex", "--json"],
                "when": {"logged_in": True},
                "stdout": '{"models":[{"provider":"openai-codex","id":"gpt"}]}',
            },
            {"args": ["models", "openai-codex", "--json"], "stdout": '{"models":[]}'},
            {"args": ["login", "openai-codex"], **login_set},
        ],
        "speckit": [
            {"args": ["--version"], "stdout": "specify $version\n"},
        ],
    }
    return [*table[hid], common_update]


BIN = {"claude": "claude", "codex": "codex", "hermes": "hermes", "pi": "pi", "omp": "omp", "speckit": "specify"}
LOCATIONS = {
    "claude": ".local/share/claude/versions/2.1.278",
    "codex": ".nvm/versions/node/v22.18.0/lib/node_modules/@openai/codex/bin/codex.js",
    "hermes": None,
    "pi": ".nvm/versions/node/v22.18.0/lib/node_modules/@earendil-works/pi-coding-agent/dist/cli.js",
    "omp": None,
    "speckit": ".local/share/uv/tools/specify-cli/bin/specify",
}
LATEST = {
    "claude": "2.1.283",
    "codex": "0.157.1",
    "hermes": "0.21.5",
    "pi": "0.87.1",
    "omp": "18.3.2",
    "speckit": "1.0.12",
}
INSTALLED = {
    "claude": "2.1.278",
    "codex": "0.156.0",
    "hermes": "0.21.4",
    "pi": "0.87.1",
    "omp": "18.3.2",
    "speckit": "1.0.12",
}


def install_fake(fh: FakeHome, hid: str, logged_in: bool = True, version: str | None = None) -> None:
    """Simulate an already-installed harness at its realistic channel location."""
    if hid == "hermes":
        (fh.root / ".hermes/hermes-agent/.git").mkdir(parents=True, exist_ok=True)
    state = {"version": version or INSTALLED[hid], "latest": LATEST[hid], "logged_in": logged_in}
    fh.write_fake(BIN[hid], harness_responses(hid), state=state, at=LOCATIONS[hid])


def stage_installer(fh: FakeHome, hid: str, url_part: str, logged_in: bool = False) -> None:
    """Make fake ``curl <url>`` emit an install script that puts the fake harness on PATH."""
    staged = fh.write_fake(
        BIN[hid],
        harness_responses(hid),
        state={"version": LATEST[hid], "latest": LATEST[hid], "logged_in": logged_in},
        staged=True,
    )
    if hid == "hermes":
        script = f"mkdir -p ~/.hermes/hermes-agent/.git && cp {staged} ~/.local/bin/hermes\n"
    else:
        script = f"cp {staged} ~/.local/bin/{BIN[hid]}\n"
    installers = getattr(fh, "_installers", [])
    installers.append({"args": ["-fsSL", url_part], "stdout": script})
    installers.append({"args": ["-LsSf", url_part], "stdout": script})
    fh._installers = installers
    fh.write_fake("curl", installers)


# --- HTTP mocking ------------------------------------------------------------------


@dataclass
class MockHttp:
    routes: dict[str, httpx.Response] = field(default_factory=dict)
    offline: bool = False
    requested: list[str] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requested.append(url)
        if self.offline:
            raise httpx.ConnectError("offline", request=request)
        if url in self.routes:
            return self.routes[url]
        return httpx.Response(404, text="not found")

    def json(self, url: str, data) -> None:
        self.routes[url] = httpx.Response(200, json=data)

    def text(self, url: str, body: str) -> None:
        self.routes[url] = httpx.Response(200, text=body)

    def bytes(self, url: str, body: bytes) -> None:
        self.routes[url] = httpx.Response(200, content=body)


def latest_routes(http: MockHttp, versions: dict[str, str] | None = None) -> None:
    v = LATEST | (versions or {})
    http.text("https://downloads.claude.ai/claude-code-releases/latest", v["claude"] + "\n")
    http.text("https://downloads.claude.ai/claude-code-releases/stable", "2.1.274\n")
    http.json("https://registry.npmjs.org/@openai/codex/latest", {"version": v["codex"]})
    http.json(
        "https://api.github.com/repos/NousResearch/hermes-agent/releases/latest",
        {"tag_name": "v2026.9.24", "name": f"Hermes Agent v{v['hermes']} (v2026.9.24)"},
    )
    http.json("https://pi.dev/api/latest-version", {"ok": True, "version": v["pi"]})
    http.json("https://registry.npmjs.org/@oh-my-pi/pi-coding-agent/latest", {"version": v["omp"]})
    http.json("https://pypi.org/pypi/specify-cli/json", {"info": {"version": v["speckit"]}})
    http.json("https://api.github.com/repos/omar2535/oh-my-ai/tags", [{"name": "v0.1.0"}])


def skills_tarball(skills: dict[str, dict[str, str]], top: str = "skills-abc") -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, files in skills.items():
            for rel, content in files.items():
                data = content.encode()
                info = tarfile.TarInfo(f"{top}/skills/productivity/{name}/{rel}")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


GRILL_TARBALL = {
    "grill-me": {"SKILL.md": "---\nname: grill-me\ndescription: d\n---\nCall grilling\n"},
    "grilling": {"SKILL.md": "---\nname: grilling\ndescription: d\n---\nInterview\n"},
}


@pytest.fixture
def http(monkeypatch):
    from omai import context

    mock = MockHttp()
    monkeypatch.setattr(context, "TRANSPORT", httpx.MockTransport(mock.handler))
    latest_routes(mock)
    from omai.config import MATTPOCOCK_PIN

    mock.bytes(f"https://codeload.github.com/mattpocock/skills/tar.gz/{MATTPOCOCK_PIN}", skills_tarball(GRILL_TARBALL))
    mock.json("https://api.github.com/repos/mattpocock/skills/commits/main", {"sha": MATTPOCOCK_PIN})
    return mock


# --- config / ctx helpers --------------------------------------------------------------


def write_config(fh: FakeHome, enabled: list[str], extra: str = "") -> Path:
    from omai.config import MATTPOCOCK_PIN

    path = fh.root / ".config/omai/config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for hid in ("claude", "codex", "hermes", "pi", "omp", "speckit"):
        lines.append(f"[harnesses.{hid}]\nenabled = {'true' if hid in enabled else 'false'}\n")
    lines.append(
        f'[[skills.sources]]\nrepo = "mattpocock/skills"\nref = "{MATTPOCOCK_PIN}"\ntrack = "main"\n'
        'skills = ["grill-me"]\n\n[[skills.sources]]\nbundled = true\nskills = ["grill-speckit"]\n'
    )
    path.write_text("\n".join(lines) + extra)
    return path


@pytest.fixture
def make_ctx(fake_home):
    from omai.context import load_ctx

    def build(enabled: list[str] | None = None):
        write_config(fake_home, enabled if enabled is not None else ["claude", "codex", "hermes", "pi", "omp"])
        ctx = load_ctx()
        ctx.os_kind = "linux"
        return ctx

    return build


@pytest.fixture
def cli(fake_home):
    from typer.testing import CliRunner

    from omai.cli import app

    runner = CliRunner()

    def invoke(*args: str):
        return runner.invoke(app, list(args))

    return invoke
