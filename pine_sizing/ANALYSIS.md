# POSITION SIZING — analysis

## What was tested

Five pre-registered sizing schemes on the exact same 263 V3.6 baseline trades
(UX51, 4H, 2024-09-16→2026-09-14). Only $ risk per trade varies. Fidelity check
passed exactly: n=263, expectancy +0.195R at 4bps. Engine verified bit-identical
to `pb.simulate_portfolio` for fixed risk (same 31.27% / 35.97% / 87+17 skips).

Accounting note: this study's absolute return (31.27%) differs slightly from the
historically quoted baseline (+35.3%) because the lifecycle trade copy records a
synthetic blended exit price. R-level fidelity is exact (263 / +0.195R), and all
scheme comparisons below are within ONE consistent accounting — the sizing
conclusions do not depend on which absolute number you anchor to.

R-space sanity check (pre-registered): expectancy R/trade = 0.195R and total R =
51.28R are IDENTICAL across all five schemes. Sizing is pure $ scaling. ✓

## Bull window, event engine, 4bps

| scheme        | ret%  | maxDD% | DD (base-risk R) | Calmar | longest streak | skipped (cap/risk) |
|---------------|-------|--------|------------------|--------|----------------|--------------------|
| S0 fixed 1.00 | 31.27 | 35.97  | 35.97            | 0.869  | 8              | 87 / 17            |
| S1 fixed 0.50 | 14.32 | 22.80  | 22.80            | 0.628  | 8              | 98 / 0             |
| S2 fixed 0.75 | 20.39 | 30.97  | 30.97            | 0.658  | 8              | 98 / 0             |
| S3 fixed 1.25 | 46.03 | 40.51  | 40.51            | 1.136  | 8              | 0 / 128            |
| S4 dd-gated   | 29.49 | 29.86  | 29.86            | 0.988  | 8              | 98 / 0             |

## Bootstrap, 10k paths, sequential-compounding accounting

| scheme        | P(ruin ≤-50%) | P(DD>20%) | DD median | DD p75 | DD p95 |
|---------------|---------------|-----------|-----------|--------|--------|
| S0 fixed 1.00 | 0.0018        | 0.687     | 23.72%    | 29.95% | 40.94% |
| S1 fixed 0.50 | 0.0000        | 0.102     | 12.44%    | 15.99% | 22.65% |
| S2 fixed 0.75 | 0.0002        | 0.399     | 18.22%    | 23.21% | 32.30% |
| S3 fixed 1.25 | 0.0055        | 0.873     | 28.93%    | 36.19% | 48.67% |
| S4 dd-gated   | 0.0000        | 0.305     | 17.52%    | 20.89% | 27.13% |

Bootstrap uses the same sequential-compounding approximation as the Monte Carlo
study (ignores the concurrency-cap drag); all schemes compared within this one
accounting, never mixed with event-engine numbers.

## 2022 validation (frozen candidates only, 30 trades, 25 symbols)

| scheme        | 4bps ret% | 4bps DD% | 25bps ret% | 25bps DD% |
|---------------|-----------|----------|------------|-----------|
| S0 fixed 1.00 | 1.69      | 24.48    | -0.57      | 25.66     |
| S4 dd-gated   | 0.88      | 17.50    | -0.53      | 18.28     |

R-space 2022: 0.160R/trade at 4bps (0.083R at 25bps), identical across schemes. ✓

## Verdict: ADOPT S4 (drawdown-gated sizing) as the recommended rule

Adoption bar, prong by prong:

1. **Better risk-adjusted in bull:** DD 29.86% vs 35.97% (−6.1pp), Calmar 0.988
   vs 0.869, return 29.49% vs 31.27% (−1.78pp given up). Pass.
2. **No 2022 degradation:** same shape — DD 17.5% vs 24.5% (−7pp), return 0.88%
   vs 1.69%; both ~flat at 25bps with S4's DD 7pp lower. Pass.
3. **Not a small-sample artifact:** bootstrap agrees in direction — P(DD>20%)
   0.305 vs 0.687, ruin 0.0000 vs 0.0018, median DD 17.5% vs 23.7%. Pass.

Exact rule: base risk 1.00% per trade. At each entry, if marked equity ≤ 90% of
running peak, risk halves to 0.50% for that trade; full risk restores when marked
equity ≥ 95% of peak. The 5% portfolio-risk gate is unchanged.

What S4 costs: ~1.8pp of bull-window return and ~0.8pp of 2022 return in exchange
for ~6–7pp less drawdown in both windows and zero bootstrap ruin. That is the
trade, stated plainly.

Rejected:
- **S1/S2 (0.50%/0.75% fixed):** lower DD but much lower return and worse Calmar
  (0.628/0.658 vs 0.869). Pure de-leveraging, not an improvement.
- **S3 (1.25% fixed):** higher Calmar (1.136) but DD 40.5%, 3× the ruin of
  control, 87% chance of a >20% DD. That is leverage, not risk management.
  Mike's problem is drawdown, not insufficient return.

## Explicit statements

- This study changed nothing live. No sizing rule is implemented anywhere.
  The output is a RECOMMENDATION. Mike has not authorized any live sizing change.
- S4 is a portfolio-construction overlay (like the rs_top2 ranking rule). It is
  orthogonal to rs_top2 and composes with it: ranking picks which slots to fill,
  S4 picks how much risk each filled slot gets.
- Sizing research is now CLOSED. Next in Mike's approved sequence: portfolio
  correlation/exposure → execution/slippage.
