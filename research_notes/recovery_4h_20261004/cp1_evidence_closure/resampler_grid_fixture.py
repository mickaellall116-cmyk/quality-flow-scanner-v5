"""Synthetic fixture: the real timezone/DST/window mechanism behind the two
4H label sets (08:30/12:30 EST cache labels vs 06:30/10:30/14:30 EDT live labels).

Run:  python3 resampler_grid_fixture.py
Requires: pandas, numpy, and scanner_rules.py importable (repo root on sys.path).

What this demonstrates (using the UNCHANGED legacy resample_closed_4h):
  1. PHASE INVARIANCE: changing the first download DATE (within the same DST
     regime) does NOT shift the 4-hour grid phase. One day = six 4-hour periods,
     so a UTC-midnight anchor is date-invariant. (ChatGPT's correction holds.)
  2. THE REAL MECHANISM: pandas `origin='start_day'` anchors to midnight in the
     INDEX'S TIMEZONE -- America/New_York for yfinance 1H data -- NOT midnight
     UTC. Midnight EST = 05:00 UTC; midnight EDT = 04:00 UTC. The anchor's UTC
     value therefore depends on the FIRST DAY'S DST REGIME, shifting the
     UTC-fixed grid by 1 hour:
       - first 1H day in EDT -> origin 04:00 UTC -> +9h30m -> 13:30 UTC grid
       - first 1H day in EST -> origin 05:00 UTC -> +9h30m -> 14:30 UTC grid
  3. SET A (cache): 13:30/17:30 UTC grid. In EST the session bins label
     08:30/12:30. (In EDT the same grid labels 09:30/13:30 -- correct by luck.)
  4. SET B (live): 14:30/18:30/22:30 UTC grid. In EDT the bins fall at
     06:30/10:30/14:30/18:30 local, so regular-session 1H data yields THREE
     bars per day (06:30, 10:30, 14:30) instead of two.

The fixture uses synthetic tz-aware America/New_York 1H data (no market data
downloaded, no network). All assertions are deterministic.
"""

import os
import sys

import numpy as np
import pandas as pd

# Fixture lives in research_notes/recovery_4h_20261004/cp1_evidence_closure/;
# repo root (scanner_rules.py) is three levels up.
REPO_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", ".."))
sys.path.insert(0, REPO_ROOT)

from scanner_rules import resample_closed_4h  # noqa: E402  (legacy, unchanged)


def make_1h_et(start_date: str, days: int) -> pd.DataFrame:
    """Synthetic 1H bars, 09:30-16:00 ET session, tz-aware America/New_York."""
    idx = []
    d = pd.Timestamp(start_date)
    i, added = 0, 0
    while added < days:
        day = d + pd.Timedelta(days=i)
        i += 1
        if day.weekday() >= 5:
            continue
        for h, m in [(9, 30), (10, 0), (11, 0), (12, 0), (13, 0), (14, 0), (15, 0)]:
            idx.append(pd.Timestamp(day.date()) + pd.Timedelta(hours=h, minutes=m))
        added += 1
    idx = pd.DatetimeIndex(idx).tz_localize("America/New_York")
    n = len(idx)
    return pd.DataFrame(
        {"Open": 100.0, "High": 101.0, "Low": 99.0,
         "Close": 100.5, "Volume": 1000},
        index=idx,
    )


NOW = pd.Timestamp("2026-12-01", tz="America/New_York")  # past all fixture data


def utc_grid(bars: pd.DataFrame):
    return sorted({t.tz_convert("UTC").strftime("%H:%M") for t in bars.index})


def et_labels(bars: pd.DataFrame):
    return [t.tz_convert("America/New_York").strftime("%m-%d %H:%M")
            for t in bars.index]


def check(name: str, cond: bool):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        raise SystemExit(f"fixture assertion failed: {name}")


