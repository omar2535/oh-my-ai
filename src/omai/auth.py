"""Auth status probes and serialized native logins.

omai never reads or writes harness credentials: status comes from each harness's own
command and logins are the harness's own flow (constitution principle I).
"""

from __future__ import annotations

import fcntl
import json
import re
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass

from omai import platform, runner
from omai.context import Ctx
from omai.registry import HarnessDef
from omai.state import now_iso

OK, MISSING, UNKNOWN, NA = "ok", "missing", "unknown", "n/a"


def auth_status(ctx: Ctx, harness: HarnessDef) -> str:
    spec = harness.auth_status
    if spec is None:
        return NA
    values = ctx.vars(harness)
    result = runner.run(runner.fill(spec.argv, values), timeout=spec.timeout)
    if result.code in (124, 127):
        status = UNKNOWN
    elif spec.parse == "exit_code":
        status = OK if result.ok else MISSING
    elif spec.parse == "json_path":
        try:
            data = json.loads(result.stdout)
            for part in spec.expr.split("."):
                data = data[part]
            status = OK if data else MISSING
        except (ValueError, KeyError, TypeError):
            status = UNKNOWN
    else:
        pattern = spec.expr
        for key, value in values.items():
            pattern = pattern.replace("{" + key + "}", re.escape(value))
        status = OK if re.search(pattern, result.output) else MISSING
    ctx.state.auth[harness.id] = {"status": status, "checked_at": now_iso()}
    ctx.state.save()
    return status


def manual_hint(ctx: Ctx, harness: HarnessDef) -> str:
    return runner.fill([harness.login.hint], ctx.vars(harness))[0]


@contextmanager
def login_lock(ctx: Ctx):
    """Serialize logins across omai processes: several harnesses share callback ports."""
    path = platform.state_dir() / "login.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


@dataclass
class LoginResult:
    id: str
    before: str
    after: str
    ran: bool
    message: str = ""
    ok: bool = True


def login(
    ctx: Ctx,
    harness: HarnessDef,
    force: bool = False,
    echo: Callable[[str], None] = print,
) -> LoginResult:
    if harness.login.mode == "none":
        return LoginResult(harness.id, NA, NA, False, "no login needed")
    before = auth_status(ctx, harness)
    if harness.login.mode == "manual":
        if before == OK:
            return LoginResult(harness.id, before, before, False, "already logged in")
        hint = manual_hint(ctx, harness)
        echo(f"ℹ️  {harness.name}: {hint}")
        return LoginResult(harness.id, before, before, False, hint)  # manual: nothing to fail
    if before == OK and not force:
        return LoginResult(harness.id, before, before, False, "already logged in")
    if before == OK and harness.login.revokes_existing:
        echo(f"⚠️  {harness.name} login revokes the existing session before signing in again.")

    opened: list[str] = []

    def on_output(chunk: str) -> None:
        if opened:
            return
        urls = platform.find_urls(chunk)
        if urls:
            opened.append(urls[0])
            platform.open_url(urls[0], ctx.os_kind, echo=echo)

    with login_lock(ctx):
        echo(f"🔐 Logging in to {harness.name} ({ctx.vars(harness)['provider']})…")
        code = runner.run_interactive(runner.fill(harness.login.argv, ctx.vars(harness)), on_output)
    after = auth_status(ctx, harness)
    message = "logged in" if after == OK else f"login exited {code}; status {after}"
    return LoginResult(harness.id, before, after, True, message, ok=after == OK)
