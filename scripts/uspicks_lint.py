#!/usr/bin/env python3
"""uspicks_lint.py — mechanical consistency gate for the /us-picks system.

WHY THIS EXISTS (2026-07-02). The /us-picks system spans ~20 tightly-coupled
files, and its documented failure mode is DRIFT: one file gets updated while a
sibling keeps the old fact (a deactivated rule still described as active, a
stale version label, a scan 10x slower than its agent claims, tracker stats
that don't re-add). The prose disciplines in CLAUDE.md (Multi-File Changes
Rule, Rigorous Self-Audit) catch much of this but depend on the model applying
them perfectly every session — the 2026-07-02 tidy-up audit still found ~50
accumulated mismatches. This script makes the recurring drift CLASSES a
mechanical check instead: it encodes the system's current state as a CONTRACT
and fails loudly when any file on disk contradicts it. The git pre-commit hook
(.git/hooks/pre-commit) runs it with --staged, so an inconsistent system
cannot be committed/pushed.

THE UPDATE RULE (read this before "fixing" a lint failure). A failure means
ONE of two things:
  1. A file drifted from the system's real state  -> fix the FILE.
  2. The system's state legitimately changed (rule wired/deactivated, version
     bump, weight change, model policy, new agent/script) -> update the
     CONTRACT below IN THE SAME EDIT SET, exactly like the spec's
     invariant->files matrix (which this contract mirrors; the spec and its
     version-history file us-picks-system-spec-history.md stay the SSOT for
     history + rationale — this file only encodes CURRENT state).
Never silence a check without doing one of those two. Bypassing the hook with
--no-verify is banned by CLAUDE.md's hard rules.

WHAT IT CANNOT CATCH (honest limits): novel prose contradictions with no
encoded sentinel, wrong-but-internally-consistent claims, and drift classes
nobody has added a check for yet. When a new drift class is found in an audit,
add a check for it here — that is this file's version of /us-picks lesson.

Scope: in-repo files only (portable for forkers — no CLAUDE.md, no credential
files, no local-only memories). Stdlib only; runs in <1s.

Usage:
  python3 scripts/uspicks_lint.py             # content checks
  python3 scripts/uspicks_lint.py --staged    # + staged-file repo-scope check
  python3 scripts/uspicks_lint.py --root DIR  # lint a different tree (tests)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# =========================================================================
# CONTRACT — the machine-readable mirror of the spec's current state.
# Update in the SAME edit set as any system-state change (see header).
# =========================================================================

VERSION = "v6.3"

# Governance scope — v6.0 (2026-08-17, user-directed "whatever was written before
# saying do not re-add or do not edit etc. those were rules i added … you make the
# rules and adjust anything to better land the top 100 or 500"). The user released
# his OWN blanket prohibitions: the constitution shrank from 8 items to FOUR, the
# spec's retired-invariants list became the PRIOR DECISIONS REGISTER (argued
# reversal, not veto), Director 2's HARD BLOCK narrowed to constitution-only, and
# E1 gained Path B (2006-2026 panel + fit/validate split + cross-era replication).
# v6.0 changed NO scoring / filter / universe / WIN / rule-state VALUE — only who
# may change them, so WEIGHTS / GRADING_* / rule states below are untouched.
# Encoded because three opposite regressions must all be caught:
#   1. stale prose still listing 8 constitutional items, or still calling the
#      register "must STAY retired" as an absolute veto (under-permissive drift);
#   2. a file claiming the Board may change the YARDSTICK, SHARIA, SPENDING THE
#      USER'S MONEY, or THE CHARTER/BAR — the four items that did NOT move
#      (over-permissive drift, the dangerous direction);
#   3. E1 Path B being read as a blanket discount ("2 weeks is enough now")
#      rather than as a panel path with a held-out split.
CONSTITUTION_HEADING = "the FOUR things the orchestrator may NOT change"  # re-keyed 2026-09-13 (Board retired)
CONSTITUTION_HARD_BLOCK = "A constitution breach is never wired"  # 2026-09-13: no Director 2 any more
E1_PATH_B = "fit/validate split"
PRIOR_DECISIONS_REGISTER = "PRIOR DECISIONS REGISTER"

# Learning loop — 2026-09-13 governance amendment (user-directed "no need for board
# anymore. you decide ur self."). The v5.9 Board of Advisors (Secretary + 5 Opus
# directors + Chair, APPROVED iff >= 4/5 APPROVE and no HARD BLOCK) is RETIRED:
# Phase U.9 is the orchestrator's DECISION REVIEW, which decides <= 3 changes per
# review under the fixed DECISION_RULE below, records each in the tracker's
# Decision Log BEFORE any edit, and stays bound by the unchanged evidence bar,
# remit, four-item constitution and rule F1. Encoded because two opposite
# regressions must both be caught: (1) stale prose describing the Board as the
# CURRENT decider (check_board_retired_no_stale), and (2) any file describing a
# wiring that was not first recorded / did not clear the bar. The charter
# (board-charter.md, now the Decision Charter) is the SSOT; its rule is pinned.
DECISION_RULE = "WIRED iff it affirmatively clears the pre-committed evidence bar (E1-E10), sits inside the remit, and touches no constitutional item"

# Grading / measurement window — v5.8 (2026-08-07, user-directed "monday open
# till friday close"). The picks AND the whole-market ranked universe are both
# measured FIRST_TRADING_DAY 09:30 open -> LAST_TRADING_DAY 16:00 regular close.
# Encoded because the v4.9 after-hours window (prior-Fri 8 PM close -> Fri 8 PM
# close) is now a RETIRED INVARIANT: it credited every pick with a weekend gap
# and a Friday after-hours move that no order in the plan captures. Two specific
# regressions this guards against:
#   1. passing ENTRY_REF_DAY as the grading ENTRY_DATE — that silently re-grades
#      the retired window while every label still reads v5.8;
#   2. re-arming a `measurement_basis == afterhours` health check — under v5.8 a
#      regular-close source IS the basis, so that check postpones every week.
# The pick-time entry REFERENCE (Last Close = prior-day after-hours close, and
# the buy-limit / stop / $5 floor / Sell-Plan levels derived from it) is
# deliberately UNCHANGED and lives in ENTRY_LIMIT_FORMULA below — do not merge
# the two concepts.
GRADING_BASIS_TOKEN = "open_to_close"
# v6.1 (2026-08-29): the window is unchanged, but the GRADE inside it is the
# +2% intraweek PEAK TOUCH, not the close return and not the rank.
GRADING_WINDOW = "`FIRST_TRADING_DAY` 09:30 OPEN → `LAST_TRADING_DAY` 16:00 REGULAR CLOSE"

# Scoring matrix — STAYS v5.7 while the SYSTEM is v5.8: the 2026-08-07 window
# change touched no weight, band, threshold, filter, or WIN tier.
# v5.7 (2026-07-28): the v5.0 layout restored by v5.6, then
# re-weighted the same day per the archive component analysis — Catalyst 40->30
# (Sig 18 / Time 9 / Conf 3, cut Timing-hardest) + Volatility 11->21 (bands
# 4/11/21/15/10, sweet-spot peak 4-8% unchanged). Parsed from scoring-model.md's
# Score Breakdown table (the SSOT for weights).
WEIGHTS = {           # v6.3 (2026-09-01): the v4.7/v4.8 matrix restored, user-directed
    "Volume Surge": 16,
    "Price Momentum": 11,
    "Catalyst": 40,   # 35 -> 40: absorbed Big Money's 5, exactly as v4.7 did
    "Options Flow": 18,
    "Risk / Liquidity": 15,
    # Big Money is INFORMATIONAL under v6.3 (0 points) and must NOT appear as a
    # scored "0-N" row in the Score Breakdown table. Its `hard_reject` stays a
    # HARD Phase 3.5 filter - a separate switch, not encoded here.
}
WEIGHTS_TOTAL = 100

# Agent model policy (2026-07-08 cost re-architecture: run-once judgment agents
# on fable; Stage-B per-ticker batch workers [catalyst/options/bigmoney] on
# sonnet with a Fable finalist verify in Phase 3.55; relays on sonnet).
AGENT_MODELS = {
    "us-market-macro.md": "fable",
    "us-sentiment-scanner.md": "fable",
    "us-sector-momentum.md": "fable",
    "us-catalyst-hunter.md": "sonnet",
    "us-options-analyzer.md": "sonnet",
    "us-bigmoney-analyzer.md": "sonnet",
    "us-risk-assessor.md": "fable",
    "us-performance-grader.md": "fable",
    "us-price-analyzer.md": "sonnet",
    "us-top-gainers-analyzer.md": "sonnet",
    "us-momentum-screener.md": "sonnet",  # disabled agent, stays sonnet
}

# Entry Plan (2026-07-28) — the per-pick buy-limit formula. Encoded because the
# retired flat `× 1.01` limit is a RETIRED INVARIANT (it cost 2.7pp of win rate
# by leaving 6.1% of slots unfilled), and because the formula is stated in five
# files that must not drift apart. The literal appears verbatim in each.
ENTRY_LIMIT_FORMULA = "after_hours_close × (1 + atr_pct/100)"

# Price-scan runtime claim — the 2026-06-22 failure class (script slower than
# its runner agent's prose). Must appear in every file that states it.
# v5.6 (2026-07-28): the membership gate is gone, so enrichment covers every
# cheap-filter survivor in the whole market again (~2-3k names) on top of the
# fixed costs (31 grouped-daily calls + the ~31 MB AH flat file). The same
# whole-market shape measured ~11 min on a closed-market Sunday (2026-06-26, with
# MORE per-ticker calls than today); mid-market-hours latency pushes to the top of
# the envelope. Claim: ~10-20 min. (Was ~5-20 min under the v5.3/v5.5 index gate.)
PRICE_SCAN_RUNTIME = "~10-20 min"

# Rule L5 (Board-wired 2026-08-21, BP-2026-08-21-1). The era boundary the
# audit's condition (a) is scoped to; the archive-resolution glob; and the
# three condition ids. Drift here silently changes what the detector sees.
L5_ERA_START = "2026-07-14"

# Spec / version-history split (2026-09-13, user-directed repo housekeeping — no
# rule, scoring, filter, universe, yardstick or grade change; F1 not restarted).
# The spec holds CURRENT STATE only; every dated amendment block lives in the
# history file, prepended newest first. Encoded because the failure mode is
# silent re-growth: a session appending a block to the spec out of pre-split
# habit puts the ~225k-token history back into every run's mandatory read, and
# a truncated history file loses the SSOT changelog (check_spec_history_split).
SPEC_FILE = "skills/us-stocks-memory/references/us-picks-system-spec.md"
SPEC_HISTORY_FILE = "skills/us-stocks-memory/references/us-picks-system-spec-history.md"
# Public release: history files ship as placeholders carrying this marker; checks that
# need the author's history skip them. (The board-ledger session sentinels were dropped
# from the tracker list for the same reason.)
PUBLIC_STUB = "<!-- public-release-stub -->"
AMENDMENT_HEADING_RE = (
    r"^\*\*(v\d+\.\d+ amendment|v\d+\.\d+ sub-amendment|"
    r"\d{4}-\d{2}-\d{2} (amendment|maintenance amendment|agent-model amendment|Board session)|"
    r"v\d\.\d Best-Mix)")
HISTORY_MIN_BLOCKS = 61  # the blocks moved at the split; the history only grows

FILES = [
    "commands/us-picks.md",
    "skills/us-stocks-memory/SKILL.md",
    "skills/us-stocks-memory/references/scoring-model.md",
    "skills/us-stocks-memory/references/us-picks-system-spec.md",
    "skills/us-stocks-memory/references/us-picks-system-spec-history.md",  # version history, split out 2026-09-13
    "skills/us-stocks-memory/references/flags-glossary.md",
    "skills/us-stocks-memory/references/sharia-blacklist.md",
    "skills/us-stocks-memory/references/report-design.md",
    "skills/us-stocks-memory/references/board-charter.md",  # v5.9 Board SSOT
    "stocks/us-weekly-tracker.md",
    "stocks/us-weekly-tracker-v5.3-archive.md",
    "stocks/us-weekly-tracker-v4.4-archive.md",
    "stocks/us-weekly-tracker-v6.0-archive.md",
    "stocks/v45-research-top100-study.md",
    "README.md",
    ".gitignore",
    "scripts/ensure-deps-us.sh",
    "scripts/uspicks_data.py",
    "scripts/uspicks_price_scan.py",
    "scripts/uspicks_gainers_scan.py",
    "scripts/uspicks_options_scan.py",
    "scripts/uspicks_grade.py",
    "scripts/uspicks_premarket_check.py",
    "scripts/uspicks_pdf.py",
    "scripts/uspicks_lint.py",
    "scripts/uspicks_board_pack.py",  # v5.9 Board evidence-pack builder
    "scripts/uspicks_universe_snapshot.py",  # rule L4 (Board-wired 2026-08-17)
    "scripts/uspicks_controls.py",  # rule F1's CTRL machinery (v6.2, 2026-08-30)
    "scripts/uspicks_run_audit.py",  # rule L5 (Board-wired 2026-08-21)
] + ["agents/" + a for a in AGENT_MODELS]

# rule L1 `bm_source` — the CANONICAL seven-token enum string (BP-2026-09-04-1, Board-wired
# 2026-09-04, APPROVED 5-0). It must appear BYTE-IDENTICAL in every file that pins the enum,
# and every member of uspicks_board_pack.py's BM_SOURCE_ENUM must be in it — a STRUCTURAL
# check (check_bm_source_enum), because the previous six-token substring sentinel stayed
# green while a seventh token had been appended to the writer (the 2026-08-31 pack then
# coerced 19 licensed-feed rows, 4 of 5 picks, to `unmapped`).
BM_SOURCE_ENUM_CANON = (   # HISTORICAL — field REVERTED 2026-09-19, D-2026-09-19-1
    "`bm_source` one of: `section16_exempt` | `financialdatasets` | `openinsider` | "
    "`polygon_news_fallback` | `none` | `not_run` | `unmapped`")
BM_SOURCE_ENUM_RETIRED_SIX = (   # historical
    "`bm_source` one of: `openinsider` | `polygon_news_fallback` | `section16_exempt` | "
    "`none` | `not_run` | `unmapped`")
# per-week ranked-universe archive — the CANONICAL partition-rule sentence (BP-2026-09-04-2,
# Board-wired 2026-09-04, APPROVED 5-0). Pinned in the spec's archive invariant row (the home),
# quoted byte-identical by commands/us-picks.md Phase U.2b, SKILL.md and the pack reader. The
# sentence itself is pinned (Chair C16 / engineer 8) — a sentinel on the field name alone would
# pass even if the "MUST partition" clause were deleted.
ARCHIVE_PARTITION_RULE = (
    "PARTITION RULE (BP-2026-09-04-2): any retro-rank analysis that spans archived weeks of "
    "different `universe_basis` MUST partition on `universe_basis` AND `price_source`, OR report "
    "percentile-of-universe instead of raw rank, OR pool only with the basis mix stated in the "
    "artifact — and `unknown_legacy` is NOT comparable to `liquid_1m`; the percentile route is "
    "ANALYSIS-ONLY and may never compute, restate or substitute for a WIN tier, a published grade, "
    "or the F1 pass line.")
# `universe_basis` is a DERIVED partition key ONLY (Chair C5) — pinned in the command and the pack.
UNIVERSE_BASIS_SCOPE = "partition key ONLY — never an input to any rank, cutoff, grade, WIN tier, score or Summary Statistics row"

# Per-file sentinel strings that must be present VERBATIM. Each entry exists
# because its drift class actually happened once. Grouped by invariant.
MUST_CONTAIN = {
    "commands/us-picks.md": [
        # BP-2026-09-04-2: the partition-rule sentence quoted byte-identical + the scope line
        ARCHIVE_PARTITION_RULE,
        UNIVERSE_BASIS_SCOPE,
        "- **`universe_basis` (the GRADING-side era marker",
        "**`liq_floor_applied` must be `true` (NEW guard, 2026-09-04",
        # rule L1 `bm_source` provenance token (Board-wired 2026-08-22, BP-2026-08-22-2,
        # APPROVED 5-0). Scope guard (condition 14): the field is pinned to the L1 row
        # schema, the Big Money agent contract and uspicks_board_pack.py ONLY — it enters
        # no score, filter, threshold, pick card, PDF payload or grade. `edgar` stays out
        # of the enum until an EDGAR path is wired IN THE SAME EDIT SET (condition 17).
        # version label (stale-version class)
        "# US Weekly Stock Picker (v6.3)",
        # learning loop (v5.9 2026-08-17): the Board session phase must exist, the
        # user must be informed-not-asked, and the fixed decision rule pinned.
        "### U.9 Decision Review (the orchestrator decides",
        # D-2026-09-13-2: the Phase 0.3 market-status print
        "print('MARKET_TODAY=' + market_today)",
        "Nothing here needs an answer",
        DECISION_RULE,
        "- Starts with **\"review\"** (or the legacy alias **\"board\"**; 2026-09-13)",
        # grading window (v5.8 2026-08-07). The ENTRY_DATE sentinel is the one
        # that matters most: passing ENTRY_REF_DAY instead silently re-grades the
        # retired after-hours window while every label still says v5.8.
        "`ENTRY_DATE` = `FIRST_TRADING_DAY`, NOT `ENTRY_REF_DAY`",
        # L5 run & governance persistence audit (Board-wired 2026-08-21).
        # The Phase 0.4 step, the report-and-proceed U.1 gate, the NEW
        # U.9.2b ledger-before-wiring ordering, and the two DETECTION-ONLY
        # guarantees that keep the detector from ever driving a grade.
        "uspicks_run_audit.py --mode <pick|update|board>",
        "**U.9.4 — Record the decision in the Decision Log FIRST, then wire.**",
        "If L5 fired, REPORT and PROCEED",
        "never passed as `WEEK_OVERRIDE` / `ENTRY_DATE` / `EXIT_DATE`",
        GRADING_WINDOW,
        GRADING_BASIS_TOKEN,
        # pick universe (v5.6 2026-07-28 — whole mid-to-mega market; the v5.3/v5.5
        # index-membership gate was REMOVED with the return to the rank objective.
        # These two sentinels pin the CONTEXT-ONLY role of the membership lists, so a
        # future edit can't silently re-gate picking (or silently drop the annotation).
        "under the whole-market universe",
        "CONTEXT ONLY",
        # scoring summary (weights-drift class)
        "Volume Surge **16** + Price Momentum **11** + **Catalyst 40** (Significance 21 / Timing 16 / Confirmation 3)",
        # WIN taxonomy (v5.6 rank-based 4-tier class — FLAT is live again)
        "BIG WIN <=100 | WIN <=500 | FLAT 501-1500 | LOSS >1500",
        # rule state (deactivated-rule-still-active class — B1 deactivated in full v6.1 2026-08-29;
        # B2/F3 2026-07-02; L1 added 2026-07-11)
        "Active modifiers applied in THIS phase: NONE.",
        "Do NOT apply B1, B2 or F3 — all three are deactivated.",
        "The active rules under v6.3 are **F1 (12-Week Freeze)",
        "~~B1 (Risk-On Aggression Tilt)~~ **DEACTIVATED IN FULL 2026-08-29",
        "L2 (Options Weight Re-evaluation Reminder)** — wired 2026-07-14, re-keyed to the v6.3 grade 2026-09-01",
        # L3 reminder (wired 2026-08-08) — counter + the load-bearing loud-banner frame
        # BP-2026-08-28-1: L3 delivered 2026-08-28, its banner retired; the pick band is S[6..10].
        "TOP 5 BY SCORE IS RESTORED",
        "\"sel_rule\": \"top5\"",
        # D-2026-09-26-1: the CK1 provisional-row stamp carries the live selection era
        # (it read "S6-10" from the 2026-08-28 wiring until 2026-09-26).
        "\"stage\": \"post-filter-pre-verify\", \"sel_rule\": \"top5\"})",
        # D-2026-09-26-3: L2's pre-committed re-arm is mechanical (status `RE-ARMED — gate N`).
        "**Re-arm — the rule's own negative branch, made mechanical 2026-09-26",
        "### 3.3.9 CK1 — Provisional Candidate-Score Checkpoint",
        "**Part A3 — CK1 supersede-and-clear",
        "**U.2b — ARCHIVE THE WEEK'S RANKED UNIVERSE",
        "\U0001F7E5\U0001F7E5\U0001F7E5",
        # L1 candidate-score log (wired 2026-07-11 — Phase 6.0 must exist)
        "### 6.0 Persist Candidate Score Log (L1",
        # L4 universe snapshot (Board-wired 2026-08-17 — Part A2 + the RUN_START_UTC provenance stamp)
        "**Part A2 — L4 full-eligible-universe feature snapshot (Board-wired 2026-08-17",
        "print('RUN_START_UTC=' + datetime.utcnow()",
        # threshold
        "70/100",
        # Sharia single-layer pin (Al Rajhi financial screen removed 2026-07-08)
        "business-activity blacklist (single-layer",
        # Trade plan retired (v6.1, 2026-08-29) — the system prescribes no entry/stop/exit
        "### 5.1 Compute Reference Values (v6.1",
        "Entry & exit: YOURS",
        # v6.2 (2026-08-30, user-directed "GO"): controls + freeze + money scoreboard
        "### U.3a Controls, SPY & Base Rates (v6.3",
        "uspicks_controls.py draw --week-start",
        "STAY ON SCRIPT",
        "RULE F1 (v6.2, 2026-08-30, user-directed)",
        # frontmatter tools (missing-Workflow class, fixed 2026-07-02)
        "  - Workflow",
        "  - Agent",
    ],
    "skills/us-stocks-memory/SKILL.md": [
        ARCHIVE_PARTITION_RULE,  # BP-2026-09-04-2 (quoted)
        "Big Money is INFORMATIONAL under v6.3 (2026-09-01)",  # v6.3 drift repaired 2026-09-04
        "(v6.3, 2026-09-01; governance 2026-09-13) grades on **WEEKLY RANK**",  # re-keyed 2026-09-14
        "# US Stocks Memory Skill (v6.3",
        "### 5. Learning Loop Awareness (2026-09-13",
        DECISION_RULE,
        GRADING_WINDOW,
        "the whole mid-to-mega market (v5.6, 2026-07-28)",
        "(0 active — B1 + F3 + B2 ALL DEACTIVATED)",
        "## Scoring Model Reference (v6.3 — the restored v4.7/v4.8 matrix",
        # v6.3: Big Money is informational - the SKILL digest must say so and
        # must NOT carry a numeric points cell for it.
        "| Big Money | — (INFORMATIONAL",
        "~~B1 (Risk-On Aggression Tilt)~~ **DEACTIVATED IN FULL 2026-08-29",
        "~~B2 (Risk-Off Regime Dock)~~ **DEACTIVATED 2026-07-02",
        "~~F3 (Catalyst Freshness)~~ **DEACTIVATED 2026-06-27",
        "L1 (Candidate Score Audit Trail + 2-Run Analysis Reminder) — ACTIVE, wired 2026-07-11",
        "THE PICK BAND IS THE TOP 5 BY SCORE AGAIN (v6.1, 2026-08-29)",
        "L4 (Full-Eligible-Universe Feature Snapshot) — ACTIVE, Board-wired 2026-08-17",
        "L5 (Run & Governance Persistence Audit) — ACTIVE, Board-wired 2026-08-21",
        "~~Entry Plan~~ — RETIRED as an instruction by v6.1",
        PRICE_SCAN_RUNTIME,
        "uspicks_lint",
    ],
    "skills/us-stocks-memory/references/scoring-model.md": [
        "RESTORED 2026-07-28 (v5.6, user-directed)",
        "## 7. Post-Score Modifiers (Lesson-Wired Rules) — F1 + L1 + L2 + L3 + L4 + L5 + CK1 ACTIVE (v6.2 — NO scoring rule; F1 = the 12-Week Freeze governing this whole file); B1 DEACTIVATED IN FULL 2026-08-29",
        # L4 universe snapshot (Board-wired 2026-08-17)
        "### L4 (ACTIVE, Board-wired 2026-08-17): Full-Eligible-Universe Feature Snapshot",
        "### L5 (ACTIVE, Board-wired 2026-08-21): Run & Governance Persistence Audit",
        # L3 selection-rule re-test reminder (wired 2026-08-08)
        "### L3 (ACTIVE, wired 2026-08-08): Selection-Rule Re-Test Reminder",
        "### L2 (ACTIVE, wired 2026-07-14; winners re-keyed to the v6.3 RANK bar 2026-09-01): Options Weight Re-evaluation Reminder",  # D-2026-09-13-1
        "### B1 (⛔ DEACTIVATED IN FULL 2026-08-29, v6.1 — was ACTIVE 2026-06-08 → 2026-08-29, RESTRUCTURED v5.0): Risk-On Aggression Tilt",
        "### L1 (ACTIVE, wired 2026-07-11): Candidate Score Audit Trail",
        "### B2 (⛔ DEACTIVATED 2026-07-02): Risk-Off Regime Dock",
        "### F3 (⛔ DEACTIVATED 2026-06-27): Catalyst Freshness Penalty",
        "| Price Momentum | 0-11 |",
        ENTRY_LIMIT_FORMULA,
        "70/100",
    ],
    "skills/us-stocks-memory/references/us-picks-system-spec.md": [
        ARCHIVE_PARTITION_RULE,  # BP-2026-09-04-2 — the canonical HOME of the sentence
        "## US Stock Picks System (v6.3",
        "**Learning loop principle (2026-09-13",
        # governance scope (v6.0 2026-08-17): the register rename + its HARD tier.
        # The `[HARD — §3]` marks are what stop a future session from "arguing a
        # reversal" of the process-integrity guards that keep the Board auditable.
        PRIOR_DECISIONS_REGISTER,
        "`[HARD — §3]`",
        "board-charter.md",
        GRADING_WINDOW,
        GRADING_BASIS_TOKEN,
        "FIVE active rules — B1",
        "ACTIVE (Board-wired 2026-08-17): L4 (Full-Eligible-Universe Feature Snapshot)",
        "ACTIVE (Board-wired 2026-08-21): L5 (Run & Governance Persistence Audit)",
        "✅ DELIVERED 2026-08-28 — L3 (Selection-Rule Re-Test Reminder, 6-run); the banner is RETIRED",
        # BP-2026-08-28-1: the pick band and its schema markers
        "**ACTIVE (Board-wired 2026-08-28): CK1 (Provisional Candidate-Score Checkpoint)",
        "ACTIVE (wired 2026-07-11): L1 (Candidate Score Audit Trail",
        "ACTIVE (wired 2026-07-14; winner definition re-keyed to the v6.3 RANK bar",
        "⛔ DEACTIVATED IN FULL 2026-08-29 (v6.1, user-directed): B1 (Risk-On Aggression Tilt)",
        "⛔ DEACTIVATED 2026-07-02 (user-directed): B2 (Risk-Off Regime Dock)",
        "⛔ DEACTIVATED 2026-06-27 (user-directed): F3 (Catalyst Freshness Penalty)",
        "Volume Surge 16 + Price Momentum 11 + Catalyst 40 + Options Flow 18 + Risk/Liquidity 15 = 100",
        ENTRY_LIMIT_FORMULA,
        # WIN taxonomy (v6.3 2026-09-01 — rank 4-tier, restored)
        "**BIG WIN** = weekly rank ≤ **100**",
        "**WIN** = policy return > `SPY_WEEK`",
        "ACTIVE (wired 2026-08-30, user-directed \"GO\"): F1 (12-Week Freeze)",
        "**LOSS** = policy return ≤ `SPY_WEEK`",
        PRICE_SCAN_RUNTIME,
        # inventory completeness (missing-from-file-list class, 2026-06-26)
        "uspicks_lint.py",
    ],
    SPEC_HISTORY_FILE: [
        # re-pointed from the spec's list at the 2026-09-13 split — both amendment
        # blocks moved into the history file byte-for-byte
        "**2026-09-04 amendment (DATA-INTEGRITY FIX",
        "**2026-09-13 amendment (GOVERNANCE",
    ],
    "stocks/us-weekly-tracker.md": [
        # BP-2026-09-04-1: the enum-completion entry + the FD-live correction (C9 — the stale
        # "tokens are absent (cancelled 2026-08-14)" clause is hunted by check_bm_source_enum)
        "- **Enum completion (Board-wired 2026-09-04 — BP-2026-09-04-1",
        "re-instated by the user on 2026-08-29",
        "The week-12 review MUST state the `universe_basis` mix",
        "# US Stock Picker — Performance Tracker (v6.3)",
        "## Board of Advisors — Decision Ledger (v5.9)",  # kept as the HISTORICAL ledger
        "## Decision Log (orchestrator",
        "**B1: Risk-On Aggression Tilt — ⛔ DEACTIVATED IN FULL 2026-08-29",
        "**F1: 12-Week Freeze — ACTIVE (wired 2026-08-30",
        "## Improvement Backlog (week-12 gate",
        "**L1: Candidate Score Audit Trail + 2-Run Analysis Reminder — ACTIVE (wired 2026-07-11",
        "**L2: Options Weight Re-evaluation Reminder — ACTIVE (wired 2026-07-14",
        "**L3: Selection-Rule Re-Test Reminder (6-Run) — ACTIVE (wired 2026-08-08",
        "**L4: Full-Eligible-Universe Feature Snapshot — ACTIVE (Board-wired 2026-08-17",
        "**L5: Run & Governance Persistence Audit — ACTIVE (Board-wired 2026-08-21",
        # rule L1 `bm_source` (Board-wired 2026-08-22, BP-2026-08-22-2) — condition 15 pins the
        # enum inside the rule that DEFINES it, so it cannot drift from commands/us-picks.md.
        "**B2: Risk-Off Regime Dock — ⛔ DEACTIVATED 2026-07-02",
        "**F3: Catalyst Freshness Penalty — ⛔ DEACTIVATED 2026-06-27",
    ],
    "agents/us-bigmoney-analyzer.md": [
        # BP-2026-09-04-1: the emitted-JSON contract carries the licensed-feed token and the
        # agent no longer tells itself FD is dead (C9 / engineer 2)
        "re-instated by the user on 2026-08-29",
        # the emitted-JSON contract must carry the token (BP-2026-08-22-2)
    ],
    "scripts/uspicks_pdf.py": [
        # 2026-09-13 drift fix: the weekly PDF's fixed footer + picks kicker
        # must state the live v6.3 RANK yardstick (charter §3.1) — the v6.2
        # money-bar wording survived the v6.3 restore there for two weeks.
        "النجاح يعني أن يحلّ السهم ضمن أفضل 500 سهم ارتفاعاً",
        "الهدف: دخول قائمة أفضل 500 سهم ارتفاعاً هذا الأسبوع",
    ],
    "scripts/uspicks_board_pack.py": [
        # BP-2026-09-04-1 + -2 readers
        "bm_source_unknown_tokens",
        "insider_licensed_ok_pct",
        "insider_source_ok_nd",
        "insider_licensed_ok_pct_by_log_scope",
        "universe_basis",
        "basis_label_conflict",
        "basis_counts",
        "mixed_basis",
        "basis_faults_LOUD",
        ARCHIVE_PARTITION_RULE,
        # the NAMED READER the 2026-08-21 deferral required (BP-2026-08-22-2)
        "bm_source_counts",
        "insider_source_ok_pct",
    ],
    "scripts/uspicks_archive_universe.py": [
        # 2026-09-04 data-integrity fix + BP-2026-09-04-2 writer stamp
        "MIN_UNIVERSE = 3000",
        "def _liq_floor_ok(d):",
        "def derive_universe_basis(d):",
        '"liq_floor": d.get("liq_floor")',
        '"universe_basis": derive_universe_basis(d)',
    ],
    "scripts/uspicks_gainers_scan.py": [
        "'liq_floor_applied': liq_floor_applied",
        "liquidity floor: applied from",
    ],
    "agents/us-top-gainers-analyzer.md": [
        "`liq_floor_applied` MUST be `true`",
    ],
    "agents/us-market-macro.md": [
        "display/advisory only since B2's deactivation 2026-07-02",
    ],
    "agents/us-catalyst-hunter.md": [
        "F3 DEACTIVATED 2026-06-27, B2 DEACTIVATED 2026-07-02",
    ],
    "agents/us-risk-assessor.md": [
        "Volatility fit | 3",  # v6.1: the R/L VolFit sub-score is back (0-15 total); the Entry-Plan formula pin retired with the trade plan
        "**Total XX/15**",
    ],
    "agents/us-price-analyzer.md": [
        PRICE_SCAN_RUNTIME,
    ],
    "README.md": [
        "Version **6.3**",
        "board-charter.md",
        "No modelled trade plan (v6.1)",
        "the whole-market mid-to-mega pick universe",
        PRICE_SCAN_RUNTIME,
        "uspicks_lint",
    ],
    "scripts/uspicks_price_scan.py": [
        "SCAN_VERSION = 'v7-v46restore'",  # eligibility = $2B + $10, RSI 25-90, no atr floor (v6.1 2026-08-29)
    ],
    "scripts/uspicks_data.py": [
        "def sp500_members",  # kept as a CONTEXT annotation under v5.6 (fail-loud internally)
        "def ndx_members",  # same context-only role since 2026-07-28
    ],
    "skills/us-stocks-memory/references/board-charter.md": [
        DECISION_RULE,  # the fixed decision rule — user-only change control (charter §13)
        "The orchestrator cannot lower its own bar",
        "## 12. Workflow script — RETIRED 2026-09-13",  # the Board workflow must stay retired
        # governance scope (v6.0 2026-08-17). These four pins are the guard against
        # the over-permissive direction: the constitution must still be FOUR items,
        # the hard block must still exist for them, and E1's panel path must keep
        # its held-out split. The register rename is pinned in the spec below.
        CONSTITUTION_HEADING,
        CONSTITUTION_HARD_BLOCK,
        E1_PATH_B,
        "Sharia — the business-activity blacklist mechanism and its 6 vice categories",
        "Spending the user's money",
        # L5 part 3 (Board-wired 2026-08-21): the ledger block is written
        # BEFORE any wiring. Losing this ordering is what made three
        # APPROVED verdicts unactionable on 2026-08-17.
        "RECORD THE DECISION IN THE DECISION LOG FIRST",
        "Wiring status (U.9.4)",
    ],
    # Rule L5 (Board-wired 2026-08-21, BP-2026-08-21-1). ERA_START scoping, the
    # archive-resolution glob, the three condition ids, the deliberate
    # gainers-output.json exclusion, and the two DETECTION-ONLY guarantees.
    "scripts/uspicks_run_audit.py": [
        'ERA_START = "%s"' % L5_ERA_START,
        'TRACKER_GLOB_PREFIX = "us-weekly-tracker"',
        "EXCLUDED_ARTIFACTS = [\"gainers-output.json\"]",
        "cond_a_logonly_missing",
        "cond_b_suspect_week",
        "cond_c_unrecorded_sessions",
        "DETECTION-ONLY",
        "ALWAYS exits 0",
    ],
    "skills/us-stocks-memory/references/sharia-blacklist.md": [
        "the WHOLE `/us-picks` Sharia screen (single-layer)",  # single-layer pin (no Al Rajhi ratio math)
    ],
    ".gitignore": [
        "!/scripts/uspicks_*.py",
    ],
}

# Repo-scope allowlist for --staged (mirrors .gitignore + CLAUDE.md's
# "in-scope files" list). Any staged path matching none of these fails.
STAGED_ALLOW = [
    r"^README\.md$",
    r"^\.gitignore$",
    r"^commands/us-picks\.md$",
    r"^agents/us-[^/]+\.md$",
    r"^scripts/ensure-deps-us\.sh$",
    r"^scripts/uspicks_[^/]+\.py$",
    r"^skills/us-stocks-memory/.+",
    r"^stocks/us-weekly-tracker\.md$",
    r"^stocks/us-weekly-tracker-v5\.3-archive\.md$",
    r"^stocks/us-weekly-tracker-v4\.4-archive\.md$",
    r"^stocks/us-weekly-tracker-v6\.0-archive\.md$",
    r"^stocks/v45-research-top100-study\.md$",
    r"^projects/[^/]+/memory/project_us_picks_tracker_v3_v4_archive\.md$",
]
# Hard blocks — fail even if a pattern above would allow them (defense in
# depth; mechanizes CLAUDE.md's "if git status shows these, STOP").
STAGED_BLOCK = [
    r"\.polygon_key$",
    r"\.financialdatasets_key$",
    r"\.polygon_flatfiles\.json$",
    r"\.key$",
    r"\.pem$",
    r"\.token$",
    r"^CLAUDE\.md$",
    r"^settings.*\.json$",
    r"credentials",
]

# =========================================================================
# Check machinery
# =========================================================================

FAILURES = []


def fail(check, msg):
    FAILURES.append("[{}] {}".format(check, msg))


def read(root, rel):
    p = root / rel
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


def check_files_exist(root):
    for rel in FILES:
        if not (root / rel).is_file():
            fail("files", "missing in-scope file: {}".format(rel))


def check_agent_models(root):
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return
    on_disk = {p.name for p in agents_dir.glob("us-*.md")}
    for name in sorted(on_disk | set(AGENT_MODELS)):
        if name not in AGENT_MODELS:
            fail("models", "agents/{} exists but is not in the contract's "
                 "AGENT_MODELS map — add it".format(name))
            continue
        text = read(root, "agents/" + name)
        if text is None:
            continue  # reported by check_files_exist
        m = re.search(r"^model:\s*(\S+)", text, re.MULTILINE)
        got = m.group(1) if m else "(none)"
        want = AGENT_MODELS[name]
        if got != want:
            fail("models", "agents/{}: model is '{}', contract says "
                 "'{}'".format(name, got, want))


def check_sentinels(root):
    for rel, needles in MUST_CONTAIN.items():
        text = read(root, rel)
        if text is None or PUBLIC_STUB in text:  # public release: placeholder file
            continue
        for needle in needles:
            if needle not in text:
                fail("sentinels", "{}: missing expected text: "
                     "{!r}".format(rel, needle[:90]))


def check_score_breakdown(root):
    """Parse scoring-model.md's Score Breakdown table (the weights SSOT)."""
    rel = "skills/us-stocks-memory/references/scoring-model.md"
    text = read(root, rel)
    if text is None:
        return
    m = re.search(r"^## Score Breakdown\n(.*?)(?=^## )", text,
                  re.MULTILINE | re.DOTALL)
    if not m:
        fail("weights", "{}: '## Score Breakdown' section not found".format(rel))
        return
    found = {}
    for name, pts in re.findall(r"^\|\s*([^|]+?)\s*\|\s*0-(\d+)\s*\|",
                                m.group(1), re.MULTILINE):
        found[name] = int(pts)
    for name, want in WEIGHTS.items():
        if name not in found:
            fail("weights", "Score Breakdown: component '{}' not found".format(name))
        elif found[name] != want:
            fail("weights", "Score Breakdown: '{}' is 0-{}, contract says "
                 "0-{}".format(name, found[name], want))
    extra = set(found) - set(WEIGHTS)
    if extra:
        fail("weights", "Score Breakdown has unexpected scored components: "
             "{} — scoring change? update WEIGHTS".format(sorted(extra)))
    if found and sum(found.values()) != WEIGHTS_TOTAL:
        fail("weights", "Score Breakdown components sum to {} — must be "
             "{}".format(sum(found.values()), WEIGHTS_TOTAL))


