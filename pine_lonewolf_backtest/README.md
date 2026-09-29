# Lone-wolf confirmatory test (2026-09-24)

## Hypothesis (pre-registered)
Skipping entries where stock 20-day RS vs SPY > 0 AND sector ETF 20-day RS vs
SPY <= 0 (lone-wolf breakouts) improves expectancy, because breakouts need
sector tailwinds -- a stock fighting its sector is swimming upstream.

## Mechanism
A breakout is a bet that demand overwhelms supply. When the whole sector is
bidding (sector RS positive), the stock's move rides a real flow. When the
stock moves alone against a weak sector, the move is idiosyncratic -- more
likely a head-fake, a short squeeze, or news that fades. P10 measured this
descriptively (both_pos +0.464R vs stock_lead -0.018R, persistent all 3 years);
this test turns it into the pre-registered filter P10 declined to propose.

## Method (declared before running)
- Canonical 4H Hybrid entries, 14-stock watchlist, 4H bars, Oct 2023-Sep 2026,
  frozen Mode B exits, 25bps costs, full portfolio sim (5 slots, 5% heat).
- P10's exact sector-ETF mapping and RS definitions reused verbatim
  (daily bars, 20-trading-day returns vs SPY, point-in-time at the SIGNAL bar,
  no lookahead). No re-tuning of anything.
- Two variants, admission rule only -- entries/exits identical:
  CONTROL (take all signals) vs NO_LONE_WOLF (skip stockRS>0 & sectorRS<=0).
- `pine_backtest` imported unmodified; portfolio sim is a faithful copy of
  `pb.simulate_portfolio` with an admission hook (same pattern as the P3 study).
- Sanity: 237 canonical trades; 83 lone-wolf flags -- exactly P10's stock_lead n.

## Results (25bps, taken-trade basis)

| Variant | Taken | Exp R | Win% | PF | Total ret | Max DD |
|---|---|---|---|---|---|---|
| CONTROL | 180 | +0.272 | 50.6 | 1.43 | 56.28% | 21.63% |
| NO_LONE_WOLF | 137 | **+0.380** | 54.0 | 1.65 | **66.23%** | **18.86%** |

- Blocked: 74 trades (83 flagged signals; 9 never reached admission due to caps).
- Blocked expectancy: **+0.064R** (50.0% win) -- mildly positive, NOT dead
  money. The filter removes below-average trades (+0.064 vs +0.380 taken),
  it does not purely dodge losers.

## Year cross-tab (taken expectancy)

| Year | CONTROL | NO_LONE_WOLF |
|---|---|---|
| 2024 | +0.420 (n=59) | +0.445 (n=49) |
| 2025 | +0.425 (n=68) | +0.482 (n=56) |
| 2026 | -0.089 (n=53) | **+0.101 (n=32)** |

Improvement in ALL three years -- including flipping underwater 2026 positive.

## Walk-forward (train entries <=2024 / test >=2025)

| Period | CONTROL | NO_LONE_WOLF | Delta |
|---|---|---|---|
| train | +0.420 (n=59) | +0.445 (n=49) | +0.025R |
| test (OOS) | +0.200 (n=121) | **+0.344 (n=88)** | **+0.144R** |

The out-of-sample delta (+0.144R) is LARGER than the in-sample delta.

## Blocked-trade symbol spread (concentration check)

12 symbols: RKLB 15, ANET 8, QQQ 8, SOFI 8, HOOD 7, SMCI 7, AMD 5, NIO 5,
ONDS 4, PLTR 4, BBAI 2, ASTX 1. Broad -- no single name drives it.

Opportunity cost (honest): the filter left real winners on the table --
blocked HOOD +0.636R (n=7), PLTR +0.910R (n=4), SOFI +0.678R (n=8),
RKLB +0.437R (n=15). It also dodged blocked QQQ -0.919R (n=8),
SMCI -0.561R (n=7), ONDS -0.446R (n=4), AMD -0.463R (n=5).

## Cost stress (pre-declared robustness points)

| Costs | CONTROL exp | NO_LONE_WOLF exp | Delta | DD ctrl / nlw |
|---|---|---|---|---|
| 25bps | +0.272R | +0.380R | +0.108R | 21.6% / 18.9% |
| 50bps | +0.212R | +0.317R | +0.106R | 22.8% / 20.1% |
| 100bps | +0.097R | +0.183R | +0.086R | 30.7% / 22.5% |

Survives realistic costs. Note the DD benefit widens at high costs
(30.7% -> 22.5% at 100bps) -- the filter's value is part expectancy,
part avoiding correlated drawdown.

## RS-lookback perturbation (pre-declared robustness points)

| Lookback | Delta exp (NLW - CTRL) |
|---|---|
| 20 trading days (pre-declared) | **+0.108R** |
| 10 trading days | -0.048R |
| 40 trading days | -0.036R |

**This is the overfitting flag.** The filter's value is specific to the
pre-declared 20-day RS definition; nearby lookbacks flip it negative.
The 20-day was NOT tuned (it was P10's measurement definition, set before
any filter existed), so this is not p-hacking -- but the mandate's
"survives nearby parameter values" gate fails, which blocks PASS.

## Verdict: MAYBE (strong)

For PASS the mandate requires: meaningful improvement (yes, +0.108R pooled,
+0.144R OOS), broad across periods/symbols (yes -- all 3 years, 12 symbols),
survives costs (yes), survives perturbation (**no** -- lookback-sensitive),
mechanism makes sense (yes), no obvious concentration (yes). One failed
gate = not PASS.

What it IS: the strongest confirmatory result of the mandate so far. The
filter was pre-registered against P10's pre-declared definition, wins in
every year including out-of-sample, improves drawdown, and has a real
mechanism. What it ISN'T: proven robust -- the lookback sensitivity means
forward validation must confirm it before any production discussion.

## Recommended next experiment
Forward-validate as a paper overlay (same pattern as the FVG sidecar):
log what the filter WOULD have blocked on live forward-test signals and
compare realized outcomes. Revisit at the ~50-signal checkpoint (late Oct 2026).
Do not touch production.

## Files
- `run_lonewolf.py` -- study script (`pine_backtest` imported unmodified)
- `run_robust.py` -- cost stress + lookback perturbation driver
- `lonewolf_results.json` -- variants, blocked analysis, yearly, walk-forward, verdict
- `lonewolf_robustness.json` -- cost/lookback robustness table
- `README.md` -- this file

Guardrails respected: research only. V5.4, Mode B, production alerts, grades,
exits, market gate, AI Observer untouched; new files only in this folder.
