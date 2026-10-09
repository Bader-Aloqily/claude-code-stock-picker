# Weekly PDF — the fixed-identity Arabic report spec (Phase 7 / Phase U.8)

> **What this file is.** The single source of truth for the **weekly PDF reports** that close every `/us-picks` run: Phase 7 saves the **WEEKLY PICKS PDF** (including on skip weeks) and Phase U.8 saves the **WEEKLY RESULTS PDF**. Feature added 2026-07-05 as paste-ready Claude Design prompts; **v7 (2026-07-17, user-directed): the prompt emission is RETIRED — the system renders the PDF ITSELF, in ARABIC, and saves it to the user's iCloud folder** (*"instead of giving me the prompt you do the pdf design yourself and save it here with name of the week and make it Arabic"*).
>
> **The consistency mechanism (load-bearing, v7):** the fixed design lives as CODE in **`~/.claude/scripts/uspicks_pdf.py`** — colors, type, geometry, tables, chips, and the fixed footer are all constants in the renderer, so every week's PDF is pixel-identical by construction. This supersedes v1–v6's embed-the-spec-verbatim-in-every-prompt mechanism (which existed because a *referenced* design system was unreliable — proven in the content-planner system, 2026-06-11; executable design is the strictest form of the same guarantee). **Edit the look ONLY in the script, only on explicit user direction, and bump this file's version line (v7 → v8 with date) + the same file ripple (this file, `commands/us-picks.md` Phase 7/U.8 + Reminders, `SKILL.md`, `README.md`, `scripts/uspicks_lint.py` if contract-relevant, the spec amendment + matrix row).**
>
> ✅ Design identity lineage: v5 poster identity USER-APPROVED 2026-07-05 ("done, i agree on the designs"); v6 (2026-07-14) updated outcome text for v5.4; **v7 (2026-07-17) carries the same identity into RTL Arabic A4 PDF** — warm paper, hairline tables, navy ink + teal accent, earned/possible scores, calm losing weeks. Do not restyle, "refresh," or propose look changes on your own initiative. _(2026-07-23 content-accuracy sync, NOT a design iteration — spec stays v7: the two kicker lines now name both indices — "مؤشري S&P 500 وناسداك 100" — matching the v5.5 pick universe; same constants edited in `uspicks_pdf.py`.)_
>
> Additive presentation feature — touches no scoring weight, threshold, WIN definition, filter, or grading math. The PDFs are files on disk; **nothing is persisted to the tracker** (the payload JSON is ephemeral and regenerable from the tracker + the run).
>
> 📝 **2026-08-07 content sync #4 (NOT a design iteration — spec stays v7):** the **grading window** moved system-wide to `FIRST_TRADING_DAY` open → `LAST_TRADING_DAY` regular close (v5.8, user-directed "monday open till friday close"), so four CONTENT slots moved in `uspicks_pdf.py`: the results-table column headers `الدخول (AH)` / `الخروج (AH)` → **`فتح الاثنين` / `إغلاق الجمعة`**; the payload row keys `entry_ah` / `exit_ah` → **`entry_open` / `exit_close`** (the legacy keys stay accepted as a fallback, so weeks logged under the 2026-06-29…2026-07-27 format still render); the results kicker; and the fixed footer's measurement clause. **The results caption was also REWRITTEN — it still carried retired v5.4 text** ("معيار النجاح: عائد ‎+1% فأكثر" and rank described as "للسياق فقط") that the 2026-07-28 v5.6 revert missed; it now states the Monday-open→Friday-close window and the rank bar. Geometry, color, type and layout untouched.
>
> 📝 **2026-09-01 content sync #5 (NOT a design iteration — spec stays v7):** the v6.3 matrix restore (Catalyst 35 → **40**, Big Money → **informational**, still no standalone Volatility) moved the SCORES-table maxes and the components caption in `uspicks_pdf.py`: the table is now **7 columns** (ticker · total · volume /16 · momentum /11 · **catalyst /40** · options /18 · riskliq /15) with **no Big Money column** — its native 0-10 stays in the WHY narrative only. Caption reads "المحفّز 40 … = 100" plus a note that Big Money is shown in the analysis and not counted in the score. The **results** report's outcome chips re-key to the RANK bar (BIG WIN = rank ≤ 100 · WIN ≤ 500 · FLAT 501-1500 · LOSS beyond) and the rank column returns as the graded field, with close return / SPY edge / peak as context. Payload: `score{}` drops `bigmoney`; `results[]` rows carry `rank` again. Design identity, colors, type, layout — untouched.
>
> 📝 **2026-09-13 content sync #6 (NOT a design iteration — spec stays v7):** v6.3 drift fixed — the picks kicker (`KICKER_PICKS_AR`) and the fixed honesty footer (`FOOTER_WEEKLY_AR[0]`) in `uspicks_pdf.py` still carried the retired v6.2 money-bar wording (goal / WIN = beat the S&P 500 that week, BIG WIN = by ≥ 5pp), which content sync #5 missed, so every PDF since 2026-08-31 printed a WIN definition contradicting its own rank caption. Both now state the rank bar: WIN = the stock lands inside the week's top 500 gainers of the liquid US universe (measured first trading day's open → last trading day's close), BIG WIN = top 100; the "result is not your profit" clause and the Sharia line are unchanged. Pinned by `uspicks_lint.py` (a MUST_CONTAIN on the footer sentence + a negative gate on the retired phrases). Geometry, color, type and layout untouched.

