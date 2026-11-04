# Databento ↔ Alpaca Parity Receipt

**Run date:** 2026-11-03 (America/New_York), re-run attempt ~21:34–22:20 ET
**Status: BLOCKED — comparison NOT executed. No verdict can be issued from this run.**

Two independent blockers, each sufficient on its own:

1. **Databento authentication fails (HTTP 401)** on every endpoint and construction.
2. **The specified reference file does not exist in the archive** at the pinned commit (or at main HEAD), so the reference construction cannot be reproduced as specified.

The expected result carried in the task brief from the lost run (matched 2,055/2,055, OHLC-exact 2,055, volume-exact 2,055, 221 extra Databento bars) was **NOT reproduced and is NOT claimed here** — no Databento data was obtained and no comparison was run in this attempt.

## Window — DISCLOSED DEVIATION (for reviewer adjudication)

- Preregistration draft (`hbuy_historical_prereg_v0_1_DRAFT.md`, §5 parity gate) named **Mar 1 – Jun 28, 2024**.
- Per the task brief, in that window SPY enters the reference only 2024-06-14 and CRDO only 2024-06-17 (2 of 5 names — untestable).
- **Intended window for this re-run: May 1 – Jul 31, 2024** (all 5 names, full coverage).
- This is a disclosed deviation for reviewer adjudication. The comparison method is unchanged.
- Note: the SPY/CRDO entry dates above come from the brief's description of the lost local reference file; they could not be re-verified in this run because that file is absent from the archive (Blocker 2).

## Blocker 1 — Databento HTTP 401 (credential / account side)

Credential: `~/.databento-qfs-credentials` (JSON, key `DATABENTO_API_KEY`, mode 0600; 35 chars, `db-` prefix, no whitespace — key value never printed or logged).

| Probe | Construction | Result |
|---|---|---|
| `metadata.list_datasets` | Official `databento` pip package v0.90.0, `db.Historical(key)` | 401 `auth_authentication_failed` |
| `metadata.list_datasets` | Raw HTTPS GET, HTTP Basic (key as username, empty password) | 401 `auth_authentication_failed` |
| `metadata.list_schemas?dataset=EQUS.MINI` | Raw HTTPS GET, Basic | 401 `auth_authentication_failed` |
| `metadata.get_cost` (EQUS.MINI, SPY, ohlcv-1h, 2024-05-01→2024-08-01) | Raw HTTPS GET, Basic | 401 `auth_authentication_failed` |

Error body (all): `{"detail":{"case":"auth_authentication_failed","message":"Authentication failed.","status_code":401,...}}`

- This is identical to the ladder recorded in `DIAGNOSTIC_LOG.md` in this directory (2026-11-03 ~21:32 ET): 401 across raw Basic, Bearer, and the official client, on metadata and timeseries alike. Client-side construction error is ruled out; the failure is on the key/account side (propagation/activation lag vs. portal entitlement/plan state — not decidable from the API side).
- **No `metadata.get_cost` estimate could be obtained** (requires auth). The brief's expected ~$0.05 estimate is unverified in this run.
- **Cost actually charged: $0.00** — no successful (billable) request was made.
- No Databento pull was attempted beyond the auth probes; the hard-stop cost gate (> $25) was never reached.

## Blocker 2 — Reference file absent from qf-data-archive

Brief specified: clone `qf-data-archive` @ `db53e24554e6e5439bb937e77820f61b6f726c7e`, reference file `captures/alpaca_tier3_v1/derived_1h.json` (9,605 hourly rows, 11 symbols incl. SPY), plus `captures/alpaca_tier3_v1/merged_30min/EXCHANGE_COMPARISON.json`.

Verified by blobless fetch of the exact pinned commit and of main HEAD (`ec0e646`):

- At db53e24, `captures/alpaca_tier3_v1/` contains ONLY: `raw/full/*_30min_sip_page*.json`, `raw/smoke/IREN_30min_sip.json`, `receipt.json`, `SHA256SUMS`.
- **No `derived_1h.json` and no `merged_30min/` directory exist anywhere in the repo tree** at db53e24 or at main HEAD.
- The 11 archived symbols are AAOI, ACN, BABA, BE, BLK, COF, CRDO, IREN, MPWR, SPOT, TWLO — **SPY is not in this capture at all**, so the brief's 5-symbol set {AAOI, BE, MPWR, CRDO, SPY} cannot be built from the archived capture.
- `receipt.json` at db53e24 records derived_row_count = 1,583 per full symbol (17,511 total incl. a 98-row IREN smoke entry) from 2,939 raw 30-min bars/symbol over 227 sessions (2023-10-19 → 2024-09-13) — not the 9,605 rows the brief attributes to `derived_1h.json`. That derived file appears to have been a local artifact of the lost run, never archived.

Consequence per the brief's own stop rule: the reference construction (411 grid bars/symbol, 2,055 total) **could not be reproduced from the specified source**, so the comparison does not proceed on a reconstructed substitute.

## Comparison

- Not run. Matched bars: 0 compared. OHLC-exact: n/a. Volume-exact: n/a. Extras: n/a.
- `parity_detail.csv` contains only its header row — zero compared bars, by design (no fabricated rows).

## Verdict — values

**NOT ISSUED — blocked.** No Databento bars were obtained (401) and the specified reference file is absent from the archive. The lost run's values verdict cannot be re-certified from this attempt.

## Verdict — barset

**NOT ISSUED — blocked**, for the same reasons. The lost run's "BLOCKED — barset composition differs (221 evening-session extras)" conclusion remains an unverified carryover from the brief, not a finding of this re-run.

## Root cause

- Values/barset root cause: not applicable — no comparison ran.
- Blocker root causes: (1) Databento key/account does not authenticate against the Historical API despite a well-formed key and correct constructions — portal-side activation/entitlement state is the open question (decider: check the key's status/scope on the portal API-keys page; if active, retest after a longer propagation interval). (2) The derived reference file from the lost run was never committed to qf-data-archive; only the raw 30-min captures were archived, and SPY was never part of that capture.

## Notes

- The free-tier SIP restriction on the Alpaca side is irrelevant here — the reference is archival.
- Nothing was posted or committed in this run. The sparse reference checkout used for verification is in /tmp (ephemeral) and is not a deliverable.
- Unblock path: (a) resolve Databento portal key state and retest the auth ladder once; (b) supply or locate the lost run's `derived_1h.json` (or authorize rebuilding the reference from the archived raw 30-min pages with a SPY source identified), then re-run this comparison mechanically per the brief.
