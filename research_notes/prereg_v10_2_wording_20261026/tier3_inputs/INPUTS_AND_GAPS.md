# Tier 3 Inputs (v1.0.1, wording-corrected by v1.0.2) — Inventory, Provenance, and the S4 Completeness Statement

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
| `generate_tier3_list_v1_2.py` | Generator v1.2.1 — local-input-only, hash-pinned, aborts (exit 2, no output) on a missing or hash-mismatched input; step-8 derivation restated as a residual list by the v1.0.2 wording amendment (selection logic unchanged from v1.2) | `5a1e074539645f687c4b54842b63dedbdf51fdf12cad0a64221ace4bf7d01fa6` |
| `tier3_list_v1_2.json` | Residual Tier 3 list (output of generator v1.2.1) — the `tier3_list` array is byte-identical to the v1.2 output (sha `fbb73446…`); the container hash differs only by the v1.0.2 label/wording corrections and the added `derivation` / `rank_12` fields | `08b670c43b68e38d0fb720dddb6b90710e8acefe7d37f34ad485613a560d2bbd` |
| `test_rank12_fixture.py` | Fixture (v1.0.2): asserts the unknown rank-12 slot remains explicitly empty, the corrected `aggregate_not_persisted__not_re_evaluated` label is used, and the list is exactly the residual top-11 | (in package manifest) |

Licensing note: S1/S2 are NASDAQ Trader's publicly posted symbol
directories and S3 is NASDAQ's public screener export; all three were
retrieved 2026-10-26 for internal research documentation and are committed
here as the immutable evidence of the selection inputs.

## Reproduction

```
python3 build_issuer_map.py          # regenerates ISSUER_MAP.json byte-identically
python3 generate_tier3_list_v1_2.py  # regenerates tier3_list_v1_2.json byte-identically
python3 test_rank12_fixture.py       # asserts the rank-12 slot stays explicitly empty
```

The generator was run twice during preparation of the v1.0.1 amendment
(output SHA-256 `fbb73446…` both times) and twice again, as v1.2.1,
during the v1.0.2 wording amendment (output SHA-256 `08b670c4…` both
times; the `tier3_list` array is byte-identical to the v1.2 output —
only labels, version strings, and the added `derivation` / `rank_12`
fields differ). `build_s4_table.py` reads the captured run outputs from the Tier 3
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
  (The generator's stage count of 2,549 candidates with no frozen row —
  2,560 step-7 candidates under v1.2/v1.2.1 after GOOG's step-6b removal,
  minus the 11 with persisted rows — decomposes as these 2,539
  computed-but-not-retained candidates plus the 10 original
  fetch-failed-or-short symbols; under the corrected v1.0.2 label all
  2,549 are `aggregate_not_persisted__not_re_evaluated`.)
- The identities of the remaining 3 `fetch_failed_or_short` symbols
  (data returned but fewer than 20 valid bars; named in no output or log).
- The exact per-symbol session dates of the 20 bars behind each aggregate
  (only the window 2026-09-01..2026-10-25 and the bar count were recorded).

**Consequence (restated by the v1.0.2 wording amendment, C1 re-review
comment `6429562606`).** The 2,549 candidates lacking a persisted S4
aggregate were **not feed failures and are not rule-ineligible symbols**:
their aggregates were computed by the v1.0/v1.1 generator but not
retained (2,539 of them), or their original fetch failed / returned too
few bars (10). The v1.0.1 wording that called them "ineligible
(fail-closed) — the same treatment rule v1.0 gives a symbol whose bars
cannot be fetched" conflated evidence loss with eligibility and is
superseded. Under generator v1.2.1 they are recorded as
`aggregate_not_persisted__not_re_evaluated`: not re-evaluated, because
the frozen record cannot support re-evaluation. The step-8 output is
therefore a **residual-list derivation, not a complete step-8
eligibility rerun**: the original proven top-12 (the persisted
aggregates) minus the issuer-ineligible GOOG (step 6b) = a **known
residual top-11; rank 12 is unknowable** from the frozen record and is
recorded as an explicitly empty slot. That shortfall is carried as
freeze-checklist open item **O9** (owner: Mike) rather than filled by
any non-mechanical means.
