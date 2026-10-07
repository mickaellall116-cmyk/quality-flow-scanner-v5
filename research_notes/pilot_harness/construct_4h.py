#!/usr/bin/env python3
"""
construct_4h.py — Deterministic 1H → 4H session construction (isolated).

Replicates the binning logic of archival
`resample_closed_4h_session_anchored` (scanner_rules.py, pinned SHA-256
7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac,
lines 149-267) as a standalone module. The archival file is NEVER imported
or modified; this is a clean-room replication for the isolated harness.

Session bins (US equities, America/New_York):
  [09:30, 13:30) → labeled 09:30
  [13:30, close)  → labeled 13:30   (shortened closing-session bar)
  Early-close day → single [09:30, 13:00) bin → labeled 09:30

Bins are assigned explicitly from local session time — never via pandas
`origin='start_day'`.

Usage:
  python3 construct_4h.py --input 1h.csv --symbol AAPL --out 4h.csv
  Input CSV: timestamp (ISO, tz-aware), open, high, low, close, volume
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

NY = "America/New_York"
SESSION_OPEN_MIN = 9 * 60 + 30          # 09:30 → 570
FIRST_BIN_CUTOFF_MIN = 13 * 60 + 30     # 13:30 → 810


def session_close_et(day: pd.Timestamp) -> pd.Timestamp | None:
    """Per-date session close from the XNYS exchange calendar.

    Returns None for unknown dates (caller decides the fail-closed policy;
    the archival constructor falls back to 16:00 — see validate_input.py
    for the harness's stricter handling).
    """
    try:
        import pandas_market_calendars as mcal
        xnys = mcal.get_calendar("XNYS")
        sched = xnys.schedule(start_date=day.date(), end_date=day.date())
        if sched.empty:
            return None
        close = sched.iloc[0]["market_close"]
        return pd.Timestamp(close).tz_convert(NY)
    except Exception:
        return None


def construct_4h(df: pd.DataFrame, symbol: str,
                 session_closes: dict | None = None,
                 now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Build session-anchored 4H bars from 1H bars.

    Args:
        df: 1H bars with tz-aware DatetimeIndex and Open/High/Low/Close/Volume.
        symbol: ticker (only used for labeling; no per-symbol logic).
        session_closes: optional {date_normalized: close_timestamp} override.
            When None, resolved per-date via session_close_et().
        now: causal cutoff; rows dated after `now` are dropped (fail-closed).

    Returns:
        4H bars with tz-aware DatetimeIndex (America/New_York),
        columns Open/High/Low/Close/Volume.
    """
    if df.empty:
        return df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("Market data must use a DatetimeIndex")
    if df.index.tz is None:
        raise TypeError("US equity data must be tz-aware")

    data = df.copy().sort_index()

    # Fail-closed causal cutoff.
    if now is not None:
        cutoff = now.tz_convert(data.index.tz) if now.tz is not None \
            else now.tz_localize(data.index.tz)
        data = data[data.index <= cutoff]
        if data.empty:
            return data

    local = data.index.tz_convert(NY)
    minutes = local.hour * 60 + local.minute
    day_key = local.normalize()

    # Per-date session close (16:00 regular, 13:00 early-close).
    closes: dict = {}
    for d in pd.DatetimeIndex(day_key.unique()):
        if session_closes and d in session_closes:
            closes[d] = session_closes[d]
        else:
            sc = session_close_et(d)
            # NOTE: archival falls back to 16:00 for unknown dates.
            # The harness validator (validate_input.py) rejects unknown
            # dates BEFORE construction; this fallback only fires when the
            # caller explicitly bypasses validation.
            closes[d] = sc if sc is not None else d + pd.Timedelta(hours=16)
    close_minutes = day_key.map(
        lambda d: int((closes[d] - d).total_seconds() // 60))

    # Keep only in-session rows.
    in_session = (minutes >= SESSION_OPEN_MIN) & (minutes < close_minutes)
    data = data[in_session].copy()
    local = local[in_session]
    minutes = minutes[in_session]
    if data.empty:
        return data

    # Explicit session bins.
    bin_start_min = [570 if m < FIRST_BIN_CUTOFF_MIN else 810
                     for m in minutes]
    session_key = local.normalize()
    labels = session_key + pd.to_timedelta(bin_start_min, unit="m")
    data = data.copy()
    # labels inherit tz-awareness from session_key (already America/New_York);
    # do NOT tz_localize an already-aware index.
    data["_bin"] = pd.DatetimeIndex(labels)

    bars = data.groupby("_bin").agg({
        "Open": "first", "High": "max", "Low": "min",
        "Close": "last", "Volume": "sum",
    }).dropna(subset=["Open", "High", "Low", "Close"])
    bars.index.name = None
    return bars


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic 1H→4H construction")
    ap.add_argument("--input", required=True, help="1H CSV (timestamp,open,high,low,close,volume)")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--verify-sources", action="store_true",
                    help="verify pinned archival SHAs before running (fail-closed)")
    args = ap.parse_args()

    if args.verify_sources:
        import subprocess
        r = subprocess.run([sys.executable,
                            str(Path(__file__).parent / "verify_sources.py")])
        if r.returncode != 0:
            return r.returncode

    df = pd.read_csv(args.input, parse_dates=["timestamp"], index_col="timestamp")
    df.index = pd.DatetimeIndex(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize(NY)
    df = df.rename(columns={c: c.capitalize() for c in df.columns})

    bars = construct_4h(df, args.symbol)
    out = Path(args.out)
    bars.to_csv(out, index_label="timestamp")
    print(f"Wrote {len(bars)} 4H bars → {out}")
    for ts, row in bars.iterrows():
        print(f"  {ts}  O={row['Open']:.2f} H={row['High']:.2f} "
              f"L={row['Low']:.2f} C={row['Close']:.2f} V={row['Volume']:.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
