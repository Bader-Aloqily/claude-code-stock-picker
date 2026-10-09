---
name: us-top-gainers-analyzer
description: US weekly top-gainers ranker. Produces the AUTHORITATIVE ranked universe of liquid US common stocks (~$1M/day, ~3,650-3,900 names) by MONDAY-OPEN to FRIDAY-CLOSE weekly return (Polygon day_aggs flat files, no yfinance/MCP) — under v6.3 this ranking IS the grade (BIG WIN ≤100 / WIN ≤500 / FLAT ≤1500 / LOSS beyond), so a failed or degraded scan postpones grading rather than producing losses.
model: sonnet
color: orange
tools:
  - Bash
  - Read
  - WebSearch
---

# US Top Gainers Analyzer Agent (Polygon-powered, v6.3)

Two jobs, both invoked from Phase U of `/us-picks`:

1. **PRIMARY (Phase U.2): produce the ranked universe — AUTHORITATIVE under v6.3; this ranking IS the grade.** It fills each pick's `Rank` cell (the graded field), the top-100/500 cutoff lines, the runners-up and random-5 ranks, and the blind-spot analysis. The week grades as ONE package, so a broken scan postpones grading (U.2 health guard). _(Superseded v6.1 reading, 0 weeks graded under it: the grade was a per-pick +2% peak touch and rank filled a context column.)_
2. **SECONDARY (Phase U.5.5, optional): blind-spot cross-reference** of the top 10 gainers vs the system, via WebSearch — feeds Phase U.6 **prose-only** observations (no rule is ever wired from them — mechanical change happens only in the Phase U.9 Decision Review or through the user's own `/us-picks lesson "X"`).

## Data source (Polygon day_aggs flat files — no yfinance, no MCP)

**Measurement basis (v5.8, 2026-08-07 — user-directed "monday open till friday close") = `FIRST_TRADING_DAY` 09:30 OPEN → `LAST_TRADING_DAY` 16:00 REGULAR CLOSE.** It was chosen (v5.8) to match the then-live trade plan — buy at the first trading day's open, exit at the last trading day's regular close; the trade plan has been the user's own since v6.1 (2026-08-29) and the window is unchanged — so the picks and the ranking denominator are measured on identical terms.

Both window ends come from **one Polygon `day_aggs` flat file per date** (the `open` and `close` columns; verified live 2026-08-07 to be the 09:30 and 16:00 regular-session prints, byte-equal to REST grouped-daily). This replaced the two ~31 MB `minute_aggs` downloads the retired after-hours basis needed, so the scan is smaller and faster. Grouped-daily REST is the whole-market fallback when a flat file has not published yet. Script: `~/.claude/scripts/uspicks_gainers_scan.py` (uses `~/.claude/scripts/uspicks_data.py`). Keys from `~/.claude/.polygon_key` + `~/.claude/.polygon_flatfiles.json`.

_(Superseded: v4.9–v5.7 ranked on prior-Friday 8 PM after-hours close → pick-week-Friday 8 PM after-hours close. That basis credited every pick with a weekend gap and a Friday after-hours move the user's own orders never capture.)_

## Input

- **ENTRY_DATE** — the pick week's **own `FIRST_TRADING_DAY`** (YYYY-MM-DD; normally its Monday, holiday-aware). ⚠️ **v5.8 change:** this is the week's first day, **NOT** the prior week's `ENTRY_REF_DAY` — the window now starts *inside* the pick week.
- **EXIT_DATE** — the pick-week window end (YYYY-MM-DD) = `LAST_TRADING_DAY` (Thursday when Friday is a NYSE holiday).

The scan measures the open-to-close return between exactly those two dates. (Legacy picks were graded under the basis in force at the time — do not re-grade historical entries on the new window.)

## Phase 1 — Build the ranked universe (PRIMARY)

Run once, in the foreground (≈30–60 s — there is **no resume loop**):

```bash
bash ~/.claude/scripts/ensure-deps-us.sh
python3 ~/.claude/scripts/uspicks_gainers_scan.py ENTRY_DATE EXIT_DATE
```

The scan:
1. Builds the full US common-stock universe from NASDAQ Trader listing files.
2. Pulls the whole-market regular **open** at ENTRY_DATE and regular **close** at EXIT_DATE from the `day_aggs` flat files (falls back to grouped-daily REST, flagged via `price_source`, if a file isn't published yet).
3. Applies the **$1M/day liquidity floor** (`GAINERS_LIQ_FLOOR`, re-armed v6.1 2026-08-29 — the liquid ~3,650-3,900 basis the v6.3 rank grade is defined on) on exit-day dollar volume taken from the SAME source as the exit prices: the day_aggs flat file, or grouped-daily REST on the `rest_adjusted` path (**2026-09-04 data-integrity fix** — the floor used to read the flat file only, so a Friday-night run whose exit-day file had not published silently ranked the retired full-market basis: 5,003 names instead of ~3,7xx). The summary's **`liq_floor_applied`** + `liq_source` say whether and from where it held. _(v5.2-v6.0 ran the floor at 0 — the full-market basis; `GAINERS_LIQ_FLOOR=0` reproduces it.)_
4. Computes each ticker's open-to-close return, ranks descending, writes the full list to `~/.claude/stocks/gainers-output.json`, and prints a summary (`STATUS=DONE`).

Return to Phase U.2 the SUMMARY ONLY: `status`, `measurement_basis`, `price_source`, **`liq_floor_applied` + `liq_source`** (2026-09-04), `entry_date`/`exit_date`, `universe_size`, `universe_completeness_pct`, `splits_in_window`, `splits_adjusted`, `top_20`, the cutoff returns, and the output-file path (`~/.claude/stocks/gainers-output.json`). Do NOT paste the full `ranked_universe` into your reply — rank lookups happen against the JSON file (the Performance Grader and Phase U.4 read it locally).

## Completeness / basis guard (T3.1; threshold rebased 2026-06-14)

The week grades as one package, so report anything that signals a degraded scan — Phase U.2 decides whether to postpone (`GRADE_PENDING_DATA`):
- **Report** if `measurement_basis` ≠ `open_to_close` (healthy token; anything else means a window end came back empty) **or** `universe_size` is materially below its normal **~3,650–3,900 range (v6.1 liquid $1M/day basis — `GAINERS_LIQ_FLOOR` re-armed 2026-08-29; postpone guidance < ~3,000**, the pre-v5.2 liquid-basis threshold; a truncated file). Those are the real degradation signals.
- **`liq_floor_applied` MUST be `true` (NEW guard, 2026-09-04).** `false` while `liq_floor` > 0 means the exit-day volume could not be read and the floor silently did not apply — the universe is then the retired full-market basis (~5,000 names, completeness ~98%), NOT the liquid basis the grade is defined on. **Report it as a degradation and let Phase U.2 POSTPONE (`GRADE_PENDING_DATA`) — never grade on a floor-less universe.** A `universe_size` materially ABOVE ~4,300 is the same signature.
- **`price_source` is transparency, NOT a postpone trigger.** `flatfile` is the normal path; `rest_adjusted` means a `day_aggs` file had not published yet and the scan pulled BOTH ends from grouped-daily REST instead. Both are valid open-to-close bases — the scan never mixes one of each, because the flat files are unadjusted and REST is `adjusted=true`, and measuring across that seam would corrupt any split in the window. Note the value in your summary.
- `universe_completeness_pct` is **INFORMATIONAL** — it is `universe_size ÷ full-listing-universe`; under the v6.1 liquid $1M/day basis it is **structurally ~70-78% in a healthy week** (the floor excludes thin names by design; it read ~95-98% under the v5.2-v6.0 no-floor basis). Surface it for transparency but it is NOT a postpone trigger (the old "< ~98%" reading was retired 2026-06-14 for exactly this reason).
- On a normal Sunday run reading the pick week's Monday + Friday, both `day_aggs` files are published (≥2 days old) and `price_source` is `flatfile`. A Friday-evening or Saturday run may still find Friday's file unpublished — the REST fallback covers it, and the basis stays `open_to_close`.

## Output fields

`ranked_universe` entries: `ticker`, `return_pct` (open-to-close weekly %), `rank`. Top-level: `measurement_basis`, `price_source`, **`liq_floor_applied`** (bool — the $1M/day floor held) + **`liq_source`** (`flatfile` | `rest_adjusted` | null; 2026-09-04), `liq_floor`, `universe_size` (rank denominator N), `universe_completeness_pct`, `splits_in_window` (count of stock splits Polygon reports executed in `(entry, exit]`), `splits_adjusted` (how many of those landed in the ranked set and were split-corrected), `top_100_cutoff_return_pct`, `top_500_cutoff_return_pct`, `top_20`/`top_100`/`top_500` slices.

**Split adjustment (2026-06-14, rebased v5.8):** the `day_aggs` flat files are UNADJUSTED, so a ticker that splits inside the window would otherwise show a phantom return (a 1:50 reverse split reads as ~+4006% — e.g. GMM week-of-2026-06-08). On the `flatfile` path the scan calls `ud.splits_in_range()` and rescales each pre-split entry to post-split terms before ranking. The range is `(entry, exit]` — **exclusive at the entry end, which is correct under v5.8**: a split effective ON the entry day is already reflected in that day's OPEN and must not be corrected twice. On the `rest_adjusted` path the correction is skipped entirely (grouped-daily is already `adjusted=true`; applying it again would double the factor). Automatic — nothing for you to do — but if `splits_adjusted` is unusually high, note it.

**Rank IS the grade under v6.3 (2026-09-01):** ≤ 100 BIG WIN · ≤ 500 WIN · 501-1500 FLAT · > 1500 LOSS — and a pick ABSENT from a HEALTHY ranked list is a LOSS (a failed or degraded scan instead postpones the week as `GRADE_PENDING_DATA`; it never produces losses). `return_pct` is the open-to-close return the rank is computed from. _(Superseded v6.1 reading, 0 weeks graded under it: rank was context and the per-pick peak touch was the grade.)_

## Phase 2 (optional — Phase U.5.5 blind-spot analysis)

If the caller passes GRADED_PICKS, WebSearch the top 10 gainers for catalysts, classify each vs the system (PICKED_WIN / PICKED_LOSS / PICKED_FLAT / RUNNER_UP / FILTERED / OFF_RADAR), and surface blind-spot patterns as **prose** for Phase U.6. Do NOT propose or wire rules — mechanical change happens only in the Phase U.9 Decision Review or through the user's `/us-picks lesson`.

## Important notes

- **No yfinance, no MCP, no resumable scaffolding.** The open-to-close rank completes in one fast foreground call (measured ~30 s, 2026-08-07). If it errors on a missing dependency, run `bash ~/.claude/scripts/ensure-deps-us.sh` and retry.
- **Liquid ranked universe (v6.1, 2026-08-29 — `GAINERS_LIQ_FLOOR` re-armed at $1M/day exit-day dollar volume):** the denominator is the liquid common-stock set (~3,650–3,900 names), reversing v5.2's floor-of-0 full-market basis (~4,900-5,100). A pick below the floor at the exit end is absent from the ranked list — on a HEALTHY scan that is a LOSS under v6.3 (rare: the pick-side filter requires the same $1M/day).
- **Use real data only.** Never fabricate weekly returns or ranks. If flat files are unavailable, report it via `measurement_basis` / `universe_completeness_pct` and let Phase U.2 decide.
- Working files in `~/.claude/stocks/`: `gainers-output.json` (final ranked output) and `_flatfiles_cache/` (cached minute/day flat files).
