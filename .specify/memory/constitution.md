<!--
Sync Impact Report
- Version change: template → 1.0.0
- Principles defined: I. Delegate, Never Hold Credentials; II. Adopt, Don't Fight; III. Declarative & Idempotent;
  IV. Data-Driven Registry; V. Hermetic Tests
- Added sections: Platform & Safety Constraints; Development Workflow
- Removed sections: none
- Deferred TODOs: none
-->
# oh-my-ai (omai) Constitution

## Core Principles

### I. Delegate, Never Hold Credentials

omai MUST authenticate harnesses only by invoking each harness's own login command and verifying
status afterward. omai MUST NOT read, copy, store, broker, or transmit OAuth tokens or credential
files belonging to any harness. API keys entered by the user MAY be written only to locations the
target harness documents. Login steps MUST check status first and MUST NOT re-run a login that would
revoke a valid session. Logins MUST run serially.

Rationale: Anthropic terms forbid third-party handling of claude.ai tokens; shared refresh tokens
break on rotation; `codex login` revokes existing credentials.

### II. Adopt, Don't Fight

Existing installs MUST be detected and adopted through their current install channel. omai MUST
update through each harness's native updater and MUST NOT disable native auto-updaters. Channel
migration happens only on explicit user request.

### III. Declarative & Idempotent

Desired state lives in one user config file. Every mutating operation MUST be safe to re-run and
MUST skip already-satisfied steps. Read-only commands (check, status) MUST NOT mutate anything.
Batch operations MUST continue past individual failures, report a summary, and exit non-zero on any
failure.

### IV. Data-Driven Registry

Harnesses and skills MUST be described as data entries (install, version, latest-source, update,
login, auth-status, skill dirs). Adding a harness MUST NOT require changes to core logic beyond a
new registry entry, except when a genuinely new capability kind is introduced.

### V. Hermetic Tests

Automated tests MUST run against a temporary HOME with fake harness executables and no network.
Live smoke tests MUST be opt-in and never part of the default suite.

## Platform & Safety Constraints

- Supported: Linux, WSL2, macOS. Native Windows is out of scope.
- omai MUST NOT invoke sudo; system-level prerequisites are reported with the exact command.
- Runtimes are installed user-local only.
- Implementation: Python ≥3.13, uv, Textual (TUI), Typer (CLI); distributed via
  `uv tool install git+https://github.com/omar2535/oh-my-ai`.

## Development Workflow

- Features flow grill-me → spec-kit (specify → plan → tasks → analyze → implement → converge).
- Every change touching the registry or login flow MUST include hermetic tests for status detection
  and idempotency.

## Governance

This constitution supersedes other practices. Amendments are made via `/speckit.constitution`,
recorded in the Sync Impact Report, and versioned semantically (MAJOR: principle removal/redefinition;
MINOR: new principle/section; PATCH: wording). Plans MUST include a constitution check.

**Version**: 1.0.0 | **Ratified**: 2026-09-26 | **Last Amended**: 2026-09-26
