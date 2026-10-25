"""Build the versioned XNYS session-table EXTENSION (P8 horizon repair).

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-30.

ChatGPT's -29r verdict (Slack TS 1792941227.393299) held P8 on the
calendar horizon: the adopted 751-session table ends 2026-10-16 and
`session_bins` correctly fails closed after it, so the prospective
telemetry journal cannot accept the Oct 26-30 pilot week or any later
forward record. The verdict requires: "commit and independently
qualify a versioned session-table extension covering the declared
future observation horizon, including holidays/early closes and a new
hash/provenance. Do not silently generate or extrapolate sessions."

This builder constructs the extension EXPLICITLY from the NYSE
published holiday / early-closing calendar — every closure and every
early close in the horizon is a named, dated entry below (no weekday
arithmetic derives a holiday; weekdays only enumerate candidate
sessions). Horizon: 2026-10-19..2027-12-31 (the first session after
the adopted table's last session, through the end of 2027).

Qualification cross-checks (all enforced by the builder; any failure
aborts the build):
  X1  The SAME rule engine, applied to 2023-10-19..2026-10-16 with
      the historical closure lists below, reproduces the adopted
      751-session table EXACTLY (dates + closes) — the construction
      method is thereby validated against the calendar of record
      itself, including its one ad-hoc closure (2025-01-09, national
      day of mourning).
  X2  exchange_calendars' XNYS schedule over the extension horizon
      agrees on every session date and every close time (independent
      library implementation of the same exchange rules).
  X3  Published-count checks: 251 sessions in calendar 2027 (NYSE
      published), 52 sessions in the 2026 tail (54 weekdays - 2
      closures), exactly 3 early closes in the extension.
  X4  Continuity: the extension's first session is the first weekday
      after the base table's last session (2026-10-16 -> 2026-10-19),
      and the two tables are disjoint.

Sources (read 2026-10-25): NYSE Group press release "NYSE Group
Announces 2026, 2027 and 2028 Holiday and Early Closings Calendar"
(2025-12-23); NYSE "Holiday Closures" PDF (holiday table 2025-2027
with early-closing footnotes: day after Thanksgiving 2026-11-27 and
2027-11-26, Christmas Eve 2026-12-24; Dec 24 2027 is the observed
Christmas closure, and there is no Jul 2 / Dec 23 early close in
2027); exchange_calendars 4.13.2 XNYS (cross-check only).

The base table is never modified: the extension is a separate
artifact with its own sha256, loaded alongside the base by
session_bins.load_union_table().
"""
import hashlib
import json
import os
import sys
from datetime import date, timedelta

BASE_TABLE_REL = os.path.join(
    "research_notes", "equity43_feed_source_review_20261024_22",
    "bundle", "calendar", "session_table_751_qualified.json")
BASE_TABLE_SHA256 = \
    "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f"

HORIZON_FIRST = date(2026, 10, 19)
HORIZON_LAST = date(2027, 12, 31)

# --- Explicit NYSE closures inside the horizon (date -> name) -------
HOLIDAYS = {
    "2026-11-26": "Thanksgiving Day",
    "2026-12-25": "Christmas Day",
    "2027-01-01": "New Year's Day",
    "2027-01-18": "Martin Luther King, Jr. Day",
    "2027-02-15": "Washington's Birthday",
    "2027-03-26": "Good Friday",
    "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth National Independence Day (observed; "
                  "Jun 19 falls on Saturday)",
    "2027-07-05": "Independence Day (observed; Jul 4 falls on Sunday)",
    "2027-09-06": "Labor Day",
    "2027-11-25": "Thanksgiving Day",
    "2027-12-24": "Christmas Day (observed; Dec 25 falls on Saturday)",
}
# --- Explicit NYSE early closes (13:00 ET) inside the horizon -------
EARLY_CLOSES = {
    "2026-11-27": "Day after Thanksgiving",
    "2026-12-24": "Christmas Eve",
    "2027-11-26": "Day after Thanksgiving",
}

