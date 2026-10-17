# Security policy

## What matters here

The system runs locally inside Claude Code. There is no server, no account system and no network service exposed by this project. The sensitive material is yours: the API keys in `~/.claude/.polygon_key`, `~/.claude/.polygon_flatfiles.json` and `~/.claude/.financialdatasets_key`, and your own trade records. The allowlist `.gitignore` and the `--staged` mode of `scripts/uspicks_lint.py` exist to keep those out of git.

The agents fetch web pages, filings and news. Treat all of it as untrusted input.

## Reporting a vulnerability

If you find a way for the scripts or the command to leak a key, act on instructions embedded in fetched content, or write outside the expected locations, report it privately through the [security advisory form](https://github.com/Bader-Aloqily/claude-code-stock-picker/security/advisories/new). Please do not open a public issue with the details. The maintainer will reply as soon as possible. There is no bug bounty.

## Supported versions

Only the `main` branch is supported.
