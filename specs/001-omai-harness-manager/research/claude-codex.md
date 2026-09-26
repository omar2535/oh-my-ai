# Claude Code & OpenAI Codex CLI — install / update / auth / skills / config facts

Research date: 2026-09-26. Facts only, no design decisions. `[UNVERIFIED]` = not confirmed from a primary source or by running it. `[INFERENCE]` = my reading of a source, not a stated fact.
Local checks were read-only (help text, `--version`, `auth status`, `doctor`, key *names* in credential files). No secrets were printed.

---

## 0. Latest versions as of 2026-09-26 (fetched live)

| Harness | Channel / source | Version |
|---|---|---|
| Claude Code | `https://downloads.claude.ai/claude-code-releases/latest` | **2.1.283** |
| Claude Code | `https://downloads.claude.ai/claude-code-releases/stable` | **2.1.274** |
| Claude Code | npm dist-tags `{stable: 2.1.274, latest: 2.1.283, next: 2.1.283}` (https://registry.npmjs.org/-/package/@anthropic-ai/claude-code/dist-tags) | 2.1.283 |
| Claude Code | GitHub `anthropics/claude-code` latest release tag `v2.1.283` (published 2026-09-25T21:50Z) | 2.1.283 |
| Claude Code | brew cask `claude-code` = 2.1.274 (stable), `claude-code@latest` = 2.1.283 (https://formulae.brew.sh/api/cask/claude-code.json, https://formulae.brew.sh/api/cask/claude-code@latest.json) | |
| Codex CLI | npm `@openai/codex` `latest` = **0.157.1**; `alpha` = 0.159.0-alpha.4 (https://registry.npmjs.org/-/package/@openai/codex/dist-tags) | 0.157.1 |
| Codex CLI | GitHub `openai/codex` releases/latest tag `rust-v0.157.1` (published 2026-09-26T01:02Z) | 0.157.1 |
| Codex CLI | `https://releases.openai.com/codex/channels/latest` → `tag_name: rust-v0.157.1` | 0.157.1 |
| Codex CLI | brew cask `codex` = 0.157.1 (https://formulae.brew.sh/api/cask/codex.json) | |

Neither has a Homebrew *formula* (formula API returns 404 for `codex` and `claude-code`); both are casks.

Local machine: `claude` 2.1.278 (native install, `~/.local/bin/claude` → `~/.local/share/claude/versions/2.1.278`); `codex-cli 0.156.0` (npm global under nvm Node v22.18.0); `brew` not installed.

---

# PART A — Claude Code (Anthropic)

## A1. Install methods (Linux/WSL2, macOS)
Source: https://code.claude.com/docs/en/setup

| Method | Command | Notes |
|---|---|---|
| **Native installer (Recommended)** | `curl -fsSL https://claude.ai/install.sh \| bash` | macOS, Linux, WSL. Args: `bash -s stable`, `bash -s latest`, `bash -s 2.1.89`. Auto-updates in background. |
| Homebrew | `brew install --cask claude-code` (stable channel, ~1 week behind) or `brew install --cask claude-code@latest` | No auto-update by default; `brew upgrade claude-code[@latest]`. |
| npm | `npm install -g @anthropic-ai/claude-code` | Requires Node.js ≥22 as of v2.1.198 (older Node gives an `EBADENGINE` warning but still works). Installs the same native binary via per-platform optional deps (`@anthropic-ai/claude-code-linux-x64`, `-darwin-arm64`, `-linux-x64-musl`, …); `claude` does not run on Node at runtime. Upgrade with `npm install -g @anthropic-ai/claude-code@latest`, not `npm update -g`. Don't use `sudo npm`. |
| apt / dnf / apk | Signed repos at `https://downloads.claude.ai/claude-code/{apt,rpm,apk}/{stable,latest}`; key `https://downloads.claude.ai/keys/claude-code.asc` (fingerprint `31DD DE24 DDFA B679 F42D 7BD2 BAA9 29FF 1A7E CACE`) | No auto-update; system package manager upgrades it. |
| WinGet (Windows only) | `winget install Anthropic.ClaudeCode` | n/a for Linux/macOS. |

**Native installer internals** (read from https://claude.ai/install.sh):
- Needs `curl` or `wget`; `jq` and `zstd` optional. Refuses to run under `sudo` from a user shell unless `CLAUDE_INSTALL_ALLOW_SUDO=1`.
- Gets the version from `https://downloads.claude.ai/claude-code-releases/latest`, then `…/<ver>/manifest.json` (per-platform sha256 + size), downloads `…/<ver>/<platform>/claude` (or `claude.zst`) into `~/.claude/downloads/`, checks sha256, then runs `<binary> install [stable|latest|VERSION]`. That step sets up the launcher `~/.local/bin/claude` as a symlink into `~/.local/share/claude/versions/<ver>`.
- Platforms: `darwin-{x64,arm64}`, `linux-{x64,arm64}`, `linux-{x64,arm64}-musl`, `win32-{x64,arm64}`. On Rosetta it installs the arm64 build.
- The manifest is GPG-signed (`manifest.json.sig`) for releases ≥ 2.1.89.

**Prerequisites** (setup doc): macOS 13+, Ubuntu 20.04+, Debian 10+, Alpine 3.19+ (musl needs `bash curl libgcc libstdc++ ripgrep` plus `USE_BUILTIN_RIPGREP=0`); 4 GB+ RAM; x64/arm64. ripgrep is usually bundled. WSL2 is supported, and sandboxing works on WSL2. WSL1 has a known native-binary `Exec format error` regression (https://code.claude.com/docs/en/troubleshoot-install). Installing needs about 512 MB free memory (install.sh message).

## A2. Version / latest / update
- **Installed version:** `claude --version` (or `-v`) prints e.g. `2.1.283 (Claude Code)`. Parse the first token.
- **Latest available, programmatically:**
  - Native channel pointers (plain text): `GET https://downloads.claude.ai/claude-code-releases/latest` and `…/stable`. This is what install.sh uses.
  - Per-version manifest: `GET https://downloads.claude.ai/claude-code-releases/<ver>/manifest.json`, with keys `version`, `buildDate`, `platforms.<plat>.{checksum,size}`.
  - npm: `GET https://registry.npmjs.org/@anthropic-ai/claude-code/latest` (`.version`) or the dist-tags endpoint above. It has `stable`, `latest`, and `next`.
  - GitHub: `GET https://api.github.com/repos/anthropics/claude-code/releases/latest` (tag `vX.Y.Z`); CHANGELOG at https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md.
  - Homebrew cask JSON (see §0).
- **Self-update** (https://code.claude.com/docs/en/setup#update-claude-code):
  - Native installs check at startup and periodically, download in the background, and apply on the next start.
  - `claude update` (alias `claude upgrade`) updates immediately. It prints `Successfully updated from <old> to version <new>` or `Claude Code is up to date (<ver>)`; brew/winget/apk installs print `Claude is up to date!`.
  - `claude install [stable|latest|<ver>]` installs or reinstalls the native binary.
  - Channel: the `autoUpdatesChannel` setting (`"latest"` default | `"stable"`). `minimumVersion` sets a floor. Managed `requiredMinimumVersion`/`requiredMaximumVersion` refuse startup outside a range.
  - Homebrew/WinGet: no auto-update by default; opt in with env `CLAUDE_CODE_PACKAGE_MANAGER_AUTO_UPDATE=1`. apt/dnf/apk are always manual.
  - npm global: auto-updates if the npm global dir is writable. Otherwise it shows a notice and `claude doctor` lists fixes.
  - A custom launcher replacing `~/.local/bin/claude` is left alone by the updater (since v2.1.207).
- **Disable updates:**
  - `DISABLE_AUTOUPDATER=1` (env, or `"env"` block in settings.json) stops only the background check. `claude update`/`claude install` still work.
  - `DISABLE_UPDATES=1` blocks every update path, including manual.
  - `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` also turns off the plugin auto-update pass (docs llms-full).
- **Diagnostics:** `claude doctor` is read-only and non-interactive. It reports install method, path, `Auto-updates: enabled|disabled (set by env: …)`, `Auto-update channel`, `Last update attempt`, and settings validation. Local run showed: `Config install method: native`, `Auto-updates: enabled`, `Auto-update channel: latest`, `Last update attempt: success → 2.1.278`.
- `~/.claude.json` also holds `installMethod` (local value `"native"`) and legacy `autoUpdates` keys (observed locally; not documented as a user setting).

## A3. Authentication
Sources: https://code.claude.com/docs/en/authentication, https://code.claude.com/docs/en/cli-reference, https://code.claude.com/docs/en/troubleshoot-install#login-and-authentication

**Account types:**
- Claude Pro/Max subscription (claude.ai OAuth).
- Team/Enterprise (claude.ai OAuth).
- Claude Console. Either keyless OAuth "Anthropic profile" (v2.1.242+) or a legacy auto-created Console API key.
- Bedrock / Vertex ("Google Cloud's Agent Platform") / Microsoft Foundry through env vars.
- Claude apps gateway (SSO).
- The free claude.ai plan has no Claude Code access.

**CLI commands (verified via local `--help`, v2.1.278):**
- `claude auth login [--claudeai (default) | --console] [--email <e>] [--sso]`. Starts the browser OAuth flow. **Prints the login URL**, and in WSL2/SSH/containers **reads the pasted code from stdin**. Docs: "copy the URL that `claude auth login` prints … `claude auth login`, which reads the pasted code from standard input".
- `claude auth logout`.
- `claude auth status [--json (default) | --text]`. **Exit 0 if logged in, 1 if not.**
  - Local JSON keys observed: `loggedIn`, `authMethod`, `apiProvider`, `configDirectory`, `projectsDirectory`, `analyticsDisabled`. The local state was expired, so it showed `loggedIn:false`, `authMethod:"none"`, `apiProvider:"firstParty"`, exit 1.
  - `--text` showed `Login: Expired — log in again` plus org/email rows. Extra fields present when logged in (email/org/subscription) are `[UNVERIFIED]`.
- `claude setup-token`. Same browser flow, then **prints** a ~1-year OAuth token to stdout without saving it. Used as `CLAUDE_CODE_OAUTH_TOKEN`. Needs a Pro/Max/Team/Enterprise plan. The token can only make model requests (no Remote Control, no claude.ai connectors). `--bare` mode ignores it.
- In-session: `/login`, `/logout`, `/status`.
- Interactive login UX: the browser opens automatically. If it doesn't, press `c` to copy the URL. If the browser can't reach the localhost callback (WSL2/SSH/containers), it shows a code to paste at `Paste code here if prompted`. On WSL2 you can set `BROWSER="/mnt/c/.../chrome.exe"`.
- There is no device-code flow; the fallback is the manual code paste.
- **Non-interactive login:** no command takes a credential on stdin and persists it (unlike codex). The non-interactive routes are env vars: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, or the `apiKeyHelper` setting (a script that prints a key; re-run every 5 min by default, `CLAUDE_CODE_API_KEY_HELPER_TTL_MS`). `ANTHROPIC_API_KEY` in interactive mode asks once for approval; with `-p` it is always used.

**Precedence** (highest first):
1. Cloud provider (`CLAUDE_CODE_USE_BEDROCK` / `_VERTEX` / `_FOUNDRY`)
2. `ANTHROPIC_AUTH_TOKEN` (Bearer)
3. `ANTHROPIC_API_KEY` (X-Api-Key)
4. `apiKeyHelper`
5. `CLAUDE_CODE_OAUTH_TOKEN`
6. Anthropic profile / WIF (`ANTHROPIC_PROFILE`, `~/.config/anthropic`)
7. Subscription OAuth from `/login`

A gateway session sits outside this list and outranks everything.

**Credential storage:**
- macOS: login Keychain. It falls back to `~/.claude/.credentials.json` (0600) when the Keychain is locked, e.g. over SSH.
- Linux/WSL: `~/.claude/.credentials.json` (mode 0600).
- Windows: `%USERPROFILE%\.claude\.credentials.json`.
- `CLAUDE_CONFIG_DIR` relocates the file and namespaces the macOS Keychain entry.
- Local file exists at `~/.claude/.credentials.json`, mode `-rw-------`, top-level keys `claudeAiOauth`, `mcpOAuth`.
- `~/.claude.json` (0600 locally) also holds `oauthAccount` metadata, `userID`, onboarding state, and per-project trust.

**Token lifetime:** the login warns 3 days before expiry (v2.1.203+). An expired login fails with `Login expired · Please run /login`. Parallel sessions coordinate refresh.

## A4. Terms / restrictions on reusing Claude subscription OAuth
- **Current primary policy** (https://code.claude.com/docs/en/legal-and-compliance, fetched 2026-09-26), section "Authentication and credential use":
  - "OAuth authentication is intended exclusively for purchasers of Claude Free, Pro, Max, Team, and Enterprise subscription plans and is designed to support ordinary use of Claude Code and other native Anthropic applications."
  - "Anthropic does not permit third-party developers to offer Claude.ai login into their own applications, or to route requests through Free, Pro, or Max plan credentials on behalf of their users. Moreover, developers may not collect, store, or intermediate Claude.ai credentials or session tokens — sign-in to a Claude account must complete through Anthropic's own flow."
  - It also says this doesn't "prevent an end user from signing in to the unmodified Claude Code binary with their own Claude subscription".
  - Products that preinstall or run Claude Code must not modify the binary and must not "remove, disable, or restrict any authentication method built into it".
  - "Anthropic reserves the right to take measures to enforce these restrictions and may do so without prior notice."
- **Consumer Terms §3.7** (https://www.anthropic.com/legal/consumer-terms, effective 2025-10-08) forbids: "Except when you are accessing our Services via an Anthropic API Key or where we otherwise explicitly permit it, to access the Services through automated or non-human means, whether through a bot, script, or otherwise."
- **Timeline (secondary sources):**
  - **2026-01-09:** Anthropic technically blocked third-party tools "spoofing the Claude Code harness" with subscription OAuth (VentureBeat: https://venturebeat.com/technology/anthropic-cracks-down-on-unauthorized-claude-usage-by-third-party-harnesses; Thariq Shihipar thread https://x.com/trq212/status/2009689809875591565 cited by The Register).
  - **2026-02-19/20:** docs updated to say "Using OAuth tokens obtained through Claude Free, Pro, or Max accounts in any other product, tool, or service — including the Agent SDK — is not permitted and constitutes a violation of the Consumer Terms of Service." OpenCode removed Claude Pro/Max support citing "anthropic legal requests" (The Register: https://www.theregister.com/software/2026/02/20/anthropic-clarifies-ban-on-third-party-tool-access-to-claude/5014546). That exact sentence is no longer on the page today; the current wording is quoted above.
  - **2026-04-04 12:00 PT:** subscriptions stopped covering third-party harness usage (OpenClaw, OpenCode, etc.). Users need "extra usage" pay-as-you-go or an API key (Engadget: https://www.engadget.com/ai/its-no-longer-free-to-use-claude-through-third-party-tools-like-openclaw-160912082.html).
  - **2026-05-13:** Anthropic announced a separate monthly "Agent SDK credit" from June 15. **2026-06-15:** that change was **paused**. The primary support page now says: "For now, nothing has changed: Claude Agent SDK, `claude -p`, and third-party app usage still draw from your subscription's usage limits" (https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan; The New Stack: https://thenewstack.io/anthropic-pauses-claude-agent-sdk-subscription-change/; Zed: https://zed.dev/blog/anthropic-subscription-changes).
  - No newer change found through 2026-09-26 (search, recency=month).
- **[INFERENCE] for a wrapper:**
  - Launching the unmodified `claude` binary and letting the user finish `claude auth login` in Anthropic's own flow matches the "end user signing in to the unmodified Claude Code binary" carve-out.
  - Reading or copying `~/.claude/.credentials.json`, capturing and storing `claude setup-token` output, or calling Anthropic APIs directly with the user's OAuth token would fall under "collect, store, or intermediate … credentials or session tokens".
  - Showing the login URL that `claude auth login` prints is not addressed explicitly.

## A5. Skills & commands
Source: https://code.claude.com/docs/en/skills

| Scope | Path |
|---|---|
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` |
| Project | `.claude/skills/<skill-name>/SKILL.md`. Loaded from the CWD and every parent up to the repo root; nested `<subdir>/.claude/skills` load lazily when Claude touches files there. |
| Enterprise | `/etc/claude-code/.claude/skills/<name>/` (Linux/WSL), `/Library/Application Support/ClaudeCode/.claude/skills/` (macOS) |
| `--add-dir` dirs | `<dir>/.claude/skills/` (plus `.claude/commands/`, `.claude/agents/`) |
| Plugin | `<plugin>/skills/<name>/SKILL.md`, invoked as `/plugin-name:skill-name` |
| claude.ai-synced | `~/.claude/skills/synced/` (reserved name; managed by Claude Code, don't author there) |

- **Format:** follows the Agent Skills open standard (https://agentskills.io). YAML frontmatter goes between `---` markers on line 1.
  - `name` is optional (defaults to the dir name). `description` is recommended.
  - Claude-specific extensions: `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `paths`, etc.
  - Codex requires `name` + `description` (§B5). A SKILL.md carrying both is portable `[INFERENCE]`.
- Symlinked skill folders are supported, and a skill loads once even if several locations point to it.
- **Claude Code does NOT read `.agents/`.** The docs' AGENTS.md section says: "Not read: `AGENTS.local.md`, `AGENTS.override.md`, or anything under a `.agents/` directory" (https://code.claude.com/docs/en/memory). So `~/.agents/skills` (Codex's user path) is not picked up by Claude.
- Instructions: `CLAUDE.md` / `.claude/CLAUDE.md`. Recent versions read `AGENTS.md` when there is no CLAUDE.md, configurable under `/config` "Project instructions" (changelog in https://code.claude.com/docs/llms-full.txt).
- **Custom slash commands:** `~/.claude/commands/*.md` and `.claude/commands/*.md`. This is the older format, now merged into skills; it still works and a skill wins on a name clash.
- Plugins: `claude plugin install <plugin>[@marketplace]`, `claude plugin marketplace …`, `claude plugin init <name>` (scaffolds at `~/.claude/skills/<name>/`), `--plugin-dir`, `--plugin-url`.
- Skill directories are watched live, except in `--bare` mode.

## A6. Config files & declarative pre-seeding
Sources: https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/settings-reference, https://code.claude.com/docs/en/managed-settings

**Precedence** (highest first):
1. Managed: `/etc/claude-code/managed-settings.json` plus `managed-settings.d/*.json` drop-ins on Linux/WSL; `/Library/Application Support/ClaudeCode/managed-settings.json` on macOS; MDM; server-managed.
2. CLI flags (`--settings`).
3. `.claude/settings.local.json`.
4. `.claude/settings.json`.
5. `~/.claude/settings.json`.

- Settings files are strict JSON (no comments or trailing commas) with a published schema `https://json.schemastore.org/claude-code-settings.json`. **They can be written declaratively before first run.** The user file is created by Claude Code only when you change a `/config` option, so pre-creating it is the documented flow.
- Useful keys: `env` (e.g. `DISABLE_AUTOUPDATER`), `autoUpdatesChannel`, `minimumVersion`, `permissions`, `apiKeyHelper`, `forceLoginMethod`, `syncClaudeAiSkills`, `disableBundledSkills`.
- `~/.claude.json` is Claude Code's own state file ("you don't need to edit it"). It holds sign-in session metadata, user-scope MCP servers, per-project trust, and "global config" keys (`autoConnectIde`, `diffTool`, `copyOnSelect`, …).
  - The onboarding flag `hasCompletedOnboarding` exists locally but is **not documented**, so pre-seeding it is `[UNVERIFIED]`.
- `CLAUDE_CONFIG_DIR` relocates `~/.claude` (settings, credentials, plugins, history).
- Project MCP config: `.mcp.json`.

---

# PART B — OpenAI Codex CLI

Docs moved to **learn.chatgpt.com** (the developers.openai.com/codex llms.txt points there). Index: https://developers.openai.com/codex/llms.txt; condensed manual: https://learn.chatgpt.com/docs/codex-manual.md.

## B1. Install methods (Linux/WSL2, macOS)
Source: https://learn.chatgpt.com/docs/codex/cli

| Method | Install | Update |
|---|---|---|
| **Standalone installer** (listed first) | `curl -fsSL https://chatgpt.com/codex/install.sh \| sh` | Re-run the same command |
| npm | `npm install -g @openai/codex` | `npm install -g @openai/codex` |
| Homebrew | `brew install --cask codex` | `brew upgrade --cask codex` |

The docs don't label one as "recommended"; the standalone installer comes first `[INFERENCE: preferred]`. Windows uses `install.ps1`.

**Standalone installer internals** (https://chatgpt.com/codex/install.sh):
- Needs `sh`, `mktemp`, `tar`, `curl`|`wget`, and `sha256sum`|`shasum`|`openssl`.
- Options: `--release <ver>` or env `CODEX_RELEASE` (default `latest`). `CODEX_NON_INTERACTIVE=1` skips prompts. `CODEX_INSTALL_DIR` defaults to `~/.local/bin`. `CODEX_INSTALLER_USE_RELEASES_OPENAI_COM=0` forces GitHub.
- Metadata: `https://releases.openai.com/codex/channels/latest` (or `/releases/<ver>/release.json`), falling back to `https://api.github.com/repos/openai/codex/releases/latest`.
- Asset: `codex-package-<target>.tar.gz` plus `codex-package_SHA256SUMS`. Targets: `x86_64-unknown-linux-musl`, `aarch64-unknown-linux-musl`, `{x86_64,aarch64}-apple-darwin`.
- Unpacks to `$CODEX_HOME/packages/standalone/releases/<ver>-<target>`. The `current` symlink points to it, and `~/.local/bin/codex` → `current/bin/codex`.
- Writes `auto-update-version` when installing `latest`.
- Appends a PATH block (`# >>> Codex installer >>>`) to `~/.bashrc`/`~/.zshrc`/`~/.zprofile`/`~/.bash_profile`/`~/.profile`.
- Detects an existing npm/bun/brew `codex` and offers to uninstall it (auto-declines when non-interactive).
- May prompt "Start Codex now?".

**Prerequisites:**
- npm package: `engines.node >= 16` (https://registry.npmjs.org/@openai/codex/latest). It pulls a platform binary via optional deps aliased to `@openai/codex@<ver>-linux-x64`, etc.
- Standalone binary: static musl, no runtime deps.
- Linux/WSL2 sandbox uses `bubblewrap`. Install `bwrap` from the distro (`sudo apt install bubblewrap`). The bundled helper needs unprivileged user namespaces.
- **WSL1 is unsupported since Codex 0.115**; WSL2 works (codex manual, "Sandbox" / "Windows" sections).
- macOS uses Seatbelt.

## B2. Version / latest / update
- **Installed version:** `codex --version` / `-V` prints `codex-cli 0.156.0`. install.sh parses the last token.
- **Latest available, programmatically:**
  - `GET https://api.github.com/repos/openai/codex/releases/latest` → `tag_name: "rust-v0.157.1"` (strip `rust-v`). Subject to GitHub rate limits.
  - `GET https://releases.openai.com/codex/channels/latest` → `tag_name`, same shape as GitHub release JSON with assets and digests.
  - npm: `GET https://registry.npmjs.org/@openai/codex/latest` → `.version`, or dist-tags (note the `alpha` tag).
  - brew: `GET https://formulae.brew.sh/api/cask/codex.json` → `.version`.
- **Built-in update check** (source: https://github.com/openai/codex/blob/main/codex-rs/tui/src/updates.rs, `update_action.rs`):
  - The TUI checks on startup unless `check_for_update_on_startup = false` in config.toml. That key can also be enforced in `requirements.toml`.
  - The latest version comes from the brew cask API for brew installs, the npm registry for npm/bun/pnpm, and GitHub releases/latest for standalone or unknown installs.
  - It is cached in `$CODEX_HOME/version.json` with keys `latest_version`, `last_checked_at`, `dismissed_version` (verified locally).
  - The TUI then offers to run the right updater:
    - `npm install -g @openai/codex`
    - `bun install -g @openai/codex`
    - `pnpm add -g @openai/codex`
    - `brew upgrade --cask codex`
    - `curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh`
- **`codex update`:** "Check for and apply a Codex CLI update when the installed release supports self-update" (codex manual). It is not available in debug builds.
- **Background auto-update:** the shared app-server daemon has a scheduled update loop (`codex-rs/app-server-daemon/src/update_loop.rs`: "Owns scheduled and manual installs…"). It re-runs `https://chatgpt.com/codex/install.sh` with `CODEX_RELEASE=latest CODEX_NON_INTERACTIVE=1 CODEX_INSTALL_IF_LATEST=1`, and install.sh only proceeds if the current selection still follows the `latest` channel (`auto-update-version` file).
  - `[INFERENCE]` This applies to standalone installs using the daemon (`codex agents`/`app-server`); npm/brew installs are not self-replaced.
  - `features.in_app_updates=false` in requirements.toml documents disabling in-app updates for the desktop app. Whether it also gates the CLI daemon is `[UNVERIFIED]`.
- **Disable:** `check_for_update_on_startup = false` (user config.toml, or enforced via `/etc/codex/requirements.toml`). Or pin with `--release <ver>`, which makes install.sh remove `auto-update-version`.
- **Diagnostics:** `codex doctor [--json|--summary|--all]`.
  - JSON top-level keys: `checks`, `codexVersion`, `generatedAt`, `overallStatus`, `schemaVersion`.
  - Check ids include `updates.status`, `installation`, `auth.credentials`, `runtime.provenance`, `sandbox.helpers`, and others.
  - Local summary showed `updates 0.157.1 available (current 0.156.0)` and `auth is configured`.

## B3. Authentication
Sources: https://learn.chatgpt.com/docs/auth, local `codex login --help` (0.156.0), source `codex-rs/cli/src/login.rs`, `codex-rs/login/src/server.rs`, `codex-rs/login/src/device_code_auth.rs`

**Methods:**
- **Sign in with ChatGPT** (Plus/Pro/Business/Enterprise subscription). `codex login` runs a browser OAuth+PKCE flow against `https://auth.openai.com` with a local callback server on **`localhost:1455`**.
  - Prints to **stderr**: `Starting local login server on http://localhost:1455.\nIf your browser did not open, navigate to this URL to authenticate:\n\n<auth_url>\n\nOn a remote or headless machine? Use \`codex login --device-auth\` instead.`
  - So a wrapper can capture the URL. Exit 0 on success.
- **Device code (beta):** `codex login --device-auth`. Prints to **stdout** a verification URL `https://auth.openai.com/codex/device` and a one-time code that expires in 15 minutes.
  - The user must first enable device-code login in ChatGPT security settings (workspace admins enable it for workspaces).
  - The TUI onboarding has a "Sign in with Device Code" option.
- **API key:** `printenv OPENAI_API_KEY | codex login --with-api-key` reads stdin and persists; it's the non-interactive login.
  - The TUI onboarding detects `OPENAI_API_KEY` in the env and prefills it (`codex-rs/tui/src/onboarding/auth.rs`).
  - `CODEX_API_KEY` env is read by `codex exec`/review/SDK only (not persisted).
- **Access token** (Enterprise automation): `printenv CODEX_ACCESS_TOKEN | codex login --with-access-token`. The `CODEX_ACCESS_TOKEN` env var also works.
- Workload identity: `OPENAI_FEDERATION_RULE_ID` + `OPENAI_IDENTITY_TOKEN_FILE`. In that mode `codex login`/`logout` are rejected.
- Amazon Bedrock auth modes also exist.
- **Headless fallbacks** (docs):
  - Copy `~/.codex/auth.json` from a machine that has a browser.
  - Or tunnel the callback: `ssh -L 1455:localhost:1455 user@remote`, then `codex login`.
- **Important:** browser and device-code `codex login` first **log out and revoke** any existing stored credentials (`clear_existing_auth_before_login` in login.rs).
- Login logs go to `codex-login.log` under the log dir (`$CODEX_HOME/log`).
- Custom CA: `CODEX_CA_CERTIFICATE`, falling back to `SSL_CERT_FILE`.

**Status and logout:**
- `codex login status` prints to stderr and exits **0 if logged in, 1 if not**. Messages:
  - `Logged in using ChatGPT`
  - `Logged in using an API key - sk-…` (masked)
  - `Logged in using access token`
  - `Logged in using personal access token`
  - `Logged in using Amazon Bedrock …`
  - `Logged in using workload identity`
  - `Not logged in`
- Verified locally: exit 0 with the real home; exit 1 `Not logged in` with an empty `CODEX_HOME`.
- `codex logout`.

**Credential storage:**
- `cli_auth_credentials_store = "file" | "keyring" | "auto" | "ephemeral"` in config.toml. **Default is `file`** (`codex-rs/config/src/types.rs`), i.e. `$CODEX_HOME/auth.json`, with `CODEX_HOME` defaulting to `~/.codex`.
- The keyring service name is `"Codex Auth"` (`codex-rs/login/src/auth/storage.rs`).
- The CLI and IDE extension share the cache. ChatGPT tokens auto-refresh.
- Local file `~/.codex/auth.json` exists, mode `-rw-------`. Top-level keys: `OPENAI_API_KEY`, `auth_mode`, `last_refresh`, `tokens`.
- Admin controls: `forced_login_method = "chatgpt"|"api"` and `forced_chatgpt_workspace_id`.

## B4. Terms / stance on third-party use of ChatGPT subscription OAuth
- **No formal OpenAI terms clause found that authorizes or forbids third-party harnesses using "Sign in with ChatGPT".**
- The OpenAI Terms of Use (effective 2026-01-01, https://openai.com/policies/row-terms-of-use/) prohibit sharing account credentials or making the account available to others, "Automatically or programmatically extract data or Output", and circumventing rate limits or protective measures.
- Public statements (secondary sources):
  - Jan 2026: Thibault Sottiaux (OpenAI) "pointedly endorsed the use of Codex subscriptions in third-party harnesses" (https://x.com/thsottiaux/status/2009742187484065881, reported by The Register, link in §A4).
  - Aug 21, 2026: Sottiaux said "sub2api" (turning subscriptions into redistributed API traffic) is unsupported and triggers fraud prevention, while "anyone using official clients or open-source tools like Pi and OpenCode that support Sign in With ChatGPT is completely fine" (Memeburn: https://memeburn.com/openai-codex-reaches-20-million-users-amid-usage-limit-complaints/). `[UNVERIFIED against the original X post]`
- auth.json guidance: "treat `~/.codex/auth.json` like a password" (https://learn.chatgpt.com/docs/auth).

## B5. Skills & prompts
Sources: https://learn.chatgpt.com/docs/build-skills, source `codex-rs/ext/skills/src/host_roots.rs`

| Scope | Path |
|---|---|
| REPO | `.agents/skills/` in every dir from CWD up to the repo root; also the project config folder's `.codex/skills/` (source: Project config layer → `<config_folder>/skills`) |
| USER | **`$HOME/.agents/skills/`** (documented). The deprecated `$CODEX_HOME/skills/` (`~/.codex/skills`) is "kept for backward compatibility" (source comment). |
| ADMIN | `/etc/codex/skills` |
| SYSTEM | Bundled, cached at `$CODEX_HOME/skills/.system` |

- **Format:** Agent Skills standard (https://agentskills.io/specification). `SKILL.md` must have `name` and `description` in frontmatter, with optional `scripts/`, `references/`, `assets/`, and `agents/openai.yaml` (UI metadata, `policy.allow_implicit_invocation`, tool/MCP deps).
- Symlinked skill folders are supported. Same-name skills are not merged; both appear.
- Disable a skill via `[[skills.config]] path=".../SKILL.md" enabled=false` in `~/.codex/config.toml`.
- Invoke with `$skill-name`. The Skills catalog budget is ~2% of context.
- **Custom prompts (deprecated):** `~/.codex/prompts/*.md`, top level only, invoked as `/prompts:<name>` (https://learn.chatgpt.com/docs/custom-prompts). They are "Deprecated. Use skills."
- Plugins: `codex plugin add|list|remove|marketplace`.
- Instructions: `AGENTS.md` (project) and `~/.codex/AGENTS.md` (global).

## B6. Config files & declarative pre-seeding
Sources: https://learn.chatgpt.com/docs/config-file/config-reference, codex manual "Configuration precedence"

**Precedence** (highest first):
1. CLI flags / `-c key=value`
2. Project `.codex/config.toml`, root → cwd (**trusted projects only**)
3. `--profile` files (`$CODEX_HOME/<name>.config.toml`)
4. User `~/.codex/config.toml`
5. Cloud-managed defaults
6. `/etc/codex/config.toml`
7. Built-ins

- Enforced policy lives in `/etc/codex/requirements.toml` (and MDM); legacy `/etc/codex/managed_config.toml`.
- TOML can be pre-seeded declaratively. `--strict-config` errors on unknown keys.
- Project trust is stored in user config as `[projects."<abs path>"] trust_level = "trusted"|"untrusted"` (observed locally).
- Project config cannot set provider/auth/notify/profile/otel keys.
- Relevant keys: `check_for_update_on_startup`, `cli_auth_credentials_store`, `forced_login_method`, `model`, `model_reasoning_effort`, `approval_policy`, `sandbox_mode`, `[[skills.config]]`, `[mcp_servers.*]`, `[projects.*]`.
- `CODEX_HOME` relocates everything (config, auth, logs, sessions, skills, standalone packages); **the directory must already exist**. `CODEX_SQLITE_HOME` moves SQLite state.
- Local `~/.codex/` contains `config.toml` (0600), `auth.json` (0600), `version.json`, `AGENTS.md`, `skills/`, `rules/`, `plugins/`, `sessions/`, `history.jsonl`, and several `*.sqlite`.

---

## Quick comparison for wrapper integration

| Concern | Claude Code | Codex CLI |
|---|---|---|
| Recommended install | `curl -fsSL https://claude.ai/install.sh \| bash` | `curl -fsSL https://chatgpt.com/codex/install.sh \| sh` (listed first) |
| Version cmd | `claude --version` → `X.Y.Z (Claude Code)` | `codex --version` → `codex-cli X.Y.Z` |
| Latest endpoint | `downloads.claude.ai/claude-code-releases/{latest,stable}` (plain text) | `api.github.com/repos/openai/codex/releases/latest` (`rust-vX.Y.Z`) or `releases.openai.com/codex/channels/latest` |
| Self-update cmd | `claude update` | `codex update` (or re-run install.sh) |
| Disable auto-update | `DISABLE_AUTOUPDATER=1` / `DISABLE_UPDATES=1` | `check_for_update_on_startup=false` |
| Login cmd | `claude auth login [--console] [--sso]` (URL printed; manual code via stdin) | `codex login` (URL on stderr, port 1455), `--device-auth`, `--with-api-key` (stdin), `--with-access-token` (stdin) |
| Status cmd (exit code) | `claude auth status --json` (0/1) | `codex login status` (0/1, text on stderr) |
| Long-lived token | `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` | API key or Enterprise access token |
| Cred store | `~/.claude/.credentials.json` (Linux), Keychain (macOS) | `~/.codex/auth.json` (default `file`), optional keyring "Codex Auth" |
| User skills | `~/.claude/skills/<n>/SKILL.md` | `~/.agents/skills/<n>/SKILL.md` (+ legacy `~/.codex/skills`) |
| Project skills | `.claude/skills/` | `.agents/skills/` (+ `.codex/skills/`) |
| Reads the other's dir? | No: `.agents/` explicitly not read | No `.claude/skills` in the source roots `[INFERENCE from host_roots.rs]` |
| Config | `~/.claude/settings.json` (JSON) + `~/.claude.json` (state) | `~/.codex/config.toml` (TOML) |
| Subscription OAuth in 3rd-party tools | Restricted: must use Anthropic's own flow in the unmodified binary; no collecting or intermediating tokens | Publicly tolerated for OSS harnesses (informal statements); sub2api-style redistribution unsupported |
