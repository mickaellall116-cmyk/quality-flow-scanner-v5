# Alpaca Tier-3 smoke — attempt record and extended-hours adjudication item (2026-11-03)

Lane B under Mike's direct-chat GO (2026-11-03 10:39 ET, "I authorized everything through chat").
Execution package: qf-data-archive branch `claude/alpaca-tier3-execution-v1`, commit `57701d3`,
execution manifest SHA-256 `fd8b9ed73cab93aa16c51f5ef6db7c75f1c962aaf5a7b62ac774ad9600942c08`.
Mike supplied the APCA pair in direct chat; the pair was proven valid (account endpoint HTTP 200)
before the second attempt. The GitHub-secrets route is not needed for this capture.

## Attempt 1 — 2026-11-03T15:59Z — STOP / HTTP_ERROR (401), 1 call, no data

Root cause: OUR runner bug. `alpaca_capture.py` used the manifest's env-var names
(`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`) as HTTP header names. Alpaca recognizes only
`APCA-API-KEY-ID` / `APCA-API-SECRET-KEY`. The PR #11 lineage was no-call by design, so the
defect was latent and synthetic transports never caught it. Receipt: calls_used 1,
raw_sha256 `9371176869a945e2958e43b349397210a1b72b83f11c67e02e0be1f950254ef2` (error body, not archived).

Fix: header names corrected; regression test added asserting the exact wire header names and
values (`HeaderNameRegressionTests`). Offline suite: 35/35 (was 34/34). Capture code hash after
fix: `cf11e4b8b3d5f29a97aec64881a61aefea081d32d6780530b0ef9c8d54aa5865`. Manifest unchanged.

## Attempt 2 — 2026-11-03T16:01Z — STOP / OFF_GRID_BAR, 1 call, HTTP 200

Payload: 41,926 bytes, raw_sha256 `5baa2257e6b108b1e6af3f03f3ff30573fd35eb618bbe0631bc2c3be46424ccb`
(error-path receipt; payload itself not archived by the runner on STOP).

Diagnosis (one diagnostic re-pull of the identical smoke URL, retained locally only, NOT archived
as capture data): Alpaca's bars endpoint returns extended-hours bars by default. The window
returned 430 bars: 248 off-grid (premarket from 04:00 ET, after-hours to 20:00 ET) and a
regular-session subset of EXACTLY 182 bars — 13 per day × 14 sessions, zero missing stamps —
deriving exactly 98 hourly rows, matching the frozen smoke expectation in full.

## Adjudication item for ChatGPT

Reading A (Muse's recommendation): archive the raw payload byte-identical (extended-hours bars
included; nothing silently dropped). Validation substance unchanged: the frozen grid set,
from the pinned session table, must be exactly complete — any missing or duplicate grid bar
still STOPs the run; a next_page_token still STOPs. Off-grid bars are classified and counted
in the receipt as `received_excluded_off_grid`, excluded from row counts and from derivation.
Frozen counts untouched (smoke 182/98; full 2,939 rows / 1,583 derived per symbol). Runner
change covered by new offline tests (extended bars present → pass with exact counts; grid
gap → still STOP) before any re-attempt.

Reading B: declare the route spec-incompatible and stop.

No further capture calls until adjudication. Capture ≠ sealed test; the test still requires
its own authorization after capture + integrity gates.
