"""Tracked spec-kit repos screen."""

from __future__ import annotations

import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from omai import repos
from omai.tui.modals import PromptScreen


class ReposScreen(Screen):
    BINDINGS = [
        Binding("i", "init", "Init repo"),
        Binding("f", "refresh", "Refresh all"),
        Binding("d", "remove", "Untrack"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="repos", cursor_type="row")
        yield Static("", id="repos-status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(DataTable).add_columns("health", "path", "integrations", "default", "spec-kit")
        self.reload()

    def reload(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for repo in self.ctx.state.repos:
            table.add_row(
                repos.repo_health(self.ctx, repo),
                repo["path"],
                ", ".join(repo.get("integrations", [])),
                repo.get("default") or "—",
                repo.get("speckit_version") or "—",
                key=repo["path"],
            )

    def _terminal(self, title: str, fn) -> None:
        with self.app.suspend():
            print(f"\n=== {title} ===")
            for report in fn():
                print(f"{'✓' if report.ok else '✗'} {report.path}")
                for line in report.steps + report.notes:
                    print(f"   {line}")
            input("\nPress Enter to return to omai…")
        self.reload()

    def action_init(self) -> None:
        def chosen(path: str | None) -> None:
            if path:
                self._terminal(f"omai init {path}", lambda: [repos.init(self.ctx, os.path.expanduser(path))])

        self.app.push_screen(PromptScreen("Initialize spec-kit in which repo?", os.getcwd()), chosen)

    def action_refresh(self) -> None:
        self._terminal("refresh tracked repos", lambda: repos.refresh_all(self.ctx))

    def action_remove(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count:
            path = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
            repos.untrack(self.ctx, path)
            self.reload()
