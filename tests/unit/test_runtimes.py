from omai import install
from omai.registry import Requirement, load_registry


def test_first_preferred_channel_uses_standalone_installer(fake_home):
    registry = load_registry()
    assert install.choose_channel(registry["codex"]).id == "standalone"
    assert install.choose_channel(registry["pi"]).id == "managed"
    assert install.choose_channel(registry["omp"]).id == "binary"
    assert install.choose_channel(registry["codex"], "npm").id == "npm"


def test_node_cannot_be_installed_by_omai_and_hint_never_sudo(fake_home):
    outcome = install.ensure_runtime(Requirement("node", "22.19"))
    assert not outcome.ok
    assert "node >= 22.19" in outcome.message and "never uses sudo" in outcome.message


def test_bun_installed_user_local_via_official_script(fake_home):
    fake_home.write_fake("curl", [{"args": ["-fsSL", "https://bun.sh/install"], "stdout": "echo bun-installed\n"}])
    assert install.ensure_runtime(Requirement("bun", "1.3.14")).ok
    assert fake_home.calls("curl") == [["-fsSL", "https://bun.sh/install"]]


def test_missing_bubblewrap_is_a_hint_not_an_action(fake_home, monkeypatch):
    monkeypatch.setattr(install.shutil, "which", lambda name: None)
    hints = install.system_prereq_hints(load_registry()["codex"], "linux")
    assert hints and "bubblewrap" in hints[0]
    assert install.system_prereq_hints(load_registry()["codex"], "macos") == []
