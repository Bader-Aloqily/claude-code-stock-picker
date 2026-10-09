#!/usr/bin/env python3
"""
/us-picks Top Gainers Analyzer — Polygon OPEN-to-CLOSE weekly rank (grading authority).

Ranks the full US common-stock universe by the weekly return measured
MONDAY OPEN -> FRIDAY REGULAR CLOSE (v5.8, 2026-08-07, user-directed: "i need the
grading/update of the stocks to be from monday open till friday close"), matching
what the trade plan actually does — the Entry Plan buys at the FIRST_TRADING_DAY
open and the Sell Plan exits at the LAST_TRADING_DAY regular close. /us-picks update
uses the resulting ranks to classify each pick BIG WIN / WIN / FLAT / LOSS.

Superseded (v4.9 -> v5.8): the window was prior-Friday 8 PM after-hours close ->
pick-week-Friday 8 PM after-hours close. That basis credited the weekend gap and the
Friday after-hours move to every pick, neither of which the user's own orders capture.

Method:
  entry_date = the pick week's FIRST_TRADING_DAY (normally Monday) — its 09:30 OPEN.
  exit_date  = the pick week's LAST_TRADING_DAY (normally Friday) — its 16:00 CLOSE.
  Both ends come from ONE day_aggs flat file per date (small; replaced the two
  ~31 MB minute_aggs downloads the after-hours basis needed). REST grouped-daily is
  the whole-market fallback when a flat file has not published yet.
  return% = (close_exit / open_entry - 1) * 100 ; rank by return desc.
  Split-adjust: flat files are UNADJUSTED, so a ticker that split in (entry,exit]
  reads as a phantom mover; ud.splits_in_range() rescales the entry to post-split
  terms (a 1:50 reverse split -> entry x50) before the return is computed. The REST
  fallback requests adjusted=true and is ALREADY split-safe, so the correction is
  applied ONLY on the flat-file path — and BOTH ends always come from the SAME
  source, never one of each (mixing adjusted with unadjusted would break the basis).

Output (stdout = summary; full ranked list saved to ~/.claude/stocks/gainers-output.json):
  status, measurement_basis, price_source, liq_floor_applied, liq_source,
  entry_date, exit_date, universe_size,
  universe_completeness_pct, splits_in_window, splits_adjusted,
  top_100/500/20 + cutoff returns, ranked_universe[...].

Run: python3 ~/.claude/scripts/uspicks_gainers_scan.py ENTRY_DATE EXIT_DATE   (YYYY-MM-DD)
     Both dates MUST be trading days — the orchestrator derives them holiday-aware
     (Phase 0.3 FIRST_TRADING_DAY / LAST_TRADING_DAY via WEEK_OVERRIDE). NOTE the
     v5.8 change: ENTRY_DATE is the week's OWN first trading day, NOT the prior
     week's ENTRY_REF_DAY. A non-trading date has no flat file -> the scan falls
     back to REST and, failing that, the U.2 guard fires.
Env: GAINERS_LIQ_FLOOR (min exit-day dollar volume; default 1_000_000 = the v6.1
     LIQUID basis, ~3,650-3,900 names — re-armed 2026-08-29 with the v4.6
     restore. Set 0 to reproduce the v5.2-v6.0 full-market basis, ~4,900-5,100.)
"""
import os, sys, json, time
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uspicks_data as ud
from uspicks_price_scan import build_universe

STOCKS_DIR = os.path.expanduser('~/.claude/stocks')
OUTPUT_FILE = os.path.join(STOCKS_DIR, 'gainers-output.json')
# v6.1 (2026-08-29, user-directed v4.6 restore): the grading universe is the
# LIQUID basis again (>= $1M/day exit-day dollar volume, ~3,750-3,900 names), as
# it was in the May v4.6 era. v5.2's floor-of-0 full-market basis (~5,000) is
# retired. Set GAINERS_LIQ_FLOOR=0 to reproduce a v5.2-v6.0-era rank.
LIQ_FLOOR = float(os.environ.get('GAINERS_LIQ_FLOOR', '1000000'))

