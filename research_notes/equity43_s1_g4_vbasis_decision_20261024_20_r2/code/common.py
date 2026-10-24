#!/usr/bin/env python3
"""
common.py — QF-EQUITY43-S1-G4-VBASIS-DECISION-PACKET-20261024-20 r2

Event-table correction only (governing: Issue #1 comment 6384407724).
Loading/admission semantics are copied unchanged from r1 (and through
it from the -02 actual-byte runner): the pinned session table is
hash-refused on mismatch, and admission is the single generic
membership rule. OFFLINE ONLY; no network anywhere in this code.

WHAT CHANGED vs r1, and why: r1's DECLARED_SPLITS_DEV carried a
hand-entered AVGO row, ("AVGO","DEV"): 2024-10-11 x10, with no issuer
source behind it. Broadcom's own record puts the first split-adjusted
trading date at 2024-07-15 — outside the DEV window — so the row was
factually wrong and it manufactured a positive control. In r2 every
declared event must come from the source-attested table below
(primary issuer records, first split-adjusted trading dates), and any
event that is unknown, unattested, or outside the window it is
attached to is REJECTED (SystemExit) rather than silently used.
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

# ---------------------------------------------------------------------
# Source-attested split events. Each row: FIRST SPLIT-ADJUSTED TRADING
# DATE + factor, pinned to the primary issuer record quoted. No row
# exists without a citation; a date may not be hand-entered here.
# ---------------------------------------------------------------------
ATTESTED_EVENTS = {
    "NVDA": {
        "date": "2024-06-10", "factor": 10,
        "issuer": "NVIDIA Corporation",
        "document": ("Press release, 'NVIDIA Announces Financial "
                     "Results for First Quarter Fiscal 2025', "
                     "2024-05-22 (investor.nvidia.com)"),
        "url": ("https://investor.nvidia.com/news/press-release-details/"
                "2024/NVIDIA-Announces-Financial-Results-for-First-"
                "Quarter-Fiscal-2025/default.aspx"),
        "quote": ("Each record holder of common stock as of the close "
                  "of market on Thursday, June 6, 2024, will receive "
                  "nine additional shares of common stock, to be "
                  "distributed after the close of market on Friday, "
                  "June 7, 2024. Trading is expected to commence on a "
                  "split-adjusted basis at market open on Monday, "
                  "June 10, 2024."),
    },
    "AVGO": {
        "date": "2024-07-15", "factor": 10,
        "issuer": "Broadcom Inc.",
        "document": ("Press release, 'Broadcom Inc. Announces Second "
                     "Quarter Fiscal Year 2024 Financial Results and "
                     "Quarterly Dividend', 2024-06-12 "
                     "(investors.broadcom.com); corroborated by the "
                     "company's split FAQ (static-files/e90fe911-"
                     "25c9-47eb-afbe-8e763b71eb64)"),
        "url": ("https://investors.broadcom.com/news-releases/"
                "news-release-details/broadcom-inc-announces-second-"
                "quarter-fiscal-year-2024-financial"),
        "quote": ("Our stockholders of record after the close of "
                  "market on July 11, 2024 will receive an additional "
                  "nine shares of common stock for each share held "
                  "after the close of market on July 12, 2024. At "
                  "market open on July 15, 2024, trading is expected "
                  "to commence on a split-adjusted basis."),
    },
    "NFLX": {
        "date": "2025-11-17", "factor": 10,
        "issuer": "Netflix, Inc.",
        "document": ("Press release, 'Netflix Announces Ten-For-One "
                     "Stock Split', 2025-10-30 (PR Newswire, SOURCE "
                     "Netflix, Inc.; also filed as Exhibit 99.1)"),
        "url": ("https://www.prnewswire.com/news-releases/"
                "netflix-announces-ten-for-one-stock-split-"
                "302600167.html"),
        "quote": ("Each shareholder of record as of the close of "
                  "trading on Monday, November 10, 2025 (the \"record "
                  "date\") will receive, after the close of trading on "
                  "Friday, November 14, 2025, nine additional shares "
                  "for every share held on the record date. Trading is "
                  "expected to begin on a split-adjusted basis at "
                  "market open on Monday, November 17, 2025."),
    },
}


def validate_declared(sym, win, splits):
    """Fail-closed admission of a declared-event list for one leg.

    Every (date, factor) must exactly match the source-attested event
    for that symbol AND fall inside the leg's window. Anything else —
    an unknown event, an unattested symbol, a wrong factor, or an
    attested event attached to a window it does not fall in — is
    rejected, never silently used. Returns the validated list.
    """
    lo, hi = WINDOWS[win]
    att = ATTESTED_EVENTS.get(sym)
    for dstr, factor in splits:
        if att is None:
            raise SystemExit(
                f"EVENT_TABLE_REJECT: {sym} has no source-attested "
                f"event; declared ({dstr}, x{factor}) refused")
        if (dstr, factor) != (att["date"], att["factor"]):
            raise SystemExit(
                f"EVENT_TABLE_REJECT: declared ({sym}, {dstr}, "
                f"x{factor}) does not match the source-attested event "
                f"({att['date']}, x{att['factor']}) — refused")
        d = date.fromisoformat(dstr)
        if not (lo <= d <= hi):
            raise SystemExit(
                f"EVENT_TABLE_REJECT: attested event {sym} {dstr} is "
                f"outside the {win} window [{lo} .. {hi}] — refused "
                f"rather than silently used")
    return list(splits)


def leg_declared(sym, win):
    """The declared splits for one leg, derived ONLY from the
    attested table: the symbol's attested event if it falls inside
    the leg's window, else no declared event for that leg."""
    att = ATTESTED_EVENTS.get(sym)
    if att is None:
        return []
    lo, hi = WINDOWS[win]
    if lo <= date.fromisoformat(att["date"]) <= hi:
        return validate_declared(sym, win, [(att["date"], att["factor"])])
    return []


# Derived leg tables (validated at import; a bad row cannot load).
# NVDA's attested event falls in HO only; NFLX's in DEV only; AVGO's
# attested event (2024-07-15) precedes the DEV window, so AVGO has NO
# declared event in DEV and is NOT a DEV positive control.
DECLARED_SPLITS_PILOT = {("NVDA", "HO"): leg_declared("NVDA", "HO")}
DECLARED_SPLITS_DEV = {
    ("NVDA", "HO"): leg_declared("NVDA", "HO"),
    ("NFLX", "DEV"): leg_declared("NFLX", "DEV"),
}

# The r1 table, preserved verbatim ONLY so the impact run and the
# fail-before tests can execute r1's exact inputs on the same bytes.
# It is invalid and is never used for any r2 verdict: r1's
# positive-control conclusion is labeled CONTROL_TABLE_INVALID.
R1_DECLARED_SPLITS_DEV = {
    ("NVDA", "HO"): [("2024-06-10", 10)],
    ("AVGO", "DEV"): [("2024-10-11", 10)],   # FALSE — no issuer source
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
