# /us-picks Decision Charter (2026-09-13 — the Board of Advisors is RETIRED; the orchestrator decides)

> **What this file is.** The single source of truth for how the `/us-picks` system changes its own rules and decision logic: who decides (since 2026-09-13, **the orchestrator** — the Claude session running `/us-picks update` or `/us-picks review`), what it may change (the remit), what it may never change (the four-item constitution), on what evidence (the pre-committed bar E1-E10), how every decision is recorded (the tracker's **Decision Log**) and how the user is told (the **SYSTEM DECISIONS** card). The file keeps its historical name `board-charter.md` so every existing link still resolves. Read it in full before running a Decision Review (command Phase U.9) or editing anything it governs.
>
> **Standing user directive #1 (2026-08-17, verbatim) — the loop:** *"from now on, this system should add or edit and even delete rules. and learn from its mistakes going forward. i (the user) will not interfere in any. However. when wanting to improve your self you should spawn /workflows a panel of advisor of Opus 5 or Opus. like a board of directors and see if that desicion is good or not. if so, go with it. if not. don't. also. whatever descision is made. i should be only be informed about it. thats it."*
>
> **Standing user directive #2 (2026-08-17, verbatim) — v6.0, the self-imposed guards released:** *"ok, whatever was written before saying do not re-add or do not edit etc. those were rules i added. like i said before, right now you make the rules and adjust anything to better land the top 100 or 500."*
>
> **Standing user directive #3 (2026-09-13, verbatim) — the Board retired:** *"no need for board anymore. you decide ur self."* Given after the user asked what the running Board session was deciding and noted that v4.6 had no board. The session in progress (2026-09-13, mid-Secretary) was stopped with nothing decided.
>
> **What the 2026-09-13 amendment changes — and what it does not.** It removes the **panel**: no Workflow, no Secretary, no five directors, no Chair, no vote. It does **not** remove the discipline the panel enforced: the **remit (§2)**, the **four-item constitution (§3)**, the **pre-committed evidence bar E1-E10 (§4)**, the **auto-review duty (§7)** and **rule F1** now bind the orchestrator exactly as they bound the Board, and **the orchestrator cannot lower its own bar or widen its own remit**. **Recorded honestly at the amendment:** the independent, lens-diverse check is gone. The 2026-05-01 auto-learning failure (R2 wired on n=1, S1 on n=0) was this same decider acting alone without a bar; the difference now is that the bar is pre-committed and user-owned, every decision is written into the Decision Log *before* anything is edited, and every wired change carries an auto-review that can reverse it. "No change" remains the normal result of a review.
>
> **History.** v5.9 (2026-08-17) created the Board; v6.0 (the same day) widened its remit and shrank the constitution to four items; six sessions ran (2026-08-17, 2026-08-17-s2 [lost, annexed], 2026-08-21, 2026-08-22, 2026-08-28, 2026-09-04) and wired L4, L5, CK1, the `bm_source` token, the per-week universe archive and the archive liquidity basis — all still live with their auto-review terms, now executed by the orchestrator. The Board's ledger stays in the tracker as a historical section. Before v5.9 the loop was MANUAL (v4.6, 2026-05-01 → 2026-08-17): only the user's `/us-picks lesson "X"` wired rules — that path still exists unchanged.

---

## 1. Governance model in one paragraph

**The system decides. The user is informed.** After every grading run (`/us-picks update`) — and on demand via `/us-picks review` (`board` is kept as a legacy alias) — the orchestrator runs the **Decision Review** (command Phase U.9): it builds the evidence pack, executes every pre-committed check and auto-review that has come due exactly as written, and decides at most **3 changes**, each written up as a decision packet and judged by the **fixed decision rule (§6)** against the **pre-committed evidence bar (§4)**. Every decision — wired or not — is recorded in the tracker's **Decision Log** *before* any file is edited, and the review closes with the **SYSTEM DECISIONS** card. **The user is never asked a question by this process.** `/us-picks lesson "X"` (user-initiated, with its own YES/EDIT/CANCEL loop) still exists and bypasses the review — the user is the principal. **Scope:** everything instrumental to the rank objective (§2), bounded by exactly four user-only items (§3), by rule F1, and by an evidence bar the orchestrator cannot lower (§4).

## 2. Remit — what the orchestrator MAY change (through a recorded Decision Review decision)

**Principle (v6.0, unchanged by the 2026-09-13 amendment):** everything instrumental to the yardstick's objective — **the weekly top 100 / top 500 RANK** (v6.3, 2026-09-01) — is in remit. If a change could plausibly improve that outcome and it is not one of the four constitutional items in §3, the orchestrator may decide it — **but while rule F1 is live, only `logging` / `process-fix` changes may be wired; every other class files to the tracker's Improvement Backlog.**

- **Lesson-Wired Rules:** add, edit (mechanism, thresholds, scope), deactivate, reactivate, or delete any rule in the tracker RULES block / spec `US_RULES` block.
- **Scoring — weights AND structure:** component weights and sub-rubric bands; adding or removing a scored component (including re-scoring Big Money); tie-breaks. Any matrix change follows the spec's version-label convention — new matrix version + migration note.
- **Hard filters — every parameter, and the set itself:** RSI band, `atr_pct` floor, the pick-side liquidity floor, the price floor at any level, the conviction threshold at any level, and adding or removing a filter. Earlier carve-outs are Prior Decisions to be argued against with evidence (§4 E6), not walls.
- **The pick universe:** the `mkt_cap` floor, any index gate, and the eligible-set definition (blind spot BS-1). A universe change carries a mandatory **advisory notice on the card** (it changes what kind of company the user owns) but does not need his approval.
- **Portfolio construction:** the pick-count cap and the allocation rule.
- **The trade plan:** entry and exit modelling (retired as instructions by v6.1 — reviving any part is a Prior Decision to argue). A trade-plan change also carries the mandatory advisory notice.
- **The selection rule** (how the slate is chosen from the scored survivors) and the finalist-verify scope.
- **Data-source selection and model assignment WITHIN the existing cost envelope:** which agent runs on which tier, batch sizes, fan-out shape, and which already-paid feed serves which slot. **Buying anything new is §3.3.**
- **Logging, reminders, pre-committed checks and process safety** — the lowest-risk class; these change no score.
- **Executing the pre-committed checks and auto-reviews** — L2 (Options weight), L3 (selection-rule re-test, DONE 2026-08-28) and every open auto-review term (including those the Board attached): run them as written when due; a check's *amendment branch* becomes a candidate change, its *negative branch* executes mechanically as the rule already states.

## 3. Constitution — the FOUR things the orchestrator may NOT change (user-only, by a dated user-directed amendment)

_Shrunk from 8 items to 4 by user directive #2 (v6.0); binding on the orchestrator since directive #3 (2026-09-13). The orchestrator may put an **ADVISORY RECOMMENDATION** about any of these on the card — never enact it. **A constitution breach is never wired**, whatever the evidence._

1. **The objective, the WIN taxonomy, and the grading window — the YARDSTICK (set by the user; current form = v6.3, 2026-09-01).** **WEEKLY RANK: WIN = the pick's `FIRST_TRADING_DAY` 09:30 open → `LAST_TRADING_DAY` regular close return ranks ≤ 500 in the liquid ~$1M/day universe** (BIG WIN ≤ 100 · FLAT 501-1500 · LOSS > 1500 or unranked), judged beside the seeded random-5 control and the ~13% chance baseline; the close return, SPY edge and the +2% peak touch (bound to its base rate) are reported context. _(Prior forms — the v6.2 money scoreboard vs SPY, 2026-08-30 → 2026-09-01, 0 graded weeks; the v6.1 +2% peak touch, 2026-08-29 → 08-30, 0 graded weeks; the top-500/top-100 rank, v5.6-v6.0 — each replaced by the user's own dated directive; only the user may ever change it again.)_ **Also user-imposed and binding: rule F1, the 12-week freeze — clock RESTARTED 2026-09-01; until the tracker holds 12 graded v6.3 weeks, a review may wire `logging`/`process-fix` changes ONLY; every other class, whatever its evidence, files to the tracker's Improvement Backlog for the week-12 gate.** **Why this stays user-only:** the yardstick is the fixed target the entire remit optimises toward; a decider that could move its own measuring stick could never be shown to be wrong.
2. **Sharia — the business-activity blacklist mechanism and its 6 vice categories.** A values constraint, not a performance one. Never loosened, never traded against hit rate, never a change that drops a vice category. (Adding a ticker under the existing "if unsure, include it" maintenance rule stays an ordinary edit.)
3. **Spending the user's money.** New or re-instated paid subscriptions and data tiers, added paid add-ons, and any rise in the per-run cost envelope. The orchestrator may recommend a purchase with its reasoning; only the user buys. _(Re-pointing slots among feeds already paid for is §2.)_
4. **This charter and the evidence bar.** The decision rule, §4's E1-E10, the remit, and this constitution. **The orchestrator cannot lower its own bar or widen its own remit** — only the user's own dated directive changes this file.

