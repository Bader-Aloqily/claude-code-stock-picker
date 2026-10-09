#!/usr/bin/env python3
"""
/us-picks v6.1 TRADE SIMULATOR — the grading engine for the +2% / 1%-trail plan.

OBJECTIVE (2026-08-29): simulate a simple trailing-stop plan: buy at the
week's open and, once the price is up 2%, follow it with a 1% trailing stop.

THE PLAN THIS SIMULATES:
    1. BUY at the FIRST_TRADING_DAY 09:30 open.
    2. When price touches +2%, arm a 1% TRAILING stop that follows the running
       peak (so the floor is ~+1% and rises with it).
    3. Exit when the trail is hit. If +2% is never reached, hold to the
       LAST_TRADING_DAY regular close.
    (No hard stop - see HARD_STOP_PCT below for why one is not used.)

WHY MINUTE BARS (this is the whole point):
    A daily-bar simulation cannot know whether the day's HIGH came before or
    after its LOW, so it silently assumes the favourable ordering. Measured on
    152 picks + runners-up on 2026-08-29, that bias was worth +1.97pp of mean
    return per trade: the daily-bar run reported +2.15% mean, the minute-bar run
    +0.18%. Minute bars give the true path, so the trail arms and stops out in
    the real order. NEVER grade this plan on daily bars.

WHAT THE 152-TRADE RUN ACTUALLY FOUND (2026-08-29):
    Trades that ARM behave exactly as designed - 123 of 123 profitable, mean
    +2.02%, minimum +1.0%. The whole drag is the 19% that never reach +2% and
    therefore have no exit: mean -7.66%, worst -14.3%. Overall +0.18% mean at an
    82% win rate.

    A HARD STOP DOES NOT FIX THAT, and this is the correction of an earlier
    error: a first pass capped unarmed losses post-hoc and reported -1% lifting
    the mean to +1.47%. Re-simulated INSIDE the real minute path, a -1% stop cuts
    the ARM RATE from 81% to 28%, because a 1% band sits far inside these names'
    normal noise - it stops you out of the winners before they arm. Sweep:
    none +0.18% (81% armed) | -1% -0.18% (28%) | -2% -0.16% (45%) |
    -3% -0.11% (57%) | -5% -0.18% (66%) | -8% -0.02% (77%). No width wins.
    The real problem is selection, not the exit.

NOTE ON SCOPE (user-directed 2026-08-29):
    "Don't worry about when I would buy and when I will sell. That is my thing
     to do... I will put it as one percent trail or half percent trail depending
     on how volatile the stock is."
    So this file is a REFERENCE TOOL ONLY. It grades nothing. The live grade is
    the +2% PEAK TOUCH in uspicks_grade.py, which models no exit at all.

HONEST LIMITATION (stated, not hidden):
    A trailing stop becomes a MARKET order when triggered, so a real fill in a
    fast drop is worse than the trail price this simulator assumes. Results are
    therefore mildly optimistic on thin or gapping names. Within-minute ordering
    is also unknown, but at 1-minute granularity that is negligible.

Usage:
    python3 uspicks_trade_sim.py TICKER ENTRY_DATE EXIT_DATE [--json]
    python3 uspicks_trade_sim.py --selftest
"""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uspicks_data as ud

ARM_PCT = 0.02        # arm the trail once price touches +2%
TRAIL_PCT = 0.01      # 1% trailing stop, follows the running peak
# HARD STOP: OFF BY DEFAULT. Measured 2026-08-29 inside the real minute path, a
# -1% stop cut the arm rate from 81% to 28% (a 1% band sits far inside these names'
# normal noise) and NO width tested (1/2/3/5/8%) beat no stop at all. An earlier
# daily-bar estimate suggesting -1% helped was WRONG: it capped losses post-hoc
# without checking that the stop fires EARLIER IN TIME than the arm. Pass
# --hard-stop PCT to explore it; the simulated plan has no hard stop.
HARD_STOP_PCT = 0.0

BIG_WIN_PCT = 5.0     # realized >= +5%

NYSE_HOLIDAYS = {
    '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', '2026-05-25',
    '2026-06-19', '2026-07-03', '2026-09-07', '2026-11-26', '2026-12-25',
    '2027-01-01', '2027-01-18', '2027-02-15', '2027-03-26', '2027-05-31',
    '2027-06-18', '2027-07-05', '2027-09-06', '2027-11-25', '2027-12-24',
}


def session_days(entry_date, exit_date):
    d0 = datetime.strptime(entry_date, '%Y-%m-%d')
    d1 = datetime.strptime(exit_date, '%Y-%m-%d')
    out, d = [], d0
    while d <= d1:
        s = d.strftime('%Y-%m-%d')
        if d.weekday() < 5 and s not in NYSE_HOLIDAYS:
            out.append(s)
        d += timedelta(days=1)
    return out


