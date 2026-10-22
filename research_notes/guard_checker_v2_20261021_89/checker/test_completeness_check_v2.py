#!/usr/bin/env python3
"""
test_completeness_check_v2.py — SYNTHETIC FIXTURES for the checker v2
candidate (task -89; design -86 F4), extending -82's 14-case suite.

Structure:
  FLOOR — -82's test_tsla_completeness_check.py (byte-copy in this
          directory, sha256 47578946…) is executed UNCHANGED as a
          subprocess. Because this directory's
          tsla_completeness_check.py IS the v2 candidate, the floor's
          14 cases run against v2.
          FINDING (root-caused at this build, disclosed in
          ../TEST_EVIDENCE.md): the floor reads 10/14 under v2, and
          all four divergences trace to ONE property of the -82
          fixture itself — its builder divides the raw path by the
          split factor at the first bar of EVERY post-split session
          (`if not pre and k == 0`), so the 'clean' series embeds a
          SECOND undeclared 3:1-shaped overnight step at
          2024-06-13 (measured: steps 1.000000 / 1.000000 /
          0.333333). V1 had no lane that could see it; v2's STEP-ALL
          sees it and fires — as designed. No v1 lane regresses:
          the floor's COUNT / ANOMALY / declared-STEP assertions all
          still pass, and the FI scenarios below reproduce all five
          -82 intents exactly on a corrected builder (split applied
          once, at its effective date only).
  FI-A..E — the five -82 scenario INTENTS (clean / zero-volume
          completeness defect / mixed basis / flat no-trade bars /
          missing bar) rebuilt on this suite's corrected builder,
          asserting the same outcomes -82 asserted, lane separation
          included.
  C15  one NaN-volume price-moving bar -> COMPLETENESS_FAIL
       (NAN_VALUE defect; convention lane untouched).
  C16  one negative-volume bar -> COMPLETENESS_FAIL.
  C17  one 1-share price-moving bar -> COMPLETENESS_FAIL; and a
       1-share FLAT bar stays NO_TRADE_FLAT (overall stays clean).
  C18  volume scale x3 step mid-series, prices continuous, no
       declared split -> CONVENTION_BREAK_SUSPECT via VBASIS; the
       price lanes (STEP / STEP-ALL) stay clean.
  C19  undeclared 3:1-shaped overnight price step ->
       CONVENTION_BREAK_SUSPECT via STEP-ALL; completeness PASS.
  C20  declared 3:1 boundary + a genuine +60% overnight gap ->
       QUALIFIED_CLEAN, NO convention flag (the false-flag guard;
       boundary classified PRICE_ACTION).
  C21  declared boundary, volume step = declared factor ->
       SCALED_BY_FACTOR note, no fail.
  C22  declared boundary, volume step ~ 1 with adjusted prices ->
       UNSCALED note, no fail.

All bars are synthetic fixture arithmetic. No real symbol data is
used; no -75 snapshot is read (that re-analysis belongs to GO G4,
not to this package).
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from tsla_completeness_check import run_check  # noqa: E402  (the v2 candidate)

NY = "America/New_York"
JUNE_DAYS = ["2024-06-10", "2024-06-11", "2024-06-12", "2024-06-13"]
SPLIT = [(pd.Timestamp("2024-06-12").date(), 3.0)]  # 3:1, effective 06-12
JUNE_SESSIONS = {pd.Timestamp(d).date(): 16 * 60 for d in JUNE_DAYS}

TEN_DAYS = ["2024-06-03", "2024-06-04", "2024-06-05", "2024-06-06",
            "2024-06-07", "2024-06-10", "2024-06-11", "2024-06-12",
            "2024-06-13", "2024-06-14"]
TEN_SESSIONS = {pd.Timestamp(d).date(): 16 * 60 for d in TEN_DAYS}


def build_series(days, split=None, price_basis="adjusted",
                 volume_basis="scaled", jump=None, volume_step=None,
                 flat_volumes=False, defects=()):
    """Synthetic series in the -82 fixture arithmetic: raw price path
    starts 300.00 and drifts +0.1% per bar; a declared split divides
    the raw level at its effective date. Presentation bases:
      price_basis  'adjusted': pre-split prices / factor (uniform);
                   'mixed':    pre-split prices left RAW (the defect).
      volume_basis 'scaled':   pre-split volumes x factor;
                   'unscaled': pre-split volumes x 1.
      jump         (date_str, mult): presented prices multiplied by
                   mult from that date on (a genuine overnight gap —
                   or, with split=None, an undeclared factor-shaped
                   step, by choice of mult).
      volume_step  (date_str, mult): presented volumes multiplied by
                   mult from that date on (a volume-basis step).
      flat_volumes: every bar's raw volume is 1000 (C18 arithmetic).
      defects      [(ts, kind)]: 'nan_vol' | 'neg_vol' |
                   'one_share_moving' | 'one_share_flat' | 'zero_vol' |
                   'flat_zero', applied last.
    """
    eff_s, factor = ((str(split[0]), float(split[1])) if split
                     else (None, 1.0))
    jump_s, jump_m = (jump if jump else (None, 1.0))
    vstep_s, vstep_m = (volume_step if volume_step else (None, 1.0))
    rows = []
    raw = 300.00
    for day_s in days:
        day = pd.Timestamp(day_s, tz=NY)
        pre = eff_s is not None and day_s < eff_s
        for k in range(7):  # full session: 09:30..15:30
            ts = day + pd.Timedelta(minutes=570 + 60 * k)
            if day_s == eff_s and k == 0 and rows:
                raw = raw / factor  # split takes effect at the boundary
            o, c = raw, raw * 1.001
            h, l = c * 1.0005, o * 0.9995
            v = 1000 if flat_volumes else 1000 + 10 * k
            po, pc, ph, pl = o, c, h, l
            if pre:
                if price_basis == "adjusted":
                    po, pc, ph, pl = o / factor, c / factor, h / factor, l / factor
                pv = v * factor if volume_basis == "scaled" else v
            else:
                pv = v
            if jump_s is not None and day_s >= jump_s:
                po, pc, ph, pl = po * jump_m, pc * jump_m, ph * jump_m, pl * jump_m
            if vstep_s is not None and day_s >= vstep_s:
                pv = pv * vstep_m
            rows.append((ts, po, ph, pl, pc, pv))
            raw = c
    df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low", "Close",
                                     "Volume"])
    df = df.set_index("ts")
    for ts, kind in defects:
        if kind == "nan_vol":
            df.loc[ts, "Volume"] = float("nan")
        elif kind == "neg_vol":
            df.loc[ts, "Volume"] = -50
        elif kind == "one_share_moving":
            df.loc[ts, "Volume"] = 1
        elif kind == "one_share_flat":
            px = df.loc[ts, "Open"]
            df.loc[ts, ["Open", "High", "Low", "Close", "Volume"]] = \
                [px, px, px, px, 1]
        elif kind == "zero_vol":
            df.loc[ts, "Volume"] = 0
        elif kind == "flat_zero":
            px = df.loc[ts, "Open"]
            df.loc[ts, ["Open", "High", "Low", "Close", "Volume"]] = \
                [px, px, px, px, 0]
    return df


RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


DEFECT_TS = pd.Timestamp("2024-06-11 10:30", tz=NY)


def main():
    # ---- FLOOR: -82's 14 cases, unchanged, against the v2 module.
    # Expected result is the PINNED DIVERGENCE documented in the
    # module docstring: 10/14, with exactly four FAILs, all tracing
    # to the second undeclared 3:1-shaped step the -82 fixture
    # builder embeds at 2024-06-13 (STEP-ALL working as designed).
    floor = subprocess.run(
        [sys.executable, str(HERE / "test_tsla_completeness_check.py")],
        cwd=str(HERE), capture_output=True, text=True)
    sys.stdout.write(floor.stdout)
    if floor.returncode != 0:
        sys.stdout.write(floor.stderr)
    fail_lines = [ln for ln in floor.stdout.splitlines()
                  if ln.startswith("FAIL")]
    case("V2_floor_reads_10_of_14",
         floor.returncode == 1 and "10/14 checks passed" in floor.stdout,
         f"rc={floor.returncode}")
    case("V2_floor_divergences_exactly_the_documented_four",
         len(fail_lines) == 4
         and any("A_clean_overall" in ln for ln in fail_lines)
         and any("B_overall_completeness_fail" in ln for ln in fail_lines)
         and any("B_convention_lane_untouched" in ln for ln in fail_lines)
         and any("D_overall_still_clean" in ln for ln in fail_lines),
         f"floor FAILs: {fail_lines}")
    case("V2_floor_v1_lanes_survive",
         "PASS  A_clean_step" in floor.stdout
         and "PASS  C_overall_convention_suspect" in floor.stdout
         and "PASS  E_missing_bar_count_fail" in floor.stdout)

    # ---- FI: the five -82 intents on the corrected builder
    # FI-A clean uniform adjustment -> QUALIFIED_CLEAN, all lanes PASS
    r = run_check(build_series(JUNE_DAYS, split=SPLIT[0]),
                  JUNE_SESSIONS, SPLIT)
    case("FI_A_clean_overall", r["overall"] == "QUALIFIED_CLEAN", r["overall"])
    case("FI_A_lanes_pass",
         r["count"]["verdict"] == "PASS" and r["anomaly"]["verdict"] == "PASS"
         and r["step"]["verdict"] == "PASS")
    # FI-B zero-volume price-moving bars -> completeness ONLY
    zv = [(pd.Timestamp("2024-06-10", tz=NY) + pd.Timedelta(minutes=570 + 60 * k),
           "zero_vol") for k in range(5)]
    r = run_check(build_series(JUNE_DAYS, split=SPLIT[0], defects=zv),
                  JUNE_SESSIONS, SPLIT)
    case("FI_B_overall_completeness_fail",
         r["overall"] == "COMPLETENESS_FAIL", r["overall"])
    case("FI_B_anomaly_count_is_5",
         len(r["anomaly"]["price_moving_zero_volume"]) == 5)
    case("FI_B_convention_lane_untouched", r["convention_verdict"] == "PASS")
    case("FI_B_count_lane_pass", r["count"]["verdict"] == "PASS")
    # FI-C mixed basis -> convention ONLY
    r = run_check(build_series(JUNE_DAYS, split=SPLIT[0],
                               price_basis="mixed"),
                  JUNE_SESSIONS, SPLIT)
    case("FI_C_overall_convention_suspect",
         r["overall"] == "CONVENTION_BREAK_SUSPECT", r["overall"])
    case("FI_C_step_observed_near_reciprocal_factor",
         abs(r["step"]["results"][0]["observed_step"] - 1 / 3.0) < 0.02,
         str(r["step"]["results"][0]["observed_step"]))
    case("FI_C_completeness_lane_untouched",
         r["completeness_verdict"] == "PASS")
    # FI-D flat zero-volume bars -> no-trade facts, still clean
    fz = [(pd.Timestamp("2024-06-11 11:30", tz=NY), "flat_zero"),
          (pd.Timestamp("2024-06-11 12:30", tz=NY), "flat_zero")]
    r = run_check(build_series(JUNE_DAYS, split=SPLIT[0], defects=fz),
                  JUNE_SESSIONS, SPLIT)
    case("FI_D_overall_still_clean",
         r["overall"] == "QUALIFIED_CLEAN", r["overall"])
    case("FI_D_flat_classified_separately",
         len(r["anomaly"]["no_trade_flat_zero_volume"]) == 2
         and len(r["anomaly"]["price_moving_zero_volume"]) == 0)
    # FI-E a missing bar -> COUNT fails on exactly that bar
    df = build_series(JUNE_DAYS, split=SPLIT[0]).drop(
        pd.Timestamp("2024-06-11 11:30", tz=NY))
    r = run_check(df, JUNE_SESSIONS, SPLIT)
    case("FI_E_missing_bar_count_fail",
         r["count"]["verdict"] == "FAIL"
         and len(r["count"]["missing_bars"]) == 1,
         str(r["count"]["missing_bars"]))

    # ---- C15: NaN volume on a price-moving bar
    r = run_check(build_series(JUNE_DAYS, split=SPLIT[0],
                               defects=[(DEFECT_TS, "nan_vol")]),
                  JUNE_SESSIONS, SPLIT)
    case("C15_nan_volume_completeness_fail",
         r["overall"] == "COMPLETENESS_FAIL", r["overall"])
    case("C15_nan_defect_recorded",
         len(r["anomaly"]["defect_bars"]) == 1
         and r["anomaly"]["defect_bars"][0]["defect"] == "NAN_VALUE",
         str(r["anomaly"]["defect_bars"]))
    case("C15_convention_lane_untouched",
         r["convention_verdict"] == "PASS", r["convention_verdict"])

    # ---- C16: negative volume
    r = run_check(build_series(JUNE_DAYS, split=SPLIT[0],
                               defects=[(DEFECT_TS, "neg_vol")]),
                  JUNE_SESSIONS, SPLIT)
    case("C16_negative_volume_completeness_fail",
         r["overall"] == "COMPLETENESS_FAIL", r["overall"])
    case("C16_negative_defect_recorded",
         len(r["anomaly"]["defect_bars"]) == 1
         and r["anomaly"]["defect_bars"][0]["defect"] == "NEGATIVE_VOLUME",
         str(r["anomaly"]["defect_bars"]))

    # ---- C17: 1-share bars — moving fails, flat is a no-trade fact
    r = run_check(build_series(JUNE_DAYS, split=SPLIT[0],
                               defects=[(DEFECT_TS, "one_share_moving")]),
                  JUNE_SESSIONS, SPLIT)
    case("C17_one_share_moving_completeness_fail",
         r["overall"] == "COMPLETENESS_FAIL", r["overall"])
    case("C17_one_share_defect_recorded",
         len(r["anomaly"]["defect_bars"]) == 1
         and r["anomaly"]["defect_bars"][0]["defect"]
         == "SUB_PLAUSIBLE_VOLUME_PRICE_MOVING",
         str(r["anomaly"]["defect_bars"]))
    r = run_check(build_series(JUNE_DAYS, split=SPLIT[0],
                               defects=[(DEFECT_TS, "one_share_flat")]),
                  JUNE_SESSIONS, SPLIT)
    case("C17_one_share_flat_stays_clean",
         r["overall"] == "QUALIFIED_CLEAN", r["overall"])
    case("C17_one_share_flat_classified_no_trade",
         str(DEFECT_TS) in r["anomaly"]["no_trade_flat_zero_volume"]
         and not r["anomaly"]["defect_bars"],
         f"flat={r['anomaly']['no_trade_flat_zero_volume']}")

    # ---- C18: volume-basis step, prices continuous, nothing declared
    df = build_series(TEN_DAYS, flat_volumes=True,
                      volume_step=("2024-06-10", 3.0))
    r = run_check(df, TEN_SESSIONS, [])
    case("C18_vbasis_overall_suspect",
         r["overall"] == "CONVENTION_BREAK_SUSPECT", r["overall"])
    case("C18_vbasis_lane_fires", r["vbasis"]["verdict"]
         == "CONVENTION_BREAK_SUSPECT", str(r["vbasis"]["results"]))
    case("C18_price_lanes_clean",
         r["step"]["verdict"] == "PASS" and r["step_all"]["verdict"] == "PASS")
    case("C18_completeness_clean", r["completeness_verdict"] == "PASS")

    # ---- C19: undeclared factor-shaped price step
    df = build_series(JUNE_DAYS, jump=("2024-06-12", 1.0 / 3.0))
    r = run_check(df, JUNE_SESSIONS, [])
    case("C19_step_all_overall_suspect",
         r["overall"] == "CONVENTION_BREAK_SUSPECT", r["overall"])
    case("C19_step_all_lane_fires",
         r["step_all"]["verdict"] == "CONVENTION_BREAK_SUSPECT"
         and abs(r["step_all"]["results"][0]["observed_step"] - 1 / 3.0) < 0.02
         and abs(r["step_all"]["results"][0]["matched_anchor"] - 1 / 3.0) < 0.01,
         str(r["step_all"]["results"]))
    case("C19_completeness_clean", r["completeness_verdict"] == "PASS")

    # ---- C20: declared boundary + genuine +60% gap -> NO flag
    df = build_series(JUNE_DAYS, split=SPLIT[0], jump=("2024-06-12", 1.6))
    r = run_check(df, JUNE_SESSIONS, SPLIT)
    case("C20_declared_gap_stays_clean",
         r["overall"] == "QUALIFIED_CLEAN", r["overall"])
    case("C20_boundary_classified_price_action",
         r["step"]["results"][0]["classification"] == "PRICE_ACTION"
         and abs(r["step"]["results"][0]["observed_step"] - 1.6) < 0.02,
         str(r["step"]["results"]))
    case("C20_no_convention_flag", r["convention_verdict"] == "PASS")

    # ---- C21: declared boundary, volume step = factor -> SCALED note
    r = run_check(build_series(JUNE_DAYS, split=SPLIT[0]),
                  JUNE_SESSIONS, SPLIT)
    case("C21_scaled_by_factor_note",
         r["volume_notes"][0]["note"] == "SCALED_BY_FACTOR"
         and abs(r["volume_notes"][0]["observed_pre_post_ratio"] - 3.0) < 0.01,
         str(r["volume_notes"]))
    case("C21_no_fail", r["overall"] == "QUALIFIED_CLEAN", r["overall"])

    # ---- C22: declared boundary, volumes unscaled -> UNSCALED note
    r = run_check(build_series(JUNE_DAYS, split=SPLIT[0],
                               volume_basis="unscaled"),
                  JUNE_SESSIONS, SPLIT)
    case("C22_unscaled_note",
         r["volume_notes"][0]["note"] == "UNSCALED"
         and abs(r["volume_notes"][0]["observed_pre_post_ratio"] - 1.0) < 0.01,
         str(r["volume_notes"]))
    case("C22_no_fail", r["overall"] == "QUALIFIED_CLEAN", r["overall"])

    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"\n{n_pass}/{len(RESULTS)} checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