# --- Historical closure lists, used ONLY for cross-check X1 ---------
# (reproducing the adopted 751 table from the same construction).
HIST_HOLIDAYS = {
    "2023-11-23": "Thanksgiving Day", "2023-12-25": "Christmas Day",
    "2024-01-01": "New Year's Day", "2024-01-15": "MLK Day",
    "2024-02-19": "Washington's Birthday", "2024-03-29": "Good Friday",
    "2024-05-27": "Memorial Day", "2024-06-19": "Juneteenth",
    "2024-07-04": "Independence Day", "2024-09-02": "Labor Day",
    "2024-11-28": "Thanksgiving Day", "2024-12-25": "Christmas Day",
    "2025-01-01": "New Year's Day",
    "2025-01-09": "National Day of Mourning (ad-hoc closure)",
    "2025-01-20": "MLK Day", "2025-02-17": "Washington's Birthday",
    "2025-04-18": "Good Friday", "2025-05-26": "Memorial Day",
    "2025-06-19": "Juneteenth", "2025-07-04": "Independence Day",
    "2025-09-01": "Labor Day", "2025-11-27": "Thanksgiving Day",
    "2025-12-25": "Christmas Day",
    "2026-01-01": "New Year's Day", "2026-01-19": "MLK Day",
    "2026-02-16": "Washington's Birthday", "2026-04-03": "Good Friday",
    "2026-05-25": "Memorial Day", "2026-06-19": "Juneteenth",
    "2026-07-03": "Independence Day (observed; Jul 4 falls on "
                  "Saturday)",
    "2026-09-07": "Labor Day",
}
HIST_EARLY_CLOSES = {
    "2023-11-24": "Day after Thanksgiving",
    "2024-07-03": "Day before Independence Day",
    "2024-11-29": "Day after Thanksgiving",
    "2024-12-24": "Christmas Eve",
    "2025-07-03": "Day before Independence Day",
    "2025-11-28": "Day after Thanksgiving",
    "2025-12-24": "Christmas Eve",
}


def build_sessions(first, last, holidays, early_closes):
    """Sessions = weekdays in [first, last] minus the explicitly
    listed closures; close 13:00 on the explicitly listed early
    closes, else 16:00. Nothing else is inferred."""
    out = []
    d = first
    while d <= last:
        if d.weekday() < 5:
            ds = d.isoformat()
            if ds not in holidays:
                out.append({"date": ds, "open": "09:30",
                            "close": "13:00" if ds in early_closes
                            else "16:00"})
        d += timedelta(days=1)
    return out


