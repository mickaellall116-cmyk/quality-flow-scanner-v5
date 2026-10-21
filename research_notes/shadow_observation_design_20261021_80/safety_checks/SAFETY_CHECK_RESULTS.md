# SAFETY CHECK RESULTS — TASK -80 shadow-observation design

Run: 2026-10-21T23:40:32.997657+00:00 · Python 3.12.3 · pinned tracker sha256 verified: 3ee92864f1afe98ce543803b8b844c1677a6d0e0ce1a6e61d1b7ea74b329a9e0

| Check | Result |
|---|---|
| S1 — writes only inside the shadow namespace | PASS |
| S2 — production state hashes identical before/after | PASS |
| S3 — no import/call path to production position-opening | PASS |
| S4 — cohort label + both timestamps on every record | PASS |
| S5 — Mode B simulation matches hand-computed fixtures | PASS |
| S6 — degraded data: zero signals + DEGRADED marker | PASS |

**Overall: PASS (6/6)** — full machine-readable detail in results.json.

S5 hand-computed expectations (risk = entry - stop = 5.00 in all three): FIXA stop-out blended -1.0000R (exit at the 95.00 stop price); FIXB TP1 at B2 (partial +1.0000R) then runner-exit at the next bar's open 109.00 (runner +1.8000R) for blended +1.9000R, with the scanner EXIT on the TP1 bar correctly ignored and no close before the pending fill; FIXC 30-bar time exit at 101.00 for +0.2000R, never armed (max favorable +0.40R).

S2's binding assertion is over a byte-identical sandbox replica of the production files (the live harness may legitimately update the real files on its own cycle; the real hashes before/after the suite are recorded in results.json as informational).
