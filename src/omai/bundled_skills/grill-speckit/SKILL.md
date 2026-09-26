---
name: grill-speckit
description: After a grilling session reaches confirmed shared understanding, record the decisions and start spec-kit specification. Use when the user says "grill-speckit", "grill then spec", or confirms a grilling outcome in a spec-kit repo.
---

Preconditions: the repo contains `.specify/`; the user has confirmed the grilling outcome. If not a spec-kit repo, tell the user to run `omai init` and stop.

1. Pick a 2–4 word kebab-case feature short name.
2. Compose the decision record: every settled decision (one bullet each), out-of-scope items, open risks, and links to any research gathered.
3. Invoke the spec-kit specify command for the current harness (`/speckit.specify`, `/speckit-specify`, or `$speckit-specify`) with the decision record as the feature description.
4. After specify creates `specs/<NNN-short-name>/`, write the decision record to `specs/<NNN-short-name>/grill.md` and add a link to it in the spec's Input line.
5. Tell the user clarify is skipped and the next step is plan.
