#!/usr/bin/env python3
"""uspicks_pdf.py — the /us-picks Arabic weekly PDF renderer (spec v7).

WHAT THIS IS (2026-07-17, user-directed). Phase 7 (weekly picks, incl. skip
weeks) and Phase U.8 (weekly results) no longer emit paste-ready Claude Design
prompts — the system renders the weekly report ITSELF as an ARABIC PDF and
saves it to the user's iCloud "Weekly Stocks" folder. This script is the fixed
design identity in executable form: the same layout, colors, and type render
every week because the design lives in code, not in a prompt (the strongest
version of the 2026-07-05 "the design always looks the same" requirement).

Design lineage: v5/v6 poster identity (report-design.md) carried into RTL
Arabic — warm paper #FAFAF7, deep-navy ink #16212E, slate labels #6B7A8C,
hairline tables #DDE3E8, deep-teal accent #0F8A73 (total scores + rules only),
green/red returns, severity dots, filled outcome chips, VIX colored by fear
band (the level, never a change). Every score renders earned/possible
("25/30" — never a bare number). Losing weeks render as calmly as winning
weeks. The fixed footer (honesty lines) is part of the design — never dropped.

Usage:
  python3 uspicks_pdf.py picks   payload.json   [--out DIR]
  python3 uspicks_pdf.py results payload.json   [--out DIR]
  python3 uspicks_pdf.py memo    payload.json   [--out DIR]

Payload contracts (all Arabic prose fields end in _ar and are authored by the
orchestrator at run time; tickers/numbers are passed VERBATIM from the run —
this script styles, it never edits, recomputes, or invents data; a missing
optional field means "omit that row/section", never fabricate):

picks payload:
  {"week_of": "YYYY-MM-DD",                 # the pick week's Monday (tracker key)
   "generated": "YYYY-MM-DD",
   "skip_week": false,
   "market": {"sp500": "6,439", "sp500_chg": "+1.2%",
              "nasdaq": "23,405", "nasdaq_chg": "+1.8%", "vix": 16.8,
              "regime": "RISK-ON|NEUTRAL|RISK-OFF",
              "advice": "RUN|CAUTION|CONSIDER SKIPPING",
              "trading_days_note_ar": "..."},           # optional (short weeks)
   "picks": [{"ticker": "DELL", "company": "Dell Technologies",
              "sector_ar": "التقنية", "mktcap_b": "64.2",
              "score": {"total": 79, "volume": 12, "momentum": 8, "catalyst": 34,
                        "options": 15, "riskliq": 10},   # v6.3: no volatility,
                        # no bigmoney - Big Money is informational (0 points)
              "why_ar": "...", "headsup_ar": "...",      # headsup optional
              "last_close": "$67.19", "best_entry": "$67.86",
              "best_entry_pct": "+4.2%",       # the pick's own 1x-ATR limit width
              "peak_target": "$73.90", "peak_target_pct": "+10%"}],
   "flags": [{"severity": "HIGH|MED|INFO", "text_ar": "...",
              "date": "YYYY-MM-DD"|null, "stocks": "DELL, MRNA"}],
   "runners_up": [{"ticker": "GH", "total": 68}],
   "skip": {"reason_ar": "...", "closest": [{"ticker":"X","total":67}]}}  # skip weeks

results payload:
  {"week_of": "YYYY-MM-DD", "graded_day_ar": "الجمعة",
   "results": [{"ticker": "MRNA", "outcome": "BIG WIN|WIN|FLAT|LOSS",
                # v5.8 (2026-08-07): entry = FIRST_TRADING_DAY open,
                # exit = LAST_TRADING_DAY regular close. Legacy after-hours
                # keys `entry_ah`/`exit_ah` still accepted for weeks logged
                # under the 2026-06-29..2026-07-27 format.
                "entry_open": "$27.36", "exit_close": "$31.92", "return": "+16.7%",
                "peak": "+18.2%", "peak_tgt": "+12%", "rank": "#100",
                "what_ar": "..."}],
   "universe_n": "4,994",                    # optional — rank-context caption
   "context_ar": "...",                      # optional — one honest context line
   #                                          (legacy key `baseline_ar` still accepted;
   #                                           the +1% Baseline metric retired 2026-07-28)
   "note_ar": "..."}                         # optional — weekly takeaway

memo payload:
  {"filename": "….pdf", "title_ar": "...", "date_label": "YYYY-MM-DD",
   "subtitle_ar": "...",                     # optional
   "sections": [{"heading_ar": "...", "paragraphs_ar": ["..."],
                 "bullets_ar": ["..."],                        # optional
                 "table": {"headers_ar": [...], "rows": [[...]],
                           "widths": [...]}}],                 # optional
   "footer_ar": ["...", "..."]}              # optional (default: brand line)

Output directory: $USPICKS_PDF_DIR if set, else the iCloud "Weekly Stocks"
folder, else (fallback, with a warning) ~/.claude/stocks/weekly-pdfs/.
Filenames: picks → "اختيارات الأسبوع <week_of>.pdf" · results →
"نتائج الأسبوع <week_of>.pdf" · memo → payload["filename"].
Prints "SAVED: <absolute path>" as its last line on success.

Fonts (Arabic-capable TTFs; .ttc collections are NOT loadable): Tahoma
regular+bold (Microsoft Office) preferred; Arial Unicode (macOS Supplemental)
fallback (no true bold — bold style reuses it). Fails loud with the searched
paths if neither exists. Requires: fpdf2 + uharfbuzz (text shaping; both in
scripts/ensure-deps-us.sh).
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from fpdf import FPDF
except ImportError:
    sys.exit("uspicks_pdf: fpdf2 is not installed — run scripts/ensure-deps-us.sh "
             "(pip3 install --user fpdf2 uharfbuzz)")

# ============================== FIXED IDENTITY ==============================
# (v7, 2026-07-17 — the v5/v6 poster identity in RTL Arabic. Do not restyle.)

PAPER = (250, 250, 247)     # warm paper
INK = (22, 33, 46)          # primary text
SLATE = (107, 122, 140)     # labels, captions, table headers
HAIRLINE = (221, 227, 232)
TEAL = (15, 138, 115)       # accent: rules + total scores ONLY
POS = (14, 124, 74)         # positive/up
NEG = (196, 64, 58)         # negative/down
WARN = (185, 122, 26)
SEV = {"HIGH": (196, 64, 58), "MED": (224, 145, 18), "INFO": (154, 167, 180)}
CHIP = {"BIG WIN": (14, 124, 74), "WIN": (15, 138, 115),
        "FLAT": (154, 167, 180), "LOSS": (196, 64, 58)}

MARGIN = 16                 # mm
PAGE_W, PAGE_H = 210, 297   # A4 portrait

BRAND_AR = "الاختيارات الأسبوعية للأسهم الأمريكية"
KICKER_PICKS_AR = "اختيارات منهجية من الأسهم الأمريكية المتوسطة والكبيرة · الهدف: دخول قائمة أفضل 500 سهم ارتفاعاً هذا الأسبوع"
KICKER_RESULTS_AR = "نتائج الأسبوع · اختيارات الأسهم الأمريكية المتوسطة والكبيرة"

# The fixed honesty footer (weekly reports) — never dropped, never reworded
# at render time. (Arabic of the v6 fixed footer; WIN = weekly RANK basis
# since the 2026-07-28 v5.6 revert — was the +1% absolute basis in v5.4/v5.5.
# Measurement window = Monday OPEN -> Friday CLOSE since v5.8, 2026-08-07.
# 2026-09-13 drift fix: the v6.2 money-bar wording (WIN = beat the index that
# week) had survived the v6.3 rank restore in this footer and in the picks
# kicker; both state the v6.3 RANK bar again - pinned by uspicks_lint.py.)
FOOTER_WEEKLY_AR = [
    "تحليل خوارزمي — ليس نصيحة استثمارية. النجاح يعني أن يحلّ السهم ضمن أفضل 500 سهم ارتفاعاً بين الأسهم الأمريكية السائلة في الأسبوع نفسه (قياسًا من افتتاح أول يوم تداول إلى إغلاق آخر يوم)، والنجاح الكبير يعني ضمن أفضل 100. النتيجة ليست ربحك: دخولك وخروجك الفعليان هما ما يحدد ربحك.",
    "الفحص الشرعي: استبعاد الأنشطة المحظورة فقط (السلاح، القمار، الكحول، التبغ، الإباحية، لحم الخنزير) — وليس اعتمادًا شرعيًا معتمدًا؛ الفحص المالي الشرعي مسؤوليتك.",
]

OUTCOME_AR = {"BIG WIN": "نجاح كبير", "WIN": "نجاح",
              "FLAT": "متوسط", "LOSS": "خسارة"}
REGIME_AR = {"RISK-ON": "إقبال على المخاطرة", "NEUTRAL": "محايد",
             "RISK-OFF": "عزوف عن المخاطرة"}
REGIME_COLOR = {"RISK-ON": POS, "NEUTRAL": SLATE, "RISK-OFF": NEG}
ADVICE_AR = {"RUN": "انطلق", "CAUTION": "تقدَّم بحذر",
             "CONSIDER SKIPPING": "فكّر في تخطي الأسبوع"}

FONT_PAIRS = [  # (regular, bold) — first existing pair wins
    ("/Applications/Microsoft Word.app/Contents/Resources/DFonts/tahoma.ttf",
     "/Applications/Microsoft Word.app/Contents/Resources/DFonts/tahomabd.ttf"),
    ("/Library/Fonts/Microsoft/tahoma.ttf", "/Library/Fonts/Microsoft/tahomabd.ttf"),
    (str(Path.home() / "Library/Fonts/tahoma.ttf"),
     str(Path.home() / "Library/Fonts/tahomabd.ttf")),
]
FONT_SINGLES = [  # Arabic-capable single-weight fallbacks (bold reuses regular)
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

ICLOUD_DIR = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Weekly Stocks"
FALLBACK_DIR = Path.home() / ".claude/stocks/weekly-pdfs"


def resolve_out_dir(override=None):
    """USPICKS_PDF_DIR > --out > iCloud folder > local fallback (warn)."""
    for cand in [os.environ.get("USPICKS_PDF_DIR"), override]:
        if cand:
            p = Path(cand).expanduser()
            p.mkdir(parents=True, exist_ok=True)
            return p
    if ICLOUD_DIR.is_dir() and os.access(ICLOUD_DIR, os.W_OK):
        return ICLOUD_DIR
    FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
    print("WARNING: iCloud folder unavailable ({}) — saving to {}".format(
        ICLOUD_DIR, FALLBACK_DIR), file=sys.stderr)
    return FALLBACK_DIR


def sign_color(s):
    s = str(s).strip()
    if s.startswith(("+",)):
        return POS
    if s.startswith(("-", "−")):
        return NEG
    return INK


def _entry_cell(p):
    """TRADE PLAN 'best entry' cell: the per-pick buy-limit price, followed by
    its own limit width when the run supplied one (2026-07-28 Entry Plan — the
    limit is 1x that pick's ATR, so the percentage differs per row and is worth
    showing). Degrades to a bare price rather than an empty '( )' when
    best_entry_pct is absent."""
    px = p.get("best_entry", "—")
    pct = str(p.get("best_entry_pct") or "").strip()
    return "{} ({})".format(px, pct) if pct else str(px)


def vix_color(level):
    try:
        v = float(str(level).replace(",", ""))
    except (TypeError, ValueError):
        return INK
    if v < 20:
        return POS
    if v <= 30:
        return (224, 145, 18)
    return NEG


class ReportPDF(FPDF):
    """A4 RTL Arabic report with the fixed header/footer identity."""

    def __init__(self, week_label_ar, kicker_ar, footer_lines_ar, title_ar=None):
        super().__init__(format="A4")
        self.week_label_ar = week_label_ar
        self.kicker_ar = kicker_ar
        self.footer_lines_ar = footer_lines_ar
        self.title_override = title_ar
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(True, margin=34)
        self._register_fonts()
        self.set_text_shaping(True)

    def _register_fonts(self):
        for reg, bold in FONT_PAIRS:
            if Path(reg).is_file() and Path(bold).is_file():
                self.add_font("Main", style="", fname=reg)
                self.add_font("Main", style="B", fname=bold)
                return
        for single in FONT_SINGLES:
            if Path(single).is_file():
                self.add_font("Main", style="", fname=single)
                self.add_font("Main", style="B", fname=single)
                return
        searched = [p for pair in FONT_PAIRS for p in pair] + FONT_SINGLES
        sys.exit("uspicks_pdf: no Arabic-capable TTF found. Searched:\n  " +
                 "\n  ".join(searched))

    # ---- fixed page furniture ------------------------------------------
    def header(self):
        # paper background under everything, every page
        self.set_fill_color(*PAPER)
        self.rect(0, 0, PAGE_W, PAGE_H, style="F")
        if self.page_no() == 1:
            title = self.title_override or BRAND_AR
            # week/date label, small, at the top-left (RTL mirror of top-right);
            # the title cell is width-constrained so the two never collide
            self.set_xy(MARGIN, MARGIN + 1)
            self.set_font("Main", size=10)
            self.set_text_color(*SLATE)
            self.cell(40, 6, self.week_label_ar, align="L")
            title_w = PAGE_W - 2 * MARGIN - 44
            self.set_xy(PAGE_W - MARGIN - title_w, MARGIN)
            self.set_text_color(*INK)
            size = 21  # shrink-to-fit so the wordmark stays on one line
            self.set_font("Main", style="B", size=size)
            while size > 14.5 and self.get_string_width(title) > title_w:
                size -= 0.5
                self.set_font("Main", style="B", size=size)
            self.multi_cell(title_w, 11, title, align="R", new_x="LMARGIN", new_y="NEXT")
            # deep-teal underline bar under the wordmark (right-anchored)
            bar_w = min(self.get_string_width(title) + 4, title_w)
            self.set_fill_color(*TEAL)
            self.rect(PAGE_W - MARGIN - bar_w, self.get_y() + 0.5, bar_w, 1.3, style="F")
            self.ln(4)
            self.set_font("Main", size=10.5)
            self.set_text_color(*SLATE)
            self.cell(0, 6, self.kicker_ar, align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)
            self._rule(self.get_y(), color=HAIRLINE, width=0.3)
            self.ln(6)
        else:
            self.set_y(MARGIN - 4)
            self.set_font("Main", size=9)
            self.set_text_color(*SLATE)
            self.cell(0, 5, self.week_label_ar + " · " + BRAND_AR, align="R",
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(4)

    def footer(self):
        self.set_y(-30)
        self._rule(self.get_y(), color=HAIRLINE, width=0.3)
        self.set_y(-27)
        self.set_font("Main", size=7.6)
        self.set_text_color(*SLATE)
        for line in self.footer_lines_ar:
            self.multi_cell(0, 4.0, line, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_y(-8.5)
        self.cell(0, 4, "{} · {}".format(BRAND_AR, self.week_label_ar), align="L")

    # ---- drawing helpers ------------------------------------------------
    def ensure_room(self, h_mm):
        """Page-break now if h_mm of content wouldn't fit above the footer."""
        if self.get_y() + h_mm > PAGE_H - 34:
            self.add_page()

    def _rule(self, y, color=HAIRLINE, width=0.3, x1=None, x2=None):
        self.set_draw_color(*color)
        self.set_line_width(width)
        self.line(x1 if x1 is not None else MARGIN, y,
                  x2 if x2 is not None else PAGE_W - MARGIN, y)

    def section_title(self, text_ar):
        if self.get_y() > PAGE_H - 70:
            self.add_page()
        self.ln(3)
        self.set_font("Main", style="B", size=13.5)
        self.set_text_color(*INK)
        self.cell(0, 8, text_ar, align="R", new_x="LMARGIN", new_y="NEXT")
        # short teal rule, right-anchored (section-title accent)
        self.set_fill_color(*TEAL)
        self.rect(PAGE_W - MARGIN - 22, self.get_y() + 0.4, 22, 0.9, style="F")
        self.ln(4.5)

    def chip(self, x, y, w, h, label_ar, rgb):
        self.set_fill_color(*rgb)
        self.rect(x, y, w, h, style="F", round_corners=True, corner_radius=1.6)
        self.set_xy(x, y)
        self.set_font("Main", style="B", size=9)
        self.set_text_color(255, 255, 255)
        self.cell(w, h, label_ar, align="C")

    def dot(self, x, y, rgb, r=1.7):
        self.set_fill_color(*rgb)
        self.ellipse(x - r, y - r, 2 * r, 2 * r, style="F")

    # ---- generic RTL table ----------------------------------------------
    def table_header(self, cols):
        """cols: list of (label_ar, width_mm) — first item is the RIGHTMOST column."""
        y = self.get_y()
        if y > PAGE_H - 60:
            self.add_page()
            y = self.get_y()
        self.set_font("Main", style="B", size=9.2)
        self.set_text_color(*SLATE)
        x = PAGE_W - MARGIN
        for label, w in cols:
            x -= w
            self.set_xy(x, y)
            self.cell(w, 7, label, align="R" if x + w == PAGE_W - MARGIN else "C")
        self._rule(y + 7, color=INK, width=0.5)
        self.set_y(y + 8.5)

    def row_cells(self, cols, values, row_h=9.5):
        """values: list of (text, rgb, bold, kind) aligned with cols.
        kind: 'text'|'num'|'chip'|'dot'. Returns after advancing y + hairline."""
        y = self.get_y()
        if y > PAGE_H - 42:
            self.add_page()
            y = self.get_y()
        x = PAGE_W - MARGIN
        for (label, w), (text, rgb, bold, kind) in zip(cols, values):
            x -= w
            if kind == "chip":
                cw = min(w - 4, 24)
                self.chip(x + (w - cw) / 2, y + (row_h - 6) / 2, cw, 6, text, rgb)
            elif kind == "dot":
                self.dot(x + w / 2, y + row_h / 2, rgb)
            else:
                self.set_xy(x, y)
                self.set_font("Main", style="B" if bold else "", size=10)
                self.set_text_color(*rgb)
                align = "R" if x + w == PAGE_W - MARGIN else "C"
                self.cell(w, row_h, str(text), align=align)
        self._rule(y + row_h, color=HAIRLINE, width=0.25)
        self.set_y(y + row_h + 0.8)

    def caption(self, text_ar):
        if self.get_y() > PAGE_H - 52:
            self.add_page()
        self.ln(0.5)
        self.set_font("Main", size=8.4)
        self.set_text_color(*SLATE)
        self.multi_cell(0, 4.6, text_ar, align="R", new_x="LMARGIN", new_y="NEXT")

    def body_ar(self, text, size=10.5, color=INK, bold=False, lh=6.4):
        self.set_font("Main", style="B" if bold else "", size=size)
        self.set_text_color(*color)
        self.multi_cell(0, lh, text, align="R", new_x="LMARGIN", new_y="NEXT")


