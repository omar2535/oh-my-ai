import pytest

from omai import config as config_mod
from omai.config import ConfigError, load_config
from omai.registry import load_registry


@pytest.fixture
def registry():
    return load_registry()


def test_missing_config_writes_defaults_with_all_harnesses_and_default_skills(tmp_path, registry):
    path = tmp_path / "config.toml"
    cfg = load_config(path, registry)
    assert path.exists()
    assert set(cfg.enabled()) == {"claude", "codex", "hermes", "pi", "omp", "speckit"}
    assert {"grill-me", "grilling", "grill-speckit"} <= set(cfg.desired_skills())
    assert cfg.harnesses["claude"].release_channel == "latest"
    assert cfg.harnesses["omp"].provider == "openai-codex"


def test_unknown_harness_is_a_config_error(tmp_path, registry):
    path = tmp_path / "config.toml"
    path.write_text("[harnesses.cursor]\nenabled = true\n")
    with pytest.raises(ConfigError, match="cursor"):
        load_config(path, registry)


def test_omai_itself_is_not_a_configurable_harness(tmp_path, registry):
    path = tmp_path / "config.toml"
    path.write_text("[harnesses.omai]\nenabled = true\n")
    with pytest.raises(ConfigError):
        load_config(path, registry)


def test_grill_me_always_brings_grilling(tmp_path, registry):
    path = tmp_path / "config.toml"
    path.write_text('[[skills.sources]]\nrepo = "o/r"\nref = "abc"\nskills = ["grill-me"]\n')
    assert set(load_config(path, registry).desired_skills()) == {"grill-me", "grilling"}


def test_edits_preserve_user_comments(tmp_path, registry):
    path = tmp_path / "config.toml"
    load_config(path, registry)
    path.write_text(path.read_text() + "\n# my note\n")
    config_mod.set_harness_enabled(path, "hermes", False)
    config_mod.add_skill_source(path, "someone/skills", "deadbeef", ["tdd"])
    text = path.read_text()
    assert "# my note" in text
    cfg = load_config(path, registry)
    assert not cfg.harnesses["hermes"].enabled
    assert cfg.desired_skills()["tdd"].ref == "deadbeef"


def test_removing_last_skill_drops_the_source(tmp_path, registry):
    path = tmp_path / "config.toml"
    load_config(path, registry)
    config_mod.add_skill_source(path, "someone/skills", "deadbeef", ["tdd"])
    assert config_mod.remove_skill(path, "tdd")
    assert all(s.repo != "someone/skills" for s in load_config(path, registry).skill_sources)
    assert not config_mod.remove_skill(path, "tdd")


def test_invalid_release_channel(tmp_path, registry):
    path = tmp_path / "config.toml"
    path.write_text('[harnesses.claude]\nrelease_channel = "nightly"\n')
    with pytest.raises(ConfigError, match="release_channel"):
        load_config(path, registry)
