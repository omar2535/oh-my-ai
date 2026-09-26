# Harness facts: Hermes Agent, Pi, oh-my-pi (omp)

Research date 2026-09-26. Facts only; no design decisions. `[UNVERIFIED]` = not confirmed from a primary source; `[INFERENCE]` = derived from observed code/data, not stated by docs. Local observations come from read-only commands on this machine (no secrets printed).

---

## 0. Version snapshot (fetched 2026-09-26)

| Harness | Latest | Source of "latest" | Installed locally (observed) |
|---|---|---|---|
| omp | **18.3.2** (npm `latest`; GitHub release `v18.3.2`, published 2026-09-26T00:00:25Z) | `https://registry.npmjs.org/-/package/@oh-my-pi/pi-coding-agent/dist-tags` → `{"latest":"18.3.2"}`; `https://api.github.com/repos/can1357/oh-my-pi/releases/latest` | `~/.bun/bin/omp` = standalone ELF binary, `omp --version` → `omp/18.3.2`. The bun global package dir (`~/.bun/install/global/node_modules/@oh-my-pi/pi-coding-agent/package.json`) still says **17.3.7** (stale; see §3.2) |
| Pi | **0.87.1** (npm `latest`; `legacy-node20` tag = 0.74.2; GitHub release `v0.87.1` 2026-09-22) | `https://registry.npmjs.org/-/package/@earendil-works/pi-coding-agent/dist-tags`; `https://pi.dev/api/latest-version` → `{"ok":true,"version":"0.87.1","packageName":"@earendil-works/pi-coding-agent"}` | `pi --version` → `0.87.1` (npm global under nvm Node 22.18.0) |
| Hermes | **v0.21.5**, tag `v2026.9.24` (published 2026-09-24) | `https://api.github.com/repos/NousResearch/hermes-agent/releases/latest` (`name: "Hermes Agent v0.21.5 (v2026.9.24)"`) | `hermes --version` → `Hermes Agent v0.21.4 (2026.9.21) · upstream d3b25b52`, `Install method: git`, `Install directory: ~/.hermes/hermes-agent`, **Python 3.11.16** (docs say current installs run on 3.14; see §1.1) |

