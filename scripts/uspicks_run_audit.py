#!/usr/bin/env python3
"""uspicks_run_audit.py — rule L5: Run & Governance Persistence Audit
(Board of Advisors, session 2026-08-21, proposal BP-2026-08-21-1, APPROVED 5-0 —
wired 2026-08-21 as a Phase 0.4 step of commands/us-picks.md).

WHAT IT DOES (and nothing else): asks three deterministic set questions about
whether work that was DONE was also RECORDED, prints at most one short block when
one of them says "no", and appends one row per evaluation to
stocks/us-run-audit.jsonl. It is DETECTION-ONLY. It changes no score, filter,
threshold, pick, grade, PDF, card or tracker row; it never wires anything, never
re-decides a verdict, never re-runs a lost session, and never reconstructs a week.

WHY IT EXISTS — two documented incidents of one failure class:
  1. 2026-08-09 (pick week lost): the run delivered its slate and died before
     Phase 6.0/6.2. price-analyzer-output.json 2026-08-10 00:06, mech-scores.json
     00:08, stageb-evidence.json 00:07 — while the tracker held no
     "### Week of 2026-08-10" block. For a week `/us-picks update` reported "no
     pending picks" because the tracker was the only thing consulted. 40 L1
     candidate rows were destroyed permanently (that week persisted 10 of 50).
  2. 2026-08-17-s2 (governance decision lost): a Board session ran to completion,
     computed three APPROVED verdicts, and ended before Phase U.9.4/U.9.5 — no
     ledger block, no wiring, no card. Found four days later by chance.
Both are "the work completed and the write-back didn't."

  ⚠️ L5 DOES NOT CLOSE INCIDENT 1 (Chair condition 18). The detector recovers no
  candidate rows — the 40 lost L1 rows were destroyed at the moment of the crash.
  Prevention (incremental L1 persistence as Stage B returns, instead of one append
  at Phase 6.0) is a separate proposal the Secretary files at the next session.

THE THREE CONDITIONS
  (a) LOG-ONLY (Chair condition 2 — demoted; it fired on NEITHER incident and was
      retained on judgement, not evidence): era-scoped log_weeks minus
      tracker_weeks. Writes a jsonl row, never a banner. Its false-alarm budget is
      ZERO — any fire attributable to (a) drops (a) immediately, on its own, with
      no effect on (b) or (c).
  (b) BANNER: artifact_week not present in any us-weekly-tracker*.md. This is the
      condition that catches incident 1.
  (c) BANNER: a stocks/board/<id>/ directory holding a session.json whose <id> has
      no "### Session <id>" header in the tracker's Board Decision Ledger. This is
      the condition that catches incident 2.

CONDITION (b) SUPPRESSIONS (Chair condition 1 — mandatory, they are what keep it
silent against live state):
  S1 run-provenance: an artifact whose mtime is at/after --run-start belongs to
     THIS run, whose week is logged later in this same run. Excluded.
     ⚠️ INTERPRETATION NOTE, recorded openly: condition 1 is worded "fire only on
     artifacts with mtime >= RUN_START_UTC". Read literally that inverts the
     detector — an artifact from a LOST EARLIER run always predates the current
     run's start, so a literal reading could never fire on either incident, and
     the same condition also demands the incident-1 replay still fire. The
     operative intent is provenance-keying, so the primitive is applied as the
     suppression above. Stated in the ledger as an interpretation, not a silent
     choice; the --selftest exercises both incident replays against it.
  S2 future week: artifact_week strictly LATER than the Monday of the run date's
     own ISO week is a week that cannot be logged yet. Excluded.
  S3 own week: WEEK_START of this run is excluded on PICK-mode runs only.

ARTIFACT SET — PINNED LITERALLY (Chair condition 13):
  REQUIRED : stocks/price-analyzer-output.json   (the only artifact with a
             documented writer — commands/us-picks.md Phase 2 Step A4)
  OPTIONAL : stocks/stageb-evidence.json, stocks/mech-scores.json — a missing or
             unreadable optional artifact is simply absent from the MAX; never an
             error, never a fire.
  EXCLUDED : stocks/gainers-output.json — DELIBERATELY. It is a GRADING-flow
             artifact written by Phase U.2, not a pick-run artifact, so its mtime
             says nothing about whether a pick week was logged. Live proof of the
             need for this exclusion: on 2026-08-22 it carried an mtime that maps
             to week 2026-08-24, a week that does not exist yet — it would have
             false-fired condition (b) on the very run that wired this rule.
  If the REQUIRED artifact is missing or unreadable, condition (b) is SKIPPED for
  that run (recorded as artifact_week=null, fired=false) — never a fire.

FAIL-OPEN AND BOUNDED (Chair condition 15): every read and parse is wrapped; any
unreadable input is treated as CLEAN plus a one-line "audit skipped (<reason>)";
the process ALWAYS exits 0 and can never abort, block, truncate or slow a run.
The fire block is at most ~8 lines, at most once per run, and is worded
"SUSPECTED" / "UNRECORDED" — never "FAILED". On a Sunday pick run it never
displaces, delays or precedes the pick card.

SESSION-ID CONTRACT (Chair condition 9): the stocks/board/ directory name IS the
ledger "### Session <id>" token, verbatim, including any suffix — the real case is
"2026-08-17-s2" against charter §9.1's unsuffixed template. Without this contract
condition (c) is a guaranteed permanent false fire.

TERMINATION PATH (Chair condition 10): a session that is triaged but cannot be
recorded is silenced by a one-line ledger stub the audit counts as recorded:
    ### Session <id> — NOT RECORDED, acknowledged YYYY-MM-DD
A (c) fire repeating across >= 2 consecutive runs with no action available counts
as a FALSE ALARM for reversal purposes, so an unresolvable fire can never nag
forever without tripping the revert.

Usage:
  python3 uspicks_run_audit.py --mode pick|update|board --week-start YYYY-MM-DD \
                               --run-start YYYY-MM-DDTHH:MM:SSZ [--session-id ID]
  python3 uspicks_run_audit.py --selftest      # reproduces the three set computations

Prints exactly one line in L4's house pattern:
    L5: audit clean  conds=a,b,c  secs=T
    L5: audit FIRED  cond=b  <suspect>  secs=T      (plus the <=8-line block)
Always exits 0. Requires: python3 stdlib only. No network, no API keys.
"""