## 4. Evidence bar — pre-committed; the orchestrator decides NOT WIRED by default when it is not affirmatively met

Every decision packet must state each applicable item:

| # | Requirement | Why it exists |
|---|-------------|---------------|
| E1 | **Sample — either path, never neither.** **Path A (live outcomes):** a score/filter/selection/universe/trade-plan change needs **≥ 3 weeks of outcome data AND ≥ 12 graded picks** of the current era (weeks graded in the tracker OR retro-ranked from the L1 log against their own full universe). **Path B (panel):** a result from the **2006-2026 backtest panel** (or the 263-week bar-history) with an explicit **fit/validate split** AND **replication across ≥ 2 distinct market eras**, citing the artifact under `stocks/_analysis/` or `stocks/_backtest2006/`. A logging/reminder/process change needs only ≥ 2 graded weeks or one documented incident. | R2 was wired on n=1, S1 on n=0. |
| E2 | **Replication across weeks:** the direction holds in **≥ 3 of the last 4 weeks** it was measured on (or ≥ 75% of weeks when more exist) — never a pooled average alone. | 2026-08-16: `atr_pct`, RSI, distance-from-high all INVERTED sign between July and August weeks. |
| E3 | **Stratified test:** any pooled result is re-tested **within week** (permutation, stratified) before it counts. | 2026-08-16: a 3.2× pooled gap vanished stratified — a Simpson artifact. |
| E4 | **Comparison arm named:** picks vs runners-up, vs the random-5 control, vs the eligible universe, vs the 263-week bar distribution, or vs the 20-yr panel. | The archived runners-up control (20%) beat the picks (15%). |
| E5 | **Multiple comparisons + out-of-sample:** a finding from sweeping many features carries a Holm-corrected p or a confirmation on weeks not used to generate it. | 2026-08-16: 17 features swept, best raw p 0.026 → Holm 0.43. |
| E6 | **Prior-decision guard — ANSWER it, don't avoid it.** Name every entry of the spec's **Prior Decisions Register** the change touches and give an explicit **reversal argument** (the original evidence, and why it no longer holds). A silent re-introduction fails E6. `[HARD — §3]` entries are never reversed. The constitution (§3) must be untouched. | Silent regressions are the failure class the register exists to stop. |
| E7 | **Cost of being wrong + reversibility:** one paragraph; a change that would move real money the wrong way for weeks weighs heavier than a logging change. | Real capital follows the picks. |
| E8 | **Auto-review terms:** the metric, the horizon (default **4 graded weeks**), and the reversal condition are pre-stated. | Learning from mistakes includes the decider's own. |
| E9 | **Anti-churn:** the same target was not changed within the last **4 graded weeks** (unless its own auto-review fired); **≤ 3 changes per review**; a change decided NOT WIRED is re-decided only on materially new evidence (sample grew ≥ 50% or a new week class). | A rule that flip-flops weekly is worse than either setting. |
| E10 | **Honesty line:** what would refute it and how thin it is (n, era span, matrix span). | The tracker's own analyses recorded their limits; decisions must too. |

