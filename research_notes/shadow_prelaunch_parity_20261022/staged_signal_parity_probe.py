#!/usr/bin/env python3
"""Read-only V5.4 staged-signal timestamp/ID parity probe. NO network.

An observer export is historical witness evidence, not launch certification.
For launch qualification rerun on actual pinned staged ordinary-cycle bytes.
"""
import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
FROZEN_OPENS = {(9, 30), (13, 30)}

def rows_from(data):
    if isinstance(data, list):
        return data, "array"
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object or row array")
    if isinstance(data.get("assessments"), list):
        return [x.get("features") or {} for x in data["assessments"]], "assessment_features"
    for key in ("qualified_signals", "candidates", "signals", "rows"):
        if isinstance(data.get(key), list):
            return data[key], key
    raise ValueError("no recognized signal array")

def aware(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None and dt.utcoffset() is not None else None

def verify(data, source_sha256=None, sample_max=4):
    rows, container = rows_from(data)
    errors = collections.Counter()
    by_open = collections.Counter()
    by_duration = collections.Counter()
    by_version = collections.Counter()
    bad, ids = [], set()
    for i, row in enumerate(rows):
        problems = []
        if not isinstance(row, dict):
            problems.append("non_object_row")
            row = {}
        symbol = row.get("symbol")
        signal_id = row.get("signal_id")
        version = row.get("v54_rule_version")
        start = aware(row.get("signal_bar_start_at"))
        close = aware(row.get("signal_bar_close_at"))
        if not symbol or not signal_id or not version:
            problems.append("missing_identity")
        if signal_id in ids:
            problems.append("duplicate_signal_id")
        if signal_id:
            ids.add(signal_id)
        if not start or not close:
            problems.append("missing_or_naive_stamps")
        else:
            local = start.astimezone(ET)
            hours = (close - start).total_seconds() / 3600
            by_open[local.strftime("%H:%M")] += 1
            by_duration[str(hours)] += 1
            if (local.hour, local.minute) not in FROZEN_OPENS:
                problems.append("off_frozen_0930_1330_grid")
            if close - start != timedelta(hours=4):
                problems.append("not_exact_four_hours")
        if signal_id and symbol and close and version:
            expected = f'v54:{symbol}:4h:{row.get("signal_bar_close_at")}:{version}'
            if signal_id != expected:
                problems.append("noncanonical_signal_id")
        by_version[str(version)] += 1
        for p in problems:
            errors[p] += 1
        if problems and len(bad) < sample_max:
            bad.append({"row_index": i, "symbol": symbol,
                        "bar_start": row.get("signal_bar_start_at"),
                        "bar_close": row.get("signal_bar_close_at"),
                        "reasons": problems})
    return {"verdict": "PASS" if rows and not errors else "HOLD",
            "scope": "offline historical witness; NOT launch certification",
            "source_sha256": source_sha256, "container": container,
            "rows": len(rows), "opening_times_ET": dict(sorted(by_open.items())),
            "durations_hours": dict(sorted(by_duration.items())),
            "rule_versions": dict(sorted(by_version.items())),
            "failures": dict(sorted(errors.items())), "bad_examples": bad}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("json_file", help="already stored JSON; NEVER fetch data")
    args = p.parse_args()
    raw = Path(args.json_file).read_bytes()
    result = verify(json.loads(raw), hashlib.sha256(raw).hexdigest())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 2

if __name__ == "__main__":
    sys.exit(main())
