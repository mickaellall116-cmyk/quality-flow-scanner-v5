# ERD v0.1 — 50-event timing-integrity audit

Frozen gate: `../erd-v0.1-preregistration-amendment-1.md`, section 15 (DATA GATE).
This directory holds the audit tooling and, once run, the audit log.

## Workflow

1. **Fetch** (needs `INTRINIO_API_KEY` in the environment — never committed):
   ```
   python3 audit_harness.py fetch --start 2005-01-01 --end 2026-06-30 \
       --out raw_surprises.json
   ```
   Pulls the frozen Zacks EPS Surprises feed. No other earnings-calendar
   source may be substituted (frozen no-substitution rule).

2. **Sample** — deterministic stratified draw honoring the frozen strata
   (50 events, ≥10 BMO, ≥10 AMC, ≥8 calendar years):
   ```
   python3 audit_harness.py sample --in raw_surprises.json --seed 20260925 \
       --out audit_sample.json
   ```
   The used seed is recorded in the output for reproducibility.

3. **Sheet** — build the human verification worksheet:
   ```
   python3 audit_harness.py sheet --in audit_sample.json \
       --out verification_sheet.csv
   ```
   A human then verifies each row's `actual_reported_date`,
   `actual_reported_time`, and timing bucket against the primary source
   (company IR press release, Business Wire / PR Newswire / newswire
   timestamp) and fills: `primary_source_type`, `primary_source_url`,
   `verified_date`, `verified_time`, `verified_bucket`,
   `date_bucket_match_YN`, `notes`.

4. **Score** — apply the frozen pass criteria:
   ```
   python3 audit_harness.py score --in verification_sheet.csv
   ```
   PASS requires ≥48/50 exact date+bucket matches and ≥90% valid timing
   coverage, plus a manual read of the mismatch breakdown for systematic
   revision/backfill patterns.

5. **Commit** the filled sheet + score report to the repo **before** any
   performance work begins. Gate FAIL → stop, report, ERD halts.

## What this is not

This harness generates zero performance data. It is a data-integrity gate,
the only ERD operation permitted before the gate passes.
