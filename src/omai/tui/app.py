"""omai dashboard (Textual)."""

from __future__ import annotations

from collections.abc import Callable

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from omai import auth, install, update, versions
from omai.context import Ctx
from omai.install import Outcome
from omai.tui.dashboard import Dashboard, row_from_state
from omai.tui.modals import ConfirmUninstall
from omai.tui.repos_screen import ReposScreen
from omai.tui.skills_screen import SkillsScreen


class OmaiApp(App):
    TITLE = "omai"
    SUB_TITLE = "coding-agent harnesses"
    BINDINGS = [
        Binding("i", "install", "Install"),
        Binding("u", "update", "Update"),
        Binding("U", "update_all", "Update all"),
        Binding("l", "login", "Login"),
        Binding("L", "login_all", "Login all"),
        Binding("x", "uninstall", "Uninstall"),
        Binding("s", "skills", "Skills"),
        Binding("r", "repos", "Repos"),
        Binding("c", "check", "Check now"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, ctx: Ctx):
        super().__init__()
        self.ctx = ctx

    def compose(self) -> ComposeResult:
        yield Header()
        yield Dashboard(id="dash")
        yield Static("", id="status")
        yield Footer()

    @property
    def dash(self) -> Dashboard:
        return self.query_one(Dashboard)

    def set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    def targets(self):
        return update.check_targets(self.ctx)

    def on_mount(self) -> None:
        for harness in self.targets():
            self.dash.upsert(row_from_state(self.ctx, harness))
        self.run_check(refresh=versions.cache_stale(self.ctx))
        self.run_auth()

    # --- background workers -------------------------------------------------

    @work(thread=True, exclusive=True, group="check")
    def run_check(self, refresh: bool) -> None:
        self.call_from_thread(self.set_status, "checking for updates…" if refresh else "detecting installs…")
        rows = update.check_rows(self.ctx, refresh=refresh, include_skills=False)
        for row in rows:
            row["auth"] = row_from_state(self.ctx, self.ctx.registry[row["id"]])["auth"]
            self.call_from_thread(self.dash.upsert, row)
        outdated = sum(r["update_available"] for r in rows)
        self.call_from_thread(self.set_status, f"{outdated} update(s) available" if outdated else "all current")

    @work(thread=True, exclusive=True, group="auth")
    def run_auth(self) -> None:
        for harness in self.ctx.managed():
            if harness.auth_status is None or harness.id not in self.ctx.state.installs:
                continue
            auth.auth_status(self.ctx, harness)
            self.call_from_thread(self.dash.upsert, row_from_state(self.ctx, harness))

    # --- terminal-bound actions (suspend the UI; installers and logins are interactive) --

    def in_terminal(self, title: str, fn: Callable[[], list[tuple[str, Outcome]]]) -> None:
        with self.suspend():
            print(f"\n=== {title} ===")
            results = fn()
            for item, outcome in results:
                print(f"{'✓' if outcome.ok else '✗'} {item}: {outcome.message}")
            input("\nPress Enter to return to omai…")
        self.run_check(refresh=False)
        self.run_auth()

    def _selected(self):
        hid = self.dash.selected_id()
        return self.ctx.registry[hid] if hid else None

    def action_install(self) -> None:
        harness = self._selected()
        if harness is None or harness.kind == "self":
            return
        channel = install.choose_channel(harness, self.ctx.config.harnesses.get(harness.id).channel)
        self.in_terminal(f"install {harness.name}", lambda: [(harness.id, install.install(self.ctx, harness, channel))])

    def action_update(self) -> None:
        harness = self._selected()
        if harness is not None:
            self.in_terminal(f"update {harness.name}", lambda: update.update(self.ctx, [harness.id]))

    def action_update_all(self) -> None:
        ids = update.resolve_targets(self.ctx, [], all_=True)
        self.in_terminal("update all", lambda: update.update(self.ctx, ids))

    def _login(self, harnesses) -> list[tuple[str, Outcome]]:
        results = []
        for harness in harnesses:
            result = auth.login(self.ctx, harness)
            results.append((harness.id, Outcome(result.ok, result.message)))
        return results

    def action_login(self) -> None:
        harness = self._selected()
        if harness is not None and harness.login.mode != "none":
            self.in_terminal(f"login {harness.name}", lambda: self._login([harness]))

    def action_login_all(self) -> None:
        targets = [h for h in self.ctx.managed() if h.login.mode != "none"]
        self.in_terminal("login all", lambda: self._login(targets))

    def action_uninstall(self) -> None:
        harness = self._selected()
        if harness is None or harness.kind == "self":
            return

        def chosen(choice: str | None) -> None:
            if choice in ("keep", "purge"):
                purge = choice == "purge"
                self.in_terminal(
                    f"uninstall {harness.name}",
                    lambda: [(harness.id, install.uninstall(self.ctx, harness, purge=purge))],
                )

        self.push_screen(ConfirmUninstall(harness), chosen)

    def action_skills(self) -> None:
        self.push_screen(SkillsScreen(self.ctx))

    def action_repos(self) -> None:
        self.push_screen(ReposScreen(self.ctx))

    def action_check(self) -> None:
        self.run_check(refresh=True)