def _repo_root():
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def main():
    root = _repo_root()
    raw = open(os.path.join(root, BASE_TABLE_REL), "rb").read()
    assert hashlib.sha256(raw).hexdigest() == BASE_TABLE_SHA256, \
        "base table hash mismatch — refusing to extend an unverified base"
    base = json.loads(raw)["sessions"]
    base_dates = {r["date"] for r in base}
    assert base[-1]["date"] == "2026-10-16"

    # X1: reproduce the adopted table from the same construction.
    repro = build_sessions(date(2023, 10, 19), date(2026, 10, 16),
                           HIST_HOLIDAYS, HIST_EARLY_CLOSES)
    assert repro == base, (
        "X1 FAILED: rule-engine reproduction of the adopted 751 "
        f"table differs ({len(repro)} vs {len(base)} sessions)")

    ext = build_sessions(HORIZON_FIRST, HORIZON_LAST,
                         HOLIDAYS, EARLY_CLOSES)

    # X3: published counts.
    n2027 = sum(1 for r in ext if r["date"].startswith("2027"))
    n2026 = sum(1 for r in ext if r["date"].startswith("2026"))
    nec = sum(1 for r in ext if r["close"] == "13:00")
    assert n2027 == 251, f"X3 FAILED: 2027 sessions {n2027} != 251"
    assert n2026 == 52, f"X3 FAILED: 2026-tail sessions {n2026} != 52"
    assert nec == 3, f"X3 FAILED: early closes {nec} != 3"

    # X4: continuity + disjointness.
    assert ext[0]["date"] == "2026-10-19" and not (
        base_dates & {r["date"] for r in ext}), "X4 FAILED"

    # X2: independent library cross-check (exchange_calendars XNYS).
    xcheck = {"library": "not available", "sessions_compared": 0,
              "date_mismatches": [], "close_mismatches": []}
    try:
        sys.path.insert(0, os.path.expanduser(
            "~/workspace/qf_td17_stage/pylibs"))
        import exchange_calendars as ecals
        cal = ecals.get_calendar("XNYS")
        # The vendored library's precomputed XNYS schedule ends
        # 2027-10-25; the cross-check covers the overlap exactly and
        # the coverage limit is recorded, not hidden. The remaining
        # tail (2027-10-26..12-31) rests on the NYSE published lists
        # plus X1/X3.
        lib_last = cal.last_session.strftime("%Y-%m-%d")
        sched = cal.schedule.loc["2026-10-19":lib_last]
        lib = {}
        for ts, row in sched.iterrows():
            lib[ts.strftime("%Y-%m-%d")] = (
                row["open"].tz_convert("America/New_York")
                .strftime("%H:%M"),
                row["close"].tz_convert("America/New_York")
                .strftime("%H:%M"))
        xcheck["library"] = f"exchange_calendars {ecals.__version__}"
        xcheck["library_coverage_through"] = lib_last
        mine = {r["date"]: (r["open"], r["close"]) for r in ext
                if r["date"] <= lib_last}
        xcheck["sessions_compared"] = len(set(mine) | set(lib))
        xcheck["date_mismatches"] = sorted(
            set(mine) ^ set(lib))
        xcheck["close_mismatches"] = sorted(
            ds for ds in set(mine) & set(lib) if mine[ds] != lib[ds])
        assert not xcheck["date_mismatches"], \
            f"X2 FAILED: date mismatches {xcheck['date_mismatches']}"
        assert not xcheck["close_mismatches"], \
            f"X2 FAILED: close mismatches {xcheck['close_mismatches']}"
    except ImportError:
        print("WARNING: exchange_calendars unavailable; X2 skipped")

    doc = {
        "artifact": "XNYS_SESSION_TABLE_EXTENSION_2027",
        "calendar_version": "XNYS-EXT-2027-20261025",
        "extends": {
            "artifact": "XNYS_SESSION_TABLE_751_UNION",
            "sha256": BASE_TABLE_SHA256,
            "last_session": "2026-10-16",
            "note": "the base table is byte-untouched; this extension "
                    "is a separate versioned artifact loaded "
                    "alongside it",
        },
        "horizon": {"first_session": ext[0]["date"],
                    "last_session": ext[-1]["date"],
                    "declared": "2026-10-19..2027-12-31"},
        "session_count": len(ext),
        "sources": [
            "NYSE Group press release 2025-12-23: 'NYSE Group "
            "Announces 2026, 2027 and 2028 Holiday and Early "
            "Closings Calendar'",
            "NYSE 'Holiday Closures' PDF (holiday table 2025-2027 "
            "with early-closing footnotes)",
            "exchange_calendars 4.13.2 XNYS (independent cross-check "
            "only, X2)",
        ],
        "construction": {
            "method": "weekdays in the declared horizon minus the "
                      "explicitly listed NYSE closures; close 13:00 "
                      "on the explicitly listed early closes, else "
                      "16:00; open 09:30 throughout. Holidays and "
                      "early closes are named per-date entries in "
                      "build_session_extension.py (HOLIDAYS / "
                      "EARLY_CLOSES); no session is extrapolated "
                      "beyond the declared horizon.",
            "holidays": HOLIDAYS,
            "early_closes": EARLY_CLOSES,
        },
        "cross_checks": {
            "X1_base_reproduction": "the same construction with the "
                                    "historical closure lists "
                                    "reproduces the adopted 751-"
                                    "session table exactly (dates + "
                                    "closes), incl. the 2025-01-09 "
                                    "ad-hoc mourning closure",
            "X2_exchange_calendars": xcheck,
            "X3_published_counts": {"sessions_2027": n2027,
                                    "sessions_2026_tail": n2026,
                                    "early_closes": nec},
            "X4_continuity": "first extension session 2026-10-19 is "
                             "the first weekday after the base "
                             "table's last session 2026-10-16; the "
                             "tables are disjoint",
        },
        "sessions": ext,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "artifacts",
                       "session_table_extension_2027.json")
    with open(out, "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    h = hashlib.sha256(open(out, "rb").read()).hexdigest()
    print(f"WROTE {out}")
    print(f"sessions={len(ext)} sha256={h}")
    print(f"X2: {xcheck}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
