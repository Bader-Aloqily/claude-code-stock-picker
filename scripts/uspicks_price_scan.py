#!/usr/bin/env python3
"""
/us-picks Price Analyzer scan — Polygon-powered (replaces the yfinance batch scan).

Pipeline:
  1. Build the full US common-stock universe from NASDAQ Trader listing files.
  2. Pull ~31 trading days of WHOLE-MARKET OHLCV via Polygon grouped-daily
     (one HTTP call per day — ~31 calls replace the legacy ~70 flaky yfinance batches).
  3. Compute the v4.x technical indicators per ticker (identical math to the legacy scan).
  4. Enrich momentum candidates with market cap + sector (Polygon ticker_details) and
     the FRIDAY AFTER-HOURS close (entry reference, user-directed 2026-06-08).

No yfinance, no MCP. **v5.6 (2026-07-28, user-directed): the PICK universe is the WHOLE
mid-to-mega market again — every cheap-hard-filter survivor with mkt_cap >= $2B and an
after-hours close >= $5. The v5.3 S&P-500 / v5.5 S&P-∪-Nasdaq-100 MEMBERSHIP GATE IS
GONE** (removed with the restoration of the top-500-rank WIN objective: most weekly
top-gainers live outside the indices, so a membership cage and a rank objective cannot
coexist). Both membership lists are still fetched and stamped per row
(`sp500_member` / `ndx_member`) as CONTEXT ONLY — they annotate the pick card and never
restrict the set. ud.sp500_members() / ud.ndx_members() still fail loud internally, but
THIS scan catches that and degrades to empty sets + an "unavailable" marker in the
summary: a missing annotation must not abort an unrestricted run, which is now the
intended behavior. Indicators are computed for the WHOLE market (zero extra network —
the grouped-daily bars are already in hand); the per-ticker network enrichment
(mkt_cap / sector / AH tick-refine) now covers every cheap-filter survivor (~2-3k names,
market-dependent; was ~150-450 under the membership gate). Enrichment stays
PARALLELIZED across a thread pool (stateless urllib — thread-safe) and RESUMABLE: each
enriched row is appended to price-analyzer-scan.jsonl as it lands (guarded by
price-analyzer-scan-meta.json on ref_date + the SCAN_VERSION eligibility token — a
journal from a different eligibility rule is wiped, not resumed). Typical wall time
~10-20 min: the FIXED costs (31 grouped-daily universe calls + the ~31 MB after-hours
flat file) plus a ~2-3k-name enrichment fan-out. Provenance of that claim: the same
whole-market shape measured ~11 min on 2026-06-26 (Sunday, closed market, WITH the
since-removed Al Rajhi balance-sheet call per name), and mid-market-hours runs sit at
the top of the envelope (the 2026-07-14 S&P-only run measured ~21 min at 446
enrichments purely on API latency). Re-measure on the first v5.6 Sunday run and tighten
this claim if it lands outside ~10-20 min. Output schema is a superset of the legacy
scan (adds `after_hours_close`, `sp500_member`, `ndx_member`), so downstream phases are
unchanged. KNOWN LIMITATION (pre-existing, recorded 2026-07-14): Polygon keys class
shares with a dot (BRK.B) while the scan universe uses the hyphen convention (BRK-B),
so dot-class tickers (BRK.B, BF.B) never match grouped-daily rows and are outside scan
coverage — immaterial for a top-gainer picker (both fail the atr_pct >= 2 floor
essentially every week); `sp500_in_data` in the summary makes the gap visible.

Output: ~/.claude/stocks/price-analyzer-output.json  (sorted by top_gainer_fit_score desc)
Run:    python3 ~/.claude/scripts/uspicks_price_scan.py
Env:    PRICE_HISTORY_DAYS (default 31),
        PRICE_ENRICH_CAP (default 300; VESTIGIAL — no longer caps enrichment under
        v5.1, only the momentum_candidates summary count),
        PRICE_ENRICH_WORKERS (default 12; enrichment thread-pool size),
        PRICE_REF_DATE (override the reference trading day, YYYY-MM-DD; default = latest).
        After-hours close: EVERY eligible name is refined tick-level via /v3/trades — the
        genuine last Friday post-market trade (consolidated tape), no fit-rank cap
        (user-directed 2026-06-26; was a top-60-by-fit subset, which missed most picks
        because picks are chosen later by CONVICTION score, not fit).
"""
import os, sys, json, re, time, threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uspicks_data as ud
import pandas as pd