def regular_session(bars):
    """Keep 09:30-15:59 ET. A retail stop does not execute in extended hours."""
    out = []
    for b in bars:
        ts = b.get('t')
        if ts is None:
            continue
        mins = ((ts // 60000) - 240) % 1440       # ET = UTC-4 (EDT)
        if 570 <= mins < 960:
            out.append(b)
    return out


def simulate(ticker, entry_date, exit_date):
    days = session_days(entry_date, exit_date)
    seq = []
    for d in days:
        try:
            seq.extend(regular_session(ud.minute_bars(ticker, d)))
        except Exception:
            continue
    seq.sort(key=lambda b: b['t'])
    if not seq:
        return {'ticker': ticker, 'window_ok': False,
                'reason': 'no minute bars in window'}

    entry = seq[0].get('o')
    if not entry or entry <= 0:
        return {'ticker': ticker, 'window_ok': False, 'reason': 'no entry open'}

    arm_px = entry * (1 + ARM_PCT)
    hard_stop = entry * (1 - HARD_STOP_PCT) if HARD_STOP_PCT else None
    armed = False
    peak = entry
    exit_px = None
    how = None
    arm_ts = None

    for b in seq:
        h, l = b.get('h'), b.get('l')
        if h is None or l is None:
            continue
        if not armed:
            # Conservative ordering: inside one minute, test the DOWNSIDE first.
            # If both the hard stop and the arm level are touched in the same
            # minute we take the stop — the pessimistic reading.
            if hard_stop is not None and l <= hard_stop:
                exit_px, how = hard_stop, 'hard_stop'
                break
            if h >= arm_px:
                armed = True
                arm_ts = b['t']
                peak = max(peak, h)
                if l <= peak * (1 - TRAIL_PCT):
                    exit_px, how = peak * (1 - TRAIL_PCT), 'trail_same_minute'
                    break
        else:
            peak = max(peak, h)
            trail = peak * (1 - TRAIL_PCT)
            if l <= trail:
                exit_px, how = trail, 'trail'
                break

    if exit_px is None:
        exit_px = seq[-1].get('c')
        how = 'held_to_close_armed' if armed else 'held_to_close_unarmed'

    ret = (exit_px / entry - 1) * 100.0
    if ret >= BIG_WIN_PCT:
        outcome = 'BIG WIN'
    elif armed:
        outcome = 'WIN'
    else:
        outcome = 'LOSS'

    return {
        'ticker': ticker,
        'window_ok': True,
        'entry_date': entry_date, 'exit_date': exit_date,
        'sessions': len(days), 'minute_bars': len(seq),
        'entry_open': round(entry, 4),
        'arm_level': round(arm_px, 4),
        'hard_stop': round(hard_stop, 4) if hard_stop else None,
        'armed': armed,
        'armed_at': (datetime.utcfromtimestamp(arm_ts / 1000) - timedelta(hours=4)
                     ).strftime('%Y-%m-%d %H:%M ET') if arm_ts else None,
        'peak_price': round(peak, 4),
        'peak_return_pct': round((peak / entry - 1) * 100, 2),
        'exit_price': round(exit_px, 4),
        'exit_reason': how,
        'realized_return_pct': round(ret, 2),
        'outcome': outcome,
        'measurement_basis': 'minute_path_2pct_arm_1pct_trail',
        'note': ('Trailing stops fill as market orders, so a real fill in a fast '
                 'drop is worse than this trail price.'),
    }


def selftest():
    """Replays the three cases the 2026-08-29 study established."""
    cases = [
        ('DK', '2026-08-24', '2026-08-28', 'armed (peak +4.4%)'),
        ('HMY', '2026-08-24', '2026-08-28', 'never armed (peak +0.6%)'),
        ('NVT', '2026-08-03', '2026-08-07', 'armed (peak +10.2%)'),
    ]
    ok = True
    for tk, a, b, expect in cases:
        r = simulate(tk, a, b)
        got = 'armed' if r.get('armed') else 'never armed'
        flag = 'OK' if (('never' in expect) == (not r.get('armed'))) else 'MISMATCH'
        if flag != 'OK':
            ok = False
        print('  %-5s %-22s -> %-11s %+6.2f%%  %-22s %s'
              % (tk, expect, got, r.get('realized_return_pct', 0),
                 r.get('exit_reason', '?'), flag))
    print('selftest:', 'PASS' if ok else 'FAIL')
    return ok


def main():
    if '--selftest' in sys.argv:
        selftest()
        return 0
    if '--hard-stop' in sys.argv:
        i = sys.argv.index('--hard-stop')
        globals()['HARD_STOP_PCT'] = float(sys.argv[i + 1]) / 100.0
        del sys.argv[i:i + 2]
    if len(sys.argv) < 4:
        print('usage: uspicks_trade_sim.py TICKER ENTRY_DATE EXIT_DATE [--json]',
              file=sys.stderr)
        return 2
    r = simulate(sys.argv[1].upper(), sys.argv[2], sys.argv[3])
    print(json.dumps(r, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
