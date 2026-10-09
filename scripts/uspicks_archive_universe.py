#!/usr/bin/env python3
"""
uspicks_archive_universe.py — Phase U.2b per-week ranked-universe archive.

Board-wired 2026-08-28 (session 2026-08-28, BP-2026-08-28-2, APPROVED 5-0;
also discharges BP-2026-08-28-1's auto-review input per the Chair's E8
resolution: "a change that moves real money may not carry an auto-review that
depends on someone remembering to copy a file").

WHAT IT DOES
    Copies the grading run's own `stocks/gainers-output.json` to a week-keyed
    archive `stocks/gainers-<WEEK_START>.json`, stamps provenance into the
    file (`_archive_meta`) and into `stocks/_universe_archives/_index.jsonl`.

WHY IT EXISTS (the E1 incident, verified in code by three directors)
    `uspicks_gainers_scan.py` hardcodes ONE output path, and every grading run
    overwrites it. All six pre-wiring archives on disk were made by hand.

    The "it regenerates in ~30 s" counter-argument is FALSE.
    `uspicks_price_scan.build_universe()` fetches the LIVE nasdaqtrader symbol
    directory, so a regeneration ranks against TODAY's listed set. Measured
    2026-08-28: the week of 2026-08-17 was graded on 5,016 names (picks #4775 /
    #4515 / #4018 / #3266 / #4334); regenerated the same day it returned 4,997
    names with IDENTICAL returns but picks at #4757 / #4500 / #4007 / #3259 /
    #4321 — 7-18 rank places off. Past yardsticks are not reconstructible.

BINDING CONDITIONS ENCODED (Chair, BP-2026-08-28-2)
    c3  provenance on every archive: archived_at, source, universe_size,
        price_source, universe_completeness_pct, entry_date, exit_date,
        measurement_basis — in-file AND in _index.jsonl.
    c4  never-overwrite predicate WIDENED to entry_date + exit_date +
        measurement_basis + universe_size + price_source. Any mismatch routes
        to a -rescan- sibling and never touches the original. EXCEPTION: a
        live_scan archive MAY replace a 'regenerated' one (the reconstruction
        moves to a -regen- name).
    c5  rescan/regen filename stamp is colon-free: YYYYMMDDTHHMMSSZ.
    c6  WEEK KEY IS <WEEK_START> (the Monday), never <ENTRY_DATE> — otherwise
        the Labor Day week (WEEK_START 2026-09-07, FIRST_TRADING_DAY
        2026-09-08) reports a false missing archive inside the review horizon.
    c7  ONE MECHANISM ONLY: this copy. `uspicks_gainers_scan.py` is NOT
        modified and gains no --out flag, so the data-layer operational
        contract does not fire and `us-top-gainers-analyzer.md` is untouched.
    c8  ACTOR is the ORCHESTRATOR, after the subagent returns its summary.
    c9  NO archive when the U.2 health guard FAILED; the week is recorded in
        _postponed.jsonl instead (the persisted, machine-readable list the
        auto-review reads). A U.3/U.4 per-pick GRADE_PENDING_DATA on an
        otherwise clean U.2 universe KEEPS its archive and is NOT a reversal.
    c11 CANONICAL MEANING: gainers-<WEEK_START>.json is the record of the
        ranked universe THE GRADE WAS COMPUTED FROM — not the most accurate
        scan of that week.
    c14 fail-open, one inline line, no pick-card advisory notice.

    Always exits 0. Never blocks, aborts or delays a grading run.

USAGE
    python3 uspicks_archive_universe.py --week-start 2026-08-24 \
        --run-start 2026-08-28T22:28:02Z --source live_scan
    python3 uspicks_archive_universe.py --week-start 2026-09-07 --postponed \
        --reason "universe_size 2900 < 3000"
    python3 uspicks_archive_universe.py --backfill        # stamp hand-made files
    python3 uspicks_archive_universe.py --selftest
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("USPICKS_ROOT", Path.home() / ".claude"))
STOCKS = ROOT / "stocks"
SCAN_OUT = STOCKS / "gainers-output.json"
ARCH_DIR = STOCKS / "_universe_archives"
INDEX = ARCH_DIR / "_index.jsonl"
POSTPONED = ARCH_DIR / "_postponed.jsonl"

# U.2 health guard (mirrors commands/us-picks.md Phase U.2 exactly).
# 2026-09-04 data-integrity fix: MIN_UNIVERSE was left at the v5.2 full-market
# threshold (4500) when v6.1 (2026-08-29) re-armed the $1M/day liquid basis
# (~3,650-3,900 names) and moved the command's guard to 3000 — so this guard
# refused the first healthy v6.3 scan (n=3596) and wrongly logged the week as
# postponed. Re-based to 3000 here; and the guard now also requires the liquidity
# floor to have actually applied (`liq_floor_applied`, emitted by the scan since
# the same date) whenever a floor is configured, because a floor-less scan is the
# retired full-market basis, not the liquid one the v6.3 grade is defined on.
MIN_UNIVERSE = 3000
HEALTHY_BASIS = "open_to_close"


LIQUID_1M_FLOOR = 1000000.0   # the v6.1/v6.3 liquid basis (GAINERS_LIQ_FLOOR default)


def derive_universe_basis(d):
    """BP-2026-09-04-2 (Board-wired 2026-09-04, APPROVED 5-0) — the DERIVED liquidity-basis
    label of a ranked-universe archive. A PARTITION KEY ONLY: never an input to any rank,
    cutoff, grade, WIN tier, score or Summary Statistics row (Chair C5).

    READ SITE (Chair C2): computed from the archive file's TOP-LEVEL keys
    (`d['liq_floor']`, `d['liq_floor_applied']`) — never from `_archive_meta`, never from
    `_index.jsonl`; legacy classification is by absence AT THAT LEVEL. The reader
    (uspicks_board_pack.py) RECOMPUTES it on every call and never trusts a stored label;
    a stored label that disagrees is reported as `basis_label_conflict` (Chair C4).

    TOTAL predicate (Chair C3 — never over-claim `liquid_1m`):
      unknown_legacy    both keys absent (the six pre-2026-09-04 archives, ~4,979-5,016 names)
      full_market       liq_floor_applied is False (GAINERS_LIQ_FLOOR=0, or the floor lapsed)
      liquid_1m         applied True AND liq_floor >= 1,000,000 (the v6.1/v6.3 basis)
      other_floor:<v>   applied True AND 0 < liq_floor < 1,000,000 (a lawfully changed floor)
      liquid_unverified applied True with liq_floor absent / non-positive / unparseable
    `source` (hand_made / regenerated / live_scan) is NOT a basis signal and must never be
    used as a proxy (Chair C10).
    """
    if not isinstance(d, dict):
        return "liquid_unverified"
    has_floor, has_applied = ("liq_floor" in d), ("liq_floor_applied" in d)
    if not has_floor and not has_applied:
        return "unknown_legacy"
    applied = d.get("liq_floor_applied")
    if applied is False:
        return "full_market"
    if applied is not True:
        return "liquid_unverified"
    try:
        floor = float(d.get("liq_floor") or 0)
    except (TypeError, ValueError):
        floor = 0.0
    if floor <= 0:
        return "liquid_unverified"
    if floor >= LIQUID_1M_FLOOR:
        return "liquid_1m"
    return "other_floor:%g" % floor


def _liq_floor_ok(d):
    """True unless a liquidity floor is configured and the scan reports it did NOT apply."""
    try:
        floor = float(d.get("liq_floor") or 0)
    except Exception:
        floor = 0.0
    if floor <= 0:
        return True
    return d.get("liq_floor_applied") is True

# Identity predicate — c4. entry/exit/basis alone do NOT establish identity:
# the 2026-08-17 pair agrees on all three and disagrees on ranks.
IDENTITY_KEYS = ("entry_date", "exit_date", "measurement_basis",
                 "universe_size", "price_source")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp(run_start):
    """c5 — colon-free filename stamp (macOS/Finder + glob hazard)."""
    s = (run_start or _now()).replace("-", "").replace(":", "")
    return s if s.endswith("Z") else s + "Z"


def _read_json(p):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


def _append(path, row):
    try:
        ARCH_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _identity(d):
    return {k: d.get(k) for k in IDENTITY_KEYS}


def _meta_of(d, source, run_start, backfill=False):
    return {
        "archived_at": _now(),
        "source": source,                       # live_scan | regenerated | hand_made
        "universe_size": d.get("universe_size"),
        "price_source": d.get("price_source"),
        "universe_completeness_pct": d.get("universe_completeness_pct"),
        "entry_date": d.get("entry_date"),
        "exit_date": d.get("exit_date"),
        "measurement_basis": d.get("measurement_basis"),
        "liq_floor_applied": d.get("liq_floor_applied"),   # 2026-09-04 provenance
        "liq_source": d.get("liq_source"),
        "liq_floor": d.get("liq_floor"),                   # BP-2026-09-04-2 C1: the raw floor beside the flag
        "universe_basis": derive_universe_basis(d),        # BP-2026-09-04-2: DERIVED label, partition key only
        "run_start": run_start,
        "backfill": backfill,
    }


def archive(week_start, run_start, source):
    t0 = time.time()
    d = _read_json(SCAN_OUT)
    if d is None:
        print("U.2: ⚠️ archive skipped — gainers-output.json unreadable")
        return
    # c9 — the health guard. Never archive a scan the guard would postpone.
    ok = (d.get("status") == "DONE"
          and d.get("measurement_basis") == HEALTHY_BASIS
          and (d.get("universe_size") or 0) >= MIN_UNIVERSE
          and _liq_floor_ok(d))
    if not ok:
        print("U.2: ⚠️ archive skipped — U.2 health guard failed "
              f"(status={d.get('status')} basis={d.get('measurement_basis')} "
              f"n={d.get('universe_size')} liq_floor_applied={d.get('liq_floor_applied')}); "
              "week recorded as postponed")
        _append(POSTPONED, {"week_start": week_start, "recorded_at": _now(),
                            "status": d.get("status"),
                            "measurement_basis": d.get("measurement_basis"),
                            "universe_size": d.get("universe_size"),
                            "liq_floor_applied": d.get("liq_floor_applied"),
                            "liq_floor": d.get("liq_floor"),
                            "universe_basis": derive_universe_basis(d),
                            "reason": "u2_health_guard_failed"})
        return

    ARCH_DIR.mkdir(parents=True, exist_ok=True)
    target = STOCKS / f"gainers-{week_start}.json"          # c6 — Monday key
    meta = _meta_of(d, source, run_start)
    note = "written"

    if target.exists():
        cur = _read_json(target) or {}
        cur_meta = cur.get("_archive_meta") or {}
        same = _identity(cur) == _identity(d)
        if same:
            print(f"U.2: archive already present and identical → {target.name} "
                  f"({d.get('universe_size')} rows)")
            _append(INDEX, {"week_start": week_start, "file": target.name,
                            "action": "noop_identical", **meta,
                            "secs": round(time.time() - t0, 3)})
            return
        # c4 exception — a live_scan MAY replace a 'regenerated' archive.
        if source == "live_scan" and cur_meta.get("source") == "regenerated":
            regen = STOCKS / f"gainers-{week_start}-regen-{_stamp(cur_meta.get('run_start'))}.json"
            try:
                shutil.move(str(target), str(regen))
                note = f"replaced regenerated archive (moved to {regen.name})"
                print(f"U.2: ⚠️ replacing a REGENERATED archive with the live scan; "
                      f"reconstruction preserved as {regen.name}")
            except Exception:
                print("U.2: ⚠️ could not move the regenerated archive — writing rescan sibling")
                target = STOCKS / f"gainers-{week_start}-rescan-{_stamp(run_start)}.json"
                note = "rescan sibling (regen move failed)"
        else:
            # c4 — mismatch never touches the original.
            target = STOCKS / f"gainers-{week_start}-rescan-{_stamp(run_start)}.json"
            note = "rescan sibling (identity mismatch)"
            print(f"U.2: ⚠️ existing archive for {week_start} differs "
                  f"(n {cur.get('universe_size')} vs {d.get('universe_size')}, "
                  f"src {cur.get('price_source')} vs {d.get('price_source')}) — "
                  f"original untouched, writing {target.name}")

    d["_archive_meta"] = meta
    try:
        tmp = target.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(d, f)
        os.replace(tmp, target)
    except Exception as e:
        print(f"U.2: ⚠️ archive write failed ({e}) — grading is unaffected")
        return

    secs = round(time.time() - t0, 3)
    _append(INDEX, {"week_start": week_start, "file": target.name,
                    "action": note, **meta, "secs": secs})
    print(f"U.2: archived ranked universe → {target.name} "
          f"({d.get('universe_size')} rows, {secs}s)")


def backfill():
    """c3 — stamp the six pre-wiring hand-made archives with provenance."""
    ARCH_DIR.mkdir(parents=True, exist_ok=True)
    known_regenerated = {"2026-08-17"}   # measured 4,997 vs the as-graded 5,016
    n = 0
    for p in sorted(STOCKS.glob("gainers-2*.json")):
        wk = p.stem.replace("gainers-", "")
        if "-rescan-" in wk or "-regen-" in wk:
            continue
        d = _read_json(p)
        if d is None:
            continue
        if "_archive_meta" in d:
            continue
        src = "regenerated" if wk in known_regenerated else "hand_made"
        d["_archive_meta"] = _meta_of(d, src, None, backfill=True)
        if wk in known_regenerated:
            d["_archive_meta"]["discrepancy"] = (
                "Regenerated 2026-08-28, NOT the as-graded universe. As graded "
                "2026-08-21: 5,016 names, picks RDDT #4775 / LUNR #4515 / SMCI "
                "#4018 / IONQ #3266 / IREN #4334. This file: 4,997 names, same "
                "picks at #4757 / #4500 / #4007 / #3259 / #4321 — identical "
                "returns, 7-18 rank places off, because build_universe() reads "
                "the LIVE listed-symbol directory. No row crosses the <=100 or "
                "<=500 tier boundary under this drift.")
        try:
            with open(p, "w") as f:
                json.dump(d, f)
            _append(INDEX, {"week_start": wk, "file": p.name,
                            "action": "backfill_stamp", **d["_archive_meta"]})
            n += 1
            print(f"  stamped {p.name} source={src}")
        except Exception as e:
            print(f"  ⚠️ {p.name}: {e}")
    print(f"backfill: stamped {n} archive(s)")


def selftest():
    ok = True
    d = _read_json(SCAN_OUT)
    print("gainers-output.json readable:", d is not None)
    archives = sorted(p.stem.replace("gainers-", "")
                      for p in STOCKS.glob("gainers-2*.json")
                      if "-rescan-" not in p.stem and "-regen-" not in p.stem)
    print("archives on disk:", archives)
    # c6 — every archive filename must be a Monday
    for wk in archives:
        try:
            dt = datetime.strptime(wk, "%Y-%m-%d")
        except ValueError:
            print(f"  ⚠️ {wk} is not a date"); ok = False; continue
        if dt.weekday() != 0:
            print(f"  ⚠️ {wk} is not a Monday (week key must be WEEK_START)"); ok = False
    # c5 — no colons in any archive filename
    if any(":" in p.name for p in STOCKS.glob("gainers-2*.json")):
        print("  ⚠️ a colon appears in an archive filename"); ok = False
    print("selftest:", "PASS" if ok else "FAIL")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week-start")
    ap.add_argument("--run-start")
    ap.add_argument("--source", default="live_scan",
                    choices=["live_scan", "regenerated"])
    ap.add_argument("--postponed", action="store_true")
    ap.add_argument("--reason", default="")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    try:
        if a.selftest:
            selftest()
        elif a.backfill:
            backfill()
        elif a.postponed:
            _append(POSTPONED, {"week_start": a.week_start, "recorded_at": _now(),
                                "reason": a.reason or "u2_health_guard_failed"})
            print(f"U.2: no archive written for {a.week_start} (postponed)")
        elif a.week_start:
            archive(a.week_start, a.run_start, a.source)
        else:
            ap.print_help()
    except Exception as e:                     # c14 — fail-open, always
        print(f"U.2: ⚠️ archive step error ({e}) — grading is unaffected")
    sys.exit(0)


if __name__ == "__main__":
    main()
