#!/usr/bin/env python3
"""Day-1 analysis driver — TD probe rerun (task -75).

Offline analysis of the Day-1 receipts/snapshots acquired by the
-75 live rerun, using ONLY the accepted -74 candidate's analyzer
(probe_analyzer.py, imported unmodified):

- NVDA window: analyze_window(REQ-ADJ-01 splits vs REQ-ADJ-01N
  none; known factor 10, split effective 2024-06-10) -> C1/C2/
  C3/C4/C6.
- TSLA window: analyze_window(REQ-ADJ-02 splits vs REQ-ADJ-02N
  none; known factor 3, split effective 2022-08-25) -> C1/C2/
  C3/C4/C6.
- AAPL control (REQ-ADJ-03, adjust=splits, dividend window, NO
  split and NO none-twin in the frozen manifest): the analyzer's
  own primitives — verify_receipt (identity/hash/params),
  parse_bars (structure/window), _ohlc_consistent (the C4
  per-bar OHLC consistency core) and a C6-style row-count /
  no-pagination confirmation. Twin checks C1/C2/C3 do not apply
  to a single-series control and are reported NOT_APPLICABLE.

C5 (revision byte-compare) is PENDING_R7_R30: the R7/R30 legs
were not authorized and not run. Verdicts are sampled-window
only (PASS | DATA_UNQUALIFIED | HOLD). This driver emits NO
global KEEP/REPLACE S2 verdict and computes no performance.

Usage: analyze_day1.py <store_dir> <output_json>
"""

from __future__ import annotations

import json
import sys
import time
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent / "td_probe_commit_offset_closure_20261021_74"
sys.path.insert(0, str(CANDIDATE))

import probe_analyzer as az  # noqa: E402


def _params(symbol, start, end, adjust):
    return {"symbol": symbol, "interval": "1h",
            "start_date": start, "end_date": end,
            "timezone": "America/New_York", "outputsize": "5000",
            "order": "ASC", "adjust": adjust}


def main() -> int:
    store = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    now_ms = int(time.time() * 1000)

    nvda_win = ("2023-12-13T00:00:00", "2024-06-21T23:59:59")
    nvda = az.analyze_window(
        splits_receipt=store / "REQ-ADJ-01.receipt.json",
        splits_snapshot=store / "REQ-ADJ-01.json",
        none_receipt=store / "REQ-ADJ-01N.receipt.json",
        none_snapshot=store / "REQ-ADJ-01N.json",
        expected_params_splits=_params("NVDA", *nvda_win, "splits"),
        expected_params_none=_params("NVDA", *nvda_win, "none"),
        factor=Decimal(10), split_date="2024-06-10",
        expected_request_id_splits="REQ-ADJ-01",
        expected_request_id_none="REQ-ADJ-01N",
        expected_symbol="NVDA", expected_interval="1h",
        expected_window=nvda_win, now_ms=now_ms)

    tsla_win = ("2022-03-07T00:00:00", "2022-09-09T23:59:59")
    tsla = az.analyze_window(
        splits_receipt=store / "REQ-ADJ-02.receipt.json",
        splits_snapshot=store / "REQ-ADJ-02.json",
        none_receipt=store / "REQ-ADJ-02N.receipt.json",
        none_snapshot=store / "REQ-ADJ-02N.json",
        expected_params_splits=_params("TSLA", *tsla_win, "splits"),
        expected_params_none=_params("TSLA", *tsla_win, "none"),
        factor=Decimal(3), split_date="2022-08-25",
        expected_request_id_splits="REQ-ADJ-02",
        expected_request_id_none="REQ-ADJ-02N",
        expected_symbol="TSLA", expected_interval="1h",
        expected_window=tsla_win, now_ms=now_ms)

    aapl_win = ("2026-02-19T00:00:00", "2026-08-24T23:59:59")
    aapl_checks: dict = {}
    try:
        az.verify_receipt(
            store / "REQ-ADJ-03.receipt.json",
            store / "REQ-ADJ-03.json",
            _params("AAPL", *aapl_win, "splits"),
            expected_request_id="REQ-ADJ-03", now_ms=now_ms)
        aapl_checks["RECEIPT"] = {"status": "PASS"}
        bars = az.parse_bars(store / "REQ-ADJ-03.json",
                             expected_symbol="AAPL",
                             expected_interval="1h", window=aapl_win)
        problems = az._ohlc_consistent(bars)
        aapl_checks["C4_OHLC_CONSISTENCY"] = {
            "status": "PASS" if not problems else "FAIL",
            "problems": problems[:10]}
        aapl_checks["C6_ROWCOUNT_NO_PAGINATION"] = {
            "status": "PASS" if 0 < len(bars) < 5000 else "FAIL",
            "rows": len(bars), "pagination_trigger_rows": 5000}
        aapl_verdict = "PASS" if all(
            c["status"] == "PASS" for c in aapl_checks.values()) \
            else "DATA_UNQUALIFIED"
        aapl = {"verdict": aapl_verdict, "checks": aapl_checks,
                "C1_C2_C3": "NOT_APPLICABLE — single-series "
                            "dividend-window control, no twin"}
    except az.EvidenceHold as e:
        aapl = {"verdict": "HOLD", "hold_tag": e.tag,
                "detail": str(e), "checks": aapl_checks}

    result = {
        "task": "QF-TD-PROBE-DAY1-RERUN-20261021-75",
        "analyzer": "probe_analyzer.py (-74 candidate, unmodified)",
        "now_ms": now_ms,
        "windows": {
            "NVDA_REQ-ADJ-01_vs_01N": nvda,
            "TSLA_REQ-ADJ-02_vs_02N": tsla,
            "AAPL_REQ-ADJ-03_control": aapl,
        },
        "C5": "PENDING_R7_R30 — revision legs not authorized, "
              "not run",
    }
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
