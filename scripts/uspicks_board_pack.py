#!/usr/bin/env python3
"""uspicks_board_pack.py — build the Board of Advisors evidence pack (v5.9, 2026-08-17).

A READER, not a judge: it assembles the facts the /us-picks Board needs into one
self-contained JSON file so the Secretary + directors (Opus agents launched by the
Workflow in commands/us-picks.md Phase U.9) argue over the same evidence and can
verify every number against the same sources. Nothing here changes a score, a
grade, or a file other than the pack it writes.

What goes in (all local, all already on disk):
  - system identity: version label, active/deactivated rule states + reminder statuses
  - tracker Summary Statistics + Sector/Catalyst tables (verbatim rows)
  - every logged week: header lines, Picks rows (status/score/outcome/rank/return),
    Runners-Up rows, Grade Reason lines
  - Lessons Learned + Cumulative Blind Spots (verbatim — the era's recorded analyses)
  - the whole Board Decision Ledger (prior verdicts, auto-reviews, rejected topics)
  - L1 candidate-log stats (distinct weeks, rows per week, partial-recovery flags)
  - the stocks/_analysis/ inventory (pre-registered tests + their artifacts)
  - run-artifact timestamps (lost-run detection: price scan / mech scores / stage-B
    evidence / gainers scan / L1 log / PDF payload)
  - pointers to the charter, spec, scoring model (the agents Read those themselves)

Usage:
  python3 scripts/uspicks_board_pack.py --session YYYY-MM-DD --trigger "graded week 2026-08-10"
  -> writes ~/.claude/stocks/board/YYYY-MM-DD/evidence-pack.json and prints a summary.
  python3 scripts/uspicks_board_pack.py --render ~/.claude/stocks/board/YYYY-MM-DD/session.json
  -> prints the fixed-width BOARD DECISIONS card + the tracker ledger block (charter §9)
     from the Workflow's persisted return value, so alignment never depends on hand-padding.
Stdlib only. Local-only output (stocks/ is repo-ignored).
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / ".claude"
TRACKER = ROOT / "stocks" / "us-weekly-tracker.md"
L1_LOG = ROOT / "stocks" / "us-candidate-scores.jsonl"
ANALYSIS_DIR = ROOT / "stocks" / "_analysis"
BOARD_DIR = ROOT / "stocks" / "board"
STOCKS = ROOT / "stocks"
COMMAND = ROOT / "commands" / "us-picks.md"
CHARTER = ROOT / "skills" / "us-stocks-memory" / "references" / "board-charter.md"
SPEC = ROOT / "skills" / "us-stocks-memory" / "references" / "us-picks-system-spec.md"
SCORING = ROOT / "skills" / "us-stocks-memory" / "references" / "scoring-model.md"
ARTIFACTS = [
    "stocks/price-analyzer-output.json", "stocks/mech-scores.json",
    "stocks/stageb-evidence.json", "stocks/gainers-output.json",
    "stocks/us-candidate-scores.jsonl", "stocks/uspicks-pdf-payload.json",
    "stocks/us-weekly-tracker.md",
]


def read(p):
    try:
        return Path(p).read_text(encoding="utf-8")
    except OSError:
        return ""


def section(text, heading_regex):
    """Return the body of the first '## <heading>' matching regex, up to the next '## '."""
    m = re.search(r"^## (" + heading_regex + r")[^\n]*\n(.*?)(?=^## |\Z)", text,
                  re.MULTILINE | re.DOTALL)
    return m.group(2).strip() if m else ""


def table_rows(block):
    rows = []
    for line in block.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r"[-:\s]*", c) for c in cells):
            continue
        rows.append(cells)
    return rows


def rules_state(text):
    m = re.search(r"<!-- RULES START -->(.*?)<!-- RULES END -->", text, re.DOTALL)
    body = m.group(1) if m else ""
    rules = []
    for line in body.splitlines():
        s = line.strip()
        hm = re.match(r"^\*\*([A-Z]\d): (.+?)\*\*", s)
        if hm:
            state = "DEACTIVATED" if "DEACTIVATED" in s else ("ACTIVE" if "ACTIVE" in s else "unknown")
            rules.append({"id": hm.group(1), "header": s[:220], "state": state})
    # Two formats coexist in the tracker: `**Reminder status:** PENDING X` and
    # `**Reminder status: DONE 2026-08-08**` — capture both halves and join.
    statuses = re.findall(r"\*\*Reminder status:?\s*([^*\n]*)\*\*:?\s*([^\n]*)", body)
    lines = [(a + " " + b).strip()[:200] for a, b in statuses]
    return {"rules": rules, "reminder_status_lines": lines,
            "raw_length_chars": len(body)}


def weeks(text):
    out = []
    hist = text.split("## Pick History", 1)
    hist = hist[1] if len(hist) > 1 else ""
    parts = re.split(r"^### Week of ", hist, flags=re.MULTILINE)
    for part in parts[1:]:
        head, _, body = part.partition("\n")
        wk = {"week": head.strip()[:80], "header_lines": [], "picks": [], "runners_up": [],
              "grade_reasons": [], "notes": []}
        for line in body.splitlines():
            s = line.strip()
            if s.startswith("**") and ":**" in s and len(wk["header_lines"]) < 12:
                wk["header_lines"].append(s[:400])
            elif s.startswith("- Grade Reason:") or s.startswith("  - Grade Reason:"):
                wk["grade_reasons"].append(s[:600])
            elif s.startswith("> ") and len(wk["notes"]) < 4:
                wk["notes"].append(s[:400])
        # tables: Picks (has 'Status' column) and Runners-Up (a Rank-ish column, no Status).
        # Header history: 'Rank (Full)' (v5.6-v6.0) -> 'Rank (ctx)' (v6.1-v6.2) -> 'Rank' (v6.3).
        for tbl in re.split(r"\n\s*\n", body):
            rows = table_rows(tbl)
            if len(rows) < 2:
                continue
            hdr = rows[0]
            if "Status" in hdr and "Ticker" in hdr:
                for r in rows[1:]:
                    d = dict(zip(hdr, r))
                    wk["picks"].append({k: d.get(k) for k in
                                        ("Ticker", "Status", "Score", "Sector", "Last Close",
                                         "Entry Open $", "Exit $", "Exit AH $", "Close Return",
                                         "Peak Tgt %", "Peak Reached", "Peak $", "Peak %",
                                         "Outcome", "Rank (Full)", "Rank (ctx)", "Rank",
                                         "Realized") if k in d})
            elif ("Ticker" in hdr and "Status" not in hdr
                  and any(h.startswith("Rank") for h in hdr)):
                for r in rows[1:]:
                    d = dict(zip(hdr, r))
                    wk["runners_up"].append(d)
        out.append(wk)
    return out


# rule L1 `bm_source` enum (Board-wired 2026-08-22, BP-2026-08-22-2, APPROVED 5-0;
# COMPLETED 2026-09-04 by BP-2026-09-04-1, APPROVED 5-0 — `financialdatasets` added).
# Total-order partition over the Big Money agent's Signal-A ladder, first match wins:
#   section16_exempt (structural exemption, evaluated FIRST — BP-2026-08-22-2 condition 2)
#   -> financialdatasets (the licensed Form 4 feed: the FIRST DATA rung; the user
#      re-instated the subscription himself on 2026-08-29, so the token is LIVE)
#   -> openinsider -> polygon_news_fallback -> none   (rungs 1-5 emitted by the agent)
#   then not_run / unmapped, assigned by Phase 6.0 itself.
# `edgar` is absent by construction (no EDGAR path exists). A token outside this tuple is
# coerced to `unmapped` for the COUNTS but is ALSO recorded raw (sanitized) in
# `bm_source_unknown_tokens`, so an unknown token can never again be invisible to the
# Board — the 2026-08-31 pack silently relabelled 19 `financialdatasets` rows, 4 of the
# 5 picks, and reported the licensed feed's availability as 0.0%.
BM_SOURCE_ENUM = ("section16_exempt", "financialdatasets", "openinsider",
                  "polygon_news_fallback", "none", "not_run", "unmapped")
# The two LICENSED Form-4 rungs (BP-2026-09-04-1 mechanism 3). `insider_source_ok_pct`
# keeps its FROZEN definition (numerator `openinsider` only — BP-2026-08-22-2's open
# auto-review, horizon ~2026-09-18, must measure an unchanged quantity); the ADDITIVE
# `insider_licensed_ok_pct` counts both rungs over the same denominator.
_LICENSED_RUNGS = ("openinsider", "financialdatasets")
_UNKNOWN_TOKEN_MAX_LEN = 64      # sanitize at capture (Chair C11)
_UNKNOWN_TOKEN_MAX_KEYS = 20     # per week; overflow bucketed as "__overflow__"
_UNKNOWN_TOKEN_SAFE = re.compile(r"[^A-Za-z0-9_.:\-]")
# insider_source_ok_pct denominator (Chair condition 7): rung-1 (`openinsider`) rows over
# rows the agent ACTUALLY RAN — `not_run` excluded (agent never saw the ticker) and
# `section16_exempt` excluded (structurally exempt, no Form 4 can exist). A week with zero
# agent output yields None -> reported as "n/a", NEVER 0%, so BP-2026-08-21-3's advisory
# <50% trip-wire cannot fire on an agent-execution failure and mis-surface a spending
# recommendation. DESCRIPTIVE RATE, never an inferential test.
_OK_DENOM_EXCLUDED = ("not_run", "section16_exempt")


def _ok_pct(counts):
    """Share of agent-run rows that came off the `openinsider` rung. None when no agent-run
    rows exist. FORMULA FROZEN (BP-2026-09-04-1 C4) — do not widen the numerator here."""
    denom = sum(v for k, v in counts.items() if k not in _OK_DENOM_EXCLUDED)
    if denom <= 0:
        return None
    return round(100.0 * counts.get("openinsider", 0) / denom, 1)


def _nd(counts, numer_keys):
    """[numerator, denominator] beside every rate (BP-2026-09-04-1 C6) — the raw N/D, so a
    denominator shift (8 -> 1,807 at the 2026-08-31 log_scope boundary) is never read as a
    signal."""
    denom = sum(v for k, v in counts.items() if k not in _OK_DENOM_EXCLUDED)
    numer = sum(counts.get(k, 0) for k in numer_keys)
    return [numer, denom]


def _licensed_pct(counts):
    """ADDITIVE licensed-rung rate: (`openinsider` + `financialdatasets`) over the SAME
    denominator as `insider_source_ok_pct`. None when no agent-run rows exist."""
    numer, denom = _nd(counts, _LICENSED_RUNGS)
    if denom <= 0:
        return None
    return round(100.0 * numer / denom, 1)


def _sanitize_token(tok):
    return _UNKNOWN_TOKEN_SAFE.sub("_", str(tok))[:_UNKNOWN_TOKEN_MAX_LEN] or "_"


def _bump_unknown(bucket, raw):
    """Record a raw out-of-enum token, capped at _UNKNOWN_TOKEN_MAX_KEYS distinct keys."""
    if raw not in bucket and len(bucket) >= _UNKNOWN_TOKEN_MAX_KEYS:
        raw = "__overflow__"
    bucket[raw] = bucket.get(raw, 0) + 1


def _norm_scope(v):
    """L1 `log_scope` era marker: 'top50' (weeks <= 2026-08-24) | 'all-eligible' (2026-08-31+;
    the widened rows carry 'full', read as all-eligible) | 'unknown' when absent."""
    if v in (None, ""):
        return "unknown"
    v = str(v)
    return "all-eligible" if v in ("full", "all-eligible") else v


def l1_stats():
    if not L1_LOG.is_file():
        return {"exists": False}
    per_week = {}
    statuses = {}
    partial = {}
    bm_src = {}            # week -> {token: n} over ALL rows
    statuses_by_era = {}   # sel_rule era -> {status: n} (BP-2026-08-28-1)
    bm_src_picks = {}      # sel_rule era -> week -> {token: n}, status == "pick" only
    bm_src_recovery = {}   # week -> {token: n} over partial_recovery rows (condition 9)
    bm_unknown = {}        # week -> {raw_token: n} for OUT-OF-ENUM tokens (BP-2026-09-04-1)
    bm_unknown_picks = {}  # sel_rule era -> week -> {raw_token: n}, status == "pick" only
    bm_scope = {}          # week -> log_scope era marker (C5: never pool across it)
    identity_violations = []
    n = 0
    for line in read(L1_LOG).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        n += 1
        w = d.get("week_start", "?")
        per_week[w] = per_week.get(w, 0) + 1
        st = d.get("status", "?")
        statuses[st] = statuses.get(st, 0) + 1
        _era = str(d.get("sel_rule") or "top5")
        statuses_by_era.setdefault(_era, {})[st] = statuses_by_era.setdefault(_era, {}).get(st, 0) + 1
        rec = bool(d.get("partial_recovery"))
        if rec:
            partial[w] = True
        # --- rule L1 bm_source provenance (absent on every pre-2026-08-22 row) ---
        tok = d.get("bm_source")
        if tok is None:
            continue
        tok = str(tok)
        bm_scope.setdefault(w, _norm_scope(d.get("log_scope")))
        if tok not in BM_SOURCE_ENUM:
            # BP-2026-09-04-1 mechanism 2: coerce for the counts, but NEVER silently —
            # the raw token is recorded (sanitized, capped) so it stays visible.
            raw = _sanitize_token(tok)
            _bump_unknown(bm_unknown.setdefault(w, {}), raw)
            if st == "pick":
                _era = str(d.get("sel_rule") or "top5")
                _bump_unknown(bm_unknown_picks.setdefault(_era, {}).setdefault(w, {}), raw)
            tok = "unmapped"
        bm_src.setdefault(w, {})[tok] = bm_src.setdefault(w, {}).get(tok, 0) + 1
        # BP-2026-08-28-1 (Chair condition): the pick BAND changed on 2026-08-28
        # from S[1..5] to S[6..10]. `status == "pick"` therefore names a DIFFERENT
        # population on either side of that date, so this reader — whose consumer
        # is BP-2026-08-22-2's still-open auto-review (horizon ~2026-09-18) — is
        # partitioned on `sel_rule` so the measurement population does not change
        # silently mid-horizon. Rows without `sel_rule` are `top5` by absence.
        if st == "pick":
            era = str(d.get("sel_rule") or "top5")
            bm_src_picks.setdefault(era, {}).setdefault(w, {})[tok] = \
                bm_src_picks.setdefault(era, {}).setdefault(w, {}).get(tok, 0) + 1
        if rec:
            bm_src_recovery.setdefault(w, {})[tok] = bm_src_recovery.setdefault(w, {}).get(tok, 0) + 1
        # condition 10: bm_source == 'not_run' iff BM is null
        bm_null = d.get("BM") is None
        if (tok == "not_run") != bm_null:
            identity_violations.append({"week_start": w, "ticker": d.get("ticker"),
                                        "bm_source": tok, "BM_is_null": bm_null})
    out = {"exists": True, "rows": n, "distinct_weeks": sorted(per_week),
           "l1_runs": len(per_week), "rows_per_week": per_week,
           "status_counts": statuses, "partial_recovery_weeks": sorted(partial),
           "status_counts_by_sel_rule": statuses_by_era}
    # Named reader for BP-2026-08-22-2. Raw counts are always emitted alongside the derived
    # rate so any director can recompute under another convention (condition 7).
    out["bm_source_counts"] = bm_src
    # Keyed by sel_rule era first ("top5" | "S6-10"), then week — never pooled
    # across the 2026-08-28 band change (BP-2026-08-28-1 Chair condition).
    out["bm_source_counts_picks_only_by_sel_rule"] = bm_src_picks
    out["bm_source_counts_partial_recovery"] = bm_src_recovery
    out["bm_source_rows"] = sum(sum(v.values()) for v in bm_src.values())
    out["bm_source_coverage_pct"] = (
        round(100.0 * out["bm_source_rows"] / n, 1) if n else 0.0)
    out["bm_source_identity_violations"] = identity_violations
    # --- CK1 provisional orphans (Board-wired 2026-08-28, BP-2026-08-28-3) ---
    # Row-count-aware (condition 13): the SOLE detector of the crash case — a run
    # that dies before Phase 6.0 never enters the L1 week list, so there is no
    # denominator there. A week with provisional rows and an authoritative count
    # BELOW them is an orphan (either a crash, or a short append that Part A3
    # correctly refused to clear).
    prov_p = STOCKS / "us-candidate-scores-provisional.jsonl"
    orphans, prov_by_week = [], {}
    if prov_p.exists():
        for line in read(prov_p).splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            w = r.get("week_start", "?")
            prov_by_week[w] = prov_by_week.get(w, 0) + 1
    for w, np_ in sorted(prov_by_week.items()):
        na = per_week.get(w, 0)
        if na < np_:
            orphans.append({"week_start": w, "n_provisional": np_,
                            "n_authoritative": na,
                            "class": "crash_or_short_append"})
    out["provisional_orphans"] = orphans
    out["provisional_rows_by_week"] = prov_by_week
    # Stale-orphan acknowledgement path: an orphan surviving 2 consecutive packs
    # is recorded so it is triaged rather than becoming background noise.
    out["provisional_orphans_note"] = (
        "An orphan week means provisional rows exist that the authoritative log "
        "does not cover. Triage it; if it persists across 2 consecutive packs, "
        "acknowledge it explicitly in the ledger rather than letting it stand.")
    ck_idx = STOCKS / "_l1ckpt" / "_index.jsonl"
    ck_rows = []
    if ck_idx.exists():
        for line in read(ck_idx).splitlines():
            line = line.strip()
            if line:
                try:
                    ck_rows.append(json.loads(line))
                except ValueError:
                    pass
    out["ck1_index"] = ck_rows
    out["insider_source_ok_pct"] = {w: _ok_pct(c) for w, c in bm_src.items()}
    # Nested era -> week (BP-2026-08-28-1): the pick band changed on 2026-08-28,
    # so this rate is reported per sel_rule era and never pooled across it.
    out["insider_source_ok_pct_picks_only_by_sel_rule"] = {
        era: {w: _ok_pct(c) for w, c in weeks.items()}
        for era, weeks in bm_src_picks.items()
    }
    # ---- BP-2026-09-04-1 (Board-wired 2026-09-04, APPROVED 5-0) ----
    # (a) out-of-enum tokens, raw + sanitized, overall and picks-only (C11 + engineer 6);
    out["bm_source_unknown_tokens"] = bm_unknown
    out["bm_source_unknown_tokens_picks_only_by_sel_rule"] = bm_unknown_picks
    # (b) the log_scope era marker beside every per-week count/rate (C5) — the
    #     denominator moved 8 -> 1,807 on 2026-08-31 for reasons unrelated to any rung;
    out["bm_source_log_scope"] = bm_scope
    # (c) raw numerator/denominator beside every rate (C6);
    out["insider_source_ok_nd"] = {w: _nd(c, ("openinsider",)) for w, c in bm_src.items()}
    out["insider_source_ok_nd_picks_only_by_sel_rule"] = {
        era: {w: _nd(c, ("openinsider",)) for w, c in weeks.items()}
        for era, weeks in bm_src_picks.items()
    }
    # (d) the ADDITIVE licensed rate (openinsider + financialdatasets / same denominator);
    out["insider_licensed_ok_pct"] = {w: _licensed_pct(c) for w, c in bm_src.items()}
    out["insider_licensed_ok_nd"] = {w: _nd(c, _LICENSED_RUNGS) for w, c in bm_src.items()}
    out["insider_licensed_ok_pct_picks_only_by_sel_rule"] = {
        era: {w: _licensed_pct(c) for w, c in weeks.items()}
        for era, weeks in bm_src_picks.items()
    }
    out["insider_licensed_ok_nd_picks_only_by_sel_rule"] = {
        era: {w: _nd(c, _LICENSED_RUNGS) for w, c in weeks.items()}
        for era, weeks in bm_src_picks.items()
    }
    # (e) both rates PARTITIONED on log_scope — never rendered as one series across the
    #     2026-08-31 top50 -> all-eligible boundary (C5, statistician 1/4, devil 5).
    def _by_scope(rate_fn):
        res = {}
        for w, c in bm_src.items():
            res.setdefault(bm_scope.get(w, "unknown"), {})[w] = rate_fn(c)
        return res
    out["insider_source_ok_pct_by_log_scope"] = _by_scope(_ok_pct)
    out["insider_licensed_ok_pct_by_log_scope"] = _by_scope(_licensed_pct)
    out["bm_source_rates_note"] = (
        "insider_source_ok_pct = openinsider-rung rows / agent-run rows (not_run + "
        "section16_exempt excluded) — FORMULA FROZEN for BP-2026-08-22-2's open auto-review "
        "(~2026-09-18). insider_licensed_ok_pct = (openinsider + financialdatasets) / the same "
        "denominator — ADDITIVE (BP-2026-09-04-1). Both are DESCRIPTIVE rates, reported per "
        "log_scope stratum and per sel_rule era, never pooled across the 2026-08-31 boundary "
        "(denominator 8 -> 1,807). BP-2026-08-21-3's buy-FD advisory trip-wire is MOOT while "
        "the user's Financial Datasets subscription is live (re-instated by the user "
        "2026-08-29); if the feed ever lapses it re-arms on the PICKS-ONLY, sel_rule-"
        "partitioned insider_licensed_ok_pct, never the whole-log rate.")
    return out


def analysis_inventory():
    if not ANALYSIS_DIR.is_dir():
        return {"exists": False}
    items = []
    for p in sorted(ANALYSIS_DIR.iterdir()):
        try:
            st = p.stat()
        except OSError:
            continue
        items.append({"name": p.name, "is_dir": p.is_dir(), "bytes": st.st_size,
                      "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")})
    readme = read(ANALYSIS_DIR / "README.md")
    return {"exists": True, "items": items, "readme_excerpt": readme[:6000]}


def artifact_times():
    out = {}
    for rel in ARTIFACTS:
        p = ROOT / rel
        try:
            st = p.stat()
            out[rel] = {"modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "bytes": st.st_size}
        except OSError:
            out[rel] = None
    return out


def prior_sessions():
    if not BOARD_DIR.is_dir():
        return []
    return sorted(p.name for p in BOARD_DIR.iterdir() if p.is_dir())


# ---------------------------------------------------------------------------
# --render: BOARD DECISIONS card + ledger block from a session.json (charter §9)
# ---------------------------------------------------------------------------

W = 69  # inner width of the fixed-width card


def _wrap(label, text, width=W):
    """Wrap `text` under a left label into card lines '|  label text  |'."""
    import textwrap
    text = " ".join(str(text or "").split()) or "—"
    lab = (label + " ").ljust(11) if label else "           "
    first = width - 2 - len(lab)
    lines = textwrap.wrap(text, width=first, break_on_hyphens=False, break_long_words=True) or ["—"]
    out = ["|  " + lab + lines[0].ljust(first) + "|"]
    for l in lines[1:]:
        out.append("|  " + " " * len(lab) + l.ljust(first) + "|")
    return out


def _short(text, n=220):
    """Compact a long field for the tracker ledger / card; the full text stays in session.json."""
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def _tally(d):
    t = d.get("tally") or {}
    return "APPROVE {} · REJECT {} · DEFER {}".format(t.get("approve", 0), t.get("reject", 0), t.get("defer", 0)) + \
        ("  (HARD BLOCK)" if d.get("hard_block") else "")


def render(session_path):
    S = json.loads(Path(session_path).read_text(encoding="utf-8"))
    sd = S.get("session_date", "?")
    sec = S.get("secretary") or {}
    decs = S.get("decisions") or []
    pack_p = BOARD_DIR / sd / "evidence-pack.json"
    ev = ""
    if pack_p.is_file():
        try:
            d = json.loads(pack_p.read_text(encoding="utf-8")).get("derived", {})
            ev = "{} graded weeks · {} picks · {} logged runs".format(
                d.get("graded_weeks", "?"), d.get("graded_picks", "?"), d.get("l1_runs", "?"))
        except ValueError:
            pass
    bar = "+" + "=" * W + "+"
    mid = "+" + "-" * W + "+"
    card = [bar, "|  BOARD OF ADVISORS — SESSION {}  (v6.0)".format(sd).ljust(W + 1) + "|"]
    card += _wrap("Trigger:", S.get("trigger", ""))
    if ev:
        card += _wrap("Evidence:", ev)
    if S.get("error"):
        card += [mid] + _wrap("FAILED:", S["error"] + " — no change made")
    for d in decs:
        p = d.get("proposal") or {}
        r = d.get("ruling") or {}
        card.append(mid)
        card += _wrap("", "{}  [{}]".format(p.get("id", "?"), p.get("kind", "?")))
        card += _wrap("Proposal:", p.get("title", ""))
        card += _wrap("Votes:", _tally(d) + "  ->  " + d.get("final_verdict", "?"))
        card += _wrap("Why:", r.get("one_line", ""))
        if d.get("final_verdict") == "APPROVED":
            card += _wrap("Effect:", "live from your next /us-picks run; wired in " + ", ".join(Path(f).name for f in (p.get("files_to_wire") or [])))
            card += _wrap("Review:", _short(r.get("auto_review_terms", ""), 300))
            if r.get("conditions"):
                card += _wrap("Conditions:", "{} attached by the directors — all wired (full text: session.json)".format(len(r["conditions"])))
        elif d.get("final_verdict") == "DEFERRED":
            card += _wrap("Re-review:", _short(r.get("re_review_condition", ""), 300))
        else:
            wcm = "; ".join("{}: {}".format(v.get("lens", "?"), _short(v.get("what_would_change_my_mind", ""), 140)) for v in d.get("votes") or [] if v.get("vote") != "APPROVE")
            card += _wrap("Would change the Board's mind:", wcm)
        adv = r.get("advisory_to_user")
        if adv:
            card += _wrap("Advisory:", _short(adv, 600))
    cnf = sec.get("considered_not_filed") or []
    card.append(mid)
    card += _wrap("Not filed:", "{} considered but not filed — {}".format(len(cnf), "; ".join(_short(c.get("topic", ""), 70) for c in cnf) or "none"))
    checks = sec.get("checks_executed") or []
    if checks:
        card += _wrap("Checks run:", "; ".join("{} -> {}".format(_short(c.get("check"), 60), _short(c.get("result"), 40)) for c in checks))
    card += _wrap("", "Nothing here needs an answer — you are being informed. Full record: tracker Board Decision Ledger + stocks/board/{}/".format(sd))
    card.append(bar)
    print("\n".join(card))

    # ledger block (markdown)
    print("\n<!-- LEDGER BLOCK -->")
    print("### Session {} — trigger: {} — evidence: {}".format(sd, S.get("trigger", "?"), ev or "n/a"))
    print()
    print("| ID | Kind | Proposal | Votes A/R/D | Verdict | Effective | Auto-review |")
    print("|----|------|----------|-------------|---------|-----------|-------------|")
    for d in decs:
        p = d.get("proposal") or {}
        r = d.get("ruling") or {}
        t = d.get("tally") or {}
        v = d.get("final_verdict", "?")
        eff = "next run" if v == "APPROVED" else "—"
        rev = (r.get("auto_review_terms") if v == "APPROVED" else (r.get("re_review_condition") if v == "DEFERRED" else "—")) or "—"
        print("| {} | {} | {} | {}/{}/{}{} | {} | {} | {} |".format(
            p.get("id"), p.get("kind"), _short(p.get("title", ""), 160), t.get("approve", 0), t.get("reject", 0),
            t.get("defer", 0), " (HB)" if d.get("hard_block") else "", v, eff, _short(rev, 260)))
    print()
    for d in decs:
        p = d.get("proposal") or {}
        r = d.get("ruling") or {}
        votes = "; ".join("{} {} ({:.2f})".format(v.get("lens"), v.get("vote"), float(v.get("confidence") or 0)) for v in d.get("votes") or [])
        line = "- **{} — ruling:** {} · votes: {}".format(p.get("id"), _short(r.get("one_line", ""), 300), votes)
        if r.get("conditions"):
            line += " · {} director condition(s) attached (full text: `stocks/board/{}/session.json`)".format(len(r["conditions"]), sd)
        if d.get("final_verdict") == "APPROVED":
            line += " · files: " + ", ".join(Path(f).name for f in (p.get("files_to_wire") or []))
        else:
            wcm = "; ".join("{}: {}".format(v.get("lens"), _short(v.get("what_would_change_my_mind", ""), 160)) for v in d.get("votes") or [] if v.get("vote") != "APPROVE")
            line += " · would change the Board's mind: " + wcm
        print(line)
    print("- **Considered, not filed ({}):** ".format(len(cnf)) + (" · ".join("{} — {}".format(_short(c.get("topic"), 90), _short(c.get("why", ""), 150)) for c in cnf) or "none"))
    if checks:
        print("- **Pre-committed checks executed:** " + " · ".join("{} → {}".format(_short(c.get("check"), 70), _short(c.get("result"), 120)) for c in checks))
    advs = [_short((d.get("ruling") or {}).get("advisory_to_user"), 700) for d in decs if (d.get("ruling") or {}).get("advisory_to_user")]
    print("- **Advisory to the user (constitutional, not enacted):** " + ("; ".join(advs) if advs else "none"))
    print("- **Full record:** `~/.claude/stocks/board/{}/` (evidence-pack.json · proposals.json · session.json — every vote and ruling verbatim).".format(sd))
    return 0



# --- Per-week ranked-universe archives (Board-wired 2026-08-28, BP-2026-08-28-2) ---
# READER ONLY. Reports the archive census the auto-review reads, and — condition
# 10 — distinguishes THREE missing states rather than two, so a blank never
# conflates "postponed, expected" with "graded but its yardstick is gone".
# Condition 3: reconstructions are reported as a DISTINCT CLASS, so wiring this
# reader cannot manufacture a false clean bill of health.
UNIV_ARCH_DIR = STOCKS / "_universe_archives"
ARCH_WIRED_WEEK = "2026-08-24"          # weeks before this predate the wiring


# ---- BP-2026-09-04-2 (Board-wired 2026-09-04, APPROVED 5-0) — universe_basis helpers ----
# The predicate lives in the WRITER (uspicks_archive_universe.derive_universe_basis) so the
# reader and the writer cannot drift; the reader recomputes it from top-level keys on every
# call and never trusts a stored label. Fail-open: an import failure yields the explicit
# marker below rather than a guess (a wrong basis label is worse than a missing one).
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from uspicks_archive_universe import derive_universe_basis as _derive_basis  # noqa: E402
except Exception:  # pragma: no cover
    def _derive_basis(d):
        return "derivation_unavailable"


def _configured_liq_floor():
    """The CONFIGURED floor (env-overridable, inside Board remit) — never a hard-coded
    literal, so a lawfully changed floor cannot silently reclassify a week (Chair C3)."""
    try:
        return float(os.environ.get("GAINERS_LIQ_FLOOR", "1000000"))
    except ValueError:
        return 1000000.0


PARTITION_RULE = (
    """PARTITION RULE (BP-2026-09-04-2): any retro-rank analysis that spans archived weeks of different `universe_basis` MUST partition on `universe_basis` AND `price_source`, OR report percentile-of-universe instead of raw rank, OR pool only with the basis mix stated in the artifact — and `unknown_legacy` is NOT comparable to `liquid_1m`; the percentile route is ANALYSIS-ONLY and may never compute, restate or substitute for a WIN tier, a published grade, or the F1 pass line."""
)


def universe_archives(weeks_in_tracker, graded_weeks=None):
    """Census of stocks/gainers-<WEEK_START>.json, by provenance class.

    `weeks_in_tracker` are WEEK_START date keys (YYYY-MM-DD). `graded_weeks`, when given,
    is the set of keys holding at least one GRADED pick row: only those can be
    "missing though graded" (Decision Review D-2026-09-26-2 — a superseded, skipped or
    still-pending week header is not a graded week and needs no archive yet)."""
    present, reconstructed, siblings = {}, [], {}
    basis_conflict = []
    for f in sorted(STOCKS.glob("gainers-2*.json")):
        stem = f.stem.replace("gainers-", "")
        if "-rescan-" in stem or "-regen-" in stem:
            wk = stem.split("-rescan-")[0].split("-regen-")[0]
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                d = {}
            siblings.setdefault(wk, []).append({
                "file": f.name,
                "price_source": d.get("price_source"),
                "universe_size": d.get("universe_size"),
                "measurement_basis": d.get("measurement_basis"),
                # BP-2026-09-04-2 engineer 7: a sibling on a different basis than its
                # primary is exactly the divergence the label exists to surface.
                "liq_floor": d.get("liq_floor"),
                "liq_floor_applied": d.get("liq_floor_applied"),
                "universe_basis": _derive_basis(d),
            })
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        m = d.get("_archive_meta") or {}
        # BP-2026-09-04-2 Chair C2/C4: the basis is RECOMPUTED from the file's TOP-LEVEL
        # keys on every call (never from _archive_meta, never from _index.jsonl); a stored
        # label that disagrees is surfaced as basis_label_conflict, never preferred.
        basis = _derive_basis(d)
        stored = m.get("universe_basis")
        if stored is not None and stored != basis:
            basis_conflict.append(stem)
        present[stem] = {
            "file": f.name,
            "source": m.get("source"),
            "universe_size": d.get("universe_size"),
            "price_source": d.get("price_source"),
            "measurement_basis": d.get("measurement_basis"),
            "universe_completeness_pct": d.get("universe_completeness_pct"),   # C10
            "entry_date": d.get("entry_date"),
            "exit_date": d.get("exit_date"),
            "archived_at": m.get("archived_at"),
            "rows": len(d.get("ranked_universe") or []),
            "liq_floor": d.get("liq_floor"),                    # top-level, raw
            "liq_floor_applied": d.get("liq_floor_applied"),    # top-level
            "liq_source": d.get("liq_source"),
            "universe_basis": basis,                            # DERIVED — partition key only
            "stored_basis": stored,                             # what the writer stamped (may be None)
        }
        if m.get("source") in ("regenerated", "hand_made"):
            reconstructed.append(stem)

    postponed = set()
    pj = UNIV_ARCH_DIR / "_postponed.jsonl"
    if pj.exists():
        for line in pj.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                postponed.add(json.loads(line).get("week_start"))
            except Exception:
                pass

    # condition 10 — three distinct states, never two
    missing_postponed, missing_graded, missing_historical = [], [], []
    for wk in weeks_in_tracker:
        if wk in present:
            continue
        if wk in postponed:
            missing_postponed.append(wk)
        elif wk < ARCH_WIRED_WEEK:
            missing_historical.append(wk)
        elif graded_weeks is not None and wk not in graded_weeks:
            continue                           # pending / skipped / superseded: no archive expected yet
        else:
            missing_graded.append(wk)          # LOUD: graded, yardstick gone

    # ---- BP-2026-09-04-2 (Board-wired 2026-09-04, APPROVED 5-0): liquidity-basis census ----
    # Counts are over the present[] census of FILES ON DISK only — never the
    # -rescan-/-regen- siblings and never _index.jsonl (whose 2026-08-24 sentinel row,
    # universe_size 1234567 with no file on disk, is a 2026-08-28 acceptance-test artifact
    # and must not enter the counts — Chair C11).
    basis_counts = {}
    for wk, row in present.items():
        basis_counts.setdefault(row["universe_basis"], []).append(wk)
    basis_counts = {b: sorted(ws) for b, ws in basis_counts.items()}
    configured = _configured_liq_floor()
    ok_labels = {"liquid_1m"} if configured >= 1000000.0 else {"other_floor:%g" % configured}
    # C14: a graded v6.3 week whose archive resolves to anything but the configured liquid
    # basis is a FLAGGED FAULT at build time — never left to the 4-week auto-review horizon.
    basis_faults = sorted(wk for wk in weeks_in_tracker
                          if wk in present and present[wk]["universe_basis"] not in ok_labels)

    return {
        "present": present,
        "reconstructed_not_as_graded": sorted(reconstructed),
        "rescan_regen_siblings": siblings,
        "missing_postponed_expected": sorted(missing_postponed),
        "missing_though_graded_LOUD": sorted(missing_graded),
        "missing_predates_wiring": sorted(missing_historical),
        "canonical_meaning": ("gainers-<WEEK_START>.json is the record of the ranked "
                              "universe THE GRADE WAS COMPUTED FROM, not the most "
                              "accurate scan of that week."),
        # BP-2026-09-04-2 — `universe_basis` is DERIVED and may serve ONLY as an analysis
        # partition key: never an input to any rank, cutoff, grade, WIN tier, score or
        # Summary Statistics row (Chair C5; violation = immediate revert).
        "basis_counts": basis_counts,
        "mixed_basis": len(basis_counts) > 1,
        "basis_label_conflict": sorted(basis_conflict),
        "basis_faults_LOUD": basis_faults,
        "configured_liq_floor": configured,
        "partition_rule": PARTITION_RULE,
        "basis_note": ("`source` (hand_made / regenerated / live_scan) is NOT a basis signal "
                       "and must never be used as a proxy — today it is 6/6 correlated with "
                       "basis by coincidence (C10). `unknown_legacy` is NOT comparable to "
                       "`liquid_1m` — explicitly not 'presumably the same'. Measured on the "
                       "single cross-basis week (2026-08-31: full-market n=5,003 vs liquid "
                       "n=3,596): percentile-of-universe is invariant to 0.01pp at the 10th "
                       "percentile (rank 500 = +6.07% vs rank 359 = +6.06%) but shifts 1.85pp "
                       "at ~30th (CRM 30.46% -> 32.31%) — sanctioned for top-500-tail "
                       "analyses, NOT for mid-distribution pooling; re-measure the first time "
                       "a second cross-basis pair exists (C8)."),
    }

def main():
    ap = argparse.ArgumentParser(description="/us-picks Board evidence pack builder")
    ap.add_argument("--session", help="session date YYYY-MM-DD")
    ap.add_argument("--trigger", default="unspecified", help="why the Board convenes")
    ap.add_argument("--out", default=None, help="override output path")
    ap.add_argument("--render", default=None, metavar="SESSION_JSON",
                    help="render the BOARD DECISIONS card + ledger block from a session.json (charter §9)")
    args = ap.parse_args()
    if args.render:
        return render(args.render)
    if not args.session:
        ap.error("--session is required (or use --render SESSION_JSON)")

    tracker = read(TRACKER)
    if not tracker:
        print("ERROR: tracker not found at", TRACKER)
        return 1
    cmd = read(COMMAND)
    vm = re.search(r"^# US Weekly Stock Picker \((v[\d.]+)\)", cmd, re.MULTILINE)
    tm = re.search(r"^# US Stock Picker — Performance Tracker \((v[\d.]+)\)", tracker, re.MULTILINE)

    pack = {
        "pack_version": 1,
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "session_date": args.session,
        "trigger": args.trigger,
        "system": {
            "command_version": vm.group(1) if vm else None,
            "tracker_version": tm.group(1) if tm else None,
            "charter": str(CHARTER), "spec": str(SPEC), "scoring_model": str(SCORING),
            "tracker": str(TRACKER), "l1_log": str(L1_LOG), "analysis_dir": str(ANALYSIS_DIR),
        },
        "rules": rules_state(tracker),
        "summary_statistics": table_rows(section(tracker, r"Summary Statistics")),
        "sector_performance": table_rows(section(tracker, r"Sector Performance")),
        "catalyst_performance": table_rows(section(tracker, r"Catalyst Performance")),
        "lessons_learned": section(tracker, r"Lessons Learned")[:40000],
        "blind_spots": section(tracker, r"Missed Opportunity Analysis")[:20000],
        "board_ledger": section(tracker, r"Board of Advisors")[:40000],
        "weeks": weeks(tracker),
        "l1_log": l1_stats(),
        "analysis": analysis_inventory(),
        "artifact_times": artifact_times(),
        "prior_board_sessions": prior_sessions(),
    }
    # D-2026-09-26-2: key weeks by DATE (a header may carry a suffix such as
    # " — SUPERSEDED (…)" or " — SKIPPED") and only GRADED weeks can be missing-though-graded.
    _wk_date = lambda w: w["week"][:10]
    _graded_keys = {_wk_date(w) for w in pack["weeks"]
                    if any(p.get("Status") == "GRADED" for p in w["picks"])}
    pack["universe_archives"] = universe_archives(sorted({_wk_date(w) for w in pack["weeks"]}),
                                                  _graded_keys)
    graded = [w for w in pack["weeks"] if any(p.get("Status") == "GRADED" for p in w["picks"])]
    pack["derived"] = {
        "graded_weeks": len(graded),
        "graded_picks": sum(1 for w in graded for p in w["picks"] if p.get("Status") == "GRADED"),
        "pending_weeks": [w["week"] for w in pack["weeks"] if any(p.get("Status") == "PENDING" for p in w["picks"])],
        "l1_runs": pack["l1_log"].get("l1_runs", 0),
    }

    out = Path(args.out) if args.out else BOARD_DIR / args.session / "evidence-pack.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, indent=1, ensure_ascii=False), encoding="utf-8")
    d = pack["derived"]
    print("BOARD_PACK={}".format(out))
    print("graded_weeks={} graded_picks={} l1_runs={} pending_weeks={} weeks_logged={} prior_sessions={}".format(
        d["graded_weeks"], d["graded_picks"], d["l1_runs"], d["pending_weeks"],
        len(pack["weeks"]), len(pack["prior_board_sessions"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
