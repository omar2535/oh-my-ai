"""Human (rich) and machine (JSON) rendering."""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from omai.converge import Summary

console = Console()

STATUS_STYLE = {"ok": "green", "failed": "red", "skipped": "yellow"}


def emit_json(data) -> None:
    print(json.dumps(data, indent=2, default=str))


def check_table(rows: list[dict], fetched_at: str | None = None) -> Table:
    table = Table(title=f"omai check{f' · {fetched_at}' if fetched_at else ''}")
    for col in ("item", "installed", "latest", "channel", "status", "notes"):
        table.add_column(col)
    for row in rows:
        if row.get("error") and not row.get("latest"):
            status = "[red]unknown[/]"
        elif row["installed"] is None:
            status = "[yellow]missing[/]"
        elif row["update_available"]:
            status = "[cyan]update[/]"
        else:
            status = "[green]current[/]"
        notes = list(row.get("warnings") or [])
        if row.get("error"):
            notes.append(f"latest lookup failed: {row['error']}")
        table.add_row(
            row["id"],
            row["installed"] or "-",
            row["latest"] or "-",
            row.get("channel") or "-",
            status,
            "\n".join(notes),
        )
    return table


def summary_table(summary: Summary, title: str = "omai up") -> Table:
    table = Table(title=title)
    for col in ("step", "result", "details"):
        table.add_column(col)
    for result in summary.results:
        style = STATUS_STYLE[result.status]
        table.add_row(result.step.description, f"[{style}]{result.status}[/]", result.message)
    return table


def summary_json(summary: Summary) -> dict:
    return {
        "ok": summary.ok,
        "steps": [{"id": r.step.id, "status": r.status, "message": r.message} for r in summary.results],
        "notes": summary.notes,
    }


def outcomes_table(title: str, rows: list[tuple[str, object]]) -> Table:
    table = Table(title=title)
    for col in ("item", "result", "details"):
        table.add_column(col)
    for item, outcome in rows:
        table.add_row(item, "[green]ok[/]" if outcome.ok else "[red]failed[/]", outcome.message)
    return table
