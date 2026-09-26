"""Dashboard table: one row per managed item."""

from __future__ import annotations

from textual.widgets import DataTable

from omai import versions

COLUMNS = ("item", "installed", "latest", "channel", "auth", "notes")


def row_from_state(ctx, harness) -> dict:
    """Build a row from cached state only (no subprocesses, no network)."""
    install = ctx.state.installs.get(harness.id) or {}
    latest = versions.cached(ctx).get(harness.id)
    auth = ctx.state.auth.get(harness.id, {}).get("status", "?")
    return {
        "id": harness.id,
        "installed": install.get("version"),
        "latest": latest.version if latest else None,
        "channel": install.get("channel"),
        "auth": auth if harness.auth_status else "n/a",
        "warnings": install.get("warnings", []),
        "update_available": versions.is_newer(latest.version if latest else None, install.get("version")),
    }


class Dashboard(DataTable):
    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        for column in COLUMNS:
            self.add_column(column, key=column)

    def upsert(self, row: dict) -> None:
        installed = row.get("installed") or "—"
        latest = row.get("latest") or "…"
        if row.get("update_available"):
            latest = f"[b cyan]{latest} ↑[/]"
        auth = row.get("auth", "?")
        auth_cell = {"ok": "[green]ok[/]", "missing": "[red]login[/]", "unknown": "[yellow]?[/]"}.get(auth, auth)
        notes = "; ".join(row.get("warnings") or [])
        cells = (row["id"], installed, latest, row.get("channel") or "—", auth_cell, notes)
        if row["id"] in self.rows:
            for column, value in zip(COLUMNS, cells, strict=True):
                self.update_cell(row["id"], column, value)
        else:
            self.add_row(*cells, key=row["id"])

    def selected_id(self) -> str | None:
        if self.row_count == 0:
            return None
        return self.coordinate_to_cell_key(self.cursor_coordinate).row_key.value
