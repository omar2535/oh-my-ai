# Registry Contract (`src/omai/registry/harnesses.toml`)

Example entry (codex):

```toml
[codex]
bin = "codex"
version = { cmd = ["codex", "--version"], regex = 'codex-cli (\S+)' }
latest = { kind = "npm", ref = "@openai/codex" }
update = ["codex", "update"]
login = { mode = "command", argv = ["codex", "login"], revokes_existing = true }
auth_status = { argv = ["codex", "login", "status"], parse = "exit_code" }
skills_dir = { kind = "canonical" }
requires = []

[[codex.channels]]
id = "standalone"
detect = ["~/.codex/packages/standalone/*"]
install = ["sh", "-c", "curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_NON_INTERACTIVE=1 sh"]
uninstall = ["rm", "-f", "~/.local/bin/codex"]

[[codex.channels]]
id = "npm"
detect = ["*/node_modules/@openai/codex/*"]
locate = ["~/.nvm/versions/node/*/bin/codex"]
runtime_bound_if = ["~/.nvm/*"]
requires = [{ runtime = "node", min = "16" }]
install = ["npm", "i", "-g", "@openai/codex"]
uninstall = ["npm", "rm", "-g", "@openai/codex"]
```

Globs use `fnmatch` (`*` crosses `/`); the resolved realpath is matched first, then `markers`, then the PATH entry. Other entries: see `src/omai/registry/harnesses.toml` and [research.md R1](../research.md). pi: `login = { mode = "manual", hint = ... }`. hermes: `config_get`/`config_set` argv templates, `config_patches = [{ key = "auth.adopt_external_logins", value = "false" }]`, `skills_dir = { kind = "external_dirs", path = "~/.agents/skills", key = "skills.external_dirs" }`. claude: `skills_dir = { kind = "symlink", path = "~/.claude/skills" }`. Commands containing `sudo` are rejected.
Validation errors fail package tests (registry test loads every entry).