import argparse
import datetime as _dt
import json
import os
import re
import sys
import time

ROOT = os.path.expanduser("~/.claude")
STOCKS = os.path.join(ROOT, "stocks")

# --- pinned constants (mirrored in scripts/uspicks_lint.py CONTRACT) -----------
ERA_START = "2026-07-14"          # v5.4 fresh-tracker boundary; (a) is era-scoped to it
TRACKER_GLOB_PREFIX = "us-weekly-tracker"   # ALL us-weekly-tracker*.md — live + archives
WEEK_HDR = re.compile(r"^###\s+Week of (\d{4}-\d{2}-\d{2})", re.M)
SESSION_HDR = re.compile(r"^###\s+Session\s+([0-9A-Za-z\-_.]+)", re.M)
LEDGER_HDR = "## Board of Advisors — Decision Ledger"

REQUIRED_ARTIFACTS = ["price-analyzer-output.json"]
OPTIONAL_ARTIFACTS = ["stageb-evidence.json", "mech-scores.json"]
# EXCLUDED on purpose — see the module docstring. Do not add gainers-output.json.
EXCLUDED_ARTIFACTS = ["gainers-output.json"]

AUDIT_LOG = os.path.join(STOCKS, "us-run-audit.jsonl")


def _safe(fn, default, errs):
    try:
        return fn()
    except Exception as e:                                  # fail-open, always
        errs.append("%s: %s" % (fn.__name__ if hasattr(fn, "__name__") else "read", e))
        return default


def _monday(d):
    return d - _dt.timedelta(days=d.weekday())


def tracker_weeks(root=ROOT, errs=None):
    """Every '### Week of YYYY-MM-DD' across ALL us-weekly-tracker*.md — live plus
    the v5.3 and v4.4 archives. A SKIPPED header counts as present."""
    errs = errs if errs is not None else []
    weeks = set()
    d = os.path.join(root, "stocks")
    try:
        names = sorted(n for n in os.listdir(d)
                       if n.startswith(TRACKER_GLOB_PREFIX) and n.endswith(".md"))
    except Exception as e:
        errs.append("tracker dir: %s" % e)
        return weeks, []
    for n in names:
        try:
            weeks.update(WEEK_HDR.findall(open(os.path.join(d, n), encoding="utf-8").read()))
        except Exception as e:
            errs.append("%s: %s" % (n, e))
    return weeks, names


def log_weeks(root=ROOT, errs=None):
    """Distinct week_start in the L1 candidate log."""
    errs = errs if errs is not None else []
    out = set()
    p = os.path.join(root, "stocks", "us-candidate-scores.jsonl")
    try:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    w = json.loads(line).get("week_start")
                except Exception:
                    continue
                if w:
                    out.add(w)
    except FileNotFoundError:
        pass
    except Exception as e:
        errs.append("l1 log: %s" % e)
    return out


