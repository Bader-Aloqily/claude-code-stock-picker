"""
Shared data layer for the /us-picks system — Polygon ("Massive"), REST/S3 only,
NO MCP. Every /us-picks agent imports this module instead of calling yfinance
or any MCP server.

Financial Datasets (REST, fail-soft) — RE-INSTATED by the user on 2026-08-29; the
   2026-08-14 cancellation note that stood here is superseded. The fd_* helpers
   (fd_key / _fget / fd_available / fd_insider_trades / fd_filings /
   fd_institutional_ownership / insider_trades_best) carry what Polygon does NOT
   license: Form 4 insider trades, SEC filings, 13F holdings. They return [] / {}
   instead of raising, so a lapse degrades Big Money to the openinsider WebFetch
   rung instead of breaking a run.
   2026-09-07 data-integrity fix: every FD list endpoint caps a response at 10 rows
   regardless of `limit` and pages via `next_page_url`; the helpers now walk that
   cursor chain (see the FD section). Before the fix each ticker silently got only
   its 10 most recent Form 4 line items.

Data sources
------------
  Polygon REST        prices, grouped-daily (whole market in 1 call), minute bars,
                      after-hours close, options-chain snapshot, ticker details (mkt_cap),
                      news+sentiment, splits, dividends, short-interest/-volume (FINRA),
                      treasury yields (/fed), full-market snapshot (pre-market gap check),
                      analyst ratings (Benzinga add-on), corporate events + forward
                      earnings dates (TMX / Wall Street Horizon add-on)
  Polygon Flat Files  bulk whole-universe day/minute aggregates over S3 (grading scans)
  Wikipedia           S&P 500 constituents list (sp500_members — CONTEXT ONLY since
                      v5.6, 2026-07-28: it annotates rows, it no longer gates the
                      pick universe; live fetch + last-good cache, fail-loud)
  Nasdaq API          Nasdaq-100 constituents list (ndx_members — same context-only
                      role since v5.6; added 2026-07-23; the index operator's
                      own feed; live fetch + last-good cache, fail-loud)
  Financial Datasets  Form 4 insider trades (/insider-trades/), SEC filings (/filings/),
                      13F holdings (/institutional-holdings/) — cursor-paginated 10-row
                      pages, fail-soft; feeds Big Money Signal A via insider_trades_best

Credentials (chmod 600, excluded from the GitHub repo by the allowlist .gitignore)
  ~/.claude/.polygon_key             Polygon REST API key
  ~/.claude/.polygon_flatfiles.json  S3 creds {access_key_id, secret_access_key, endpoint, bucket}
  ~/.claude/.financialdatasets_key   Financial Datasets API key (LIVE again since 2026-08-29;
                                     env override FINANCIALDATASETS_API_KEY)
  (the Polygon key may be overridden by the env var POLYGON_API_KEY; every key
   file stays gitignored so it can never be committed)

After-hours rule (user-directed 2026-06-08)
  The entry baseline AND both grading window-ends use the FRIDAY AFTER-HOURS close
  = the close of the last trade with ET start <= 20:00. Falls back to the regular
  16:00 close when a ticker has no extended-hours prints that day.

Verified live 2026-06-08 against the user's account:
  grouped_daily('2026-06-05') -> 12,244 tickers in one call
  after_hours_close('AAPL','2026-06-05') -> (307.78 AH, 307.39 regular)
  options_chain('AAPL') -> contracts with greeks/IV/open_interest/day volume
  flat files -> us_stocks_sip/{day_aggs_v1 0.3MB, minute_aggs_v1 31MB}/YYYY/MM/DATE.csv.gz
"""
import os, sys, json, re, time, gzip
import urllib.request, urllib.error
from datetime import datetime, timedelta

try:
    import pytz
    _ET = pytz.timezone('America/New_York')
    _UTC = pytz.utc
except Exception:                      # pragma: no cover
    _ET = None
    _UTC = None

CACHE_DIR = os.path.expanduser('~/.claude/stocks/_flatfiles_cache')


# ----------------------------------------------------------------------------
# Credentials
# ----------------------------------------------------------------------------
def polygon_key():
    k = os.environ.get('POLYGON_API_KEY')
    if k:
        return k.strip()
    return open(os.path.expanduser('~/.claude/.polygon_key')).read().strip()


def flatfile_creds():
    return json.load(open(os.path.expanduser('~/.claude/.polygon_flatfiles.json')))


# ----------------------------------------------------------------------------
# Time helpers — Polygon timestamps are Unix epoch; flat files use nanoseconds,
# REST uses milliseconds. _ts_to_ms() auto-detects the unit by magnitude so the
# same ET conversion works for both.
# ----------------------------------------------------------------------------
def _ts_to_ms(v):
    v = int(v)
    if v > 10**17:        # nanoseconds
        return v / 1e6
    if v > 10**14:        # microseconds
        return v / 1e3
    if v > 10**11:        # milliseconds
        return float(v)
    return v * 1000.0     # seconds


def _to_et(ts_any):
    ms = _ts_to_ms(ts_any)
    if _ET is None:       # pragma: no cover  (pytz missing — UTC-4 EDT fallback)
        return datetime.utcfromtimestamp(ms / 1000.0)
    return datetime.fromtimestamp(ms / 1000.0, tz=_UTC).astimezone(_ET)


def _et_minutes(ts_any):
    """ET minute-of-day (0-1439) for a Polygon timestamp."""
    et = _to_et(ts_any)
    return et.hour * 60 + et.minute


# ----------------------------------------------------------------------------
# Polygon REST
# ----------------------------------------------------------------------------
POLY = 'https://api.polygon.io'
_BACKOFF = [2, 5, 15, 40]


def _pget(path, params=None, retries=4):
    qs = '&'.join('%s=%s' % (k, v) for k, v in (params or {}).items())
    sep = '&' if '?' in path else '?'
    url = POLY + path + sep + ((qs + '&') if qs else '') + 'apiKey=' + polygon_key()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'uspicks/1.0'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            transient = (e.code == 429) or (500 <= e.code < 600)
            if transient and attempt < retries - 1:
                time.sleep(_BACKOFF[min(attempt, len(_BACKOFF) - 1)]); continue
            raise
        except Exception:
            if attempt < retries - 1:
                time.sleep(_BACKOFF[min(attempt, len(_BACKOFF) - 1)]); continue
            raise
    return {}


