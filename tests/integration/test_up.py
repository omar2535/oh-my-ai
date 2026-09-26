from conftest import install_fake, stage_installer, write_config

HERMES_URL = "https://hermes-agent.nousresearch.com/install.sh"
OMP_URL = "https://omp.sh/install"


def installs(fake_home):
    return [argv[1] for argv in fake_home.calls("curl")]


def test_up_adopts_existing_installs_and_installs_the_rest(fake_home, http, cli):
    install_fake(fake_home, "claude", logged_in=True)
    install_fake(fake_home, "codex", logged_in=True)
    stage_installer(fake_home, "hermes", HERMES_URL)
    stage_installer(fake_home, "omp", OMP_URL)
    write_config(fake_home, ["claude", "codex", "hermes", "omp"])

    result = cli("up")

    assert result.exit_code == 0, result.output
    assert installs(fake_home) == [HERMES_URL, OMP_URL]  # nothing reinstalled
    assert ["login"] not in fake_home.calls("codex")
    assert ["auth", "login"] not in fake_home.calls("claude")
    assert ["auth", "add", "openai-codex"] in fake_home.calls("hermes")
    assert ["login", "openai-codex"] in fake_home.calls("omp")
    assert fake_home.state("hermes")["adopt"] == "false"
    assert (fake_home.path(".agents/skills/grilling/SKILL.md")).exists()
    assert fake_home.path(".claude/skills/grill-speckit").is_symlink()


def test_second_up_is_a_no_op(fake_home, http, cli):
    for hid in ("claude", "codex", "hermes", "omp"):
        stage_installer(
            fake_home,
            hid,
            {
                "claude": "https://claude.ai/install.sh",
                "codex": "https://chatgpt.com/codex/install.sh",
                "hermes": HERMES_URL,
                "omp": OMP_URL,
            }[hid],
        )
    write_config(fake_home, ["claude", "codex", "hermes", "omp"])
    assert cli("up").exit_code == 0
    before = len(fake_home.invocations())

    second = cli("up")

    assert second.exit_code == 0, second.output
    assert "nothing to do" in second.output
    new = fake_home.invocations()[before:]
    mutating = [
        r
        for r in new
        if r["argv"] in (["login"], ["update"])
        or r["argv"][:2] in (["auth", "login"], ["auth", "add"], ["config", "set"], ["login", "openai-codex"])
    ]
    assert mutating == [] and not any(r["bin"] == "curl" for r in new)


def test_failure_continues_and_skips_dependents(fake_home, http, cli):
    fake_home.write_fake(
        "curl",
        [
            {"args": ["-fsSL", HERMES_URL], "stdout": "exit 3\n"},
        ],
    )
    stage_installer(fake_home, "omp", OMP_URL)
    fake_home.write_fake("curl", [{"args": ["-fsSL", HERMES_URL], "stdout": "exit 3\n"}, *fake_home._installers])
    write_config(fake_home, ["hermes", "omp"])

    result = cli("up", "--json")

    assert result.exit_code == 1
    import json

    steps = {s["id"]: s["status"] for s in json.loads(result.stdout)["steps"]}
    assert steps["install:hermes"] == "failed"
    assert steps["configure:hermes:auth.adopt_external_logins"] == "skipped"
    assert steps["login:hermes"] == "skipped"
    assert steps["install:omp"] == "ok" and steps["login:omp"] == "ok"


def test_runtime_bound_install_hidden_from_path_is_not_reinstalled(fake_home, http, cli):
    fake_home.write_fake("codex", [], at=".nvm/versions/node/v22.18.0/bin/codex")
    (fake_home.bin / "codex").unlink()
    write_config(fake_home, ["codex"])

    result = cli("up", "--no-login")

    assert "not reinstalling" in result.output
    assert fake_home.calls("curl") == []


def test_up_never_invokes_sudo(fake_home, http, cli):
    stage_installer(fake_home, "hermes", HERMES_URL)
    write_config(fake_home, ["hermes"])
    cli("up")
    assert not any("sudo" in " ".join(r["argv"]) for r in fake_home.invocations())
