#!/usr/bin/env python3
"""
test_completeness_check_v94.py — task -94 checker delta suite.

Proves the -94 correction (ChatGPT review, Issue #1 comment
6353306848): the crypto session model is the ADOPTED S-C1…S-C6
spec — session [D 09:30 ET, D+1 09:30 ET), expected bars generated
as absolute UTC instants — against DST adversarial fixtures:

  spring session 2024-03-09: 23 bars, and the nonexistent 02:00 ET
    wall hour is NOT a missing bar;
  fall session 2024-11-02: 25 bars, and the duplicated 01:00 ET
    wall hour is NOT a duplicate timestamp;
  a real missing bar, a real duplicate instant, and an off-grid
    extra bar still fail closed;
  the -93 midnight-anchored "clean" fixture shape now FAILS —
    the false pass the -94 review identified is closed.

All fixtures synthetic. Equity floor spot-check included; the full
equity regression is the prior suites re-run against this module
(see ../TEST_EVIDENCE.md).
"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import crypto_session_model as model  # noqa: E402
import tsla_completeness_check as chk  # noqa: E402

NY = "America/New_York"
NYZ = ZoneInfo(NY)
RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name, detail if not cond else "")


def bars_for_sessions(session_dates, tz=NY):
    """UTC-contiguous hourly bars over the given sessions, built
    from the adopted model, stamped in `tz`."""
    instants = []
    for d in session_dates:
        instants += model.expected_bar_instants_utc(d)
    rows = []
    price = 100.0
    for t in sorted(set(instants)):
        ts = pd.Timestamp(t)
        if tz != "UTC":
            ts = ts.tz_convert(tz)
        o = price
        c = price + 0.01
        rows.append((ts, o, max(o, c) + 0.005, min(o, c) - 0.005, c, 500))
        price = c
    df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low",
                                     "Close", "Volume"])
    return df.set_index("ts").sort_index()


def sess_table(session_dates):
    return {d: 1440 for d in session_dates}


def defects(res):
    return [d["defect"] for d in res["structural"]["defects"]] + \
           [d["defect"] for d in res["anomaly"]["defect_bars"]]


def main():
    print(f"checker version: {chk.CHECKER_VERSION}")
    case("V94_C0_version_string",
         chk.CHECKER_VERSION == "checker-v3-candidate-2",
         chk.CHECKER_VERSION)

    # ---- session model: canonical DST counts and span instants --
    case("V94_M1_model_counts_23_24_25",
         model.expected_bar_count(date(2024, 3, 9)) == 23
         and model.expected_bar_count(date(2024, 1, 2)) == 24
         and model.expected_bar_count(date(2024, 11, 2)) == 25)
    s, e = model.session_span_utc(date(2024, 3, 9))
    case("V94_M2_spring_span_instants",
         s == datetime(2024, 3, 9, 14, 30, tzinfo=timezone.utc)
         and e == datetime(2024, 3, 10, 13, 30, tzinfo=timezone.utc),
         f"{s} {e}")
    s, e = model.session_span_utc(date(2024, 11, 2))
    case("V94_M3_fall_span_instants",
         s == datetime(2024, 11, 2, 13, 30, tzinfo=timezone.utc)
         and e == datetime(2024, 11, 3, 14, 30, tzinfo=timezone.utc),
         f"{s} {e}")
    # The checker's internal generator agrees with the model,
    # instant for instant, across a DST week on each side.
    agree = True
    for base in (date(2024, 3, 6), date(2024, 10, 30)):
        for k in range(7):
            d = base + timedelta(days=k)
            mine = [t.to_pydatetime()
                    for t in chk._expected_instants_crypto(d)]
            if mine != model.expected_bar_instants_utc(d):
                agree = False
    case("V94_M4_checker_matches_model", agree)
    # Independent zoneinfo re-derivation of the fall count: the
    # span [Nov 2 09:30 ET, Nov 3 09:30 ET) is 25 elapsed hours.
    start = datetime.combine(date(2024, 11, 2),
                             datetime.min.time(), tzinfo=NYZ) \
        .replace(hour=9, minute=30)
    end = datetime.combine(date(2024, 11, 3),
                           datetime.min.time(), tzinfo=NYZ) \
        .replace(hour=9, minute=30)
    case("V94_M5_zoneinfo_rederive_fall_25",
         (end.astimezone(timezone.utc) - start.astimezone(timezone.utc))
         == timedelta(hours=25))

    JAN = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]

    # ---- clean series on the adopted anchor ----------------------
    res = chk.run_check(bars_for_sessions(JAN), sess_table(JAN), [],
                        instrument="crypto")
    case("V94_K1_clean_normal_sessions",
         res["overall"] == "QUALIFIED_CLEAN", str(res["overall"]))

    res = chk.run_check(bars_for_sessions(JAN, tz="UTC"),
                        sess_table(JAN), [], instrument="crypto")
    case("V94_K2_clean_utc_stamps_attributed",
         res["overall"] == "QUALIFIED_CLEAN", str(res["overall"]))

    SPRING = [date(2024, 3, 8), date(2024, 3, 9), date(2024, 3, 10)]
    df = bars_for_sessions(SPRING)
    assert len(df) == 24 + 23 + 24
    res = chk.run_check(df, sess_table(SPRING), [], instrument="crypto")
    case("V94_K3_clean_spring_23_no_missing_wall_hour",
         res["overall"] == "QUALIFIED_CLEAN"
         and res["count"]["missing_bars"] == []
         and "DUPLICATE_TIMESTAMP" not in defects(res),
         str(res["overall"]) + " " + str(res["count"]["missing_bars"]))

    FALL = [date(2024, 11, 1), date(2024, 11, 2), date(2024, 11, 3)]
    df = bars_for_sessions(FALL)
    assert len(df) == 24 + 25 + 24
    stamps = [str(t) for t in df.index]
    # Fixture sanity: the frame really carries both fall wall-hour
    # occurrences as distinct offset-aware stamps (bars are
    # :30-phase — session opens are 09:30 — so the repeated hour
    # surfaces as 01:30-04:00 and 01:30-05:00).
    assert any(s.startswith("2024-11-03 01:30:00-04:00")
               for s in stamps)
    assert any(s.startswith("2024-11-03 01:30:00-05:00")
               for s in stamps)
    res = chk.run_check(df, sess_table(FALL), [], instrument="crypto")
    case("V94_K4_clean_fall_25_no_false_duplicate",
         res["overall"] == "QUALIFIED_CLEAN"
         and "DUPLICATE_TIMESTAMP" not in defects(res),
         str(res["overall"]) + " " + str(defects(res)))

    # ---- real defects still fail closed --------------------------
    # A genuinely missing bar inside the spring session.
    df = bars_for_sessions(SPRING)
    drop = pd.Timestamp("2024-03-10 07:30", tz="UTC")
    res = chk.run_check(df.drop(drop.tz_convert(NY)), sess_table(SPRING),
                        [], instrument="crypto")
    case("V94_K5_real_missing_bar_fails",
         res["overall"] == "COMPLETENESS_FAIL"
         and any("2024-03-10 03:30:00-04:00" in m
                 for m in res["count"]["missing_bars"]),
         str(res["count"]["missing_bars"]))

    # A genuinely duplicated instant (exact repeated row).
    df = bars_for_sessions(FALL)
    dup = pd.concat([df, df.iloc[[30]]]).sort_index()
    res = chk.run_check(dup, sess_table(FALL), [], instrument="crypto")
    case("V94_K6_real_duplicate_instant_fails",
         "DUPLICATE_TIMESTAMP" in defects(res)
         and res["completeness_verdict"] == "FAIL", str(defects(res)))

    # An off-grid extra bar (defective vendor stamp, +30 min).
    df = bars_for_sessions(JAN)
    extra_ts = pd.Timestamp("2024-01-03 10:00", tz=NY)
    row = pd.DataFrame(
        [(100.5, 100.6, 100.4, 100.55, 500)],
        columns=["Open", "High", "Low", "Close", "Volume"],
        index=pd.DatetimeIndex([extra_ts], name="ts"))
    df2 = pd.concat([df, row]).sort_index()
    res = chk.run_check(df2, sess_table(JAN), [], instrument="crypto")
    case("V94_K7_off_grid_extra_bar_fails",
         res["overall"] == "COMPLETENESS_FAIL"
         and len(res["count"]["extra_bars"]) >= 1,
         str(res["count"]["extra_bars"]))

    # A whole DST session absent from the frame: named, and its
    # expected starts number 23 — the spring count, not 24.
    sess = sess_table(SPRING)
    df = bars_for_sessions([SPRING[0], SPRING[2]])
    res = chk.run_check(df, sess, [], instrument="crypto")
    ms = res["count"]["missing_sessions"]
    case("V94_K8_missing_dst_session_23_expected",
         res["overall"] == "COMPLETENESS_FAIL" and len(ms) == 1
         and ms[0]["session"] == "2024-03-09"
         and len(ms[0]["expected_bar_starts"]) == 23, str(ms))

    # The -93 fixture shape (midnight-anchored) is a misaligned
    # series under the adopted spec: the old false pass is closed.
    rows = []
    price = 100.0
    for d in JAN:
        base = pd.Timestamp(d, tz=NY)
        for h in range(24):
            ts = base + pd.Timedelta(hours=h)
            o = price
            c = price + 0.01
            rows.append((ts, o, max(o, c) + 0.005,
                         min(o, c) - 0.005, c, 500))
            price = c
    legacy = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low",
                                         "Close", "Volume"]) \
        .set_index("ts").sort_index()
    res = chk.run_check(legacy, sess_table(JAN), [], instrument="crypto")
    case("V94_K9_midnight_anchored_series_fails",
         res["overall"] == "COMPLETENESS_FAIL", str(res["overall"]))

    # Floors: declared splits refused; naive index named, no crash.
    try:
        chk.run_check(bars_for_sessions(JAN), sess_table(JAN),
                      [("2024-01-03", 3.0)], instrument="crypto")
        case("V94_K10_declared_split_refused", False, "no raise")
    except ValueError as e:
        case("V94_K10_declared_split_refused",
             "CRYPTO_DECLARED_SPLITS_NOT_APPLICABLE" in str(e), str(e))
    df = bars_for_sessions(JAN)
    df.index = df.index.tz_localize(None)
    res = chk.run_check(df, sess_table(JAN), [], instrument="crypto")
    case("V94_K11_naive_index_named_not_crash",
         "TZ_NAIVE" in defects(res)
         and res["completeness_verdict"] == "FAIL", str(defects(res)))

    # Equity floor spot-check: the equity path is untouched.
    rows = []
    price = 100.0
    for d in ("2024-01-02", "2024-01-03", "2024-01-04"):
        day = pd.Timestamp(d, tz=NY)
        for k in range(7):
            ts = day + pd.Timedelta(minutes=570 + 60 * k)
            o = price
            c = price + 0.10
            rows.append((ts, o, max(o, c) + 0.05, min(o, c) - 0.05,
                         c, 1000))
            price = c
    eq = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low",
                                     "Close", "Volume"]).set_index("ts")
    eq_sess = {pd.Timestamp(d).date(): 960
               for d in ("2024-01-02", "2024-01-03", "2024-01-04")}
    res = chk.run_check(eq, eq_sess, [])
    case("V94_K12_equity_floor_clean",
         res["overall"] == "QUALIFIED_CLEAN", str(res["overall"]))

    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"{n_pass}/{len(RESULTS)} checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