def grouped_daily(date_str, include_otc=False):
    """Whole-market regular-session daily OHLCV for one date -> {ticker: bar}.
    bar keys: o,h,l,c,v,vw,n (T=ticker). One HTTP call returns the entire market."""
    d = _pget('/v2/aggs/grouped/locale/us/market/stocks/%s' % date_str,
              {'adjusted': 'true', 'include_otc': 'true' if include_otc else 'false'})
    return {b['T']: b for b in (d.get('results') or [])}


def daily_aggs(ticker, from_date, to_date):
    """Per-ticker regular-session daily bars over a date range (asc)."""
    d = _pget('/v2/aggs/ticker/%s/range/1/day/%s/%s' % (ticker, from_date, to_date),
              {'adjusted': 'true', 'sort': 'asc', 'limit': '5000'})
    return d.get('results') or []


def minute_bars(ticker, date_str):
    """Per-ticker minute bars for one date, INCLUDING extended hours (04:00-20:00 ET)."""
    d = _pget('/v2/aggs/ticker/%s/range/1/minute/%s/%s' % (ticker, date_str, date_str),
              {'adjusted': 'true', 'sort': 'asc', 'limit': '50000'})
    return d.get('results') or []


def after_hours_close(ticker, date_str):
    """(ah_close, reg_close) for `date_str`.
       reg_close = close of last minute bar with ET start <= 16:00
       ah_close  = close of last minute bar with ET start <= 20:00 (falls back to reg)."""
    bars = minute_bars(ticker, date_str)
    if not bars:
        return (None, None)
    reg = ah = None
    for b in bars:
        m = _et_minutes(b['t'])
        if m <= 16 * 60:
            reg = b['c']
        if m <= 20 * 60:
            ah = b['c']
    if ah is None:
        ah = reg
    if reg is None:
        reg = ah
    return (ah, reg)


def after_hours_close_tick(ticker, date_str, outlier_pct=0.75, strict_round_lot=True):
    """Tick-level (ah_close, reg_close, source) for `date_str` from /v3/trades.

    The minute-aggregate path (`after_hours_close` / `afterhours_close_all`) ~= the last
    ROUND-LOT print and misses thin/late odd-lot after-hours trades, so it can disagree
    with the consolidated after-hours close brokers/Yahoo show. This reads the trade tape.

    STRICT ROUND-LOT mode (default since 2026-07-27, user-directed "yes, tighten"):
      ah_close = the last ROUND LOT (size >= 100 AND no odd-lot condition 37) in
                 16:00-20:00 ET. Odd lots are IGNORED OUTRIGHT, however close to the
                 round-lot price they print -- an odd lot is not a price you can trade
                 at in size, so it must never set the entry/grading basis.
                 Falls back to the regular close when the session has no AH round lot
                 (odd-lot-only tape == no real after-hours market for our purposes).
      Driver: HOOD 2026-07-24 -- a 25-share print at 19:59:57 ($94.70) was accepted over
      the last true round lot ($94.61 @ 19:59:25, 116 sh) because it sat only 0.095%
      away, inside the old 0.75% outlier band. The band made odd-lot acceptance depend
      on price proximity rather than on tradability.

    LEGACY mode (`strict_round_lot=False`, the 2026-06-14 "Option A" behaviour, kept for
    the documented reversal path): ah_close = last trade of any size, EXCEPT a final
    sub-100-share odd lot is skipped only when it is an outlier (> `outlier_pct`%) from
    the last AH round lot.

      reg_close = official daily close (for the fallback + the reg field).
    Cost: 2 REST calls/ticker (trades + daily) -> use for the pick/candidate pool only,
    NOT the whole universe (the flat-file path stays authoritative for the rank scan)."""
    reg = None
    try:
        da = daily_aggs(ticker, date_str, date_str)
        reg = da[-1]['c'] if da else None
    except Exception:
        reg = None

    try:
        d = _pget('/v3/trades/%s' % ticker,
                  {'timestamp': date_str, 'order': 'desc', 'sort': 'timestamp', 'limit': '5000'})
        res = d.get('results') or []
    except Exception:
        res = []

    # Conditions 15 ("Market Center Official Close") and 38 ("Corrected Consolidated
    # Close") are the REGULAR-session close re-disseminated with an after-hours
    # timestamp -- both carry updates_volume=False, i.e. they are not trades at all.
    # Polygon re-stamps them at 18:30 and 19:00 ET, often for enormous size (HUM
    # 145,367 sh @ its 4 PM close of $389.32 on 2026-07-24). They must never be read
    # as after-hours round lots, or the "after-hours close" silently becomes the
    # regular close for any name whose AH tape is thin.
    CLOSE_REPRINT = (15, 38)

    last_ah = None        # (price, size, conditions) of the latest genuine AH trade
    last_roundlot = None  # price of the latest genuine AH round lot
    n_oddlot_skipped = 0  # genuine odd lots newer than that round lot (reporting)
    for tr in res:                              # desc => latest first
        ts = tr.get('participant_timestamp') or tr.get('sip_timestamp')
        px = tr.get('price')
        if ts is None or px is None:
            continue
        m = _et_minutes(ts)
        if not (16 * 60 < m <= 20 * 60):        # after-hours window only (16:00-20:00 ET)
            continue
        cond = tr.get('conditions') or []
        if any(c in cond for c in CLOSE_REPRINT):   # official-close re-print, not a trade
            continue
        sz = tr.get('size') or 0
        if last_ah is None:
            last_ah = (px, sz, cond)
        if sz >= 100 and 37 not in cond:        # round lot, not an odd-lot condition
            last_roundlot = px
            break
        n_oddlot_skipped += 1
    if last_ah is None:
        return (reg, reg, 'reg_close (no after-hours trades)')

    px, sz, cond = last_ah

    if strict_round_lot:
        # 1. A genuine AH round lot always wins -- odd lots never set the close,
        #    however near the round-lot price they print.
        if last_roundlot is not None:
            if n_oddlot_skipped:
                return (last_roundlot, reg if reg else last_roundlot,
                        'AH round-lot (ignored %d later odd-lot print(s))' % n_oddlot_skipped)
            return (last_roundlot, reg if reg else last_roundlot, 'AH round-lot')
        # 2. No round lot all session: the AH market was thin but REAL, and its last
        #    print is still better evidence of the next open than the 4 PM close.
        return (px, reg if reg else px,
                'AH last odd-lot %d-sh (no round lot after hours)' % sz)

    # LEGACY (2026-06-14 "Option A"): keep the odd lot unless it is a price outlier.
    is_oddlot = (sz < 100) or (37 in cond)
    if is_oddlot and last_roundlot and abs(px - last_roundlot) / last_roundlot * 100.0 > outlier_pct:
        return (last_roundlot, reg if reg else last_roundlot,
                'AH round-lot (skipped %d-sh odd-lot outlier %.2f)' % (sz, px))
    return (px, reg if reg else px, 'AH last trade')


