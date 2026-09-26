# Research: omai

Raw cited findings: [research/](./research/). Versions checked 2026-09-26.

## R1 Harness facts (registry seed)

| Harness | Channels (detect by resolved path) | Version probe | Latest source | Update | Login | Auth status |
|---|---|---|---|---|---|---|
| claude | native `~/.local/share/claude/versions/*`; npm `@anthropic-ai/claude-code`; brew | `claude --version` → `X (Claude Code)` | text `https://downloads.claude.ai/claude-code-releases/latest` | `claude update` | `claude auth login` (URL printed; paste code on WSL/SSH) | `claude auth status --json`, exit 0/1 |
| codex | standalone `$CODEX_HOME/packages/standalone` via `chatgpt.com/codex/install.sh`; npm `@openai/codex`; brew | `codex --version` → `codex-cli X` | npm `@openai/codex` latest | `codex update` | `codex login` (localhost:1455) / `--device-auth` | `codex login status`, exit 0/1 |
| hermes | git `~/.hermes/hermes-agent` via install.sh | `hermes --version` → `Hermes Agent vX` | GitHub releases `NousResearch/hermes-agent` | `hermes update` | `hermes auth add openai-codex` (device code default) | `hermes auth status openai-codex` → `…: logged in`/`…: logged out` (exit 0 both; regex) — verified |
| pi | npm `@earendil-works/pi-coding-agent`; managed `~/.pi/agent/install` via `pi.dev/install.sh`; brew | `pi --version` → `X` | text/json `https://pi.dev/api/latest-version` | `pi update` | manual (TUI `/login`) | `pi auth check --provider P --no-refresh --json` exit 0/1 — verified |
| omp | bun global / binary `~/.local/bin` via `omp.sh/install`; brew; npm | `omp --version` → `omp/X` | npm `@oh-my-pi/pi-coding-agent` | `omp update` | `omp login openai-codex` | no status command; `omp models openai-codex --json` lists models only for authenticated providers (regex) — verified. Never `omp token` (prints a secret) |
| speckit | uv tool `specify-cli` | `specify --version` → `specify X` | PyPI `specify-cli` | `uv tool install --force specify-cli` | — | — |
| omai | uv tool | `importlib.metadata` | GitHub tags `omar2535/oh-my-ai` | `uv tool upgrade omai` (git source) | — | — |

- Decision: encode above in `registry/harnesses.toml`. Rationale: constitution IV. Alternative: Python classes per harness — rejected, violates IV.
- Auth-status commands verified against the real CLIs on 2026-09-26 and covered by `pytest -m live`; registry allows `auth_status.parse` = `exit_code` | `json_path` | `regex`.

## R2 Channel inference
- Decision: `realpath(which(bin))` matched against ordered registry glob patterns (`**/node_modules/<pkg>/**` → npm, `~/.bun/**` → bun, `/opt/homebrew|/home/linuxbrew/**` → brew, channel-specific dirs). nvm detected by `~/.nvm/versions/node/` prefix → flag `runtime_bound`.
- Rationale: no credential/config reads; cheap. Alternative: querying package managers — slower, misses native.

## R3 Latest-version fetching & caching
- Decision: httpx async, 5 s timeout per source, all sources in parallel; cache in state.json with timestamp; TTL 6 h for TUI; `omai check` always refreshes unless `--cached`. Compare with `packaging.version`, fallback string equality.
- Offline → return cached with age, exit code 2 (distinct from 1 = updates available with `--exit-code`).

## R4 Skills fetching
- Decision: download GitHub tarball for pinned commit (`codeload.github.com/<o>/<r>/tar.gz/<sha>`), extract selected skill dirs into `~/.agents/skills/<name>`; lock records source, ref, resolved sha, sha256 of files. Drift check = GitHub API `commits/<ref>` sha vs locked (read-only). spec-kit is not a global skill: it's the `specify` CLI + per-repo `omai init`.
- Rationale: vercel `skills check` mutates; git not required. Alternative: shell out to `npx skills` — rejected (mutating check, no omp key, Node dependency).
- Fan-out: symlink `~/.claude/skills/<name>` → canonical; Hermes `config.yaml` `skills.external_dirs` gains `~/.agents/skills`; Codex/pi/omp read canonical natively. Don't touch omp `skills.enableClaudeUser`.
- Existing non-symlink entries with same name in `~/.claude/skills` → report conflict, don't overwrite.

## R5 Config patching (Hermes)
- Decision: registry `config_patch` entries (file, format yaml, key path, value) applied via `hermes config set <key> <value>` command, not direct YAML edit. Patches: `auth.adopt_external_logins=false`, `skills.external_dirs` append. Rationale: native tool owns its file (principle II). Verified in a throwaway `HERMES_HOME`: `hermes config set skills.external_dirs '["~/.agents/skills"]'` writes a YAML list; `config get` prints `[]` or `- item` lines.

## R6 Login orchestration
- Decision: process-wide `fcntl` lock file `~/.local/state/omai/login.lock`; run login command attached to the terminal (inherit stdio) so interactive paste/device prompts work; tee stderr/stdout line scanner extracts first `https://` URL and opens it via platform opener. Re-probe status after exit.
- WSL opener: detect `/proc/sys/kernel/osrelease` contains `microsoft`; open via `cmd.exe /c start "" <url>` (fallback `powershell.exe Start-Process`); macOS `open`; Linux `xdg-open`. Always print the URL.
- TUI login: suspend the Textual app (`App.suspend()`) and run the login in the real terminal.

## R7 Runtimes
- Decision: registry `requires` (node ≥22.19 for pi, bun ≥1.3.14 for omp-bun channel). Missing runtime → install uv / bun via official user-local installers; Node via standalone channels preferred (avoid needing Node). Never sudo; bubblewrap missing for codex on Linux → print distro command.

## R8 TUI
- Decision: Textual `DataTable` dashboard; `@work(exclusive=True)` thread worker for checks; renders cached state immediately. Key bindings: i install, u update, U update all, l login, L login all, x uninstall, s skills, r repos, c check now, q quit.

## R9 Distribution
- Decision: `pyproject` `[project.scripts] omai = "omai.cli:app"`, hatchling build, package data for registry + bundled skill. `bootstrap.sh`: install uv via `astral.sh/uv/install.sh` if absent, then `uv tool install git+https://github.com/omar2535/oh-my-ai`, then `omai up`.

## R10 Repo init
- Decision (verified with spec-kit 1.0.12): `specify init --here --force --integration omp --script sh --non-interactive` if uninitialized (`--force` is required for non-empty dirs in non-interactive mode), then `specify integration install claude|codex|pi`; `specify integration use omp`; verify `specify integration status --json`. Track path in state. Refresh: for each tracked repo `specify integration upgrade <key>` per installed integration. Requires spec-kit ≥1.0 (`integration` subcommands) → `omai init` checks version and prompts update.
