from conftest import install_fake

from omai.state import now_iso
from omai.tui.app import OmaiApp
from omai.tui.modals import ConfirmUninstall
from omai.tui.repos_screen import ReposScreen
from omai.tui.skills_screen import SkillsScreen


def record_terminal(monkeypatch):
    ran = []

    def fake_in_terminal(self, title, fn):
        ran.append((title, fn()))

    monkeypatch.setattr(OmaiApp, "in_terminal", fake_in_terminal)
    return ran


async def test_dashboard_renders_cached_rows_without_network(fake_home, http, make_ctx):
    install_fake(fake_home, "claude")
    ctx = make_ctx(["claude"])
    ctx.state.installs["claude"] = {"version": "2.1.278", "channel": "native", "warnings": []}
    ctx.state.data["checks"] = {"fetched_at": now_iso(), "items": {"claude": {"latest": "2.1.283", "error": None}}}
    app = OmaiApp(ctx)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        table = app.dash
        assert table.get_cell("claude", "installed") == "2.1.278"
        assert "2.1.283" in str(table.get_cell("claude", "latest"))
    assert http.requested == []


async def test_stale_cache_triggers_background_check(fake_home, http, make_ctx):
    install_fake(fake_home, "codex")
    app = OmaiApp(make_ctx(["codex"]))
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert "0.157.1" in str(app.dash.get_cell("codex", "latest"))
    assert any("registry.npmjs.org/@openai/codex" in url for url in http.requested)


async def test_update_key_runs_native_updater_for_selected_row(fake_home, http, make_ctx, monkeypatch):
    ran = record_terminal(monkeypatch)
    install_fake(fake_home, "claude")
    app = OmaiApp(make_ctx(["claude"]))
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("u")
        await pilot.pause()
    assert ran and ran[0][0] == "update Claude Code"
    assert ["update"] in fake_home.calls("claude")


async def test_uninstall_asks_and_keeps_config(fake_home, http, make_ctx, monkeypatch):
    ran = record_terminal(monkeypatch)
    install_fake(fake_home, "claude")
    app = OmaiApp(make_ctx(["claude"]))
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("x")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmUninstall)
        await pilot.click("#keep")
        await pilot.pause()
    assert ran and ran[0][1][0][1].ok
    assert not fake_home.path(".local/bin/claude").exists()
    assert fake_home.path(".claude/.credentials.json").exists()


async def test_skills_and_repos_screens_open(fake_home, http, make_ctx):
    app = OmaiApp(make_ctx(["claude"]))
    async with app.run_test() as pilot:
        await pilot.press("s")
        await pilot.pause()
        assert isinstance(app.screen, SkillsScreen)
        rows = app.screen.query_one("DataTable").row_count
        assert rows == 3  # grill-me, grilling, grill-speckit
        await pilot.press("escape")
        await pilot.press("r")
        await pilot.pause()
        assert isinstance(app.screen, ReposScreen)
