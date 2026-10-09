# /us-picks Heads-Up Flags — Glossary & Render Spec

> **Single source of truth** for the **HEADS-UP FLAGS** table that renders at the TOP of every `/us-picks` pick card (and skip-week output).
>
> **Why this exists (2026-06-06).** An in-window NFP (monthly jobs report) macro-binary risk for week-of-2026-06-01 was surfaced only as buried prose in the tracker week header. The user skimmed past it; that Friday a hot-jobs "good news is bad news" session cut the US market ~$2T. Fix: surface EVERY risk/warning a pick run raises in ONE prominent, plain-English table so nothing important is ever buried in prose again.
>
> **Read by:** `commands/us-picks.md` Phase 5.1.5 (build the table) → Phase 5.2 (render at top of pick card) / Phase 3.6 (render on skip-week). Part of the `us-stocks-memory` skill (GitHub allowlist).

---

## 1. Severity levels (sort order)

| Level | Dot | Plain meaning | Sort |
|-------|-----|---------------|------|
| HIGH  | 🔴  | Could cost real money, or the WHOLE market can lurch | 1st (top) |
| MED   | 🟡  | Tilts the odds against you — size down / be careful  | 2nd |
| INFO  | ⚪  | Good to know, no action needed                       | 3rd (bottom) |

Rows ALWAYS render sorted **HIGH → MED → INFO** so the scariest flags sit on top and never get skimmed past. The rendered table uses the **text** level (`HIGH`/`MED`/`INFO`) in the grid (emoji break monospace column alignment); the dots live only in this glossary's legend table above — the §5 script's rendered legend line is plain text, dot-free.

## 2. Plain-English mandate (HARD RULE)

Every cell must pass the **"smart 14-year-old" test** — NO Wall-Street jargon. If a term is unavoidable, define it inline with an everyday analogy. Use this jargon→plain map (extend as needed, never regress):

