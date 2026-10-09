#!/usr/bin/env python3
"""uspicks_universe_snapshot.py — rule L4: per-week snapshot of the full eligible
universe's mechanical features (Board of Advisors, session 2026-08-17, proposal
BP-2026-08-17-1, APPROVED 5-0 — wired 2026-08-17 as Phase 6.0 Part A2 of
commands/us-picks.md).

WHAT IT DOES (and nothing else): after the L1 full-universe append (top-50 before 2026-08-31), copy the run's own
full-universe scan output — every `eligible == true` row of
~/.claude/stocks/price-analyzer-output.json, VERBATIM and complete (the Board's
condition 6: never trim to "just the mechanical features"; the irreplaceable
content is the point-in-time non-price layer — float_shares, short_pct, mkt_cap,
sector, sp500/ndx membership, the after-hours close, and the run's own `eligible`
verdict, all overwritten every Sunday otherwise) — into an immutable per-week
JSONL under ~/.claude/stocks/_universe/, plus the run's mechanical component
scores (mech-scores.json) when present and fresh. It changes NO score, filter,
threshold, pick, grade, PDF, card or tracker row. It is a LOGGING rule.

BOARD CONDITIONS ENCODED (charter §8 — the ruling's numbered conditions):
  1  PROVENANCE + STALENESS ABORT: the scan file's mtime must be at/after this
     run's start (--run-start, printed by Phase 0.3 as RUN_START_UTC). Older ->
     write NOTHING, print a one-line warning, exit 0. A snapshot labelled with the
     wrong week is worse than no snapshot; the N<500 check cannot detect it.
     Every row carries week_start / matrix / src_mtime / entry_ref_day.
  2  CAPTURE THE COMPONENT SCORES: mech-scores.json rows are ALSO snapshotted
     when the file is present and fresh (universe-mech-<WEEK>.jsonl); a missing
     or stale mech file is a warning, never an abort (it has no documented
     producer in the command — price-analyzer-output.json is the primary source).
  3  MECHANICALLY NON-BLOCKING: the whole run is wrapped; the process ALWAYS
     exits 0 — no exception, disk-full or malformed row may abort Phase 6.x/7.
  5  MACHINE-READABLE RUN INDEX: one meta line per run appended to
     _universe/_index.jsonl {week_start, path, rows, bytes, secs, src_mtime, ok,
     mech_path, mech_rows, scan_complete, universe_rows, matrix, run_start,
     entry_ref_day, backfill, note} — the auto-review reads THIS, not transcripts.
  6  PAYLOAD VERBATIM-COMPLETE (see above).
  7  RUN-TIME VICE-BLACKLIST STATE: each row gets `vice_blacklisted` (bool) from
     a deterministic ticker lookup in sharia-blacklist.md AT RUN TIME (the list
     mutates; retro-applying a future list would misdescribe the run's universe).
  8  COMPLETENESS FLAG IN-FILE: a header line (row 0, "_meta": true) carries
     scan_complete + the pre-filter universe row count + provenance; a resumed /
     truncated scan (journal or meta file still present) is flagged, not hidden.
  9  COLLISION NAMING: never overwrite — universe-features-<WEEK>.jsonl, then
     -r2, -r3, ... until a free name is found. The auto-review counts DISTINCT
     week_start values with >=1 valid file, not filenames.
  13 DISK CEILING: warn when _universe/ exceeds ~250 MB in total.
  Scope honesty (12): the snapshot holds mechanical features + component scores
  + top_gainer_fit_score ONLY — not the total conviction score, not the judgment
  components (Catalyst / Options / Big Money live in the L1 log — full-universe from 2026-08-31, ~top-50 before).

Usage (Phase 6.0 Part A2, every pick run incl. skip weeks — AFTER the L1 append):
  python3 ~/.claude/scripts/uspicks_universe_snapshot.py \
      --week-start 2026-08-24 --matrix v5.7 --entry-ref-day 2026-08-21 \
      --run-start 2026-08-23T18:02:11Z
  Prints exactly one `L4: ...` status line (inline at Phase 6.0 — never after the
  Phase 7 SAVED: line). --backfill marks a deliberate operator backfill of an
  older scan (still requires --run-start; recorded in the header + index).
Stdlib only. Local-only output (stocks/ is repo-ignored). Always exits 0.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.home() / ".claude"
SCAN = ROOT / "stocks" / "price-analyzer-output.json"
MECH = ROOT / "stocks" / "mech-scores.json"
JOURNAL = ROOT / "stocks" / "price-analyzer-scan.jsonl"
JOURNAL_META = ROOT / "stocks" / "price-analyzer-scan-meta.json"
BLACKLIST = ROOT / "skills" / "us-stocks-memory" / "references" / "sharia-blacklist.md"
OUT_DIR = ROOT / "stocks" / "_universe"
INDEX = OUT_DIR / "_index.jsonl"
MIN_ROWS = 500
DISK_CEILING_MB = 250


def utc_iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    d = datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp()


def blacklist_tickers():
    tks = set()
    try:
        for line in BLACKLIST.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Z][A-Z0-9-]*)\b", line)
            if m:
                tks.add(m.group(1))
    except OSError:
        pass
    return tks


def free_path(base):
    """universe-features-<WEEK>.jsonl, then -r2, -r3, ... — never overwrite."""
    if not base.exists():
        return base
    n = 2
    while True:
        cand = base.with_name(base.stem + "-r{}".format(n) + base.suffix)
        if not cand.exists():
            return cand
        n += 1


def dir_size_mb(p):
    tot = 0
    for f in p.rglob("*"):
        try:
            tot += f.stat().st_size
        except OSError:
            pass
    return tot / (1024 * 1024)


def append_index(rec):
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with INDEX.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def snapshot(args):
    t0 = time.time()
    rec = {"week_start": args.week_start, "matrix": args.matrix, "run_start": args.run_start,
           "entry_ref_day": args.entry_ref_day, "backfill": bool(args.backfill),
           "path": None, "rows": 0, "bytes": 0, "secs": 0.0, "src_mtime": None, "ok": False,
           "mech_path": None, "mech_rows": 0, "scan_complete": None, "universe_rows": 0, "note": ""}
    run_start_ts = parse_iso(args.run_start)

    if not SCAN.is_file():
        rec["note"] = "scan file missing"
        append_index(rec)
        print("L4: ⚠️ no snapshot — {} not found (nothing written)".format(SCAN))
        return
    src_mtime = SCAN.stat().st_mtime
    rec["src_mtime"] = utc_iso(src_mtime)
    # Condition 1 — provenance / staleness abort.
    if src_mtime < run_start_ts and not args.backfill:
        rec["note"] = "STALE: scan mtime {} predates run start {} — nothing written".format(rec["src_mtime"], args.run_start)
        append_index(rec)
        print("L4: ⚠️ no snapshot — price-analyzer-output.json mtime {} predates this run's start {} "
              "(stale scan; nothing written — a mislabelled snapshot is worse than none)".format(rec["src_mtime"], args.run_start))
        return

    data = json.loads(SCAN.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else (data.get("rows") or data.get("tickers") or [])
    universe_rows = len(rows)
    eligible = [r for r in rows if isinstance(r, dict) and r.get("eligible") is True]
    # Condition 8 — completeness: a resumed/truncated scan leaves its journal behind.
    scan_complete = not (JOURNAL.exists() or JOURNAL_META.exists())
    rec["scan_complete"] = scan_complete
    rec["universe_rows"] = universe_rows
    if not eligible:
        rec["note"] = "0 eligible rows in scan output — nothing written"
        append_index(rec)
        print("L4: ⚠️ no snapshot — 0 eligible rows in price-analyzer-output.json (nothing written)")
        return

    vice = blacklist_tickers()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = free_path(OUT_DIR / "universe-features-{}.jsonl".format(args.week_start))
    header = {"_meta": True, "rule": "L4", "week_start": args.week_start, "matrix": args.matrix,
              "entry_ref_day": args.entry_ref_day, "run_start": args.run_start, "src": str(SCAN),
              "src_mtime": rec["src_mtime"], "scan_complete": scan_complete,
              "universe_rows": universe_rows, "eligible_rows": len(eligible),
              "vice_blacklist_tickers": len(vice), "backfill": bool(args.backfill),
              "scope": "mechanical features + top_gainer_fit_score + eligible verdict; NOT the total conviction score, NOT Catalyst/Options/Big Money (finalists-only, see L1)",
              "written_at": utc_iso(time.time())}
    with out.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(header, ensure_ascii=False) + "\n")
        for r in eligible:
            row = dict(r)  # verbatim + the stamps
            row["week_start"] = args.week_start
            row["matrix"] = args.matrix
            row["src_mtime"] = rec["src_mtime"]
            row["entry_ref_day"] = args.entry_ref_day
            row["vice_blacklisted"] = (str(r.get("ticker", "")).upper() in vice)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    # re-read + count (data rows exclude the header)
    n = sum(1 for _ in out.open(encoding="utf-8")) - 1
    rec.update({"path": str(out), "rows": n, "bytes": out.stat().st_size})

    # Condition 2 — mechanical component scores, when present and fresh.
    mech_note = ""
    if MECH.is_file():
        m_mtime = MECH.stat().st_mtime
        if m_mtime >= run_start_ts or args.backfill:
            try:
                mrows = json.loads(MECH.read_text(encoding="utf-8"))
                if isinstance(mrows, list) and mrows:
                    mout = free_path(OUT_DIR / "universe-mech-{}.jsonl".format(args.week_start))
                    with mout.open("w", encoding="utf-8") as fh:
                        fh.write(json.dumps({"_meta": True, "rule": "L4", "week_start": args.week_start,
                                             "matrix": args.matrix, "src": str(MECH),
                                             "src_mtime": utc_iso(m_mtime), "rows": len(mrows),
                                             "backfill": bool(args.backfill)}, ensure_ascii=False) + "\n")
                        for r in mrows:
                            row = dict(r)
                            row["week_start"] = args.week_start
                            row["matrix"] = args.matrix
                            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                    rec["mech_path"] = str(mout)
                    rec["mech_rows"] = len(mrows)
                else:
                    mech_note = "mech-scores.json empty/unexpected shape"
            except (OSError, ValueError) as e:
                mech_note = "mech-scores.json unreadable: {}".format(e)
        else:
            mech_note = "mech-scores.json stale (mtime {} < run start) — not captured".format(utc_iso(m_mtime))
    else:
        mech_note = "mech-scores.json absent — component scores not captured this run"

    rec["secs"] = round(time.time() - t0, 3)
    rec["ok"] = (n >= MIN_ROWS)
    rec["note"] = ("; ".join(x for x in [mech_note, "" if scan_complete else "scan journal present — resumed/partial scan flagged"] if x)) or "ok"
    append_index(rec)

    warn = ""
    if n < MIN_ROWS:
        warn += " ⚠️ rows<{}".format(MIN_ROWS)
    if not scan_complete:
        warn += " ⚠️ scan_complete=false"
    if mech_note:
        warn += " ⚠️ " + mech_note
    size_mb = dir_size_mb(OUT_DIR)
    if size_mb > DISK_CEILING_MB:
        warn += " ⚠️ _universe/ is {:.0f} MB (> {} MB ceiling)".format(size_mb, DISK_CEILING_MB)
    print("L4: snapshot {} rows={} bytes={} secs={} mech={} src_mtime={}{}".format(
        out, n, rec["bytes"], rec["secs"], rec["mech_rows"] or "none", rec["src_mtime"], warn))


def main():
    ap = argparse.ArgumentParser(description="/us-picks L4 universe snapshot (Phase 6.0 Part A2)")
    ap.add_argument("--week-start", required=True, help="Phase 0.3 WEEK_START (YYYY-MM-DD)")
    ap.add_argument("--matrix", required=True, help="live scoring-matrix label, e.g. v5.7")
    ap.add_argument("--entry-ref-day", required=True, help="Phase 0.3 ENTRY_REF_DAY (the scan's PRICE_REF_DATE)")
    ap.add_argument("--run-start", required=True, help="Phase 0.3 RUN_START_UTC (ISO 8601) — provenance guard")
    ap.add_argument("--backfill", action="store_true", help="operator backfill of an older scan (recorded as such)")
    args = ap.parse_args()
    try:
        snapshot(args)
    except Exception as e:  # condition 3 — never blocks the run
        try:
            append_index({"week_start": args.week_start, "ok": False, "note": "EXCEPTION: {}".format(e),
                          "run_start": args.run_start, "matrix": args.matrix, "backfill": bool(args.backfill)})
        except Exception:
            pass
        print("L4: ⚠️ snapshot step failed non-fatally ({}: {}) — run continues".format(type(e).__name__, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
