# Implementation Plan: omai — Personal Coding-Agent Harness Manager

**Branch**: `001-omai-harness-manager` | **Date**: 2026-09-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-omai-harness-manager/spec.md`; decisions in [grill.md](./grill.md).

## Summary

`omai` is a Python CLI (Typer) + TUI (Textual) that converges a machine to a declarative config:
installs/adopts five harnesses (Claude Code, Codex, Hermes, pi, omp), drives their **native** login
commands serially after status checks, reports and applies updates through each harness's native
updater, syncs pinned skills into one canonical dir symlinked for every harness, and initializes /
tracks spec-kit repos. All harness behaviour lives in a data registry (TOML shipped in the package);
core code implements a small set of generic step kinds (probe, install, update, login, auth-status).

## Technical Context

**Language/Version**: Python ≥3.13 (repo pins 3.13 via `.python-version`)

**Primary Dependencies**: Typer 0.27, Textual 8.2, httpx 0.28 (latest-version fetches), tomlkit 0.15
(round-trip config edits), packaging 26 (version compare), platformdirs 4.11. stdlib `tomllib` for
registry reads.

**Storage**: Files only — config `~/.config/omai/config.toml`; state `~/.local/state/omai/state.json`
(detected installs, check cache, tracked repos); skills lock `~/.config/omai/skills.lock.json`
(travels with dotfiles).

**Testing**: pytest 9 with a `fake_home` fixture (temp `HOME`, `XDG_*`, `PATH` = dir of fake
harness scripts emitting canned `--version`/status output, recording invocations to a log) and
`httpx.MockTransport` for latest-version sources. `pytest -m live` opt-in smoke suite.

**Target Platform**: Linux, WSL2, macOS.

**Project Type**: Single-project CLI/TUI, `src/` layout, entry point `omai`.

**Performance Goals**: `omai check` < 10 s (parallel latest-version fetches, 5 s per-source
timeout); TUI first paint before any network I/O.

**Constraints**: never sudo; never read harness credential files (auth status only via harness
commands); logins strictly serial; checks read-only; idempotent converge.

**Scale/Scope**: 1 user, 5 harnesses + spec-kit + omai, ~4 default skills, tens of tracked repos.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre | Post-design |
|---|---|---|---|
| I. Delegate credentials | Auth only via registry `login`/`auth_status` commands; no module opens credential paths; logins behind a global lock; status-first | PASS | PASS — `auth.py` exposes only command runners; test asserts credential files never opened (fake HOME with canary files + audit hook) |
| II. Adopt, don't fight | Channel detection from resolved binary path; updates via native updater; no auto-updater disabling | PASS | PASS — `update` uses `harness.update` command; migrate is separate explicit command |
| III. Declarative & idempotent | `omai up` plan = diff(desired, detected); check path has no writes except cache | PASS | PASS — cache write is omai's own state, not managed items |
| IV. Data-driven registry | Harness facts in `registry/harnesses.toml`; per-harness Python only for enumerated hook kinds | PASS | PASS — two hook kinds justified below (config patching for Hermes, pi manual-login) expressed as data (`config_patch`, `login.mode = "manual"`) |
| V. Hermetic tests | Fake HOME + fake binaries; network mocked; live tests marked | PASS | PASS |
| Platform & safety | No sudo; user-local runtimes; Linux/WSL2/macOS | PASS | PASS |

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-omai-harness-manager/
├── plan.md
├── grill.md
├── research.md
├── research/            # raw cited research from grilling
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── config.schema.md
│   ├── registry.schema.md
│   └── grill-speckit.SKILL.md
└── tasks.md             # /speckit.tasks
```

### Source Code (repository root)

```text
src/omai/
├── __init__.py
├── __main__.py
├── cli.py               # Typer app: up, check, update, login, status, install, uninstall, migrate, init, repos, skills, self, tui
├── config.py            # load/validate/edit config.toml (tomlkit)
├── state.py             # state.json: installs, check cache, tracked repos
├── context.py           # Ctx: registry + config + state + HTTP client factory
├── registry/
│   ├── __init__.py      # load + validate registry entries
│   └── harnesses.toml   # 5 harnesses + speckit + omai
├── platform.py          # OS/WSL detection, browser opener, PATH/runtime probing
├── runner.py            # subprocess wrapper: timeouts, streaming, URL/code capture, invocation log
├── detect.py            # installed version + channel inference
├── versions.py          # latest-version sources (npm, github, url-text, pypi, command), cache
├── install.py           # install/uninstall/migrate per channel, runtimes, harness config patches
├── update.py            # native updater invocation
├── auth.py              # status probe, serial login, manual-login hints
├── skills.py            # fetch pinned sources, lockfile, canonical dir, symlink fan-out, drift check
├── repos.py             # omai init (specify integration install), tracking, refresh
├── converge.py          # plan + execute `up`, failure summary
├── report.py            # table/JSON rendering
├── bundled_skills/grill-speckit/SKILL.md
└── tui/
    ├── app.py           # Textual App, background check worker
    ├── dashboard.py
    ├── modals.py
    ├── skills_screen.py
    └── repos_screen.py

tests/
├── conftest.py          # fake_home, fake_bin factory, mock http
├── fakes/               # fake harness script template
├── live/                # opt-in read-only smoke tests (-m live)
├── unit/                # versions compare, channel inference, config validation, registry validation
└── integration/         # up idempotency, check read-only, login status-first/serial, skills fan-out, init, uninstall
bootstrap.sh             # installs uv (if missing) then `uv tool install git+https://github.com/omar2535/oh-my-ai`
```

**Structure Decision**: single `src/omai` package replacing the scaffold `main.py`; registry as
package data; tests split unit/integration with hermetic fixtures per constitution V.

## Complexity Tracking

None.
