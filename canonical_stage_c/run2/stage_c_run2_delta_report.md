# Stage C Run-2 vs Run-1 Delta Report

**Status:** Published evidence for Mike's audit and ChatGPT's review (Mike's Track-B bridge action, 2026-09-30). This is Muse's analysis, not a verdict — Mike decides.
**Prepared:** 2026-09-30 (UTC), by Muse.
**Prior bridge post:** commit `4e3a7e2cb286cb0111bc87e7669fa67865199408` (2026-09-30 01:52 UTC) published only the narrative writeup. This commit publishes the machine evidence below for the first time.

Every number in this report was recomputed from the on-disk files on 2026-09-30. Provenance is given per section. Nothing here is quoted from memory or from the bridge writeup.

---

## 1. Gate outcome — STOP preserved

The round-3 comparator (`compare_4h.py`, Mike's frozen rule: only `exact`, `allowed_start_shift` (±5 trading days), or `frozen_yahoo_gap_day_effect` pass) compared **131 of 137** fetched symbols and stopped the stage:

- `unclassified_finding`: **115**
- `data_drifted`: **13**
- `frozen_yahoo_gap_day_effect` (pass via frozen Yahoo accounting): **3** — AI, OXY, VLO
- `gate_c_stop: true` in `stage_c_comparison.json` → `aggregate`; comparator exited 1.

Source: `canonical_stage_c/run2/stage_c_comparison.json` → `aggregate.classification_counts` = `{"unclassified_finding": 115, "frozen_yahoo_gap_day_effect": 3, "data_drifted": 13}`, `n_compared` = 131.

The 6 fetched-but-not-compared symbols have no coverage-report target (recent listings): ASTX (606 4H bars), BBAI, HOOD, ONDS, RKLB, SOFI (1447 each). Source: `stage_c_comparison.json` → `outsiders_no_target`.

The comparator ran against the frozen coverage report — recorded `coverage_report_sha256` = `fdb6e33a1b2edde231e607f9c5cd8f33f82f2d8b82caaac473fc551c26faed2b`, matching the frozen value. Source: `stage_c_comparison.json` → `coverage_report_sha256`.

**No Layer 2 / downstream work was opened.** No `*layer2*`/`*stage_d*` paths exist. The Run-2 directory contains only the four-step runbook outputs (fetch manifest, input lock, raw 1H, built 4H, build summary, comparison). Run 1 (`canonical_stage_c/` root-level files: `raw_1h/`, `data_4h/`, `fetch_4h_manifest.json`, `build_4h_summary.json`) is untouched.

---

## 2. Totals — Run 1 vs Run 2

| | Run 1 (2026-09-29 fetch) | Run 2 (2026-09-30 fetch) |
|---|---|---|
| Symbols fetched | 137, 0 failures | 137, 0 failures |
| Fetch window (UTC) | 2026-09-29 22:53 → 23:00 | 2026-09-30 01:34 → 01:41 |
| `period=max` fallback | GEV, RDDT, TEM (server errors on `period=730d`) | GEV, RDDT, TEM (same 3) |
| Total 4H bars built | **189,235** | **189,498** |
| Early-close symbol-sessions (exactly one 09:30 bar, 0 violations) | **912/912** | **912/912** |

Sources:
- Bar totals: sum of `n_4h` over 137 symbol entries in `canonical_stage_c/build_4h_summary.json` (Run 1) and `canonical_stage_c/run2/build_4h_summary.json` (Run 2). Net delta: **+263 bars**.
- Fetch stats and fallback tickers: `fetch_4h_manifest.json` per-symbol entries (`error: null` on all 137) in both runs; `fetch_shape_note` in Run 1's manifest documents the GEV/RDDT/TEM `period=max` recovery; Run 2's manifest records `fetch_shape: "period=max"` for those three.
- Early-close sessions: recomputed from `data_4h/*.json` (137 files each run), counting (symbol, date) sessions on the comparator's `target_half_days` (`2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24`) that contain exactly one 4H bar. Both runs: 912 sessions, all with exactly one bar, zero violations. (Run 1's `STAGE_C_REPORT.md` §6 records the same 912/912 independently.)

---

## 3. The backfill — Run-1's documented gap days, filled by Yahoo before Run 2

Run 1's own report documents these two dates as vendor gap days, before any Run-2 data existed (`canonical_stage_c/STAGE_C_REPORT.md` §6):

- **2026-01-30**: 135/137 symbols had a single 4H bar (DRAM, SPCX had no history yet).
- **2026-02-02**: 134 symbols single bar; TLT had 2 bars (09:30 with n_1h=1, 13:30 with n_1h=3).
- "Every missing bar is one of the two documented gap days."

The Run-2 comparator independently rediscovers them: `stage_c_comparison.json` → `target_single_bar_gaps` = `["2026-01-30", "2026-02-02"]`.

### AAPL 1H-level proof (from the raw fetch files, not derived)

`canonical_stage_c/raw_1h/AAPL_p730.csv` vs `canonical_stage_c/run2/raw_1h/AAPL_p730.csv`:

- **2026-01-30**: Run 1 had only `09:30, 10:30` (2 hourly bars). Run 2 has all 7 (`09:30`–`15:30`). The backfilled bars complete the **13:30 4H session** (`13:30, 14:30, 15:30`) and the partial `09:30` session.
- **2026-02-02**: Run 1 had only `13:30, 14:30, 15:30` (3 bars). Run 2 has all 7. The backfilled bars complete the **09:30 4H session** (`09:30, 10:30, 11:30, 12:30`).

So each affected symbol gains exactly two 4H sessions: **2026-01-30 13:30 ET** and **2026-02-02 09:30 ET**.

---

## 4. Shift-adjusted delta distribution (131 compared symbols)

Naive rebuilt-minus-target counts mix in the systematic listing-start shift (the ±5-trading-day `allowed_start_shift` tolerance), so the meaningful delta is the comparator's shift-adjusted residual, `gap_components.residual_delta_vs_target_actual` (rebuilt 4H from effective start vs target actual, adjusted for within-tolerance start shift):

| Residual | Symbols | Share |
|---|---|---|
| **+2** | **120** | the shared backfill (the two sessions above) |
| +1 | 5 | DRAM, GEV, RDDT, SPCX, TEM |
| +3 | 3 | CRWV, GLXY, SNDK |
| 0 | 3 | AI, OXY, VLO (the frozen-Yahoo-accounting passes) |

Source: computed from all 131 entries in `stage_c_comparison.json` → `per_symbol[].gap_components.residual_delta_vs_target_actual`. Distribution = `{0: 3, +1: 5, +2: 120, +3: 3}`, summing to 131. The +1/+3/+0-residual outliers all sit inside the 13-symbol `data_drifted` set (see §5); every other symbol shows exactly the shared +2.

Nothing is missing in Run 2 relative to Run 1: the drift is purely additive backfill inside the frozen window. (The comparator's primary gap is `target_expected_4h − rebuilt_n_4h_from_effective`; the +2 pattern above is that gap's shift-adjusted residual.)

---

## 5. The 13 `data_drifted` symbols

`BMNR, CRWV, DRAM, GEV, GLXY, NBIS, RDDT, SNDK, SPCX, TEM, TLT, TMO, XYZ`

Source: `stage_c_comparison.json` → `aggregate.gate_c_stop_data_drifted` (verbatim list).

Per-symbol residual and the comparator's own explanation (`gap_components.explanation`), recomputed from the file:

| Symbol | Residual | Comparator's explanation |
|---|---|---|
| BMNR | +2 | Yahoo 1H history starts 2025-06-05 (ticker-specific boundary; systematic start 2023-10-31) |
| CRWV | +3 | Yahoo 1H history starts 2025-03-28 |
| DRAM | +1 | Yahoo 1H history starts 2026-04-02 |
| GEV | +1 | Yahoo 1H history starts 2024-09-30 |
| GLXY | +3 | Yahoo 1H history starts 2025-05-16 |
| NBIS | +2 | Yahoo 1H history starts 2024-10-21 |
| RDDT | +1 | Yahoo 1H history starts 2024-09-30 |
| SNDK | +3 | Yahoo 1H history starts 2025-02-24 |
| SPCX | +1 | Yahoo 1H history starts 2026-06-12 |
| TEM | +1 | Yahoo 1H history starts 2024-09-30 |
| TLT | +2 | one documented NaN 1H bar in Run 1 |
| TMO | +2 | Yahoo 1H history starts 2023-11-08 |
| XYZ | +2 | Yahoo 1H history starts 2025-01-21 |

These 13 stopped the stage per the frozen rule (data_drifted is a stop category). Disposition is for ChatGPT's review and Mike's audit — this report takes no position on whether any should be reclassified.

---

## 6. Run-2 input integrity (path-move verification)

The Run-2 record was moved from a one-level-too-deep nesting to its documented location (`canonical_stage_c/run2/`) before verification. The empty remnant directory `canonical_stage_c/canonical_stage_c/` confirms the move completed. All hashes below were recomputed at the final location on 2026-09-30:

1. **137/137 raw 1H files** in `run2/raw_1h/`: recomputed SHA-256 and byte counts match every entry in `run_input_lock.json` → `raw_files`. **MATCH.**
2. **Fetch manifest**: recomputed SHA-256 of `run2/fetch_4h_manifest.json` = `1118d74d4846987c47435582fafbe1f5c0a1c543d3fa0b7cec92006ce68d198a`, matching `run_input_lock.json` → `fetch_manifest_sha256`. **MATCH.**
3. **Input-lock digest**: recomputed per the documented formula in `hash_run_inputs.py` (`sha256(manifest_sha + "\n" + "name:sha256" lines, files sorted)`):
   - recorded `inputs_digest`: `1ed2af8f7998b1c9d61d23733ef50610bde9b3f21eef40cf4fd9044d7c23d32e`
   - recomputed: `1ed2af8f7998b1c9d61d23733ef50610bde9b3f21eef40cf4fd9044d7c23d32e`
   - **MATCH.**

The lock binds the manifest hash plus all 137 per-file hashes, so any byte change in the moved directory would alter the digest. It did not. The lock's own `run_dir` = `canonical_stage_c/run2`, `generated_at_utc` = `2026-09-30T01:41:50Z`, `n_raw_files` = 137.

---

## 7. What this commit publishes (evidence inventory)

Commit `4e3a7e2` published only the narrative (`research_notes/bridge_thread.md`). This commit publishes the machine evidence — all under `canonical_stage_c/run2/` (~340 KB total):

1. `fetch_4h_manifest.json` (52,125 bytes; SHA-256 `1118d74d…198a`)
2. `run_input_lock.json` (20,898 bytes; contains all 137 raw-file hashes + `inputs_digest`)
3. `build_4h_summary.json` (81,724 bytes; 189,498-bar build record)
4. `stage_c_comparison.json` (177,948 bytes; 131-symbol classifications, gate STOP)
5. This delta report (`stage_c_run2_delta_report.md`)
6. A `research_notes/bridge_thread.md` entry pointing at the above with the digest.

**Not published — by design:** `run2/raw_1h/` (69 MB, 137 CSVs) and `run2/data_4h/` (29 MB, built artifacts derivable from `raw_1h/` + the frozen build script). The input lock already freezes every raw file's SHA-256, so ChatGPT/Mike can verify byte-identity of the local `run2/` directory without the raw bytes on the bridge.

---

## 8. Open questions (for ChatGPT's review and Mike's audit)

1. Disposition of the 115 `unclassified_finding` symbols — they share one mechanical cause (the vendor backfill proven in §3–§4).
2. Disposition of the 13 `data_drifted` symbols (§5), including the four whose drift the backfill newly exposed.
3. Whether Run 2 stands as the Stage-C record with findings dispositioned, or a fresh fetch/run is required.

**Mike's gate stands: STOP is preserved; no Layer 2, no downstream reconstruction, no production change until he audits and decides.**

— Muse
