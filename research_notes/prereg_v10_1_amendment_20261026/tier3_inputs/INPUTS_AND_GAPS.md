# Tier 3 Inputs (v1.0.1) — Inventory, Provenance, and the S4 Completeness Statement

This directory makes the Tier 3 selection reproducible **from the committed
package alone** (C1 finding 1): every input the generator reads is here,
hash-pinned inside the generator itself, and the generator refuses to run
on a missing or hash-mismatched input (verified: tampered S4 table →
exit 2; missing issuer map → exit 2; no output file is written on failure).

## Inventory

| File | Role | SHA-256 |
|---|---|---|
| `sources/nasdaqlisted.txt` | S1 — NASDAQ Trader symbol directory, File Creation Time 2026-10-26 15:41 ET | `8e72f822228a2536b0e712e5ee91c14e30db07408cc8863a6d64cb1bac1c2c19` |
| `sources/otherlisted.txt` | S2 — NASDAQ Trader symbol directory (other exchanges), same date | `67c1e321790341bf89172e2dc30119e1a39180d3dd4b2d7cb4e420ba02305ca6` |
| `sources/nasdaq_screener_raw.json` | S3 — NASDAQ screener export (IPO year), retrieved 2026-10-26 | `464e82847212024e3c2b871c487c4ac6a3af854763f82dbd124ed4987b39b912` |
| `exclusion_universes.json` | Step 6 input — UX51 (51) ∪ X2 (199) prior-study symbols | `c7112909009aa605a380b198d07b3ebd421fa44ce5a4751e830c8496ca535e04` |
| `ISSUER_MAP.json` | Step 6b input — issuer equivalents of all 250 prior-study symbols | `3bccdbf27bbfd0c89810ee16169bdd149b7351a5370995bcd26d7d0d1ad1ed85` |
| `S4_FROZEN_AGGREGATES.csv` | Step 8 input — frozen S4 aggregates (see completeness statement) | `d345fbabeec144f50f117f4d2a6ae7b947e8acb0a4604af64fa869ed25bbd595` |
| `build_issuer_map.py` | Builds `ISSUER_MAP.json` from S1/S2/S3 + exclusion file (offline) | `b9ae9b3644c39341d801212e4d3e80da53bfa2ae1907941003d00a55b673a4c5` |
| `build_s4_table.py` | Builds `S4_FROZEN_AGGREGATES.csv` from the captured run outputs (offline; fail-closed on hash/selection mismatch) | `e726d909cdb227c965b9c04636b832113115fe77db896bd1c50de26d7a9fb146` |
| `generate_tier3_list_v1_2.py` | Generator v1.2 — local-input-only, hash-pinned, fail-closed | (in package manifest) |
| `tier3_list_v1_2.json` | Regenerated Tier 3 list (output of v1.2) | `fbb734465ef7a0b05398d519dd847795b4cdcc3a63dd59e2f0ee8773ed190f48` |

Licensing note: S1/S2 are NASDAQ Trader's publicly posted symbol
directories and S3 is NASDAQ's public screener export; all three were
retrieved 2026-10-26 for internal research documentation and are committed
here as the immutable evidence of the selection inputs.

## Reproduction

```
python3 build_issuer_map.py          # regenerates ISSUER_MAP.json byte-identically
python3 generate_tier3_list_v1_2.py  # regenerates tier3_list_v1_2.json byte-identically
```

Both were run twice during preparation of this amendment; outputs were
byte-identical across runs (generator output SHA-256 `fbb73446…` both
times). `build_s4_table.py` reads the captured run outputs from the Tier 3
staging directory (outside this package) and refuses to build if the three
agreeing outputs are not byte-identical to the frozen hash or if run 2's
selection differs; inside this package the CSV itself is the frozen
artifact.

## S4 completeness statement — what exists, what is missing (precise)

S4 in rule v1.0 is "Yahoo Finance daily bars, 2026-09-01 → 2026-10-25",
fetched live by generator v1.0/v1.1 on 2026-10-26 for the 2,561 step-7
candidates (see `../ERRATUM_PROVENANCE.md` for the corrected provenance of
those fetches). The generator computed each candidate's aggregates in
memory and **persisted only the 12 selected symbols' aggregates** (plus
stage counts) in its output JSON. No candidate price series was stored.

**What exists (frozen in `S4_FROZEN_AGGREGATES.csv`):**

- ADV20, last close, and bars used (= 20) for the 12 originally selected
  symbols — identical in runs 1, 3, 4 (output SHA-256 `9e7ae052…`) and
  identical as a selection in run 2.
- Per-run stage counts: 2,561 step-7 candidates; `fetch_failed_or_short`
  = 10 (runs 1/3/4) or 15 (run 2, transient feed drops); 797 candidates
  passed the step-8 cutoffs (795 in run 2).
- The identities of 7 of the 10 permanent fetch failures, named in the run
  logs: AXG, COCH, ENLV, HCTI, IPW, PARA, SXTC (no data returned).

**What is missing (never persisted, not recoverable offline):**

- Per-symbol aggregates for the other 2,549 candidates. 2,551 candidate
  aggregates were computed in memory per run (2,561 − 10 failures); only
  the top 12 were written out, so **2,539 computed aggregates are lost**,
  including the identity and ADV20 of rank 13 and of every rank below 12.
- The identities of the remaining 3 `fetch_failed_or_short` symbols
  (data returned but fewer than 20 valid bars; named in no output or log).
- The exact per-symbol session dates of the 20 bars behind each aggregate
  (only the window 2026-09-01..2026-10-25 and the bar count were recorded).

**Consequence.** The step-8 ranking is reproducible from the frozen record
only down through the persisted top 12. Under generator v1.2, a candidate
with no frozen aggregate row is ineligible (fail-closed — the same
treatment rule v1.0 gives a symbol whose bars cannot be fetched). After
step 6b removes GOOG, **11 names are fully determined by the frozen
record; the 12th slot is not determinable offline.** That shortfall is
carried as freeze-checklist open item **O9** (owner: Mike) rather than
filled by any non-mechanical means.