# v6.1: the per-PICK grade is the intraday peak (uspicks_grade.py), but the
# RANKED UNIVERSE stays on the close basis — peak-ranking was MEASURED AND
# REJECTED 2026-08-29 (it lifts the bar with the picks and rewards
# spike-and-crash). Default MEASURE='close'; GAINERS_MEASURE=peak re-arms the
# rejected path for one-off comparisons only.
# v6.1 FINAL: the ranked universe is CONTEXT ONLY — WIN is decided by the per-pick
# +2% PEAK TOUCH in uspicks_grade.py, not by rank. The rank is therefore computed on
# the plain CLOSE basis (comparable to every prior era). Peak-RANK was built and
# tested on 2026-08-29 and REJECTED: ranking the whole universe on peak lifts the bar
# with the picks (top-500 went +4.68% -> +8.11%), produced the identical 0W/1F/4L
# outcome, and DEMOTED the one pick that worked (DK #796 -> #1133) because it rewards
# spike-and-crash over grind-and-hold. Set GAINERS_MEASURE=peak to reproduce it.
MEASURE = os.environ.get('GAINERS_MEASURE', 'close').strip().lower()


def open_close_map(date_str):
    """({ticker: (regular_open, regular_close)}, basis_label) for the whole market.

    day_aggs flat file (UNADJUSTED — needs the split correction) -> grouped-daily
    REST (adjusted=true — already split-safe). v5.8 grading basis."""
    try:
        m = ud.regular_open_close_all(date_str)
        if m:
            return m, 'flatfile'
    except Exception as e:
        print('  regular_open_close_all(%s) failed: %s' % (date_str, e), file=sys.stderr)
    g = ud.grouped_daily(date_str)
    return ({t: (b['o'], b['c']) for t, b in g.items() if b.get('o') and b.get('c')},
            'rest_adjusted')


def trading_days(entry_date, exit_date):
    """Calendar walk entry..exit, weekdays only (a holiday simply returns no bars)."""
    d0 = datetime.strptime(entry_date, '%Y-%m-%d')
    d1 = datetime.strptime(exit_date, '%Y-%m-%d')
    out, d = [], d0
    while d <= d1:
        if d.weekday() < 5:
            out.append(d.strftime('%Y-%m-%d'))
        d += timedelta(days=1)
    return out


def peak_map(entry_date, exit_date):
    """({ticker: max intraday HIGH across the window}, n_sessions_used).

    v6.1 peak basis. One grouped-daily call per weekday (~5/week); a date that
    returns nothing (holiday) is skipped, so this is holiday-safe by construction.
    grouped_daily requests adjusted=true, so this path is already split-safe.
    """
    highs, used = {}, 0
    for ds in trading_days(entry_date, exit_date):
        try:
            g = ud.grouped_daily(ds)
        except Exception as e:
            print('  grouped_daily(%s) failed: %s' % (ds, e), file=sys.stderr)
            continue
        if not g:
            continue
        used += 1
        for tk, b in g.items():
            h = b.get('h')
            if h and (highs.get(tk) is None or h > highs[tk]):
                highs[tk] = h
    return highs, used


