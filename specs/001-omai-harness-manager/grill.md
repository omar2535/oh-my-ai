# Grill outcome: omai harness manager (2026-09-26)

## Decisions
- Personal tool; harnesses/skills as data registry. Command `omai`. Python + Textual + Typer; uv tool from GitHub omar2535/oh-my-ai plus curl bootstrap installing uv.
- Platforms: Linux, WSL2, macOS. WSL opens login URLs in Windows browser (no wslview present).
- Declarative `~/.config/omai/config.toml`; `omai up` converges idempotently; continue on failure, summary, non-zero exit. State in `~/.local/state/omai/`.
- Harnesses: Claude Code, Codex, Hermes, pi, omp. Adopt existing installs (record channel); `omai migrate` opt-in; suggest standalone installers for nvm-bound codex/pi (pi needs Node ≥22.19, host has 22.18).
- Native auto-updaters stay on. `omai update` invokes native updaters (claude update, codex update, hermes update, pi update, omp update; spec-kit via `uv tool install --force specify-cli`); omai self-updates too. Claude compared against `latest` channel.
- TUI checks updates async on open, 6h cache. `omai check [--json] [--exit-code]` read-only.
- Auth: delegate to native login only; status-first; serialized (port 1455 shared). Accounts: Claude Pro/Max (Claude Code), ChatGPT Plus/Pro (Codex, omp, Hermes default). Copilot: backup only, not configured. pi: user logs in manually; omai shows status via `pi auth check` + hint. Hermes: set `auth.adopt_external_logins: false`.
- Skills: defaults grill-me + grilling + spec-kit + new `grill-speckit` bridge; extra sources configurable. Fetched upstream, pinned, lockfile; read-only drift check (vercel `skills check` mutates — don't use for checks). Canonical `~/.agents/skills`, symlinked into `~/.claude/skills`, Hermes `skills.external_dirs`; omp claude-user skills opt-in stays off.
- `omai init` per repo: spec-kit integrations claude, codex, pi, omp; default omp; skip Hermes integration (not multi-install safe; Hermes reads `.agents/skills` after `hermes skills trust`). Tracked repos; `omai update speckit --repos`.
- `grill-speckit`: writes `specs/<feature>/grill.md`, invokes `/speckit.specify`, skips clarify.
- TUI: dashboard, install/update/login single or all, uninstall (keep config; `--purge`), manage skill sources, tracked repos + init.
- Testing: fake HOME + fake binaries, no network; opt-in live smoke.
- Settings management (models, permissions, MCP, instructions): out of scope v1.

## Research
research/claude-codex.md, research/hermes-pi-omp.md, research/skills-speckit.md
