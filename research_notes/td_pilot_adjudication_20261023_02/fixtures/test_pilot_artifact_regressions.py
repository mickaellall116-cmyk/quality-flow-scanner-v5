#!/usr/bin/env python3
"""
test_pilot_artifact_regressions.py — regression fixtures for
QF-TD-PILOT-ADJUDICATION-20261023-02.

Both fixtures are derived from the SHAPES of the artifacts found in
the actual Twelve Data pilot bytes (scanner package
td_pilot_20261023_01; archive qf-data-archive 45496f8). ALL prices
and volumes here are SYNTHETIC, invented for these fixtures — no raw
holdout or vendor values are copied. Dates are used only as
calendar shapes (an early-close date has a 13:00 pinned close; the
April-2024 zero-volume pattern has per-date counts 4/1/6/4/2/2).

F-ZV  zero-volume / nonflat class (the SMCI/HO finding): 19
      price-moving zero-volume bars across 6 sessions are flagged
      by the checker ANOMALY lane on raw AND admitted bytes —
      session admission cannot cure a volume-completeness defect —
      and map to NOT_EVALUABLE_PROVIDER_VOLUME. A zero-volume FLAT
      control bar is NO_TRADE_FLAT, never an anomaly.
F-PH  early-close phantom stub (the DEV-leg finding): a post-close
      15:30 row on a 13:00 early-close session is flagged by COUNT
      as an extra bar on raw bytes and is excluded by the ONE
      generic pinned-session admission rule (membership in the
      expected bar-start set) — in both its observed shapes: flat
      zero-volume (F-PH1) and nonflat nonzero-volume (F-PH2). The
      rule is shape-blind; both variants trip it mechanically.

Instrument: checker candidate-2 (../checker, byte-identical to
research_notes/repair_94_20261022). Admission uses the driver's own
expected_start_set, so the fixture tests the production rule, not a
copy. Fixture spans are short (< 5 sessions per side), so the
VBASIS lane does not evaluate by construction; these fixtures own
the COUNT / ANOMALY / admission behaviour only.
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "checker"))
import tsla_completeness_check as chk  # noqa: E402
import run_actual_byte_check as drv  # noqa: E402

ZONE = "America/New_York"
NORMAL_CLOSE = 16 * 60
EARLY_CLOSE = 13 * 60


def make_session(d, close_min, price, zero_nonflat=(), flat_zero=(),
                 phantom=None, seed_vol=1_000_000):
    """One synthetic session of hourly bars. Returns (rows, price)
    where rows are (Timestamp-naive, O, H, L, C, V) and price is the
    last close (continuity into the next session)."""
    starts = chk._expected_starts(pd.Timestamp(d), close_min)
    rows = []
    for i, ts in enumerate(starts):
        o = price
        c = o * (1.001 if i % 2 == 0 else 0.9995)
        h, l = max(o, c) * 1.001, min(o, c) * 0.999
        v = float(seed_vol + 137 * i)
        if i in zero_nonflat:
            v = 0.0  # range stays nonzero: price-moving, no volume
        if i in flat_zero:
            o = h = l = c = o  # flat AND zero-volume: NO_TRADE_FLAT
            v = 0.0
        rows.append((ts, o, h, l, c, v))
        price = c
    if phantom is not None:
        rows.append(phantom(price))
    return rows, price


def to_frame(rows):
    idx = pd.DatetimeIndex([r[0] for r in rows]).tz_localize(ZONE)
    return pd.DataFrame(
        {"Open": [r[1] for r in rows], "High": [r[2] for r in rows],
         "Low": [r[3] for r in rows], "Close": [r[4] for r in rows],
         "Volume": [r[5] for r in rows]}, index=idx)


def admit(frame, sessions):
    starts = drv.expected_start_set(sessions)
    mask = [ts in starts for ts in frame.index]
    return frame[mask], frame[[not m for m in mask]]


def test_phantom_variants():
    sessions = {date(2024, 11, 27): NORMAL_CLOSE,
                date(2024, 11, 29): EARLY_CLOSE,
                date(2024, 12, 2): NORMAL_CLOSE}
    ec_day = pd.Timestamp(date(2024, 11, 29))
    variants = {
        "F-PH1 flat zero-volume stub":
            lambda p: (ec_day + pd.Timedelta(hours=15, minutes=30),
                       p, p, p, p, 0.0),
        "F-PH2 nonflat nonzero-volume stub":
            lambda p: (ec_day + pd.Timedelta(hours=15, minutes=30),
                       p, p * 1.002, p * 0.998, p * 1.001, 250_000.0),
    }
    for name, phantom in variants.items():
        rows, price = make_session(date(2024, 11, 27), NORMAL_CLOSE, 100.0)
        r2, price = make_session(date(2024, 11, 29), EARLY_CLOSE, price,
                                 phantom=phantom)
        r3, _ = make_session(date(2024, 12, 2), NORMAL_CLOSE, price)
        frame = to_frame(rows + r2 + r3)
        raw = chk.run_check(frame, sessions, [], instrument="equity")
        assert raw["count"]["extra_bars"] == [
            "2024-11-29 15:30:00-05:00"], (name, raw["count"]["extra_bars"])
        assert raw["completeness_verdict"] == "FAIL", name
        admitted, excluded = admit(frame, sessions)
        assert len(excluded) == 1 and len(admitted) == len(frame) - 1, name
        adm = chk.run_check(admitted, sessions, [], instrument="equity")
        assert adm["completeness_verdict"] == "PASS", (name, adm)
        assert adm["count"]["extra_bars"] == [], name
        print(f"PASS {name}: raw COUNT extra = the 15:30 stub; "
              f"admission excluded exactly 1 row; admitted PASS")


def test_zero_volume_nonflat_class():
    # April-2024 shape: per-date zero-volume/nonflat counts
    # 4 / 1 / 6 / 4 / 2 / 2 = 19, plus one flat zero-volume control.
    plan = {date(2024, 4, 8): ({0, 1, 2, 4}, ()),
            date(2024, 4, 9): ({3}, {5}),
            date(2024, 4, 10): ({0, 1, 2, 3, 4, 5}, ()),
            date(2024, 4, 12): ({1, 2, 4, 6}, ()),
            date(2024, 4, 15): ({0, 5}, ()),
            date(2024, 4, 17): ({2, 3}, ())}
    sessions = {d: NORMAL_CLOSE for d in plan}
    rows, price = [], 400.0
    for d in sorted(plan):
        zn, fz = plan[d]
        r, price = make_session(d, NORMAL_CLOSE, price,
                                zero_nonflat=zn, flat_zero=fz)
        rows += r
    frame = to_frame(rows)
    for label, fr in (("raw", frame), ("admitted", admit(frame, sessions)[0])):
        res = chk.run_check(fr, sessions, [], instrument="equity")
        n = len(res["anomaly"]["price_moving_zero_volume"])
        assert n == 19, (label, n)
        assert len(res["anomaly"]["no_trade_flat_zero_volume"]) == 1, label
        assert res["count"]["verdict"] == "PASS", label  # all in-session
        assert res["completeness_verdict"] == "FAIL", label
        classification = ("NOT_EVALUABLE_PROVIDER_VOLUME" if n > 0
                          else "REVIEW_REQUIRED")
        assert classification == "NOT_EVALUABLE_PROVIDER_VOLUME", label
        print(f"PASS F-ZV ({label}): 19 price-moving zero-volume bars "
              f"flagged, 1 flat control = NO_TRADE_FLAT, COUNT PASS, "
              f"classification NOT_EVALUABLE_PROVIDER_VOLUME")


if __name__ == "__main__":
    test_phantom_variants()
    test_zero_volume_nonflat_class()
    print("ALL PILOT-ARTIFACT REGRESSION FIXTURES PASS")
