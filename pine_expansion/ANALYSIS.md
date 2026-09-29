# Pine V3.6 expansion — results & verdicts (2026-09-18)

Local-only research. Definitions frozen in `PINE_EXPANSION_SPEC.md` **before** any
result was seen. Baselines: Pine 4H UX51 = 263 trades, +0.195R, PF 1.27 (4bps).

Costs shown at 4bps unless noted; 25bps figures in the JSONs.
Conventions everywhere: $10k, 1% risk/trade, max 5 positions, 5% portfolio risk.

---

## Study 1 — Scanner agreement filter: **NO**

Pine trades kept only if a V5 scanner structural candidate fired on the same
symbol within ±N four-hour bars (primary N=2).

| Filter | Kept | Exp (R) | PF | Verdict |
|---|---|---|---|---|
| N=0 | 1 / 263 | −0.841 | 0.00 | |
| N=1 | 8 / 263 | −0.388 | 0.41 | |
| **N=2 (primary)** | **14 / 263** | **−0.243** | **0.59** | **NO** |
| N=3 | 17 / 263 | +0.373 | 1.77 | noise blip (see below) |
| N=5 | 32 / 263 | −0.297 | 0.61 | |

Requiring agreement keeps 5% of trades and they lose money. The two systems are
nearly disjoint — Pine (momentum/breakout hybrid) and the scanner (pullback-to-
EMA21) fire at different times. The N=3 positive is noise: N=2 and N=5 with
similar/smaller samples are both deeply negative, and it fails the pre-specified
strong-positive trigger (needs ≥30 trades; has 17). **No 2022 validation was
triggered, per spec. Do not filter Pine signals by scanner agreement.**

### Bonus finding (exploratory): scanner-alone S0

Scanner S0 structural + scanner exits on UX51 4H, same window:
**309 trades, +0.314R, PF 1.45, +73.6%, DD 22.6%** — beats Pine's +0.195R.

Supplementary 2022 check (NOT pre-specified, 30 symbols, bear market, identical
no-EOD treatment both legs): scanner **−0.125R** vs Pine **−0.331R**. Both
negative → the scanner-alone edge is **regime-dependent, not validated**.
Pipeline verified: reproduces the exit_fix 2022 baseline (+0.147R vs reported
+0.160R) once EOD liquidation is applied. No action; hypothesis only.

---

## Study 2 — X2 universe (199 symbols): **NO**

Unmodified Pine V3.6 4H on the full X2 cohort, 199/199 symbols downloaded, 0 dropped.

| Universe | Trades | Exp (R) | PF | Return | MaxDD |
|---|---|---|---|---|---|
| X2 (199) | 888 | **−0.012** | 0.98 | +16.0% | 41.7% |
| UX51 baseline | 263 | +0.195 | 1.27 | +35.3% | 35.2% |
| Pooled (250) | 1151 | +0.035 | 1.05 | +20.6% | 50.6% |

The edge does not survive the broad universe — expectancy goes to ~zero and the
pooled drawdown balloons to 50.6%. **The edge lives in the curated UX51, not in
the strategy applied blindly to 199 names. Do not expand.**

---

## Study 3 — Daily / Weekly transfer

| Timeframe | Window | Trades | Exp (R) | PF | Return | MaxDD | Verdict |
|---|---|---|---|---|---|---|---|
| Daily UX51 | 2021-09→2026-09 | 262 | **−0.048** | 0.94 | −17.8% | 40.1% | **NO** |
| Weekly UX51 | 2020/21→2026-09 | 31 | **+0.547** | 2.05 | +25.7% | 16.2% | **tentative YES** |

- **Daily: NO.** Rerun reproduces the Sep-15 prior art byte-for-byte (−0.048R).
  The edge does not transfer down.
- **Weekly: tentative YES.** +0.547R, PF 2.05, DD only 16.2% — but **31 trades**
  across 25 symbols (ASTS 4, RKLB 3, META 2). Above the pre-specified 20-trade
  minimum, so not "inconclusive" — but this is hypothesis-generating, not a
  conclusion. Average hold 16.4 weeks (~4 months/trade). Worth watching /
  paper-trading; not worth sizing yet. No more weekly history exists to validate
  against.

---

## Bottom line for Mike

1. **Scanner agreement → NO.** Don't require it; the systems disagree 95% of the time and the overlap loses.
2. **X2 universe → NO.** Don't run the indicator on the broad 199; keep it on your curated 51.
3. **Daily → NO. Weekly → maybe.** Daily is dead; weekly looks promising on 31 trades — interesting enough to paper-trade, too thin to size.

Nothing here changes the indicator, the scanner, or any live process.
All result files: `pine_expansion_results.json` (consolidated),
`study1_results.json`, `study1_2022_validation.json`, `study2_results.json`,
`study3_results.json`.