def main():
    if len(sys.argv) < 3:
        print('usage: uspicks_gainers_scan.py ENTRY_DATE EXIT_DATE (YYYY-MM-DD)', file=sys.stderr)
        sys.exit(2)
    entry_date, exit_date = sys.argv[1], sys.argv[2]
    t0 = time.time()

    universe = build_universe()
    print('universe: %d common stocks' % len(universe), file=sys.stderr)

    # v5.8: entry = FIRST_TRADING_DAY 09:30 OPEN, exit = LAST_TRADING_DAY 16:00 CLOSE.
    entry_map, src_entry = open_close_map(entry_date)
    exit_map, src_exit = open_close_map(exit_date)
    # Both ends MUST share a source: the flat files are unadjusted and the REST aggs
    # are adjusted=true, so one of each would measure the return across a split-basis
    # seam. If they disagree, pull BOTH from REST (the common, already-adjusted one).
    if src_entry != src_exit:
        print('  source mismatch (%s / %s) -> forcing REST at both ends'
              % (src_entry, src_exit), file=sys.stderr)
        g_e, g_x = ud.grouped_daily(entry_date), ud.grouped_daily(exit_date)
        entry_map = {t: (b['o'], b['c']) for t, b in g_e.items() if b.get('o') and b.get('c')}
        exit_map = {t: (b['o'], b['c']) for t, b in g_x.items() if b.get('o') and b.get('c')}
        src_entry = src_exit = 'rest_adjusted'
    entry_px = {t: v[0] for t, v in entry_map.items()}   # OPEN at the entry end
    close_px = {t: v[1] for t, v in exit_map.items()}    # CLOSE at the exit end

    # ---- v6.1 (2026-08-29, user-directed): the ranked value is the week's
    # INTRADAY PEAK measured from the entry OPEN, not the exit close. The whole
    # universe is ranked on the same basis, so the top-500 bar rises with it —
    # peak grading is NOT a free upgrade, it is a different question ("how far
    # did it run at any point" instead of "where did it finish").
    peak_px, n_sessions = ({}, 0)
    if MEASURE == 'peak':
        peak_px, n_sessions = peak_map(entry_date, exit_date)
        print('peak basis: %d sessions, %d tickers with a high'
              % (n_sessions, len(peak_px)), file=sys.stderr)
    exit_px = peak_px if MEASURE == 'peak' else close_px

    if MEASURE == 'peak':
        basis = 'open_to_peak' if (entry_px and exit_px) else 'incomplete'
    else:
        basis = 'open_to_close' if (entry_px and exit_px) else 'incomplete'
    print('basis=%s price_source=%s (entry n=%d, exit n=%d)'
          % (basis, src_entry, len(entry_px), len(exit_px)), file=sys.stderr)

    # liquidity floor (v6.1 2026-08-29: GAINERS_LIQ_FLOOR re-armed at $1M/day — the
    # liquid ~3,650-3,900 basis the v6.3 rank grade is DEFINED on; v5.2-v6.0 ran it
    # at 0). Filter on exit-day dollar volume (volume * close) taken from the SAME
    # source that supplied the exit prices: the day_aggs flat file on the flatfile
    # path, grouped-daily REST (which carries `v`) on the rest_adjusted path.
    # 2026-09-04 DATA-INTEGRITY FIX: this block used to read the flat file ONLY, so on
    # a Friday-night run (exit-day file not yet published) the floor silently
    # skipped and the "liquid" rank quietly became the retired full-market basis
    # (measured on the first v6.3 grading run: 5,003 names instead of ~3,7xx).
    # The output now states whether the floor applied (`liq_floor_applied`) and
    # from which source (`liq_source`); Phase U.2 postpones when it did not.
    liq_ok, liq_source = None, None
    if LIQ_FLOOR > 0:
        liq_ok = set()
        try:
            if src_exit == 'flatfile':
                path = ud.download_flatfile('day_aggs', exit_date)
                for parts, idx in ud._iter_flatfile(path):
                    try:
                        if float(parts[idx['volume']]) * float(parts[idx['close']]) >= LIQ_FLOOR:
                            liq_ok.add(parts[idx['ticker']])
                    except Exception:
                        pass
                liq_source = 'flatfile'
            else:
                g_x = ud.grouped_daily(exit_date)
                for t, b in g_x.items():
                    try:
                        if float(b.get('v') or 0) * float(b.get('c') or 0) >= LIQ_FLOOR:
                            liq_ok.add(t)
                    except Exception:
                        pass
                liq_source = 'rest_adjusted'
            if not liq_ok:
                raise RuntimeError('no exit-day volume rows from %s' % liq_source)
        except Exception as e:
            print('  liquidity floor unavailable (%s) — NOT applied' % e, file=sys.stderr)
            liq_ok, liq_source = None, None
    liq_floor_applied = bool(LIQ_FLOOR > 0 and liq_ok is not None)
    if LIQ_FLOOR <= 0:
        print('liquidity floor: OFF (GAINERS_LIQ_FLOOR=0 — full-market basis)', file=sys.stderr)
    elif liq_floor_applied:
        print('liquidity floor: applied from %s (%d names >= $%d/day)'
              % (liq_source, len(liq_ok), int(LIQ_FLOOR)), file=sys.stderr)
    else:
        print('liquidity floor: NOT APPLIED — universe is the full market, not the liquid basis',
              file=sys.stderr)

    # Split adjustment: the day_aggs FLAT FILES are UNADJUSTED, so a ticker that
    # split between entry and exit shows a PHANTOM return (a 1:50 reverse split
    # reads as ~+5000%; a forward split as a deep fake loss). Express each pre-split
    # entry in post-split terms so both window ends share a basis.
    # splits_in_range is (entry_date, exit_date] — EXCLUSIVE at the entry end, which
    # is exactly right under v5.8: a split effective ON the entry day is already
    # reflected in that day's OPEN and must not be corrected a second time.
    # Skipped on the REST path (grouped_daily requests adjusted=true and is already
    # split-safe — correcting it again would double-apply the factor).
    # (uspicks_grade.py's per-pick aggs also request adjusted=true -> split-safe.)
    # On the PEAK path the highs come from grouped_daily (adjusted=true), so the
    # exit end is already split-safe; the entry OPEN, however, still comes from the
    # unadjusted flat file, so the correction is still required there.
    split_factor = ud.splits_in_range(entry_date, exit_date) \
        if src_entry == 'flatfile' else {}

    rows = []
    n_split_adj = 0
    for t in universe:
        pe, px = entry_px.get(t), exit_px.get(t)
        if not pe or not px or pe <= 0:
            continue
        if liq_ok is not None and t not in liq_ok:
            continue
        f = split_factor.get(t)
        if f:
            pe = pe * f
            n_split_adj += 1
        cx = close_px.get(t)
        cr = round((cx / pe - 1) * 100, 2) if cx else None
        rows.append((t, round((px / pe - 1) * 100, 2), cr))
    rows.sort(key=lambda r: r[1], reverse=True)
    ranked = [{'ticker': t, 'return_pct': r, 'close_return_pct': cr, 'rank': i + 1}
              for i, (t, r, cr) in enumerate(rows)]
    N = len(ranked)

    def cutoff(n):
        return ranked[n - 1]['return_pct'] if N >= n else None

    out = {
        'status': 'DONE',
        'measurement_basis': basis,          # 'open_to_close' healthy (default MEASURE='close'); 'open_to_peak' only under GAINERS_MEASURE=peak (rejected path)
        'measure_mode': MEASURE,             # 'peak' (v6.1 default) | 'close'
        'peak_sessions_used': n_sessions,
        'liq_floor': LIQ_FLOOR,
        'liq_floor_applied': liq_floor_applied,   # 2026-09-04: False = the floor silently did not apply (full-market basis) -> Phase U.2 POSTPONES
        'liq_source': liq_source,               # 'flatfile' | 'rest_adjusted' | None
        'price_source': src_entry,           # 'flatfile' | 'rest_adjusted' (both valid)
        'entry_date': entry_date, 'exit_date': exit_date,
        'universe_size': N,
        'universe_completeness_pct': round(100.0 * N / max(len(universe), 1), 1),
        'splits_in_window': len(split_factor),
        'splits_adjusted': n_split_adj,
        'top_100_cutoff_return_pct': cutoff(100),
        'top_500_cutoff_return_pct': cutoff(500),
        'top_20': ranked[:20], 'top_100': ranked[:100], 'top_500': ranked[:500],
        'ranked_universe': ranked,
        'elapsed_sec': round(time.time() - t0, 1),
    }
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(out, f)
    summary = dict(out)
    summary['ranked_universe'] = '<%d rows in %s>' % (N, OUTPUT_FILE)
    summary['top_500'] = '<500 rows in file>'
    summary['top_100'] = '<100 rows in file>'
    print('STATUS=DONE', file=sys.stderr)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