def ticker_details(ticker):
    """Reference data incl. market cap + shares. {} on miss."""
    d = _pget('/v3/reference/tickers/%s' % ticker).get('results') or {}
    return {
        'ticker': ticker,
        'market_cap': d.get('market_cap'),
        'shares': d.get('share_class_shares_outstanding') or d.get('weighted_shares_outstanding'),
        'sector': d.get('sic_description'),
        'name': d.get('name'),
        'primary_exchange': d.get('primary_exchange'),
        'type': d.get('type'),
    }


def splits_in_range(after_date, through_date):
    """{ticker: price_factor} for stock splits with execution_date in
    (after_date, through_date].  price_factor = product of (split_from/split_to);
    MULTIPLY a PRE-split (raw flat-file) price by it to express it in POST-split
    terms, so a pre-split entry and a post-split exit share one basis.
    Reverse split (from>to) -> factor>1; forward split (from<to) -> factor<1.

    Why: the minute_aggs / day_aggs FLAT FILES are UNADJUSTED, so a ticker that
    splits inside the grading window shows a phantom return (a 1:50 reverse split
    reads as ~+5000%).  The per-ticker REST aggs (minute_bars / daily_aggs request
    adjusted=true) are ALREADY split-adjusted and do NOT need this -- only the
    whole-market flat-file scan (uspicks_gainers_scan.py) does.
    Source: Polygon /v3/reference/splits."""
    out = {}
    params = {'execution_date.gt': after_date, 'execution_date.lte': through_date,
              'limit': '1000', 'order': 'asc', 'sort': 'execution_date'}
    for _ in range(10):  # cursor-paginate defensively (a weekly window has ~tens)
        d = _pget('/v3/reference/splits', params)
        for s in (d.get('results') or []):
            try:
                f = float(s['split_from']); t = float(s['split_to'])
                if f > 0 and t > 0:
                    out[s['ticker']] = out.get(s['ticker'], 1.0) * (f / t)
            except Exception:
                pass
        nxt = d.get('next_url') or ''
        if 'cursor=' not in nxt:
            break
        params = {'cursor': nxt.split('cursor=', 1)[1].split('&', 1)[0]}
    return out


def options_chain(underlying, limit=250, max_pages=8):
    """Option-chain snapshot: list of contracts each with .greeks, .implied_volatility,
       .open_interest, .day.volume, .details.{ticker,strike_price,expiration_date,contract_type}."""
    out = []
    d = _pget('/v3/snapshot/options/%s' % underlying, {'limit': str(limit)})
    out.extend(d.get('results') or [])
    pages = 0
    while d.get('next_url') and pages < max_pages:
        nu = d['next_url']
        url = nu + ('&' if '?' in nu else '?') + 'apiKey=' + polygon_key()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'uspicks/1.0'})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read())
            out.extend(d.get('results') or [])
        except Exception:
            break
        pages += 1
    return out


# ----------------------------------------------------------------------------
# Polygon Flat Files (S3) — bulk whole-universe aggregates for grading scans
# ----------------------------------------------------------------------------
def _s3():
    import boto3
    from botocore.config import Config
    c = flatfile_creds()
    client = boto3.client(
        's3', endpoint_url=c['endpoint'],
        aws_access_key_id=c['access_key_id'],
        aws_secret_access_key=c['secret_access_key'],
        region_name='us-east-1',
        config=Config(signature_version='s3v4'),
    )
    return client, c['bucket']


def download_flatfile(kind, date_str, force=False):
    """kind in {'day_aggs','minute_aggs','trades','quotes'}. Returns local .csv.gz path."""
    y, m, _ = date_str.split('-')
    key = 'us_stocks_sip/%s_v1/%s/%s/%s.csv.gz' % (kind, y, m, date_str)
    os.makedirs(CACHE_DIR, exist_ok=True)
    local = os.path.join(CACHE_DIR, '%s_%s.csv.gz' % (kind, date_str))
    if os.path.exists(local) and not force and os.path.getsize(local) > 0:
        return local
    s3, bucket = _s3()
    s3.download_file(bucket, key, local)
    return local


def _iter_flatfile(path):
    """Yield (cols_list, name->index dict) — streaming, low memory."""
    with gzip.open(path, 'rt') as f:
        header = f.readline().rstrip('\n').split(',')
        idx = {h: i for i, h in enumerate(header)}
        for line in f:
            parts = line.rstrip('\n').split(',')
            if len(parts) >= len(header):
                yield parts, idx


def regular_close_all(date_str):
    """{ticker: regular_close} for the whole market from the day_aggs flat file."""
    path = download_flatfile('day_aggs', date_str)
    out = {}
    for parts, idx in _iter_flatfile(path):
        try:
            out[parts[idx['ticker']]] = float(parts[idx['close']])
        except Exception:
            pass
    return out