def _parse_table(text, section):
    """Return list of cell-lists for the first table after `## section`."""
    m = re.search(r"^## {}\n(.*?)(?=^## |\Z)".format(re.escape(section)),
                  text, re.MULTILINE | re.DOTALL)
    if not m:
        return None
    rows = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r"[-:\s]*", c) for c in cells):
            continue  # separator row
        rows.append(cells)
    return rows


def _breakdown_table_totals(rows, label):
    """Check a Picks/Big Wins/Wins/Flats/Losses breakdown table; return totals."""
    header = rows[0]
    try:
        idx = {k: header.index(k) for k in
               ("Picks", "Big Wins", "Wins", "Flats", "Losses", "Win Rate")}
    except ValueError as e:
        fail("tracker", "{} table: missing column ({})".format(label, e))
        return None
    tot = dict.fromkeys(("Picks", "Big Wins", "Wins", "Flats", "Losses"), 0)
    for cells in rows[1:]:
        try:
            vals = {k: int(cells[idx[k]]) for k in tot}
        except (ValueError, IndexError):
            fail("tracker", "{} table: unparseable row {}".format(label, cells[:2]))
            continue
        # Convention: 'Wins' INCLUDES Big Wins (rank<=100 is also <=500),
        # so Wins + Flats + Losses == Picks and Big Wins <= Wins.
        if vals["Wins"] + vals["Flats"] + vals["Losses"] != vals["Picks"]:
            fail("tracker", "{} table, row '{}': Wins+Flats+Losses = {} but "
                 "Picks = {}".format(label, cells[0],
                 vals["Wins"] + vals["Flats"] + vals["Losses"], vals["Picks"]))
        if vals["Big Wins"] > vals["Wins"]:
            fail("tracker", "{} table, row '{}': Big Wins {} > Wins {}"
                 .format(label, cells[0], vals["Big Wins"], vals["Wins"]))
        wr = re.match(r"(\d+)%", cells[idx["Win Rate"]])
        if wr and vals["Picks"] > 0:
            want = 100.0 * vals["Wins"] / vals["Picks"]
            if abs(int(wr.group(1)) - want) > 1.0:
                fail("tracker", "{} table, row '{}': Win Rate {}% but "
                     "Wins/Picks = {:.0f}%".format(label, cells[0],
                                                   wr.group(1), want))
        for k in tot:
            tot[k] += vals[k]
    return tot


