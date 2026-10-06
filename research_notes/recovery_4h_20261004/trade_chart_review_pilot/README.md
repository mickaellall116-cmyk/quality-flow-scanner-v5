# Pilot Trade-Chart Evidence Review

Bounded assignment: GitHub Issue #1 comment 6017640614 (ChatGPT), authorized by Mike 2026-10-06.

## What this is

Six pilot trades rendered from **retained evidence only** — no fresh data fetch,
no holdout access, no corrected-performance run, no frozen-system changes.
Charts supplement the numerical CP1 audit; visual agreement cannot prove byte parity.

## REV 2 corrections (ChatGPT read-back, Issue #1 comment 6023866252)

Applied 2026-10-06. All changes are presentation/provenance fixes; no new data,
no recomputation from unretained sources.

1. **SVG charts added** (`charts/<TID>_<SYM>.svg`): text-safe (matplotlib
   `svg.fonttype=none`, real `<text>` elements), self-contained, remotely
   readable. PNGs remain local-only (connector binary limitation, see below).
2. **CSV tables restructured** (`tables/<TID>_<SYM>_source_rows.csv`):
   - Gap rows now cite the **canonical shard-reconstructed**
     `trade_intersection.json` SHA-256 (`02608fd4…`), with an explicit note
     mapping the local pretty-print hash (`a457e7a1…`, content-identical).
   - Every row carries the anchored `trade_id` and the deterministic
     `ledger_row_index` (integer position in `c1_240_trade_ledger.json`'s trade
     list; `(symbol, entry_time)` pairs are unique across all 240 trades, so the
     index is unambiguous).
   - Timestamps and prices are separate explicit columns
     (`event_timestamp_et`, `event_timestamp_utc`, `price`) — no overloading.
   - New columns (or explicit `UNAVAILABLE` labels): `candle_end_time_et`
     (derived as candle start + 4h on the recorded 4h grid), `pinned_source_commit`,
     `system_engine_version`, `equity_session_boundary`, `intended_entry_price`,
     `recorded_fill_price`, `target_tp1_price`, `target_stop_price`.
   - Labeled `UNAVAILABLE` (never inferred): system/engine version (no version
     string retained in the ledger provenance), equity session boundary (not
     recorded; defective grid makes session mapping UNRESOLVED), intended entry
     price (ledger records one entry price = the backtest's recorded fill; no
     separate intended entry exists), TP1 price target (ledger carries
     `tp1_hit` boolean only).
3. **Selection chronology corrected** (`pilot_selection.json`): the
   `"published_before_rendering": true` claim was removed. Replaced with
   `selection_render_chronology`, which documents the observed mtimes/commits
   and states plainly that any "published before rendering" claim beyond the
   documented observations is self-reported chronology — the pilot directory was
   untracked in git, so no timestamped commit cleanly anchors selection-before-render.
4. **Manifest expanded** (`SHA256_MANIFEST.txt`): now lists every file in the
   package (charts, tables, README, selection, renderer) except itself.

## Selection

Trade IDs (rule descriptions in `pilot_selection.json`; the selection's
render chronology is documented there as self-reported — see REV 2 note 3):

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

Note: render at dpi>=130. dpi=110 triggers an Agg subpixel rasterization
artifact (spurious gray box) in matplotlib 3.6.3. Charts are saved as
palette-32 PNGs to stay under the GitHub MCP connector's single-argument
size limit; visual content is unchanged.

## Manifest

`SHA256_MANIFEST.txt` lists SHA-256 hashes of every file in the package
(charts PNG+SVG, tables, README, `pilot_selection.json`, renderer) except the
manifest itself. PNGs are hashed for local verification even though they are
not published (see below).

## Publication note

Text files (README, selection, renderer, tables, manifest) are published to
the repo `main` branch via the GitHub MCP connector and verified byte-identical
by Git blob SHA. The six PNG charts are **local-only**: the MCP connector's
`create_or_update_file`/`push_files` tools accept text content only (the server
UTF-8-encodes the content string before base64; binary bytes do not round-trip —
verified by a probe upload that produced a corrupted blob, since removed).
Charts are reproducible byte-identical from `render_pilot_charts.py`; their
SHA-256 hashes are in the manifest for independent verification.
