"""Skills management screen."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from omai import config as config_mod
from omai import skills
from omai.config import SkillSource
from omai.tui.modals import PromptScreen


class SkillsScreen(Screen):
    BINDINGS = [
        Binding("a", "add", "Add source"),
        Binding("d", "remove", "Remove skill"),
        Binding("y", "sync", "Sync"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="skills", cursor_type="row")
        yield Static("", id="skills-status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("skill", "source", "ref", "state")
        self.reload()

    def reload(self) -> None:
        self.ctx.reload_config()
        table = self.query_one(DataTable)
        table.clear()
        lock = skills.load_lock()["skills"]
        pending = {a.name: a for a in skills.plan(self.ctx)}
        for name, source in self.ctx.config.desired_skills().items():
            entry = lock.get(name, {})
            action = pending.get(name)
            state = action.kind if action else ("installed" if entry else "missing")
            table.add_row(name, source.label, (entry.get("ref") or source.ref)[:12], state, key=name)

    def status(self, text: str) -> None:
        self.query_one("#skills-status", Static).update(text)

    def action_add(self) -> None:
        def added(answer: str | None) -> None:
            if not answer:
                return
            source, _, names = answer.partition(" ")
            skill_names = [n for n in names.replace(",", " ").split() if n]
            if not skill_names:
                self.status("format: owner/repo[@ref] skill1,skill2")
                return
            self.add_source(source, skill_names)

        self.app.push_screen(PromptScreen("Add skills", "owner/repo[@ref] skill1,skill2"), added)

    @work(thread=True)
    def add_source(self, source: str, names: list[str]) -> None:
        repo, _, ref = source.partition("@")
        try:
            ref = ref or skills.upstream_head(self.ctx, SkillSource(skills=names, repo=repo))
        except Exception as exc:  # surface network problems in the status line
            self.app.call_from_thread(self.status, f"could not resolve {repo}: {exc}")
            return
        config_mod.add_skill_source(self.ctx.config_path, repo, ref, names)
        self.sync()

    def action_remove(self) -> None:
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return
        name = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        config_mod.remove_skill(self.ctx.config_path, name)
        self.sync()

    def action_sync(self) -> None:
        self.sync()

    @work(thread=True, exclusive=True)
    def sync(self) -> None:
        self.app.call_from_thread(self.status, "syncing…")
        self.ctx.reload_config()
        results = skills.sync(self.ctx)
        failed = [f"{a.name}: {o.message}" for a, o in results if not o.ok]
        self.app.call_from_thread(self.reload)
        self.app.call_from_thread(self.status, "; ".join(failed) or f"synced ({len(results)} change(s))")
