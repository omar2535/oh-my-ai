# CLI Contract: `omai`

Global: `--config PATH`, `--version`. `--json` is per command (up, check, status, repos list, skills list). Exit codes: 0 ok, 1 failure (or updates available with `--exit-code`), 2 network/partial data, 3 invalid config.

| Command | Behaviour | Mutates |
|---|---|---|
| `omai` / `omai tui` | open TUI; background check if cache > TTL | via actions only |
| `omai up [--no-login] [--only ID...]` | converge: runtimes → installs (adopt existing) → config patches → skills → logins (serial, status-first); summary table | yes |
| `omai check [--json] [--exit-code] [--cached]` | installed/latest/channel/runtime warnings for harnesses, speckit, skills, omai | cache only |
| `omai status [--json]` | installs + auth status (probe commands), no network | cache only |
| `omai update [ID...\|--all] [--repos]` | native updaters; `skills` moves pins to upstream heads; `--repos` refreshes tracked repos; `omai update omai` self-update | yes |
| `omai uninstall ID [--purge] [--yes]` | remove program; `--purge` also deletes config dirs (confirmation unless `--yes`) | yes |
| `omai login [ID...\|--all] [--force]` | status-first serial native login; pi prints hint; `--force` skips status check (warns for codex revocation) | harness-owned |
| `omai install ID [--channel C]` | install one item, adopting an existing install | yes |
| `omai migrate ID --to CHANNEL` | install via new channel, verify, remove old | yes |
| `omai skills list\|add REPO@REF --skill N\|remove N\|sync` | manage sources + lock | yes (except list) |
| `omai init [PATH]` | speckit init + integrations claude,codex,pi,omp (default omp); track repo; print Hermes trust hint | repo |
| `omai repos list\|remove PATH` | tracked repos | state |

`check --json` shape:
```json
{"checked_at":"ISO8601","items":[{"id":"codex","kind":"harness","installed":"0.156.0","latest":"0.157.1","channel":"npm","update_available":true,"warnings":["runtime_bound:nvm"],"error":null}]}
```
