# Shadow prospective parity probe — offline evidence only

**Status:** investigation/HOLD, not operational adapter integration, not launch authorization.

## Independent historical witness (as of existing commit ba4276f)

Read-only inspection of `forward_test/v54_ai_observer.json` (Git blob `a394c4a6c65411531288f475681f8e4fa816d74b`, 37 `assessments[].features` rows) shows:

- Start times ET: **06:30 (15)**, **10:30 (11)**, **14:30 (11)**; **zero** start at frozen 09:30/13:30 grid.
- Durations: **4h (26)**, **1.5h (11)**, as last bar closes at 16:00 ET.
- Frozen `v54_rule_version`: **2026-09-15-v54 (37)**.
- Syntactic signal IDs are `v54:<symbol>:4h:<bar_close_at>:<rule_version>`; do not treat this as proof IDs are collision-free under restarts.
- The staged `forward_test/v54_status.json` (blob `312ee0ac41f747003c65af1067ae653097b31873`) additionally identifies a pending MSFT signal on 2026-10-19 with 06:30→10:30 ET timestamps. It confirms this is not merely ancient sample formatting.

**Interpretation:** the actual existing V5.4 observer output materially disagrees with the signal-only successor's `GRID_OPEN_WALL={(9,30),(13,30)}` and proposed exact-four-hours rule. A synthetic PASS cannot certify the actual 250-name scanner. **Do not simply bless the existing displaced timestamps, relabel bars, or change the frozen 09:30 clock**. The eventual tail-session partial-bar semantics need an explicit, predeclared rule backed by the confirmed bar/engine implementation.

## Exact offline commands (on Muse's VM)

```bash
python3 -B test_staged_signal_parity_probe.py
python3 -B staged_signal_parity_probe.py /path/to/quality-flow-scanner-v5/forward_test/v54_ai_observer.json
```

The second command is **expected to exit 2 / HOLD** on existing historical witness. Next, run the *actual pinned* `v54_qualified_signals(rows)` adapter against the **last existing ordinary-cycle inputs**, not synthetic rows or any new Yahoo/vendor fetch, record input SHA256 and the code pins, and repeat the same probe. If staged scan inputs are missing, report **NOT AVAILABLE**, not a fabricated PASS. Verify 250 unique cohort symbols and a distinct market-frame-failure fast-exit before any cohort scan. Run after confirming the correct actual time-index conventions including 13:30-to-session-close treatment.

No production, vendor, holdout, backtest, trading, launch authorization, or observer activation changes under this branch.