def regular_open_close_all(date_str):
    """{ticker: (regular_open, regular_close)} for the whole market from the day_aggs
       flat file — the v5.8 (2026-08-07) GRADING basis: the pick week is measured
       FIRST_TRADING_DAY open -> LAST_TRADING_DAY regular close, so both ends come
       from this one small file (it replaced two ~31 MB minute_aggs downloads).

       Verified live 2026-08-07 on 2026-08-03: the day_aggs `open` column IS the
       09:30 ET regular-session open (byte-equal to the REST grouped-daily `o` and
       to the 09:30 minute bar) and `close` IS the 16:00 regular close — NOT an
       extended-hours print. Do NOT swap this for minute_aggs "first/last bar":
       those include 04:00-09:30 pre-market and 16:00-20:00 after-hours.

       UNADJUSTED (like every flat file) -> the caller must apply
       splits_in_range() to the entry end. See uspicks_gainers_scan.py."""
    path = download_flatfile('day_aggs', date_str)
    out = {}
    for parts, idx in _iter_flatfile(path):
        try:
            out[parts[idx['ticker']]] = (float(parts[idx['open']]),
                                         float(parts[idx['close']]))
        except Exception:
            pass
    return out


def afterhours_close_all(date_str):
    """{ticker: after_hours_close} for the whole market from the minute_aggs flat file.
       After-hours close = close of the last minute bar with ET start <= 20:00.
       Streaming parse (keeps one bar per ticker) so a ~300MB uncompressed file
       stays memory-bounded.

       RETAINED, but NO LONGER the grading basis: uspicks_gainers_scan.py moved to
       regular_open_close_all() at v5.8 (2026-08-07, user-directed "monday open till
       friday close"). Kept as the documented reversal path back to the v4.9
       after-hours-close-to-close rank — do not delete."""
    path = download_flatfile('minute_aggs', date_str)
    best = {}   # ticker -> (window_start, close)
    for parts, idx in _iter_flatfile(path):
        try:
            if _et_minutes(parts[idx['window_start']]) > 20 * 60:
                continue
            t = parts[idx['ticker']]
            ws = int(parts[idx['window_start']])
            prev = best.get(t)
            if prev is None or ws > prev[0]:
                best[t] = (ws, float(parts[idx['close']]))
        except Exception:
            pass
    return {t: v[1] for t, v in best.items()}


# ----------------------------------------------------------------------------
# Financial Datasets REST — RETIRED 2026-08-14 (subscription cancelled).
# The fd_* helpers were deleted; recoverable from git on re-subscription.
# Insider trades / 13F / SEC filing text → WebFetch fallbacks in the agents.
# ----------------------------------------------------------------------------


# ============================================================================
# Financial Datasets REST — RE-WIRED 2026-08-29 (user-directed)
# ----------------------------------------------------------------------------
# Retired 2026-08-14 when the subscription was cancelled; restored on 2026-08-29
# at the user's direction ("wire FD in the system so u can use big money score and
# get insider information and filing, given polygon does not have that"), because
# v6.1 makes Big Money a SCORED 0-5 component again and Polygon carries no Form 4
# insider trades, no 13F and no SEC filings.
#
# STATE OF THE SUBSCRIPTION: **LIVE, verified 2026-08-29** — /insider-trades/
# returned real Form 4 rows for DELL. An earlier probe in the same session reported
# HTTP 403 only because it omitted the trailing slash in the path; the key at
# ~/.claude/.financialdatasets_key works. The 2026-08-14 retirement note that called
# this key dead is therefore WRONG and is corrected here.
#
# Helpers still FAIL SOFT (return {} / [] rather than raising) so that a future
# lapse degrades Big Money to openinsider instead of breaking a pick run.
#
# PAGINATION (data-integrity fix 2026-09-07): every FD list endpoint returns AT
# MOST 10 rows per response no matter what `limit` says, and signals more with a
# `next_page_url` (an absolute https://api.financialdatasets.ai/... cursor URL);
# it stops issuing one once `limit` rows have been served or the data / date
# window is exhausted. Until this fix fd_insider_trades() read page 1 only, so
# every ticker's Signal-A input was silently capped at its 10 most recent Form 4
# LINE ITEMS (one row per price lot): ALAB's 2026-09-01 director sale — 24 lots,
# $51.26M per the SEC filing — read as 2 lots / $6.56M, an ~8x undercount that
# fed the Big Money hard_reject filter. _fd_paged() now walks the chain (same
# host only, <= FD_MAX_PAGES requests), and insider_trades_best() asks for the
# FULL 30-day filing window (filing_date_gte) instead of a row count, because a
# 30-day window on a heavy filer is 90-100 rows (ALAB 99, META 94 on 2026-09-07)
# — a 50-row cap would still have truncated exactly the multi-lot sellers the
# filter exists to catch. Measured 2026-09-07: ~0.55-0.7 s per page; 12 heavy
# filers needed 1-10 pages each for the 30-day window; a typical $2B+ name is one
# page, so a breadth pass costs 1 probe + 1-10 requests per ticker (was 1 + 1).
# fd_institutional_ownership was re-pointed the same day: /institutional-ownership/
# now answers HTTP 410 "deprecated" -> /institutional-holdings/ (same 10-row pages,
# a different row schema — see its docstring).
#
# NOTE ON SPEND: nothing here buys anything. If the subscription ever does lapse,
# the cost to restore is ~$5-10/month at finalists-only volume (a $20/1,000-credit
# pack), NOT the ~$200 figure retired on 2026-08-21 — and it is the user's call
# alone (charter §3.3).
# ============================================================================
FD = 'https://api.financialdatasets.ai'


def fd_key():
    k = os.environ.get('FINANCIALDATASETS_API_KEY')
    if k:
        return k.strip()
    try:
        return open(os.path.expanduser('~/.claude/.financialdatasets_key')).read().strip()
    except Exception:
        return ''


def fd_available():
    """True only if a key exists AND the API answers. Cached per process."""
    global _FD_OK
    try:
        return _FD_OK
    except NameError:
        pass
    ok = False
    if fd_key():
        try:
            req = urllib.request.Request(
                FD + '/insider-trades/?ticker=AAPL&limit=1',
                headers={'X-API-KEY': fd_key(), 'User-Agent': 'uspicks/1.0'})
            with urllib.request.urlopen(req, timeout=15):
                ok = True
        except Exception:
            ok = False
    globals()['_FD_OK'] = ok
    return ok