> 📝 **2026-07-28 content sync #3 (NOT a design iteration — spec stays v7):** the v5.7 re-weight (Catalyst 40 → 30, Volatility 11 → 21) moved the SCORES-table maxes and the components caption in `uspicks_pdf.py` (`catalyst` renders /30, `volatility` /21; caption "المحفّز 30 · التذبذب 21"). Payload keys unchanged. Geometry, color, type and layout untouched. (Also fixed in the same pass: the §3 component-order line below still carried the stale v5.4 "Volume /4 · Setup /15" maxes the #2 sync missed.)

> 📝 **2026-07-28 content sync #2 (NOT a design iteration — spec stays v7):** the `/us-picks` objective reverted to the top-500-RANK bar (v5.6, user-directed), so three CONTENT slots moved in `uspicks_pdf.py`: the two kickers (universe wording), the fixed honesty footer (WIN basis = rank ≤ 500 / BIG WIN = top 100 + "rank is not your profit"), the SCORES table (component maxes back to the v5.0 matrix: volume /8, `momentum` /11) and the results verdict (the **FLAT** tier is live again). Geometry, color, type and layout are untouched.
>
> 📝 **2026-07-28 content sync (NOT a design iteration — spec stays v7):** the Entry Plan changed system-wide (per-pick 1×ATR buy-limit on the first trading day + a second-trading-day fallback, replacing the flat +1% Monday limit), so the TRADE PLAN column now renders `best_entry (best_entry_pct)` from the new payload field and its Arabic caption states the ATR limit + fallback + "all picks are bought on the same day". Text/data accuracy only — geometry, colors, type and table structure are untouched, exactly like the v5.5 kicker sync.

---

## 1. THE FIXED IDENTITY (documentation — the authoritative values live in `uspicks_pdf.py`)