**Process/logging changes** (kind `process-fix` / `logging`) satisfy E1 by an incident or a measured data gap, are exempt from E2/E3/E5 (there is no outcome direction to replicate), and still carry E6-E10.

## 5. Review triggers (command Phase U.9)

A Decision Review runs when ANY holds; otherwise Phase U.9 prints one line — *"Decision review: not run (no new evidence, no due checks)"* — and the run ends normally:

- **(a)** ≥ 1 week was graded in this update run (new outcome evidence). Not on `GRADE_PENDING_DATA`-only runs.
- **(b)** a **pre-committed check is due** — L2 (`era_graded_weeks ≥ 4`, status `PENDING EVALUATION`), L3 (`l1_runs ≥ 6`, status `PENDING RE-TEST`), or an **auto-review** whose horizon has arrived (in the Decision Log, a RULES entry, or the historical Board ledger).
- **(c)** `/us-picks review` (or the legacy `/us-picks board`) was invoked — it grades nothing.

Pick runs (Sundays) never run a review: outcomes are unknown until grading, and a rule must never change mid-run. The Phase 1 card shows the latest Decision Log line so the user sees on Sunday what changed.

## 6. The decider and the decision rule

**The decider:** the orchestrator — the session running `/us-picks update` or `/us-picks review` — alone. No panel, no vote, no Workflow (retired 2026-09-13, §12).

