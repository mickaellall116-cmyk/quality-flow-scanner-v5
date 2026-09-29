# Hedge overlay backtest — analysis (2026-09-18)

Spec: `HEDGE_SPEC.md` (frozen before testing). Window 2022-01-03→2026-09-14 (1,178 trading days),
$100k QQQ buy-and-hold proxy. Regime = scanner's own market-regime scoring on daily bars
(documented adaptation of `backtest.py::regime_at`; first RISK-OFF fired 2022-01-18, −7.7% into the bear —
the lag is structural: 3 of 4 trend conditions must fail). 334 RISK-OFF days (28.4%), 23 episodes.

## Results

| Hedge | Net P&L | Ann. drag | Max DD (long-only −34.8%) | Activity |
|---|---|---|---|---|
| A: regime-timed QQQ puts (BS, σ=VIX) | −$2,334 | −0.50%/yr | −30.8% (−4.0pp) | 27 buys, 5 rolls, 12 skips |
| A @ σ=1.15×VIX | −$1,675 | −0.36%/yr | −30.8% | 49 skips |
| B: always-on QQQ puts (BS, σ=VIX) | +$18,796 | +4.02%/yr | −19.4% | 52 rolls, 9 skips |
| B @ σ=1.05×VIX | +$2,164 | — | — | — |
| B @ σ=1.10×VIX | −$10,492 | — | — | — |
| B @ σ=1.15×VIX | −$13,622 | −2.9%/yr | −40.9% (worse) | 39 skips |
| C: regime-timed SH (exact) | −$1,528 | −0.33%/yr | −34.8% (no cut) | 23 round trips |
| D: always-on 10% SH (exact) | −$3,499 | −0.75%/yr | −32.7% (−2.1pp) | 56 monthly rebalances |

Put detail: A paid $12,241 premium / $9,907 payouts; B paid $33,313 / $51,297 (at 1.0×).
Year splits: A made +$3,658 in 2022 then lost money every year after. D made +$1,988 in 2022
then bled $1.1–1.6k/yr. C lost $132 **in 2022** despite SH gaining +19.7% that year.

## Findings

1. **The +$18.8k for always-on puts is a vol-miscalibration artifact, not edge.** Sign flips
   between σ=1.05× and 1.10× VIX; breakeven ≈ 1.06×. True QQQ 30-day IV runs ≈1.15–1.25× VIX
   (SPX IV), so at market prices always-on puts lose ~$10–14k (−2 to −3%/yr). The 1.0× run
   systematically underpays for QQQ options. (A is less sensitive — brief holds wash the
   miscalibration out — but shares the other flaws.)
2. **Regime timing buys late and sells into relief rallies.** C lost money in 2022 across 9
   whipsawed episodes despite SH being up on the year; its max-DD reduction is zero. Timing
   the hedge costs more than it saves, both in puts (A's fragility) and SH (C's whipsaw).
3. **A 0.5%-of-portfolio premium budget cannot buy protection when it's most needed.**
   At VIX ≳ 40 a single 5%-OTM QQQ put costs more than the budget (A: 12 skips, B: 39 at
   1.15×) — the insurance desk is closed during the fire. In 2025's tariff crash and 2026's
   selloff, the timed put hedge mostly sat out.
4. **SH numbers are exact and therefore the only fully trustworthy ones.** D: −0.75%/yr drag,
   −2.1pp of max-DD reduction, pays mechanically in bear years (+$2k in 2022). No model risk,
   no timing decisions.

## Verdict (ranked on "does it earn its keep")

1. **D (always-on 10% SH)** — least-bad: exact, no timing whipsaw, modest drag, real DD cut.
2. **A (regime puts)** — best DD-per-drag on paper, but BS-estimated and unbuyable at high VIX.
3. **C (regime SH)** — exact yet pointless: lag + whipsaw erase the protection.
4. **B (always puts)** — at fair IV the most expensive; headline profit is an artifact.

**Overall: none earns its keep.** Every hedge was a net cost over 2022-2026; D's −0.75%/yr is an
insurance premium, not an investment.

## Recommendation

If downside protection is wanted despite the cost: **D — a constant ~10% SH allocation,
rebalanced monthly, no timing signals.** Otherwise: no hedge; accept the long-only −34.8% max DD.

## Caveats / honesty notes

- Puts are Black-Scholes estimates: European exercise (slight understatement vs American),
  no bid/ask spread (flattering, small), r=4% and q=0.6% held constant, and σ=VIX/100 is the
  dominant bias (flattering — see sensitivity sweep; break-even ≈1.06×, market ≈1.15–1.25×).
- SH legs are exact (adjusted closes, 4bps each way, distributions ignored as immaterial).
- One bear year in 4.67: hedge value concentrates in rare events; a second bear market could
  change the ranking — but nothing here was fitted, per the anti-overfit commitment.
- Files: `HEDGE_SPEC.md`, `data_regime.py`, `hedge_backtest.py`, `hedge_results.json`, `cache/data.pkl`.
