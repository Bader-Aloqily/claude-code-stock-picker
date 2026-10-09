#!/usr/bin/env python3
"""
/us-picks per-pick price metrics — v6.3 (user-directed 2026-09-01).

THIS SCRIPT DOES NOT DECIDE THE GRADE. Under v6.3 the outcome is the pick's
WEEKLY RANK in the liquid ranked universe (`uspicks_gainers_scan.py` ->
gainers-output.json), assigned by Phase U.3/U.4:

    BIG WIN  rank <= 100
    WIN      rank <= 500
    FLAT     rank 501-1500
    LOSS     rank > 1500, or absent from a HEALTHY ranked universe

What this script returns is the per-pick PRICE record that the grade is reported
alongside: `close_return_pct` (the Mon-open -> Fri-close policy return),
`peak_return_pct` (the highest intraweek regular-session price vs the entry open),
`entry_open`, `exit_close`, `week_high`, `peak_source`, `window_ok`.

`peak_label` (below) is a PRICE-BASED LABEL ONLY, kept because the +2% touch is
still reported on every pick: a trader exiting on a tight trail into
intraweek strength monetizes the peak, and the gap
between "ranked well" and "paid well" must stay visible. It is NOT the outcome
and must never be written into a tracker Outcome cell.

The raw `peak_return_pct` is always recorded, so ANY threshold (0.5 / 1 / 1.5 / 2%)
stays re-readable later without re-running a thing.

ERA HISTORY (never re-grade a closed week onto a later basis): rank tiers
v4.4-v6.0; +2% peak-touch tiers v6.1 (2026-08-29 -> 08-30, 0 weeks graded);
policy return vs SPY v6.2 (08-30 -> 09-01, 0 weeks graded); rank restored v6.3.
Measured honestly at the v6.3 restore: across 67 graded picks 15% won on rank
while 80% touched +2% - the rank bar is the harder and more falsifiable one
(~13% by chance), and it is the bar the user chose.

PEAK SOURCE: minute bars (regular session 09:30-15:59 ET), not daily highs, so an
extended-hours print can never manufacture a peak the user could not have traded.
Falls back to daily-bar highs only if minute data is unavailable, and says which
it used in `peak_source`.

Also returns entry open, exit close and the close return as DISPLAY CONTEXT.

Usage: python3 uspicks_grade.py TICKER STOP ENTRY_DATE EXIT_DATE
       (STOP is accepted for backward compatibility and may be NA - stops are the
        user's own business under v6.1 and never affect a grade.)
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uspicks_data as ud


def main():
    if len(sys.argv) < 5:
        print('usage: uspicks_grade.py TICKER STOP ENTRY_DATE EXIT_DATE', file=sys.stderr)
        sys.exit(2)
    ticker = sys.argv[1].upper()
    try:
        stop = float(sys.argv[2])
    except ValueError:
        stop = None
    entry_date, exit_date = sys.argv[3], sys.argv[4]

    # One adjusted=true request covers the whole window: first bar = entry day,
    # last bar = exit day. Same bars feed the intraweek low/high, so the peak and
    # the stop check are measured over exactly the graded window (v5.8: the entry
    # day is now INSIDE the window, so its bar is kept — the old basis dropped a
    # leading prior-Friday bar that is no longer requested).
    bars = ud.daily_aggs(ticker, entry_date, exit_date)

    # Date guard: bars[0] must actually BE the entry day and bars[-1] the exit day.
    # A halted / newly-listed / delisted name can return a range that silently starts
    # or ends on a different session — grading off that bar would be a wrong number
    # that looks right. Null the affected end instead, so Phase U.3 marks the pick
    # GRADE_PENDING_DATA rather than mis-grading it.
    def _bar_date(b):
        return ud._to_et(b['t']).strftime('%Y-%m-%d')

    first_ok = bool(bars) and _bar_date(bars[0]) == entry_date
    last_ok = bool(bars) and _bar_date(bars[-1]) == exit_date
    entry_open = bars[0].get('o') if first_ok else None
    exit_close = bars[-1].get('c') if last_ok else None

    out = {
        'ticker': ticker, 'entry_date': entry_date, 'exit_date': exit_date,
        'measurement_basis': 'open_to_close',
        'entry_open': round(entry_open, 2) if entry_open else None,
        'exit_close': round(exit_close, 2) if exit_close else None,
        'close_return_pct': round((exit_close / entry_open - 1) * 100, 2)
        if (entry_open and exit_close and entry_open > 0) else None,
        'window_ok': bool(first_ok and last_ok),
        'first_bar_date': _bar_date(bars[0]) if bars else None,
        'last_bar_date': _bar_date(bars[-1]) if bars else None,
    }

    lows = [b['l'] for b in bars if 'l' in b]
    highs = [b['h'] for b in bars if 'h' in b]
    out['week_low'] = round(min(lows), 2) if lows else None
    out['stop_hit'] = bool(stop and lows and min(lows) <= stop)
    out['trading_days'] = len(bars)

    # ---- price metrics + peak diagnostic (v6.3: the GRADE is rank, Phase U.3/U.4) ----
    # The peak is taken from MINUTE bars, regular session only (09:30-15:59 ET),
    # so an extended-hours print can never manufacture a high the user could not
    # have traded. Daily highs are the documented fallback only.
    peak_px, peak_source = None, None
    if entry_open:
        mins = []
        for b in bars:
            d = _bar_date(b)
            try:
                for mb in ud.minute_bars(ticker, d):
                    ts = mb.get('t')
                    if ts is None or mb.get('h') is None:
                        continue
                    et = ((ts // 60000) - 240) % 1440      # ET = UTC-4 (EDT)
                    if 570 <= et < 960:                     # 09:30 .. 15:59
                        mins.append(mb['h'])
            except Exception:
                continue
        if mins:
            peak_px, peak_source = max(mins), 'minute_regular_session'
        elif highs:
            peak_px, peak_source = max(highs), 'daily_high_fallback'

    out['week_high'] = round(peak_px, 2) if peak_px else (
        round(max(highs), 2) if highs else None)
    out['peak_source'] = peak_source
    pk = round((peak_px / entry_open - 1) * 100, 2) \
        if (peak_px and entry_open) else None
    out['peak_return_pct'] = pk

    # v6.3: the GRADE is the weekly rank, assigned by Phase U.3/U.4 from
    # gainers-output.json. This script emits NO `outcome` field on purpose -
    # a price-derived `outcome` key here was read as the grade under v6.1/v6.2
    # and must not reappear. `peak_label` is the +2%-touch diagnostic's label,
    # reported only beside the week's measured base rate.
    if pk is None:
        out['peak_label'] = None
    elif pk >= 5.0:
        out['peak_label'] = 'touched +5%'
    elif pk >= 2.0:
        out['peak_label'] = 'touched +2%'
    elif pk >= 1.0:
        out['peak_label'] = 'touched +1%'
    else:
        out['peak_label'] = 'no +1% touch'
    out['measurement_basis'] = 'open_to_close_return_plus_peak'
    out['grade_source'] = 'weekly_rank (gainers-output.json) - NOT this script'

    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
