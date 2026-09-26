"""Subprocess helpers: captured runs and interactive runs with output scanning."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    code: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def output(self) -> str:
        return (self.stdout + "\n" + self.stderr).strip()


def fill(argv: list[str], values: Mapping[str, str] | None = None) -> list[str]:
    """Substitute ``{name}`` placeholders and expand a leading ``~`` in each arg."""
    out = []
    for arg in argv:
        for key, value in (values or {}).items():
            arg = arg.replace("{" + key + "}", value)
        out.append(os.path.expanduser(arg) if arg.startswith("~") else arg)
    return out


def run(argv: list[str], timeout: float = 60, cwd: str | None = None) -> Result:
    """Run a command non-interactively and capture its output."""
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        return Result(127, "", str(exc))
    except subprocess.TimeoutExpired:
        return Result(124, "", f"timed out after {timeout}s: {' '.join(argv)}")
    return Result(proc.returncode, proc.stdout, proc.stderr)


def run_interactive(
    argv: list[str],
    on_output: Callable[[str], None] | None = None,
    cwd: str | None = None,
) -> int:
    """Run a command attached to the user's terminal, passing output through.

    ``on_output`` receives decoded output chunks so callers can spot login URLs.
    A pty is used when attached to a terminal so prompts (paste-a-code, device
    codes, pickers) behave as if the harness were run directly.
    """
    try:
        if sys.stdin.isatty() and sys.stdout.isatty():
            return _run_pty(argv, on_output, cwd)
        return _run_piped(argv, on_output, cwd)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 127


def _run_piped(argv, on_output, cwd) -> int:
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd, bufsize=1)
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        if on_output:
            on_output(line)
    return proc.wait()


def _run_pty(argv, on_output, cwd) -> int:
    import pty

    def read(fd: int) -> bytes:
        data = os.read(fd, 1024)
        if on_output and data:
            on_output(data.decode(errors="replace"))
        return data

    previous = os.getcwd()
    try:
        if cwd:
            os.chdir(cwd)
        status = pty.spawn(argv, read)
    finally:
        os.chdir(previous)
    return os.waitstatus_to_exitcode(status)
