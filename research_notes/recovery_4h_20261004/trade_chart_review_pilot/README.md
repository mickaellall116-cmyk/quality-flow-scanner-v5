# Pilot Trade-Chart Evidence Review

Bounded assignment: GitHub Issue #1 comment 6017640614 (ChatGPT), authorized by Mike 2026-10-06.

## What this is

Six pilot trades rendered from **retained evidence only** — no fresh data fetch,
no holdout access, no corrected-performance run, no frozen-system changes.
Charts supplement the numerical CP1 audit; visual agreement cannot prove byte parity.

## Selection

Published in `pilot_selection.json` **before** rendering (rule + trade IDs):

| # | Trade | Symbol | Rule |
|---|-------|--------|------|
| 1 | T145 | PFE | exact gap intersection (audit gap refs) |
| 2 | T146 | GOOGL | exact gap intersection (audit gap refs) |
| 3 | T029 | LRCX | earliest shifted equity entry (51-trade set) |
| 4 | T041 | PFE | earliest unshifted equity entry (115-trade set) |
| 5 | T005 | DOGE-USD | earliest crypto calendar entry (31-trade set) |
| 6 | T027 | SOL-USD | earliest SOL trade within the 31 crypto-calendar set |

T192 SOL exact-gap intersection was **withdrawn** (zero SOL trades intersect exact
gaps); rule 6 uses the earliest SOL trade from the 31-trade crypto set instead.
No trade was selected on profit/loss. All six IDs are distinct.

## Per-trade evidence

For each trade:
- `charts/<TID>_<SYM>.png` — retained h4 OHLC (defective grid **as stored**),
  with recorded signal/entry/exit lines, entry/stop levels, shifted-label bars
  (orange edges, derived from the audit), and audit gap annotations.
- `tables/<TID>_<SYM>_source_rows.csv` — machine-readable table linking every
  plotted candle and event to its source file, SHA-256, row index, timestamps
  (NY + UTC), and ledger fields.

**Recorded vs derived:** OHLC bars, signal/entry/exit times, entry/stop/exit
prices, exit reasons, and gap refs are recorded facts from the ledger,
intersection record, and audit. Orange "shifted label" edges are a derived
classification (EST label hour 8/12 on the UTC-anchored grid). Gaps are not
interpolated.

**UNAVAILABLE for all six trades:** constituent 1H windows — no 1h pickles are
retained in `backtest_cache/v3/`. Label-vs-price-window identity is therefore
UNDETERMINED wherever it would require 1H evidence.

## Reproduction

Dependencies: Python 3.12, pandas 2.1.4, matplotlib 3.6.3, numpy.

```bash
cd research_notes/recovery_4h_20261004/trade_chart_review_pilot
python3 render_pilot_charts.py [--out DIR]
```

Reads (relative to the repo root):
- `research_notes/recovery_4h_20261004/cp1_followup/trade_intersection.json`
- `research_notes/recovery_4h_20261004/cp1_followup/audit_52symbol.json`
- `research_notes/recovery_4h_20261004/cp1_bundle/02_c1_ledger/c1_240_trade_ledger.json`
- `backtest_cache/v3/h4_<SYM>.pkl`
- `pilot_selection.json` (this directory)

Writes `charts/`, `tables/`, and `SHA256_MANIFEST.txt` into the output dir.

Note: render at dpi>=150. dpi=110 triggers an Agg subpixel rasterization
artifact (spurious gray box) in matplotlib 3.6.3.

## Manifest

`SHA256_MANIFEST.txt` lists SHA-256 hashes of all charts and tables.
