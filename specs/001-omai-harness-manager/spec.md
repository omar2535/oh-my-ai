# Feature Specification: omai — Personal Coding-Agent Harness Manager

**Feature Branch**: `001-omai-harness-manager`

**Created**: 2026-09-26

**Status**: Draft

**Input**: User description: "A CLI/TUI that installs my coding agents (Claude Code, Codex, Hermes, pi, oh-my-pi) in one go, drives their logins, shows available updates, and bundles grill-me and spec-kit skills with a grill → spec-kit workflow." Full decision record: [grill.md](./grill.md).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One-shot machine setup (Priority: P1)

On a fresh or existing machine, the user runs a single command that brings every harness listed in their config to an installed state, adopting any already-installed harness rather than reinstalling it.

**Why this priority**: "Everything in one go" is the core promise.

**Independent Test**: In a sandboxed home with some harnesses present and others absent, run the setup command; all configured harnesses end installed, pre-existing ones untouched, and a second run changes nothing.

**Acceptance Scenarios**:

1. **Given** a config listing five harnesses and none installed, **When** the user runs setup, **Then** all five are installed user-locally without elevated privileges.
2. **Given** a harness already installed through some channel, **When** setup runs, **Then** it is recorded with its channel and not reinstalled.
3. **Given** one harness install fails, **When** setup runs, **Then** remaining steps still execute, a summary lists the failure, and the command exits non-zero.
4. **Given** a completed setup, **When** setup runs again, **Then** no steps execute and it exits zero.

---

### User Story 2 - Guided logins (Priority: P1)

After installs, the user is walked through signing each harness into the right account, using each harness's own login flow, with the login link or device code displayed and opened in their browser.

**Why this priority**: Removes manual per-harness configuration.

**Independent Test**: With fake harnesses reporting logged-out status, run the login step; each harness's native login is invoked once, one at a time, and status is verified afterwards.

**Acceptance Scenarios**:

1. **Given** a harness already logged in, **When** login runs, **Then** its login flow is not invoked (prevents revoking a valid session).
2. **Given** Claude Code logged out, **When** login runs, **Then** the native Claude login is launched and the user's subscription account is used.
3. **Given** Codex, omp and Hermes logged out, **When** login runs, **Then** each launches its native ChatGPT login sequentially, never concurrently.
4. **Given** pi logged out, **When** login runs, **Then** no login is launched and the user sees pi's status with the instruction to run pi and use its login command.
5. **Given** WSL2, **When** a login link is produced, **Then** it opens in the Windows host browser and is also printed.
6. **Given** Hermes is configured, **When** setup runs, **Then** Hermes is set to not borrow other harnesses' credentials.

---

### User Story 3 - See and apply updates (Priority: P1)

The user sees installed vs. latest version for each harness, spec-kit, skills and omai itself—both in the TUI on open and via a CLI check command—and can apply updates for one item or all.

**Why this priority**: Explicitly requested; keeps the toolchain current.

**Independent Test**: With fake version sources, the check command reports correct outdated items without modifying anything; the update command invokes each item's native updater.

**Acceptance Scenarios**:

1. **Given** the TUI opens, **When** cached results are older than 6 hours, **Then** a background check runs without blocking the interface.
2. **Given** `check` with machine-readable output requested, **Then** results are emitted as structured data; with exit-code mode, **Then** it exits non-zero if updates exist.
3. **Given** any check, **Then** no files, installs or skills are modified.
4. **Given** update for a harness, **Then** that harness's own update command is used.
5. **Given** update of omai itself, **Then** omai upgrades through its own install channel.
6. **Given** Claude Code, **Then** latest version is compared against the "latest" release channel.

---

### User Story 4 - Skills installed once, visible everywhere (Priority: P2)

grill-me, grilling, spec-kit and a bridge skill `grill-speckit` are installed from pinned upstream sources into one canonical location and made visible to every harness; the user can add extra skill sources.

**Why this priority**: Enables the grill → spec-kit workflow across harnesses.

**Independent Test**: In a sandboxed home, sync skills; each harness's skill discovery location resolves the same skill set, with no duplicates.

**Acceptance Scenarios**:

1. **Given** defaults, **When** skills sync, **Then** grill-me and grilling are always installed together.
2. **Given** a synced skill set, **Then** Claude Code, Codex, Hermes, pi and omp each see each skill exactly once.
3. **Given** an upstream source changed since pinning, **When** check runs, **Then** drift is reported without modifying skills.
4. **Given** the user adds or removes a skill source, **When** sync runs, **Then** installed skills match the config and lockfile.

---

### User Story 5 - Per-repo spec-kit setup and tracking (Priority: P2)

In a repository, the user runs an init command that sets up spec-kit for Claude Code, Codex, pi and omp (omp default). The repo is tracked so later spec-kit upgrades can refresh it.

**Why this priority**: spec-kit is per-project; the workflow needs it in each repo.

**Independent Test**: Run init in a scratch repo; spec-kit reports all four integrations healthy; the repo appears in the tracked list; a repo refresh upgrades their integrations.

**Acceptance Scenarios**:

1. **Given** a repo, **When** init runs, **Then** four integrations are installed, omp is default, and no Hermes integration is installed.
2. **Given** Hermes is used in the repo, **Then** the user is told to trust the repo in Hermes so it reads the shared project skills.
3. **Given** spec-kit was upgraded, **When** the user requests repo refresh, **Then** each tracked repo's integrations are upgraded; missing repos are reported and skipped.

---

### User Story 6 - Grill-to-spec workflow (Priority: P2)

The user invokes grill-me in any harness; at the end, the `grill-speckit` bridge saves the agreed decisions to `specs/<feature>/grill.md` and starts spec-kit's specify step with it, skipping clarify.

