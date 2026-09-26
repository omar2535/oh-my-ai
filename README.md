# omai (oh-my-ai)

Install, log in, update and equip your coding-agent harnesses in one go:
**Claude Code, Codex, Hermes Agent, pi, oh-my-pi (omp)** plus **spec-kit**, with the
**grill-me → spec-kit** workflow skills installed for every harness.

Linux, WSL2 and macOS. omai never uses `sudo` and never reads or copies harness credentials:
logins always run the harness's own login flow.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/omar2535/oh-my-ai/main/bootstrap.sh | sh
```

The bootstrap installs `uv` if missing, runs `uv tool install git+https://github.com/omar2535/oh-my-ai`,
then `omai up`. From a checkout: `uv tool install -e .`

## Use

| Command | What it does |
|---|---|
| `omai` | Dashboard (TUI). Checks for updates in the background (cached 6 h). |
| `omai up [--no-login] [--only ID]` | Converge to `~/.config/omai/config.toml`: install missing harnesses (existing installs are adopted, never reinstalled), apply harness config, sync skills, log in where needed. Safe to re-run. |
| `omai check [--json] [--exit-code] [--cached]` | Installed vs latest for harnesses, spec-kit, skill sources and omai. Read-only. Exit 1 with `--exit-code` when updates exist, 2 when a lookup failed. |
| `omai update ID… \| --all [--repos]` | Run each item's native updater (`claude update`, `codex update`, `hermes update`, `pi update`, `omp update`, `uv tool install --force specify-cli`, `uv tool upgrade omai`). `skills` moves skill pins to upstream. `--repos` refreshes spec-kit files in tracked repos. |
| `omai status [--json]` | Installs and login status. |
| `omai login [ID… \| --all] [--force]` | Native logins, one at a time, skipping harnesses already logged in (`codex login` would revoke a valid session). pi logs in only inside its TUI: run `pi`, then `/login`. |
| `omai install ID` / `omai uninstall ID [--purge]` | Uninstall keeps config and credentials unless `--purge`. |
| `omai migrate ID --to CHANNEL` | e.g. move nvm-bound npm installs to standalone: `omai migrate codex --to standalone`, `omai migrate pi --to managed`. |
| `omai skills list \| add owner/repo[@ref] --skill NAME \| remove NAME \| sync` | Skills live once in `~/.agents/skills` (read by Codex, pi, omp), are symlinked into `~/.claude/skills`, and added to Hermes' `skills.external_dirs`. |
| `omai init [PATH]` / `omai repos list \| remove PATH` | Set up spec-kit in a repo for claude, codex, pi and omp (default omp) and track it. Needs spec-kit ≥ 1.0. |

## The grill → spec-kit workflow

1. In any harness, run **grill-me** (`/grill-me`, or `$grill-me` in Codex). It interviews you until
   every decision is settled.
2. Run **grill-speckit**. It writes the decisions to `specs/<NNN-feature>/grill.md` and starts
   spec-kit's specify step (skipping clarify, since grilling already did it):
   - omp / pi: `/speckit.specify`
   - Claude Code: `/speckit-specify`
   - Codex: `$speckit-specify`
3. Continue with plan → tasks → analyze → implement.

Hermes: spec-kit's Hermes integration is skipped (it isn't multi-install safe). Run
`hermes skills trust` in the repo so Hermes reads the shared `.agents/skills`.

## Config

`~/.config/omai/config.toml` is created on first run:

```toml
[harnesses.claude]
enabled = true
release_channel = "latest"   # latest | stable

[harnesses.omp]
enabled = true
provider = "openai-codex"

[[skills.sources]]
repo = "mattpocock/skills"
ref = "<pinned commit>"
track = "main"
skills = ["grill-me", "grilling"]
```

Harness facts (install channels, version/latest sources, login and status commands, skill dirs)
live in `src/omai/registry/harnesses.toml`; adding a harness is a new entry there.

## Development

```sh
uv sync
uv run pytest            # hermetic: temp HOME, fake harness binaries, mocked network
uv run pytest -m live    # opt-in, read-only probes of the real harnesses and sources
uv run ruff check && uv run ruff format --check
```
