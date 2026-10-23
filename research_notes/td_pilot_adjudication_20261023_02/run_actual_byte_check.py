#!/usr/bin/env python3
"""
run_actual_byte_check.py — QF-TD-PILOT-ADJUDICATION-20261023-02

Actual-byte checker run over the ALREADY CAPTURED Twelve Data pilot
bytes (Step-1 pilot, 2026-10-23, scanner package
research_notes/td_pilot_20261023_01 commit 5d129fb; private archive
qf-data-archive commit 45496f8). OFFLINE ONLY: this script reads the
byte-identical local store and makes no network call of any kind.

Instrument: the calendar-bound completeness checker, candidate-2
lineage (task -94), copied byte-identical into ./checker/ from
research_notes/repair_94_20261022/ on origin/main
(tsla_completeness_check.py sha256 4fdc31cb...,
crypto_session_model.py sha256 248442f1...). CANDIDATE, not adopted
(G4 remains Mike's GO).

Calendar: the pinned adopted session table
research_notes/shadow_closeout_20261022/session_table.json,
sha256 00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f
(XNYS-751-UNION-20261021). This script REFUSES to run if the table
bytes do not match the pin (fail-closed).

THE ADMISSION RULE (one generic rule, no symbol/date special cases):
a vendor row is ADMITTED iff its bar-open instant is a member of the
expected bar-start set of its session date under the pinned table
(the checker's own _expected_starts: hourly starts from 09:30 up to
the pinned close — 16:00 normal, 13:00 early close). Every other row
is EXCLUDED and enumerated. The rule is shape-blind: it does not look
at OHLCV, flatness, or volume. Post-close vendor rows (the 15:30
phantom stubs Twelve Data appends after 13:00 early closes) fail
membership and are excluded by this rule alone.

Per leg this script reports three runs:
  RAW      — checker on the vendor bytes exactly as captured;
  ADMITTED — checker on the rows surviving the admission rule;
  plus the excluded-row enumeration and admitted grid endpoints
  (first/last admitted bar-open).

SMCI/HO is read from the quarantine body (unreceipted, preserved
byte-exact in the archive). Its classification is computed here and
stated in ADJUDICATION.md: NOT_EVALUABLE_PROVIDER_VOLUME.

Usage: run_actual_byte_check.py <session_table.json> <store_dir>
Output: checker_report.json next to this script + stdout summary.
"""
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "checker"))
import tsla_completeness_check as chk  # noqa: E402

SESSION_TABLE_PIN = "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f"
ZONE = "America/New_York"

WINDOWS = {
    "HO": (date(2023, 10, 19), date(2024, 9, 13)),   # 227 sessions
    "DEV": (date(2024, 9, 16), date(2026, 10, 16)),  # 524 sessions
}
# Declared split boundaries inside the pilot windows (adjust=splits
# basis; the STEP lane classifies, it does not assume).
DECLARED_SPLITS = {
    ("NVDA", "HO"): [("2024-06-10", 10)],
}
LEGS = [("NVDA", "HO"), ("NVDA", "DEV"),
        ("TSLA", "HO"), ("TSLA", "DEV"),
        ("AAPL", "HO"), ("AAPL", "DEV"),
        ("SPY", "HO"), ("SPY", "DEV")]
QUARANTINED = [("SMCI", "HO")]


def load_sessions(table_path: Path):
    raw = table_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SESSION_TABLE_PIN:
        raise SystemExit(
            f"SESSION_TABLE_PIN_MISMATCH: got {digest}, "
            f"pinned {SESSION_TABLE_PIN} — refusing to run")
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
    frame = pd.DataFrame(
        {"Open": [float(v["open"]) for v in values],
         "High": [float(v["high"]) for v in values],
         "Low": [float(v["low"]) for v in values],
         "Close": [float(v["close"]) for v in values],
         "Volume": [float(v["volume"]) for v in values]},
        index=idx)
    return frame


def expected_start_set(sessions_w):
    """Union of expected bar-open instants under the pinned table,
    built with the checker's own _expected_starts (same rule the
    COUNT lane reconciles against)."""
    out = set()
    for d, close_min in sessions_w.items():
        day = pd.Timestamp(d).tz_localize(ZONE)
        out.update(chk._expected_starts(day, close_min))
    return out


