#!/usr/bin/env python3
"""
/us-picks Options Analyzer data — Polygon options-chain metrics per ticker (no yfinance).

Computes the inputs the Options Analyzer scores 0-20 (Bullish flow / Implied move /
Smart money): put-call volume & OI ratios (whole chain), nearest-expiry ATM implied
volatility, implied move to that expiry, and unusual-activity (day volume > open
interest) counts.

NBBO quote context (added 2026-07-14 — the user's Polygon Options ADVANCED tier,
subscribed same day, unlocks real-time quotes in the chain snapshot): per ticker the
scan now also emits the ATM contract's bid/ask + spread% and the chain's quote
coverage. INFORMATIONAL fields — they sharpen the Analyzer's liquidity/smart-money
read; the 0-20 scoring rubric is UNCHANGED.

Run:  python3 ~/.claude/scripts/uspicks_options_scan.py TICKER1 TICKER2 ...
      (or OPTIONS_TICKERS="NVDA,AMD,..." env, or comma/space-separated on stdin)
Out:  JSON array, one object per ticker.
"""
import os, sys, json, math
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uspicks_data as ud


def _vol(c):
    return (c.get('day') or {}).get('volume') or 0


def _oi(c):
    return c.get('open_interest') or 0


def _det(c, k):
    return (c.get('details') or {}).get(k)


def analyze(ticker):
    chain = ud.options_chain(ticker, limit=250)
    if not chain:
        return {'ticker': ticker, 'error': 'no_chain'}
    calls = [c for c in chain if _det(c, 'contract_type') == 'call']
    puts = [c for c in chain if _det(c, 'contract_type') == 'put']
    call_vol = sum(_vol(c) for c in calls)
    put_vol = sum(_vol(c) for c in puts)
    call_oi = sum(_oi(c) for c in calls)
    put_oi = sum(_oi(c) for c in puts)

    spot = None
    for c in chain:
        ua = c.get('underlying_asset') or {}
        if ua.get('price'):
            spot = ua['price']
            break

    # Nearest upcoming expiration drives the weekly ATM IV / implied-move signal.
    exps = sorted({_det(c, 'expiration_date') for c in chain if _det(c, 'expiration_date')})
    near_exp = None
    for e in exps:
        try:
            if (date.fromisoformat(e) - date.today()).days >= 1:
                near_exp = e
                break
        except Exception:
            pass
    if near_exp is None and exps:
        near_exp = exps[0]

    iv_cands = [c for c in chain if _det(c, 'expiration_date') == near_exp
                and c.get('implied_volatility') and _det(c, 'strike_price')]
    atm_iv = None
    atm_bid = atm_ask = atm_spread_pct = None
    if iv_cands:
        if spot:
            atm = min(iv_cands, key=lambda c: abs(_det(c, 'strike_price') - spot))
        else:
            atm = max(iv_cands, key=lambda c: _vol(c) + _oi(c))
        atm_iv = round(atm['implied_volatility'], 4)
        # NBBO quote on the ATM contract (Options Advanced, 2026-07-14) —
        # informational liquidity context; missing/crossed quotes -> None.
        q = atm.get('last_quote') or {}
        bid, ask = q.get('bid'), q.get('ask')
        if bid and ask and ask >= bid > 0:
            atm_bid, atm_ask = round(bid, 2), round(ask, 2)
            mid = (bid + ask) / 2
            atm_spread_pct = round((ask - bid) / mid * 100, 2) if mid else None

    implied_move_pct = None
    if atm_iv and near_exp:
        try:
            dte = max((date.fromisoformat(near_exp) - date.today()).days, 1)
        except Exception:
            dte = 5
        implied_move_pct = round(atm_iv * math.sqrt(dte / 365.0) * 100, 2)

    unusual = [_det(c, 'ticker') for c in chain
               if _vol(c) and _oi(c) and _vol(c) > max(_oi(c), 100)]

    quoted = sum(1 for c in chain if (c.get('last_quote') or {}).get('ask'))

    return {
        'ticker': ticker, 'spot': spot, 'contracts': len(chain), 'near_expiration': near_exp,
        'pc_vol_ratio': round(put_vol / call_vol, 3) if call_vol else None,
        'pc_oi_ratio': round(put_oi / call_oi, 3) if call_oi else None,
        'call_vol': call_vol, 'put_vol': put_vol, 'call_oi': call_oi, 'put_oi': put_oi,
        'atm_iv': atm_iv, 'implied_move_pct': implied_move_pct,
        'atm_bid': atm_bid, 'atm_ask': atm_ask, 'atm_spread_pct': atm_spread_pct,
        'quote_coverage': round(quoted / len(chain), 3) if chain else None,
        'unusual_count': len(unusual), 'unusual_sample': unusual[:10],
    }


def main():
    tickers = sys.argv[1:]
    if not tickers and os.environ.get('OPTIONS_TICKERS'):
        tickers = [t.strip() for t in os.environ['OPTIONS_TICKERS'].split(',') if t.strip()]
    if not tickers and not sys.stdin.isatty():
        tickers = [t.strip() for t in sys.stdin.read().replace(',', ' ').split() if t.strip()]
    if not tickers:
        print('usage: uspicks_options_scan.py TICKER1 TICKER2 ...', file=sys.stderr)
        sys.exit(2)
    print(json.dumps([analyze(t) for t in tickers], indent=2))


if __name__ == '__main__':
    main()
