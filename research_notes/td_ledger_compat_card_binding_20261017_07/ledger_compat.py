#!/usr/bin/env python3
"""
ledger_compat.py — QF-TD-LEDGER-COMPAT-AND-CARD-BINDING-20261017-07 r1.

Separate-output, dry-run-only compatibility converter: legacy pilot
limiter ledger (rate_limiter.py v3 schema {"day","spent","window"})
-> the reservation schema consumed by BOTH the r2 dispatch gate
(dispatch_gate_r2.py gate 4) and the integrated live driver
(live_driver.py Limiter): {"reservations":[{"rid","ts","day","weight"}]}.

Safety contract:
- The source ledger is READ-ONLY here. It is never overwritten, renamed,
  or mutated; the candidate is written to a distinct output path
  (refused if it equals the source path).
- Conservative accounting: every legacy credit is preserved or
  overcounted, never undercounted. The candidate's per-UTC-day weight
  sum for the legacy day equals max(spent, same-day window sum); the
  rolling-60s window content is carried record-for-record.
- Fail closed (CompatRefusal) on malformed / future / duplicate /
  negative / ambiguous source states. Nothing is silently reset.
- Deterministic: identical (source bytes, source path, target instant)
  -> byte-identical candidate and receipt (idempotence is testable).
"""
import calendar
import hashlib
import json
import math
import os
import re
import time

DAY_CAP = 800          # pinned: dispatch_gate_r2.DAY_CAP / Limiter day_cap
WINDOW_SECONDS = 60.0  # pinned: rate_limiter.WINDOW_SECONDS
_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class CompatRefusal(Exception):
    """Fail-closed refusal: the source state cannot be converted
    conservatively, so no candidate is emitted."""


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def day_of(ts):
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def day_start(day):
    return calendar.timegm(time.strptime(day, "%Y-%m-%d"))


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validate_source(obj, target_instant):
    """Validate the legacy schema exactly; return (day, spent, window)
    with window as a list of (float_ts, int_weight). Raises CompatRefusal."""
    if not isinstance(obj, dict):
        raise CompatRefusal("SOURCE_NOT_OBJECT")
    if "reservations" in obj:
        raise CompatRefusal("SOURCE_ALREADY_RESERVATION_SCHEMA")
    unknown = set(obj) - {"day", "spent", "window"}
    if unknown:
        raise CompatRefusal("SOURCE_UNKNOWN_KEYS:%s" % sorted(unknown))
    day = obj.get("day")
    spent = obj.get("spent", 0)
    window = obj.get("window", [])
    if day is not None:
        if not isinstance(day, str) or not _DAY_RE.match(day):
            raise CompatRefusal("SOURCE_DAY_MALFORMED")
        try:
            time.strptime(day, "%Y-%m-%d")
        except ValueError:
            raise CompatRefusal("SOURCE_DAY_NOT_A_DATE")
    if not isinstance(spent, int) or isinstance(spent, bool):
        raise CompatRefusal("SOURCE_SPENT_NOT_INT")
    if spent < 0:
        raise CompatRefusal("SOURCE_SPENT_NEGATIVE")
    if spent > DAY_CAP:
        raise CompatRefusal("SOURCE_SPENT_OVER_DAY_CAP")
    if not isinstance(window, list):
        raise CompatRefusal("SOURCE_WINDOW_NOT_LIST")
    clean = []
    seen = set()
    for item in window:
        if not (isinstance(item, (list, tuple)) and len(item) == 2):
            raise CompatRefusal("SOURCE_WINDOW_ENTRY_MALFORMED")
        ts, w = item
        if not _is_num(ts) or not math.isfinite(ts) or ts < 0:
            raise CompatRefusal("SOURCE_WINDOW_TS_INVALID")
        if not isinstance(w, int) or isinstance(w, bool) or w < 1:
            raise CompatRefusal("SOURCE_WINDOW_WEIGHT_INVALID")
        if w > DAY_CAP:
            raise CompatRefusal("SOURCE_WINDOW_WEIGHT_OVER_DAY_CAP")
        ts = float(ts)
        if ts > target_instant:
            raise CompatRefusal("SOURCE_WINDOW_TS_FUTURE")
        key = (ts, w)
        if key in seen:
            raise CompatRefusal("SOURCE_WINDOW_DUPLICATE_RECORD")
        seen.add(key)
        clean.append((ts, int(w)))
    if day is None:
        if spent != 0 or clean:
            raise CompatRefusal("SOURCE_DAY_ABSENT_BUT_STATE_NONEMPTY")
        return day, spent, clean
    start = day_start(day)
    for ts, _w in clean:
        d = day_of(ts)
        if d == day:
            continue
        # Cross-midnight retention is the only legitimate off-day case:
        # the entry belongs to the previous UTC day and was still inside
        # the rolling window when the day rolled over (ts >= start-60).
        prev = day_of(start - 1)
        if d == prev and ts >= start - WINDOW_SECONDS:
            continue
        raise CompatRefusal("SOURCE_WINDOW_ENTRY_DAY_AMBIGUOUS")
    same_day_sum = sum(w for ts, w in clean if day_of(ts) == day)
    if spent < same_day_sum:
        # Unreachable under the legacy limiter (spent counts every grant
        # of the day; the window is a subset). Ambiguous -> refuse.
        raise CompatRefusal("SOURCE_SPENT_BELOW_WINDOW_SUM")
    return day, spent, clean


