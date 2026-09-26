from conftest import install_fake

from omai.detect import detect
from omai.registry import load_registry


def test_channels_inferred_from_real_install_locations(fake_home):
    for hid in ("claude", "codex", "hermes", "omp"):
        install_fake(fake_home, hid)
    fake_home.write_fake("omp", [{"args": ["--version"], "stdout": "omp/18.3.2\n"}], at=".bun/bin/omp")
    registry = load_registry()
    found = {hid: detect(registry[hid]) for hid in ("claude", "codex", "hermes", "omp")}
    assert {hid: f.channel for hid, f in found.items()} == {
        "claude": "native",
        "codex": "npm",
        "hermes": "git",
        "omp": "bun",
    }
    assert found["claude"].version == "2.1.278"
    assert found["codex"].runtime_bound and not found["claude"].runtime_bound
    assert "omai migrate codex --to standalone" in found["codex"].warnings[0]


def test_absent_harness_is_none(fake_home):
    assert detect(load_registry()["codex"]) is None


def test_runtime_bound_install_hidden_by_node_switch_is_found_off_path(fake_home):
    install_fake(fake_home, "codex")
    (fake_home.bin / "codex").unlink()  # e.g. `nvm use` another Node version
    fake_home.write_fake("codex", [], at=".nvm/versions/node/v22.18.0/bin/codex")
    (fake_home.bin / "codex").unlink()
    found = detect(load_registry()["codex"])
    assert found is not None and not found.on_path and found.runtime_bound
    assert "not reinstalling" in found.warnings[0]


def test_unmet_node_requirement_is_warned(fake_home):
    install_fake(fake_home, "pi")
    fake_home.write_fake("node", [{"args": ["--version"], "stdout": "v22.18.0\n"}])
    found = detect(load_registry()["pi"])
    assert any("node >= 22.19 (found 22.18.0)" in w for w in found.warnings)
