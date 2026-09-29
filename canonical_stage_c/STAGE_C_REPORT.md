# Stage C Report — fresh 4H cache construction (redo) — 2026-09-29

## 0. Redo note

A first Stage C attempt (local commit `2f4331d`, **never published**) reached a
FAIL verdict based on a flawed probe: it used yfinance 1H with explicit
start/end and wrongly concluded history before 2024-09-30 was unrecoverable.
That attempt was discarded in full (`git reset --hard b37f9afe`); no part of
it survives in this branch. This report supersedes it.

## 1. Fetch-shape correction (verified 2026-09-29)

- yfinance 1H with **explicit start/end is capped at 730 CALENDAR days**: a
  2023-10-26→2025-10-26 pull returns 0 rows with the
  "must be within the last 730 days" error.
- yfinance 1H with **period="730d" serves 730 TRADING SESSIONS**: verified
  reproducible — SPY pull: 5072 rows, 730 distinct sessions, oldest bar
  2023-10-31 09:30 ET.
- Consequence: the documented 2023-10-26 4H start is 3 trading days
  (10-26/27/30) older than what Yahoo serves today. Per §5B the
  effective-history start may be within **±5 trading days** of 2023-10-26
  with the divergence recorded and caused — 3 trading days qualifies.

## 2. Fetch (canonical_stage_c/fetch_4h.py)

- 137 symbols = 131 rebuilt universe (`canonical_stage_b/universe_rebuilt.json`)
  + 6 overlay outsiders (SOFI, RKLB, ONDS, ASTX, BBAI, HOOD).
- **One period="730d" pull per symbol**, `interval="1h"`, `prepost=False`,
  `auto_adjust=False`. Pacing: ~1.2s between requests, 8s per 10 symbols,
  2 bounded retries. Per-symbol fetch timestamps in `fetch_4h_manifest.json`.
- **134/137 succeeded on the primary shape.** GEV, RDDT, TEM failed all
  retries with a Yahoo server-side error
  ("1h data not available ... must be within the last 730 days") — a
  ticker-specific Yahoo quirk (their 1H history is bounded at 2024-09-30).
  Recovered with **period="max"** on the same endpoint/interval
  (3477/3477/3478 rows; oldest bar 2024-09-30 09:30 ET for all three) —
  same vendor, same bar shape, different lookback parameter, fully
  documented per-symbol in the manifest (`fetch_shape` field). Not a vendor
  substitution; no hammering (3 attempts each on the primary shape, then one
  diagnostic each).
- Total: **664,387 1H rows** fetched. Raw CSVs under
  `canonical_stage_c/raw_1h/`. Zero symbols unrecoverable.

## 3. 4H aggregation rule (canonical_stage_c/build_4h.py — per rev-6.1 §11 / UNIVERSE.md)

- Only regular-session 1H bars (`prepost=False`). Each 1H bar is assigned to
  the session containing its **open** timestamp (America/New_York wall clock):
  opens 09:30/10:30/11:30/12:30 → morning bar labeled **09:30**;
  opens 13:30/14:30/15:30 → afternoon bar labeled **13:30**.
- Bars with any other open time are anomalies (0 across all 137 symbols).
- Bar timestamp built from date+time with `tzinfo=America/New_York`
  (DST-safe, no arithmetic across transitions). All 189,235 bars carry
  tz-aware ISO timestamps; 0 bars with non-09:30/13:30 labels; 0 duplicate
  timestamps.
- Early-close (13:00) days: only morning 1H bars exist → exactly one 4H bar
  labeled 09:30. No bar spans the overnight gap.
- OHLCV: open=first, high=max, low=min, close=last, volume=sum, ordered by
  1H timestamp within the session.
- 1H bars are Yahoo split-adjusted, NOT dividend-adjusted (same property as
  the original cache, per UNIVERSE.md).
- 4H output clipped to the frozen window end **2026-09-24** (the raw pull
  includes newer sessions; they are recorded in the manifest, not built).
