# Config Contract (`~/.config/omai/config.toml`)

```toml
[harnesses.claude]
enabled = true
release_channel = "latest"   # latest | stable

[harnesses.codex]
enabled = true
provider = "openai-codex"

[harnesses.hermes]
enabled = true
provider = "openai-codex"

[harnesses.pi]
enabled = true
provider = "openai-codex"    # pi logs in only inside its TUI: run `pi`, then /login

[harnesses.omp]
enabled = true
provider = "openai-codex"

[[skills.sources]]
repo = "mattpocock/skills"
ref = "<pinned sha>"
track = "main"
skills = ["grill-me", "grilling"]

[[skills.sources]]
bundled = true
skills = ["grill-speckit"]

[harnesses.speckit]
enabled = true

[check]
ttl_hours = 6
```

Rules: missing file → `omai up` writes defaults above. Unknown keys → warning; unknown harness id → exit 3. `grill-me` implies `grilling`.
