import threading

from conftest import LOGIN_URL, harness_responses, install_fake

from omai import auth


def test_login_all_is_status_first_and_leaves_pi_to_the_user(fake_home, cli):
    install_fake(fake_home, "claude", logged_in=False)
    install_fake(fake_home, "codex", logged_in=True)
    install_fake(fake_home, "hermes", logged_in=False)
    install_fake(fake_home, "pi", logged_in=False)
    install_fake(fake_home, "omp", logged_in=False)

    result = cli("login", "--all")

    assert result.exit_code == 0, result.output
    assert fake_home.calls("claude").count(["auth", "login"]) == 1
    assert ["login"] not in fake_home.calls("codex")  # would revoke the valid session
    assert ["auth", "add", "openai-codex"] in fake_home.calls("hermes")
    assert ["login", "openai-codex"] in fake_home.calls("omp")
    assert not any(argv[:1] == ["login"] for argv in fake_home.calls("pi"))
    assert "/login" in result.output
    assert fake_home.state("claude")["logged_in"] is True


def test_login_opens_the_printed_url_once(fake_home, make_ctx):
    install_fake(fake_home, "codex", logged_in=False)
    ctx = make_ctx(["codex"])
    result = auth.login(ctx, ctx.registry["codex"], echo=lambda _: None)
    assert result.ran and result.ok and result.after == auth.OK
    assert fake_home.calls("xdg-open") == [[LOGIN_URL]]


def test_concurrent_logins_never_overlap(fake_home, make_ctx):
    for hid in ("codex", "omp"):
        responses = harness_responses(hid)
        for r in responses:
            if r.get("set") == {"logged_in": True}:
                r["sleep"] = 0.4
        fake_home.write_fake(
            {"codex": "codex", "omp": "omp"}[hid], responses, state={"version": "1", "logged_in": False}
        )
    ctx = make_ctx(["codex", "omp"])
    threads = [
        threading.Thread(target=auth.login, args=(ctx, ctx.registry[h]), kwargs={"echo": lambda _: None})
        for h in ("codex", "omp")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    logins = sorted(
        (r for r in fake_home.invocations() if r["argv"][:1] == ["login"] and r["argv"] != ["login", "status"]),
        key=lambda r: r["start"],
    )
    assert len(logins) == 2
    assert logins[0]["end"] <= logins[1]["start"]


def test_force_login_warns_when_it_revokes(fake_home, make_ctx):
    install_fake(fake_home, "codex", logged_in=True)
    ctx = make_ctx(["codex"])
    said = []
    auth.login(ctx, ctx.registry["codex"], force=True, echo=said.append)
    assert any("revokes" in line for line in said)
    assert ["login"] in fake_home.calls("codex")


def test_status_reports_auth_without_reading_credentials(fake_home, cli):
    install_fake(fake_home, "claude", logged_in=False)
    install_fake(fake_home, "pi", logged_in=False)
    result = cli("status", "--json")
    assert result.exit_code == 0
    import json

    rows = {r["id"]: r for r in json.loads(result.output)}
    assert rows["claude"]["auth"] == "missing"
    assert rows["pi"]["auth"] == "missing" and "/login" in rows["pi"]["hint"]
    # the fake_home fixture fails the test if any canary credential file was opened