def summarize(result):
    return {
        "overall": result["overall"],
        "completeness_verdict": result["completeness_verdict"],
        "convention_verdict": result["convention_verdict"],
        "structural": result["structural"]["verdict"],
        "count": {
            "verdict": result["count"]["verdict"],
            "missing_bars": len(result["count"]["missing_bars"]),
            "extra_bars": result["count"]["extra_bars"],
            "missing_sessions": [
                s["session"] for s in result["count"]["missing_sessions"]],
            "expected_sessions": result["count"]["expected_sessions"],
            "present_sessions": result["count"]["present_sessions"],
        },
        "anomaly": {
            "verdict": result["anomaly"]["verdict"],
            "price_moving_zero_volume":
                result["anomaly"]["price_moving_zero_volume"],
            "price_moving_zero_volume_count":
                len(result["anomaly"]["price_moving_zero_volume"]),
            "no_trade_flat_zero_volume":
                result["anomaly"]["no_trade_flat_zero_volume"],
            "defect_bars": result["anomaly"]["defect_bars"],
        },
        "step": result["step"]["results"],
        "step_all_suspects": len(result["step_all"]["results"]),
        "vbasis_suspects": len(result["vbasis"]["results"]),
        "untestable": result["untestable"],
    }


def run_leg(symbol, window, sessions_w, store: Path, quarantined=False):
    base = store / ("quarantine" if quarantined else "raw")
    path = base / f"{symbol}__{window}.json"
    frame = load_frame(path)
    splits = DECLARED_SPLITS.get((symbol, window), [])
    raw_result = chk.run_check(frame, sessions_w, splits,
                               instrument="equity")
    starts = expected_start_set(sessions_w)
    admitted_mask = [ts in starts for ts in frame.index]
    admitted = frame[admitted_mask]
    excluded = [
        {"bar_open": str(ts),
         "flat": bool(r["Open"] == r["High"] == r["Low"] == r["Close"]),
         "volume": float(r["Volume"])}
        for ts, r in frame[[not m for m in admitted_mask]].iterrows()]
    adm_result = chk.run_check(admitted, sessions_w, splits,
                               instrument="equity")
    return {
        "leg": f"{symbol}/{window}",
        "source": ("quarantine (unreceipted)" if quarantined
                   else "raw (receipted)"),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows_raw": len(frame),
        "rows_admitted": len(admitted),
        "rows_excluded": len(excluded),
        "excluded_rows": excluded,
        "admitted_first_bar": str(admitted.index[0]) if len(admitted) else None,
        "admitted_last_bar": str(admitted.index[-1]) if len(admitted) else None,
        "raw_check": summarize(raw_result),
        "admitted_check": summarize(adm_result),
    }


def main():
    table_path, store = Path(sys.argv[1]), Path(sys.argv[2])
    sessions, digest, cal_version = load_sessions(table_path)
    report = {
        "task": "QF-TD-PILOT-ADJUDICATION-20261023-02",
        "checker_version": chk.CHECKER_VERSION,
        "checker_module_sha256": hashlib.sha256(
            (HERE / "checker" / "tsla_completeness_check.py")
            .read_bytes()).hexdigest(),
        "session_table_sha256": digest,
        "session_table_version": cal_version,
        "session_table_sessions": len(sessions),
        "legs": [],
    }
    for symbol, window in LEGS:
        report["legs"].append(
            run_leg(symbol, window, window_sessions(sessions, window),
                    store))
    for symbol, window in QUARANTINED:
        leg = run_leg(symbol, window, window_sessions(sessions, window),
                      store, quarantined=True)
        anomalies = leg["admitted_check"]["anomaly"][
            "price_moving_zero_volume_count"]
        leg["classification"] = (
            "NOT_EVALUABLE_PROVIDER_VOLUME" if anomalies > 0 else
            "REVIEW_REQUIRED")
        leg["classification_basis"] = (
            f"{anomalies} price-moving zero-volume bars survive the "
            "generic admission rule; no session-membership rule can "
            "cure a volume-completeness defect without imputation, "
            "which is prohibited. TSLA C2 precedent (-76).")
        report["legs"].append(leg)
    out = HERE / "checker_report.json"
    out.write_text(json.dumps(report, indent=1))
    for leg in report["legs"]:
        print(f"{leg['leg']}: raw_rows={leg['rows_raw']} "
              f"admitted={leg['rows_admitted']} "
              f"excluded={leg['rows_excluded']} "
              f"raw_overall={leg['raw_check']['overall']} "
              f"admitted_overall={leg['admitted_check']['overall']} "
              f"admitted_anomalies="
              f"{leg['admitted_check']['anomaly']['price_moving_zero_volume_count']}"
              + (f" classification={leg['classification']}"
                 if "classification" in leg else ""))
    print(f"report written: {out}")


if __name__ == "__main__":
    main()