| Jargon | Say instead |
|--------|-------------|
| NFP / non-farm payrolls / jobs Friday | the monthly **jobs report** (the government's count of new jobs) |
| CPI | the monthly **inflation report** (how fast everyday prices are rising) |
| PPI | **wholesale inflation** — what businesses pay before goods hit shelves |
| FOMC / the Fed / hawkish / dovish | the **Federal Reserve's interest-rate decision**; hawkish = "wants to keep money expensive (high rates)"; dovish = "ready to make money cheaper" |
| OPEX / options expiration | the day large side-bets called **options** all come due at once (usually the 3rd Friday) |
| BMO / AMC | **before the market opens** / **after it closes** |
| gap / gap down | the stock can **open the next morning far below** where it closed |
| priced-in | **the good news already happened and the stock already jumped; you'd be late** |
| catalyst | a real piece of **company news or event** that can move the stock |
| binary event | a **coin-flip moment** that resolves yes/no and can swing the stock either way |
| RSI / overbought | a **how-hard-has-this-been-bought meter**; high = stretched, overdue for a snap-back |
| ATR | the stock's **normal day-to-day price swing** |
| stop / stop-loss | your **automatic safety-net sell order** that cuts losses; "whipsaw" = bumped out by random noise |
| liquidity / thin / illiquid | **how many dollars trade per day**; thin = your own order moves the price |
| volatility / chop | **how wildly the price swings** day to day |
| implied move / IV | **option traders are bracing for a big swing** |
| put/call ratio / bearish flow | **option traders heavily betting the stock will fall** |
| short interest / short squeeze | **people betting the stock will fall; a forced bail-out can spike it up** |
| dilution / S-1 / S-3 | the company is about to **print and sell new shares**, making each existing share worth less |
| insider selling / Form 4 / hard_reject | **company bosses selling large amounts of their own shares** |
| 13F / institutional distribution | **big investment funds trimming or exiting** their stake |
| buyback / ASR | the company **buying back its own shares** (a confidence sign) — but an announced plan ≠ actually doing it |
| analyst downgrade | **professional stock-raters lowering their opinion** |
| pump / social-only | **promoters hyping a price online** to sell to latecomers |
| DXY / strong dollar | the **dollar is strong** vs other currencies (a quiet drag on big exporters & commodities) |
| 10Y / Treasury yield | the **government's borrowing interest rate**; high rates hit fast-growing stocks hardest |
| VIX / fear regime | the market's **fear gauge**; high = traders bracing for big swings |
| risk-off / sector rotation / defensive | **money fleeing risky stocks for safe, boring ones** (a nervous signal) |
| calm / quiet "tape" · risk-on tape | the **market overall** ("the tape"); calm/quiet = **small daily moves, low fear**; "risk-on" = **money flowing into riskier stocks** |
| ex-dividend | the **cutoff day to qualify for a cash payout**, when the price mechanically ticks down by the payout |
| index rebalance | a stock **added to / dropped from a famous list** (e.g. the S&P 500), forcing funds to buy or sell it |
| rank-based WIN | a **WIN = the stock beat most others that week**, NOT that you personally made money |

## 3. The 12 flag categories

Each category becomes at most ONE row per week (shared flags list their tickers in `HITS`). Source = which agent/phase raises it.

| # | Category (plain FLAG name) | Default level | Scope | What fires it (source) | Plain meaning + action |
|---|----------------------------|---------------|-------|------------------------|------------------------|
| 1 | **Big scheduled event** | HIGH (jobs/inflation/Fed) · MED (options-expiry) | whole-week | Market Macro calendar alerts; Phase-0 OPEX | A government report or Fed rate decision lands this week — the whole market can jump/drop several % regardless of your stocks, and *good* economic news can still sink stocks (it can mean rates stay high). → Mark the date; size down / brace. |
| 2 | **Pick reports this week** | HIGH (earnings) · MED (recent 8-K / event) · INFO (ex-dividend) | per-pick | Catalyst Hunter (in-window earnings, recent material filing); Risk Assessor (event, ex-div) | This stock has its own big day during your holding week — a coin-flip that can gap 10%+ overnight, past your safety-net sell. → A binary event: the result can move the stock sharply either way. |
| 3 | **Old news — you'd be late** | MED | per-pick | Catalyst Hunter (resolved/priced-in freshness booleans, politician-trade lag; F3 + B2 both deactivated — flag is informational only) | The exciting news already happened and the stock already jumped — easy gains may be gone. → Lower expectations; don't chase. |
| 4 | **Ran too hot** | MED | per-pick | Price Analyzer (overbought / near highs / explosive spike) | Bought up so fast it's stretched like a rubber band, near its highs with little cushion. → Don't chase; a normal cool-off could trip your stop. |
| 5 | **Weak safety-net** | MED | per-pick | Risk Assessor (stop too wide / too tight / backup-method stop) | The auto-sell price is set badly — so far below you'd lose a lot first, or so close that normal wiggles eject you. → Set your own exit; size smaller. |
| 6 | **Wild or thin** | MED (wild / thin) · INFO (too quiet) | per-pick | Price Analyzer (volatility, liquidity, short interest) | Either huge daily swings (noise shakes you out), or so few shares trade your own order moves the price, or so calm it can't be a top gainer. → Smaller size; use price limits. |
| 7 | **Thin or hyped reason** | MED | per-pick | Sentiment Scanner + Catalyst Hunter (no real catalyst / social-only / anti-pump guard) | The reason to own it is weak — no real company news, just chart momentum or loud online hype (the classic "pump" fingerprint). → Steer clear if it can't be traced to an official source. |
| 8 | **Backers leaving / negative** | HIGH (insiders dumping → advisory, you decide) · MED (fading backing) | per-pick | Big Money (insider selling, hard_reject), Sentiment (downgrade, dilution), Options (heavy put-buying) | Company bosses selling their own shares heavily (a 🔴 HIGH **advisory** flag since 2026-06-26 — you decide whether to skip; it no longer auto-removes the pick), or funds trimming / analysts cutting / new shares coming / option traders betting it falls. → Weigh against the bull case. |
| 9 | **Rough or crowded market** | MED (HIGH if market falling + fear gauge >25) | whole-week | Market Macro (mood, fear gauge, rates, dollar, rotation) + sentiment extremes (greed gauge, narrow breadth); Sector Momentum (all-picks-same-theme) | The whole market is sour/falling OR euphoric/over-crowded (a contrarian warning) — a headwind that drags most stocks down. Also fires when all picks sit in one theme (one basket). → Extra caution; smaller positions or sit out; spread out if concentrated. |
| 10 | **Short or odd week** | MED | whole-week | Phase 0.3 (holiday, early close, suboptimal-midweek run); Phase 5.1 (tiny-target sell sequencing) | Not a normal full week — a holiday closes a day, the market closes early, or you ran it mid-week so scoring days are already gone. → Smaller window, lower hit chance; the final sell-everything moment shifts to the last open day; run on Sunday for best results. |
| 11 | **Data behind picks shaky** | HIGH | whole-week | Any agent: data-login expired, feed down/rate-limited, scan didn't finish, missing market cap, holiday calendar aged out | Some data feeding this run is missing or came from a rougher backup — parts of the analysis rest on less reliable numbers. → Treat picks with extra caution; fix the data issue (often re-log into the data service); if a scan didn't finish, consider postponing. |
| 12 | **System auto-handled** | INFO | whole-week | Phase 3.5 filters (market-cap / price-floor / Sharia), disclaimers, benign single-source fallbacks, prompt-injection guards | Things the system quietly took care of — auto-removing tiny/cheap/faith-screened names, ignoring web pages that try to trick it into hyping a stock, skipping a bad week. → No action. Two facts worth knowing: a "WIN" = ranked above most stocks that week, NOT your actual profit; a blank "no picks" week is intentional and healthy, not a glitch. |

## 4. Table format & build rules

- **Placement:** a fenced code block at the VERY TOP of the Phase 5 output — above the MARKET CONTEXT / pick-card box. First thing the eye hits. _(Since 2026-06-17, the advisory **MARKET REGIME banner** — Phase 5.1.4 — renders ONE step higher, immediately above this Heads-Up table: regime + run/skip advice headline first, then this per-pick risk index. The banner is the headline form of the Category 9 "rough/crowded market" macro-regime signal; display-only — the B2 −5 dock it used to arm was deactivated 2026-07-02.)_
- **Columns:** `LVL | FLAG | HITS | WHAT IT MEANS / WHAT TO DO`. Fixed widths (below) so columns never drift.
- **One row per FIRING flag**, not per possible flag. A clean week shows 3–8 rows. When several picks trip the SAME flag, they share ONE row and the `HITS` cell lists the tickers (e.g. `OKTA, IBM, ESTC`); whole-week flags say `ALL PICKS` or `THIS WEEK`.
- **`HITS` is the column the user specifically wanted** — it must name exactly which picks each flag touches.
- **Sort HIGH → MED → INFO.** All benign housekeeping collapses into the single `INFO / System auto-handled` row — it must never crowd out the 🔴/🟡 rows. Hard cap ~10 rows: keep every HIGH + MED individually, roll any remaining INFO into the one summary row.
- **Clean week:** if nothing fires beyond standard cautions, render one line instead of the grid: `>> No flags this week — standard cautions apply (see DISCLAIMER).`
- **Plain-English mandate (§2) applies to every cell.** No jargon.
- The table is an at-a-glance INDEX; the full per-pick detail still lives in each pick's own block below.

## 5. Render script (run this — guarantees aligned columns)

Phase 5.1.5 fills the `FLAGS` list (level, flag, hits, meaning — meaning ends with a `→` action) and runs this. Widths are fixed: `LVL=4, FLAG=22, HITS=16, MEAN=44`. Levels sort HIGH→MED→INFO automatically.

```python
import textwrap
W_LVL, W_FLAG, W_HITS, W_MEAN = 4, 22, 16, 44
ORDER = {"HIGH": 0, "MED": 1, "INFO": 2}

# === Phase 5.1.5 fills this list with the week's FIRING flags only ===
FLAGS = [
    # ("HIGH"|"MED"|"INFO", "Flag name", "HITS (tickers / ALL PICKS / -)", "plain-English meaning. -> action"),
]
WEEK = "YYYY-MM-DD"

FLAGS.sort(key=lambda r: ORDER.get(r[0], 9))

def bar():
    return ("+"+"-"*(W_LVL+2)+"+"+"-"*(W_FLAG+2)+"+"+"-"*(W_HITS+2)+"+"+"-"*(W_MEAN+2)+"+")

def cell(s, w):
    return " " + s.ljust(w) + " "

print(f"=> HEADS-UP FLAGS  -  Week of {WEEK}   (read this BEFORE the picks)")
print("   Levels:  HIGH = can cost real money   MED = size down   INFO = fyi")
if not FLAGS:
    print("\n   >> No flags this week - standard cautions apply (see DISCLAIMER).")
else:
    print(); print(bar())
    print("|"+cell("LVL",W_LVL)+"|"+cell("FLAG",W_FLAG)+"|"+cell("HITS",W_HITS)+"|"+cell("WHAT IT MEANS  /  WHAT TO DO",W_MEAN)+"|")
    print(bar())
    for lvl, flag, hits, mean in FLAGS:
        lw = textwrap.wrap(lvl, W_LVL) or [""]
        fw = textwrap.wrap(flag, W_FLAG) or [""]
        hw = textwrap.wrap(hits, W_HITS) or [""]
        mw = textwrap.wrap(mean, W_MEAN) or [""]
        n = max(len(lw), len(fw), len(hw), len(mw))
        for i in range(n):
            g = lambda xs: xs[i] if i < len(xs) else ""
            print("|"+cell(g(lw),W_LVL)+"|"+cell(g(fw),W_FLAG)+"|"+cell(g(hw),W_HITS)+"|"+cell(g(mw),W_MEAN)+"|")
        print(bar())
```

## 6. How the command builds it (Phase 5.1.5 source scan)

Scan THIS run's outputs for firing flags and map each to a category above:

- **Phase 0.3** → short/odd week (`TRADING_DAYS_THIS_WEEK < 5`, `EARLY_CLOSE_DAYS`, `TIMING=SUBOPTIMAL_MIDWEEK`), **data-shaky** (`HOLIDAY_LIST_STALE`).
- **Market Macro** → big scheduled event (in-window jobs/CPI/PPI/Fed), rough/crowded market (mood, fear gauge, rates, dollar, rotation, greed-gauge extreme, narrow breadth). _(Its `Regime`=RISK-OFF read is the headline driver of the separate MARKET REGIME banner (Phase 5.1.4) — display-only since the B2 dock's deactivation 2026-07-02; this Category 9 flag is the Heads-Up-table echo of the same signal.)_
- **Catalyst Hunter** → pick reports this week (in-window earnings / recent material filing), old news (resolved/priced-in, politician-lag), thin/hyped reason (social-only / anti-pump).
- **Risk Assessor** → weak safety-net, wild-or-thin, pick-event (ex-div / options-expiry), overnight-gap.
- **Price Analyzer** → ran too hot (overbought), wild-or-thin (volatility / liquidity / short interest).
- **Big Money** → backers leaving (`hard_reject` heavy insider dumping → 🔴 HIGH **advisory** flag since 2026-06-26 — you decide; NOT auto-removed, NOT in the auto-handled count; weak/fading backing → MED).
- **Sentiment Scanner** → backers leaving (downgrade / dilution), thin/hyped reason (hype / pump).
- **Sector Momentum** → rough/crowded market (all-picks-same-theme concentration).
- **Phase 3.4** → no longer a flag source (**F3 deactivated 2026-06-27, B2 deactivated 2026-07-02**; the old-news flag now comes only from the Catalyst Hunter's freshness booleans).
- **Phase 3.5 filters** → system auto-handled (count of dropped candidates: market-cap / price-floor / Sharia). _(Big Money `hard_reject` is NO LONGER here — demoted 2026-06-26 to the Category 8 advisory flag.)_
- **Data plumbing (any agent)** → if run-threatening (auth expired, scan incomplete, degraded universe), ONE HIGH **data-shaky** row naming the cause; benign single fallbacks fold into **system auto-handled**.

Always emit the `System auto-handled` INFO row (it carries the "WIN = rank, not profit" reminder), even on a clean week.