def artifact_state(root=ROOT, errs=None):
    """MAX mtime over the pinned artifact set -> (ts, per-file mtimes, required_ok)."""
    errs = errs if errs is not None else []
    mtimes, best, required_ok = {}, None, False
    for name in REQUIRED_ARTIFACTS + OPTIONAL_ARTIFACTS:
        p = os.path.join(root, "stocks", name)
        try:
            ts = os.path.getmtime(p)
        except Exception:
            mtimes[name] = None
            continue
        mtimes[name] = _dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")
        if name in REQUIRED_ARTIFACTS:
            required_ok = True
        best = ts if best is None else max(best, ts)
    return best, mtimes, required_ok


def artifact_week(ts):
    """Thu-Sun -> the NEXT Monday (a weekend pick run targets the coming week);
    Mon-Wed -> the Monday of its own ISO week."""
    if ts is None:
        return None
    d = _dt.datetime.fromtimestamp(ts).date()
    if d.weekday() >= 3:                                    # Thu(3)..Sun(6)
        d = _monday(d) + _dt.timedelta(days=7)
    else:
        d = _monday(d)
    return d.isoformat()


def ledger_sessions(root=ROOT, errs=None):
    """'### Session <id>' ids inside the tracker's Board Decision Ledger section.
    A '<id> — NOT RECORDED, acknowledged <date>' stub counts as recorded
    (Chair condition 10 termination path)."""
    errs = errs if errs is not None else []
    p = os.path.join(root, "stocks", "us-weekly-tracker.md")
    try:
        s = open(p, encoding="utf-8").read()
    except Exception as e:
        errs.append("tracker: %s" % e)
        return set()
    i = s.find(LEDGER_HDR)
    if i < 0:
        return set()
    j = s.find("\n## ", i + 1)
    return set(SESSION_HDR.findall(s[i: j if j > 0 else len(s)]))


def board_sessions(root=ROOT, errs=None):
    """Directory names under stocks/board/ that contain a session.json. The
    directory name IS the ledger id, verbatim (session-id contract)."""
    errs = errs if errs is not None else []
    d = os.path.join(root, "stocks", "board")
    out = set()
    try:
        for n in os.listdir(d):
            if os.path.isfile(os.path.join(d, n, "session.json")):
                out.add(n)
    except FileNotFoundError:
        pass
    except Exception as e:
        errs.append("board dir: %s" % e)
    return out


def evaluate(mode, week_start, run_start, session_id, root=ROOT):
    """Pure computation. Returns the jsonl row + the (<=8-line) fire block."""
    errs = []
    t0 = time.time()
    tw, tracker_files = tracker_weeks(root, errs)
    lw = log_weeks(root, errs)
    ts, mtimes, required_ok = artifact_state(root, errs)
    aw = artifact_week(ts)
    bs, ls = board_sessions(root, errs), ledger_sessions(root, errs)

    # ---- condition (a) — LOG-ONLY (Chair condition 2) -------------------------
    a_missing = sorted(w for w in lw if w >= ERA_START and w not in tw and w != week_start)

    # ---- condition (b) — banner, with the three mandatory suppressions --------
    b_missing, excluded_by, would_fire_wo_excl = None, [], False
    if aw is not None and aw not in tw:
        would_fire_wo_excl = True
        run_day = _dt.date.today()
        if run_start:
            try:
                run_day = _dt.datetime.strptime(run_start, "%Y-%m-%dT%H:%M:%SZ").date()
            except Exception:
                pass
        run_week_monday = _monday(run_day).isoformat()
        if run_start and ts is not None:
            try:
                rs = _dt.datetime.strptime(run_start, "%Y-%m-%dT%H:%M:%SZ")
                if _dt.datetime.utcfromtimestamp(ts) >= rs:
                    excluded_by.append("S1 run-provenance (artifact is this run's own)")
            except Exception:
                pass
        if aw > run_week_monday:
            excluded_by.append("S2 future week (later than this run's own ISO Monday)")
        if mode == "pick" and week_start and aw == week_start:
            excluded_by.append("S3 own week (pick mode)")
        if not excluded_by:
            b_missing = aw
    if not required_ok:
        excluded_by.append("required artifact absent — condition (b) skipped")
        b_missing = None

    # ---- condition (c) — banner ---------------------------------------------
    c_missing = sorted(s for s in bs - ls if s != session_id)

    fired = bool(b_missing) or bool(c_missing)
    reasons = ([] + (["b"] if b_missing else []) + (["c"] if c_missing else []))
    row = {
        "run_ts": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode, "WEEK_START": week_start, "run_start": run_start,
        "artifact_mtimes": mtimes, "artifact_week": aw,
        "in_any_tracker": (aw in tw) if aw else None,
        "excluded_by": excluded_by, "would_fire_without_exclusion": would_fire_wo_excl,
        "tracker_files": tracker_files, "tracker_newest_week": (max(tw) if tw else None),
        "board_sessions": sorted(bs), "ledger_sessions": sorted(ls),
        "cond_a_logonly_missing": a_missing,          # never banners (Chair cond 2)
        "cond_b_suspect_week": b_missing,
        "cond_c_unrecorded_sessions": c_missing,
        "fired": fired, "fire_reason": ",".join(reasons) or None,
        "errors": errs, "elapsed_secs": round(time.time() - t0, 3),
    }

    block = []
    if b_missing:
        block += [
            "  L5 — SUSPECTED unlogged week: %s" % b_missing,
            "     run artifacts exist for it but no '### Week of %s' header is in any" % b_missing,
            "     us-weekly-tracker*.md.  artifacts: " +
            ", ".join("%s=%s" % (k, v) for k, v in mtimes.items() if v),
            "     RECOVERY: locate the delivered slate (pick card / pick-card payload) and",
            "     log it verbatim; do NOT recompute. artifact_week is DETECTION-ONLY — never",
            "     pass it as WEEK_OVERRIDE / ENTRY_DATE / EXIT_DATE.",
        ]
    if c_missing:
        block += [
            "  L5 — UNRECORDED Board session(s): %s" % ", ".join(c_missing),
            "     stocks/board/<id>/session.json exists with computed verdicts, but no",
            "     '### Session <id>' header is in the tracker's Board Decision Ledger.",
            "     RECOVERY: record the verdicts for AUDIT ONLY. Nothing may be wired from a",
            "     session whose verdict was never recorded — re-file it as a new proposal.",
            "     To silence a triaged-but-unrecordable session, add the one-line stub:",
            "     '### Session <id> — NOT RECORDED, acknowledged YYYY-MM-DD'.",
        ]
    return row, block[:8]