def main() -> None:
    # --- 1. Phase invariance: same DST regime, different first dates -> same grid
    grids = set()
    for start in ("2026-09-15", "2026-09-22", "2026-10-01"):  # all EDT
        bars = resample_closed_4h(make_1h_et(start, 5), "TEST", now=NOW)
        grids.add(tuple(utc_grid(bars)))
    check("phase invariance across first dates (EDT regime)", len(grids) == 1)

    # --- 2. Anchor depends on first day's DST regime (ET-midnight, not UTC-midnight)
    bars_edt = resample_closed_4h(make_1h_et("2026-09-15", 5), "TEST", now=NOW)
    bars_est = resample_closed_4h(make_1h_et("2026-01-15", 5), "TEST", now=NOW)
    g_edt, g_est = utc_grid(bars_edt), utc_grid(bars_est)
    print(f"  EDT-anchored UTC grid: {g_edt}")
    print(f"  EST-anchored UTC grid: {g_est}")

    def grid_phase(g):
        # Grid phase mod 4h, in minutes past the hour, from the first bin.
        h, m = g[0].split(":")
        return (int(h) * 60 + int(m)) % 240

    check("EDT-anchored grid is 13:30/17:30 UTC",
          g_edt == ["13:30", "17:30"])
    check("EST-anchored grid is on the 14:30+4k UTC grid "
          "(14:30/18:30 observed; 10:30/22:30 bins have no session data in EST)",
          grid_phase(g_est) == grid_phase(["14:30"]) and
          all(t in ("10:30", "14:30", "18:30", "22:30", "02:30", "06:30") for t in g_est))
    check("grids differ by 1h (DST-regime anchor shift)",
          grid_phase(g_est) == (grid_phase(g_edt) + 60) % 240)

    # --- 3. SET A: EDT-anchored grid viewed in EST -> 08:30/12:30 labels
    df_a = make_1h_et("2024-09-16", 70)  # crosses 2024-11-03 fall-back
    bars_a = resample_closed_4h(df_a, "TEST", now=NOW)
    lab_a = et_labels(bars_a)
    # Clean EST dates only (Nov 3+; Nov 1 is the fall-back transition day).
    nov = sorted({l[6:] for l in lab_a
                  if l.startswith("11-") and int(l[3:5]) >= 3})
    print(f"  SET A Nov (EST) label times: {nov}")
    check("SET A: EST-regime labels are 08:30/12:30", nov == ["08:30", "12:30"])
    check("SET A: UTC grid is 13:30/17:30 (matches byte_identity_report)",
          utc_grid(bars_a) == ["13:30", "17:30"])

    # --- 4. SET B: EST-anchored grid viewed in EDT -> 06:30/10:30/14:30 labels
    df_b = make_1h_et("2026-01-15", 200)  # crosses 2026-03-08 spring-forward
    bars_b = resample_closed_4h(df_b, "TEST", now=NOW)
    lab_b = et_labels(bars_b)
    sep = sorted({l[6:] for l in lab_b if l.startswith("09-")})
    print(f"  SET B Sep (EDT) label times: {sep}")
    check("SET B: EDT-regime labels are 06:30/10:30/14:30", sep == ["06:30", "10:30", "14:30"])
    # three bars per day: the 06:30 bin catches 09:30-10:30 session data
    sep_days = {}
    for l in lab_b:
        if l.startswith("09-"):
            sep_days.setdefault(l[:5], []).append(l[6:])
    check("SET B: three session bars per day in EDT",
          all(v == ["06:30", "10:30", "14:30"] for v in list(sep_days.values())[:3]))

    print("\nAll fixture assertions passed.")
    print("Mechanism: origin='start_day' = midnight America/New_York of the first")
    print("1H day (05:00 UTC in EST, 04:00 UTC in EDT); +9h30m offset fixes the")
    print("UTC grid; DST then moves the ET labels. The live 06:30 grid is the")
    print("EST-anchored 14:30 UTC grid seen in EDT -- reproduced here without")
    print("any market-data download.")


if __name__ == "__main__":
    main()
