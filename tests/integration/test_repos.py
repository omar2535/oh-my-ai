import shutil

from omai import repos

STATUS = {
    "args": ["integration", "status", "--json"],
    "json_from_state": {"status": "status", "installed_integrations": "integrations", "default_integration": "default"},
}


def fake_specify(fake_home, version="1.0.12", state=None):
    fake_home.write_fake(
        "specify",
        [
            {"args": ["--version"], "stdout": "specify $version\n"},
            {
                "args": ["init"],
                "sh": "mkdir -p .specify",
                "set": {"status": "ok", "integrations": ["omp"], "default": "omp"},
            },
            STATUS,
            {"args": ["integration", "install"], "append_argv": {"integrations": 2}},
            {"args": ["integration", "use"], "set_argv": {"default": 2}},
            {"args": ["integration", "upgrade"]},
        ],
        state={"version": version, **(state or {})},
        at=".local/share/uv/tools/specify-cli/bin/specify",
    )


def test_init_installs_four_integrations_with_omp_default_and_no_hermes(fake_home, make_ctx, tmp_path):
    fake_specify(fake_home)
    repo = tmp_path / "proj"
    repo.mkdir()
    ctx = make_ctx()

    report = repos.init(ctx, str(repo))

    assert report.ok, report.notes
    calls = fake_home.calls("specify")
    assert calls[1][:4] == ["init", "--here", "--force", "--integration"] and calls[1][4] == "omp"
    installs = [c[2] for c in calls if c[:2] == ["integration", "install"]]
    assert installs == ["claude", "codex", "pi"]
    assert not any("hermes" in c for call in calls for c in call)
    assert any("hermes skills trust" in n for n in report.notes)
    assert ctx.state.repos[0]["path"] == str(repo) and ctx.state.repos[0]["default"] == "omp"


def test_init_is_idempotent_on_initialized_repo(fake_home, make_ctx, tmp_path):
    fake_specify(fake_home, state={"status": "ok", "integrations": ["omp", "claude", "codex", "pi"], "default": "omp"})
    repo = tmp_path / "proj"
    (repo / ".specify").mkdir(parents=True)
    report = repos.init(make_ctx(), str(repo))
    assert report.ok and report.steps == []
    assert not any(c[:1] == ["init"] or c[:2] == ["integration", "install"] for c in fake_home.calls("specify"))


def test_old_speckit_is_refused(fake_home, make_ctx, tmp_path):
    fake_specify(fake_home, version="0.16.2")
    report = repos.init(make_ctx(), str(tmp_path))
    assert not report.ok and "omai update speckit" in report.notes[0]
    assert fake_home.calls("specify") == [["--version"]]


def test_refresh_upgrades_integrations_and_flags_missing_repos(fake_home, make_ctx, tmp_path):
    fake_specify(fake_home)
    ctx = make_ctx()
    keep, gone = tmp_path / "keep", tmp_path / "gone"
    for repo in (keep, gone):
        repo.mkdir()
        repos.init(ctx, str(repo))
    shutil.rmtree(gone)

    reports = {r.path: r for r in repos.refresh_all(ctx)}

    assert reports[str(keep)].ok
    upgrades = [c[2] for c in fake_home.calls("specify") if c[:2] == ["integration", "upgrade"]]
    assert sorted(upgrades) == ["claude", "codex", "omp", "pi"]
    assert not reports[str(gone)].ok and "no longer exists" in reports[str(gone)].notes[0]
    assert repos.repo_health(ctx, {"path": str(gone)}) == "missing"
