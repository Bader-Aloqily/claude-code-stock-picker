#!/usr/bin/env python3
"""
/us-picks CONTROL ARMS helper — v6.3 (rank bar, user-directed 2026-09-01;
first wired as the v6.2 money-scoreboard helper 2026-08-30).

Two modes:

  draw  --week-start YYYY-MM-DD
      Runs on every PICK run (Phase 6.0 Part A4), after the eligible set is final.
      Draws the week's RANDOM-5 control — 5 tickers, SEEDED (sha256 of the week
      key, reproducible forever) — from price-analyzer-output.json rows with
      eligible == true, minus the Sharia vice blacklist. Appends one row to
      ~/.claude/stocks/us-controls.jsonl and prints it. The draw is made and
      LOGGED before outcomes exist, so the control can never be cherry-picked.

  grade --week-start YYYY-MM-DD --entry-date YYYY-MM-DD --exit-date YYYY-MM-DD
      Runs on every GRADING run (Phase U.3a). For the logged RANDOM-5 it
      computes the v6.3 GRADE — each control ticker's WEEKLY RANK from
      gainers-output.json and its outcome on the same bar as the picks
      (BIG WIN <=100 / WIN <=500 / FLAT <=1500 / LOSS beyond) — plus, as
      reported context, the POLICY return (buy ENTRY_DATE 09:30 open, sell
      EXIT_DATE regular close — grouped-daily auction prints, adjusted), the
      daily-high peak vs the entry open, and SPY's same-window return.
      `random5_top500_rate` is the arm rule F1's pass line reads. ALSO computes the week's +1/+2/+5%
      PEAK-TOUCH BASE RATES across the frozen eligible universe (the L4 snapshot
      stocks/_universe/universe-features-<week>.jsonl; daily-high basis — a
      slightly optimistic bound vs minute bars, labeled as such). Appends a
      result row to us-controls.jsonl and prints JSON.

Fail-soft: exits 0 always; a missing input prints a WARN and writes nothing.
Never a scoring input — controls and base rates are measurement, not selection.
"""
import os, sys, json, time, hashlib, random, re, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uspicks_data as ud

STOCKS = os.path.expanduser('~/.claude/stocks')
CTRL = os.path.join(STOCKS, 'us-controls.jsonl')
BLACKLIST = os.path.expanduser(
    '~/.claude/skills/us-stocks-memory/references/sharia-blacklist.md')


def vice_tickers():
    out = set()
    try:
        for line in open(BLACKLIST, encoding='utf-8'):
            m = re.match(r'^([A-Z][A-Z0-9.\-]{0,6})\b', line.strip())
            if m:
                out.add(m.group(1))
    except Exception as e:
        print('WARN: blacklist unreadable (%s) — drawing without it' % e)
    return out


