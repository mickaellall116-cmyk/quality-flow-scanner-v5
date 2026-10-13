# TD integration review — evidence package (2026-10-12)

Packaged 2026-10-13 per ChatGPT evidence intake, Issue #1 comment `6136948813`.
**Packaging only:** verbatim copies of the review's existing scratch tree.
Nothing was rerun, regenerated, or modified — neither the repair candidate
(`af49bf4`) nor the original collector (`411457d`). `diff -r` against the
source scratch tree verified the copy is byte-identical (208 files, ~1.7 MB).

## Source

- Scratch tree: `/tmp/tdreview/` (still present at packaging time).
- Review report: `research_notes/TD_INTEGRATION_REVIEW_20261012.md`
  (blob `6ac362b9007f54e2900494dcb02684a37c415413`).
- Candidate under review: PR #8, commit
  `af49bf4a65acca08876a4bd9823a945ca8aa3d17`,
  `research_notes/td_lifecycle_repair_candidate/`.

## Contents

| Path | What it is |
|---|---|
| `run_integration.py` | Main scenario driver (scenarios S0, S0b, a, b1, b2, c, d, f, g) against the actual pinned dependencies. |
| `run_h_driver.py` | Scenario-h driver (tampered pinned source, run against `run_h/`). |
| `prereq.json` | Prerequisites file used by the runs (copy of the `411457d` `prerequisites.json`: plan Basic, retention `BOUNDED_RESOLVED`). |
| `cand/` | Candidate files exactly as archived from `af49bf4` (README, `td_min_collector.py`, `test_lifecycle_repair.py`, `test_output.txt`). |
| `orig/` | `411457d` extract: `pilot_harness/` (incl. synthetic fixtures + `tests/synthetic_test_output.txt`) and `td_minimal_collector/` (original collector, reduced manifest, prerequisites). |
| `run/` | The executed tree: actual-dependency `pilot_harness/` + candidate copy + archival sources (`recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/`), incl. `__pycache__` from the run. |
| `run_h/` | Scenario-h copy of the executed tree (with the tampered `scanner_rules.py`). |
| `scenarios/` | Per-scenario persisted outputs: `lifecycle.jsonl`, `receipts/`, `pilot_state.json`, `ledger.json`, `manifest_binding.json` for s0, sa, sb1 (start_date/adjust/order/outputsize/venue), sb2, sc, sd, sf, sg. |
| `scen_h/` | Scenario-h state remnants (`collector.lock`, empty `receipts/`). |
| `pins/` | Empty directory in the scratch tree; nothing to package. |

**Output note (honest gap in the scratch record):** `run_integration.py`
prints its final RESULTS JSON to stdout (line 176); that stdout was not
separately persisted to a file in the scratch tree. The persisted outputs
packaged here are the per-scenario state artifacts under `scenarios/` and the
`test_output.txt` / `synthetic_test_output.txt` files in the trees above. The
scenario outcomes as reported are in the review report itself.

## Environment pins (from the review report)

- Python 3.12.3, pandas 2.1.4, numpy 1.26.4, pytest 9.1.1.
- **`pandas_market_calendars` NOT installed** in the review environment
  (`ModuleNotFoundError`) — see standing gaps.
- Dependency blob pins, all verified MATCH against the scratch copies before
  the original run:
  - `pilot_harness/verify_sources.py` — `fd03906` blob `0732b1f48f34d867c86d1cfd9ccddca864f12bb3`
  - `pilot_harness/validate_input.py` — `fd03906` blob `74424d2a41bc86a334f3525801aa899082953f4d`
  - `pilot_harness/rate_limiter.py` — `fd03906` blob `bf8a7db115a272029035dfb09905d1962f3dfebc`
  - `pilot_harness/construct_4h.py` — `fd03906` blob `fe76c48a22514e073e232811880fd82d963e54f1`
  - Candidate `td_min_collector.py` (+ tests, README) — per-commit blobs at `af49bf4`
  - Archival `pine_backtest.py` — `verify_sources.PINNED` SHA-256 `447a9a13…d160e5`
  - Archival `scanner_rules.py` — `verify_sources.PINNED` SHA-256 `7db282df…0cac`
- Limiter: real `RollingCreditLimiter(8, 800)` persisted per scenario.
- Manifests: explicit venue manifest (`venue_identity = {exchange: NASDAQ, currency: USD}`).
- Transport: in-process callable returning synthetic bytes. Zero vendor calls,
  zero credits, zero spend.

## Elapsed time of the original review (as reported)

- Spawn: ~22:07 EDT, 2026-10-12 (Mike's direct authorization, main chat).
- Completion reported: ~22:11 EDT, 2026-10-12.
- That is ≈4 minutes wall-clock **as reported**; the review was not
  independently instrumented, and no finer precision is claimed. (ChatGPT's
  intake asked for actual elapsed minutes within the original 30-minute
  review allocation; this packaging was performed inside that remaining
  allocation, packaging only.)

## Standing gaps — NOT closed by this package

1. **XNYS 1H calendar completeness UNTESTED.** `pandas_market_calendars` is
   absent, so the real 1H session-completeness path (seven-constituent check)
   was never exercised; 1H requests fail closed (`HOLD: … No module named
   'pandas_market_calendars'`). No stub was substituted.
2. **Venue mapping unverified.** Venue identities in the manifests were not
   checked against provider documentation.
3. **Transport is a separate unresolved gate.** The candidate has no HTTP
   client by construction; any transport enabling needs its own separately
   reviewed adapter. No vendor response shapes, real-account credit
   accounting, or HTTP behavior were tested.
4. **Reproducibility HOLD.** Independent reproducibility remains HOLD until
   ChatGPT can rerun from this packaged evidence. This package does not
   upgrade acquisition readiness: no P4 clearance, no merge, no vendor calls,
   no new repair round.

— Muse (packaging only, 2026-10-13)
