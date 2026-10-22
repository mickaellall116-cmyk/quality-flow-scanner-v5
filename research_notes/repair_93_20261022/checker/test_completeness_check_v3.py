#!/usr/bin/env python3
"""
test_completeness_check_v3.py — task -93 checker v3 suite.

Proves the v3 additions from Claude's -92 HOLD (Issue #1 comment
6343957169): STRUCTURAL lane (duplicates / tz / order), invalid-
OHLC defect classes, NaN-at-split-boundary -> UNTESTABLE, and the
crypto 24/7 instrument mode — plus floor re-proofs that the
v1/v2 verdicts on their own cases are unchanged (clean control,
TSLA-class zero-volume, -91 missing session, clean declared
split). The -82/-89/-91 suites re-run against their pristine
modules as regressions (see ../TEST_EVIDENCE.md).
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import tsla_completeness_check as chk  # noqa: E402

NY = "America/New_York"
RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name, detail if not cond else "")


EQ_DAYS = ["2024-01-02", "2024-01-03", "2024-01-04"]


def equity_frame(days=EQ_DAYS, start_price=100.0):
    rows = []
    price = start_price
    for d in days:
        day = pd.Timestamp(d, tz=NY)
        for k in range(7):
            ts = day + pd.Timedelta(minutes=570 + 60 * k)
            o = price
            c = price + 0.10
            rows.append((ts, o, max(o, c) + 0.05, min(o, c) - 0.05, c, 1000))
            price = c
    df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low", "Close",
                                     "Volume"])
    return df.set_index("ts")


def equity_sessions(days=EQ_DAYS):
    return {pd.Timestamp(d).date(): 960 for d in days}


def defects(res):
    return [d["defect"] for d in res["structural"]["defects"]] + \
           [d["defect"] for d in res["anomaly"]["defect_bars"]]


def main():
    print(f"checker version: {chk.CHECKER_VERSION}")
    case("V3_C0_version_string",
         chk.CHECKER_VERSION == "checker-v3-candidate-1",
         chk.CHECKER_VERSION)

    # Clean equity control: all lanes pass, floor verdict unchanged.
    res = chk.run_check(equity_frame(), equity_sessions(), [])
    case("V3_C1_clean_control_qualified",
         res["overall"] == "QUALIFIED_CLEAN"
         and res["structural"]["verdict"] == "PASS", str(res["overall"]))

    # STRUCTURAL: duplicate timestamp (v2's set-COUNT was blind).
    df = equity_frame()
    dup = pd.concat([df, df.iloc[[3]]]).sort_index()
    res = chk.run_check(dup, equity_sessions(), [])
    case("V3_C2_duplicate_timestamp_flagged",
         "DUPLICATE_TIMESTAMP" in defects(res)
         and res["completeness_verdict"] == "FAIL", str(defects(res)))

    # STRUCTURAL: naive index.
    df = equity_frame()
    df.index = df.index.tz_localize(None)
    res = chk.run_check(df, equity_sessions(), [])
    case("V3_C3_naive_index_flagged",
         "TZ_NAIVE" in defects(res)
         and res["completeness_verdict"] == "FAIL", str(defects(res)))

    # STRUCTURAL: UTC-stamped equity frame (v2 reported COUNT chaos;
    # v3 names the basis defect).
    df = equity_frame()
    df.index = df.index.tz_convert("UTC")
    res = chk.run_check(df, equity_sessions(), [])
    case("V3_C4_utc_equity_flagged",
         "TZ_NOT_SESSION_ZONE" in defects(res)
         and res["completeness_verdict"] == "FAIL", str(defects(res)))

    # STRUCTURAL: order violation (two adjacent bars swapped).
    df = equity_frame()
    order = list(range(len(df)))
    order[2], order[3] = order[3], order[2]
    res = chk.run_check(df.iloc[order], equity_sessions(), [])
    case("V3_C5_order_violation_flagged",
         "ORDER_VIOLATION" in defects(res)
         and res["completeness_verdict"] == "FAIL", str(defects(res)))

    # OHLC validity: an all-zero flat bar. v2 classified this
    # NO_TRADE_FLAT; v3 (disclosed tightening) calls it a defect.
    df = equity_frame()
    pos = 4
    for col in ("Open", "High", "Low", "Close", "Volume"):
        df.iloc[pos, df.columns.get_loc(col)] = 0
    res = chk.run_check(df, equity_sessions(), [])
    case("V3_C6_zero_price_defect",
         "ZERO_OR_NEGATIVE_PRICE" in defects(res)
         and res["overall"] == "COMPLETENESS_FAIL", str(defects(res)))

    # OHLC validity: High < Low.
    df = equity_frame()
    pos = 4
    df.iloc[pos, df.columns.get_loc("High")] = 90.0
    df.iloc[pos, df.columns.get_loc("Low")] = 95.0
    res = chk.run_check(df, equity_sessions(), [])
    case("V3_C7_high_lt_low_defect",
         "HIGH_LT_LOW" in defects(res), str(defects(res)))

    # OHLC validity: Close above High.
    df = equity_frame()
    pos = 4
    df.iloc[pos, df.columns.get_loc("Close")] = \
        df.iloc[pos]["High"] + 5.0
    res = chk.run_check(df, equity_sessions(), [])
    case("V3_C8_price_out_of_range_defect",
         "PRICE_OUT_OF_RANGE" in defects(res), str(defects(res)))

    # NaN at a declared split boundary: the boundary classifies
    # UNTESTABLE (never v2's silent PRICE_ACTION), the untestable
    # list names it, and the NaN bar itself remains a completeness
    # defect (both facts reported, neither hidden).
    df = equity_frame()
    last_pre = len(df[df.index.normalize() == pd.Timestamp(EQ_DAYS[1], tz=NY)]) \
        + 6  # last bar of day 2
    df.iloc[last_pre, df.columns.get_loc("Close")] = float("nan")
    res = chk.run_check(df, equity_sessions(), [(EQ_DAYS[2], 3.0)])
    step = res["step"]["results"][0]
    case("V3_C9_nan_boundary_untestable",
         step["status"] == "UNTESTABLE_NAN_BOUNDARY"
         and any(u["reason"] == "NAN_AT_SPLIT_BOUNDARY"
                 for u in res["untestable"])
         and "NAN_VALUE" in defects(res),
         str(step) + " " + str(res["untestable"]))

    # Declared boundary outside the span: overall UNTESTABLE with
    # every other lane passing.
    res = chk.run_check(equity_frame(), equity_sessions(),
                        [("2023-12-29", 3.0)])
    case("V3_C10_boundary_outside_span_untestable",
         res["overall"] == "UNTESTABLE"
         and res["completeness_verdict"] == "PASS"
         and res["convention_verdict"] == "PASS", str(res["overall"]))

    # Floor re-proof: TSLA-class zero-volume price-moving bar.
    df = equity_frame()
    df.iloc[4, df.columns.get_loc("Volume")] = 0
    res = chk.run_check(df, equity_sessions(), [])
    case("V3_C11_floor_zero_volume_moving",
         res["overall"] == "COMPLETENESS_FAIL"
         and len(res["anomaly"]["price_moving_zero_volume"]) == 1,
         str(res["overall"]))

    # Floor re-proof (-91): a session in the table with zero rows.
    sess = equity_sessions()
    sess[pd.Timestamp("2024-01-05").date()] = 960
    res = chk.run_check(equity_frame(), sess, [])
    case("V3_C12_floor_missing_session",
         res["overall"] == "COMPLETENESS_FAIL"
         and len(res["count"]["missing_sessions"]) == 1,
         str(res["count"]["missing_sessions"]))

    # Floor re-proof: clean declared split on the adjusted basis
    # (prices continuous, volume scaled by the factor).
    df = equity_frame()
    d3 = df.index.normalize() == pd.Timestamp(EQ_DAYS[2], tz=NY)
    df.loc[d3, "Volume"] = (df.loc[d3, "Volume"] / 3).round()
    res = chk.run_check(df, equity_sessions(), [(EQ_DAYS[2], 3.0)])
    case("V3_C13_floor_clean_declared_split",
         res["overall"] == "QUALIFIED_CLEAN"
         and res["step"]["results"][0]["classification"]
         == "CONTINUOUS_ADJUSTED", str(res["step"]["results"]))

    # ---------------- crypto mode (S-C1…S-C6) ----------------
    c_days = ["2024-01-02", "2024-01-03", "2024-01-04"]

    def crypto_frame(days=c_days, tz=NY):
        rows = []
        price = 100.0
        for d in days:
            day = pd.Timestamp(d, tz=tz)
            if tz != NY:
                day = day.tz_convert(NY).normalize().tz_convert(tz)
            base = pd.Timestamp(d, tz=NY)
            for h in range(24):
                ts = base + pd.Timedelta(hours=h)
                if tz != NY:
                    ts = ts.tz_convert(tz)
                o = price
                c = price + 0.01
                rows.append((ts, o, max(o, c) + 0.005,
                             min(o, c) - 0.005, c, 500))
                price = c
        df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low",
                                         "Close", "Volume"])
        return df.set_index("ts").sort_index()

    c_sess = {pd.Timestamp(d).date(): 1440 for d in c_days}

    res = chk.run_check(crypto_frame(), c_sess, [], instrument="crypto")
    case("V3_K1_crypto_clean",
         res["overall"] == "QUALIFIED_CLEAN", str(res["overall"]))

    # Same series stamped in UTC: ET-date attribution makes the
    # verdict identical.
    res = chk.run_check(crypto_frame(tz="UTC"), c_sess, [],
                        instrument="crypto")
    case("V3_K2_crypto_utc_stamps_attributed_et",
         res["overall"] == "QUALIFIED_CLEAN", str(res["overall"]))

    # One missing hour inside a date.
    df = crypto_frame()
    drop_ts = pd.Timestamp("2024-01-03 05:00", tz=NY)
    res = chk.run_check(df.drop(drop_ts), c_sess, [], instrument="crypto")
    case("V3_K3_crypto_missing_hour",
         res["overall"] == "COMPLETENESS_FAIL"
         and any("2024-01-03 05:00" in m
                 for m in res["count"]["missing_bars"]),
         str(res["count"]["missing_bars"]))

    # A full ET date in the table with zero bars.
    sess = dict(c_sess)
    sess[pd.Timestamp("2024-01-05").date()] = 1440
    res = chk.run_check(crypto_frame(), sess, [], instrument="crypto")
    ms = res["count"]["missing_sessions"]
    case("V3_K4_crypto_missing_date",
         res["overall"] == "COMPLETENESS_FAIL" and len(ms) == 1
         and len(ms[0]["expected_bar_starts"]) == 24, str(ms))

    # Declared splits in crypto mode are a caller error (fail-closed).
    try:
        chk.run_check(crypto_frame(), c_sess, [("2024-01-03", 3.0)],
                      instrument="crypto")
        case("V3_K5_crypto_declared_split_refused", False, "no raise")
    except ValueError as e:
        case("V3_K5_crypto_declared_split_refused",
             "CRYPTO_DECLARED_SPLITS_NOT_APPLICABLE" in str(e), str(e))

    # Duplicate stamp in crypto mode.
    df = crypto_frame()
    dup = pd.concat([df, df.iloc[[10]]]).sort_index()
    res = chk.run_check(dup, c_sess, [], instrument="crypto")
    case("V3_K6_crypto_duplicate_flagged",
         "DUPLICATE_TIMESTAMP" in defects(res)
         and res["completeness_verdict"] == "FAIL", str(defects(res)))

    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"{n_pass}/{len(RESULTS)} checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
