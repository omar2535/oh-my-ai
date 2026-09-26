# spec-kit, grill-me/grilling, and vercel-labs `skills` CLI — facts for oh-my-ai

Researched 2026-09-26 by SkillsSpeckitResearch. Facts only, no design decisions. Where something wasn't directly observed it's marked **[UNVERIFIED]** or **[INFERENCE]**.
How I checked things: read local files in the repo (read-only), ran the local `specify` 0.16.2 (help, `check`, `integration list/status`, `self check`, `self upgrade --dry-run`), ran specify **1.0.12** via `uvx`/`uv run --with` in `/tmp` scratch projects (Hermes install was sandboxed with `HOME=/tmp/fakehome`), unpacked the 1.0.12 wheel from PyPI, and read the source of `skills@1.7.0` from the npx cache.

---

## 0. Current state of the repo (this repo)

- The installed CLI is `specify-cli v0.16.2`, a `uv tool` install at `~/.local/bin/specify` (`uv tool list`). `specify self check` reports **Update available: 0.16.2 → v1.0.12**.
- `.specify/integration.json`:
  `{"version":"0.16.2","integration_state_schema":1,"installed_integrations":["omp"],"integration_settings":{"omp":{"script":"sh","invoke_separator":"."}},"integration":"omp","default_integration":"omp"}`
- `.specify/init-options.json`: `{"ai":"omp","feature_numbering":"sequential","here":true,"integration":"omp","script":"sh","speckit_version":"0.16.2"}`
- `.specify/integrations/omp.manifest.json` lists the 10 command files it installed under `.omp/commands/speckit.{analyze,checklist,clarify,constitution,converge,implement,plan,specify,tasks,taskstoissues}.md`. `.specify/integrations/speckit.manifest.json` tracks the shared scripts and templates (12 files).
- `.specify/workflows/workflow-registry.json` contains the bundled workflow `speckit` ("Full SDD Cycle" v1.0.0, source `bundled`). Its definition is `.specify/workflows/speckit/workflow.yml`.
- `skills-lock.json` is version 1 and holds 38 skills, all with `source: mattpocock/skills` and `sourceType: github`. Each entry has `skillPath` and `computedHash`. No entry has `ref` or `sourceUrl`.
- Skill layout on disk: the real files live in `.agents/skills/<name>/`. `.claude/skills/<name>`, `.hermes/skills/<name>` and `.pi/skills/<name>` are **relative symlinks** (`../../.agents/skills/<name>`). There is no `.omp/skills`.
- The global skills lock `~/.agents/.skill-lock.json` is version 3, with keys `version, skills, dismissed, lastSelectedAgents`. `skills` contains only `find-skills`. `lastSelectedAgents` = amp, cline, codex, cursor, droid, gemini-cli, github-copilot, kilo, kimi-code-cli, opencode, warp, zed, claude-code, pi, hermes-agent.
- The npx cache holds `skills@1.7.0` (latest) and `skills@1.5.11`.

---

## 1. github/spec-kit (Specify CLI)

