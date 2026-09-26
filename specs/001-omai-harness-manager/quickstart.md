# Quickstart / Validation

Prereqs: uv; repo checkout. Contracts: [cli](./contracts/cli.md), [config](./contracts/config.schema.md), [registry](./contracts/registry.schema.md).

## Hermetic (default)
```sh
uv sync && uv run pytest
```
Expected: all pass; covers up idempotency (2nd run 0 steps), check read-only (fake HOME tree hash unchanged), login status-first + serial (invocation log), credential canaries never opened, skills visible once per harness, uninstall keeps config.

## Local manual
```sh
uv tool install -e . && omai check        # 5 harnesses + speckit + skills + omai rows; codex/pi flagged runtime_bound:nvm
omai check --exit-code; echo $?           # 1 while codex/hermes/claude/speckit outdated
omai status                               # claude auth missing (expired), pi manual hint
omai up --no-login                        # adopts all, no reinstall; writes config, skills, hermes patches
omai up --no-login                        # "nothing to do"
omai login claude                         # native URL opens in Windows browser (WSL)
omai                                      # TUI renders instantly, check column fills in background
cd /tmp/scratch && git init && omai init  # specify integration status: claude, codex, pi, omp healthy; default omp
```

## Live smoke (opt-in)
`uv run pytest -m live` — real version probes and latest sources; verifies hermes/omp auth-status commands (research R1 items marked verify).
