"""Opt-in checks against the real machine and network: `uv run pytest -m live`.

Read-only: probes versions, latest-version sources and auth status. Nothing is installed,
updated or logged in. Harnesses that aren't installed are skipped.
"""

import pytest

from omai import auth, versions
from omai.context import load_ctx
from omai.detect import detect

pytestmark = pytest.mark.live

HARNESSES = ["claude", "codex", "hermes", "pi", "omp", "speckit"]


@pytest.fixture(scope="module")
def ctx():
    return load_ctx()


@pytest.mark.parametrize("hid", HARNESSES)
def test_real_version_probe_and_channel(ctx, hid):
    found = detect(ctx.registry[hid])
    if found is None:
        pytest.skip(f"{hid} not installed")
    assert found.version, f"{hid} version regex no longer matches `--version` output"
    assert found.channel != "unknown", f"{hid} at {found.real} matches no registry channel"


@pytest.mark.parametrize("hid", [*HARNESSES, "omai"])
def test_real_latest_sources_resolve(ctx, hid):
    harness = ctx.registry[hid]
    with ctx.http() as client:
        try:
            latest = versions.fetch_latest(client, harness.latest, ctx.vars(harness))
        except Exception as exc:
            if hid == "omai":
                pytest.skip(f"omai has no published tags yet: {exc}")
            raise
    assert latest[0].isdigit()


@pytest.mark.parametrize("hid", ["claude", "codex", "hermes", "pi", "omp"])
def test_real_auth_status_commands_are_understood(ctx, hid):
    harness = ctx.registry[hid]
    found = detect(harness)
    if found is None or not found.on_path:
        pytest.skip(f"{hid} not installed")
    assert auth.auth_status(ctx, harness) in (auth.OK, auth.MISSING)


def test_hermes_config_get_parses(ctx):
    from omai.install import config_get, parse_list

    hermes = ctx.registry["hermes"]
    if detect(hermes) is None:
        pytest.skip("hermes not installed")
    assert config_get(ctx, hermes, "auth.adopt_external_logins") in ("true", "false")
    assert isinstance(parse_list(config_get(ctx, hermes, "skills.external_dirs")), list)
