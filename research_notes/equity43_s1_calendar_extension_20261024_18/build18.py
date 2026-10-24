#!/usr/bin/env python3
"""QF-EQUITY43-S1-CALENDAR-EXTENSION-20261024-18 — build + prove.

Assembles the candidate extended session table and proves:
  * the pinned 751-row table is byte-identical to its recorded SHA;
  * the rule generator (calendar_gen18) reproduces all 751 qualified
    rows exactly (fail-before anchor for the extension rules);
  * three-way agreement over 2023-10-19..2027-12-31 between the rule
    generator and BOTH pinned library paths (pandas_market_calendars
    4.5.1 native NYSE = path A; exchange_calendars 4.13.2 XNYS =
    path C, emitted by the byte-identical -35 generator, sha
    2995b124…) — any disagreement is a STOP with a full census;
  * the extended table's sessions segment carries the 751 qualified
    rows as an exact byte prefix;
  * the first appended session is 2026-10-19 (Mon).

Any failed check raises SystemExit(STOP) — no artifact is blessed.
"""
import hashlib
import json
import sys
from datetime import date

sys.path.insert(0, ".")
import calendar_gen18

PINNED_TABLE = "/home/hatch/workspace/qf_td17_stage/harness/session_table.json"
PINNED_TABLE_SHA = ("00c5555c26d391444509e54de322841fa3269b64f3"
                    "161a50aa507bf1d2bd416f")
FULL_START, FULL_END = date(2023, 10, 19), date(2027, 12, 31)
EXT_START = date(2026, 10, 17)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _rows_bytes(rows):
    return (json.dumps(rows, separators=(",", ":"), ensure_ascii=True)
            ).encode("utf-8")


def main():
    raw = open(PINNED_TABLE, "rb").read()
    assert _sha(raw) == PINNED_TABLE_SHA, "pinned table SHA mismatch"
    pinned = json.loads(raw)
    old_rows = pinned["sessions"]
    assert len(old_rows) == 751 and old_rows[-1]["date"] == "2026-10-16"
    print(f"pinned table sha OK ({PINNED_TABLE_SHA[:12]}…), 751 rows, "
          f"last {old_rows[-1]['date']}")

    # rule generator: qualified range must reproduce the pinned rows
    qual = calendar_gen18.generate(FULL_START, date(2026, 10, 16))
    assert qual == old_rows, "rule generator diverges on qualified range"
    print("rule generator reproduces all 751 qualified rows exactly")

    # three-way agreement over the full range
    full_rules = calendar_gen18.generate(FULL_START, FULL_END)
    lib_a = json.load(open("emission_A_full.json"))
    lib_c = json.load(open("emission_C_full.json"))
    for name, lib in (("A/pmc-NYSE", lib_a), ("C/ec-XNYS", lib_c)):
        if lib != full_rules:
            gs = {r["date"]: r for r in full_rules}
            ls = {r["date"]: r for r in lib}
            diffs = [(d, gs.get(d), ls.get(d))
                     for d in sorted(set(gs) | set(ls))
                     if gs.get(d) != ls.get(d)]
            print(f"STOP: rules vs {name}: {len(diffs)} diffs")
            for d in diffs[:40]:
                print("  DIFF", d)
            raise SystemExit(2)
        print(f"rules == path {name}: {len(lib)} sessions, exact")
    assert lib_a == lib_c
    print("three-way agreement: rules == A == C over "
          f"{FULL_START}..{FULL_END} ({len(full_rules)} sessions)")

    appended = [r for r in full_rules if r["date"] >= EXT_START.isoformat()]
    assert appended and appended[0]["date"] == "2026-10-19", appended[:1]
    assert full_rules[:751] == old_rows
    print(f"appended sessions: {len(appended)} "
          f"({appended[0]['date']}..{appended[-1]['date']}); "
          f"total {len(full_rules)}")

    # byte-prefix proof on the sessions segment
    old_seg = _rows_bytes(old_rows)
    new_seg = _rows_bytes(full_rules)
    assert new_seg[:len(old_seg) - 1] == old_seg[:-1] or \
        new_seg.startswith(old_seg[:-1] + b",")
    prefix_ok = new_seg[:len(old_seg) - 1] == old_seg[:-1]
    print(f"sessions-segment byte prefix (751 rows): {prefix_ok}")
    assert prefix_ok

    table = {
        "artifact": "XNYS_SESSION_TABLE_751_UNION_PLUS_S1_EXTENSION_"
                    "CANDIDATE_20261024_18",
        "sources": [
            "XNYS_SESSION_TABLE_751_UNION (751 sessions, "
            "2023-10-19..2026-10-16) — prefix, byte-identical rows",
            "QF-EQUITY43-S1-CALENDAR-EXTENSION-20261024-18 rule "
            "generator calendar_gen18 (append-only extension "
            "2026-10-19..2027-12-31), three-way cross-checked vs "
            "pandas_market_calendars 4.5.1 (NYSE) and "
            "exchange_calendars 4.13.2 (XNYS) via the pinned -35 "
            "generator (sha 2995b124…) — CANDIDATE, NOT ADOPTED",
        ],
        "calendar_version": "XNYS-751-UNION+S1EXT-CANDIDATE-20261024-18",
        "session_count": len(full_rules),
        "sessions": full_rules,
    }
    blob = (json.dumps(table, separators=(",", ":"), ensure_ascii=True)
            + "\n").encode("utf-8")
    with open("session_table_extended_candidate.json", "wb") as f:
        f.write(blob)
    print(f"extended table written: {len(blob)} bytes sha256={_sha(blob)}")
    census = {
        "pinned_table_sha256": PINNED_TABLE_SHA,
        "prefix_sessions": 751,
        "appended_sessions": len(appended),
        "total_sessions": len(full_rules),
        "first_appended": appended[0],
        "last_appended": appended[-1],
        "appended_early_closes": [r["date"] for r in appended
                                  if r["close"] != "16:00"],
        "extended_table_sha256": _sha(blob),
        "extended_table_bytes": len(blob),
        "sessions_segment_byte_prefix": prefix_ok,
    }
    with open("build_census.json", "w") as f:
        json.dump(census, f, indent=2, sort_keys=True)
    print(json.dumps(census, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