def check_tracker_math(root):
    rel = "stocks/us-weekly-tracker.md"
    text = read(root, rel)
    if text is None:
        return

    # 1. Census of graded pick rows (rows containing a '| GRADED |' status).
    counts = {"BIG WIN": 0, "WIN": 0, "FLAT": 0, "LOSS": 0}
    graded_rows = 0
    for line in text.splitlines():
        if not line.startswith("|") or "| GRADED" not in line:
            continue
        graded_rows += 1
        for outcome in ("BIG WIN", "WIN", "FLAT", "LOSS"):  # BIG WIN first
            if re.search(r"\|\s*{}\s*\|".format(re.escape(outcome)), line):
                counts[outcome] += 1
                break
        else:
            fail("tracker", "graded row with no parseable Outcome cell: "
                 "{}".format(line[:60]))
    if graded_rows == 0:
        # v5.4 fresh-era state (tracker reset 2026-07-14): 0 graded rows is
        # VALID iff Summary Statistics agrees (Total Picks = 0). Any other
        # 0-row read means the parser or the tracker format broke.
        txt2 = text
        m0 = re.search(r"^\|\s*Total Picks\s*\|\s*(\d+)", txt2, re.MULTILINE)
        if m0 and int(m0.group(1)) == 0:
            return
        fail("tracker", "found 0 graded pick rows — tracker format changed? "
             "update the parser")
        return

    # 2. Summary Statistics vs the census.
    stats = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$", line)
        if m:
            stats.setdefault(m.group(1), m.group(2))

    def stat_int(label_prefix):
        for k, v in stats.items():
            if k.startswith(label_prefix):
                m = re.match(r"(\d+)", v)
                return int(m.group(1)) if m else None
        return None

    total = stat_int("Total Picks")
    big = stat_int("Big Wins")
    wins = stat_int("Wins (")
    flats = stat_int("Flats")
    losses = stat_int("Losses")
    if None in (total, big, wins, flats, losses):
        fail("tracker", "Summary Statistics rows not found/parseable "
             "(Total/Big Wins/Wins/Flats/Losses)")
        return
    if total != graded_rows:
        fail("tracker", "Summary says {} Total Picks but {} GRADED rows "
             "exist".format(total, graded_rows))
    if big != counts["BIG WIN"]:
        fail("tracker", "Summary says {} Big Wins but {} 'BIG WIN' outcome "
             "cells exist".format(big, counts["BIG WIN"]))
    # 'Wins (rank <=500)' includes Big Wins.
    if wins != counts["BIG WIN"] + counts["WIN"]:
        fail("tracker", "Summary says {} Wins but BIG WIN + WIN cells = "
             "{}".format(wins, counts["BIG WIN"] + counts["WIN"]))
    if flats != counts["FLAT"]:
        fail("tracker", "Summary says {} Flats but {} FLAT cells "
             "exist".format(flats, counts["FLAT"]))
    if losses != counts["LOSS"]:
        fail("tracker", "Summary says {} Losses but {} LOSS cells "
             "exist".format(losses, counts["LOSS"]))
    wr = stats.get("Win Rate", "")
    m = re.match(r"(\d+)%\s*\((\d+)\s*/\s*(\d+)\)", wr)
    if not m:
        fail("tracker", "Win Rate row not in 'N% (W / T)' form: {!r}".format(wr))
    else:
        pct, w, t = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if t == 0:
            pass  # v5.4 fresh era: "0% (0 / 0)" is the reset state
        elif (w, t) != (wins, total):
            fail("tracker", "Win Rate fraction ({}/{}) != Wins/Total "
                 "({}/{})".format(w, t, wins, total))
        elif t > 0 and abs(pct - 100.0 * w / t) > 1.0:
            fail("tracker", "Win Rate {}% != {}/{} = {:.0f}%".format(
                pct, w, t, 100.0 * w / t))

    # 3. Sector + Catalyst breakdown tables must re-add to the same totals
    #    (the 2026-07-02 'Commodity/Macro row' fix class).
    for section in ("Sector Performance", "Catalyst Performance"):
        rows = _parse_table(text, section)
        if not rows:
            fail("tracker", "'## {}' table not found".format(section))
            continue
        tot = _breakdown_table_totals(rows, section)
        if tot is None:
            continue
        expect = {"Picks": total, "Big Wins": big, "Wins": wins,
                  "Flats": flats, "Losses": losses}
        for k, want in expect.items():
            if tot[k] != want:
                fail("tracker", "{} table: '{}' column sums to {} but "
                     "Summary Stats says {}".format(section, k, tot[k], want))


