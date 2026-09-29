# Detection-Delay Study — Pre-registered Specification (v1)

**Status:** FROZEN for the paper phase. Observation only.

**Research question:** where does detection latency actually consume the
most edge? I.e., across which slices of paper trades is the
achievable-vs-canonical drag (per `pine_live/paper/dual.py`) largest —
so a future real-time feed can be aimed where it matters most.

**Data source (read-only):** `pine_live/paper_state/ledger/trades.jsonl`.
Only closed trades with a finite `drag_bps` are included. Nothing here
writes to `paper_state/`, affects positions, or touches strategy.

## 1. Minimum-sample safeguard

`MIN_BUCKET_TRADES = 10`. No bucket (of any slice dimension) is ranked
by mean drag until it holds at least 10 trades. Buckets below threshold
are labeled `INSUFFICIENT_SAMPLE`, excluded from all rankings, and
listed separately in the report — the report states this explicitly
rather than showing a noisy ranking.

## 2. Slice dimensions (frozen bucket definitions)

All drag figures are `drag_bps` from the dual ledger (positive =
achievable worse than canonical). Each slice reports n, mean and median
drag_bps, mean drag_r (4bps leg), and is ranked by mean drag_bps
descending among qualifying buckets.

- **Symbol:** one bucket per symbol (e.g. `NVDA`).
- **Structural-vol bucket** — stop distance as fraction of entry price,
  `(entry_px - stop_px) / entry_px`, a volatility proxy (the frozen stop
  is ~1.5× ATR by construction):
  `vol<1.5%` | `vol 1.5-3%` | `vol 3-5%` | `vol>=5%`.
- **Time-of-day bucket** — UTC hour of `entry_time`:
  `tod 00-05` | `tod 06-11` | `tod 12-17` | `tod 18-23`.
  (Labeled as entry-time hour; the signal bar immediately precedes it.)
- **Gap-size bucket** — entry-leg gap in bps,
  `|entry_px - ach_entry_px| / entry_px * 10000`:
  `gap<10bps` | `gap 10-30bps` | `gap 30-75bps` | `gap>=75bps`.
- **Regime bucket** — from the trade record's `regime` field when
  present (regime tagging is a separate research job; until it exists
  this slice reports unavailable rather than inventing tags).

## 3. Report

`pine_live/research/detection_delay_report.md` is **regenerated** from
the ledger on every run (not append-only state). With zero qualifying
trades it reports `INSUFFICIENT_DATA`. With trades but no qualifying
bucket in a dimension, that dimension reports `INSUFFICIENT_SAMPLE`
across the board. The report's headline section — "where a real-time
feed would matter most" — lists the top qualifying buckets by mean
drag_bps across all dimensions.

## 4. Anti-tuning

These bucket definitions are frozen at pre-registration (see
`SHADOW_ADVISOR_SPEC.md` §6). No redefining buckets to make results
look better; changes require the full change-control bar.
