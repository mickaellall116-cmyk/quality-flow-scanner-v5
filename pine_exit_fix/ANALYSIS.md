# Pine V3.6 Exit-Fix Study — Analysis

## Question
The exit ablation found Pine's structural stop too tight (cuts recoveries:
entries + dumb 20-bar exit = +0.329R vs baseline +0.195R) but valuable as
drawdown control (stop/TP1-only variant: maxDD 23.9% vs 35.2%). Can a
pre-specified exit variant keep the insurance cheaper? Spec:
`PINE_EXIT_FIX_SPEC.md` (written before any test; frozen).

## Variants (entries byte-identical everywhere)
- **baseline**: Pine exits verbatim (sanity rerun).
- **fixA "wide_stop"**: stop 2.25× ATR (1.5× baseline multiple), rest identical.
- **fixB "late_arm"**: 2.25× ATR disaster stop until +1R MFE, then baseline
  management (2.5× trail, EMA55/trendBear) takes over.
- **fixC "slow_trail"**: baseline stop, 3.5× ATR trail after TP1, trendBear exit removed.

Winner criterion (pre-specified): highest expectancy at 4bps with maxDD ≤ 40%.

## Step 2 — exploratory (2024-09-16 → 2026-09-14, UX51 4H, 51 symbols)

| Variant | Trades | Win% | Exp (R) | PF | Ret% | MaxDD% | Avg hold |
|---|---|---|---|---|---|---|---|
| baseline | 263 | 44.9 | +0.195 | 1.27 | +35.3 | 35.2 | 18.1 |
| fixA | 254 | 52.8 | +0.234 | 1.47 | +24.8 | 22.5 | 22.1 |
| fixB | 250 | 54.4 | **+0.289** | 1.57 | +46.6 | 17.9 | 24.8 |
| fixC | 246 | 42.7 | +0.419 | 1.58 | +92.6 | **42.9** | 23.9 |

(25bps ordering identical: baseline +0.115 / fixA +0.181 / fixB +0.236 / fixC +0.339.)

- fixC excluded by the pre-specified DD cap (42.9% > 40%) — the cap did its job.
- Exploratory winner: **fixB** (+0.289R, DD 17.9%). fixA also qualified (+0.234R, DD 22.5%).
- Baseline rerun reproduced +0.195R exactly (sanity check passed).

## Step 3 — out-of-sample validation (2022-01-01 → 2022-12-31 4H)

25 symbols: NVDA PLTR TSLA AMD AAPL MSFT AVGO GOOGL AMZN NFLX CRM SPY (from
v6_short_v2/cache) + MU INTC LRCX AMAT QCOM PYPL NIO MRNA PFE F SNOW BTC-USD
ETH-USD (new Dukascopy pulls via the data_2022.py pipeline, same
resample_closed_4h builder; volume is CFD tick volume, relative use only).
Could not obtain: SOFI SMCI COIN MSTR SHOP NET DDOG CRWD MELI NU HOOD APP
(not on Dukascopy), META (not on Dukascopy), ARM (did not exist in 2022),
ETFs/small crypto (uncertain availability). Signals ≥ 2022-01-01 only;
EOD liquidation at last close for all variants.

| Variant | Trades | Win% | Exp (R) | PF | Ret% | MaxDD% |
|---|---|---|---|---|---|---|
| baseline | 30 | 40.0 | **+0.160** | 1.17 | +1.69 | 24.5 |
| fixA | 29 | 41.4 | +0.056 | 1.08 | +0.05 | 18.6 |
| fixB | 29 | 41.4 | +0.031 | 1.04 | −0.67 | 19.2 |

Adoption rule (pre-specified): beat baseline expectancy at 4bps with maxDD ≤ 40%.
- fixA: 0.056 < 0.160 → NO. fixB: 0.031 < 0.160 → NO.

## Verdict: NO FIX — keep current exits.

The exploratory gains did not generalize. Wider stops that looked brilliant in
the 2024–26 bull window let losers run in the 2022 bear market — the textbook
overfit signature, and exactly what the pre-specified validation was designed
to catch. Per the anti-overfit commitment, no Fix D.

## Bonus finding (not pre-specified, observational only)
The **baseline itself** held up out-of-sample: +0.160R in 2022 vs +0.195R in
2024–26, PF 1.17, maxDD 24.5%. The current Pine exits are regime-robust —
they earn their keep in a bear market too. The ablation's "-0.134R cost" was
a bull-window measurement; across regimes the insurance looks fairly priced.

## Caveats
- Small OOS sample (~30 trades; long entries are scarce in bear markets).
- Python reimplementation approximations (documented in pine_backtest.py).
- Dukascopy volume is CFD tick volume; dividends unadjusted (sub-1% effects).
- R denominated in each variant's own risk unit (standard, comparable).

## Files
- `PINE_EXIT_FIX_SPEC.md` — pre-specified hypothesis (frozen before testing)
- `pine_exit_fix.py` — Step 2 exploratory script
- `pine_exit_fix_results.json` — exploratory metrics
- `fetch_2022_extra.py` + `cache_2022/` + `cache_2022_fetch.log` — validation data build
- `pine_exit_fix_validate.py` — Step 3 validation script
- `pine_exit_fix_validate.json` — validation metrics
- `ANALYSIS.md` — this file
