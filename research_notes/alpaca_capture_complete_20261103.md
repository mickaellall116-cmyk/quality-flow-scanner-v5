# Alpaca Tier-3 capture — COMPLETE (2026-11-03)

Mike's decisions, in direct chat: the Lane B GO ("I authorized everything through chat",
2026-11-03 10:39 ET), the APCA pair supplied directly (transient use; values never stored),
and "Just do it" (11:05 ET) ruling Reading A on the extended-hours question without waiting
for adjudication. ChatGPT review of this record is invited; the sealed TEST still requires
its own authorization after capture + integrity gates. Capture != test.

## Result

- Run: 2026-11-03T16:08:22Z → 16:10:51Z, run_status COMPLETE, 109 HTTP calls (1 smoke + 108 pages).
- Smoke (IREN 2024-04-04..23): 182 grid rows / 98 derived / 14 sessions, raw_sha256
  `5baa2257e6b108b1e6af3f03f3ff30573fd35eb618bbe0631bc2c3be46424ccb` — byte-identical across
  attempts 2, 3 (stopped) and the final run (deterministic payload).
- Full (11 symbols × 2023-10-19..2024-09-15): EVERY symbol exactly 2,939 grid rows / 1,583
  derived / 227 sessions; duplicates 0, missing buckets 0, nonfinite 0. Off-grid
  (extended-hours) bars classified and counted in the receipt (range: BLK 530 … BABA 4,307).
- Archive: qf-data-archive main commit `db53e24554e6e5439bb937e77820f61b6f726c7e`,
  path `captures/alpaca_tier3_v1/` — 111 files (109 raw page payloads + SHA256SUMS +
  receipt.json), 5.5 MB; SHA256SUMS verified locally before the push and the remote ref
  verified after. Every raw page is archived byte-identical.
- Execution manifest v2 SHA-256 `716c22b95b9d0fb98252e77aef83685d2da118ac346997efaf7d3ea33b096d00`
  (v1 was `fd8b9ed7…`); capture code SHA-256 (final run) `cdb19a38a8f5b4206379cfe86a8879950e7967a59959fd20c25669f4c52ca7a3`;
  rights/adjudication record unchanged `dd823c32…`. Offline suite 39/39.

## Deviations from the frozen no-call design (all transport mechanics)

The capture spec itself — symbols, endpoint, feed, timeframe, window, adjustment, asof,
limit, expected counts, pinned session table, receipt discipline — is unchanged, and
`alpaca_guard.py` (PR #11) is byte-unmodified. Three assumptions of the no-call package
proved false against the live API:

1. **Header names.** v1 sent the manifest env-var names as HTTP header names; Alpaca
   recognizes only `APCA-API-KEY-ID` / `APCA-API-SECRET-KEY`. Attempt 1 STOP (401).
   Fixed + regression test pinning the wire names.
2. **Extended-hours bars (Reading A).** Alpaca returns pre/post-market bars by default;
   the frozen "any off-grid bar = STOP" reading made the route unusable. Under Reading A,
   clean off-grid bars are classified, counted (`off_grid_count`), archived in the raw
   pages, and excluded from counts/derivation; grid completeness remains the gate
   (a missing or duplicate grid bar still STOPs — tested). Attempt 2 STOP (OFF_GRID_BAR)
   and the attempt record are in `alpaca_smoke_attempts_20261103.md`.
3. **Pagination.** The API pages this query at ~561 bars despite `limit=10000` (observed:
   AAOI page 1 = 561 bars, 2023-10-19..2023-11-27, with a next_page_token), so the frozen
   "pagination forbidden / stop on any token" rule could not retrieve the window. v2
   follows `next_page_token` continuations of the same pinned request until the token is
   null (full-phase ceiling 500 calls; a repeated token or >100 pages per symbol STOPs).
   Multi-page receipt `raw_sha256` is over the canonical merged payload, exactly
   reproducible by concatenating the archived pages' bars arrays in order.

Attempt 3 (v1 + Reading A) passed the smoke, then STOPped on AAOI's page token
(UNEXPECTED_PAGE_TOKEN) — the receipt is preserved locally with the run records.

## Package state

Execution branch `claude/alpaca-tier3-execution-v1` (commits `57701d3` v1, `99a2fb1` v2)
exists only locally: pushing it is blocked by the PAT's missing Workflows permission
(GitHub refuses workflow-file pushes without it). This affects only future GitHub Actions
runs; the capture itself ran locally under the same code and manifest.

## What remains

- Independent verification of the archived capture against the frozen expectations
  (recompute grid/derived counts from the archived pages) — Claude/ChatGPT lane.
- The sealed Tier-3 TEST: separate authorization, after integrity gates.