**Independent Test**: Invoke the bridge after a grilling session in a spec-kit repo; a grill record and a new spec exist in the same feature directory.

**Acceptance Scenarios**:

1. **Given** a finished grilling session the user confirmed, **When** the bridge runs, **Then** a decision record is written and the specify step is invoked with it.

---

### User Story 7 - Manage everything from the TUI (Priority: P3)

A dashboard shows each harness's installed/latest version, install channel, login status and skill status, with actions to install, update, log in (single or all), uninstall, manage skill sources, and manage tracked repos / init.

**Acceptance Scenarios**:

1. **Given** uninstall of a harness, **Then** the program is removed and its config/credentials kept unless purge is explicitly chosen.
2. **Given** a harness bound to a Node version manager or an outdated runtime, **Then** the dashboard warns and offers opt-in migration to the standalone installer.

### Edge Cases

- A harness command disappears because the active Node version changed → reported as "not found (runtime-bound)", not silently reinstalled.
- Login callback port already in use → logins stay serialized; conflict reported with the occupying process hint.
- Network unavailable during check → cached results shown with age; check exits with an error distinct from "updates available".
- Harness runtime too old (pi needs Node ≥22.19; Hermes expects a newer Python) → warning with remediation.
- Upstream skill source removed or renamed → reported as drift error; installed copy retained.
- Harness's own auto-updater changes version between check and display → next check reflects it; no conflict.
- A tracked repo was deleted or moved → skipped and flagged.
- Missing system prerequisite needing root → exact command printed; omai never escalates.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read desired state (harnesses, skill sources, account per harness) from a single user config file.
- **FR-002**: System MUST provide a converge command installing missing items and skipping satisfied ones, idempotently.
- **FR-003**: System MUST detect existing installs and their channel, and manage them through that channel.
- **FR-004**: System MUST offer opt-in migration of a harness to a different install channel.
- **FR-005**: System MUST install missing runtimes user-locally and MUST NOT use elevated privileges.
- **FR-006**: System MUST continue past per-item failures, summarize, and exit non-zero on any failure.
- **FR-007**: System MUST authenticate only via each harness's native login and MUST NOT read, copy or store harness credentials.
- **FR-008**: System MUST check auth status before login and skip login when already authenticated.
- **FR-009**: System MUST run logins one at a time.
- **FR-010**: System MUST display login URLs/codes and open them in the user's browser, including the Windows host browser under WSL2.
- **FR-011**: System MUST show pi auth status and manual-login hint without launching pi's login.
- **FR-012**: System MUST configure Hermes not to adopt other harnesses' credentials.
- **FR-013**: System MUST report installed vs. latest versions for all harnesses, spec-kit, skills and omai.
- **FR-014**: Check MUST be read-only and support structured output and an exit-code mode.
- **FR-015**: TUI MUST run update checks in the background on open using a 6-hour cache.
- **FR-016**: Update MUST use each item's native updater, for one item or all; omai MUST update itself.
- **FR-017**: System MUST NOT disable harnesses' native auto-updaters.
- **FR-018**: System MUST install default skills (grill-me, grilling, spec-kit, grill-speckit) from pinned upstream sources recorded in a lockfile, plus user-configured sources.
- **FR-019**: System MUST keep one canonical skill copy exposed to all five harnesses with no duplicate discovery.
- **FR-020**: System MUST provide per-repo init installing spec-kit integrations for Claude Code, Codex, pi and omp with omp default, excluding Hermes.
- **FR-021**: System MUST track initialized repos and refresh their spec-kit integrations on request.
- **FR-022**: System MUST ship the `grill-speckit` bridge skill writing `specs/<feature>/grill.md` and invoking specify.
- **FR-023**: TUI MUST provide dashboard, install/update/login (single/all), uninstall, skill-source management and tracked-repo management.
- **FR-024**: Uninstall MUST preserve harness config and credentials unless purge is requested.
- **FR-025**: Harnesses and skills MUST be defined as data entries so new ones require no core-logic change.
- **FR-026**: System MUST support Linux, WSL2 and macOS.
- **FR-027**: System MUST warn about harnesses bound to a version-managed runtime or requiring a newer runtime.

### Key Entities

- **Harness Definition**: name, install channels, version probe, latest-version source, update command, login command(s), auth-status probe, skill locations, runtime requirements.
- **Skill Source**: upstream location, pinned revision, content hash, selected skills.
- **User Config**: desired harnesses, account per harness, skill sources, options.
- **Machine State**: detected installs + channels, last check results + timestamp, tracked repos.
- **Tracked Repo**: path, installed integrations, spec-kit version at init.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a fresh machine, one bootstrap plus one converge command yields all five harnesses installed and prompts for every required login, with no other manual configuration.
- **SC-002**: A second converge run performs zero changes.
- **SC-003**: Update check results appear in the TUI without delaying first render; CLI check completes in under 10 seconds on a normal connection.
- **SC-004**: No test or run ever results in a harness credential being read or copied by omai.
- **SC-005**: Every skill is discoverable exactly once in each of the five harnesses.
- **SC-006**: Re-running login on already-authenticated harnesses never signs the user out.
- **SC-007**: Adding a sixth harness requires only a new registry entry and its tests.

## Assumptions

- Single user; no multi-user or team features.
- Harness setting management (models, permissions, MCP, global instructions) is out of scope for v1.
- GitHub Copilot is not configured in v1.
- Harness login commands and update commands remain as researched on 2026-09-26 (see grill.md research links).
- Network access is available for installs and checks; checks degrade to cached data offline.
- omai source is hosted at GitHub omar2535/oh-my-ai.