STOCKS_DIR = os.path.expanduser('~/.claude/stocks')
OUTPUT_FILE = os.path.join(STOCKS_DIR, 'price-analyzer-output.json')
# Resumable-enrichment journal (2026-06-22): per-ticker enriched rows + a ref_date
# guard, so a crash/kill mid-enrichment is resumed instead of losing the pass.
SCAN_JSONL = os.path.join(STOCKS_DIR, 'price-analyzer-scan.jsonl')
SCAN_META = os.path.join(STOCKS_DIR, 'price-analyzer-scan-meta.json')
os.makedirs(STOCKS_DIR, exist_ok=True)

HISTORY_DAYS = int(os.environ.get('PRICE_HISTORY_DAYS', '31'))
ENRICH_CAP = int(os.environ.get('PRICE_ENRICH_CAP', '300'))
# After-hours close is refined tick-level (via /v3/trades = the consolidated last AH
# trade) for EVERY ELIGIBLE name — no fit-rank cap (user-directed 2026-06-26). See the
# tail of _enrich_one. PRICE_AH_REFINE_CAP is retired (picks are chosen by conviction
# score over the whole eligible set, so a fit cap silently missed most of them).
# Enrichment thread-pool size. The data layer is stateless urllib (thread-safe);
# Polygon "Massive" has no per-minute cap and _pget already retries 429s. Under the
# v5.6 whole-market pick universe the pool covers ~2-3k per-ticker enrichments
# (every eligible name's after-hours close is also tick-refined — 2 extra calls
# each); the same pool handled that load v5.1-v5.2 at ~11 min measured. Whole-run
# wall time = the FIXED universe/flat-file costs + this fan-out — see the docstring.
ENRICH_WORKERS = int(os.environ.get('PRICE_ENRICH_WORKERS', '12'))
REF_OVERRIDE = os.environ.get('PRICE_REF_DATE', '').strip()

# v5.1 (2026-06-18) — eligibility is decided in the scan so the command can fan
# agents over ALL eligible names (no momentum pre-filter). v5.3 (2026-07-14) →
# v5.5 (2026-07-23) gated the universe on index membership; **v5.6 (2026-07-28,
# user-directed) REMOVED that gate** — the pick universe is the whole mid-to-mega
# market again, so the cheap hard filters alone decide which names get enriched and
# mkt_cap is applied during enrichment. The vice-business blacklist (the
# single-layer Sharia screen) is applied by the command (it parses the markdown
# list). The momentum gate (breakout OR weekly_chg>3%) is RETAINED only
# to populate `momentum_candidates` in the summary — it no longer caps enrichment.
# v6.1 (2026-08-29, user-directed v4.6 restore): price floor back to $10, the
# oversold RSI < 25 gate is BACK, and the B1 atr_pct >= 2.0 floor is REMOVED
# (B1 deactivated in full). Recorded honestly: the 2006-2026 backtest is what
# lowered the floor to $5 and removed the RSI<25 gate in v5.0 — v6.1 reverses
# both by user direction, not because that evidence changed.
HARD_PRICE_MIN = float(os.environ.get('HARD_PRICE_MIN', '10'))
HARD_LIQ_MIN = float(os.environ.get('HARD_LIQ_MIN', '1000000'))
HARD_ATR_MIN = float(os.environ.get('HARD_ATR_MIN', '0'))     # v6.1: B1 floor OFF
HARD_RSI_MAX = float(os.environ.get('HARD_RSI_MAX', '90'))
HARD_RSI_MIN = float(os.environ.get('HARD_RSI_MIN', '25'))    # v6.1: oversold gate BACK
MKT_CAP_MIN = float(os.environ.get('MKT_CAP_MIN', '2000000000'))