- **Page:** A4 portrait, 16 mm margins, warm-paper background `#FAFAF7` on every page. Multi-page allowed; tables are kept whole on a page.
- **Language/direction:** Arabic, RTL (text shaping via uharfbuzz). Tickers, prices, percentages, and dates stay in Western digits/Latin, verbatim.
- **Color:** ink `#16212E`, slate labels `#6B7A8C`, hairlines `#DDE3E8`, deep-teal accent `#0F8A73` (wordmark bar, section rules, total scores ONLY), positive `#0E7C4A`, negative `#C4403A`, warning `#B97A1A`. Severity dots: HIGH `#C4403A` · MED `#E09112` · INFO `#9AA7B4`. Outcome chips (filled, white bold text): BIG WIN `#0E7C4A` · WIN `#0F8A73` · LOSS `#C4403A`. **VIX colors by FEAR BAND** — the level, never a change: < 20 green · 20–30 amber · > 30 red.
- **Type:** Tahoma regular+bold (Microsoft Office fonts; full Arabic coverage) — fallback Arial Unicode (macOS Supplemental). No gradients, no shadows, no photos, no emoji (severity is a colored dot).
- **Fixed header:** Arabic wordmark **"الاختيارات الأسبوعية للأسهم الأمريكية"** over a teal bar; kicker line (picks: "اختيارات منهجية من الأسهم الأمريكية المتوسطة والكبيرة · الهدف: الوصول إلى قائمة أفضل 500 سهم صاعد هذا الأسبوع"; results: "نتائج الأسبوع · اختيارات مؤشري S&P 500 وناسداك 100"); the week label `أسبوع YYYY-MM-DD` top-left.
- **Tables:** slate header row over a 2-unit ink rule; 1-px hairlines between rows; first (rightmost) column = ticker; **every score renders earned/possible ("25/30", "79/100" — never a bare number)**.
- **Fixed footer (every page — never dropped, never reworded at render time):** the two Arabic honesty lines (**WIN = weekly RANK ≤ 500 of the US market + BIG WIN = top 100**, measured **Monday open → Friday close** (v5.8, 2026-08-07; was after-hours close → after-hours close), with the explicit "rank is not your profit" clause — re-keyed 2026-07-28 with the v5.6 revert; it read "+1% close-to-close, BIG WIN ≥ +5%" while v5.4/v5.5 were live; Sharia = vice-blacklist-only, not a certified advisory, financial screen is the user's own check) + the brand·week line. Losing weeks render as calmly as winning weeks.

**Spec versioning:** any look change bumps this header line (v7 → v8 with date) AND is implemented in `uspicks_pdf.py` — never silently. Past PDFs are not regenerated.

---

## 2. Output contract — where files go and what they're called

| | |
|---|---|
| Renderer | `python3 ~/.claude/scripts/uspicks_pdf.py {picks\|results\|memo} <payload.json>` |
| Destination | `~/Library/Mobile Documents/com~apple~CloudDocs/Weekly Stocks/` (the user's iCloud folder; override with `$USPICKS_PDF_DIR`) |
| Fallback | `~/.claude/stocks/weekly-pdfs/` when iCloud is unavailable — the script prints a WARNING; surface it to the user |
| Picks filename | `اختيارات الأسبوع YYYY-MM-DD.pdf` (the week's Monday — same date as the tracker's `### Week of` header; skip weeks use the same name) |
| Results filename | `نتائج الأسبوع YYYY-MM-DD.pdf` (the GRADED week's Monday) |
| Success signal | the script's final `SAVED: <absolute path>` line — echo it in chat as the run's very last output |
| Payload file | `~/.claude/stocks/uspicks-pdf-payload.json` (ephemeral, overwritten each run, never committed) |
| Memo mode | ad-hoc one-off Arabic memos in the same identity (first use: the 2026-07-17 strategy-change memo); filename from the payload |

Dependencies: `fpdf2` + `uharfbuzz` (in `scripts/ensure-deps-us.sh`). The renderer needs no network and no API keys.

---

## 3. Payload contracts (the full field-level schemas live in `uspicks_pdf.py`'s docstring)

**picks** — `week_of` (Monday), `skip_week`, `market` (S&P/NASDAQ levels+changes, VIX, `regime`/`advice` enums verbatim, optional `trading_days_note_ar`), `picks[]` (ticker, company, `sector_ar`, `mktcap_b`, `score{total,volume,momentum,catalyst,options,riskliq}` (**v6.3: no `volatility`, no `bigmoney` — 5 scored components; `catalyst` renders /40**) (**`momentum` since 2026-07-28** — the v5.0 matrix was restored; the renderer still accepts the legacy `setup` key), `why_ar`, optional `headsup_ar`, `last_close`, `best_entry`, **`best_entry_pct`** (the pick's own 1×ATR limit width, e.g. `"+4.2%"` — 2026-07-28; the TRADE PLAN cell renders `best_entry (best_entry_pct)`, so a missing value silently degrades to a bare price; **both are OMITTED since v6.1 (2026-08-29) retired the Entry Plan — the cell then prints `—`**), `peak_target`, `peak_target_pct`), `flags[]` (severity, `text_ar`, date|null, stocks), `runners_up[]`; skip weeks add `skip{reason_ar, closest[]}` instead of picks. Component order is fixed (v6.3, 2026-09-01): Volume /16 · Momentum /11 · Catalyst /40 · Options /18 · Risk-Liq /15 — maxes sum to 100, exactly the renderer's SCORES table. _(Superseded v5.7 order, 2026-07-28 → 2026-08-29: Volume /8 · Momentum /11 · Catalyst /30 · Options /18 · Volatility /21 · Risk-Liq /12.)_ Big Money is NOT on the report (informational-only internally).

**results** — `week_of`, `graded_day_ar`, `results[]` (ticker, outcome enum — **BIG WIN / WIN / FLAT / LOSS, with FLAT live again (v5.6; still live under the v6.3 rank bar)**, **`entry_open`, `exit_close`** (v5.8 — the `FIRST_TRADING_DAY` open and `LAST_TRADING_DAY` regular close; the legacy `entry_ah` / `exit_ah` keys are still accepted for weeks logged under the 2026-06-29…2026-07-27 format), `return`, `peak`, `peak_tgt`, `rank`, `what_ar`), optional `universe_n` (rank-context caption), optional `context_ar` (ONE honest context line; the legacy `baseline_ar` key is still accepted — the `Baseline ≥+1%` metric itself retired 2026-07-28 with the +1% objective), optional `note_ar` (ONE takeaway from U.6). `entry_open` = the U.4-filled `Entry Open $`; `exit_close` = the grader's `exit_close` (the `LAST_TRADING_DAY` regular close). _(The ENTRY AH / EXIT AH columns belong to the 2026-06-29…2026-07-27 weeks only.)_ The v6 rules carry over: NO cutoff tiles, NO running track-record panel (they live in the U.7 terminal report + tracker).

**memo** — `filename`, `title_ar`, `date_label`, optional `subtitle_ar`, `sections[]` (heading + paragraphs/bullets/simple table), optional `footer_ar`.

---

## 4. Data-fill rules (Phase 7 / U.8 build discipline)

1. **Verbatim from the run — never recomputed.** Every numeric/enum slot is filled from values the run already computed: Phase 5.1.4 + Market Macro → `market`; Phase 5.1.5's built flag rows → `flags` (same severity + HITS; DATE only for dated events); Phase 3.3/3.55 verified scores → `score`; Phase 4/5.1 → trade-plan prices; Phase 3.6 **slots 6-10** → `runners_up` (the top-5-by-score selection, restored by v6.1 on 2026-08-29 and unchanged by v6.3; _superseded 2026-08-28 → 08-29: slots 11-15 under the Board's S[6..10] band, whose excluded top five were never published_). For U.8: U.4's graded cells → `results`; U.2's `universe_size` → `universe_n`; one honest context line (e.g. what the week's top-500 bar took) → `context_ar` (the `Baseline ≥+1%` metric and its `baseline_ar` key retired 2026-07-28).
2. **Arabic prose slots (`*_ar`) are TRANSLATIONS, not new content.** The orchestrator translates the run's already-built plain-English text (WHY reasons, flag text, grade reasons, macro note) into natural Arabic at build time. Translation changes the language — NEVER the substance: nothing added, dropped, softened, or "improved"; tickers/numbers/percentages stay verbatim in Western digits. The flags-glossary §2 plain-language mandate applies in Arabic too (no untranslated jargon).
3. **N is exact.** 1–5 pick entries / results rows, matching the run. Missing optional value → omit the field (the renderer omits the row) — never invent data to fill a layout.
4. **Skip week** → `skip_week: true` payload (reason + top-5 near-misses; flags still included). **`GRADE_PENDING_DATA`** → NO results PDF for that week; say in one line that it comes after the data publishes. **Multiple weeks graded in one run** → one `results` render per graded week.
5. **Bidi hygiene:** don't wrap mixed Arabic+number phrases in quotation marks, and avoid `%X-Y` numeric ranges inside Arabic sentences (write `من X إلى Y%`) — both shuffle under RTL shaping.
6. **Emission format:** run the script, then echo its `SAVED:` line (+ any fallback WARNING) as the run's closing output — only the due 📊 L1/L2 reminder banners may render after it. The PDF is the deliverable — no fenced design prompt, no poster text in chat.

## 5. Hard rules (every render)

1. **The design is law and it is code.** Never restyle at build time, never bypass `uspicks_pdf.py` with a hand-built document, never edit its identity constants without explicit user direction + a version bump here.
2. **Honest surface.** The fixed footer's WIN-basis line (rank ≤ 500 since the 2026-07-28 v5.6 revert) and Sharia not-certified line are part of the design — never dropped. Losing weeks render with the same calm layout as winning weeks. The running track record stays OFF the results PDF (user-directed 2026-07-05).
3. **Data is final.** The renderer styles; it never edits, reorders, recomputes, or invents. The payload is the only data path.
4. **Never block the run on the PDF.** Picks/grades are already logged by the time Phase 7/U.8 runs — a render failure is reported (with the payload path + error) and the run still counts. Deps via `ensure-deps-us.sh`; iCloud-unavailable falls back to `~/.claude/stocks/weekly-pdfs/` with a surfaced warning.

---

## 6. Historical record — the Claude Design prompt era (2026-07-05 → 2026-07-17, RETIRED)

v1→v5 iterated same-day on 2026-07-05 from user markup of real renders (dark cards → light/table-first → full-size 1600 px → VIX fear-band color → slim trade-plan table), v5 user-approved; v6 (2026-07-14) updated the footer/outcome text for v5.4 (WIN = +1%, FLAT chip retired). Each run emitted ONE fenced, paste-ready Claude Design prompt with the §1 DESIGN SPEC embedded verbatim (the then-sameness mechanism) under the header `🎨 Report design prompt — paste into Claude Design:`. **Retired 2026-07-17 (user-directed)** in favor of the self-rendered Arabic PDF above — the identity carried over; the optional "save it as a Claude Design system" setup (old §6) is obsolete. The old skeletons are recoverable from git history if ever needed; do NOT re-add prompt emission without explicit user direction.
