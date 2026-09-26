# Data Model: omai

## HarnessDef (registry, read-only)
| Field | Type | Notes |
|---|---|---|
| id | str | `claude`, `codex`, `hermes`, `pi`, `omp`, `speckit`, `omai` |
| bin | str | executable name |
| channels | list[ChannelDef] | ordered; first = preferred for fresh install |
| version | {cmd, regex} | regex group 1 = version |
| latest | {kind: npm\|github\|pypi\|url_text\|url_json, ref, path?} | |
| update | list[str] \| null | argv |
| login | {mode: command\|manual\|none, argv?, hint?} | |
| auth_status | {argv, parse: exit_code\|json_path\|regex, expr?, timeout?} \| null | |
| config_get / config_set / config_patches | argv templates + list[{key, value}] | applied via the harness's own config command (hermes) |
| skills_dir | {kind: canonical\|symlink\|external_dirs\|none, path?} | |
| requires | list[{runtime, min}] | |

**ChannelDef**: `id` (native/npm/bun/brew/git/standalone/managed/binary/uv), `detect` (realpath globs), `markers` (paths whose existence identifies the channel), `locate` (globs used when the binary is off PATH), `install`/`uninstall` argv, `runtime_bound_if` (glob, e.g. nvm), `requires` (runtime minimums).

Validation: ids unique; regex compiles; `login.mode=command` ⇒ argv; every harness has ≥1 channel.

## Config (`~/.config/omai/config.toml`, user-owned)
| Field | Type | Default |
|---|---|---|
| harnesses.<id>.enabled | bool | true for 5 harnesses |
| harnesses.<id>.provider | str | claude→`anthropic`, codex→`openai`, omp/hermes/pi→`openai-codex` (pi login is manual per registry) |
| harnesses.<id>.channel | str? | unset = adopt/preferred |
| harnesses.claude.release_channel | `latest`\|`stable` | `latest` |
| skills.sources | list[{repo, ref, track, skills[]} or {bundled, skills[]}] | mattpocock/skills@<sha> [grill-me, grilling]; bundled grill-speckit |
| check.ttl_hours | int | 6 |

Validation: unknown harness id → error; grill-me selected ⇒ grilling auto-included.

## State (`~/.local/state/omai/state.json`, omai-owned)
- `installs.<id>`: {version, channel, path, runtime_bound: bool, detected_at}
- `checks`: {fetched_at, items.<id>: {latest, error?}}
- `auth.<id>`: {status: ok|missing|unknown|manual, checked_at}
- `repos`: list[{path, integrations[], default, speckit_version, added_at}]

## SkillsLock (`~/.config/omai/skills.lock.json`)
`{version:1, skills:{<name>:{source, ref, sha, hash, installed_at}}}`

## State transitions
Harness: `absent → installed(channel) → outdated ⇄ current`; `installed → absent` via uninstall (config dirs kept unless purge).
Auth: `unknown → missing → (login) → ok`; `ok` never re-logged by `up`; `manual` for pi.
Repo: `untracked → tracked(healthy) → stale(after speckit upgrade) → healthy (refresh)`; `missing` if path gone.
