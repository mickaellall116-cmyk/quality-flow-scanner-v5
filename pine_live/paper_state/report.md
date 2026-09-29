# Pine V3.6 Paper Phase — Three-Question Report

Generated: 2026-09-29T11:13:48.707211+00:00  |  Halted: no

## Q1 — Does the system behave exactly as specified?

- Cycles run: 66
- Packets replayed: 935, mismatches: 0 (CLEAN)
- Decisions logged: 90 | fills: 9 | completed trades: 2 | rejections: 1006
- Refused timestamps: 0 | failed-closed timestamps: 0
- Cycle completeness: BROKEN — see incomplete_cycles
- Reason codes: {"RANKED_OUT": 63, "RISK_CAP": 1, "SECTOR_CAP": 19, "TAKEN": 7}
- **Verdict: ATTENTION**

## Q2 — Does execution remain within the tested cost envelope?

- Fills logged: 9 (2 exits); total fill deviation: 0.0 R (max abs 0.0 R)
- Fills match theory: yes (0.0 R deviation)
- Avg extra cost/trade at 25bps vs 4bps: 7.4447 $ (modeled 25bps round-trip: 8.8628 $)
- Detection delay: n=66, median=0.0 min, p95=0.1 min, max=0.1 min
- paper fills assume execution at the bar open; median detection delay was 0.0 min (p95 0.1 min) over 66 cycles.

## Execution realism: canonical vs achievable

- canonical fill = next bar's OPEN (the backtest assumption); achievable fill = last visible price at detection: CLOSE of the signal bar (entries) / CLOSE of the exit-trigger bar (exits), under the current achievable-fill policy 'signal-bar-close-at-detection'. This is the honest conservative proxy for what the hourly-polling architecture can do today, not necessarily the eventual production fill: when a real-time feed lands, the policy upgrades to first-actionable-quote. Gate thresholds are unchanged by the policy. Positive drag = achievable worse. See pine_live/paper/dual.py.
- Closed trades with dual data: 2 (of 2 total; 0 missing achievable data)
- Expectancy/trade, 4bps leg: canonical +0.7404 R | achievable +0.7380 R
- Expectancy/trade, 25bps leg: canonical +0.6660 R | achievable +0.6635 R
- Detection-delay drag: mean +0.8 bps/trade (median +0.8; range -0.0 to +1.5; mean +0.0024 R)
- Realized equity (from $10,000): canonical $10,148.04 | achievable $10,147.56
- **Production gate (PROPOSED -- pending Mike's sign-off; reported only, never a halt):**
  - Overall: **INSUFFICIENT_DATA** -- only 2 closed paper trades with dual data; need >= 20. Nothing is inferred.
  - (a)/(b): INSUFFICIENT_DATA (need >= 20 dual trades)
  - (c) real-time feed attested: NOT_ATTESTED -- gate_c_attestation.json not present; no real-time feed has been attested

## Q3 — Is realized behavior statistically plausible vs the backtest?

### 4bps leg (n=2)
- Win rate: 100.0% (exact 95% CI 15.8%–100.0%; locked 46.2%)
- Expectancy: +0.740 R/trade (95% CI +0.014 to +1.467 R; locked +0.337)
- Avg win +0.740 R / avg loss n/a (locked +2.212 / -1.270)
- Profit factor: None (locked 1.49)
### 25bps leg (n=2)
- Win rate: 100.0% (exact 95% CI 15.8%–100.0%; locked 45.8%)
- Expectancy: +0.666 R/trade (95% CI -0.051 to +1.382 R; locked +0.280)
- Avg win +0.666 R / avg loss n/a (locked n/a / n/a)
- Profit factor: None (locked n/a)
- Max drawdown: 4.21% (locked 31.63%)
- Longest losing streak: 0 trades
- Reason codes (paper vs locked):
  - TAKEN: paper 7 / locked 143 (locked share 54.4%)
  - RANKED_OUT: paper 63 / locked 94 (locked share 35.7%)
  - SECTOR_CAP: paper 19 / locked 16 (locked share 6.1%)
  - NO_SLOT: paper 0 / locked 0 (locked share 0.0%)
  - RISK_CAP: paper 1 / locked 10 (locked share 3.8%)

*n=2 paper trades: plausibility means cannot-reject, not proven. At ~1.4 trades/week the 8-week phase expects ~11 trades; statistical power is low by design — the phase tests engineering fidelity, not edge.*