# ================================ PICKS =====================================

def render_picks(data, out_dir):
    week = data["week_of"]
    pdf = ReportPDF("أسبوع " + week, KICKER_PICKS_AR, FOOTER_WEEKLY_AR)
    pdf.add_page()

    # MARKET block — indices line, then regime/advice line (never collide)
    m = data.get("market") or {}
    if m:
        def put_line(parts, y, h=7):
            """parts: list of (text, rgb, bold, size) laid out right-to-left."""
            x = PAGE_W - MARGIN
            for txt, rgb, bold, size in parts:
                pdf.set_font("Main", style="B" if bold else "", size=size)
                w = pdf.get_string_width(str(txt)) + 1.2
                x -= w
                pdf.set_xy(x, y)
                pdf.set_text_color(*rgb)
                pdf.cell(w, h, str(txt), align="C")
            pdf.set_y(y + h)
        put_line([
            ("مؤشرات السوق:  ", SLATE, True, 10),
            ("S&P 500 " + str(m.get("sp500", "—")) + " ", INK, False, 10),
            ("(" + str(m.get("sp500_chg", "—")) + ")", sign_color(m.get("sp500_chg", "")), False, 10),
            ("  ·  ناسداك " + str(m.get("nasdaq", "—")) + " ", INK, False, 10),
            ("(" + str(m.get("nasdaq_chg", "—")) + ")", sign_color(m.get("nasdaq_chg", "")), False, 10),
            ("  ·  مؤشر الخوف VIX ", INK, False, 10),
            (str(m.get("vix", "—")), vix_color(m.get("vix")), True, 10),
        ], pdf.get_y())
        regime = str(m.get("regime", "NEUTRAL"))
        adv = str(m.get("advice", ""))
        regime_parts = [
            ("وضع السوق:  ", SLATE, True, 10),
            (REGIME_AR.get(regime, regime), REGIME_COLOR.get(regime, SLATE), True, 10),
        ]
        if adv:
            regime_parts.append((" — " + ADVICE_AR.get(adv, adv), INK, False, 10))
        note = m.get("trading_days_note_ar")
        if note:
            regime_parts.append(("      " + note, SLATE, False, 8.8))
        put_line(regime_parts, pdf.get_y() + 0.5)
        pdf._rule(pdf.get_y() + 1.5)
        pdf.ln(4)

    if data.get("skip_week"):
        skip = data.get("skip") or {}
        pdf.ln(8)
        pdf.set_font("Main", style="B", size=24)
        pdf.set_text_color(*INK)
        pdf.cell(0, 14, "لا اختيارات هذا الأسبوع", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.body_ar(skip.get("reason_ar",
                    "لم يتجاوز أي سهم عتبة 70/100 بعد تطبيق جميع الفلاتر. الجودة قبل الكثرة — التشغيل القادم: الأحد."),
                    size=11, color=SLATE)
        closest = skip.get("closest") or []
        if closest:
            pdf.ln(3)
            pdf.section_title("الأقرب إلى العتبة")
            line = "  ·  ".join("{} {}/100".format(c["ticker"], c["total"]) for c in closest)
            pdf.body_ar(line, size=10.5, color=SLATE)
    else:
        picks = data.get("picks") or []
        n = len(picks)

        # SCORES table — fixed component order (v6.3, 2026-09-01): V/16 M/11 C/40 O/18 R/15
        # Big Money is INFORMATIONAL under v6.3 (0 points) and is NOT a column.
        pdf.section_title("تقييم اختيارات هذا الأسبوع ({} {})".format(
            n, "اختيار" if n == 1 else "اختيارات"))
        cols = [("السهم", 24), ("الإجمالي", 26), ("الحجم", 22), ("الزخم", 23),
                ("المحفّز", 25), ("الخيارات", 26), ("المخاطر/السيولة", 32)]
        pdf.table_header(cols)
        for p in picks:
            s = p["score"]
            pdf.row_cells(cols, [
                (p["ticker"], INK, True, "num"),
                ("{}/100".format(s["total"]), TEAL, True, "num"),
                ("{}/16".format(s["volume"]), INK, False, "num"),
                ("{}/11".format(s.get("momentum", s.get("setup"))), INK, False, "num"),
                ("{}/40".format(s["catalyst"]), INK, False, "num"),
                ("{}/18".format(s["options"]), INK, False, "num"),
                ("{}/15".format(s["riskliq"]), INK, False, "num"),
            ])
        pdf.caption("كل خلية = النقاط المحقَّقة من النقاط الممكنة. المكوّنات: حجم التداول 16 · الزخم السعري 11 · المحفّز 40 · تدفق عقود الخيارات 18 · المخاطر والسيولة 15 = 100. (مؤشّر الأموال الكبيرة يُعرض في التحليل ولا يدخل في الدرجة.)")

        # WHY
        pdf.section_title("لماذا هذه الاختيارات؟")
        for p in picks:
            head = "{} — {} ({}، ‎${}B)".format(
                p["ticker"], p.get("company", ""), p.get("sector_ar", ""),
                p.get("mktcap_b", "—"))
            pdf.body_ar(head, size=11, bold=True)
            pdf.body_ar(p.get("why_ar", ""), size=10.2, color=(60, 72, 88), lh=6.2)
            if p.get("headsup_ar"):
                pdf.body_ar("تنبيه: " + p["headsup_ar"], size=9.6, color=WARN, lh=5.8)
            pdf.ln(2.2)

        # TRADE PLAN (v5-slim: last close / best entry / peak target only)
        pdf.ensure_room(min(34 + len(picks) * 10.3, 200))  # keep table whole
        pdf.section_title("بيانات مرجعية")
        tcols = [("السهم", 32), ("آخر إغلاق", 46), ("حركة اليوم المعتادة", 50), ("حجم المحفّز المقدّر", 50)]
        pdf.table_header(tcols)
        for p in picks:
            pdf.row_cells(tcols, [
                (p["ticker"], INK, True, "num"),
                (p.get("last_close", "—"), INK, False, "num"),
                (p.get("atr_note", "—"), INK, False, "num"),
                (p.get("catalyst_mag", "—"), POS, False, "num"),
            ])
        pdf.caption("آخر إغلاق = سعر مرجعي فقط (إغلاق ما بعد الجلسة ليوم الجمعة). حركة اليوم المعتادة = متوسط المدى الحقيقي، لقياس تقلّب السهم. حجم المحفّز المقدّر = مدى الحركة الممكنة، وليس هدف بيع. النظام لا يحدّد سعر دخول ولا وقف ولا خروج — توقيت الشراء والبيع قرارك أنت.")

    # FLAGS (both normal + skip weeks)
    flags = data.get("flags") or []
    if flags:
        pdf.section_title("تنبيهات يجب الانتباه لها")
        fcols = [("", 8), ("التنبيه", 102), ("التاريخ", 26), ("الأسهم", 42)]
        pdf.set_font("Main", style="B", size=9.2)
        y = pdf.get_y()
        x = PAGE_W - MARGIN
        for label, w in fcols:
            x -= w
            pdf.set_xy(x, y)
            pdf.set_text_color(*SLATE)
            pdf.cell(w, 7, label, align="R" if x + w == PAGE_W - MARGIN else "C")
        pdf._rule(y + 7, color=INK, width=0.5)
        pdf.set_y(y + 8.5)
        order = {"HIGH": 0, "MED": 1, "INFO": 2}
        for f in sorted(flags, key=lambda f: order.get(f.get("severity", "INFO"), 3)):
            y = pdf.get_y()
            if y > PAGE_H - 46:
                pdf.add_page()
                y = pdf.get_y()
            pdf.set_font("Main", size=9.6)
            text = f.get("text_ar", "")
            text_w = fcols[1][1] - 4
            lines = pdf.multi_cell(text_w, 5.4, text, align="R", dry_run=True, output="LINES")
            row_h = max(9, len(lines) * 5.4 + 3.4)
            x = PAGE_W - MARGIN - fcols[0][1]
            pdf.dot(x + 4, y + row_h / 2, SEV.get(f.get("severity", "INFO"), SLATE))
            x -= fcols[1][1]
            pdf.set_xy(x + 2, y + 1.7)
            pdf.set_text_color(*INK)
            pdf.multi_cell(text_w, 5.4, text, align="R")
            x -= fcols[2][1]
            pdf.set_xy(x, y)
            pdf.set_font("Main", size=9.4)
            pdf.set_text_color(*SLATE)
            pdf.cell(fcols[2][1], row_h, str(f.get("date") or "—"), align="C")
            x -= fcols[3][1]
            pdf.set_xy(x, y)
            pdf.set_text_color(*INK)
            pdf.cell(fcols[3][1], row_h, str(f.get("stocks", "—")), align="C")
            pdf._rule(y + row_h, color=HAIRLINE, width=0.25)
            pdf.set_y(y + row_h + 0.8)

    # RUNNERS-UP — label on its own line, then the pure-LTR scores line
    # (keeps bidi from shuffling the list across wraps)
    runners = data.get("runners_up") or []
    if runners and not data.get("skip_week"):
        pdf.ln(2)
        if pdf.get_y() > PAGE_H - 48:
            pdf.add_page()
        pdf.set_font("Main", style="B", size=9.6)
        pdf.set_text_color(*SLATE)
        pdf.cell(0, 5.6, "الاحتياط (الأقرب بعد الاختيارات):", align="R",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Main", size=9.6)
        line = "  ·  ".join("{} {}/100".format(r["ticker"], r["total"]) for r in runners)
        pdf.multi_cell(0, 5.6, line, align="R", new_x="LMARGIN", new_y="NEXT")

    name = "اختيارات الأسبوع {}.pdf".format(week)
    path = out_dir / name
    pdf.output(str(path))
    return path


# =============================== RESULTS ====================================

def render_results(data, out_dir):
    week = data["week_of"]
    pdf = ReportPDF("أسبوع " + week, KICKER_RESULTS_AR, FOOTER_WEEKLY_AR)
    pdf.add_page()

    results = data.get("results") or []
    n = len(results)
    big = sum(1 for r in results if r.get("outcome") == "BIG WIN")
    win = sum(1 for r in results if r.get("outcome") == "WIN")
    flat = sum(1 for r in results if r.get("outcome") == "FLAT")
    loss = sum(1 for r in results if r.get("outcome") == "LOSS")

    # VERDICT line (big, colored counts; calm regardless of outcome)
    y = pdf.get_y() + 2
    x = PAGE_W - MARGIN
    def put(txt, rgb, size=17, bold=True):
        nonlocal x
        pdf.set_font("Main", style="B" if bold else "", size=size)
        w = pdf.get_string_width(str(txt)) + 1.6
        x -= w
        pdf.set_xy(x, y)
        pdf.set_text_color(*rgb)
        pdf.cell(w, 10, str(txt), align="C")
    put("النتيجة:  ", INK)
    put("نجاح كبير {}".format(big), CHIP["BIG WIN"])
    put("  ·  ", SLATE)
    put("نجاح {}".format(win), CHIP["WIN"])
    put("  ·  ", SLATE)
    put("متوسط {}".format(flat), CHIP["FLAT"])
    put("  ·  ", SLATE)
    put("خسارة {}".format(loss), CHIP["LOSS"])
    pdf.set_y(y + 11)
    pdf.set_font("Main", size=9.6)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 5.5, "من أصل {} اختيارات · قُيّمت من افتتاح الاثنين إلى إغلاق يوم {}".format(
        n, data.get("graded_day_ar", "الجمعة")), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # RESULTS table — peak achieved/target as two pure-number columns
    # (mixing Arabic into a number cell lets bidi shuffle the signs)
    pdf.ensure_room(min(34 + n * 10.8, 200))  # keep table whole
    pdf.section_title("النتائج")
    cols = [("السهم", 20), ("النتيجة", 26), ("فتح الاثنين", 26), ("إغلاق الجمعة", 26),
            ("العائد", 22), ("الذروة", 21), ("هدف الذروة", 20), ("الترتيب", 17)]
    pdf.table_header(cols)
    for r in results:
        outcome = r.get("outcome", "LOSS")
        pdf.row_cells(cols, [
            (r["ticker"], INK, True, "num"),
            (OUTCOME_AR.get(outcome, outcome), CHIP.get(outcome, SLATE), True, "chip"),
            # v5.8 keys, with the pre-2026-08-07 after-hours keys as fallback.
            (r.get("entry_open", r.get("entry_ah", "—")), INK, False, "num"),
            (r.get("exit_close", r.get("exit_ah", "—")), INK, False, "num"),
            (r.get("return", "—"), sign_color(r.get("return", "")), True, "num"),
            (r.get("peak", "—"), INK, False, "num"),
            (r.get("peak_tgt", "—"), SLATE, False, "num"),
            (r.get("rank", "—"), SLATE, False, "num"),
        ], row_h=10)
    # v5.8 (2026-08-07): the measured window is Monday's OPEN to Friday's CLOSE —
    # what the trade plan actually executes. This caption also corrects drift left
    # by the v5.6 revert: it still described the retired +1% success bar and called
    # the rank "context only" after rank had become the grade again.
    cap = ("القياس من سعر الافتتاح يوم الاثنين إلى سعر الإغلاق يوم الجمعة — وهي نفس الفترة "
           "التي تنفَّذ فيها الخطة (الشراء عند افتتاح أول يوم تداول، والبيع عند إغلاق آخر يوم).")
    if data.get("universe_n"):
        cap += (" معيار النجاح هو الترتيب بين الأسهم الأمريكية السائلة (~{}): "
                "نجاح كبير = ضمن أفضل 100، نجاح = ضمن أفضل 500.".format(data["universe_n"]))
    else:
        cap += " معيار النجاح هو الترتيب بين الأسهم الأمريكية السائلة: نجاح كبير = ضمن أفضل 100، نجاح = ضمن أفضل 500."
    pdf.caption(cap)
    ctx = data.get("context_ar") or data.get("baseline_ar")
    if ctx:
        pdf.caption(ctx)

    # WHAT HAPPENED
    pdf.section_title("ماذا حدث؟")
    for r in results:
        pdf.body_ar(r["ticker"], size=11, bold=True)
        pdf.body_ar(r.get("what_ar", ""), size=10.2, color=(60, 72, 88), lh=6.2)
        pdf.ln(1.6)

    if data.get("note_ar"):
        pdf.ln(1)
        pdf._rule(pdf.get_y())
        pdf.ln(2.5)
        pdf.body_ar("خلاصة الأسبوع: " + data["note_ar"], size=10.2, color=SLATE)

    name = "نتائج الأسبوع {}.pdf".format(week)
    path = out_dir / name
    pdf.output(str(path))
    return path


# ================================ MEMO ======================================

def render_memo(data, out_dir):
    footer = data.get("footer_ar") or [""]
    pdf = ReportPDF(data.get("date_label", ""), data.get("subtitle_ar", ""),
                    footer, title_ar=data.get("title_ar", BRAND_AR))
    pdf.add_page()
    for sec in data.get("sections", []):
        if sec.get("heading_ar"):
            pdf.section_title(sec["heading_ar"])
        for para in sec.get("paragraphs_ar", []):
            pdf.body_ar(para, size=10.6, lh=6.6)
            pdf.ln(1.2)
        for b in sec.get("bullets_ar", []):
            pdf.body_ar("•  " + b, size=10.4, lh=6.4)
            pdf.ln(0.6)
        table = sec.get("table")
        if table:
            pdf.ln(1.5)
            widths = table.get("widths")
            headers = table["headers_ar"]
            if not widths:
                widths = [(PAGE_W - 2 * MARGIN) / len(headers)] * len(headers)
            cols = list(zip(headers, widths))
            pdf.table_header(cols)
            for row in table["rows"]:
                y = pdf.get_y()
                if y > PAGE_H - 46:
                    pdf.add_page()
                    y = pdf.get_y()
                pdf.set_font("Main", size=9.8)
                cell_ws = [w - 4 for _, w in cols]
                line_counts = [len(pdf.multi_cell(cw, 5.6, str(v), align="R",
                                                  dry_run=True, output="LINES"))
                               for cw, v in zip(cell_ws, row)]
                row_h = max(9, max(line_counts) * 5.6 + 3.2)
                x = PAGE_W - MARGIN
                for (label, w), val in zip(cols, row):
                    x -= w
                    pdf.set_xy(x + 2, y + 1.6)
                    pdf.set_font("Main", size=9.8)
                    pdf.set_text_color(*INK)
                    pdf.multi_cell(w - 4, 5.6, str(val),
                                   align="R" if x + w == PAGE_W - MARGIN else "C")
                pdf._rule(y + row_h, color=HAIRLINE, width=0.25)
                pdf.set_y(y + row_h + 0.8)
            pdf.ln(2)
        pdf.ln(2.5)

    name = data.get("filename") or "مذكرة {}.pdf".format(data.get("date_label", ""))
    path = out_dir / name
    pdf.output(str(path))
    return path


# ================================= CLI ======================================

def main():
    ap = argparse.ArgumentParser(description="Render /us-picks Arabic weekly PDFs")
    ap.add_argument("mode", choices=["picks", "results", "memo"])
    ap.add_argument("payload", help="path to the JSON payload")
    ap.add_argument("--out", help="output directory override")
    args = ap.parse_args()

    with open(args.payload, encoding="utf-8") as fh:
        data = json.load(fh)
    out_dir = resolve_out_dir(args.out)
    renderer = {"picks": render_picks, "results": render_results, "memo": render_memo}[args.mode]
    path = renderer(data, out_dir)
    print("SAVED: {}".format(path))


if __name__ == "__main__":
    main()
