#!/usr/bin/env python3
"""
common.py — QF-EQUITY43-S1-G4-VBASIS-DECISION-PACKET-20261024-20

Shared pinned-input loading. Semantics copied from the -02 actual-byte
runner (research_notes/td_pilot_adjudication_20261023_02/run_actual_byte_check.py,
commit 7823538): the pinned session table is hash-refused on mismatch,
and admission is the single generic membership rule (a vendor row is
admitted iff its bar-open instant is in the expected-start set of its
session under the pinned table). OFFLINE ONLY; no network anywhere.
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG / "checker"))
import tsla_completeness_check as chk  # noqa: E402

ZONE = "America/New_York"
SESSION_TABLE_PIN = ("00c5555c26d391444509e54de322841f"
                     "a3269b64f3161a50aa507bf1d2bd416f")
CHECKER_PIN = ("4fdc31cbfc4b1a96baaabe775d883135cf64a4f7dc2"
               "606c7b679756da1e7d936")

WINDOWS = {
    "HO": (date(2023, 10, 19), date(2024, 9, 13)),   # 227 sessions
    "DEV": (date(2024, 9, 16), date(2026, 10, 16)),  # 524 sessions
}

# Declared split boundaries (adjust=splits basis; the STEP lane
# classifies, it does not assume). Pilot table from -02; DEV capture
# additions are the two 10:1 splits inside the DEV window among the
# captured 43 names.
DECLARED_SPLITS_PILOT = {("NVDA", "HO"): [("2024-06-10", 10)]}
DECLARED_SPLITS_DEV = {
    ("NVDA", "HO"): [("2024-06-10", 10)],
    ("AVGO", "DEV"): [("2024-10-11", 10)],
    ("NFLX", "DEV"): [("2025-11-17", 10)],
}


def verify_checker_pin():
    digest = hashlib.sha256(
        (PKG / "checker" / "tsla_completeness_check.py")
        .read_bytes()).hexdigest()
    if digest != CHECKER_PIN:
        raise SystemExit(f"CHECKER_PIN_MISMATCH: {digest}")
    return digest


def load_sessions(table_path: Path):
    raw = table_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SESSION_TABLE_PIN:
        raise SystemExit(
            f"SESSION_TABLE_PIN_MISMATCH: got {digest} — refusing to run")
    table = json.loads(raw)
    sessions = {}
    for row in table["sessions"]:
        d = date.fromisoformat(row["date"])
        hh, mm = row["close"].split(":")
        sessions[d] = int(hh) * 60 + int(mm)
    return sessions, digest, table["calendar_version"]


def window_sessions(sessions, window):
    lo, hi = WINDOWS[window]
    return {d: c for d, c in sessions.items() if lo <= d <= hi}


def load_frame(path: Path) -> pd.DataFrame:
    body = json.loads(path.read_bytes())
    values = body["values"]
    idx = pd.DatetimeIndex(
        [pd.Timestamp(v["datetime"]) for v in values]).tz_localize(ZONE)
    return pd.DataFrame(
        {"Open": [float(v["open"]) for v in values],
         "High": [float(v["high"]) for v in values],
         "Low": [float(v["low"]) for v in values],
         "Close": [float(v["close"]) for v in values],
         "Volume": [float(v["volume"]) for v in values]},
        index=idx)


def expected_start_set(sessions_w):
    out = set()
    for d, close_min in sessions_w.items():
        day = pd.Timestamp(d).tz_localize(ZONE)
        out.update(chk._expected_starts(day, close_min))
    return out


def admit(frame: pd.DataFrame, sessions_w):
    starts = expected_start_set(sessions_w)
    mask = [ts in starts for ts in frame.index]
    return frame[mask], frame[[not m for m in mask]]


def session_totals(frame: pd.DataFrame):
    """[(date, total_volume)] per ET session date present in frame."""
    out = []
    for d, grp in frame.groupby(frame.index.date):
        out.append((d, float(grp["Volume"].sum())))
    out.sort()
    return out
