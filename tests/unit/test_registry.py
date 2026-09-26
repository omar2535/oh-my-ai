import re
from pathlib import Path

import pytest

from omai.detect import parse_version
from omai.registry import RegistryError, load_registry

# Real `--version` output captured on 2026-09-26 (research.md R1).
REAL_VERSION_OUTPUT = {
    "claude": ("2.1.278 (Claude Code)", "2.1.278"),
    "codex": ("codex-cli 0.156.0", "0.156.0"),
    "hermes": ("Hermes Agent v0.21.4 (2026.9.21) · upstream d3b25b52\nInstall directory: ~/.hermes", "0.21.4"),
    "pi": ("0.87.1", "0.87.1"),
    "omp": ("omp/18.3.2", "18.3.2"),
    "speckit": ("specify 0.16.2", "0.16.2"),
}


def test_packaged_registry_loads_and_covers_every_harness():
    registry = load_registry()
    assert {"claude", "codex", "hermes", "pi", "omp", "speckit", "omai"} <= set(registry.harnesses)


@pytest.mark.parametrize("hid", sorted(REAL_VERSION_OUTPUT))
def test_version_regex_parses_real_output(hid):
    output, expected = REAL_VERSION_OUTPUT[hid]
    assert parse_version(load_registry()[hid], output) == expected


def test_real_auth_outputs_parse():
    registry = load_registry()
    hermes = registry["hermes"].auth_status
    assert re.search(hermes.expr, "openai-codex: logged in")
    assert not re.search(hermes.expr, "openai-codex: logged out")


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "r.toml"
    path.write_text(body)
    return path


BASE = """
[x]
bin = "x"
version = {{ cmd = ["x", "--version"], regex = '{regex}' }}
latest = {{ kind = "npm", ref = "x" }}
update = ["x", "update"]
login = {{ mode = "{mode}"{login_extra} }}
[[x.channels]]
id = "a"
install = {install}
uninstall = ["rm", "x"]
"""


def entry(regex="x (\\\\S+)", mode="none", login_extra="", install='["sh", "-c", "curl x | sh"]'):
    return BASE.format(regex=regex, mode=mode, login_extra=login_extra, install=install)


@pytest.mark.parametrize(
    "body, message",
    [
        (entry(regex="x (\\\\S+"), "bad regex"),
        (entry(mode="command"), "requires argv"),
        (entry(mode="manual"), "requires hint"),
        (entry(mode="weird"), "login.mode"),
        (entry(install='["sudo", "apt", "install", "x"]'), "sudo"),
        (entry(install='["sh", "-c", "curl x | sudo sh"]'), "sudo"),
    ],
)
def test_invalid_entries_are_rejected(tmp_path, body, message):
    with pytest.raises(RegistryError, match=message):
        load_registry(_write(tmp_path, body))


def test_entry_without_channels_is_rejected(tmp_path):
    body = entry().split("[[x.channels]]")[0]
    with pytest.raises(RegistryError, match="channel"):
        load_registry(_write(tmp_path, body))
