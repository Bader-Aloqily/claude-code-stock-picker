#!/usr/bin/env python3
"""
Monday pre-market gap check for /us-picks (added 2026-06-14).

Compares each pick's CURRENT price (Polygon full-market snapshot; lastTrade.p
includes pre-market) against its logged after-hours ENTRY reference, so you can
see -- BEFORE the Monday open -- how far each pick has gapped away from the price
the system scored. Recommendation context only; it does NOT change any grade.

Why: /us-picks scores off the prior-Fri AFTER-HOURS close but you FILL at Monday's
open. A big pre-market gap means your real entry differs from the scored entry --
worth seeing before you place orders. (Ties to the run-timing guidance: run the
system Sunday, sanity-check gaps Monday pre-market.)

Usage
  # auto: read the latest non-skipped week's Picks table from the tracker
  python3 ~/.claude/scripts/uspicks_premarket_check.py

  # explicit tickers (entry optional, ':' separated)
  python3 ~/.claude/scripts/uspicks_premarket_check.py AAPL:307.78 MSFT NVDA:120.50
"""
import sys, os, re
sys.path.insert(0, os.path.expanduser('~/.claude/scripts'))
import uspicks_data as ud

TRACKER = os.path.expanduser('~/.claude/stocks/us-weekly-tracker.md')
GAP_FLAG = 3.0   # |gap%| beyond this is highlighted


def _parse_picks_table(chunk):
    """Parse one week-block's Picks table -> [(ticker, entry_or_None), ...].
       Column lookup is by HEADER NAME (robust to the 2026-06-14 Peak columns,
       the 2026-06-19 Entry->Last Close rename, or any future column adds), not
       by position. The reference price is 'Last Close' (2026-06-19+) or 'Entry'
       (older weeks) -- both hold the prior-day after-hours close."""
    rows = [ln for ln in chunk.splitlines() if ln.strip().startswith('|')]
    hdr_i = cols = None
    for i, ln in enumerate(rows):
        cells = [c.strip() for c in ln.strip().strip('|').split('|')]
        if 'Ticker' in cells and ('Last Close' in cells or 'Entry' in cells):
            hdr_i, cols = i, cells
            break
    if hdr_i is None:
        return []
    ti = cols.index('Ticker')
    ei = cols.index('Last Close') if 'Last Close' in cols else cols.index('Entry')
    out = []
    for ln in rows[hdr_i + 2:]:                      # skip header + separator row
        cells = [c.strip() for c in ln.strip().strip('|').split('|')]
        if len(cells) <= max(ti, ei):
            continue
        tk = cells[ti]
        if not re.match(r'^[A-Z][A-Z0-9.\-]*$', tk):  # stop at non-ticker / sell-plan rows
            break
        m = re.search(r'[\d.]+', cells[ei].replace('$', ''))
        out.append((tk, float(m.group()) if m else None))
    return out


def parse_latest_week(path):
    """(week_label, picks) for the highest-dated non-SKIPPED week (order-independent)."""
    if not os.path.exists(path):
        return (None, [])
    text = open(path).read()
    best = None  # (date_str, header, picks)
    for chunk in re.split(r'(?m)^### Week of ', text)[1:]:
        header = chunk.splitlines()[0].strip()
        if 'SKIPPED' in header.upper():
            continue
        m = re.match(r'(\d{4}-\d{2}-\d{2})', header)
        if not m:
            continue
        picks = _parse_picks_table(chunk)
        if picks and (best is None or m.group(1) > best[0]):
            best = (m.group(1), header, picks)
    return (best[1], best[2]) if best else (None, [])


def main():
    args = sys.argv[1:]
    if args:
        picks = []
        for a in args:
            if ':' in a:
                t, e = a.split(':', 1)
                try:
                    picks.append((t.upper(), float(e)))
                except ValueError:
                    picks.append((t.upper(), None))
            else:
                picks.append((a.upper(), None))
        week = '(CLI args)'
    else:
        week, picks = parse_latest_week(TRACKER)
        if not picks:
            print('No picks found in tracker. Pass tickers explicitly, e.g.:\n'
                  '  python3 ~/.claude/scripts/uspicks_premarket_check.py AAPL:307.78 MSFT')
            return

    snap = ud.market_snapshot([t for t, _ in picks])

    print('PRE-MARKET GAP CHECK -- week of %s' % week)
    print('(ref = logged after-hours Last Close; last = live price incl. pre-market)')
    print('%-8s %12s %12s %10s %9s  %s' % ('TICKER', 'LAST CLOSE', 'LAST', 'GAP%', 'DAY%', 'NOTE'))
    for t, entry in picks:
        s = snap.get(t) or {}
        last = (s.get('lastTrade') or {}).get('p')
        if last is None:
            last = (s.get('min') or {}).get('c') or (s.get('day') or {}).get('c')
        daypc = s.get('todaysChangePerc')
        gap = ((last / entry - 1) * 100) if (last and entry) else None
        note = ''
        if gap is not None and abs(gap) >= GAP_FLAG:
            note = '** gapped %s vs entry' % ('UP' if gap > 0 else 'DOWN')
        print('%-8s %12s %12s %10s %9s  %s' % (
            t,
            ('$%.2f' % entry) if entry else '-',
            ('$%.2f' % last) if last else 'n/a',
            ('%+.2f%%' % gap) if gap is not None else '-',
            ('%+.2f%%' % daypc) if daypc is not None else '-',
            note))


if __name__ == '__main__':
    main()
