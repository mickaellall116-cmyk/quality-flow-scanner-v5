# Methods Survey — Correction Table (ChatGPT review 2026-10-07)

Corrections to load-bearing recommendations from the top-quant research methods survey
(`research_notes/top-quant-research-testing-methods-20261007-1823/report.md`).
Each row separates what the primary source establishes from what was proposed as policy.

| # | Recommendation (as surveyed) | Primary source | What the source establishes | What is NOT established | Corrected status |
|---|---|---|---|---|---|
| 1 | Compute DSR ≥ 0.95; log every trial's Sharpe | Bailey & López de Prado (2014), "The Deflated Sharpe Ratio," JPM 40(5) | DSR corrects for trial-selection bias in Sharpe ratios; requires the empirical variance of Sharpe across trials actually run | Fixed Sharpe tables and universal DSR cutoffs are not established in the paper; 0.95 is a conventional confidence level, not a paper-specified threshold | **Proposed policy**, not a paper mandate. DSR computation is sound; the 0.95 cutoff is our chosen convention. |
| 2 | Use CSCV/CPCV instead of single walk-forward | Bailey et al. (2016), "The Probability of Backtest Overfitting," JCF; López de Prado (2018), Ch. 7 | CSCV estimates PBO (probability the selected configuration is overfit); CPCV adds purging/embargo for serial dependence | CSCV/CPCV do not automatically replace walk-forward — they answer different questions (overfit probability vs out-of-sample performance estimate). PBO > 0.05 rejection threshold is a convention, not a theorem. | **Complementary tools**, not replacements. Use both; do not drop walk-forward. |
| 3 | Require >60% of parameter neighborhood profitable (plateau rule) | Practitioner literature (survey synthesis) | Intuition: robust edges should not depend on exact parameter values | No primary source establishes 60% as a threshold; the specific number is not an institutional standard | **Proposed heuristic**, not adopted standard. |
| 4 | Must beat buy-and-hold + 200-day trend + random entry under identical rules | Practitioner literature (survey synthesis) | Multi-benchmark comparison is good practice for isolating signal value | Not an established institutional gate; the specific benchmark set is not standardized | **Proposed diagnostic**, not adopted standard. |
| 5 | 6-month paper-trading incubation before live | Chan, "Quantitative Trading" (2008); industry interviews | Incubation/paper trading as walk-forward overfit detection is widely advocated | The specific 6-month duration is not an institutional standard; varies by firm and strategy frequency | **Proposed convention**, not adopted standard. |
| 6 | Harvey–Liu haircuts; t > 3.0 bar for factors | Harvey & Liu (2015); Harvey, Liu & Zhu (2016) | Multiple-testing corrections for backtest Sharpe ratios; t > 3.0 proposed as the hurdle for claimed factors | The papers propose, not mandate; adoption varies. The 50%-haircut shortcut is explicitly too lenient for low SR and too harsh for high SR (nonlinearity). | **Paper-proposed**, adoption varies. Do not use the flat 50% rule. |

## Standing notes

- Random benchmarks on forward-test data require a **frozen analysis plan** before execution (design the null, pre-commit the test, then run). Not created here.
- Feed-route memo remains the first priority; this survey is secondary reference material.
- All existing HOLD/KILL/quarantine decisions are unchanged.
