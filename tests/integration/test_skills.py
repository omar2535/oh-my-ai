import os

from conftest import install_fake

from omai import config as config_mod
from omai import skills
from omai.install import parse_list

NAMES = {"grill-me", "grilling", "grill-speckit"}


def visible_skills(fake_home, ctx) -> dict[str, list[str]]:
    """Skill names each harness discovers, per its documented discovery dirs."""
    home = fake_home.root

    def names(*dirs):
        out = []
        for d in dirs:
            if d.is_dir():
                out += [p.name for p in d.iterdir() if (p / "SKILL.md").exists()]
        return out

    canonical = home / ".agents/skills"
    hermes_dirs = [home / ".hermes/skills"] + [
        home / d.removeprefix("~/") for d in parse_list(fake_home.state("hermes").get("external_dirs"))
    ]
    return {
        "claude": names(home / ".claude/skills"),  # Claude never reads .agents/
        "codex": names(canonical),
        "pi": names(home / ".pi/agent/skills", canonical),
        "omp": names(home / ".omp/agent/skills", canonical),  # ~/.claude/skills is opt-in, left off
        "hermes": names(*hermes_dirs),
    }


def test_each_harness_sees_each_skill_exactly_once(fake_home, http, make_ctx):
    install_fake(fake_home, "hermes")
    ctx = make_ctx()
    results = skills.sync(ctx)
    assert all(o.ok for _, o in results), results
    for harness, found in visible_skills(fake_home, ctx).items():
        assert sorted(found) == sorted(NAMES), harness
    link = fake_home.path(".claude/skills/grilling")
    assert link.is_symlink() and os.path.realpath(link) == str(fake_home.path(".agents/skills/grilling"))
    lock = skills.load_lock()["skills"]
    assert set(lock) == NAMES and lock["grilling"]["source"] == "mattpocock/skills"
    assert skills.plan(ctx) == []  # idempotent


def test_unmanaged_existing_skills_are_reported_not_overwritten(fake_home, http, make_ctx):
    mine = fake_home.path(".claude/skills/grilling")
    mine.mkdir(parents=True)
    (mine / "SKILL.md").write_text("my own")
    ctx = make_ctx(["claude"])
    results = skills.sync(ctx)
    conflicts = [a for a, o in results if a.kind == "conflict"]
    assert [a.name for a in conflicts] == ["grilling"]
    assert (mine / "SKILL.md").read_text() == "my own"


def test_drift_is_read_only(fake_home, http, make_ctx):
    ctx = make_ctx(["codex"])
    skills.sync(ctx)
    http.json("https://api.github.com/repos/mattpocock/skills/commits/main", {"sha": "f" * 40})
    before = skills.lock_path().read_text()
    rows = skills.drift(ctx)
    assert rows[0]["update_available"] and rows[0]["latest"] == "fffffff"
    assert skills.lock_path().read_text() == before


def test_removing_a_skill_cleans_canonical_link_and_lock(fake_home, http, make_ctx):
    ctx = make_ctx(["claude"])
    skills.sync(ctx)
    config_mod.remove_skill(ctx.config_path, "grill-speckit")
    ctx.reload_config()
    skills.sync(ctx)
    assert not fake_home.path(".agents/skills/grill-speckit").exists()
    assert not fake_home.path(".claude/skills/grill-speckit").is_symlink()
    assert "grill-speckit" not in skills.load_lock()["skills"]


def test_update_skills_moves_pin_to_upstream_head(fake_home, http, make_ctx):
    from conftest import GRILL_TARBALL, skills_tarball

    from omai import update

    ctx = make_ctx(["codex"])
    skills.sync(ctx)
    head = "a" * 40
    http.json("https://api.github.com/repos/mattpocock/skills/commits/main", {"sha": head})
    changed = {**GRILL_TARBALL, "grilling": {"SKILL.md": "---\nname: grilling\ndescription: d\n---\nv2\n"}}
    http.bytes(f"https://codeload.github.com/mattpocock/skills/tar.gz/{head}", skills_tarball(changed))
    outcome = update.update_skills(ctx)
    assert outcome.ok, outcome.message
    assert "v2" in fake_home.path(".agents/skills/grilling/SKILL.md").read_text()
    assert f'ref = "{head}"' in ctx.config_path.read_text()
