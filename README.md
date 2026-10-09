# /us-picks — Weekly US Stock Pick System for Claude Code

> A Claude Code slash-command that picks **up to 5 mid-to-mega-cap US stocks** every Sunday, graded on **WEEKLY RANK (v6.3, 2026-09-01): where the pick's Monday-open → Friday-close return lands among the ~3,650-3,900 liquid US common stocks** — BIG WIN ≤ 100, WIN ≤ 500, FLAT 501-1500, LOSS beyond. **Chance baseline: ~13% top-500, ~2.6% top-100**, and every reported win rate is printed beside it and beside a seeded RANDOM-5 control drawn from the same eligible universe — so the system can never flatter itself with a high-base-rate metric (the retired +2% touch bar sat on a ~60-69% base rate; it is still reported, beside that base rate, because the author's own trailing exits monetize the intraweek peak). **The whole configuration is FROZEN under rule F1 until the 12th graded week**, with a pre-registered pass line (beat the random-5's top-500 rate by ≥ 8pp AND clear the ~13% chance baseline — else simplify to filters + random). Version **6.3** — self-amending through its own recorded Decision Review since 2026-09-13 (the Board of Advisors is retired).

This repo packages the system as a standalone Claude Code skill / agent / command bundle that you can fork, drop into `~/.claude/`, and run.

> ⚠️ **Not investment advice.** This is the author's personal research tool, shared as open source. It does not tell anyone what to buy; the author does not publish picks before the week or manage anyone's money. Past results do not predict future results. Use at your own risk.
>
> **Public release:** the author's own pick history, trade results and version history are not included — the tracker starts empty.

---

## Contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Install](#install)
- [Usage](#usage)
- [Forking & adapting](#forking--adapting)
- [Anatomy](#anatomy)
- [Version history](#version-history)
- [Cost](#cost)
- [Disclaimer](#disclaimer)
- [License](#license)

---

## What it does

Every Sunday, running `/us-picks` in Claude Code produces a slate of **0 to 5 US stocks** scored **≥ 70 / 100** on a 6-component conviction model. Each pick comes with:

- **Score breakdown (v6.3 — the restored v4.7/v4.8 matrix, 2026-09-01):** Volume Surge (16) + Price Momentum (11) + **Catalyst (40 — Sig 21 + Time 16 + Conf 3)** + Options Flow (18) + Risk/Liquidity (15 — Stop 7 + Liq 5 + Volatility-fit 3) = 100. **Big Money is informational** (native 0-10 shown as narrative, 0 points — its 5 went into Catalyst, as in v4.7); its `hard_reject` insider-selling flag is still a hard drop. The standalone Volatility component (0-21 under v5.7) is deleted — it maxed on 19 of 20 era picks
- **Last Close (price reference — NOT a graded endpoint):** prior trading day's after-hours (8 PM ET) close (normally Friday; holiday-aware), shown as `Last Close` next to the ATR context line. The **grade** is the intraweek PEAK vs Monday's 09:30 open
- **No modelled trade plan (v6.1):** entry timing and exits are left to the trader — the system prescribes no buy day, limit, stop, or exit. _(The retired 2026-07-28 Entry Plan's evidence — day-1 entry dominates, d1 open 42.65% → d4 close 25.8% on 181,444 ticker-weeks — is preserved in the spec for reference.)_
- **Catalyst narrative** (Tier 1–4 magnitude), **big-money flow** (insider / 13F / buyback — scored, and heavy insider-selling clusters are a **hard drop** again), **Sharia compliance status** (single-layer vice business-activity blacklist — Al Rajhi ratio screen removed 2026-07-08)

Picks are graded weekly via `/us-picks update` on **weekly rank** — where the Monday-open → Friday-close return lands in the liquid ranked universe — beside the seeded random-5 control (`uspicks_controls.py`), the runners-up bench, SPY, and the +2% touch next to its measured base rate:

| Weekly rank (Mon open → Fri close) | Grade |
|------------------------------------|-------|
| ≤ 100 | **BIG WIN** (also counts as a WIN) |
| ≤ 500 | **WIN** |
| 501-1500 | FLAT |
| > 1500, or unranked | LOSS |

Each pick's own close return is recorded and displayed as context; the rank is the grade. **Honest note:** the archived rank-era record (47 graded picks, v4.5→v5.3) was 15% WIN with the runners-up control at 20% — a top-500 rank bar is genuinely hard for $2B+ names, because the weekly extremes are dominated by microcaps this universe excludes (tracker blind spot BS-1).

If **0 candidates** clear the 70 / 100 conviction threshold, the week is skipped — quality over cadence.

**The system amends itself — through a recorded Decision Review (since 2026-09-13; the v5.9 Board of Advisors is retired).** Every grading run ends with a **Decision Review** (`/us-picks review` runs one on demand; `board` is a legacy alias): the orchestrator executes the due pre-committed checks and auto-reviews itself, then decides at most 3 changes under a fixed rule — **WIRED iff it affirmatively clears the pre-committed evidence bar (E1-E10), sits inside the remit, and touches no constitutional item**, with NOT WIRED as the default and a mandatory written counter-case. The bar is strict: ≥ 3 weeks AND ≥ 12 graded picks (or a 2006-2026 panel result with a held-out split) for any scoring/filter/selection change, direction replicated in ≥ 3 of the last 4 weeks, a stratified-within-week re-test, a named comparison arm, an argued reversal of any prior decision, auto-review terms, and cooling-off ≥ 4 graded weeks. Every decision is written into the tracker's **Decision Log** before any file is edited, then wired, linted, committed, and auto-reviewed later (a breached review makes the reversal a decision of its own). Four things are **constitutional** — the yardstick (objective, WIN tiers, grading window), Sharia, spending money, and the charter + the evidence bar itself — user-only; the system may only advise. While rule F1's freeze is live, reviews may only change logging/process. The user is informed by a SYSTEM DECISIONS card and is never asked. `/us-picks lesson "X"` remains the user's own wiring path. Honest limit: there is no independent panel any more — an earlier auto-learning loop wired rules on n=1 / n=0 and was disabled in v4.6, so the pre-committed bar, the record-first log and auto-review are the safeguards, and most reviews will honestly change nothing. _(2026-08-17 → 2026-09-13 a Board of Advisors — a Secretary, five Opus directors and a Chair voting under an APPROVED-iff-≥ 4/5 rule — held this role; its six sessions stay in the tracker as a historical ledger.)_

---

## How it works

Phase 2 (v5.1) runs **3 market-wide agents once (Stage A) plus the price scan directly via Bash (Step A4, 2026-06-22 — not a subagent), then fans the Stage-B roster out over EVERY eligible name** (no momentum pre-filter, no cap):

**Stage A** (3 agents + the direct price scan, no inter-dependency — run in parallel)
- `us-market-macro` — Fed posture, oil, geopolitics, risk regime
- `us-sentiment-scanner` — analyst ratings + Reddit / X / StockTwits flow
- `us-sector-momentum` — 11 sector ETF performance, rotation themes
- `scripts/uspicks_price_scan.py` — full ~5–7k common-stock universe scan (Polygon grouped-daily bulk), run **directly via Bash** since 2026-06-22 (parallel + resumable; **~10-20 min** — v5.6 enriches every cheap-filter survivor in the whole market again (~2-3k names), on top of the fixed universe/flat-file costs; `SCAN_VERSION = 'v6-wholemkt'`); `agents/us-price-analyzer.md` is retained as the scan's reference spec, no longer launched as a subagent

**Stage B** — fanned out over ALL eligible names (every hard filter, incl. the vice blacklist) via a batched workflow (v5.1; was: the ~20-30 momentum candidates)
- `us-catalyst-hunter` — earnings, 8-K filings, M&A, analyst upgrades, Capitol Trades / Truth Social signals; Tier 1–4 magnitude tagging
- `us-options-analyzer` — call/put flow, implied move, smart-money detection
- `us-bigmoney-analyzer` — Form 4 insider trades, 13F changes, buyback PRs (**informational only**, not scored under v4.7+; its `hard_reject` insider-selling flag is **advisory** since 2026-06-26 — a Heads-Up flag, no longer a hard filter)

> The `us-sharia-screen` agent (v4.7 Sharia Layer 2 — AAOIFI ratios) was retired in v4.8. A financial-ratio screen was briefly re-added as the **Al Rajhi screen** (v5.1, 2026-06-18) and then **removed again 2026-07-08 (user-directed)**. Sharia compliance is now the **single-layer business-activity vice blacklist** (`sharia-blacklist.md`, applied in Phase 3.5) — no ratio math, no separate agent.

Candidates flow through hard filters (**mkt_cap ≥ $2B — the whole-market mid-to-mega pick universe**, after-hours price ≥ $10, **Sharia vice blacklist** (business-activity, single-layer — financial-ratio screens such as interest/debt are not applied), RSI 25-90, avg daily $ volume ≥ $1M, and the Big Money `hard_reject` insider-selling veto); **every eligible name is then fully scored** (the Stage-B roster fans out over all of them — no momentum gate, no cap within the membership), then ranked by Total Conviction Score. Top names scoring ≥ 70 / 100 (up to 5, equal-weight allocation) become the week's slate. Grading (v5.6): each pick's **weekly rank in the full US market** decides the outcome (≤500 WIN / ≤100 BIG WIN / 501-1500 FLAT / >1500 LOSS); the pick's own close return is displayed as context. The bar is deliberately hard — read the win rate against the archived 15% (47 graded picks) rather than against zero.

---

## Install

### Prerequisites

- macOS or Linux
- [Claude Code](https://www.anthropic.com/claude-code)
- Python 3 + `pip` (for `boto3` + `pandas` + `pytz` — installed by `ensure-deps-us.sh`)
- A [Polygon.io](https://polygon.io/) plan that includes **stocks REST + flat files (S3)** — the universe scan, after-hours closes, options chains, the grading rank, plus news+sentiment, short-interest/-volume (FINRA), dividends, treasury yields, and the full-market snapshot all come from Polygon — and (optional paid add-ons) Benzinga Analyst Ratings + TMX Corporate Events for structured analyst actions and forward earnings dates
- (Optional) `pandoc` if you want to generate education PDFs via `/us-picks educate`

### Steps

1. **Clone the repo to a side directory** (do not clone directly into `~/.claude/` if you already use Claude Code — see [Forking & adapting](#forking--adapting)):

   ```bash
   git clone https://github.com/Bader-Aloqily/claude-code-stock-picker.git ~/us-picks-fork
   ```

2. **Install Python dependencies:**

   ```bash
   bash ~/us-picks-fork/scripts/ensure-deps-us.sh
   ```

3. **Create the API-key files** (chmod 600; the allowlist `.gitignore` keeps them out of git):

   ```bash
   echo "YOUR_POLYGON_REST_KEY"            > ~/.claude/.polygon_key
   cat > ~/.claude/.polygon_flatfiles.json <<'JSON'
   {"access_key_id": "...", "secret_access_key": "...",
    "endpoint": "https://files.polygon.io", "bucket": "flatfiles"}
   JSON
   chmod 600 ~/.claude/.polygon_key ~/.claude/.polygon_flatfiles.json
   ```

   Smoke-test the data layer: `python3 ~/.claude/scripts/uspicks_data.py` (prints ticker details, grouped-daily count, after-hours close, options chain, flat-file reads, ratings + earnings-date add-ons).

4. **Overlay the files into `~/.claude/`** — see [Forking & adapting](#forking--adapting) for what to copy and what to skip.

5. **Run on Sunday:**

   ```
   /us-picks
   ```

---

## Usage

| Command | Effect | When to run |
|---------|--------|-------------|
| `/us-picks` | Weekly pick cycle. Outputs up to 5 picks scored ≥ 70/100. | Sunday (any time) |
| `/us-picks update` | Grades the previous week's picks using the rank-based 4-tier criterion, then closes with a **Decision Review** whose SYSTEM DECISIONS card is the last output. | After Friday market close |
| `/us-picks review` | Runs the Decision Review on demand — evidence pack → due checks → decisions under the pre-committed bar; grades nothing; informs you of every decision. (`board` still works as a legacy alias.) | Any time you want a self-review cycle outside the weekly grading |
| `/us-picks lesson "X"` | Wires a lesson YOU dictate into the relevant agent / scoring / command files (your own path — it bypasses the Decision Review; you confirm it). | After grading, if you spot a pattern worth encoding |
| `/us-picks realized TICKER +X% success` | Records actual realized P&L outcome alongside the system rank-grade. | When you exit a position |
| `/us-picks educate` | Generates a Buffett-conversation-level PDF writeup explaining each pick. Output in `~/.claude/education/`. | Anytime after a pick run |

---

## Forking & adapting

This repo is a **personal research workflow made shareable**, not a plug-and-play product. To fork:

### Copy into your `~/.claude/`

- `commands/us-picks.md`
- `agents/us-*.md` (10 active + 1 disabled — disabled `us-momentum-screener.md` preserved for historical reference)
- `scripts/ensure-deps-us.sh` + `scripts/uspicks_*.py` (the Polygon/Financial-Datasets data layer: `uspicks_data.py` + 4 scan scripts the system can't run without, plus the standalone `uspicks_premarket_check.py` Monday gap check, the `uspicks_pdf.py` Arabic weekly-PDF renderer (Phase 7 / U.8, 2026-07-17), and the `uspicks_lint.py` consistency gate — see [Consistency gate](#consistency-gate))
- `skills/us-stocks-memory/**`

### Do NOT copy

- **`CLAUDE.md`** — intentionally **NOT included** in this repo (it's the author's private, global Claude Code config with cross-system rules). The general working rules that matter for `/us-picks` — the *Multi-File Changes Rule*, the *Pre-Plan Audit Checklist*, and the *Rigorous Self-Audit Discipline* — are worth adopting into your own global `CLAUDE.md`. The full `/us-picks` spec, invariant matrix, retired-invariants list, and Lesson-Wired Rules live in `skills/us-stocks-memory/references/us-picks-system-spec.md`, and its version history (every dated amendment block, split out 2026-09-13) in `skills/us-stocks-memory/references/us-picks-system-spec-history.md` (both of which you *do* copy, via `skills/us-stocks-memory/**` above).
- **`stocks/us-weekly-tracker.md`** — start your own tracker. Use the v4.4 archive and the v4.5 study as format references.
- **`projects/-Users-YOURNAME/memory/*`** — author's personal Claude memory (lessons / feedback). Yours will accumulate as you run the system.

### Customize

- **Sharia filter** — a single-layer business-activity vice blacklist `skills/us-stocks-memory/references/sharia-blacklist.md` (6 categories), applied in `commands/us-picks.md` Phase 3.5. The Al Rajhi debt/interest ratio screen (v5.1) was **removed 2026-07-08**. To disable Sharia screening entirely, empty `sharia-blacklist.md`; re-adding a financial-ratio screen is a structured change (the removed `uspicks_data.alrajhi_screen` code is in git history). No separate agent.
- **Scoring weights** — `skills/us-stocks-memory/references/scoring-model.md` is the rubric. Edit weights and **Phase 3.3** of the command file in sync. Run a strict pre-plan audit (re-read every file you changed; verify cross-references in both directions) before declaring multi-file changes done.
- **Universe & price floors** — `mkt_cap ≥ $2B` and `price ≥ $10` (restored by v6.1, 2026-08-29; it was $5 under v5.0-v6.0) are the HARD universe filters wired in Phase 3.5. **v5.6 (2026-07-28) removed the index-membership gate** that v5.3/v5.5 had added (S&P 500, then S&P 500 ∪ Nasdaq-100): a top-500-RANK objective and a large-cap membership cage cannot coexist, because only ~12 of each week's 100 biggest gainers are index members. `uspicks_data.sp500_members()` / `ndx_members()` still run each week and still fail loud internally, but the price scan catches that and continues — their output is now a per-row CONTEXT annotation (`sp500_member` / `ndx_member`) shown on the pick card. Loosen the remaining floors at your own risk; they were calibrated to the empirical loss pattern documented in `stocks/v45-research-top100-study.md`.

### Consistency gate

The system spans ~20 tightly-coupled markdown/Python files, and its documented failure mode is **drift** — one file updated while a sibling keeps the old fact. `scripts/uspicks_lint.py` (added 2026-07-02, stdlib-only, <1s) mechanically checks the files against a CONTRACT of the current state: rule active/deactivated markers, version labels, the scoring weights (5 components under v6.3, parsed from `scoring-model.md`'s Score Breakdown table), agent `model:` frontmatter, the price-scan runtime claim, and the tracker's arithmetic (graded-row census vs Summary Statistics vs the Sector/Catalyst breakdown tables).

```bash
python3 ~/.claude/scripts/uspicks_lint.py            # check the tree
python3 ~/.claude/scripts/uspicks_lint.py --staged   # + staged-path repo-scope check
```

Install it as a git pre-commit hook so an inconsistent state can't be committed (hooks aren't versioned by git — re-run this after any fresh clone):

```bash
printf '#!/bin/bash\nroot="$(git rev-parse --show-toplevel)"\nexec python3 "$root/scripts/uspicks_lint.py" --staged --root "$root"\n' > ~/.claude/.git/hooks/pre-commit
chmod +x ~/.claude/.git/hooks/pre-commit
```

If you change the system's state on purpose (wire/deactivate a rule, bump the version, change weights or models), update the CONTRACT at the top of `uspicks_lint.py` in the same edit — a lint failure after a legitimate change means the contract is stale, not that the change is wrong.

---

## Anatomy

```
~/.claude/
├── README.md                                  # this file
├── .gitignore                                 # allowlist — scope-locks the repo
├── commands/us-picks.md                       # main slash command (Phase 0 → 7 + U.1 → U.8)
├── agents/
│   ├── us-market-macro.md                     # Stage A: Fed, oil, risk regime
│   ├── us-sentiment-scanner.md                # Stage A: analyst + social
│   ├── us-sector-momentum.md                  # Stage A: 11 sector ETFs
│   ├── us-price-analyzer.md                   # scan reference spec (runs direct via Bash since 2026-06-22)
│   ├── us-catalyst-hunter.md                  # Stage B: catalyst Tier tagging
│   ├── us-options-analyzer.md                 # Stage B: options flow
│   ├── us-bigmoney-analyzer.md                # Stage B: insider / 13F / buyback (informational + advisory insider-sell flag)
│   ├── us-risk-assessor.md                    # post-pick: stop / liquidity (vol promoted to a scored component in v5.0)
│   ├── us-top-gainers-analyzer.md             # grading: full-universe rank
│   ├── us-performance-grader.md               # grading: pick-by-pick
│   └── us-momentum-screener.md                # DISABLED — preserved for historical reference
├── skills/us-stocks-memory/
│   ├── SKILL.md                               # surfaces tracker data to the slash command
│   └── references/
│       ├── scoring-model.md                   # the rubric (6 components, 100 pts)
│       ├── sharia-blacklist.md                # the whole /us-picks Sharia screen: vice blacklist, 6 cats (single-layer since 2026-07-08)
│       ├── flags-glossary.md                  # Heads-Up Flags taxonomy + plain-English map + render script
│       ├── report-design.md               # weekly Arabic PDF reports — output/payload contracts + fill rules (spec v7; design lives in uspicks_pdf.py)
│       ├── board-charter.md                   # Decision Charter (the Board retired 2026-09-13; file name kept) — remit / constitution / evidence bar / decision rule / Decision Log + card formats
│       ├── us-picks-system-spec.md            # current-state system spec — invariant matrix, retired invariants, Lesson-Wired Rules
│       └── us-picks-system-spec-history.md    # version history — placeholder (the author's history is not included)
├── scripts/
│   ├── ensure-deps-us.sh                      # pip install boto3 + pandas + pytz + fpdf2 + uharfbuzz (idempotent)
│   ├── uspicks_data.py                        # shared Polygon REST/S3 + Financial Datasets REST module (no MCP, no yfinance; FD fail-soft, cursor-paginated)
│   ├── uspicks_price_scan.py                  # Price Analyzer universe scan -> price-analyzer-output.json
│   ├── uspicks_gainers_scan.py                # grading rank scan -> gainers-output.json
│   ├── uspicks_options_scan.py                # options-chain metrics per ticker
│   ├── uspicks_grade.py                       # per-pick open-to-close grading prices
│   ├── uspicks_premarket_check.py             # standalone Monday pre-market gap check (live price vs entry)
│   ├── uspicks_pdf.py                         # Arabic weekly PDF renderer — Phase 7 picks / U.8 results / ad-hoc memos (2026-07-17)
│   ├── uspicks_board_pack.py                  # Decision Review evidence-pack builder — Phase U.9 (built for the v5.9 Board 2026-08-17; its --render mode is unused since 2026-09-13)
│   ├── uspicks_universe_snapshot.py           # rule L4 — Phase 6.0 Part A2 full-eligible-universe feature snapshot (Board-wired 2026-08-17)
│   ├── uspicks_run_audit.py                   # rule L5 — Phase 0.4 run & governance persistence audit, detection-only (Board-wired 2026-08-21)
│   ├── uspicks_archive_universe.py            # Phase U.2b per-week ranked-universe archive (Board-wired 2026-08-28)
│   └── uspicks_lint.py                        # consistency gate — drift linter + git pre-commit hook (2026-07-02)
└── stocks/
    ├── us-weekly-tracker.md                   # your pick history + summary stats + Decision Log (starts empty)
    ├── us-weekly-tracker-v4.4-archive.md      # placeholder (archive not included)
    └── v45-research-top100-study.md           # pattern study behind v4.5 weight rebalance
```

---

## Version history

The system went through about 25 versions between March and October 2026; the current version is **v6.3**. The dated history is the author's private record and is not part of this public release. The current state of every rule is documented in `skills/us-stocks-memory/references/us-picks-system-spec.md`.

---

## Cost

**What the author pays to run it, every month (October 2026): $1,095.99.**

| Service | What it does in the system | Monthly |
|---|---|---:|
| **Polygon** — Stocks Advanced, Options Advanced and Indices Advanced, plus the Benzinga Analyst Ratings and TMX Corporate Events add-ons | Prices, the weekly ranking of every US stock, options flow, index levels, analyst rating changes, earnings dates | $695.99 |
| **Financial Datasets** | Insider trades (Form 4) and SEC filings | $200 |
| **Claude** subscription | Runs Claude Code and its 10 agents | $200 |
| **Total** | | **$1,095.99** |

You don't need all of it to start: the two Polygon add-ons and Financial Datasets are optional, and the system falls back to free sources without them (details below).

Under the v4.9 data layer (2026-06-09) the cost structure changed — the per-request MCP table from v4.8 (~$10.60/week) no longer applies:

- **Polygon** — a flat monthly subscription (your plan must include stocks REST + flat-file/S3 access). The weekly scans are well within normal plan limits: ~31 grouped-daily calls + per-ticker enrichment of every cheap-filter survivor in the whole market (~2-3k names under v5.6, 2026-07-28; it was ~150-450 while the v5.3/v5.5 index gate was live, parallel + resumable — incl. tick-refining the after-hours close of every eligible name; ~10-20 min, the fixed universe/flat-file costs dominating) per pick run, two ~31 MB flat-file downloads per grading run.
- **Polygon partner add-ons (optional, 2026-06-14)** — Benzinga Analyst Ratings + TMX Corporate Events are **$99/mo each** (~$198/mo together). They upgrade the catalyst layer (structured analyst ratings + forward earnings dates), but are **not required** — the system runs on the base plan + free feeds. The author added both. Benzinga Earnings/Guidance/News, ETF Global, and European Consumer Spending were evaluated and skipped (Earnings is covered by TMX dates + WebSearch surprise coverage; the rest are out of scope for a US single-stock picker).
- **Financial Datasets — OPTIONAL (fail-soft).** The author cancelled it on 2026-08-14 and re-instated it on 2026-08-29; it feeds the Big Money agent's Form 4 input through `ud.insider_trades_best()` (the `hard_reject` HARD filter reads it) and, since the 2026-09-07 fix, returns the FULL 30-day filing window by walking the API's 10-row pages (1 probe + 1-10 requests per ticker; a typical $2B+ name is one page). Without a key the helpers degrade on their own to the free WebFetch sources (openinsider.com for Form 4; dataroma.com/whalewisdom.com for 13F) — the system still runs, with `bm_source` recording which rung served. Plan and price are the author's own subscription; a $20 / 1,000-request credit pack is the smallest entry point.
- **Claude Code** — your subscription / API costs (separate). The Decision Review adds no extra agents (the retired Board added roughly $10-30 per grading run on Opus).

---

## Disclaimer

**This system is not financial advice.** It is the author's personal research workflow. The score-based system may pick stocks that decline. Past performance — including the rank-based "win rate" tracked in `stocks/us-weekly-tracker.md` — is not indicative of future results.

The Sharia compliance filter is a **single-layer business-activity vice blacklist** (`sharia-blacklist.md`, 6 categories — defense, gambling, alcohol, tobacco/cannabis, adult, pork). The Al Rajhi debt/interest financial-ratio screen (added v5.1, 2026-06-18; data-fixed to v2-realint 2026-07-03) was **REMOVED 2026-07-08 (user-directed)** — so conventional financials (banks/insurers/lenders) and cash-rich names living off interest are **eligible again** (financial-ratio Sharia checks are left to the user). **It is not a certified Sharia advisory.** Verify any compliance claim independently with a qualified authority before acting on it.

The system makes **no guarantees** of profit, capital preservation, or accuracy. You are solely responsible for your investment decisions. Do your own research.

---

## License

Released under the [MIT License](LICENSE). You are free to use, copy, modify and share this code, including commercially, as long as the copyright notice stays with it. It is a personal research workflow, provided as-is with no warranty of any kind. Nothing in this repo is investment advice, and the author accepts no liability for trading decisions or losses.
