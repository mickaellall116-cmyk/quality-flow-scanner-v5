# EDGAR 10-event feasibility pilot — WORKING NOTES (report to be finalized)

**Status:** in progress. Selection rule frozen prospectively (see edgar_pilot_selection_rule_20260930.md).
Draw executed with seed 20260930 BEFORE any EDGAR pull.

## Draw results (seed 20260930, single stream, draw order)

| # | Ticker | Year | Q | Announcement window | CIK |
|---|--------|------|---|---------------------|-----|
| 1 | MMM | 2019 | Q3 | 2019-07-01 → 2019-09-30 | 66740 |
| 2 | JNJ | 2018 | Q4 | 2018-10-01 → 2018-12-31 | 200406 |
| 3 | AAPL | 2022 | Q1 | 2022-01-01 → 2022-03-31 | 320193 |
| 4 | JPM | 2015 | Q1 | 2015-01-01 → 2015-03-31 | 19617 |
| 5 | CAT | 2016 | Q3 | 2016-07-01 → 2016-09-30 | 18230 |
| 6 | AMZN | 2020 | Q4 | 2020-10-01 → 2020-12-31 | 1018724 |
| 7 | NKE | 2024 | Q3 | 2024-07-01 → 2024-09-30 | 320187 |
| 8 | TRV | 2025 | Q1 | 2025-01-01 → 2025-03-31 | 86312 |
| 9 | TRV | 2012 | Q4 | 2012-10-01 → 2012-12-31 | 86312 |
| 10 | VZ | 2017 | Q1 | 2017-01-01 → 2017-03-31 | 732712 |

10 distinct years. Fixed denominator 10.

## Access notes

- SEC WAF blocked curl entirely (403) and most browser fetches (data.sec.gov, cgi-bin,
  per-accession Archives pages). Working: /files/company_tickers.json, /Archives/edgar/data/{cik}/
  directory listings (used to identify candidate accessions by last-modified date).
- After a burst of requests the WAF began 403ing previously-working paths (rate limiting).
  Paused all SEC traffic ~5 min; canary re-test pending.
- Wayback playback (web.archive.org) returned 500s for the filing index snapshot; availability API worked.

## Per-event findings

(pending access restoration)