def convert(source_bytes, source_path, target_instant):
    """Convert legacy ledger bytes -> (candidate_obj, candidate_bytes,
    receipt_obj). Pure and deterministic. Raises CompatRefusal."""
    src_sha = sha256(source_bytes)
    try:
        obj = json.loads(source_bytes)
    except ValueError:
        raise CompatRefusal("SOURCE_MALFORMED_JSON")
    day, spent, window = validate_source(obj, target_instant)
    prefix = "legacy-%s" % src_sha[:12]
    records = []
    mapping = []
    for i, (ts, w) in enumerate(window):
        rid = "%s-%04d" % (prefix, i)
        records.append({"rid": rid, "ts": ts, "day": day_of(ts), "weight": w})
        mapping.append({"legacy_index": i, "rid": rid, "ts": ts,
                        "day": day_of(ts), "weight": w, "kind": "window"})
    residual = 0
    if day is not None:
        same_day_sum = sum(w for ts, w in window if day_of(ts) == day)
        residual = spent - same_day_sum  # >= 0, enforced by validation
        if residual > 0:
            same_day_ts = [ts for ts, _w in window if day_of(ts) == day]
            rts = max(same_day_ts) if same_day_ts else float(day_start(day))
            for j in range(residual):
                rid = "%s-residual-%04d" % (prefix, j)
                records.append({"rid": rid, "ts": rts, "day": day, "weight": 1})
                mapping.append({"legacy_index": None, "rid": rid, "ts": rts,
                                "day": day, "weight": 1, "kind": "day_residual"})
    records.sort(key=lambda r: (r["ts"], r["rid"]))
    candidate = {"reservations": records}
    candidate_bytes = canon(candidate)
    cand_sha = sha256(candidate_bytes)

    def day_sum(d):
        return sum(r["weight"] for r in records if r["day"] == d)

    def active(t):
        sel = [r for r in records if r["ts"] > t - WINDOW_SECONDS]
        return {"records": len(sel), "weight": sum(r["weight"] for r in sel)}

    src_active = [w for ts, w in window if ts > target_instant - WINDOW_SECONDS]
    max_src_ts = max([ts for ts, _w in window], default=None)
    staleness = {
        "source_day": day,
        "target_day": day_of(target_instant),
        "source_day_is_target_day": day == day_of(target_instant),
        "max_source_ts": max_src_ts,
        "all_source_ts_older_than_rolling_window": (
            max_src_ts is not None
            and max_src_ts <= target_instant - WINDOW_SECONDS),
        "proven_from_timestamps": True,
        "silent_reset": False,
    }
    receipt = {
        "receipt": "LEDGER_COMPAT_CONVERSION",
        "task": "QF-TD-LEDGER-COMPAT-AND-CARD-BINDING-20261017-07",
        "source_path": os.path.abspath(source_path),
        "source_sha256": src_sha,
        "target_instant": target_instant,
        "target_instant_iso": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(target_instant)),
        "candidate_sha256": cand_sha,
        "candidate_records": len(records),
        "source_accounting": {
            "day": day,
            "spent": spent,
            "window_entries": len(window),
            "window_weight_total": sum(w for _ts, w in window),
            "window_weight_on_ledger_day": (
                sum(w for ts, w in window if day_of(ts) == day)
                if day is not None else 0),
        },
        "candidate_accounting": {
            "day_sum_on_source_day": day_sum(day) if day is not None else 0,
            "day_sum_on_target_day": day_sum(day_of(target_instant)),
            "active_window_at_target": active(target_instant),
            "source_active_window_at_target": {
                "records": len(src_active), "weight": sum(src_active)},
            "day_residual_emitted": residual,
        },
        "conservation": {
            "day_total_preserved_or_overcounted": (
                day is None
                or day_sum(day) >= spent),
            "rolling_window_preserved_or_overcounted": (
                active(target_instant)["weight"] >= sum(src_active)),
            "undercount": False,
        },
        "staleness": staleness,
        "mapping": mapping,
    }
    return candidate, candidate_bytes, receipt


def convert_file(source_path, out_path, receipt_path, target_instant):
    if os.path.abspath(out_path) == os.path.abspath(source_path):
        raise CompatRefusal("OUTPUT_EQUALS_SOURCE")
    with open(source_path, "rb") as f:
        before = f.read()
    candidate, candidate_bytes, receipt = convert(before, source_path,
                                                  target_instant)
    with open(out_path, "wb") as f:
        f.write(candidate_bytes)
    with open(source_path, "rb") as f:
        after = f.read()
    receipt["source_sha256_after"] = sha256(after)
    receipt["source_bytes_unchanged"] = (after == before)
    if after != before:
        raise CompatRefusal("SOURCE_CHANGED_DURING_CONVERSION")
    with open(receipt_path, "wb") as f:
        f.write(canon(receipt))
    return receipt


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--target-instant", required=True, type=float)
    ap.add_argument("--out", required=True)
    ap.add_argument("--receipt", required=True)
    a = ap.parse_args()
    try:
        r = convert_file(a.source, a.out, a.receipt, a.target_instant)
    except CompatRefusal as e:
        print("REFUSED:%s" % e)
        sys.exit(2)
    print("OK candidate_sha256=%s records=%d source_unchanged=%s"
          % (r["candidate_sha256"], r["candidate_records"],
             r["source_bytes_unchanged"]))
