# Contributing to Claude Code Stock Picker

Thanks for looking. This started as one person's research system and is now open source. Contributions are welcome, and this page explains how to make one that lands.

**Short version:** open an issue or a discussion first for anything bigger than a small fix, keep the ~20 coupled files consistent, run the linter, never commit a key, and don't post stock picks.

## Where help is wanted

Good first contributions. None of these need a Polygon plan or Claude Code to work on:

- **Tests.** There are none yet. A test suite for the pure-Python pieces (`scripts/uspicks_lint.py`, `uspicks_controls.py`, `uspicks_grade.py`, the filter logic in `uspicks_price_scan.py`) is the single most valuable thing missing.
- **A stats script for `results/`.** The numbers in [`results/README.md`](results/README.md) were computed by hand from the CSV. A small `results/stats.py` that recomputes them, and the chart, would keep them honest as the file grows.
- **Packaging and portability.** A `pyproject.toml` next to `requirements.txt`, Windows/WSL testing, a devcontainer or Dockerfile.
- **Data-layer robustness.** Retries, rate-limit handling and clearer error messages in `scripts/uspicks_data.py` and the scan scripts.
- **Documentation.** Anything in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) that is unclear, an English option for the weekly PDF report (it is Arabic today), screenshots of real output.

Bigger contributions, welcome after a discussion:

- **Alternative data providers** behind the same `uspicks_data.py` interface, with Polygon staying the reference implementation.
- **Other markets.** The scoring rubric and the governance (frozen configuration, random control, Decision Review) are market-agnostic; the data layer, the universe filters, the holiday calendar and the session times are US-specific. A port is a new data layer plus new filters, not a rewrite of the method.

## What needs evidence, not just a pull request

The scoring weights, the hard filters, the pick universe, the selection rule and the grading yardstick are **frozen under rule F1** until the system has 12 graded weeks on the current version. After that they change only through the Decision Review's pre-committed evidence bar: at least 3 weeks and 12 graded picks, or a multi-year panel with a held-out split, a named comparison arm, and more, all spelled out in `skills/us-stocks-memory/references/board-charter.md`. A pull request that changes any of them should arrive with that evidence, or start life as a discussion. Four items are the maintainer's alone: the yardstick, the Sharia screen, spending money, and the charter itself.

## Ground rules

1. **No credentials, ever.** API keys live in `~/.claude/.polygon_key` and its siblings, outside the repo. The `.gitignore` is an allowlist (a new file is ignored until its path is explicitly allowed), and `scripts/uspicks_lint.py --staged` refuses to let a credential file through.
2. **No personal files.** Your `CLAUDE.md`, your Claude memories and your own tracker stay local. `stocks/us-weekly-tracker.md` in the repo is the empty starter.
3. **No investment advice.** No "buy X" content and no picks in issues, discussions or pull requests. The project publishes a method and a record, not recommendations.
4. **Consistency over speed.** About 20 Markdown and Python files state the same facts: versions, rule states, weights, runtimes. If you change a fact in one file, change it in every sibling in the same pull request. The linter encodes the current state as a contract and fails on drift.

## Setting up

```bash
git clone https://github.com/<your-user>/claude-code-stock-picker.git
cd claude-code-stock-picker
bash scripts/ensure-deps-us.sh             # boto3, pandas, pytz, fpdf2, uharfbuzz (or: pip install -r requirements.txt)
python3 scripts/uspicks_lint.py --root .   # must print "all checks passed"
python3 -m unittest discover -s tests      # offline unit tests, no API keys needed
```

Install the linter as a pre-commit hook so an inconsistent state cannot be committed:

```bash
printf '#!/bin/bash\nroot="$(git rev-parse --show-toplevel)"\nexec python3 "$root/scripts/uspicks_lint.py" --staged --root "$root"\n' > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Running the actual pick cycle needs Claude Code and a Polygon.io plan (see the [README](README.md#quick-start)). Most of the contributions listed above need neither.

## Making a change

1. For anything beyond a small fix, open an issue or a discussion first so nobody duplicates work.
2. Fork, branch from `main`, and keep each pull request focused on one thing.
3. Run the linter. If it fails after a deliberate change to the system's state (a rule, a version label, a weight, a model, a new script), the contract is stale: update the `CONTRACT` section at the top of `scripts/uspicks_lint.py` and the spec in `skills/us-stocks-memory/references/us-picks-system-spec.md` in the same pull request. Never silence a check.
4. Fill in the pull request template. CI runs the linter on every pull request.
5. The maintainer reviews. Expect questions about cross-file consistency.

## Reporting bugs and security issues

Bugs go in [Issues](https://github.com/Bader-Aloqily/claude-code-stock-picker/issues) using the bug template. Strip API keys and account details from logs before pasting. For anything security-related, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## License

By contributing you agree that your contribution is licensed under the project's [MIT License](LICENSE).
