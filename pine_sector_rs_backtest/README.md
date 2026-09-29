# P10 — Sector-relative strength (2026-09-24)

## Question (pre-registered)
Is a setup stronger when BOTH stock-level and sector-level relative strength
(vs SPY) agree? Independent of the failed Pine/scanner indicator-agreement
study — that was indicator agreement, this is price relative strength.

## Method (declared before looking at results)
- Baseline: canonical 4H Hybrid trades, 14-stock watchlist, 4H bars,
  Oct 2023–Sep 2026, frozen Mode B exits, 25bps costs. `pine_backtest`
  imported unmodified. MEASUREMENT study — no filter built or proposed.
- At each trade's signal date (point-in-time), 20-trading-day returns on
  DAILY bars (4H ETF history only reaches ~Oct 2024, so daily is used for
  everything to keep the window whole):
  - stockRS  = stock_ret20 − SPY_ret20
  - sectorRS = sectorETF_ret20 − SPY_ret20
- Sector ETF mapping (pre-declared):
  QQQ→XLK, SMCI→SOXX, PLTR→XLK, ANET→XLK, SOFI→XLF, RKLB→XLI, ONDS→XLK,
  DRAM→SOXX, SPCX→XLI, ASTX→XLK, BBAI→XLK, NIO→XLY, HOOD→XLF, AMD→SOXX
- Buckets: both_pos / stock_lead / sector_lead / both_neg.

## Results (237 trades, 25bps)

| bucket | n | exp R | win% | PF |
|---|---|---|---|---|
| both_pos (agree strong) | 124 | **+0.464** | 54.8 | 1.81 |
| stock_lead (stock strong, sector weak) | 83 | −0.018 | 47.0 | 0.97 |
| sector_lead (sector strong, stock weak) | 16 | −0.145 | 43.8 | 0.79 |
| both_neg (agree weak) | 14 | +0.207 | 42.9 | 1.36 |

Incremental test (does sector agreement add beyond stock RS?):
- Given stockRS>0: sector agrees +0.464R (n=124) vs disagrees −0.018R (n=83).
  Stock RS alone cannot explain the split.
- Given stockRS≤0: both thin buckets, no conclusions.

Persistence (both_pos vs stock_lead by year):
- 2024: +0.487R (n=37) vs +0.108R (n=25)
- 2025: +0.632R (n=56) vs +0.273R (n=33)
- 2026: +0.132R (n=31) vs −0.529R (n=25)
Agreement wins in all three years, including underwater 2026.

Symbol spread: both_pos spans 13 of 14 names, no name >15% of bucket;
11 of 13 names individually positive. stock_lead spans 12 names, mostly
flat/negative. Not a concentration artifact.

## Verdict: MAYBE (strong)
Pre-declared buckets, large n on both sides, persistent across all three
years, broad across symbols, plausible mechanism (sector tailwind vs
lone-wolf move). Not PASS — still in-sample on the development set; needs
forward validation before any production discussion. Descriptive implied
effect: dropping stock_lead trades would have lifted expectancy to ~+0.38R,
but that is a filter proposal and research stays measurement-only.

## Files
- `run_sector_rs.py` — study script (`pine_backtest` imported unmodified)
- `sector_rs_results.json` — buckets, incremental test, persistence, by-sector
- `cache/` — daily SPY/XLK/SOXX/XLF/XLI/XLY bars (4h_* partials unused)