Other channels: Homebrew core has `pi-coding-agent` 0.87.1 (https://formulae.brew.sh/api/formula/pi-coding-agent.json) and `hermes-agent` 2026.9.21 built on `python@3.13` (https://formulae.brew.sh/api/formula/hermes-agent.json). PyPI `hermes-agent` is stale at 0.19.0 (2026-07-20) (https://pypi.org/pypi/hermes-agent/json).

---

## 1. Nous Research Hermes Agent

Repo: https://github.com/NousResearch/hermes-agent · Docs: https://hermes-agent.nousresearch.com/docs/ (source in `website/docs/`).

### 1.1 Install (Linux/WSL2/macOS)
- **Recommended (CLI-only):** `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash` — same one-liner for Linux, macOS, WSL2 (README; https://github.com/NousResearch/hermes-agent/blob/main/website/docs/getting-started/installation.md).
- What it does: clones source to `~/.hermes/hermes-agent/`, bootstraps `uv`, delegates to "PM" which provides pinned Python, Node.js, npm, ripgrep, FFmpeg; installs `agent-browser` + Chromium by default; creates `~/.local/bin/hermes` wrapper; data in `~/.hermes/`. Interactive runs also invoke setup + gateway configuration (installation.md "What the source installer does", "Install layout").
- Installer flags (https://hermes-agent.nousresearch.com/install.sh, header/arg parser): `--branch NAME`, `--commit SHA`, `--dir PATH` (source checkout; env `HERMES_INSTALL_DIR`), `--hermes-home PATH` (env `HERMES_HOME`, default `~/.hermes`), `--non-interactive` / `--skip-setup` (skip stages needing input), `--skip-browser` (alias `--no-playwright`), `--include-desktop`, `--verbose`, `--manifest`, `--stage NAME [--json]`. Env `HERMES_REPO_URL` overrides clone URL. Logs to `$HERMES_HOME/logs/install.log`.
- Prereqs for POSIX script: Git, curl, tar, SHA-256 utils; uv optional (downloaded if absent) (installation.md "Prerequisites").
- **Runtime:** "Current first-party installations run on **Python 3.14**"; `pyproject.toml` declares `>=3.11,<3.15` only so pre-PM venvs can run the updater once; every runtime dep carries `python_version >= '3.14'` marker (installation.md; https://github.com/NousResearch/hermes-agent/blob/main/website/docs/getting-started/updating.md "Python 3.14 and older interpreters").
- **Unsupported:** `pip install .`, `uv pip install .`, PyPI or Homebrew packages built on Python 3.11–3.13 "install hermes-agent with no dependencies and the package does not import" (updating.md). Note: the homebrew-core formula depends on `python@3.13` → falls in this unsupported class [INFERENCE from formula JSON + doc].
- Other methods: Desktop bundles (macOS DMG — **Apple Silicon only**; Windows MSIX), Docker (`nousresearch/hermes-agent`), Nix (best-effort only), Termux APT (installation.md).
- Local observation: installed via git but still on Python 3.11.16 → possibly a pre-PM venv; docs say repair with `hermes update` or `python -m pm.cli install` (updating.md) [INFERENCE].

### 1.2 Version / latest / update
- Installed version: `hermes --version` (prints version, date tag, upstream sha, install dir/method, Python) (observed; https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md). Also `hermes-agent --version`.
- Latest: GitHub releases API `repos/NousResearch/hermes-agent/releases/latest` (tag `vYYYY.M.D`, name contains `vX.Y.Z`). Docs point to the releases page for comparison (updating.md "Checking your current version").
- Built-in: `hermes update [--check] [--plan] [--yes] [--backup|--no-backup] [--branch NAME] [--force] ...` — pulls git + re-prepares deps via PM, restarts gateways. `--check` compares with configured source target without changes; `--plan` read-only. Default source channel tracks `origin/main`; stable/canary release channels exist (`hermes update --channel stable --check`) (cli-commands.md `hermes update`; updating.md). Passive update checks query the GitHub REST API for the tip of `main` (configuration.md "Background checks"). Docker/Nix/apt installs refuse self-update (exit 2) and print the owner's command (updating.md).
- Config: `updates.pre_update_backup: quick|full|off`, `updates.non_interactive_local_changes`, etc. (https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md "Update Behavior").

### 1.3 Authentication
Commands (cli-commands.md):
- `hermes model` — interactive provider+model wizard; **the** place to add providers, run OAuth, enter API keys. `/model` inside a session only switches among already-configured providers.
- `hermes setup [model|tts|terminal|gateway|tools|agent] [--non-interactive] [--reset] [--quick] [--portal]` — full wizard; `--portal` = one-shot Nous Portal OAuth + set provider + enable Tool Gateway; `--non-interactive` = "Use defaults / environment values without prompts".
- `hermes auth [add|list|remove|reset|priority|refresh|status|logout|spotify]` — credential pools. `hermes auth add <provider> [--type oauth|api-key] [--api-key KEY] [--label] [--priority N] [--no-browser] [--browser] [--timeout] [--insecure] [--ca-bundle]` (observed `hermes auth add --help`).
- `hermes login` / `hermes logout` — **deprecated/removed**; use `hermes auth` (cli-commands.md).
- `hermes config set OPENROUTER_API_KEY sk-...` writes to `~/.hermes/.env` (UPPER_SNAKE → `.env`, dotted → `config.yaml`) (configuration.md).
- `hermes portal info|status|open|tools`; `hermes usage`; `hermes auth status <provider>`.

Providers / flows (https://github.com/NousResearch/hermes-agent/blob/main/website/docs/integrations/providers.md; https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/oauth-over-ssh.md; `hermes_cli/auth.py` ProviderConfig):
| Provider id | Method | Flow |
|---|---|---|
| `nous` (Nous Portal) | OAuth | **device code** (`auth.py`: `ProviderConfig("nous", ..., "oauth_device_code")`); refresh token in `~/.hermes/auth.json`, short-lived JWTs minted per request (https://github.com/NousResearch/hermes-agent/blob/main/website/docs/integrations/nous-portal.md). Note nous-portal.md says "Opens your browser"; oauth-over-ssh.md table says device code, no tunnel. |
| `openai-codex` (ChatGPT sub) | OAuth | **device code by default**; `--browser` or `auth.codex_login_flow: browser` → PKCE loopback on fixed `http://localhost:1455/auth/callback`. Can import Codex CLI `~/.codex/auth.json`. |
| `anthropic` | OAuth (Claude **Max + purchased extra-usage credits only**; Pro not supported), API key `ANTHROPIC_API_KEY`, or setup-token `ANTHROPIC_TOKEN` | "paste-the-code flow" (no tunnel). Can borrow Claude Code creds. |
| `copilot` (GitHub Copilot) | OAuth device code, or `COPILOT_GITHUB_TOKEN` / `GH_TOKEN` / `gh auth token` (classic `ghp_` PATs unsupported) | device code |
| `copilot-acp` | spawns local `copilot --acp --stdio` | external process |
| `xai-oauth` (SuperGrok / X Premium+) | OAuth | device code |
| `qwen-oauth` | OAuth | browser PKCE |
| `minimax-oauth` | OAuth | providers.md says browser PKCE; oauth-over-ssh.md lists `minimax` as device code — docs conflict [UNVERIFIED which] |
| `openrouter` | `OPENROUTER_API_KEY`, or `hermes auth add openrouter --type oauth` (PKCE that mints a key; OS-assigned local port; over SSH switches to paste-code) | |
| `gemini` | `GOOGLE_API_KEY`/`GEMINI_API_KEY` only — no consumer Gemini-plan login | |
| `vertex` | service-account JSON / ADC | |
| Many API-key providers | `.env` vars (OpenAI `OPENAI_API_KEY`, xAI `XAI_API_KEY`, DeepSeek, Fireworks, Novita, etc.) | |
| Custom endpoint | `hermes model` → Custom endpoint (saved in `config.yaml`) | |
| Spotify / MCP OAuth | loopback (Spotify 43827; MCP auto port) — needs `ssh -L` or paste redirect URL when remote | |

Storage:
- OAuth credentials + credential pools: `~/.hermes/auth.json` (configuration.md "Directory Structure"). Local file exists; top-level keys observed: `version`, `providers`, `active_provider`, `updated_at`, `credential_pool` (both currently holding `openai-codex`).
- API keys/secrets: `~/.hermes/.env` (configuration.md "Configuration Precedence"). External secret backends (Bitwarden, 1Password) via `secrets:` block / `hermes secrets`.
- **Borrowed logins:** when Hermes has no own login for `openai-codex`/`anthropic` it reads & refreshes `~/.codex/auth.json` and `~/.claude/.credentials.json` (or Keychain); disable with `auth.adopt_external_logins: false` (https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/security.md "Borrowed CLI logins"). Rotating single-use refresh tokens → sharing causes mutual invalidation.

Headless / non-interactive paths:
- API keys: pre-write `~/.hermes/.env`, `hermes config set KEY value`, or `hermes auth add <provider> --type api-key --api-key KEY` (non-interactive).
- `hermes setup --non-interactive`; installer `--non-interactive`.
- OAuth device-code providers (nous, openai-codex default, xai-oauth, copilot) print URL + code; `--no-browser` suppresses auto-open. Still requires a human to approve in a browser. Loopback flows need `ssh -L` (oauth-over-ssh.md).

### 1.4 Skills
(https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md; source `agent/skill_utils.py`)
- Standard: agentskills.io compatible; `SKILL.md` with frontmatter `name`, `description`, optional `version`, `platforms`, `metadata.hermes.{tags,category,requires_toolsets,fallback_for_toolsets,config}`.
- **User/profile dir:** `~/.hermes/skills/` (single source of truth; category subdirs allowed, e.g. `~/.hermes/skills/mlops/axolotl/SKILL.md`; bundled skills seeded here on install; `.hub/` state). Per-profile: `~/.hermes/profiles/<name>/skills` [from system_prompt.py comment].
- **Project dirs:** `<root>/.hermes/skills/` and `<root>/.agents/skills/`, root = nearest `.git` ancestor — **only loaded after `hermes skills trust [path]`** (stored in `skills.trusted_project_dirs`); `skills.project_discovery: false` disables. Untrusted repos just show a banner notice. Project skills are security-scanned (quarantine on "dangerous").
- **Extra dirs:** `skills.external_dirs: [~/.agents/skills, ...]` in `config.yaml` (non-existent paths skipped); `skills.create_dir` redirects agent-created skills.
- Precedence: project → `~/.hermes/skills` (local) → `external_dirs`.
- Does NOT read `~/.claude/skills` natively; `hermes import-agent claude-code` copies `~/.claude/skills/<name>/` → `~/.hermes/skills/claude-code-imports/<name>/`; `hermes import-agent codex` → `codex-imports/`; `--sync` re-imports changes; credentials never read (https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/import-from-other-agents.md). Claude `commands/*.md` are skipped.
- Install from hub/URL: `hermes skills install <source>` (e.g. `skills-sh/anthropics/skills/pdf`, `https://.../SKILL.md`), `hermes skills browse|search|inspect|check|update|config|reset|opt-out|opt-in|trust|untrust` (cli-commands.md `hermes skills`).
- Slash commands: every installed skill becomes `/<skill-name>` (built-in names win; fallback `/skill <name>`); `bundles:` in config.yaml = `/<bundle>` loading several skills; `quick_commands:` (`type: exec` shell or `type: alias`) — **no prompt-template/commands directory**; "String-only prompt shortcuts are not supported" (https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/slash-commands.md).

### 1.5 Config files & declarative pre-seeding
- `~/.hermes/` (or `$HERMES_HOME`): `config.yaml` (settings), `.env` (secrets), `auth.json` (OAuth), `SOUL.md`, `memories/`, `skills/`, `state.db`, `logs/`, `backups/` (configuration.md).
- Example: `cli-config.yaml.example` in repo root. Precedence: CLI args > `config.yaml` > `.env` > defaults. `${VAR}` / `${env:VAR}` substitution in config.yaml.
- Pre-seeding: plain YAML + dotenv, so declarative seeding is feasible; `hermes config set/get/unset` for scripted edits; profiles via `HERMES_HOME`; Nix flake/NixOS module exists (best-effort) (installation.md; getting-started/nix-setup.md). Config backups to `backups/config/`.
- Context files: `.hermes.md`/`HERMES.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules` (first match wins) (https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/which-file-does-what.md).

---

## 2. Pi coding agent (Mario Zechner)

**Renamed/moved:** npm `@mariozechner/pi-coding-agent` is deprecated at 0.73.1 ("please use @earendil-works/pi-coding-agent instead going forward") (https://registry.npmjs.org/@mariozechner/pi-coding-agent/latest). Current package `@earendil-works/pi-coding-agent`, repo `github.com/earendil-works/pi` (`badlogic/pi-mono` redirects there; GitHub API returns `full_name: earendil-works/pi`). Binary name `pi`. Site https://pi.dev.

### 2.1 Install
- npm: `npm install -g --ignore-scripts @earendil-works/pi-coding-agent` — **Node.js ≥ 22.19** (`engines.node ">=22.19.0"`) (https://github.com/earendil-works/pi/blob/main/packages/coding-agent/README.md; npm latest JSON). Node 20 users: dist-tag `legacy-node20` = 0.74.2.
- Installer (macOS/Linux): `curl -fsSL https://pi.dev/install.sh | sh` (README; https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/quickstart.md). Script facts (https://pi.dev/install.sh): checks Node ≥ 22.19 + npm, offers to install Node (brew or standalone into `$XDG_DATA_HOME/pi-node` / `~/.local/share/pi-node`); default is a **managed install** at `${PI_CODING_AGENT_DIR:-~/.pi/agent}/install` (marker `managed-install.json`) with the `pi` launcher placed in the first writable of `~/.pi/agent/bin`, `~/.local/bin`, `~/bin`, ... on PATH; `PI_LEGACY_INSTALL=1` → npm global prefix (or `~/.local`). Uses `/dev/tty` for an install/reinstall/uninstall menu; without a TTY it proceeds non-interactively. Uninstall = rerun installer and choose Uninstall.
- Homebrew: `pi-coding-agent` formula in homebrew/core (0.87.1, depends on node) (https://formulae.brew.sh/api/formula/pi-coding-agent.json). Not mentioned in pi docs [INFERENCE: community formula].
- Uninstall leaves `~/.pi/agent/` intact (quickstart.md).

### 2.2 Version / latest / update
- Installed: `pi --version` / `pi -v` (quickstart.md; observed `0.87.1`).
- Latest: `https://pi.dev/api/latest-version` (what `pi update` uses; `dist/utils/version-check.js` `LATEST_VERSION_URL`), npm registry `.../@earendil-works/pi-coding-agent/latest` or dist-tags, GitHub releases `earendil-works/pi` (`v0.87.1`).
- Built-in: `pi update` (= `--self`, `self`, `pi`), `pi update --all` (pi + packages), `--extensions`, `--models` (refresh model catalogs), `<source>`, `--force` (https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/cli.md "Update Pi or packages"; observed `pi update --help`). Self-update detects managed install vs npm/pnpm etc. (`dist/package-manager-cli.js`: `runManagedSelfUpdate`, `detectInstallMethod`; Windows only npm/pnpm). `PI_OFFLINE=1` disables startup network ops.

### 2.3 Authentication
(https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/providers.md)
- In-TUI only for pi itself: `/login [provider]` (OAuth or API-key flow, saved to `auth.json`), `/logout`. There is **no `pi login` subcommand**; `pi auth` only has `print-api-key`, `print-bearer-token`, `check [--json] [--credentials] [--no-refresh]` (observed `pi auth --help`; cli.md "Credential commands").
- Standalone CLI login: `npx @earendil-works/pi-ai login [provider]` / `list` — "Credentials are saved to `auth.json` in the current directory" (https://github.com/earendil-works/pi/blob/main/packages/ai/README.md "CLI Login"). Its stored OAuth object `{type:"oauth", access, refresh, expires, accountId}` matches the fields in the local `~/.pi/agent/auth.json` entries [INFERENCE: running it with cwd `~/.pi/agent` would produce a pi-usable file; not documented].
- OAuth providers in 0.87.1 (`pi-ai` CLI list): `anthropic`, `github-copilot`, `kimi-coding`, `meta`, `openai-codex`, `openrouter`, `radius`, `xai`. Google Gemini CLI & Antigravity login were **removed in 0.71.0** (CHANGELOG 0.71.0/0.71.1).
- Flows (source `packages/ai/src/auth/oauth/*.ts`, https://github.com/earendil-works/pi/tree/main/packages/ai/src/auth/oauth; inspected installed dist 0.87.1):
  - anthropic: PKCE + loopback `http://localhost:53692/callback` (bind host `PI_OAUTH_CALLBACK_HOST`, default 127.0.0.1) racing a `manual_code` paste prompt.
  - openai-codex: select "Browser login (default)" = PKCE loopback `http://localhost:1455/auth/callback`, or "Device code login (headless)" via `auth.openai.com/codex/device`.
  - github-copilot, kimi-coding, meta, xai: device code.
  - openrouter: PKCE loopback on random port + manual paste (mints an API key).
  - radius: loopback `127.0.0.1:1456/oauth/callback`.
  - Docs: "On a remote or headless machine ... paste the final redirect URL or authorization code back into Pi" (providers.md).
- API keys via env (`ANTHROPIC_API_KEY`, `ANTHROPIC_OAUTH_TOKEN`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `COPILOT_GITHUB_TOKEN`, `OPENROUTER_API_KEY`, `XAI_API_KEY`, ...), or `--api-key`.
- Storage: `~/.pi/agent/auth.json` (`PI_CODING_AGENT_DIR` relocates) — map `providerId → credential` with `type: "api_key"|"oauth"`; `key` may be `"!shell command"` (executed, cached per process); optional `env` object per credential (providers.md). Local file exists; top-level keys: `github-copilot`, `openai-codex` (both `type: oauth`, fields `access, refresh, expires` + `accountId` / `availableModelIds`).
- Non-interactive: env vars; pre-written `auth.json` with `api_key` entries (incl. `!command` for secret managers); `pi auth check` to verify readiness.

### 2.4 Skills, prompts
(https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md; configuration.md; prompt-templates.md; security.md)
- Implements Agent Skills spec (agentskills.io). Frontmatter `name`, `description` (required; missing → not loaded), `license`, `compatibility`, `metadata`, `allowed-tools`, `disable-model-invocation`. Name ≤64 chars lowercase/digits/hyphens; description ≤1024. `/skill:name [args]` forces load; `enableSkillCommands` setting.
- Dirs: user `~/.pi/agent/skills/`, project `.pi/skills/`, plus `~/.agents/skills/` and `.agents/skills/` (cwd → ancestors, stop at repo root). Discovery is **recursive** for dirs containing `SKILL.md`. Extra via `settings.json` `skills: [...]` array, `--skill <path>`, or Pi packages (`pi install npm:...|git:...`).
- Does **not** read `~/.claude/skills` (no `.claude` references in pi docs) [INFERENCE: add via `skills` setting].
- Prompt templates (slash commands): `~/.pi/agent/prompts/*.md`, `.pi/prompts/*.md` (direct `.md` children only); filename = `/command`; frontmatter `description`, `argument-hint`; `$1`, `$@`, `$ARGUMENTS`, `${1:-default}` substitutions.
- **Project trust:** `.pi/settings.json`, `.pi/{extensions,skills,prompts,themes}`, `.pi/SYSTEM.md`, and project `.agents/skills` load only after trust (`/trust`, saved in `~/.pi/agent/trust.json`; `--approve`/`--no-approve`; `defaultProjectTrust: ask|always|never` in user settings). In print/JSON/RPC modes with `ask`, protected resources are skipped.

### 2.5 Config & pre-seeding
- `~/.pi/agent/` (`PI_CODING_AGENT_DIR`): `settings.json`, `keybindings.json`, `models.json` (custom endpoints/models), `auth.json`, `AGENTS.md`/`CLAUDE.md`, `SYSTEM.md`, `APPEND_SYSTEM.md`, `extensions/`, `skills/`, `prompts/`, `themes/`, `trust.json`, `sessions/` (configuration.md; security.md).
- Project `.pi/settings.json` etc. Settings keys e.g. `defaultProvider`, `defaultModel`, `defaultThinkingLevel`, `enabledModels`, `packages`, `skills`, `prompts`, `defaultProjectTrust` (https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/settings.md). Plain JSON → declaratively seedable. `pi config` = TUI to toggle package resources.

---

## 3. oh-my-pi (`omp`, can1357, fork of Pi; now "Built by Stencil Labs")

Repo https://github.com/can1357/oh-my-pi · site https://omp.sh · npm `@oh-my-pi/pi-coding-agent` (bin `omp`).

### 3.1 Install
(README https://github.com/can1357/oh-my-pi)
- `curl -fsSL https://omp.sh/install | sh` (macOS/Linux). Script (https://omp.sh/install): options `--source` (bun global install; installs bun if missing), `--binary` (prebuilt GitHub release binary), `--ref/-r <tag|commit|branch>`. **Default: bun install if bun is present and matches host arch, else prebuilt binary** downloaded to `${PI_INSTALL_DIR:-~/.local/bin}/omp` and smoke-tested with `omp --version`. `MIN_BUN_VERSION=1.3.14`.
- Homebrew: `brew install can1357/tap/omp` (tap repo `can1357/homebrew-tap`, `Formula/omp.rb`).
- Bun ("recommended" in README): `bun install -g @oh-my-pi/pi-coding-agent` — `engines: { bun: ">=1.3.14" }` (npm JSON). The package is TypeScript source run by Bun (`main: ./src/index.ts`); npm/node install is detected by the updater but README only lists bun [INFERENCE].
- Nix: `nix run|profile install github:can1357/oh-my-pi`; flake exposes `homeManagerModules.default` (`programs.omp.settings`).
- mise: `mise use -g github:can1357/oh-my-pi`. Windows: `irm https://omp.sh/install.ps1 | iex`.
- Alpine/musl: needs `apk add libstdc++ libgcc`. Release assets: `omp-{linux,darwin}-{x64,arm64}`, `omp-linux-musl-*`, `omp-windows-*`, `SHA256SUMS.txt`.
- Shell completions: `omp completions bash|zsh|fish`.

### 3.2 Version / latest / update
- Installed: `omp --version` / `-v` → `omp/<ver>` (parsed by updater `parseReportedVersion`) (observed; https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md).
- Latest: npm dist-tags `latest` / `canary` (updater `fetchLatestManifest` uses registry tag `latest` or `canary`); GitHub `releases/latest` (tag `vX.Y.Z`) for binaries (`GITHUB_TOKEN`/`GH_TOKEN` or `gh auth token` used to avoid rate limits) (https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/cli/update-cli.ts).
- Built-in: `omp update [-c|--check] [-f|--force] [-l|--plugins] [--canary|--stable]` (observed help). Update method auto-detected from the PATH-resolved `omp`: `nix` (refuses; update flake), `brew` (`brew update && brew upgrade`), `mise` (`mise upgrade github:can1357/oh-my-pi --bump`), `bun`, `npm`, or standalone `binary` (download + verify + atomic replace). Releases may be flagged binary-only, in which case bun/npm launchers are **taken over in place by the standalone binary** (`shouldForceBinaryUpdate`, `updateViaShimTakeover`) — consistent with this machine: `~/.bun/bin/omp` is an ELF 18.3.2 binary while the bun global package.json says 17.3.7. ⇒ read the version from `omp --version`, not from package.json/`bun pm ls` [INFERENCE].

### 3.3 Authentication
- In-session: `/login` (selector of all login-capable providers, OAuth **and** API-key), `/login <provider>`, `/login <redirect-url>` to finish a pending callback manually, `/logout` (https://github.com/can1357/oh-my-pi/blob/main/docs/providers.md "OAuth vs API key"; `packages/coding-agent/src/slash-commands/builtin-session.ts`).
- **CLI outside the TUI:** `omp login [provider]` — "terminal counterpart of /login": prints `Open this URL in your browser:` + full URL (and a `Local shortcut (this machine only): http://localhost:<port>/launch` loopback redirect when applicable), best-effort opens the browser, reads prompts from stdin (numbered picker if no provider), saves to `agent.db` (or auth broker), prints `Credentials saved to <path>`; exit code 1 on failure (https://github.com/can1357/oh-my-pi/blob/main/packages/coding-agent/src/commands/login.ts, `src/cli/login-cli.ts`, `src/cli/oauth-terminal.ts`). Manual paste prompt only for "paste-code" providers (fixed non-loopback redirect, e.g. `gitlab-duo-agent`'s `vscode://` URI).
- Also: `omp auth-broker login [<provider>] [--via=user@host]` (runs flow locally, `ssh -L <port>` forward, credential written on broker host), `omp auth-broker import <file|dir>` (imports CLIProxyAPI-style JSON; maps `claude→anthropic`, `codex→openai-codex`, `gemini/gemini-cli→google-gemini-cli`, `antigravity→google-antigravity`), `omp auth-broker list --json` (all login provider ids; 78 observed locally), `omp token <provider> [--raw] [--force-refresh] [--list] [--account N]` (print key/token), `omp usage` (https://github.com/can1357/oh-my-pi/blob/main/docs/auth-broker-gateway.md). RPC mode has `{"type":"login","providerId":...}` and `get_login_providers` commands (`src/modes/rpc/rpc-types.ts`).
- Login roster order (`packages/catalog/src/compat/rules/auth/_order.kdl`): `openai-codex, anthropic, zai, zai-coding-plan, kimi-code, openrouter, github-copilot, cursor, devin, google-antigravity, google-gemini-cli, openai-codex-device, xai, xai-oauth, gitlab-duo, gitlab-duo-agent, alibaba-*, ... qwen-portal, minimax-code(-cn), ... ollama, lm-studio, llama.cpp, vllm, ...` (rest are API-key paste logins).
- OAuth mechanics (base class `packages/ai/src/registry/oauth/callback-server.ts`: local `Bun.serve` callback server, prefers fixed port, falls back to random port unless provider pins redirect URI, 5-min timeout, `/launch` route; per-provider KDL in `packages/catalog/src/compat/rules/auth/*.kdl`):

| Provider id | Name | Flow | Callback |
|---|---|---|---|
| `anthropic` | Anthropic (Claude Pro/Max) | PKCE auth-code, `claude.ai/oauth/authorize` | `localhost:54545/callback`; KDL instructions allow pasting redirect URL/code if browser can't reach host |
| `openai-codex` | ChatGPT Plus/Pro (Codex Subscription) | PKCE auth-code | fixed `http://localhost:1455/auth/callback`, **no port fallback** (fails if busy) |
| `openai-codex-device` | ChatGPT Plus/Pro (Codex, headless/device) | device code (`auth.openai.com/codex/device`); stored as `openai-codex` | none |
| `github-copilot` | GitHub Copilot | device code (`verification_uri` + "Enter code: XXXX"); enterprise domain prompt | none |
| `google-gemini-cli` | Google Cloud Code Assist (Gemini CLI) | auth-code | `127.0.0.1:8085/oauth2callback` |
| `google-antigravity` | Antigravity (Gemini 3, Claude, GPT-OSS) | auth-code | `127.0.0.1:51121/oauth-callback` |
| `xai-oauth` | xAI Grok OAuth (SuperGrok / X Premium+) | device code | none |
| `kimi-code` | Kimi | device code | none |
| `cursor`, `devin` (59653), `gitlab-duo` (8080), `gitlab-duo-agent` (paste), `zai-coding-plan` (9999), `qwen-portal`, `perplexity`, ... | | mixed | per auth-broker doc port list |

- Env tokens (non-interactive): `ANTHROPIC_OAUTH_TOKEN` (beats `ANTHROPIC_API_KEY`), `OPENAI_CODEX_OAUTH_TOKEN`, `COPILOT_GITHUB_TOKEN`, `CURSOR_ACCESS_TOKEN`, `XAI_OAUTH_TOKEN`, `QWEN_OAUTH_TOKEN`, plus API keys `OPENAI_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, ... (providers.md env table; `omp --help`).
- Credential precedence: `--api-key` > `models.yml` `apiKey` > stored OAuth > login-stored API key > env var (incl. `.env`) > other stored key > models.yml fallback (providers.md).
- `.env` files loaded (first wins): process env > `<cwd>/.env` > `~/.omp/agent/.env` > `~/.omp/.env` > `~/.env` (providers.md).
- **Storage:** `~/.omp/agent/agent.db` (SQLite; `PI_CODING_AGENT_DIR` relocates). **No auth.json** — "Removed legacy auth.json file—credentials are stored exclusively in agent.db" (pi-coding-agent CHANGELOG). Local DB tables include `auth_credentials(id, provider, credential_type, data, disabled_cause, identity_key, ...)`; providers currently stored: `anthropic`, `openai-codex`. Multiple accounts per provider supported (round-robin). Optional remote auth broker (`OMP_AUTH_BROKER_URL`/`TOKEN`).
- omp does not read Pi's `~/.pi/agent/auth.json` [INFERENCE: no discovery provider for `~/.pi`; `skills.enablePiUser` is a legacy name gating the native `~/.omp` source — docs/config-usage.md].

### 3.4 Skills, commands, prompts
(https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md; `packages/coding-agent/src/discovery/{builtin,agents,claude}.ts`; `src/capability/index.ts`; docs/settings.md)
- Layout: `<skills-root>/<name>/SKILL.md`, **one level only** (nested not discovered, unlike Pi/Hermes). Frontmatter: `name`, `description`, `globs`, `alwaysApply`, `hide`, `disable-model-invocation`, extra keys preserved. `description` required for native `.omp`, custom dirs, plugins, `.github/skills`; optional for claude/codex/agents/opencode providers.
- Providers by priority (name dedup, first wins):
  1. `native` (100): user `~/.omp/agent/skills/`, project `.omp/skills/` (walk up cwd → repo root / home).
  2. `omp-plugins` (90): `skills/` in extension packages / `~/.omp/plugins/node_modules`.
  3. `claude` (80): project `.claude/skills/` (walk-up, **default on**); user `~/.claude/skills/` **opt-in** (`enabledProviders: [claude]` or `*`/`all`, or `skills.enableClaudeUser: true`, or `CLAUDE_CONFIG_DIR` set).
  4. (70) `claude-plugins`, `agents` (`~/.agent[s]/skills` + project `.agent[s]/skills` walk-up — default on; "canonical OMP-native location"), `codex` (`~/.codex/skills` opt-in).
  5. `opencode` (55), `github` (30, project `.github/skills/`), `omp-managed` (5, `~/.omp/agent/managed-skills`, auto-learn).
- Foreign user-level sources opt-in list: `cursor, codex, claude, claude-plugins, gemini, opencode, windsurf, github` (`FOREIGN_USER_PROVIDERS`); `enabledProviders` default `[]` (settings.md). README's claim that omp "inherits ... skills ... from .claude, .cursor, ..." holds for project roots by default, user roots only when opted in.
- Filters: `skills.customDirectories`, `ignoredSkills`, `includeSkills`, `disabledExtensions: [skill:<name>]`, `skills.enabled`, CLI `--skills <globs>`, `--no-skills`. `/skill:<name> [args]` commands when `skills.enableSkillCommands`. `skill://<name>/...` URLs.
- Registry: `omp skill install|search|publish|update|uninstall ...` (Skillshare registry skills.omp.sh; `-g` = user-global `skills.json`) (observed `omp skill --help`).
- Slash commands (markdown): native `~/.omp/agent/commands/*.md` and `<cwd>/.omp/commands/*.md` (cwd only); `.agents/commands` / `~/.agents/commands`; Claude `.claude/commands/*.md` (recursive, namespaced aliases; user dir opt-in). Prompts: `~/.omp/agent/prompts`, `.omp/prompts`, `.agent[s]/prompts`. Also `RULES.md`, `AGENTS.md`, `SYSTEM.md` in `~/.omp/agent` / `.omp` (discovery/builtin.ts, agents.ts, claude.ts).
- Bundled subagents exportable: `omp agents unpack [--project]` → `~/.omp/agent/agents` or `./.omp/agents`.

### 3.5 Config & pre-seeding
(https://github.com/can1357/oh-my-pi/blob/main/docs/settings.md; providers.md; models.md)
- Global `~/.omp/agent/config.yml` (or existing `config.yaml`; legacy `settings.json` migrated once). Project `<cwd>/.omp/config.yml` (+ legacy `.omp/settings.json`), cwd only, no ancestor walk. Overlays `--config <file>` / `PI_CONFIG_FILES`. Precedence: defaults < global < project < overlays < runtime flags < setting env var. Arrays replaced, objects deep-merged.
- `~/.omp/agent/models.yml` (custom providers; `apiKey` = env-var-name-or-literal or `!shell cmd`), `~/.omp/agent/secrets.yml` (obfuscation), `.env` files as above, `agent.db` (settings + auth SQLite), `sessions/`, `plugins/`. Profiles: `--profile <name>` / `OMP_PROFILE` → `~/.omp/profiles/<name>/agent`. `omp config init-xdg` for XDG layout. `omp config path` prints active agent dir.
- Scriptable: `omp config list|get|set|reset [--json]` (e.g. `omp config set modelRoles...`); README shows preconfiguring `modelRoles.default` in config.yml; Home Manager module `programs.omp.settings`. ⇒ settings/models are declaratively seedable YAML; credentials are **not** a flat file (SQLite) — seed via env/.env/models.yml or `omp auth-broker import`.
- `omp setup [python|speech] [--check] [--json]` = onboarding wizard / optional deps.

---

## 4. Cross-harness quick comparison

| | Hermes | Pi | omp |
|---|---|---|---|
| Install one-liner | `curl -fsSL https://hermes-agent.nousresearch.com/install.sh \| bash` | `curl -fsSL https://pi.dev/install.sh \| sh` or `npm i -g --ignore-scripts @earendil-works/pi-coding-agent` | `curl -fsSL https://omp.sh/install \| sh`, `bun i -g @oh-my-pi/pi-coding-agent`, `brew install can1357/tap/omp` |
| Runtime | Python 3.14 (PM-managed, bundled uv) | Node ≥ 22.19 | Bun ≥ 1.3.14 (or standalone binary) |
| Version cmd | `hermes --version` | `pi --version` | `omp --version` (`omp/X.Y.Z`) |
| Latest source | GitHub releases API | npm / `pi.dev/api/latest-version` | npm dist-tags / GitHub releases |
| Update | `hermes update [--check]` | `pi update [--all]` | `omp update [--check]` |
| CLI login | `hermes auth add <p>`, `hermes model`, `hermes setup --portal` | none in `pi` (TUI `/login`); `npx @earendil-works/pi-ai login` → ./auth.json | `omp login [<p>]`, `omp auth-broker login` |
| Cred store | `~/.hermes/auth.json` + `~/.hermes/.env` | `~/.pi/agent/auth.json` | `~/.omp/agent/agent.db` (SQLite) |
| User skills | `~/.hermes/skills` (+`external_dirs`) | `~/.pi/agent/skills`, `~/.agents/skills` | `~/.omp/agent/skills`, `~/.agents/skills` (+`~/.claude/skills` opt-in) |
| Project skills | `.hermes/skills`, `.agents/skills` (after `hermes skills trust`) | `.pi/skills`, `.agents/skills` (after project trust) | `.omp/skills`, `.agents/skills`, `.claude/skills`, `.github/skills` |
| Prompt/slash cmds | none (skills = `/<name>`, `quick_commands`, `bundles`) | `~/.pi/agent/prompts`, `.pi/prompts` | `~/.omp/agent/commands`, `.omp/commands`, `.claude/commands`, `.agents/commands`; prompts dirs |
| Codex callback | 1455 (opt-in `--browser`; device code default) | 1455 or device code (select) | 1455 fixed, or `openai-codex-device` |
| Anthropic callback | paste-code | 53692 + paste | 54545 (+ paste fallback per KDL) |
