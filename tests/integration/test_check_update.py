import hashlib
import json

from conftest import install_fake, latest_routes, write_config


def tree_digest(root, exclude):
    """Hash paths, sizes and mtimes (not contents: credential canaries must stay unopened)."""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if not str(p).startswith(str(exclude))):
        stat = path.lstat()
        mtime = 0 if path.is_dir() else stat.st_mtime_ns  # dir mtimes move when omai creates its state dir
        digest.update(f"{path}:{stat.st_size}:{mtime}".encode())
    return digest.hexdigest()


def all_installed(fake_home):
    for hid in ("claude", "codex", "hermes", "pi", "omp", "speckit"):
        install_fake(fake_home, hid)
    write_config(fake_home, ["claude", "codex", "hermes", "pi", "omp", "speckit"])


def test_check_is_read_only_and_reports_updates(fake_home, http, cli):
    all_installed(fake_home)
    before = tree_digest(fake_home.root, fake_home.path(".local/state"))

    result = cli("check", "--json")

    assert result.exit_code == 0, result.output
    assert tree_digest(fake_home.root, fake_home.path(".local/state")) == before
    rows = {r["id"]: r for r in json.loads(result.output)["items"]}
    assert rows["claude"]["update_available"] and rows["claude"]["latest"] == "2.1.283"
    assert rows["hermes"]["update_available"] and rows["hermes"]["latest"] == "0.21.5"
    assert not rows["pi"]["update_available"]
    assert rows["codex"]["channel"] == "npm" and any("runtime-bound" in w for w in rows["codex"]["warnings"])
    assert rows["skills:mattpocock/skills"]["update_available"] is False
    assert set(rows["omai"]) >= {"installed", "latest", "channel", "update_available", "warnings", "error"}
    assert not [c for c in fake_home.invocations() if c["argv"][:1] == ["update"]]


def test_exit_code_mode(fake_home, http, cli):
    all_installed(fake_home)
    assert cli("check", "--exit-code").exit_code == 1
    latest_routes(http, {"claude": "2.1.278", "codex": "0.156.0", "hermes": "0.21.4", "speckit": "1.0.12"})
    http.json("https://api.github.com/repos/omar2535/oh-my-ai/tags", [{"name": "v0.0.0"}])
    assert cli("check", "--exit-code").exit_code == 0


def test_offline_check_exits_2_and_keeps_cached_latest(fake_home, http, cli):
    all_installed(fake_home)
    cli("check")
    http.offline = True
    result = cli("check", "--json")
    assert result.exit_code == 2
    rows = {r["id"]: r for r in json.loads(result.output)["items"]}
    assert rows["claude"]["latest"] == "2.1.283" and "network error" in rows["claude"]["error"]


def test_claude_stable_channel(fake_home, http, cli):
    install_fake(fake_home, "claude")
    write_config(fake_home, ["claude"], extra='\n[harnesses.claude]\nrelease_channel = "stable"\n')
    config = fake_home.path(".config/omai/config.toml")
    config.write_text(config.read_text().replace("[harnesses.claude]\nenabled = true\n", "", 1))
    rows = {r["id"]: r for r in json.loads(cli("check", "--json").output)["items"]}
    assert rows["claude"]["latest"] == "2.1.274" and not rows["claude"]["update_available"]


def test_update_uses_native_updaters(fake_home, http, cli):
    all_installed(fake_home)
    fake_home.write_fake("uv", [{"args": ["tool"], "stdout": "ok\n"}])

    result = cli("update", "claude", "hermes")

    assert result.exit_code == 0, result.output
    assert ["update"] in fake_home.calls("claude") and ["update"] in fake_home.calls("hermes")
    assert ["update"] not in fake_home.calls("codex")
    assert fake_home.state("claude")["version"] == "2.1.283"


def test_update_all_covers_speckit_skills_and_self(fake_home, http, cli):
    all_installed(fake_home)
    fake_home.write_fake("uv", [{"args": ["tool"], "stdout": "ok\n"}])
    result = cli("update", "--all")
    assert result.exit_code == 0, result.output
    assert ["tool", "install", "--force", "specify-cli"] in fake_home.calls("uv")
    assert ["tool", "upgrade", "omai"] in fake_home.calls("uv")
    for bin_ in ("claude", "codex", "hermes", "pi", "omp"):
        assert ["update"] in fake_home.calls(bin_)