# Eligibility-logic version — stamped into the resume-journal meta so a journal
# written under a DIFFERENT eligibility rule (e.g. the pre-2026-07-08 Al Rajhi
# financial screen, the v5.3 S&P-only universe, or the v5.5 S&P-∪-NDX universe) is
# wiped, not resumed. Bump when the `eligible` logic changes. v6 = the v5.6
# whole-market revert (2026-07-28) — deliberately a NEW token, not a reuse of the
# pre-v5.3 'v3-vice-only' string, so a stale journal from either era is discarded.
SCAN_VERSION = 'v7-v46restore'   # v6.1 (2026-08-29): $10 floor, RSI 25-90 band, no atr floor

EXCLUDE_NAME = re.compile(r'\b(Preferred|Warrants?|Rights?|Units?|Notes?|Bonds?|Debentures?|Fund)\b', re.I)
SPAC_NAME = re.compile(r'\bAcquisition\s+(?:Corp|Company|Corporation|Holdings|Partners|Inc)\b', re.I)


def _fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='ignore')


def build_universe():
    tickers = set()
    try:
        for line in _fetch('https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt').strip().split('\n')[1:]:
            if line.startswith('File Creation Time'):
                continue
            p = line.split('|')
            if len(p) < 8:
                continue
            sym, name, _mkt, test, fin, _lot, etf, nxt = p[:8]
            if test == 'Y' or etf == 'Y' or nxt == 'Y':
                continue
            if fin and fin not in ('N', ''):
                continue
            if EXCLUDE_NAME.search(name) or SPAC_NAME.search(name):
                continue
            if re.match(r'^[A-Z]{1,5}$', sym):
                tickers.add(sym)
    except Exception as e:
        print('nasdaqlisted fail:', e, file=sys.stderr)
    try:
        for line in _fetch('https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt').strip().split('\n')[1:]:
            if line.startswith('File Creation Time'):
                continue
            p = line.split('|')
            if len(p) < 8:
                continue
            act, name, exch, _cqs, etf, _lot, test, _nas = p[:8]
            if test == 'Y' or etf == 'Y' or exch not in ('A', 'N', 'P', 'Z', 'V'):
                continue
            if EXCLUDE_NAME.search(name) or SPAC_NAME.search(name):
                continue
            sym = act.strip().replace('.', '-')
            if re.match(r'^[A-Z]{1,5}(-[A-Z])?$', sym):
                tickers.add(sym)
    except Exception as e:
        print('otherlisted fail:', e, file=sys.stderr)
    try:
        import io
        html = _fetch('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        tbl = pd.read_html(io.StringIO(html))[0]
        tickers.update(t.replace('.', '-') for t in tbl['Symbol'].tolist())
    except Exception as e:
        print('sp500 supplement fail:', e, file=sys.stderr)
    return tickers


def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    d = closes.diff()
    ag = d.where(d > 0, 0.0).rolling(period, min_periods=period).mean()
    al = (-d).where(d < 0, 0.0).rolling(period, min_periods=period).mean()
    rsi = 100 - (100 / (1 + ag / al))
    return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None


def calc_macd(closes):
    if len(closes) < 26:
        return None, None
    m = closes.ewm(span=12).mean() - closes.ewm(span=26).mean()
    return round(float(m.iloc[-1]), 4), round(float(m.ewm(span=9).mean().iloc[-1]), 4)


def calc_atr(high, low, close, period=14):
    if len(close) < period + 1:
        return None
    tr = pd.DataFrame({'hl': high - low, 'hc': (high - close.shift(1)).abs(),
                       'lc': (low - close.shift(1)).abs()}).max(axis=1)
    atr = tr.rolling(period).mean()
    return round(float(atr.iloc[-1]), 4) if not pd.isna(atr.iloc[-1]) else None


def main():
    t0 = time.time()
    universe = build_universe()
    print('universe: %d common stocks' % len(universe), file=sys.stderr)

    # v5.6 (2026-07-28): the PICK universe is the WHOLE market again (mid-to-mega,
    # mkt_cap >= $2B + AH close >= $5) — the v5.3/v5.5 index-membership GATE is GONE.
    # Both membership lists are still fetched, but they are now INFORMATIONAL ONLY
    # (they annotate each row and feed the pick card's "S&P 500 / NDX member" context
    # line). Because membership no longer gates anything, a fetch failure must NOT
    # abort a whole-market run: ud.sp500_members() / ud.ndx_members() still fail loud
    # by design (unchanged), and THIS caller degrades to empty sets + a summary marker.
    # That is not a silent data downgrade — under v5.6 an unrestricted run IS the
    # intended behavior; the only loss is a context annotation.
    try:
        sp500, sp500_src = ud.sp500_members()
    except Exception as e:                      # noqa: BLE001 — informational only
        sp500, sp500_src = set(), 'unavailable (%s)' % type(e).__name__
    print('sp500 membership: %d tickers via %s [context only]'
          % (len(sp500), sp500_src), file=sys.stderr)
    try:
        ndx, ndx_src = ud.ndx_members()
    except Exception as e:                      # noqa: BLE001 — informational only
        ndx, ndx_src = set(), 'unavailable (%s)' % type(e).__name__
    print('ndx membership: %d tickers via %s [context only] (union %d)'
          % (len(ndx), ndx_src, len(sp500 | ndx)), file=sys.stderr)

    # Discover the last HISTORY_DAYS trading days via grouped-daily (empty = holiday/weekend).
    day_data = {}
    d = datetime.strptime(REF_OVERRIDE, '%Y-%m-%d').date() if REF_OVERRIDE else datetime.utcnow().date()
    probes = 0
    while len(day_data) < HISTORY_DAYS and probes < HISTORY_DAYS * 2 + 20:
        if d.weekday() < 5:
            ds = d.isoformat()
            g = ud.grouped_daily(ds)
            if g:
                day_data[ds] = g
        d -= timedelta(days=1)
        probes += 1
    dates = sorted(day_data.keys())
    if not dates:
        print('ERROR: no grouped-daily data returned', file=sys.stderr)
        sys.exit(1)
    ref_date = dates[-1]
    print('history: %d trading days %s..%s (ref=%s)' % (len(dates), dates[0], dates[-1], ref_date), file=sys.stderr)

    series = {}
    for ds in dates:
        for tk, bar in day_data[ds].items():
            if tk in universe:
                series.setdefault(tk, []).append(bar)

    results, candidates = [], []
    for tk, bars in series.items():
        if len(bars) < 5:
            continue
        close = pd.Series([b['c'] for b in bars], dtype=float)
        high = pd.Series([b['h'] for b in bars], dtype=float)
        low = pd.Series([b['l'] for b in bars], dtype=float)
        vol = pd.Series([b['v'] for b in bars], dtype=float)
        cp = round(float(close.iloc[-1]), 2)
        if cp <= 0:
            continue
        weekly_chg = round((close.iloc[-1] / close.iloc[-5] - 1) * 100, 2) if len(close) >= 5 else 0.0
        monthly_chg = round((close.iloc[-1] / close.iloc[0] - 1) * 100, 2)
        avg_vol = vol.mean()
        vol_ratio = round(float(vol.iloc[-1] / avg_vol), 2) if avg_vol > 0 else 0
        rsi = calc_rsi(close)
        rsi = round(rsi, 1) if rsi is not None else None
        macd_line, macd_signal = calc_macd(close)
        atr = calc_atr(high, low, close)
        up_days = int((close.tail(5).diff().dropna() > 0).sum()) if len(close) >= 5 else 0
        high_20d = round(float(high.tail(20).max()), 2)
        low_20d = round(float(low.tail(20).min()), 2)
        sma10 = round(float(close.rolling(10).mean().iloc[-1]), 2) if len(close) >= 10 else None
        sma20 = round(float(close.rolling(20).mean().iloc[-1]), 2) if len(close) >= 20 else None
        avg_daily_value = round(float(avg_vol * cp), 0)
        chg_3d = round((close.iloc[-1] / close.iloc[-3] - 1) * 100, 2) if len(close) >= 3 else 0.0
        daily_chg = round((close.iloc[-1] / close.iloc[-2] - 1) * 100, 2) if len(close) >= 2 else 0.0
        explosive = bool((vol_ratio >= 5 and daily_chg > 5) or (vol_ratio >= 3 and daily_chg > 20)
                         or (weekly_chg > 20 and vol_ratio >= 2))
        pct_from_20d_high = round((cp / high_20d - 1) * 100, 2) if high_20d > 0 else 0.0
        breakout = pct_from_20d_high >= -3.0 and vol_ratio >= 1.5
        vc = min(vol_ratio * 10, 40)
        mc = max(0, min(weekly_chg * 2, 30))
        rc = max(0, min(chg_3d * 3, 15))
        bc = 15 if breakout else (8 if pct_from_20d_high >= -8 else 0)
        tgfs = round(vc + mc + rc + bc, 1)
        row = {
            "ticker": tk, "close": cp, "weekly_chg": weekly_chg, "monthly_chg": monthly_chg,
            "chg_3d": chg_3d, "daily_chg": daily_chg, "vol_ratio": vol_ratio, "rsi": rsi,
            "macd_line": macd_line, "macd_signal": macd_signal, "atr": atr,
            "atr_pct": round(atr / cp * 100, 2) if (atr and cp) else None,
            "up_days_5": up_days, "high_20d": high_20d, "low_20d": low_20d,
            "pct_from_20d_high": pct_from_20d_high, "breakout_flag": breakout,
            "explosive_mover": explosive, "top_gainer_fit_score": tgfs,
            "sma10": sma10, "sma20": sma20, "avg_daily_value": avg_daily_value,
            "high_52w": None, "pct_from_52w_high": None, "short_pct": None,
            "float_shares": None, "mkt_cap": None, "sector": None, "after_hours_close": None,
            "sp500_member": tk in sp500, "ndx_member": tk in ndx, "eligible": None,
        }
        results.append(row)
        if breakout or weekly_chg > 3.0 or explosive:
            candidates.append(row)

    candidates.sort(key=lambda x: x.get('top_gainer_fit_score', 0), reverse=True)
    # Eligibility (v5.6, 2026-07-28 — user-directed revert to the rank objective):
    # enrich EVERY cheap-hard-filter survivor in the WHOLE market — no membership
    # gate, no momentum gate, no cap (the v5.1 full-fan-out principle applied to the
    # mid-to-mega universe, exactly as it stood v5.1-v5.2). Index membership is
    # annotated for context only and never restricts the set.
    def _passes_cheap(r):
        return (r['close'] >= HARD_PRICE_MIN
                and (r['avg_daily_value'] or 0) >= HARD_LIQ_MIN
                and (r['atr_pct'] or 0) >= HARD_ATR_MIN
                and (r['rsi'] is None
                     or (HARD_RSI_MIN <= r['rsi'] <= HARD_RSI_MAX)))
    cheap_pass = [r for r in results if _passes_cheap(r)]
    enrich = sorted(cheap_pass,
                    key=lambda x: x.get('top_gainer_fit_score', 0), reverse=True)
    print('computed %d tickers; %d pass cheap hard filters -> enriching all of them '
          '(v5.6 whole-market pick universe; %d are S&P 500 / Nasdaq-100 members '
          '[context only]; %d momentum candidates, info-only)'
          % (len(results), len(cheap_pass),
             sum(1 for r in cheap_pass if r['sp500_member'] or r['ndx_member']),
             len(candidates)), file=sys.stderr)

    try:
        ah_all = ud.afterhours_close_all(ref_date)
    except Exception as e:
        print('afterhours_close_all failed (%s) — per-ticker fallback' % e, file=sys.stderr)
        ah_all = {}

    # --- Resumable, parallel enrichment (2026-06-22) -----------------------------
    # The v5.1 "enrich every survivor" change raised enrichment from ~300 to ~3k
    # sequential per-ticker network calls (~60-90 min) with a single write at the
    # very end, so any crash/kill lost the whole pass. Fix: (a) PARALLELIZE across a
    # thread pool (the data layer is stateless urllib — no shared session/cache, so
    # it's thread-safe), and (b) RESUME from a per-ticker JSONL (ref_date-guarded).
    ENRICHED_FIELDS = ('after_hours_close', 'ah_source', 'mkt_cap', 'sector', 'eligible')

    # Load any prior progress for THIS ref_date; else start the journal clean.
    done = {}
    try:
        meta = json.load(open(SCAN_META)) if os.path.exists(SCAN_META) else {}
    except Exception:
        meta = {}
    # Resume only when BOTH the ref_date AND the eligibility-logic version match —
    # a journal written under a different `eligible` rule carries stale flags.
    if (meta.get('ref_date') == ref_date
            and meta.get('screen') == SCAN_VERSION
            and os.path.exists(SCAN_JSONL)):
        with open(SCAN_JSONL) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    done[rec['ticker']] = rec
                except Exception:
                    pass
    else:  # ref_date or eligibility version changed (or first run) -> stale journal; wipe it.
        for p in (SCAN_JSONL, SCAN_META):
            try:
                os.remove(p)
            except OSError:
                pass
    with open(SCAN_META, 'w') as f:
        json.dump({'ref_date': ref_date, 'screen': SCAN_VERSION}, f)

    # Apply already-enriched rows from the journal; queue only the rest.
    todo = []
    for i, row in enumerate(enrich):
        rec = done.get(row['ticker'])
        if rec is not None:
            for k in ENRICHED_FIELDS:
                if k in rec:
                    row[k] = rec[k]
        else:
            todo.append((i, row))
    if done:
        print('resume: %d/%d already enriched (ref=%s); %d remaining'
              % (len(enrich) - len(todo), len(enrich), ref_date, len(todo)), file=sys.stderr)

    def _enrich_one(idx, row):
        tk = row['ticker']
        ah = ah_all.get(tk)
        if ah is None:
            try:
                ah, _ = ud.after_hours_close(tk, ref_date)
            except Exception:
                ah = None
        row['after_hours_close'] = round(ah, 2) if ah else row['close']
        row['ah_source'] = 'flatfile'  # refined tick-level below once eligibility is known
        try:
            td = ud.ticker_details(tk)
            row['mkt_cap'] = td.get('market_cap')
            row['sector'] = td.get('sector')
        except Exception:
            pass
        mc = row.get('mkt_cap')
        ah_px = row.get('after_hours_close') or row.get('close')
        # v5.6 (2026-07-28): eligibility is the mid-to-mega pair again — $2B market
        # cap + $5 after-hours price. NO membership conjunct (the v5.3/v5.5 index
        # gate was removed by user direction when the rank objective was restored).
        elig = bool(mc and mc >= MKT_CAP_MIN and ah_px >= HARD_PRICE_MIN)
        # Tick-level after-hours close for EVERY eligible name (user-directed 2026-06-26;
        # no fit-rank cap). The flat-file minute aggs ~= the last ROUND-LOT print and miss
        # thin/late odd-lot after-hours trades, drifting ~0.5-2% from the consolidated AH
        # close. Picks/runners-up are chosen later by CONVICTION score over the whole
        # eligible set (orthogonal to fit), so the old top-by-fit gate missed most of them.
        # after_hours_close_tick(): the last genuine ROUND LOT <=20:00 ET (STRICT since
        # 2026-07-27 -- odd lots never set the close, however near they print, because an
        # odd lot is not a price you can trade at in size; "Market Center Official Close"
        # re-prints, conditions 15/38, are excluded too -- they are the 4 PM close
        # re-stamped with an AH timestamp). Falls back to the last odd lot when a name has
        # NO after-hours round lot at all, and to the regular close when the AH tape is
        # empty. 2 REST calls/name; runs inside
        # the parallel+journaled path, so it stays crash-safe/resumable. The whole-universe
        # RANK scan stays flat-file (tick-pulling ~5k names/week is infeasible).
        if elig:
            try:
                ah_t, _reg_t, src = ud.after_hours_close_tick(tk, ref_date)
                if ah_t:
                    row['after_hours_close'] = round(ah_t, 2)
                    row['ah_source'] = src
                    ah_px = row['after_hours_close']
            except Exception:
                pass
        row['eligible'] = bool(mc and mc >= MKT_CAP_MIN and ah_px >= HARD_PRICE_MIN)
        return row

    # Each thread mutates only its OWN row dict; _save runs in the main thread as
    # futures complete (the lock is belt-and-suspenders for any future refactor).
    save_lock = threading.Lock()
    jsonl_f = open(SCAN_JSONL, 'a')

    def _save(row):
        rec = {'ticker': row['ticker']}
        for k in ENRICHED_FIELDS:
            rec[k] = row.get(k)
        with save_lock:
            jsonl_f.write(json.dumps(rec) + '\n')
            jsonl_f.flush()

    if todo:
        n_done = 0
        with ThreadPoolExecutor(max_workers=ENRICH_WORKERS) as ex:
            futs = {ex.submit(_enrich_one, idx, row): row for idx, row in todo}
            for fut in as_completed(futs):
                try:
                    r = fut.result()
                except Exception:
                    r = futs[fut]  # leave defaults but still journal it (don't retry forever)
                _save(r)
                n_done += 1
                if n_done % 100 == 0:
                    print('  enriched %d/%d (this run)' % (n_done, len(todo)), file=sys.stderr)
    jsonl_f.close()

    results.sort(key=lambda x: x.get('top_gainer_fit_score', 0), reverse=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    n_eligible = sum(1 for r in results if r.get('eligible'))
    # Enrichment finished end-to-end -> clear the resume journal so next week is clean.
    for p in (SCAN_JSONL, SCAN_META):
        try:
            os.remove(p)
        except OSError:
            pass
    summary = {"status": "DONE", "ref_date": ref_date, "trading_days": len(dates),
               "universe": len(universe), "computed": len(results),
               # Membership counts are CONTEXT ONLY under v5.6 (they no longer gate
               # eligibility); a `*_source` of "unavailable (...)" means the annotation
               # is missing for this run, NOT that the universe changed.
               "sp500_members": len(sp500), "sp500_source": sp500_src,
               "sp500_in_data": sum(1 for r in results if r.get('sp500_member')),
               "ndx_members": len(ndx), "ndx_source": ndx_src,
               "ndx_in_data": sum(1 for r in results if r.get('ndx_member')),
               "index_members_union": len(sp500 | ndx),
               "membership_is_context_only": True,
               "momentum_candidates": len(candidates), "cheap_filter_pass": len(cheap_pass),
               "enriched": len(enrich),
               "eligible": n_eligible, "scan_version": SCAN_VERSION,
               "workers": ENRICH_WORKERS,
               "output_file": OUTPUT_FILE, "elapsed_sec": round(time.time() - t0, 1)}
    print('STATUS=DONE %s' % json.dumps(summary), file=sys.stderr)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
