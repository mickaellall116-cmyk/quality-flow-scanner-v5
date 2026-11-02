#!/usr/bin/env python3
"""R7 analysis driver — TD probe REV7 re-pull (2026-11-01).

Offline C5 revision byte-compare of the R7 snapshots against the
Day-1 (-75) base snapshots, using ONLY the accepted -74
candidate's analyzer (probe_analyzer.py, imported unmodified):

- REQ-ADJ-01 (NVDA splits, Day-1) vs REQ-ADJ-01R7 (R7 re-pull)
- REQ-ADJ-02 (TSLA splits, Day-1) vs REQ-ADJ-02R7 (R7 re-pull)

C5 verdicts are sampled-window only (PASS | DIFFERS->HOLD |
HOLD). This driver emits NO global KEEP/REPLACE S2 verdict and
computes no performance.

Usage: analyze_r7.py <store_dir> <candidate_dir> <output_json>
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def _params(symbol, start, end, adjust):
    return {"symbol": symbol, "interval": "1h",
            "start_date": start, "end_date": end,
            "timezone": "America/New_York", "outputsize": "5000",
            "order": "ASC", "adjust": adjust}


def main() -> int:
    store = Path(sys.argv[1])
    candidate = Path(sys.argv[2])
    out_path = Path(sys.argv[3])
    sys.path.insert(0, str(candidate))
    import probe_analyzer as az  # noqa: E402

    now_ms = int(time.time() * 1000)
    results = {}

    nvda_win = ("2023-12-13T00:00:00", "2024-06-21T23:59:59")
    results["REQ-ADJ-01R7"] = az.analyze_revision(
        base_receipt=store / "REQ-ADJ-01.receipt.json",
        base_snapshot=store / "REQ-ADJ-01.json",
        rev_receipt=store / "REQ-ADJ-01R7.receipt.json",
        rev_snapshot=store / "REQ-ADJ-01R7.json",
        expected_params=_params("NVDA", *nvda_win, "splits"),
        expected_base_request_id="REQ-ADJ-01",
        expected_rev_request_id="REQ-ADJ-01R7",
        expected_symbol="NVDA",
        expected_interval="1h",
        expected_window=nvda_win,
        now_ms=now_ms)

    tsla_win = ("2022-03-07T00:00:00", "2022-09-09T23:59:59")
    results["REQ-ADJ-02R7"] = az.analyze_revision(
        base_receipt=store / "REQ-ADJ-02.receipt.json",
        base_snapshot=store / "REQ-ADJ-02.json",
        rev_receipt=store / "REQ-ADJ-02R7.receipt.json",
        rev_snapshot=store / "REQ-ADJ-02R7.json",
        expected_params=_params("TSLA", *tsla_win, "splits"),
        expected_base_request_id="REQ-ADJ-02",
        expected_rev_request_id="REQ-ADJ-02R7",
        expected_symbol="TSLA",
        expected_interval="1h",
        expected_window=tsla_win,
        now_ms=now_ms)

    out_path.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
