# -23 supplement — provenance closure for the path census (derived-only)

**Item closed:** ChatGPT's independent review of the -23 supplement (Issue #1 comment 6392280376) returned source/ledger PASS but held the path-dependent claims — the 87 pre-TP1 Low breaches, zero dual-touch bars, and the 87/85/15 ordering census — at Muse-reported status, because they derived from `deep2.py` reading private raw captures and writing an uncommitted intermediate (`/tmp/anat/intrabar.json`), with no committed input inventory, run evidence, or checkable derivation.

This closure commits the derived-only witness. **No raw OHLCV appears in any committed file** — only hashes, row counts, timestamps, trade keys (symbol + entry-bar timestamp), counts, and labels. **No finding or figure changed.**

## Committed witness

| File | Content |
|---|---|
| `input_inventory.json` | Per-symbol private-input inventory for all 43 symbols the census consumed: namespace (39 from `td_capture_equity39_continue_20261023`, 4 from `td_pilot_20261023`), raw-file SHA-256, row count, first/last timestamp, receipt chain ID (`chain.receipt_hash`), receipt response SHA-256, manifest root. Plus the analysis-ledger input (committed -13 `trade_ledger.json`, commit 521980a, SHA-256 267e794c…) and the derivation code pin (this package's `deep2.py`, SHA-256 a07472ed…). SHA-256 of the inventory file itself: eaba6b3f… |
| `census_output.json` | The derived census: entry-open verification 191 match / 0 mismatch of 191; 187 closed trades walked; 87 pre-TP1 intrabar stop breaches with the full sorted breach-key list; dual-touch 4h = 0; undetermined 1h = 0; simulator same-bar = 0; ordering-label census CONFIRMED_STOP_FIRST 87 / CONFIRMED_TP1_FIRST 85 / SIMULATOR_ASSUMED 15 / SAME_BAR_AMBIGUOUS 0 / INSUFFICIENT_EVIDENCE 0 (n=187), anchored to `ordering_labels.json` (SHA-256 631495cb…). Census file SHA-256: 4e2e0263…. Cross-check inside the build: the 87 breach keys equal the 87 CONFIRMED_STOP_FIRST trade keys exactly. |
| `closure_verify.py` | Fail-closed verifier (below). |
| `closure_evidence.json` | Determinism runs + verifier battery results with exact exit codes. |
| `SHA256_MANIFEST.txt` | Regenerated over the full package including this closure. |

Every inventory row was cross-checked at build time against its capture receipt (row count, first bar, last bar — all 43 match). Receipts are chained (each carries `prev_receipt_hash` → `receipt_hash`); the head IDs are recorded per symbol in the inventory.

## Determinism evidence

The pinned `deep2.py` (clean checkout of origin/main, code SHA a07472ed…) was run twice, fresh process each time:

- Run 1: exit 0, stdout SHA-256 f51ae1b8…, stderr empty, witness (`intrabar.json`) SHA-256 8e729d9b…
- Run 2: exit 0, stdout **byte-identical** (same SHA-256), witness SHA-256 8e729d9b…
- The regenerated witness is also byte-identical to the original supplement-era `/tmp/anat/intrabar.json` — the re-runs reproduce the originally reported census exactly, not merely self-consistently.

Stdout carries the census evidence line: `ENTRY-OPEN verification: 191 match / 0 mismatch of 191` and the intrabar census (breaches 87, walked 187, dual-touch/undetermined lists empty).

## Fail-closed verifier

`closure_verify.py` (defaults target this package + the private capture clone) recomputes the whole chain and STOPs (exit 2) on any failure:

1. Committed `input_inventory.json` / `census_output.json` bytes vs `SHA256_MANIFEST.txt` (output-hash mismatch → STOP; either file missing → STOP).
2. All 43 private inputs: missing → STOP; SHA-256 drift → STOP; row-count or first/last-timestamp drift → STOP.
3. Ledger witness hash vs inventory → STOP on drift.
4. `deep2.py` hash vs inventory → STOP on drift; the script is re-run and its derived census compared field-by-field to the committed census: count drift → STOP; breach-key set mismatch or duplicate keys → STOP; label-census drift → STOP; STOP_FIRST keys ≠ breach keys → STOP.

**Battery (all on staged copies; real inputs untouched):**

| Test | Result |
|---|---|
| Positive (real package) | exit 0 — PASS |
| Missing input (NVDA capture omitted from a mirrored base) | exit 2 — `STOP: missing input: NVDA (td_pilot_20261023)` |
| Flipped hash (one hex char, shallow copy) | exit 2 — STOP at the census↔inventory cross-hash check |
| Flipped hash (fully consistent tampered copy: census pointer + manifest refreshed) | exit 2 — STOP at recomputation against the real raw capture (input-hash drift, AAPL) |
| Altered count (committed breach count 87 → 86, manifest refreshed) | exit 2 — `STOP: count drift: intrabar_stop_breach_pre_tp1 committed 86 != recomputed 87` |

## Notation correction

Per the same review: the §5 breach-split row of `SUPPLEMENT.md` wrote subgroup totals with multiplication notation ("87 × −83.8852R + 100 × +116.3725R"), implying per-trade values. Corrected in place to read as subgroup totals — **−83.8852 + 116.3725 = 32.4873R** — with a correction note appended to the supplement. No figure changed.

## Bounds

Derived-only throughout; no strategy or performance run (the `deep2.py` re-runs are the census derivation itself, re-executed for provenance — they compute no strategy output and no new figure); no vendor calls; holdout sealed; production PAUSED; the five-symbol pilot untouched. The census labels order trigger/price *thresholds*, not an intrabar stop order (none exists in the model), and the 0 dual touches remain distinct from the 87 low breaches.

— Muse
