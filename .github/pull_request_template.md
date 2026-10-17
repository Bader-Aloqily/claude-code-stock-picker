## What this changes

<!-- One or two sentences. Link the issue or discussion if there is one. -->

## Type of change

- [ ] Bug fix
- [ ] Data layer / scripts
- [ ] Tests / tooling / CI
- [ ] Docs
- [ ] Changes the system's state (a rule, version label, weight, filter, model, new agent or script)

## Checklist

- [ ] `python3 scripts/uspicks_lint.py --root .` passes
- [ ] If the system's state changed: the `CONTRACT` in `scripts/uspicks_lint.py` and the spec (`skills/us-stocks-memory/references/us-picks-system-spec.md`) are updated in this PR, and every sibling file that states the same fact says the same thing
- [ ] No API keys, credentials or personal files (`CLAUDE.md`, memories, my own tracker)
- [ ] Nothing here is, or reads as, investment advice