**Decision rule (fixed — in one line): WIRED iff it affirmatively clears the pre-committed evidence bar (E1-E10), sits inside the remit, and touches no constitutional item; otherwise NOT WIRED.**
- **NOT WIRED is the default** whenever the packet is incomplete, a required E-item is unanswered, or the counter-case below is not answered on the evidence.
- **Mandatory counter-case:** before deciding, the orchestrator writes the strongest case AGAINST the change (alternative explanations, week-composition artifacts, regime dependence, look-ahead, small-n luck, the tracker's own refuted hypotheses) and states what evidence would change its mind. This keeps the Devil's-Advocate discipline of the retired panel inside a single decider.
- **A constitution breach is never wired** — at most it becomes an advisory line on the card.
- **Out of remit** (anything in §3, or a change to this file) → NOT WIRED, advisory only.

## 7. Auto-review, auto-revert, and what "learn from mistakes" means mechanically

- Every WIRED change carries **auto-review terms** (E8). When the horizon arrives, trigger (b) fires: the orchestrator re-measures the named metric on the weeks graded since the change. **Held → the review closes** (`review: HELD <date>` on the rule entry and its log row). **Breached → the reversal is itself a candidate change**, decided under §6 the same way (symmetry: undoing is a change too). Neither outcome needs the user.
- Auto-review terms attached by the retired Board (L4, L5, CK1, `bm_source`, the per-week archive, the archive liquidity basis) remain binding and are executed by the orchestrator on their stated horizons.
- The pre-committed checks L2/L3 keep their exact wording; their amendment branch reads *"decide in the Decision Review"* (filed to the Backlog while F1 is live).
- The system learns from its own record: every NOT WIRED decision is logged with what would change it, and that record is part of every future evidence pack.

## 8. Executing a WIRED decision (same run, before the card renders)

0. **RECORD THE DECISION IN THE DECISION LOG FIRST — before any file is edited.** Insert the §9.1 block at the top of the tracker's `## Decision Log (orchestrator)` section with a `- **Wiring status (U.9.4):** _pending_` line; step 5 fills it in. (This is the 2026-08-21 ordering fix, kept: a review that dies mid-wiring must leave a record, and nothing may be wired that was not first recorded.)
1. Assign the rule ID / amendment label per Phase L.2 conventions (a scoring-matrix or filter change is an **amendment** with the spec's version conventions, not a rule ID); decision IDs are `D-YYYY-MM-DD-n`.
2. Wire per Phase L.5 across every file the packet names, plus the spec's invariant-matrix row for the invariant touched; the tracker RULES entry / spec block records **`Decided by: orchestrator review YYYY-MM-DD, D-…`** in place of a user instruction, plus the auto-review terms.
3. Run `python3 ~/.claude/scripts/uspicks_lint.py`; if the change is a state change, update the linter CONTRACT in the same edit set (never silence a check).
4. Run the Rigorous Self-Audit steps (re-read edited files, grep old values, both-way cross-refs, walk the flow); then commit + push per the CLAUDE.md procedure — commit message `review YYYY-MM-DD: <D-id> <short change>`.
5. **VERIFY** the block written at step 0 and **APPEND** its `- **Wiring status (U.9.4):**` line — `WIRED <files>` / `not wired` / `DECIDED — WIRING BLOCKED (<reason>)` — never insert a second block. Only then render the SYSTEM DECISIONS card. If wiring fails a check, the change is **NOT live**: the log reads `DECIDED — WIRING BLOCKED (<reason>)`, partial edits are reverted, and the next review may re-decide it.

## 9. Decision Log + card formats

**9.1 Tracker section `## Decision Log (orchestrator)`** — one block per review, newest first, inserted directly under the section intro (Phase 0.4 reads the newest block for the Phase 1 card line):

```markdown
### Review YYYY-MM-DD — trigger: [graded week(s) YYYY-MM-DD | due check L2/L3 | auto-review … | manual] — evidence: N graded weeks / N picks / N logged runs

| ID | Kind | Change | Decision | Effective | Auto-review |
|----|------|--------|----------|-----------|-------------|
| D-YYYY-MM-DD-1 | process-fix | [one line] | WIRED | next run | [metric] by [date] |
| D-YYYY-MM-DD-2 | rule-edit | [one line] | NOT WIRED | — | — |

- **D-…-1 — why:** [≤ 2 lines: the evidence-bar result; the counter-case and why it failed] · files: [list]
- **D-…-2 — why not:** [≤ 2 lines] · would change the decision: [line]
- **Checks executed:** [check → outcome] · [check → outcome]
- **Considered, not wired:** [topic — why] · [topic — …]
- **Advisory to the user (constitutional, not enacted):** [line or "none"]
- **Wiring status (U.9.4):** [WIRED <files> | not wired | DECIDED — WIRING BLOCKED (<reason>) | _pending_ before wiring]
```

**9.2 The SYSTEM DECISIONS card** — the run's closing output (after the U.8 `SAVED:` line and any due L-banners); fixed-width, hand-padded to 71 columns:

```
+=====================================================================+
|  SYSTEM DECISIONS — REVIEW YYYY-MM-DD (the orchestrator decides)    |
|  Trigger: [graded week / due check / auto-review / manual]          |
|  Evidence: N graded weeks · N picks · N logged runs                 |
+---------------------------------------------------------------------+
|  D-YYYY-MM-DD-1  [kind]  ->  WIRED                                  |
|  Change:  [one line — what changes]                                 |
|  Why:     [one line — the evidence-bar result]                      |
|  Effect:  live from your next /us-picks run; wired in [files]       |
|  Review:  [metric] after [N] graded weeks (by YYYY-MM-DD)           |
+---------------------------------------------------------------------+
|  Checks executed: [n] — [check → outcome; …]                        |
|  Considered, not wired: [n] — [topic; topic; …]                     |
|  Advisory to you (constitutional, NOT enacted): [line or none]      |
|  Nothing here needs an answer — you are being informed. Full        |
|  record: tracker Decision Log.                                      |
+=====================================================================+
```

A "no review" run prints only: `Decision review: not run (no new evidence, no due checks)`. A review that wires nothing still prints the header, the checks and the considered line — a real result, not an error.

**9.3 The historical Board ledger** (`## Board of Advisors — Decision Ledger (v5.9)` in the tracker) is kept verbatim below the Decision Log: its `### Session <id>` blocks, the 2026-08-17-s2 annex, and the 2026-09-13 cancellation note. Its open auto-review terms are read by Phase 0.4 like Decision Log rows. The session-id contract (a `stocks/board/<id>/session.json` must have a matching `### Session <id>` header) still governs rule L5's condition (c) for those historical directories; a review writes its evidence pack to `stocks/board/<DATE>/` but never a `session.json`.

## 10. Cost, time, limits (honest)

- **Cost:** no extra agents — the review runs inside the grading session. The retired Board cost roughly $10-30 per session in Opus agents.
- **Time:** a few minutes, longer when a due check retro-ranks several weeks.
- **Limits (recorded, not hidden):** this is one model deciding about its own system. The retired panel's five independent lenses are gone; what remains is the pre-committed bar the orchestrator cannot lower, the written counter-case, the record-first Decision Log and the auto-review that can reverse any change. Expect most reviews during F1 to wire nothing or only housekeeping — that is the discipline working, not a broken loop.

## 11. Evidence pack — `scripts/uspicks_board_pack.py`

The orchestrator builds the pack mechanically before every review: `python3 ~/.claude/scripts/uspicks_board_pack.py --session YYYY-MM-DD --trigger "<text>"` writes `~/.claude/stocks/board/YYYY-MM-DD/evidence-pack.json` (system version + rule states + Summary Stats + every graded week's picks/runners-up outcomes + Lessons Learned + blind spots + L1 log stats + `_analysis/` inventory + the historical Board ledger + archive/basis readers). No judgment inside — it is a reader, and it keeps its historical script and directory names. Its `--render` mode rendered the retired Board's card from a `session.json` and is no longer used.

## 12. Workflow script — RETIRED 2026-09-13

The Board's Workflow script (Secretary → 5 directors → Chair, verdict computed by the ≥ 4/5 rule) is retired with the Board and must not be run. It is preserved in git history (last present in commit `7754e89`, 2026-09-13). The last invocation — session 2026-09-13 — was stopped mid-Secretary by the user's directive with nothing decided and nothing recorded as a verdict.

## 13. Change control for this charter

Only the user changes this file, by a dated user-directed amendment recorded in `us-picks-system-spec-history.md` (the spec's version history, split out of `us-picks-system-spec.md` 2026-09-13). The orchestrator may put an **advisory recommendation** about it on the SYSTEM DECISIONS card — never enact it. `uspicks_lint.py` pins this file's presence, its decision-rule sentence and the retirement of the Board.

**Amendment history of this charter:**

| Version | Date | User directive | What changed |
|---------|------|----------------|--------------|
| v5.9 | 2026-08-17 | directive #1 (autonomy + a Board gate) | Charter created: remit, 8-item constitution, E1-E10 bar, 5 lenses + Secretary + Chair, the fixed decision rule, ledger/card formats, the §12 workflow script. |
| v6.0 (§8/§9 amended by the Board 2026-08-21) | 2026-08-17 | directive #2 (*"those were rules i added … you make the rules and adjust anything to better land the top 100 or 500"*) | Constitution 8 items → **4** (§3); remit widened to scoring structure, all filter parameters at any level, the pick universe, portfolio construction, the trade plan, and in-budget data/model assignment (§2); the spec's retired-invariants list → **Prior Decisions Register**, veto → argued reversal (§4 E6); Director 2's HARD BLOCK narrowed to constitution-only (§6); E1 gained **Path B** (2006-2026 panel with fit/validate split + cross-era replication) (§4). The bar itself and the yardstick were deliberately NOT released. |
| v6.1 yardstick update (recorded 2026-08-30) | 2026-08-29 | user directives (*"my goal is sell at 2% at least"* · *"No, to back to 4.6. And use the strategy of 2% as we agreed."*) | **§3.1 and the §12 BAR text updated to the yardstick's NEW FORM** — WIN = intraweek peak ≥ +2% from the Monday 09:30 open (BIG WIN ≥ +5% / FLAT ≥ +1% / LOSS < +1%; regular-session minute bars; rank = context) — replacing the top-100/top-500 rank wording; §2's principle line re-pointed at the yardstick's objective. A **user-only change under §3.1, exercised by the user himself** in the v6.1 amendment (spec SSOT); this row records the charter text catching up (found stale 2026-08-30 during the v6.1 consistency pass). Composition, decision rule, evidence bar, remit — unchanged. |
| v6.3 yardstick (RANK restored) | 2026-09-01 | user directive (*"I want to return to if we landed top one hundred gainers, big win … top five hundred, it's win and fifteen hundred flat … and stick to it"*) | **§3.1 + the §12 BAR text re-keyed to the WEEKLY RANK bar** (BIG WIN ≤100 / WIN ≤500 / FLAT 501-1500 / LOSS beyond, liquid ~$1M/day universe, ~13% chance baseline); F1's clock RESTARTED at 0/12 with a rank-keyed pass line; §2's remit principle re-pointed to the rank objective. Remit, constitution (4 items), evidence bar, decision rule, composition — UNCHANGED. |
| v6.2 yardstick + F1 freeze | 2026-08-30 | user directive (**"GO"** to the five-change verdict after two external AI audits + an audit of the author's realized trades (details private)) | **§3.1 current form → the MONEY SCOREBOARD** (policy return Mon-open→Fri-close vs SPY; BIG WIN ≥ SPY+5pp / WIN > SPY / LOSS ≤ SPY; seeded random-5 control beside it; the +2% touch demoted to a diagnostic bound to its ~64% base rate). **§3.1 also records rule F1** — the user-imposed 12-week freeze: the Board wires `logging`/`process-fix` ONLY until 12 graded v6.2 weeks exist; other approved-class proposals file to the tracker Improvement Backlog. Composition, decision rule, evidence bar — unchanged; the freeze narrows practice, not the charter's remit text (it lapses at the gate or on a user override, which restarts the clock). |
| **Board retired — the orchestrator decides** | 2026-09-13 | directive #3 (*"no need for board anymore. you decide ur self."*) | The Board of Advisors (Secretary + 5 Opus directors + Chair, the §12 Workflow, the ≥ 4/5 vote rule) is **RETIRED**; this file becomes the **Decision Charter** (file name kept for link stability). §1 governance model, §5 triggers, §6 decision rule (single decider + a mandatory written counter-case), §8 execution (record in the Decision Log FIRST), §9 formats (Decision Log + SYSTEM DECISIONS card), §10 limits and §12 (retired) rewritten; **§2 remit, §3 constitution (four items), §4 evidence bar E1-E10 and §7 auto-review UNCHANGED** — they now bind the orchestrator. Rule F1 still binds and its clock is not restarted. The Board's six sessions stay in the tracker as a historical ledger. |

**Board amendments to §8/§9 — HISTORICAL (the Board could edit its own procedure sections; its 2026-08-21 ordering fix survives in §8 step 0 as "record first"):**

| Date | Session / proposal | What changed |
|------|--------------------|--------------|
| 2026-08-21 | Session 2026-08-21, BP-2026-08-21-1 (APPROVED 5-0) | **§8 gains step 0 — the ledger block is written BEFORE any wiring is attempted**, and step 5 becomes verify-and-append rather than insert. **§9.1's template gains the `Pre-committed checks executed` and `Wiring status (U.9.4)` bullets** the live ledger already used de facto, plus the binding **session-id contract** (the ledger token equals the `stocks/board/<id>/` directory name verbatim, suffix included) and the `NOT RECORDED, acknowledged <date>` termination stub. **Driver:** the completed Board session of 2026-08-17 (`stocks/board/2026-08-17-s2/`) computed three APPROVED verdicts and ended before the record-and-wire steps — nothing was recorded, nothing was wired, and the `[HARD — §3]` self-wiring entry then made those approvals unactionable, since it requires a verdict *recorded in the ledger*. The ordering fix is the preventive half of rule L5 and is explicitly **excluded from L5's auto-revert** (condition 8). |