### 1.1 Versions and distribution
- Latest release is **v1.0.12**, published 2026-09-25 (GitHub Releases API: https://api.github.com/repos/github/spec-kit/releases, https://github.com/github/spec-kit/releases/tag/v1.0.12). Earlier releases: 1.0.11 (09-24), 1.0.10 (09-22), 1.0.0 (2026-08-21). 0.16.2 came out 2026-08-10 (https://github.com/github/spec-kit/blob/main/CHANGELOG.md).
- **It is on PyPI** as `specify-cli`: https://pypi.org/project/specify-cli/ (JSON: https://pypi.org/pypi/specify-cli/json). Latest there is 1.0.12, uploaded 2026-09-25, with 67 releases going back to 0.9.4. It requires Python >= 3.11. The docs say PyPI is an *official* channel maintained by the Spec Kit maintainers, and PyPI versions track the GitHub tags (PyPI `X.Y.Z` = tag `vX.Y.Z`) (https://github.com/github/spec-kit/blob/main/docs/installation.md, https://github.com/github/spec-kit/blob/main/docs/install/pypi.md).
- License: MIT (https://github.com/github/spec-kit/blob/main/LICENSE).

### 1.2 Install

| Route | Command | Source |
|---|---|---|
| PyPI (the README quick-start now uses this) | `uv tool install specify-cli` (also `pipx install specify-cli`, `pip install specify-cli`); pin with `uv tool install specify-cli==X.Y.Z` | README, docs/install/pypi.md |
| Git source (docs call it "recommended", pinned to a tag) | `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@vX.Y.Z` (keep the `v`) | docs/installation.md |
| One-shot | `uvx --from git+https://github.com/github/spec-kit.git specify ...` or `uvx --from specify-cli==X specify ...` (temporary; does not update the persistent install) | docs/upgrade.md, docs/reference/integrations.md |

### 1.3 Installed vs latest version
- Installed version:
  - `specify --version` / `specify -V` prints `specify 0.16.2`.
  - `specify version` prints a Rich panel (CLI version, Python, platform).
  - In 1.0.12, **`specify version --features --json`** prints `{"version":"1.0.12","features":{...}}`. This is observed, offline and machine-readable. The feature keys are `controlled_multi_install_integrations, integration_use_command, multi_install_safe_registry_metadata, integration_upgrade_command, self_check_command, workflow_catalog, bundled_templates`.
  - `uv tool list` also shows `specify-cli vX`.
- Latest version:
  - **`specify self check`** is read-only and resolves the latest stable release through GitHub Releases. Output is either `Up to date: 1.0.12` or `Update available: 0.16.2 → v1.0.12`, followed by the upgrade and manual-fallback commands. It has no `--json` option (help observed in both 0.16.2 and 1.0.12).
  - Alternatives: PyPI JSON `info.version`, or GitHub `releases/latest`.
- `specify check` works offline. It scans for agent CLIs and does **not** compare versions (docs/reference/core.md, docs/upgrade.md).

### 1.4 Upgrade
- **`specify self upgrade`** upgrades immediately with no prompt. Variants: `--dry-run`, `--tag vX.Y.Z[suffix]`, and the env var `SPECIFY_UPGRADE_TIMEOUT_SECS`.
  - It auto-detects the install method: uv-tool, pipx, uvx (ephemeral), source checkout, or unsupported. Only uv-tool and pipx are upgraded automatically.
  - For uv-tool it runs `uv tool install specify-cli --force --from git+https://github.com/github/spec-kit.git@vX.Y.Z`. On this machine, `self upgrade --dry-run` printed exactly: `~/.local/bin/uv tool install specify-cli --force --from git+https://github.com/github/spec-kit.git@v1.0.12`.
  - Exit codes: 0 ok/no-op; 1 tag resolution/validation failure; 2 verification mismatch; 3 installer missing; 124 timeout; anything else is passed through from the installer (help text; docs/upgrade.md).
- Caveat: `self upgrade` **rebuilds PyPI installs from the Git URL**. To stay on PyPI, use `uv tool install --force specify-cli` or `pipx install --force specify-cli`, or `pip install --upgrade specify-cli`. `uv tool upgrade` keeps an existing version pin (docs/install/pypi.md).
- Refreshing a project after a CLI upgrade: run `specify integration upgrade <key>` once per installed integration, then `specify extension update`. Fallback: `specify init --here --force --integration <key>`. Upgrading never touches `.specify/memory/constitution.md`, and it blocks on locally modified managed files unless `--force` (docs/upgrade.md).

### 1.5 `specify init` flags (1.0.12, from `specify init --help` and docs/reference/core.md)
`specify init [PROJECT_NAME|.] [--here] [--force] [--integration KEY] [--integration-options "..."] [--script sh|ps|py] [--ignore-agent-tools] [--non-interactive] [--preset ID] [--extension X (repeatable)] [--trust-extension-urls]`
- **`--ai`, `--ai-commands-dir`, `--ai-skills` were removed in 0.10.0** (CHANGELOG: "feat!: remove legacy --ai, --ai-commands-dir, and --ai-skills flags (0.10.0) (#2872)"; `--ai` had been deprecated in 0.7.x, #2218). I checked this directly: both 0.16.2 and 1.0.12 reply `No such option: --ai`, and 1.0.12 replies `No such option: --ai-skills`. `--integration` replaces them.
- Skills vs commands mode is now chosen per integration through `--integration-options="--skills"` (or `--commands` / `--legacy-commands` on some integrations). The result is persisted as `"ai_skills": true` in `.specify/init-options.json`.
- `--non-interactive` is new in 1.0.x; 0.16.2 doesn't have it. It never prompts. Without `--integration` it falls back to **copilot**, which can be overridden with `SPECKIT_INTEGRATION_DEFAULT`.
- `--script` defaults to `sh` on non-Windows and `ps` on Windows. `py` also exists.
- Git init is no longer done by `init`. It needs `specify extension add git` (docs/reference/core.md).
- Init is offline: templates come bundled in the wheel.
- Other env vars: `SPECIFY_INIT_DIR` (points project-scoped commands at a project root), `SPECIFY_FEATURE_DIRECTORY`, `SPECIFY_FEATURE`, `SPECIFY_FEATURE_NO_PERSIST`.
- The 1.0.12 CLI has a hidden `--skip-tls` option, which I only saw in a click suggestion. **[UNVERIFIED semantics]**

### 1.6 Supported integrations at 1.0.12 (41 keys)
Source: the `INTEGRATION_REGISTRY` dumped from the 1.0.12 wheel, plus https://github.com/github/spec-kit/blob/main/docs/reference/integrations.md.
Compared with 0.16.2 (38 keys), 1.0.12 adds `docker-agent`, `dsh` (DeepSeek Harness) and `muse` (Muse Code).

| key | name | layout (dir, ext) | multi-install safe |
|---|---|---|---|
| agy | Antigravity | skills `.agents/skills` | no |
| alquimia | Alquimia AI | skills `.alquimia/skills` | yes |
| amp | Amp | cmds `.agents/commands/*.md` | no |
| auggie | Auggie CLI | cmds `.augment/commands` | yes |
| bob | IBM Bob | skills `.bob/skills` by default (`--legacy-commands` → `.bob/commands`) | no |
| **claude** | Claude Code | **skills `.claude/skills/speckit-<cmd>/SKILL.md`** | yes |
| cline | Cline (IDE) | cmds `.clinerules/workflows` | yes |
| codebuddy | CodeBuddy | cmds `.codebuddy/commands` | yes |
| **codex** | Codex CLI | **skills `.agents/skills/speckit-<cmd>/SKILL.md`** | yes |
| command-code | Command Code | skills `.commandcode/skills` | yes |
| copilot | GitHub Copilot | skills `.github/skills` by default; `--commands` → `.github/agents/*.agent.md` + prompts | no |
| cursor-agent | Cursor (IDE) | skills `.cursor/skills` | yes |
| devin | Devin for Terminal | skills `.devin/skills` | no |
| docker-agent | Docker Agent | skills `.agents/skills` | no |
| droid | Factory Droid | skills `.factory/skills` | yes |
| dsh | DeepSeek Harness | skills `.dsh/skills` | yes |
| firebender | Firebender (IDE) | cmds `.firebender/commands/*.mdc` | yes |
| forge | Forge | cmds `.forge/commands` | no |
| gemini | Gemini CLI | TOML `.gemini/commands/*.toml` | yes |
| generic | bring-your-own | cmds at `--commands-dir` (or `--skills`) | no |
| goose | Goose | YAML recipes `.goose/recipes` | no |
| grok | Grok Build | skills `.grok/skills` | yes |
| **hermes** | Hermes Agent | **skills written to GLOBAL `~/.hermes/skills/speckit-<cmd>/SKILL.md`**, plus an empty project marker `.hermes/skills/` | **no** |
| junie | Junie | cmds `.junie/commands` | yes |
| kilocode | Kilo Code (IDE) | cmds `.kilo/commands` | yes |
| kimi | Kimi Code | skills `.kimi-code/skills` | no |
| kiro-cli | Kiro CLI | cmds `.kiro/prompts` | yes |
| lingma | Lingma (IDE) | skills `.lingma/skills` | yes |
| muse | Muse Code | skills `.agents/skills` | no |
| **omp** | Oh My Pi | **slash commands `.omp/commands/speckit.<cmd>.md`** | yes |
| opencode | opencode | cmds `.opencode/commands` | yes |
| **pi** | Pi Coding Agent | **prompt templates `.pi/prompts/speckit.<cmd>.md`** (slash commands) | yes |
| qodercli | Qoder CLI | skills `.qoder/skills` | yes |
| qwen | Qwen Code | cmds `.qwen/commands` | yes |
| rovodev | RovoDev ACLI | skills `.rovodev/skills` | no |
| shai | SHAI | cmds `.shai/commands` | yes |
| tabnine | Tabnine CLI | TOML `.tabnine/agent/commands` | yes |
| trae | Trae (IDE) | skills `.trae/skills` | yes |
| vibe | Mistral Vibe | skills `.vibe/skills` | yes |
| zcode | ZCode | skills `.zcode/skills` | yes |
| zed | Zed (IDE) | skills `.agents/skills` | no |

**The five target harnesses (all supported in 0.16.2 and 1.0.12; their integration code is essentially unchanged between the two, which I confirmed by diffing):**

| harness | key | installs as | files | how you invoke it (from the observed `build_command_invocation`) | `--integration-options` |
|---|---|---|---|---|---|
| Claude Code | `claude` | **skills** (default, only mode) | `.claude/skills/speckit-*/SKILL.md` (argument-hint injected) | `/speckit-specify` | `--events` (hooks into `.claude/settings.json`) |
| Codex CLI | `codex` | **skills** (`--skills` defaults to True; commands are deprecated) | `.agents/skills/speckit-*/SKILL.md` | `$speckit-specify` | `--skills`, `--events` (`.codex/config.toml`) |
| Pi | `pi` | **slash commands** (Pi prompt templates) | `.pi/prompts/speckit.*.md` | `/speckit.specify` | none. Docs note `taskstoissues` needs MCP, which Pi lacks by default |
| oh-my-pi | `omp` | **slash commands** | `.omp/commands/speckit.*.md` | `/speckit.specify` | none |
| Hermes Agent | `hermes` | **skills, global** | `~/.hermes/skills/speckit-*/SKILL.md` (no project copies); uninstall removes the global `speckit-*` skills and the marker | `/speckit-specify` | `--skills` (default True) |

- Sources for the table: integration source in the 1.0.12 wheel (`specify_cli/integrations/{claude,codex,pi,omp,hermes}/__init__.py`), docs/reference/integrations.md, and the throwaway 1.0.12 project where I installed claude, codex, pi and omp and saw exactly the file layouts above.
- The Hermes docstring in spec-kit says Hermes has no project-local skills dir. Peer HermesPiOmpResearch says that is **out of date**: Hermes v0.21.4 does load `<root>/.hermes/skills` and `<root>/.agents/skills`, but only for trusted roots (`hermes skills trust`).
- Workflow and non-interactive dispatch argv that spec-kit builds (observed via `build_exec_args`):
  - claude: `claude -p PROMPT --output-format json`
  - codex: `codex exec PROMPT --json`
  - pi: `pi -p PROMPT --output-format json`
  - omp: `omp --print --mode json PROMPT`
  - hermes: `hermes chat -Q --json -q PROMPT`
  - The executable can be overridden with `SPECKIT_INTEGRATION_<KEY>_EXECUTABLE` (per the codex source comment).
- `specify check` in 0.16.2 on this machine reported these as available: Claude Code, Codex CLI, Gemini CLI, Hermes Agent, Oh My Pi, opencode, Pi Coding Agent, VS Code.

### 1.7 Running several integrations in one project
- Commands: `specify integration install <key>` (adds one; the default doesn't change), `use <key>` (changes the default, keeps the others), `switch <key>` (uninstall + install, or behaves like `use` if the target is already installed), `upgrade [<key>]`, `uninstall [<key>]`, `list [--catalog]`, `status [--json]`, `search`, `info`, `catalog list/add/remove`, `scaffold`. All of them need an initialized project (docs/reference/integrations.md).
- Install is automatic only when **every** involved integration is multi-install safe. Otherwise you get an error suggesting `switch`, or passing `--force` to proceed anyway. I watched this happen: `hermes` was refused next to claude/codex/pi/omp, and `--force` let it through. After that, `specify integration status` reports `Integration status: ERROR … error unsafe-multi-install … hermes` and exits 1.
- State lives in `.specify/integration.json`: `installed_integrations` (list), `default_integration`, `integration` (legacy alias of the default), `integration_settings.<key>.{script, invoke_separator}` (`-` for skills, `.` for commands), and `integration_state_schema: 1`. There is one manifest per integration, `.specify/integrations/<key>.manifest.json`, holding SHA-256 hashes used to detect modified files, plus `speckit.manifest.json` for shared infrastructure. Observed 1.0.12 state after installing claude+codex+pi+omp and then running `use omp`: `installed_integrations: [claude,codex,pi,omp(,hermes)]`, `default_integration: omp`.
- The shared templates and `init-options.json` (`ai`, `ai_skills`) follow the **default** integration only. Extensions and presets register only for the default integration; running `use` or `switch` re-scaffolds them for the new default.
- codex, agy, docker-agent, muse and zed all write to `.agents/skills`. Only codex is marked safe; the others are unsafe because they share that directory.
- Interaction to watch for **[INFERENCE]**: codex writes `.agents/skills/speckit-*`. The vercel `skills` CLI uses `.agents/skills` as its canonical store, and omp/Pi/Hermes also read `.agents/skills`. So installing spec-kit's codex integration would make the `speckit-*` skills visible to those harnesses as well.

### 1.8 `specify check`
`specify check` has no options. It lists every CLI-based integration as available or not found, and marks IDE-based ones "no CLI check". It is offline and ends with a tip to run `specify self check` (observed; docs/reference/core.md).

### 1.9 Workflows (`.specify/workflows`)
- `specify init` installs the bundled workflow `speckit` into `.specify/workflows/speckit/workflow.yml` and records it in `.specify/workflows/workflow-registry.json`.
  - The workflow runs specify → gate → plan → gate → tasks → implement.
  - `integration: "auto"` means it uses the project's default integration.
  - `requires.speckit_version: ">=0.8.5"`.
  - The docs show v1.0.1 at main; the local copy is 1.0.0.
- Commands: `specify workflow run <id|url|file.yml> [-i key=value…] [--json]`, `resume <run_id> [-i …] [--json]`, `status [<run_id>] [--json]`, `list`, `add <src> [--dev|--from url]`, `remove`, `update [id]`, `enable`, `disable`, `search`, `info`, `resolve`, `catalog …`, `step …`, `overlay …`.
- Run state is kept under `.specify/workflows/runs/<run_id>/` (`state.json`). Possible statuses: created, running, completed, paused, failed, aborted.
- Step types: command, prompt, shell, init, slot, gate, if, switch, while, do-while, fan-out, fan-in. Command steps dispatch to the integration's CLI in non-interactive mode (argv listed in §1.6) and can carry `integration_args`, `integration_options` and `model`.
- `shell` steps run with no sandbox.
- Example: `specify workflow run speckit -i spec="…"`.
- Source: https://github.com/github/spec-kit/blob/main/docs/reference/workflows.md

### 1.10 Canonical command sequence
From docs/reference/agentic-sdd.md:

`/speckit.constitution -> /speckit.specify -> /speckit.clarify -> /speckit.plan -> /speckit.checklist -> /speckit.tasks -> /speckit.analyze -> /speckit.implement -> /speckit.converge`

Plus `/speckit.taskstoissues`, which is optional and needs a GitHub `origin` remote and the GitHub MCP tools.

- Required: `constitution` (once per project), then per feature `specify → plan → tasks → implement → converge`. Repeat implement → converge until it reports "Converged".
- Optional quality gates: `clarify` (before plan; up to 5 questions per run), `checklist` (after plan), `analyze` (read-only, after tasks and before implement).
- `converge` is append-only: it only ever adds tasks to `tasks.md`.
- The 10 core commands are the same in 0.16.2 and 1.0.12: analyze, checklist, clarify, constitution, converge, implement, plan, specify, tasks, taskstoissues.
- Spelling depends on the agent: `/speckit.x` (command layouts such as omp and pi), `/speckit-x` (claude, hermes, and copilot skills), `$speckit-x` (codex, command-code, zcode), `/skill:speckit-x` (kimi).
- The README now also describes bundled opt-in processes: `specify extension add bug` (`/speckit-bug-assess|fix|test`) and `specify extension add assess` (intake/research/define/shape/decide) (https://github.com/github/spec-kit/blob/main/README.md).

---

## 2. Matt Pocock's grill-me (and grilling)

- **Canonical source:** https://github.com/mattpocock/skills, file `skills/productivity/grill-me/SKILL.md`. The docs page is `docs/productivity/grill-me.md`, which renders at https://www.aihero.dev/skills-grill-me.
  - Repo facts: MIT License, "Copyright (c) 2026 Matt Pocock" (https://github.com/mattpocock/skills/blob/main/LICENSE). The GitHub API reports the license as MIT.
  - The Claude plugin `plugin.json` also says `"license": "MIT"`, version 1.2.3.
- **grill-me's full SKILL.md:**
  ```
  ---
  name: grill-me
  description: A relentless interview to sharpen a plan or design.
  disable-model-invocation: true
  ---

  Call the Skill tool with "grilling".
  ```
  Its `agents/openai.yaml` sets `interface.display_name: "Grill Me"` and `policy.allow_implicit_invocation: false`. The locally installed copy is identical.
- **How it relates to `grilling`:** grill-me is a **user-invoked, one-line wrapper that delegates to the model-invoked `grilling` primitive**. `grilling` (`skills/productivity/grilling/SKILL.md`) holds the whole technique: design tree, rounds that ask the full "frontier", a ❓/➡️ question format with a recommended answer, facts found by sub-agents while decisions are left to the user, and a confirmation gate at the end.
  - The docs say plainly: "`grill-me` is a one-line skill whose whole body is 'run a `/grilling` session', so it needs this skill installed too" (https://github.com/mattpocock/skills/blob/main/docs/productivity/grilling.md).
  - `grilling` is also the primitive behind grill-with-docs (which additionally needs `domain-modeling`), triage, wayfinder and improve-codebase-architecture (README "Reference").
  - `batch-grill-me` was merged into `grilling` and no longer exists.
- **What the aihero page tells you to run** (install widget, pulled from the page HTML):
  - Single skill: `npx skills@latest add mattpocock/skills --skill=grill-me`, "Then type /grill-me in your coding agent."
  - Tab "Install the skills → All agents": `npx skills@latest add mattpocock/skills` ("Installs the whole set"). Update with `npx skills update`.
  - There is also a "Claude Code" tab, but its content isn't server-rendered. The repo's `.agents/install-block.md` defines the canonical Claude Code block as `claude plugins install mattpocock-skills` (or `/plugin install mattpocock-skills` in a session). It comes from Claude Code's official marketplace `claude-plugins-official` and auto-updates. The fallback, not documented to users, is `/plugin marketplace add mattpocock/skills` then `/plugin install mattpocock-skills@mattpocock`.
  - I did not render the Claude tab itself **[UNVERIFIED that the tab shows exactly this]**, but README §Installation says the same thing.
  - The canonical per-skill update is `npx skills@latest update <name>`.
- The README says the plugin and skills.sh routes are **exclusive**: "installing both leaves you with every skill twice." The plugin is a managed read-only bundle; skills.sh copies editable files.
- Warning from `.agents/install-block.md`: installing selectively with `--skill=grill-me` alone leaves grill-me broken, because the `grilling` primitive is missing. Install `--skill=grill-me --skill=grilling`, or the whole set.

---

## 3. vercel-labs `skills` CLI (skills.sh)

- **Package:** npm `skills` (https://www.npmjs.com/package/skills; registry https://registry.npmjs.org/skills).
  - dist-tags: latest **1.7.0**, published 2026-09-17. Snapshot tag: 1.5.23-snapshot.2.
  - bins: `skills` and `add-skill` (both point to `bin/cli.mjs`).
  - MIT. Repo https://github.com/vercel-labs/skills. Homepage/directory https://skills.sh.
  - Run with `npx skills <cmd>`; aihero and mattpocock pin `npx skills@latest`.
- **Commands (1.7.0 `--help` plus the dispatch source):**
  - `add <source>` (aliases `a`, `install`, `i`). Sources can be owner/repo, GitHub/GitLab/Azure/any git URL, a tree URL, a local path, or a direct `SKILL.md`/archive URL.
  - `use <source>@<skill>` generates a prompt without installing. With `--agent`, it launches claude-code, codex or sarvam-code.
  - `remove` / `rm` / `r [skills]`.
  - `list` / `ls` (`-g`, `-a`, `--json`).
  - `find [query]` (`--owner`).
  - `update [skills...]` (aliases **`upgrade`, `check`**; flags `-g`, `-p`, `-y`).
  - `init [name]`.
  - `experimental_install` restores from `skills-lock.json` into `.agents/skills/`.
  - `experimental_sync` syncs from node_modules.
  - In 1.7.0, **`check` is only an alias of `update`, so it modifies files.** The dist source has `case "check": case "update": case "upgrade": await runUpdate(...)`. Nothing in the CLI is a read-only "is an update available" command.
- **`add` flags:** `-g/--global`, `-a/--agent <agents…>` (`'*'` = all), `-s/--skill <names…>` (`'*'` = all), `-l/--list`, `-y/--yes`, `--copy`, `--all` (= `--skill '*' --agent '*' -y`), `--full-depth`, `--json`, `--metadata <json>`, `--subagent`.
- **Env vars:** `DISABLE_TELEMETRY` / `DO_NOT_TRACK` (telemetry is on by default), `GITHUB_TOKEN` / `GH_TOKEN`, `INSTALL_INTERNAL_SKILLS`, `SKILLS_DOWNLOAD_MAX_BYTES` and similar, `XDG_STATE_HOME`, `XDG_CONFIG_HOME`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `HERMES_HOME`.
- **Project vs global:**
  - Project (default) goes under `./<agent skillsDir>/`.
  - `-g` goes under the agent's global dir.
  - The canonical store is `./.agents/skills/<name>` for project installs and `~/.agents/skills/<name>` for global.
  - Code detail: with `-g`, "universal" agents (those whose project dir is `.agents/skills`, e.g. codex) are pointed at the canonical `~/.agents/skills`. The README table instead shows `~/.codex/skills` for Codex, so it may be stale. **[INFERENCE from `getAgentBaseDir`]**
- **Symlink vs copy (`installSkillForAgent`):**
  - The default mode is `symlink`. The skill is copied once into the canonical `.agents/skills/<name>`. Each non-universal agent then gets a symlink `<agentDir>/<name> → canonical`, which is what this repo shows. If creating the symlink fails, it falls back to copying.
  - `--copy` writes independent copies into each agent dir.
  - For project installs, a non-universal agent's symlink is **skipped when that agent's root dir (e.g. `.hermes/`) doesn't exist in the project**. Claude Code is the exception (`createProjectSkillsDirByDefault`).
  - Agents are auto-detected with `detectInstalled` (for example `~/.claude`, `~/.codex`, `~/.hermes`, `~/.pi/agent`).
- **Supported agents:** 79 entries in 1.7.0 (78 plus `universal`). The README says "OpenCode, Claude Code, Codex, Cursor and 75 more". The targets relevant here:

| harness | `--agent` | project dir | global dir |
|---|---|---|---|
| Claude Code | `claude-code` | `.claude/skills/` | `~/.claude/skills/` (`$CLAUDE_CONFIG_DIR`) |
| Codex | `codex` | `.agents/skills/` (universal) | README: `~/.codex/skills/` (`$CODEX_HOME`); see the code note above |
| Hermes Agent | `hermes-agent` | `.hermes/skills/` | `~/.hermes/skills/` (`$HERMES_HOME`) |
| Pi | `pi` | `.pi/skills/` | `~/.pi/agent/skills/` |
| oh-my-pi (omp) | **not listed** (no `omp`/`oh-my-pi` anywhere in the 1.7.0 source) | — | — |

  omp is still reached indirectly. Per https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md, omp's `agents` provider (`.agent[s]/skills`, "the canonical OMP-native location") and its `claude` provider load project skills by default, and it de-duplicates by realpath, which handles symlinks. Pi also reads `.agents/skills` and `~/.agents/skills` (https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md). Per peer HermesPiOmpResearch, Hermes loads project `.hermes/skills` and `.agents/skills` only for trusted roots.

  The rest of the agent keys (project dir), from the README table: aider-desk, amp/replit/universal (.agents), antigravity, antigravity-cli, astrbot, autohand-code, augment, bob, openclaw, cline/dexto/kimi-code-cli/loaf/sarvam-code/warp/zed (.agents), codearts-agent, codebuddy, codemaker, codestudio, command-code, continue, cortex, crush, cursor (.agents), deepagents, devin, droid (.agents), eve, firebender, forgecode, fx, gemini-cli (.agents), github-copilot (.agents), goose, grok, inference-sh, jazz, junie, iflow-cli, kilo, kimchi, kiro-cli, kode, lingma, mcpjam, minimax-code, mistral-vibe, moxby, mux, opencode (.agents), openhands, ona, posit-assistant, qoder, qoder-cn, qwen-code, reasonix, rovodev, roo, tabnine-cli, terramind, tinycloud, trae, trae-cn, windsurf, zcode, zencoder, zenflow, neovate, pochi, promptscript, adal. See https://github.com/vercel-labs/skills#supported-agents.

- **`skills-lock.json` (project lock, `version: 1`, written sorted by skill name)**:
  ```
  { "version": 1,
    "skills": { "<name>": { "source": "owner/repo|url|./rel/path",
                            "sourceUrl"?: "...", "ref"?: "...",
                            "sourceType": "github|gitlab|git|local|node_modules|well-known|...",
                            "skillPath"?: "skills/.../SKILL.md",
                            "computedHash": "<sha256>",
                            "subagents"?: [...] } } }
  ```
  - `computedHash` is a SHA-256 over the skill folder's files, sorted by relative path, hashing path then content, skipping `.git` and `node_modules` (`computeSkillFolderHash`). It is a hash of local content, not a git SHA.
  - A version lower than 1 or a malformed file is treated as empty.
- **Global lock:** `$XDG_STATE_HOME/skills/.skill-lock.json`, or `~/.agents/.skill-lock.json` otherwise. It is `version: 3`, with `skills.<name>.{source, sourceType, sourceUrl, skillPath, skillFolderHash, installedAt, updatedAt, …}`, `dismissed`, and `lastSelectedAgents`.
  - Project installs don't write skill entries here, but they do update `lastSelectedAgents`. This is what the local file shows.
- **Does the lock support update checks?**
  - **Global:** yes, a real diff. `updateGlobalSkills` fetches the GitHub repo tree and compares the skill folder's tree SHA with `skillFolderHash`. Only changed skills are re-installed. If the API fails it falls back to a git clone.
  - **Project:** **no diff.** `updateProjectSkills` reads `skills-lock.json`, skips `local` and `node_modules` entries, re-clones each source, handles deletions upstream (prompting, or skipping when non-interactive), and then **re-runs `skills add <source> --skill <name> -y` for every entry that has `skillPath`**. The output says "Refreshing N skill(s)…". Entries without `skillPath` get a manual reinstall hint.
  - The lock's `computedHash` *would* let a caller detect drift by hashing a fresh upstream checkout the same way. The CLI itself only uses `computedHash` for `experimental_sync` / install-from-lock "already up to date" checks. **[INFERENCE for the drift use]**
- **`skills ls --json`** (observed): an array of `{name, path, scope: "project"|"global", agents: [display names], source, sourceUrl, sourceType}`. In this repo it returns 38 project skills, each reporting agents Claude Code, Codex, Gemini CLI, GitHub Copilot, Hermes Agent, OpenCode, Pi.
- There is a `--json` for `add` too, which prints a result array.

---

## Key URLs
- https://github.com/github/spec-kit (README, CHANGELOG.md, docs/installation.md, docs/install/pypi.md, docs/upgrade.md, docs/reference/{core,integrations,workflows,agentic-sdd}.md)
- https://pypi.org/project/specify-cli/ · https://github.com/github/spec-kit/releases/tag/v1.0.12
- https://www.aihero.dev/skills-grill-me · https://github.com/mattpocock/skills (README.md, LICENSE, .agents/install-block.md, .agents/invocation.md, docs/productivity/{grill-me,grilling}.md, skills/productivity/{grill-me,grilling}/SKILL.md, .claude-plugin/{plugin,marketplace}.json)
- https://github.com/vercel-labs/skills · https://www.npmjs.com/package/skills · https://skills.sh
- https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md · https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/{skills,prompt-templates}.md
