# Pine V3.6 Paper Phase — Three-Question Report

Generated: 2026-09-20T14:13:55.023487+00:00  |  Halted: no

## Q1 — Does the system behave exactly as specified?

- Cycles run: 12
- Packets replayed: 121, mismatches: 0 (CLEAN)
- Decisions logged: 0 | fills: 0 | completed trades: 0 | rejections: 121
- Refused timestamps: 0 | failed-closed timestamps: 0
- Cycle completeness: BROKEN — see incomplete_cycles
- Reason codes: {}
- **Verdict: ATTENTION**

## Q2 — Does execution remain within the tested cost envelope?

- Fills logged: 0 (0 exits); total fill deviation: 0 R (max abs 0.0 R)
- Fills match theory: yes (0.0 R deviation)
- Avg extra cost/trade at 25bps vs 4bps: None $ (modeled 25bps round-trip: None $)
- Detection delay: n=12, median=0.0 min, p95=0.0 min, max=0.1 min
- paper fills assume execution at the bar open; median detection delay was 0.0 min (p95 0.0 min) over 12 cycles.

## Execution realism: canonical vs achievable

- canonical fill = next bar's OPEN (the backtest assumption); achievable fill = last visible price at detection: CLOSE of the signal bar (entries) / CLOSE of the exit-trigger bar (exits), under the current achievable-fill policy 'signal-bar-close-at-detection'. This is the honest conservative proxy for what the hourly-polling architecture can do today, not necessarily the eventual production fill: when a real-time feed lands, the policy upgrades to first-actionable-quote. Gate thresholds are unchanged by the policy. Positive drag = achievable worse. See pine_live/paper/dual.py.
- Closed trades with dual data: 0 (of 0 total; 0 missing achievable data)
- No closed trades with dual data yet.
- **Production gate (PROPOSED -- pending Mike's sign-off; reported only, never a halt):**
  - Overall: **INSUFFICIENT_DATA** -- only 0 closed paper trades with dual data; need >= 20. Nothing is inferred.
  - (a)/(b): INSUFFICIENT_DATA (need >= 20 dual trades)
  - (c) real-time feed attested: NOT_ATTESTED -- gate_c_attestation.json not present; no real-time feed has been attested

## Q3 — Is realized behavior statistically plausible vs the backtest?

### 4bps leg (n=0)
- No completed trades yet.
### 25bps leg (n=0)
- No completed trades yet.
- Max drawdown: 0.00% (locked 31.63%)
- Longest losing streak: 0 trades
- Reason codes (paper vs locked):
  - TAKEN: paper 0 / locked 143 (locked share 54.4%)
  - RANKED_OUT: paper 0 / locked 94 (locked share 35.7%)
  - SECTOR_CAP: paper 0 / locked 16 (locked share 6.1%)
  - NO_SLOT: paper 0 / locked 0 (locked share 0.0%)
  - RISK_CAP: paper 0 / locked 10 (locked share 3.8%)

*n=0 paper trades: plausibility means cannot-reject, not proven. At ~1.4 trades/week the 8-week phase expects ~11 trades; statistical power is low by design — the phase tests engineering fidelity, not edge.*

