# EXPOSURE_SPEC.md — Portfolio correlation / exposure study on Pine V3.6

**Status: FROZEN before any testing. Written 2026-09-18.**

## Question
Is V3.6's ~35% drawdown driven by correlated / clustered positions, and does
any portfolio-level exposure rule earn its keep?

V3.6 entries and exits are byte-identical. Sizing is fixed at 1% per trade for
this study (the S4 drawdown-gated sizing recommendation is NOT implemented
here — sizing is held constant so exposure effects are isolated). No new entry
filters on individual signals: these are PORTFOLIO-level gates only, evaluated
at entry time against currently open positions.

## What is NOT being tested
- No entry changes, no exit changes, no parameter retuning, no sizing changes.
- No signal-level filters (nothing that deletes a signal unconditionally).
- Pine V3.6 only, 4H only, UX51 universe (51 symbols), no shorts, no hedges.
- No parameter fishing, no combinatorial search beyond what is pre-registered.

## Portfolio / cost conventions (identical to all prior studies)
- $10,000 start, 1% risk per trade, max 5 concurrent positions (control),
  5% max portfolio risk, next-bar-open entries, stop-first on ambiguity.
- Costs: 4bps and 25bps legs. Research window: UX51 4H 2024-09-16 → 2026-09-14.
- Control = take-all = V3.6 baseline: 263 trades, +0.195R @4bps (must reproduce).

## Sector / theme map (defined by the researcher, documented, frozen here)

UX51 (51 symbols):
- SEMIS (9): NVDA, AMD, AVGO, MU, INTC, LRCX, AMAT, QCOM, ARM
- AI_INFRA (1): SMCI
- AI_SOFTWARE (11): PLTR, MSFT, GOOGL, META, CRM, APP, NET, SNOW, DDOG, CRWD, SHOP
- SPACE (3): RKLB, ASTS, LUNR
- CRYPTO (9): BTC-USD, ETH-USD, SOL-USD, DOGE-USD, AVAX-USD, LINK-USD, XRP-USD, COIN, MSTR
- FINTECH (5): SOFI, HOOD, PYPL, NU, MELI
- CONSUMER (6): TSLA, AAPL, AMZN, NFLX, NIO, F
- HEALTHCARE (2): MRNA, PFE
- ETF (5): SPY, IWM, SMH, ARKK, XLF

MEGA_AI theme (for rule E2) = SEMIS + AI_INFRA + AI_SOFTWARE + SPACE (24 symbols).

2022-validation extra symbols (not in UX51): COST→STAPLES, WMT→STAPLES,
JPM→BANKS, LLY→HEALTHCARE, ORCL→AI_SOFTWARE, QQQ→ETF, XOM→ENERGY.

## Exposure rules (maximum 4, exactly defined)

Evaluated at each candidate entry event, after exits at the same timestamp are
processed (same event ordering as the control simulator: exits kind=0 before
entries kind=1). A candidate skipped by a gate is gone permanently (same
documented approximation as the ranking study: the symbol cannot re-take a
later signal; bias direction identical across variants).

- **E1 "sector2"**: skip the candidate if ≥2 positions in the candidate's
  sector are already open. (Max 2 concurrent positions per sector.)
- **E2 "mega3"**: skip the candidate if it belongs to MEGA_AI and ≥3 MEGA_AI
  positions are already open. Candidates outside MEGA_AI are never skipped
  by E2.
- **E3 "corr70"**: skip the candidate if its trailing 360-bar 4H log-return
  correlation with ANY currently open position exceeds 0.70. Correlation is
  computed on 4h-bar log returns over the 360 bars ending at (and including)
  the bar before the entry bar — point-in-time, no lookahead. Requires ≥100
  overlapping bars with an open position; if fewer, that pair is ignored
  (treated as 0, no skip). Crypto pairs trade 24/7 vs equities 6 bars/day;
  overlap is on timestamp-aligned bars (inner join on bar timestamps).
- **E4 "cap3"**: hard cap of 3 concurrent positions instead of 5
  (MAX_CONCURRENT=3). The 5% portfolio-risk cap is unchanged.

The same 5%-portfolio-risk cap as the control applies to all variants.

## Interplay with the adopted rs_top2 ranking rule
Primary evaluation: each exposure rule is tested WITHOUT ranking, against the
take-all control (263 trades) — this isolates the exposure effect, as required
by the study brief. Documented production stacking (not the primary comparison):
at a contested timestamp, rs_top2 selects the top min(2, free slots) by 20-bar
return-minus-SPY first; the exposure gate then applies to those selected
candidates in rank order at entry time. For any frozen candidate, the stacked
(rs_top2 + rule) variant is additionally reported as a secondary diagnostic —
reported, not a candidate path.

## Diagnostics (no rule changes; run before rule comparison)

- **D1 — DD-episode anatomy.** On the baseline marked-equity curve, find the
  max-drawdown peak→trough window. Report: avg and max concurrent positions
  during the window; sectors of positions open at the DD start; mean pairwise
  trailing-360-bar 4h log-return correlation among positions open at DD start.
- **D2 — concurrency share of DD.** Fraction of the peak→trough decline that
  occurred on bars with ≥3 concurrent positions open (vs <3). Also report the
  concurrency histogram during the DD window.
- **D3 — clustered cohorts as one oversized trade.** Group control trades by
  entry timestamp. For cohorts with ≥2 trades from the same bar, compute the
  cohort's total R and the mean within-cohort pairwise outcome correlation.
  Report var(cohort total R) / sum(var_i) across multi-trade cohorts: ≈1 means
  independent trades, >>1 means they behave like one levered trade.
- **D4 — sector concentration.** Per sector: trade count, total R, share of
  total R, and approximate DD contribution (sum of R on trades open during the
  max-DD window, by sector).

## Metrics per variant (both cost legs)
trades, win rate, expectancy (R/trade), PF, total return %, max DD %,
Calmar (return/DD), avg winner R, avg loser R, TP1 hit rate %,
fill rate = trades taken / candidate signals available,
skipped-by-gate count (per rule), skipped-by-cap count.

## Fidelity check
The exposure simulator with no gates enabled must reproduce the control
(263 trades, +0.195R @4bps) trade-for-trade vs pb.simulate_portfolio before
any rule is evaluated.

## Candidate selection (research window → freeze, max 2)
A variant becomes a candidate only if ALL hold @4bps:
1. max DD cut by ≥5pp vs control,
2. expectancy ≥ 80% of control (≥0.156R),
3. trades ≥ 50 (not a tiny sample).
At most 2 candidates, frozen in CANDIDATES_FROZEN.md BEFORE touching 2022.

## 2022 validation
Same protocol as the ranking study: the 32-symbol 2022 set
(AAPL AMAT AMD AMZN AVGO BTC-USD COST CRM ETH-USD F GOOGL INTC JPM LLY LRCX
MRNA MSFT MU NFLX NIO NVDA ORCL PFE PLTR PYPL QCOM QQQ SNOW SPY TSLA WMT XOM),
signals with signal_time ≥ 2022-01-01 only, EOD liquidation at last close,
caches v6_short_v2/cache + pine_exit_fix/cache_2022.
Adoption bar in 2022: expectancy ≥ (2022 control expectancy − 0.05R),
max DD not materially worse than 2022 control (≤ control + 3pp).

## Verdict options
- Adopt an exposure rule: report it exactly (rule + engagement definition).
- Or close exposure research: "no exposure rule earns its keep; drawdown is
  the documented price of the edge," with the diagnostic answers (D1–D4)
  reported. If all variants fail: no new rules are invented.