def draw(week_start):
    src = os.path.join(STOCKS, 'price-analyzer-output.json')
    try:
        raw = json.load(open(src))
    except Exception as e:
        print('CTRL: WARN no scan output (%s) — no draw' % e)
        return
    # price-analyzer-output.json is a LIST of ticker rows; tolerate a dict
    # wrapper too. (Fixed 2026-08-31: the previous form called .get() on the
    # list and aborted every draw — this script had never executed since it
    # was wired 2026-08-30.)
    rows = raw.get('results', []) if isinstance(raw, dict) else raw
    vice = vice_tickers()
    pool = sorted({r['ticker'] for r in rows
                   if r.get('eligible') and r.get('ticker')
                   and r['ticker'].upper() not in vice})
    if len(pool) < 5:
        print('CTRL: WARN eligible pool %d < 5 — no draw' % len(pool))
        return
    # one draw per week, ever — a re-run returns the logged draw
    for line in open(CTRL) if os.path.exists(CTRL) else []:
        try:
            d = json.loads(line)
            if d.get('week_start') == week_start and d.get('type') == 'random5':
                print('CTRL: random-5 for %s already drawn: %s'
                      % (week_start, ' '.join(d['tickers'])))
                return
        except Exception:
            pass
    seed = int(hashlib.sha256(('us-picks-random5-' + week_start).encode())
               .hexdigest(), 16) % (2 ** 32)
    rng = random.Random(seed)
    picks = rng.sample(pool, 5)
    row = {'type': 'random5', 'week_start': week_start, 'tickers': picks,
           'seed': seed, 'pool_size': len(pool),
           'drawn_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    with open(CTRL, 'a') as f:
        f.write(json.dumps(row) + '\n')
    print('CTRL: random-5 drawn for %s (seed %d, pool %d): %s'
          % (week_start, seed, len(pool), ' '.join(picks)))


def _week_days(entry_date, exit_date):
    import datetime
    d0 = datetime.date.fromisoformat(entry_date)
    d1 = datetime.date.fromisoformat(exit_date)
    days, d = [], d0
    while d <= d1:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return days


def _ranks():
    """v6.3: {ticker: rank} + universe_size from the run's ranked universe.

    gainers-output.json is written by uspicks_gainers_scan.py in Phase U.2,
    immediately before this runs, and is the SAME file the picks are graded
    from — so the control arm is judged on identical data, not a re-scan.
    Fail-soft: an unreadable file yields no ranks and the control still
    reports its price context.
    """
    path = os.path.join(STOCKS, 'gainers-output.json')
    try:
        with open(path, encoding='utf-8') as f:
            g = json.load(f)
        ranked = g.get('ranked_universe') or []
        return ({r['ticker']: r['rank'] for r in ranked if r.get('ticker')},
                g.get('universe_size'))
    except Exception as e:
        print('CTRL: WARN ranked universe unavailable (%s) — control graded on '
              'price context only' % e)
        return {}, None


def _outcome(rank):
    """The v6.3 bar — identical to Phase U.3/U.4's classification."""
    if rank is None:
        return None            # absent here means UNKNOWN, never an auto-LOSS
    if rank <= 100:
        return 'BIG WIN'
    if rank <= 500:
        return 'WIN'
    if rank <= 1500:
        return 'FLAT'
    return 'LOSS'


def grade(week_start, entry_date, exit_date):
    # the logged draw
    tickers = None
    for line in open(CTRL) if os.path.exists(CTRL) else []:
        try:
            d = json.loads(line)
            if d.get('week_start') == week_start and d.get('type') == 'random5':
                tickers = d['tickers']
        except Exception:
            pass
    days = _week_days(entry_date, exit_date)
    daily = {}
    for day in days:
        try:
            js = ud._pget('/v2/aggs/grouped/locale/us/market/stocks/' + day,
                          {'adjusted': 'true'})
            daily[day] = {r['T']: (r.get('o'), r.get('h'), r.get('c'))
                          for r in js.get('results') or []}
        except Exception as e:
            print('CTRL: WARN grouped %s failed (%s)' % (day, e))
            daily[day] = {}

    def policy(t):
        first = daily.get(days[0], {}).get(t)
        last = daily.get(days[-1], {}).get(t)
        if not first or not last or not first[0]:
            return None
        o = first[0]
        highs = [daily[d][t][1] for d in days if t in daily.get(d, {})
                 and daily[d][t][1]]
        return {'ticker': t, 'entry_open': o, 'exit_close': last[2],
                'policy_return_pct': round(100 * (last[2] / o - 1), 2),
                'peak_pct_dailyhigh': round(100 * (max(highs) / o - 1), 2)
                if highs else None}

    ranks, universe_size = _ranks()

    def graded(t):
        """Price context + the v6.3 rank grade for one control ticker."""
        row = policy(t) or {'ticker': t, 'entry_open': None,
                            'exit_close': None, 'policy_return_pct': None,
                            'peak_pct_dailyhigh': None}
        row['rank'] = ranks.get(t)
        row['outcome'] = _outcome(row['rank'])
        return row

    r5 = [graded(t) for t in tickers] if tickers else None
    out = {'type': 'grade', 'week_start': week_start,
           'entry_date': entry_date, 'exit_date': exit_date,
           'grade_bar': 'weekly_rank (v6.3): BIG WIN<=100 WIN<=500 FLAT<=1500',
           'universe_size': universe_size,
           'spy': policy('SPY'),            # reported context under v6.3
           'random5': r5}
    # The control arm rule F1's pass line reads: the picks' top-500 rate must
    # beat THIS by >= 8pp over 12 graded weeks.
    if r5:
        scored = [r for r in r5 if r['outcome'] is not None]
        if scored:
            wins = sum(1 for r in scored if r['outcome'] in ('BIG WIN', 'WIN'))
            out['random5_top500'] = '%d/%d' % (wins, len(scored))
            out['random5_top500_rate'] = round(100.0 * wins / len(scored), 1)
    # base rates over the frozen L4 eligible snapshot (daily-high basis)
    snap = os.path.join(STOCKS, '_universe',
                        'universe-features-%s.jsonl' % week_start)
    try:
        uni = []
        for line in open(snap, encoding='utf-8'):
            d = json.loads(line)
            if not d.get('_meta') and d.get('ticker'):
                uni.append(d['ticker'])
        peaks = []
        for t in uni:
            p = policy(t)
            if p and p['peak_pct_dailyhigh'] is not None:
                peaks.append(p['peak_pct_dailyhigh'])
        if peaks:
            n = len(peaks)
            out['base_rate'] = {
                'n': n, 'basis': 'daily_high (optimistic bound)',
                'touch_ge_1pct': round(100.0 * sum(1 for p in peaks if p >= 1) / n, 1),
                'touch_ge_2pct': round(100.0 * sum(1 for p in peaks if p >= 2) / n, 1),
                'touch_ge_5pct': round(100.0 * sum(1 for p in peaks if p >= 5) / n, 1),
                'median_peak_pct': round(sorted(peaks)[n // 2], 2)}
    except Exception as e:
        out['base_rate'] = {'error': 'L4 snapshot unavailable: %s' % e}
    with open(CTRL, 'a') as f:
        f.write(json.dumps(out) + '\n')
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['draw', 'grade'])
    ap.add_argument('--week-start', required=True)
    ap.add_argument('--entry-date')
    ap.add_argument('--exit-date')
    a = ap.parse_args()
    try:
        if a.mode == 'draw':
            draw(a.week_start)
        else:
            grade(a.week_start, a.entry_date, a.exit_date)
    except Exception as e:
        print('CTRL: WARN %s — continuing (fail-soft)' % e)
    sys.exit(0)


if __name__ == '__main__':
    main()