- Effective rule: 60th 4H bar from first available bar for the 11 admitted
  new listings; first 4H bar otherwise (UNIVERSE.md: "listing + 30 trading
  days (≈60 4H bars)"; and "new listings with 4H starting after their rule
  eligibility: effective = 60th 4H bar from first available bar").

## 4. Build result

- **137 symbols, 189,235 4H bars.** Per-symbol files:
  `canonical_stage_c/data_4h/{SYM}.json` (tz-aware ISO timestamps,
  per-bar `n_1h`, provenance, anomaly list).
- Per-symbol record (`build_4h_summary.json`): fetch counts, 1H→4H counts,
  first/last bar, `effective_4h_from`, expected vs actual vs the independent
  calendar (trading days from the Stage-A fresh SPY daily cache), missing%,
  quality flags.
- Expected calendar: 727 trading days 2023-10-31→2026-09-24; all 7
  documented early closes inside (2023-11-24, 2024-07-03, 2024-11-29,
  2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24).

## 5. Coverage comparison vs whitelisted target

Check target `canonical_baseline/coverage_report.json` hashed before use:
SHA-256 `fdb6e33a1b2edde231e607f9c5cd8f33f82f2d8b82caaac473fc551c26faed2b`
(matches frozen). Target is comparison-only, never an input.

| Group | Target | Rebuilt | Gap | Cause |
|---|---|---|---|---|
| 118 full-history | 1451 bars, eff 2023-10-26 | 1445 bars, eff 2023-10-31 | −6 bars / 3 td | Yahoo 1H serves from 2023-10-31; within §5B ±5td tolerance |
| ARM | 1392, eff 2023-12-08 | 1386 from eff, eff 2023-12-13 | −6 / 3 td | Same start shift (60th bar from first available) |
| BMNR, NBIS | 592 / 900 | 592 / 900 from eff | 0 | eff exact |
| CRWV, DRAM, GLXY, SNDK, SPCX | 686/183/618/734/85 | +1 bar each from eff | −1 | Rebuild matches the independent trading-day calendar exactly (SPCX: 43 days × 2 = 86); target is 1 short — documented, not tuned |
| GEV, RDDT, TEM | 936, eff 2024-11-06 | 931 from eff, eff 2024-11-08 | 2 td | Original first bar 2024-09-26 (UNIVERSE.md); Yahoo now serves these tickers from 2024-09-30; 60th-bar rule applied identically |
| TLT | 1451 | 1446 | −5 | TLT has 2 bars on 2026-02-02 (others: 1); plus the NaN bar below |
| TMO | 1439, eff 2023-11-03 | 1433, eff 2023-11-08 | −6 | Yahoo 1H for TMO now starts 2023-11-08 (was 2023-11-03); finding reproduces from the first attempt |
| XYZ | 839, eff 2025-01-21 | 839, eff 2025-01-21 | 0 | Exact |

Aggregate: 131 compared; effective_from exact: 8 (7 listings + XYZ; the rest
differ by the systematic start shift); bar-count exact (raw): 1 (XYZ).

## 6. Documented exceptions — verified

- **Early closes: 912/912** sessions have exactly one 09:30 bar, 0 violations.
- **2026-01-30**: 135/137 symbols single bar (DRAM, SPCX have no history yet).
- **2026-02-02**: 134 single bar + **TLT 2 bars** (09:30 n_1h=1, 13:30 n_1h=3).
- Per-symbol missing% vs the independent calendar: ≤ 0.33 everywhere, and
  every missing bar is one of the two documented gap days (missing = 2 for
  full-history symbols, 1 for TLT).

## 7. Findings

1. **TLT NaN bar (reproduces the first-attempt finding).** TLT 2026-02-02
   09:30 bar: all-NaN OHLC, zero volume (single 1H bar fed it). Quality
   flags: nan_ohlc=4, zero_volume=1, bad_wick=1 — the only symbol with any
   quality flags (0 anomalies_1h everywhere). The whitelisted target's TLT
   quality shows no NaN: Yahoo's backfilled data for that session differs
   from (or was dropped by) the original build. Documented, not patched.
2. **TMO servable-boundary shift (reproduces).** TMO 1H now starts
   2023-11-08 vs the target's 2023-11-03. Cause: Yahoo-side history
   boundary, not a build error.
3. **GEV/RDDT/TEM Yahoo 1H boundary.** Yahoo serves 1H for these tickers
   only from 2024-09-30; period="730d" server-errors for them (recovered via
   period="max"). This matches UNIVERSE.md's documented original-cache
   property ("first 4H bar actually 2024-09-26"). Their effective dates land
   2024-11-08 vs the target's 2024-11-06 (2 trading days, first-bar shift).
4. **SPCX/CRWV/DRAM/GLXY/SNDK +1 bar vs target from effective.** The rebuild
   matches the independent trading-day calendar exactly; the target is one
   short. Documented, not tuned.
5. **No quarantined data was opened.** The sealed comparator, quarantined
   scripts/data, and all Layer-2 artifacts were untouched. No portfolio
   simulation, no production V5.4 changes.

## 8. PIT / session-semantics statement

Bars are built only from completed, regular-session 1H bars available as of
the fetch; no forward-looking information enters any 4H bar. Session
assignment uses the 1H bar's own open timestamp; no bar spans the overnight
gap or an early close; DST transitions are handled by wall-clock
construction. Effective dates follow the documented 60th-4H-bar rule from
first available data. Nothing was substituted or tuned to close a gap.

## 9. Artifact hashes (SHA-256)

- 140 files hashed (137 per-symbol 4H JSON + manifest + build summary +
  comparison): see `canonical_stage_c/artifact_hashes.json`.
- Combined cache fingerprint (sorted per-symbol SHA-256 digest chain):
  `5d8ffa7175fc5746…` (full value in `artifact_hashes.json`).
- This report's own hash is recorded in the commit.

## Verdict

Coverage comparison **COMPLETE**: all divergences enumerated above with
causes. The effective-history start (2023-10-31) is within the §5B ±5
trading-day tolerance of 2023-10-26; every bar-count divergence traces to
that shift, the two documented Yahoo gap days, or the four documented
ticker-specific data findings. No tuning was performed. Gate C: **PASS with
recorded divergences** — subject to Mike's audit before anything downstream.