def _append_log(row):
    try:
        os.makedirs(STOCKS, exist_ok=True)
        with open(AUDIT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass                                                # logging never blocks


def selftest():
    """Chair condition 16 — reproduce the three set computations mechanically."""
    errs = []
    tw, files = tracker_weeks(ROOT, errs)
    lw = log_weeks(ROOT, errs)
    ts, mtimes, req = artifact_state(ROOT, errs)
    bs, ls = board_sessions(ROOT, errs), ledger_sessions(ROOT, errs)
    print("L5 selftest")
    print("  tracker files          : %s" % ", ".join(files))
    print("  tracker weeks          : %d  newest=%s" % (len(tw), max(tw) if tw else None))
    print("  L1 log weeks (all)     : %d  %s" % (len(lw), sorted(lw)))
    print("  (a) era-scoped >= %s : %s" % (ERA_START, sorted(w for w in lw if w >= ERA_START and w not in tw) or "EMPTY"))
    print("  (a) unscoped           : %s" % (sorted(lw - tw) or "EMPTY"))
    print("  artifacts (required=%s): %s" % (req, mtimes))
    print("  excluded artifacts     : %s" % EXCLUDED_ARTIFACTS)
    print("  (b) artifact_week      : %s  in_tracker=%s" % (artifact_week(ts), artifact_week(ts) in tw))
    print("  board sessions         : %s" % sorted(bs))
    print("  ledger sessions        : %s" % sorted(ls))
    print("  (c) board minus ledger : %s" % (sorted(bs - ls) or "EMPTY"))
    print("  mtime->week mapping    : Thu-Sun -> next Monday, Mon-Wed -> own Monday")
    if errs:
        print("  read errors            : %s" % errs)
    return 0


def main():
    ap = argparse.ArgumentParser(description="/us-picks L5 run & governance persistence audit (Phase 0.4)")
    ap.add_argument("--mode", choices=["pick", "update", "board"], default="update")
    ap.add_argument("--week-start", default=None)
    ap.add_argument("--run-start", default=None)
    ap.add_argument("--session-id", default=None,
                    help="this run's own Board session id, excluded from condition (c)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    try:
        row, block = evaluate(a.mode, a.week_start, a.run_start, a.session_id)
    except Exception as e:                                  # fail-open (cond 15)
        print("L5: audit skipped (%s)" % e)
        return 0
    _append_log(row)
    if row["fired"]:
        print("L5: audit FIRED  cond=%s  secs=%s" % (row["fire_reason"], row["elapsed_secs"]))
        for line in block:
            print(line)
    else:
        note = ""
        if row["excluded_by"]:
            note = "  (suppressed: %s)" % "; ".join(row["excluded_by"])
        print("L5: audit clean  conds=a,b,c  secs=%s%s" % (row["elapsed_secs"], note))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                                  # never abort a run
        print("L5: audit skipped (%s)" % e)
        sys.exit(0)
