# ERD v0.1 — 50-event timing-integrity audit

Frozen gate: `../erd-v0.1-preregistration-amendment-1.md`, section 15 (DATA GATE).
This directory holds the audit tooling and, once run, the audit log.

**The frozen gate criteria are unchanged by anything in this directory:**
50 events, ≥10 BMO, ≥10 AMC, ≥8 calendar years, ≥48/50 exact date+bucket
matches, ≥90% valid timing coverage, no systematic backfill/revision pattern.
What changed (ChatGPT reviewer PASS decision, 2026-09-25) is the *hardening of
the audit mechanics*: reproducibility infrastructure and synthetic edge-case
coverage. This harness generates zero performance data.

## Workflow

1. **Fetch** (needs `INTRINIO_API_KEY` in the environment — never committed):
   ```
   python3 audit_harness.py fetch --start 2005-01-01 --end 2026-06-30 \
       --out raw_surprises.json
   ```
   Pulls the frozen Zacks EPS Surprises feed. No other earnings-calendar
   source may be substituted (frozen no-substitution rule). The harness
   computes SHA-256 over the raw record payload and stores it as `raw_hash`
   inside the output file (control C2).

2. **Verify** raw integrity at any time:
   ```
   python3 audit_harness.py verify --in raw_surprises.json
   ```
   Prints `OK` or `TAMPERED` (exit 1). Any edit to the vendor data after
   fetch is detected.

3. **Sample** — deterministic stratified draw honoring the frozen strata
   (50 events, ≥10 BMO, ≥10 AMC, ≥8 calendar years):
   ```
   python3 audit_harness.py sample --in raw_surprises.json --seed 20260925 \
       --out audit_sample.json
   ```
   `sample` first verifies `raw_hash` and REFUSES on mismatch. The used seed
   and a SHA-256 `sample_hash` (canonical serialization of each row's vendor
   fields) are recorded in the output (control C1). The sample is final —
   see the no-replacement rule below.

4. **Sheet** — build the human verification worksheet:
   ```
   python3 audit_harness.py sheet --in audit_sample.json \
       --out verification_sheet.csv
   ```
   `sheet` recomputes `sample_hash` from the sample rows and REFUSES on
   mismatch. The sheet header embeds the precommitted evidence-precedence
   rules (control C4) before any human examines evidence. A human then
   verifies each row's `actual_reported_date`, `actual_reported_time`, and
   timing bucket against the primary source and fills: `primary_source_type`,
   `primary_source_url`, `verified_date`, `verified_time`, `verified_bucket`,
   `date_bucket_match_YN`, `notes`. The vendor columns must not be edited —
   `score` re-hashes them against the committed `sample_hash`.

5. **Score** — apply the frozen pass criteria:
   ```
   python3 audit_harness.py score --in verification_sheet.csv
   ```
   `score` recomputes `sample_hash` from the sheet's vendor columns and
   REFUSES on mismatch (or a missing hash header). PASS requires ≥48/50
   exact date+bucket matches and ≥90% valid timing coverage, plus a manual
   read of the mismatch breakdown for systematic revision/backfill patterns.

6. **Commit** the filled sheet + score report to the repo **before** any
   performance work begins. Gate FAIL → stop, report, ERD halts.

## Integrity controls (reviewer-mandated, 2026-09-25)

- **C1 — sample hash before evidence examination.** `compute_sample_hash()`
  hashes the canonical vendor-field projection of every sampled row
  (event_id, ticker, intrinio_reported_date/time/code, derived_bucket).
  Stored in `audit_sample.json` and in the sheet header; `sheet` and
  `score` recompute and refuse on mismatch.
- **C2 — raw vendor data immutability.** `fetch` stores `raw_hash`;
  `sample` verifies it first; `verify` re-hashes on demand.
- **C3 — no-replacement rule.** The 50 sampled events are final. A sampled
  event that turns out missing/ambiguous is scored as a non-match and counts
  against coverage per the frozen rules (missing/ambiguous timing →
  EXCLUDE). It is NEVER replaced with a convenient substitute, and no code
  path exists that swaps sampled events. Re-running with a new seed after
  seeing the draw to dodge inconvenient events is prohibited.
- **C4 — precommitted evidence precedence** (`EVIDENCE_PRECEDENCE` in
  `audit_harness.py`, printed into every sheet header):
  1. Company IR press-release timestamp (highest)
  2. Newswire timestamp (Business Wire / PR Newswire)
  3. NYSE official calendar: that day's actual regular-session open/close
     (early closes honored)
  4. Intrinio/Zacks vendor fields (lowest — the data under audit)
  
  Conflicts between 1–2 resolve to the earliest published timestamp; vendor
  code vs timestamp-derived bucket disagreement → ambiguous → EXCLUDE.

## Files

- `audit_harness.py` — fetch / verify / sample / sheet / score + controls C1–C4.
- `event_clock.py` — the frozen §1 event clock, implemented exactly as
  specified (actual NYSE open/close per day as inputs; before open → S=D;
  during [open, actual close] → EXCLUDE; exactly-at-close → EXCLUDE; after
  close → next session; weekend/holiday → next session; missing/ambiguous →
  EXCLUDE; code/timestamp disagreement → EXCLUDE). NYSE calendar lookup is
  out of scope — the caller supplies the day's actual session times.
- `test_edge_cases.py` — synthetic edge-case suite (stdlib unittest, no
  network): the exact §1 vectors (08:59, 09:30, 12:00, 15:59, 16:01 ET,
  Saturday, plus the 13:00 ET early-close case), DST spring-forward/fall-back
  weekends, exact-close timestamps, code/timestamp conflicts, missing timing,
  ticker-change/delisting identity, tampered raw files, sample-hash mismatch
  refusals, and the no-replacement scoring rule.
  Run: `python3 -m unittest test_edge_cases -v` (32 tests, all passing
  2026-09-25).

## What this is not

This harness generates zero performance data. It is a data-integrity gate,
the only ERD operation permitted before the gate passes.