def check_staged_scope(root):
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        print("  (staged check skipped — git unavailable)")
        return
    if out.returncode != 0:
        print("  (staged check skipped — not a git repo)")
        return
    for path in out.stdout.splitlines():
        path = path.strip()
        if not path:
            continue
        if any(re.search(b, path) for b in STAGED_BLOCK):
            fail("staged", "BLOCKED path staged: {} — never commit this "
                 "(credentials/private config). Unstage and investigate "
                 "before pushing.".format(path))
        elif not any(re.match(a, path) for a in STAGED_ALLOW):
            fail("staged", "out-of-scope path staged: {} — the repo is "
                 "/us-picks-only (CLAUDE.md Backup-Repo rules). Unstage or, "
                 "if newly in-scope, update .gitignore + STAGED_ALLOW "
                 "together.".format(path))


def check_ck1_no_contamination(root):
    """CK1 (BP-2026-08-28-3, condition 21) — ZERO-TOLERANCE, EVERY COMMIT.

    Not one row in the authoritative L1 log may carry a `provisional` key.
    A single contaminated row reverts CK1 (revert, do not patch). Baseline
    verified green at wiring: 260 rows, 0 hits.
    """
    log = root / "stocks" / "us-candidate-scores.jsonl"
    if not log.exists():
        return
    bad = 0
    try:
        with open(log, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    if "provisional" in json.loads(line):
                        bad += 1
                except ValueError:
                    continue
    except OSError:
        return
    if bad:
        FAILURES.append(
            "[ck1] stocks/us-candidate-scores.jsonl: {} row(s) carry a "
            "`provisional` key — CK1 contamination is a zero-tolerance "
            "REVERT condition (BP-2026-08-28-3)".format(bad))


def check_bm_source_enum(root):
    """BP-2026-09-04-1 (Board-wired 2026-09-04, APPROVED 5-0) — STRUCTURAL enum check that
    closes the CLASS, not the instance (Chair C12 / engineer 7): (a) every member of
    uspicks_board_pack.py's BM_SOURCE_ENUM appears in the canonical string and vice-versa;
    (b) the canonical string is present BYTE-IDENTICAL in every file that pins it; (c) NEGATIVE —
    the retired six-token 'one of:' string and the stale FD-cancelled phrases must not survive
    on a live-path line (a line carrying an explicit superseded/historical marker is exempt)."""
    pack = read(root, "scripts/uspicks_board_pack.py")
    if pack is None:
        return
    m = re.search(r"BM_SOURCE_ENUM\s*=\s*\(([^)]*)\)", pack, re.S)
    if not m:
        fail("bm-source-enum", "BM_SOURCE_ENUM tuple not found in scripts/uspicks_board_pack.py")
        return
    members = re.findall(r'"([a-z0-9_]+)"', m.group(1))
    canon = re.findall(r"`([a-z0-9_]+)`", BM_SOURCE_ENUM_CANON.split("one of:")[1])
    for tok in members:
        if tok not in canon:
            fail("bm-source-enum", "reader enum member {!r} is missing from the canonical "
                 "string — move ALL pinned files together".format(tok))
    for tok in canon:
        if tok not in members:
            fail("bm-source-enum", "canonical token {!r} is missing from the reader's "
                 "BM_SOURCE_ENUM".format(tok))
    pinned = ["commands/us-picks.md", "stocks/us-weekly-tracker.md",
              "skills/us-stocks-memory/references/scoring-model.md",
              "skills/us-stocks-memory/SKILL.md",
              "skills/us-stocks-memory/references/us-picks-system-spec.md", "README.md"]
    for rel in pinned:
        text = read(root, rel)
        if text is not None and BM_SOURCE_ENUM_CANON not in text:
            fail("bm-source-enum", "{}: canonical bm_source enum string missing".format(rel))
    stale = (BM_SOURCE_ENUM_RETIRED_SIX,
             "Financial Datasets tokens are absent",
             "Financial Datasets tokens are likewise absent",
             "FD RETIRED (2026-08-14)",
             "Financial Datasets RETIRED 2026-08-14, subscription cancelled")
    markers = ("superseded", "historical", "2026-08-22 state", "re-opened", "retired_six",
               "before the fix", "prior status", "bp-2026-09-04", "the stale", "stale text")
    for rel in pinned + ["agents/us-bigmoney-analyzer.md"]:
        text = read(root, rel)
        if text is None:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            for phrase in stale:
                if phrase in line and not any(k in low for k in markers):
                    fail("bm-source-enum", "{}:{}: stale bm_source/FD phrase survives on a "
                         "live-path line: {!r}".format(rel, ln, phrase[:60]))


def check_board_retired_no_stale(root):
    """2026-09-13 governance amendment — NEGATIVE gate: the Board of Advisors is
    RETIRED, so no CURRENT-STATE text may describe it as the decider. History
    stays (lines marked retired / historical / superseded / formerly / legacy are
    exempt, and markdown table rows — the README version history — are skipped).
    """
    stale = ("convene the Board of Advisors on demand", "the Board's Secretary runs",
             "Phase U.9 Board session", "BOARD DECISIONS card is the run",
             "### U.9 Board of Advisors Session", "`/us-picks board` convenes")
    markers = ("retired", "historical", "superseded", "formerly", "legacy", "was ")
    targets = ["commands/us-picks.md", "skills/us-stocks-memory/SKILL.md",
               "skills/us-stocks-memory/references/board-charter.md", "README.md"]
    for rel in targets:
        text = read(root, rel)
        if text is None:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("|"):
                continue
            low = line.lower()
            if any(k in low for k in markers):
                continue
            for phrase in stale:
                if phrase in line:
                    fail("board-retired", "{}:{}: describes the retired Board as current: "
                         "{!r}".format(rel, ln, phrase))


def check_board_rekey_no_stale(root):
    """2026-09-14 governance re-key — NEGATIVE gate extending check_board_retired_no_stale.

    The 2026-09-13 amendment re-keyed the command, SKILL.md and the charter but left
    present-tense Board / Secretary / director wording in the spec's rule entries and
    Prior Decisions Register, the tracker's rules section and scoring-model.md; that
    wording was re-keyed to the orchestrator's Decision Review on 2026-09-14. These are
    the phrases removed. A dated record may still quote one when a marker sits in the
    160 characters BEFORE it — a window, not the whole line, because the spec's rule
    entries are multi-KB lines that nearly always contain "retired" somewhere. Table
    rows are skipped; the tracker is scanned only in its Lesson-Wired Rules section
    (its Board ledger is history by design).
    """
    stale = ("judged by the Board", "a Board auto-revert", "the next Board pack",
             "routes through a Board proposal", "A Board proposal (or the user) MAY reverse",
             "the Risk Officer votes REJECT", "hard-blockable** by Director 2",
             "Board-of-Advisors verdict", "carried verbatim into the Secretary's prompt",
             "is in Board remit", "the Board's Secretary executes", "no future Board",
             "the Board may only recommend", "a Board verdict computed under the fixed rule",
             "Phase U.9 BOARD DECISIONS card", "U.9.2b ledger-before-wiring",
             "Phase U.9.2b ordering:")
    markers = ("until 2026-09-13", "→ 2026-09-13", "under the board", "board era",
               "historical", "superseded", "retired", "formerly")
    targets = ["skills/us-stocks-memory/references/us-picks-system-spec.md",
               "skills/us-stocks-memory/references/scoring-model.md",
               "skills/us-stocks-memory/SKILL.md", "commands/us-picks.md",
               "skills/us-stocks-memory/references/board-charter.md", "README.md",
               "stocks/us-weekly-tracker.md"]
    for rel in targets:
        text = read(root, rel)
        if text is None:
            continue
        offset = 0
        if rel == "stocks/us-weekly-tracker.md":
            a = text.find("## Lesson-Wired Rules Applied")
            b = text.find("<!-- RULES END -->")
            if a < 0 or b < 0:
                continue
            offset = text[:a].count("\n")
            text = text[a:b]
        for ln, line in enumerate(text.splitlines(), 1 + offset):
            if line.lstrip().startswith("|"):
                continue
            for phrase in stale:
                start = line.find(phrase)
                while start >= 0:
                    window = line[max(0, start - 160):start].lower()
                    if not any(k in window for k in markers):
                        fail("board-rekey", "{}:{}: retired-Board wording written as "
                             "current: {!r}".format(rel, ln, phrase))
                    start = line.find(phrase, start + 1)


def check_current_state_no_stale(root):
    """2026-10-04 Decision Review D-2026-10-04-1 — NEGATIVE gate on agent files,
    the weekly-PDF spec and README.

    The user's v6.1 (2026-08-29) and v6.3 (2026-09-01) restores were propagated to
    the command, spec, SKILL.md and scoring-model.md, and the 2026-09-13 / 2026-09-14
    drift fixes swept those again — but no gate read the agent files, so the two
    GRADING agents still told their subagents that rank is "context only" and SPY "the
    benchmark every Outcome derives from", and the risk assessor's task 4 still said
    "do NOT assign R/L points" to volatility beside its own VolFit 0-3 formula. These
    are the phrases removed (the class, not the instance). A dated record may still
    quote one when a marker sits in the 160 characters BEFORE it; table rows skipped.
    """
    stale = ("Rank is CONTEXT ONLY", "the benchmark every Outcome derives from",
             "harmless, since rank is context", "the CONTEXT rank for each pick",
             "do NOT assign R/L points", "Risk/Liquidity Score: XX/12",
             "after_hours_close ≥ $5`", "`price ≥ $5`", "B1 `atr_pct ≥ 2.0` floor",
             "the oversold < 25 blacklist was removed",
             "feeds the v5.0 Volatility scoring component",
             "Component order is fixed (v5.7", "**slots 11-15** → `runners_up`",
             "week baseline → `baseline_ar`", "wired manually via",
             "that is manual via `/us-picks lesson`")
    markers = ("superseded", "historical", "retired", "legacy", "until 2026-",
               "→ 2026-0", "(was ", " was ")
    targets = sorted(p.relative_to(root).as_posix()
                     for p in (root / "agents").glob("us-*.md"))
    targets += ["skills/us-stocks-memory/references/report-design.md", "README.md"]
    for rel in targets:
        text = read(root, rel)
        if text is None:
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("|"):
                continue
            for phrase in stale:
                start = line.find(phrase)
                while start >= 0:
                    window = line[max(0, start - 160):start].lower()
                    if not any(k in window for k in markers):
                        fail("current-state", "{}:{}: retired v6.1/v6.3-era statement "
                             "written as current: {!r}".format(rel, ln, phrase))
                    start = line.find(phrase, start + 1)


def check_spec_history_split(root):
    """2026-09-13 spec / version-history split — the spec is CURRENT STATE only.

    (a) NEGATIVE: no line of the spec may open a dated amendment block — new
    blocks are prepended to the history file, never added to the spec; (b) the
    history file must still hold at least HISTORY_MIN_BLOCKS amendment-block
    headings — a truncated or overwritten history is a lost SSOT, not a tidy-up.
    """
    pat = re.compile(AMENDMENT_HEADING_RE)
    spec = read(root, SPEC_FILE)
    if spec is not None:
        for ln, line in enumerate(spec.splitlines(), 1):
            if pat.match(line):
                fail("spec-history", "{}:{}: amendment-block heading in the spec — "
                     "prepend it to {} instead: {!r}".format(
                         SPEC_FILE, ln, SPEC_HISTORY_FILE, line[:60]))
    hist = read(root, SPEC_HISTORY_FILE)
    if hist is not None and PUBLIC_STUB not in hist:  # public release ships a placeholder
        n = sum(1 for line in hist.splitlines() if pat.match(line))
        if n < HISTORY_MIN_BLOCKS:
            fail("spec-history", "{}: {} amendment-block headings, expected at least "
                 "{} — history truncated or overwritten?".format(
                     SPEC_HISTORY_FILE, n, HISTORY_MIN_BLOCKS))


def check_pdf_yardstick_no_stale(root):
    """2026-09-13 drift fix — NEGATIVE gate on the weekly PDF renderer.

    The v6.2 money-scoreboard wording (WIN = the stock beats the S&P 500's
    same-week return; picks goal = beat the S&P 500) survived the 2026-09-01
    v6.3 rank restore in uspicks_pdf.py's fixed footer and picks kicker, so
    every weekly PDF printed a WIN definition contradicting its own rank
    caption. The yardstick is user-only (board-charter §3.1); a reader
    surface must state the live one. Gate the retired phrases (the class).
    """
    rel = "scripts/uspicks_pdf.py"
    text = read(root, rel)
    if text is None:
        return
    for phrase in ("على عائد مؤشر S&P 500", "الهدف: التفوّق على مؤشر S&P 500"):
        if phrase in text:
            fail("pdf-yardstick", "{}: retired v6.2 SPY-bar wording survives: "
                 "{!r}".format(rel, phrase))


def check_selection_band_no_stale(root):
    """v6.1 (2026-08-29) — NEGATIVE grep gate, INVERTED from its 2026-08-28 form.

    The pick band is the TOP 5 BY SCORE again (the Board's S[6..10] band of
    BP-2026-08-28-1 was reverted by user direction with the v4.6 restore), so the
    stale assertion to hunt is now the S-band wording, not "top 5 by score".
    Historical / superseded prose is exempt where it is explicitly marked.
    """
    stale = ("picks = S[6..10]", "runners-up = S[11..15]",
             "the S[6..10] band", "`excluded-top` = S[1..5]")
    targets = [
        root / "commands" / "us-picks.md",
        root / "skills" / "us-stocks-memory" / "SKILL.md",
        root / "skills" / "us-stocks-memory" / "references" / "report-design.md",
    ]
    for f in targets:
        if not f.exists():
            continue
        try:
            body = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for phrase in stale:
            for ln, line in enumerate(body.splitlines(), 1):
                if phrase not in line:
                    continue
                low = line.lower()
                if any(k in low for k in ("superseded", "retired", "historical",
                                          "reverted", "was ", "v6.1", "board bp-",
                                          "original", "archive", "carried forward")):
                    continue
                fail("selection-band",
                     "{}:{}: stale S-band assertion '{}' survives the 2026-08-29 "
                     "v6.1 top-5 restore".format(f.relative_to(root), ln, phrase))


def main():
    ap = argparse.ArgumentParser(description="/us-picks consistency gate")
    ap.add_argument("--root", default=str(Path.home() / ".claude"),
                    help="system root (default ~/.claude)")
    ap.add_argument("--staged", action="store_true",
                    help="also verify staged git paths against the repo-scope "
                         "allowlist (used by the pre-commit hook)")
    args = ap.parse_args()
    root = Path(args.root).expanduser()

    check_files_exist(root)
    check_agent_models(root)
    check_sentinels(root)
    check_score_breakdown(root)
    check_tracker_math(root)
    check_ck1_no_contamination(root)
    check_selection_band_no_stale(root)
    check_pdf_yardstick_no_stale(root)
    check_board_retired_no_stale(root)
    check_board_rekey_no_stale(root)
    check_current_state_no_stale(root)
    # check_bm_source_enum retired 2026-09-19 (D-2026-09-19-1) — the field is no longer written
    check_spec_history_split(root)
    if args.staged:
        check_staged_scope(root)

    if FAILURES:
        print("uspicks_lint: {} FAILURE(S) in {}".format(len(FAILURES), root))
        for f in FAILURES:
            print("  ❌ " + f)
        print("\nFix the file(s) — or if the system state legitimately "
              "changed, update the CONTRACT in scripts/uspicks_lint.py in "
              "the same edit set (see the header's UPDATE RULE).")
        return 1
    print("uspicks_lint: ✅ all checks passed ({} files, root {})".format(
        len(FILES), root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
