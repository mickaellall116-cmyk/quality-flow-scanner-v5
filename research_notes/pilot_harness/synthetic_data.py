#!/usr/bin/env python3
"""
synthetic_data.py — Synthetic 1H bar generator for harness tests.

Generates deterministic synthetic 1H bars (seeded RNG) for the edge cases
the validator and constructor must handle:

  regular      : normal 09:30–16:00 session (7 bars, 15:30 partial)
  earlyclose   : 2025-11-28 (Fri after Thanksgiving), 09:30–13:00 (4 bars)
  holiday      : 2026-07-03 (July 4 observed) — zero bars expected
  dst_spring   : week of 2026-03-09 (DST began Sun 03-08)
  dst_fall     : week of 2025-11-03 (DST ended Sun 11-02)
  straddle_bad : a bar whose [start,end) crosses the 13:30 bin boundary
                 (validator must REJECT)
  closeday_bad : bars emitted on a holiday (validator must REJECT)
  gap_bad      : a regular day with one 1H constituent missing
                 (validator must REJECT — gaps observable, not filled)

All timestamps America/New_York. Prices are a seeded random walk — values
are irrelevant; structure is what matters.

Usage:
  python3 synthetic_data.py --case regular --out tests/fixtures/synth_regular.csv
  python3 synthetic_data.py --all --dir tests/fixtures/
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

NY = "America/New_York"
SEED = 20261007


def _walk(n: int, start: float = 100.0, seed: int = SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.001, 0.01, n)
    return start * np.exp(np.cumsum(rets))


def _bars(starts: list[pd.Timestamp], seed: int = SEED) -> pd.DataFrame:
    closes = _walk(len(starts), seed=seed)
    opens = np.concatenate([[closes[0] * 0.999], closes[:-1]])
    highs = np.maximum(opens, closes) * 1.003
    lows = np.minimum(opens, closes) * 0.997
    vols = np.random.default_rng(seed + 1).integers(100_000, 900_000, len(starts))
    df = pd.DataFrame({
        "timestamp": pd.DatetimeIndex(starts).tz_convert(NY),
        "open": np.round(opens, 2), "high": np.round(highs, 2),
        "low": np.round(lows, 2), "close": np.round(closes, 2),
        "volume": vols,
    })
    return df


def session_starts(day: str, open_hm: str = "09:30", close_hm: str = "16:00"):
    d = pd.Timestamp(day).tz_localize(NY)
    o = d + pd.Timedelta(hours=int(open_hm[:2]), minutes=int(open_hm[3:]))
    c = d + pd.Timedelta(hours=int(close_hm[:2]), minutes=int(close_hm[3:]))
    out, t = [], o
    while t < c:
        out.append(t)
        t += pd.Timedelta(hours=1)
    return out


def gen_case(case: str) -> pd.DataFrame:
    if case == "regular":
        return _bars(session_starts("2026-09-08"))
    if case == "earlyclose":
        # 2025-11-28: day after Thanksgiving, 13:00 close
        return _bars(session_starts("2025-11-28", close_hm="13:00"), seed=SEED + 1)
    if case == "holiday":
        # 2026-07-03: full holiday — zero bars
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    if case == "dst_spring":
        frames = [_bars(session_starts(d), seed=SEED + i)
                  for i, d in enumerate(["2026-03-09", "2026-03-10", "2026-03-11",
                                         "2026-03-12", "2026-03-13"])]
        return pd.concat(frames, ignore_index=True)
    if case == "dst_fall":
        frames = [_bars(session_starts(d), seed=SEED + 10 + i)
                  for i, d in enumerate(["2025-11-03", "2025-11-04", "2025-11-05",
                                         "2025-11-06", "2025-11-07"])]
        return pd.concat(frames, ignore_index=True)
    if case == "straddle_bad":
        # A 1H bar labeled 13:00 whose interval [13:00,14:00) crosses the
        # 13:30 bin boundary — validator must reject (V3).
        df = _bars(session_starts("2026-09-08"))
        bad_ts = pd.Timestamp("2026-09-08 13:00").tz_localize(NY)
        df.loc[len(df)] = [bad_ts, 100.0, 101.0, 99.0, 100.5, 500_000]
        return df.sort_values("timestamp").reset_index(drop=True)
    if case == "closeday_bad":
        # Bars on 2026-07-03 (full holiday) — validator must reject (V4).
        return _bars(session_starts("2026-07-03"), seed=SEED + 2)
    if case == "gap_bad":
        # Regular day minus the 11:30 bar — validator must reject (V6).
        df = _bars(session_starts("2026-09-08"))
        drop_ts = pd.Timestamp("2026-09-08 11:30").tz_localize(NY)
        return df[df["timestamp"] != drop_ts].reset_index(drop=True)
    if case == "intervalend_bad":
        # Regular day with a vendor interval_end column whose every end is
        # two hours AFTER the bar start — validator must reject (V9).
        # ChatGPT 6037842097 probe: v1 ignored this column entirely.
        df = _bars(session_starts("2026-09-08"))
        df["interval_end"] = df["timestamp"] + pd.Timedelta(hours=2)
        return df
    if case == "naive":
        # Tz-naive timestamps — entrypoint must refuse silent localization.
        df = _bars(session_starts("2026-09-08"))
        df["timestamp"] = pd.DatetimeIndex(df["timestamp"]).tz_localize(None)
        return df
    if case == "partial_1030":
        # Causally-partial capture: only the 09:30 bar, whose interval
        # [09:30,10:30) has closed as of 10:30. For as_of=10:00 the only
        # causally-valid input is EMPTY (no 1H bar has closed yet).
        df = _bars(session_starts("2026-09-08"))
        keep = pd.Timestamp("2026-09-08 09:30").tz_localize(NY)
        return df[df["timestamp"] == keep].reset_index(drop=True)
    if case == "partial_1330":
        # Bars 09:30–12:30 (intervals closed as of 13:30). First 4H bin
        # [09:30,13:30) closes exactly at 13:30 → one completed bin.
        df = _bars(session_starts("2026-09-08"))
        cutoff = pd.Timestamp("2026-09-08 12:30").tz_localize(NY)
        return df[df["timestamp"] <= cutoff].reset_index(drop=True)
    raise ValueError(f"unknown case: {case}")


CASES = ["regular", "earlyclose", "holiday", "dst_spring", "dst_fall",
         "straddle_bad", "closeday_bad", "gap_bad",
         "intervalend_bad", "naive", "partial_1030", "partial_1330"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Synthetic 1H generator")
    ap.add_argument("--case", choices=CASES)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--dir", default="tests/fixtures")
    args = ap.parse_args()

    if args.all:
        d = Path(args.dir)
        d.mkdir(parents=True, exist_ok=True)
        for c in CASES:
            df = gen_case(c)
            p = d / f"synth_{c}.csv"
            df.to_csv(p, index=False)
            print(f"{c:12} → {p} ({len(df)} bars)")
        return 0

    if not args.case:
        ap.error("--case or --all required")
    df = gen_case(args.case)
    if args.out:
        df.to_csv(args.out, index=False)
        print(f"Wrote {len(df)} bars → {args.out}")
    else:
        print(df.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