FD_PAGE_ROWS = 10        # server-side cap per response (measured 2026-09-07); a larger `limit` is PAGED
FD_MAX_PAGES = 50        # safety cap on one cursor walk: 500 rows ~ 30 s at the measured ~0.6 s/page
FD_INSIDER_LOOKBACK_DAYS = 30   # Signal-A window — us-bigmoney-analyzer.md "Look back: last 30 days" (filing-date basis)


def _fget_url(url, retries=3):
    """FAIL-SOFT GET of an ABSOLUTE FD URL (the `next_page_url` cursors are absolute).
    Returns the parsed JSON dict, or {} on any failure. {} carries no list key, which is
    how callers tell a FAILED fetch from a genuinely EMPTY page ({'insider_trades': []})."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={'X-API-KEY': fd_key(), 'User-Agent': 'uspicks/1.0'})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(_BACKOFF[min(attempt, len(_BACKOFF) - 1)]); continue
            return {}
        except Exception:
            if attempt < retries - 1:
                time.sleep(_BACKOFF[min(attempt, len(_BACKOFF) - 1)]); continue
            return {}
    return {}


def _fget(path, retries=3):
    """FAIL-SOFT (v6.1): returns {} instead of raising, so a dead subscription
    degrades Big Money to its fallback rather than breaking a pick run."""
    return _fget_url(FD + path, retries)


def _fd_paged(path, key, limit, max_pages=FD_MAX_PAGES):
    """Walk an FD list endpoint through its `next_page_url` cursor chain (2026-09-07).

    Returns (rows, ok, pages, partial):
      rows     the concatenated list under `key`, newest-first as served, cut at `limit`
      ok       False iff the FIRST page failed (no `key` in the response) — the caller
               treats that as "FD did not serve this ticker" and falls back a rung
      pages    number of requests made
      partial  True when a LATER page failed after retries, the page cap was hit, or an
               off-host cursor was refused — `rows` is what was gathered so far
    An empty page ({key: []}) is a successful fetch with zero rows, never a failure.
    Only same-host cursors are followed (the API key travels in the header).
    """
    rows, pages, partial = [], 0, False
    url = FD + path
    tag = path.split('?')[0]
    while True:
        if pages >= max_pages:
            partial = True
            sys.stderr.write('uspicks_data: FD %s hit the %d-page cap — %d rows may be incomplete\n'
                             % (tag, max_pages, len(rows)))
            break
        body = _fget_url(url)
        pages += 1
        if not isinstance(body, dict) or key not in body:
            if pages == 1:
                return [], False, pages, False
            partial = True
            sys.stderr.write('uspicks_data: FD %s page %d failed after retries — returning %d partial rows\n'
                             % (tag, pages, len(rows)))
            break
        rows.extend(body.get(key) or [])
        nxt = body.get('next_page_url')
        if not nxt or len(rows) >= limit:
            break
        if not str(nxt).startswith(FD + '/'):
            partial = True
            sys.stderr.write('uspicks_data: FD %s returned an off-host next_page_url — refusing to follow it (%d rows kept)\n'
                             % (tag, len(rows)))
            break
        url = nxt
    return rows[:limit], True, pages, partial


def fd_insider_trades_ex(ticker, limit=500, since=None, until=None, max_pages=FD_MAX_PAGES):
    """Form 4 insider transactions WITH fetch provenance — (rows, ok, pages, partial).
    `since` / `until` are ISO dates applied server-side as filing_date_gte / _lte (the
    filing-date basis openinsider's FilingDateFrom uses). Each row is ONE Form 4 line
    item — a single 10b5-1 sale can span 20+ lots at different prices — so aggregate by
    insider before applying any dollar threshold."""
    path = '/insider-trades/?ticker=%s&limit=%d' % (ticker, limit)
    if since:
        path += '&filing_date_gte=%s' % since
    if until:
        path += '&filing_date_lte=%s' % until
    return _fd_paged(path, 'insider_trades', limit, max_pages)


def fd_insider_trades(ticker, limit=50, since=None, until=None):
    """Form 4 insider transactions (list). Polygon has no equivalent — this is the whole
    reason FD was re-wired. Paginated since 2026-09-07: the API serves <= 10 rows per
    response, so `limit` is honoured by walking `next_page_url`. Empty list when the
    subscription is inactive OR the fetch failed — use fd_insider_trades_ex() /
    insider_trades_best() when the caller must tell those apart."""
    return fd_insider_trades_ex(ticker, limit, since, until)[0]


def fd_filings(ticker, limit=20):
    """SEC filings index. Polygon has no equivalent. Paginated (10 rows/response)."""
    return _fd_paged('/filings/?ticker=%s&limit=%d' % (ticker, limit), 'filings', limit)[0]


def fd_institutional_ownership(ticker, limit=20):
    """13F holders. Polygon has no equivalent (dataroma/whalewisdom is the scrape).
    2026-09-07: FD retired /institutional-ownership/ (HTTP 410 "deprecated") in favour
    of /institutional-holdings/ — same query shape, rows under `institutional_holdings`
    (filer_name, filer_cik, shares, value_usd, report_period, filing_date, form_type,
    put_call ...), 10 rows/response, paginated. Re-pointed here; the ROW SCHEMA differs
    from the retired endpoint's."""
    return _fd_paged('/institutional-holdings/?ticker=%s&limit=%d' % (ticker, limit),
                     'institutional_holdings', limit)[0]


def insider_trades_best(ticker, limit=500, lookback_days=FD_INSIDER_LOOKBACK_DAYS):
    """The Big Money Signal-A entry point (v6.1; window-complete since 2026-09-07).

    Returns (rows, source) where source is one of:
        'financialdatasets'  the licensed Form 4 feed served THIS ticker (rows may be
                             empty — a genuine no-insider-activity window is still data)
        'openinsider'        FD did not serve the ticker — subscription inactive, OR this
                             ticker's fetch failed after retries — caller performs the WebFetch
        'none'               is the CALLER's token when its own fallback also fails

    Rows = EVERY Form 4 line item filed in the last `lookback_days` days (filing-date
    basis, server-side filing_date_gte), walked through the API's 10-row pages up to
    `limit` rows / FD_MAX_PAGES requests. Before 2026-09-07 this returned only the 10
    most recent rows whatever the requested count (ALAB's $51.26M / 24-lot director sale
    read as 2 lots / $6.56M). A LATER-page failure keeps the rows gathered and prints
    one stderr WARN line (the label stays 'financialdatasets' — FD did serve the ticker).

    The `source` token feeds rule L1's `bm_source` field, so the default rate is
    measurable week to week rather than assumed.
    """
    if not fd_available():
        return [], 'openinsider'                 # caller performs the WebFetch
    since = None
    if lookback_days:
        since = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
    rows, ok, _pages, _partial = fd_insider_trades_ex(ticker, limit, since=since)
    if not ok:
        return [], 'openinsider'                 # this ticker's FD fetch failed -> next rung
    return rows, 'financialdatasets'


# ----------------------------------------------------------------------------
# News (Polygon / Benzinga-sourced) — for Catalyst / Sentiment / Big Money
# ----------------------------------------------------------------------------
def polygon_news(ticker, limit=10):
    """Ticker-tagged news headlines + insights (Polygon). Each item: title, published_utc,
       article_url, publisher, description, insights[{sentiment, sentiment_reasoning}]."""
    d = _pget('/v2/reference/news', {'ticker': ticker, 'limit': str(limit),
                                     'order': 'desc', 'sort': 'published_utc'})
    return d.get('results') or []


# ----------------------------------------------------------------------------
# Corporate actions, short interest, macro, snapshot (added 2026-06-14)
#   Additive data sources — no change to scoring/grading. Wired into:
#   dividends -> us-risk-assessor (ex-div flag); short_interest / short_volume ->
#   us-catalyst-hunter (squeeze signal); treasury_yields -> us-market-macro (10Y +
#   curve, replaces the WebSearch read); market_snapshot -> uspicks_premarket_check.
#   All sort newest-first client-side so default API ordering can't surprise us.
# ----------------------------------------------------------------------------
def dividends(ticker, limit=8):
    """Recent + upcoming cash dividends (newest ex-date first). Row keys:
       ex_dividend_date, cash_amount, declaration_date, pay_date, record_date,
       frequency, dividend_type. Risk Assessor flags an ex-date inside the pick week.
       Windowed to the last ~60d + future so upcoming ex-dates are included."""
    floor = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    d = _pget('/v3/reference/dividends',
              {'ticker': ticker, 'ex_dividend_date.gte': floor, 'limit': '200'})
    rows = d.get('results') or []
    rows.sort(key=lambda r: r.get('ex_dividend_date') or '', reverse=True)
    return rows[:limit]


def short_interest(ticker, limit=8):
    """Bi-weekly FINRA short interest (newest settlement first). Row keys:
       settlement_date, short_interest (shares), avg_daily_volume, days_to_cover.
       days_to_cover is the headline squeeze metric (short shares / avg volume).
       NOTE: this endpoint ignores order/sort and defaults OLDEST-first, so we window
       with `.gte` then sort newest-first client-side (a plain limit returns 2017)."""
    floor = (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%d')
    d = _pget('/stocks/v1/short-interest',
              {'ticker': ticker, 'settlement_date.gte': floor, 'limit': '500'})
    rows = d.get('results') or []
    rows.sort(key=lambda r: r.get('settlement_date') or '', reverse=True)
    return rows[:limit]


def short_volume(ticker, limit=10):
    """Daily FINRA short volume (newest first). Row keys: date, total_volume,
       short_volume, short_volume_ratio (+ per-venue breakdowns). A rising
       short_volume_ratio corroborates a squeeze setup. Same oldest-first default
       as short_interest -> window with `.gte` + client sort."""
    floor = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    d = _pget('/stocks/v1/short-volume',
              {'ticker': ticker, 'date.gte': floor, 'limit': '500'})
    rows = d.get('results') or []
    rows.sort(key=lambda r: r.get('date') or '', reverse=True)
    return rows[:limit]


def treasury_yields(limit=1):
    """Latest US Treasury constant-maturity yields (newest date first). Row keys:
       date, yield_1_month .. yield_30_year (only populated maturities present).
       Replaces the Market Macro WebSearch 10Y read (yield_10_year). This endpoint
       also defaults OLDEST-first (a plain limit returns 1962) -> window + client sort."""
    floor = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    d = _pget('/fed/v1/treasury-yields', {'date.gte': floor, 'limit': '500'})
    rows = d.get('results') or []
    rows.sort(key=lambda r: r.get('date') or '', reverse=True)
    return rows[:limit]


def market_snapshot(tickers):
    """Full-market snapshot limited to `tickers` (list or comma str) -> {ticker: snap}.
       snap.lastTrade.p reflects PRE-MARKET / after-hours trades, so it is the live
       gap-check price before the open; snap.todaysChangePerc is vs the prior regular
       close. Used by uspicks_premarket_check.py (Monday gap check)."""
    if isinstance(tickers, (list, tuple)):
        tickers = ','.join(tickers)
    d = _pget('/v2/snapshot/locale/us/markets/stocks/tickers', {'tickers': tickers})
    return {t.get('ticker'): t for t in (d.get('tickers') or []) if t.get('ticker')}


# ----------------------------------------------------------------------------
# Paid Polygon partner add-ons (subscribed 2026-06-14, $99/mo each):
#   Benzinga Analyst Ratings -> benzinga_ratings (Catalyst Phase 4)
#   TMX / Wall Street Horizon Corporate Events -> corporate_events + next_earnings_date
#     (fixes the forward-earnings-DATE gap: Catalyst Phase 1 + Risk gap-risk)
# ----------------------------------------------------------------------------
def benzinga_ratings(ticker, limit=10):
    """Analyst ratings + price-target actions (newest first) — Polygon Benzinga add-on.
       Row keys: date, time, rating_action (upgrades/downgrades/initiates/maintains/
       reiterates), rating, previous_rating, price_target_action (raises/lowers),
       price_target, previous_price_target, price_percent_change, firm, analyst,
       importance (0-5), company_name. Feeds Catalyst Hunter Phase 4.
       Defaults newest-first; client sort as backstop."""
    d = _pget('/benzinga/v1/ratings', {'ticker': ticker, 'limit': str(max(limit, 20))})
    rows = d.get('results') or []
    rows.sort(key=lambda r: (r.get('date') or '', r.get('time') or ''), reverse=True)
    return rows[:limit]


def corporate_events(ticker, types=None, after=None, limit=50):
    """TMX / Wall Street Horizon corporate events (forward + recent), sorted by date
       ASC (soonest first). Row keys: date, type, status, name, company_name, ticker, url.
       `type` includes earnings_announcement_date (the forward earnings DATE — fixes the
       long-standing gap), earnings_results_announcement, dividend, stock_split,
       conference, shareholder_meeting, business_update, interim_statement. `status`:
       unconfirmed/confirmed/approved/historical; `name` often carries BMO/AMC.
         after  ISO date floor (default = 7 days ago -> just-happened + all upcoming)
         types  optional str / list of `type` values to keep"""
    if after is None:
        after = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    d = _pget('/tmx/v1/corporate-events', {'ticker': ticker, 'date.gte': after, 'limit': str(limit)})
    rows = d.get('results') or []
    if types:
        keep = {types} if isinstance(types, str) else set(types)
        rows = [r for r in rows if r.get('type') in keep]
    rows.sort(key=lambda r: r.get('date') or '')
    return rows


def next_earnings_date(ticker):
    """The soonest UPCOMING earnings-announcement date for `ticker` (TMX), or None.
       Returns the event dict {date, status, name (BMO/AMC), ...}. Replaces the WebSearch
       forward-earnings lookup in Catalyst Phase 1 + Risk gap-risk."""
    today = datetime.now().strftime('%Y-%m-%d')
    evs = corporate_events(ticker, types=['earnings_announcement_date'], after=today, limit=20)
    return evs[0] if evs else None


# ----------------------------------------------------------------------------
# Index membership — S&P 500 (added v5.3, 2026-07-14) ∪ Nasdaq-100 (added v5.5,
# 2026-07-23). ROLE CHANGED in v5.6 (2026-07-28, user-directed): these lists no
# longer DEFINE the pick universe (which is the whole mid-to-mega market again) —
# they are CONTEXT annotations on each scanned row. Both functions still fail loud
# when neither their live source nor their cache is available; it is the CALLER
# (uspicks_price_scan.py) that now decides a missing annotation is non-fatal.
# ----------------------------------------------------------------------------
SP500_URL = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
SP500_CACHE = os.path.expanduser('~/.claude/stocks/sp500-members.json')


def sp500_members():
    """Current S&P 500 constituents as a set of tickers ('.'->'-' normalized to
    match the scan universe convention, e.g. BRK-B). Returns (tickers, source).

    Source order: (1) LIVE — the Wikipedia constituents table (updated within
    ~a day of index changes; the same page the price scan already uses as a
    universe supplement), cached to SP500_CACHE on every good fetch; (2) the
    cached last-good list when the live fetch/parse fails. A parse yielding an
    implausible count (outside 480-520) is treated as a FAILED fetch — a broken
    page layout must never silently garble the list.
    (FD's /index-funds SPY holdings were evaluated 2026-07-14 and rejected as
    the primary: N-PORT-sourced, ~2-3 months stale.)

    FAILS LOUD (RuntimeError) when neither source is available. Under v5.3-v5.5
    that was load-bearing (membership GATED the pick universe, so running
    unrestricted would have been a silent universe downgrade). Since v5.6
    (2026-07-28) membership is context-only, so the price scan CATCHES this and
    continues without the annotation — but the raise stays, both for callers that
    do need a real list and so that re-gating the universe is a one-line change."""
    err = None
    try:
        req = urllib.request.Request(SP500_URL, headers={'User-Agent': 'uspicks/1.0'})
        html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
        m = re.search(r'<table[^>]*id="constituents"[^>]*>(.*?)</table>', html, re.S)
        syms = []
        if m:
            for tr in m.group(1).split('<tr')[2:]:  # [0]=pre-row junk, [1]=header row
                td = re.search(r'<td[^>]*>\s*(?:<a[^>]*>)?([A-Z][A-Z0-9.\-]{0,6})(?:</a>)?', tr)
                if td:
                    syms.append(td.group(1).replace('.', '-'))
        if 480 <= len(syms) <= 520:
            tickers = sorted(set(syms))
            try:
                os.makedirs(os.path.dirname(SP500_CACHE), exist_ok=True)
                with open(SP500_CACHE, 'w') as f:
                    json.dump({'as_of': datetime.now().strftime('%Y-%m-%d'),
                               'source': 'wikipedia', 'tickers': tickers}, f)
            except OSError:
                pass  # cache write failure must not fail a good live fetch
            return set(tickers), 'wikipedia-live (%d tickers)' % len(tickers)
        err = 'parse returned %d symbols (expected ~503)' % len(syms)
    except Exception as e:
        err = repr(e)
    try:
        c = json.load(open(SP500_CACHE))
        tk = c.get('tickers') or []
        if len(tk) >= 480:
            return set(tk), 'CACHE as-of %s (%d tickers) — live fetch failed: %s' % (
                c.get('as_of'), len(tk), err)
    except Exception:
        pass
    raise RuntimeError(
        'S&P 500 membership unavailable (live fetch: %s; no valid cache at %s). '
        'Never returns a partial/empty list silently — fix connectivity or the '
        'parse, or restore the cache file. (Since v5.6 the price scan treats this '
        'as a missing CONTEXT annotation and continues; any caller that needs a '
        'real membership list must handle this raise.)' % (err, SP500_CACHE))


NDX_URL = 'https://api.nasdaq.com/api/quote/list-type/nasdaq100'
NDX_CACHE = os.path.expanduser('~/.claude/stocks/ndx-members.json')


def ndx_members():
    """Current Nasdaq-100 constituents as a set of tickers ('.'->'-' normalized,
    same convention as sp500_members). Returns (tickers, source).

    Source order: (1) LIVE — Nasdaq's own index-constituents API (the index
    operator's feed; browser-style headers required, the endpoint rejects plain
    urllib UAs), cached to NDX_CACHE on every good fetch; (2) the cached
    last-good list when the live fetch/parse fails. A parse outside 95-110
    symbols is treated as a FAILED fetch — the index holds ~100-103 listings
    (dual-class lines included). Wikipedia was evaluated 2026-07-23 and
    REJECTED as the source: its Nasdaq-100 article no longer carries a
    components table (external links only), so the sp500_members scrape
    pattern does not transfer.

    FAILS LOUD (RuntimeError) when neither source is available — same contract as
    sp500_members(), and since v5.6 (2026-07-28) the same context-only role: the
    price scan catches the raise because membership no longer gates picking."""
    err = None
    try:
        req = urllib.request.Request(NDX_URL, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Accept': 'application/json, text/plain, */*'})
        raw = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
        rows = ((json.loads(raw).get('data') or {}).get('data') or {}).get('rows') or []
        syms = set()
        for r in rows:
            s = (r.get('symbol') or '').strip()
            if s and re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,6}', s):
                syms.add(s.replace('.', '-'))
        if 95 <= len(syms) <= 110:
            tickers = sorted(syms)
            try:
                os.makedirs(os.path.dirname(NDX_CACHE), exist_ok=True)
                with open(NDX_CACHE, 'w') as f:
                    json.dump({'as_of': datetime.now().strftime('%Y-%m-%d'),
                               'source': 'nasdaq-api', 'tickers': tickers}, f)
            except OSError:
                pass  # cache write failure must not fail a good live fetch
            return set(tickers), 'nasdaq-api-live (%d tickers)' % len(tickers)
        err = 'parse returned %d symbols (expected ~100-103)' % len(syms)
    except Exception as e:
        err = repr(e)
    try:
        c = json.load(open(NDX_CACHE))
        tk = c.get('tickers') or []
        if len(tk) >= 95:
            return set(tk), 'CACHE as-of %s (%d tickers) — live fetch failed: %s' % (
                c.get('as_of'), len(tk), err)
    except Exception:
        pass
    raise RuntimeError(
        'Nasdaq-100 membership unavailable (live fetch: %s; no valid cache at %s). '
        'Never returns a partial/empty list silently — fix connectivity or the '
        'parse, or restore the cache file. (Since v5.6 the price scan treats this '
        'as a missing CONTEXT annotation and continues; any caller that needs a '
        'real membership list must handle this raise.)' % (err, NDX_CACHE))


# ----------------------------------------------------------------------------
# Smoke test:  python3 ~/.claude/scripts/uspicks_data.py [DATE]
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    date = sys.argv[1] if len(sys.argv) > 1 else '2026-06-05'
    print('--- polygon REST ---')
    td = ticker_details('AAPL')
    print('ticker_details AAPL: mkt_cap=%s sector=%s' % (td['market_cap'], td['sector']))
    g = grouped_daily(date)
    print('grouped_daily %s: %d tickers; AAPL close=%s' % (date, len(g), g.get('AAPL', {}).get('c')))
    ah, reg = after_hours_close('AAPL', date)
    print('after_hours_close AAPL %s: ah=%s reg=%s' % (date, ah, reg))
    aht, regt, srct = after_hours_close_tick('AAPL', date)
    print('after_hours_close_tick AAPL %s: ah=%s reg=%s src=%s' % (date, aht, regt, srct))
    oc = options_chain('AAPL', limit=50)
    print('options_chain AAPL: %d contracts; sample IV=%s' %
          (len(oc), (oc[0].get('implied_volatility') if oc else None)))
    print('--- flat files ---')
    try:
        rc = regular_close_all(date)
        print('regular_close_all: %d tickers; AAPL=%s' % (len(rc), rc.get('AAPL')))
        ahall = afterhours_close_all(date)
        print('afterhours_close_all: %d tickers; AAPL=%s' % (len(ahall), ahall.get('AAPL')))
    except Exception as ex:
        print('flatfile ERR:', type(ex).__name__, str(ex)[:200])
    print('--- corporate actions / short / macro / snapshot (2026-06-14) ---')
    dv = dividends('AAPL', 2)
    print('dividends AAPL: %d rows; latest ex-date=%s' % (len(dv), dv[0].get('ex_dividend_date') if dv else None))
    si = short_interest('AAPL', 2)
    print('short_interest AAPL: %d rows; latest days_to_cover=%s' % (len(si), si[0].get('days_to_cover') if si else None))
    sv = short_volume('AAPL', 2)
    print('short_volume AAPL: %d rows; latest short_volume_ratio=%s' % (len(sv), sv[0].get('short_volume_ratio') if sv else None))
    ty = treasury_yields(1)
    print('treasury_yields: latest date=%s 10Y=%s' % ((ty[0].get('date'), ty[0].get('yield_10_year')) if ty else (None, None)))
    snap = market_snapshot(['AAPL', 'MSFT'])
    aapl = snap.get('AAPL', {})
    print('market_snapshot: %d tickers; AAPL last=%s todaysChangePerc=%s' % (
        len(snap), (aapl.get('lastTrade') or {}).get('p'), aapl.get('todaysChangePerc')))
    print('--- paid add-ons (Benzinga ratings + TMX events, 2026-06-14) ---')
    br = benzinga_ratings('AAPL', 1)
    print('benzinga_ratings AAPL: %d rows; latest %s %s/%s PT->%s %s' % (
        len(br), br[0].get('date'), br[0].get('rating_action'), br[0].get('price_target_action'),
        br[0].get('price_target'), br[0].get('firm')) if br else 'benzinga_ratings EMPTY')
    ne = next_earnings_date('AAPL')
    print('next_earnings_date AAPL:', (ne.get('date'), ne.get('status'), ne.get('name')) if ne else None)
    print('--- Financial Datasets (fail-soft; cursor-paginated since 2026-09-07) ---')
    if fd_available():
        it, src = insider_trades_best('AAPL')
        print('insider_trades_best AAPL: %d Form 4 rows in the 30-day filing window; source=%s' % (len(it), src))
    else:
        print('insider_trades_best: FD unavailable -> source=openinsider (fallback rung)')
