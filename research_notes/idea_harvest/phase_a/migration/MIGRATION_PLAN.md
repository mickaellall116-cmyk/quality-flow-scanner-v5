# MIGRATION PLAN + DATA — Harvest #1 → Phase A store

Status: **EXECUTED** 2026-10-13 (Phase A build, QF-IDEA-PIPELINE-PHASE-A-20261013-01 r1).
Executor: `migration_events.py` in this directory. Migration is **data + events in
the new store only** — `registry.json` was read, pinned, and asserted byte-identical
before/after (sha256 `86600c0775bccb9d…`, 90,606 bytes, 21 experiments).

## Approach

1. **Backfill first.** `registry_backfill.json` derives the family test index from
   the pinned registry blob, with explicit coverage limits (3 entries have
   `experiment_id = null`; `failure_strategy_family` populated for only 7 of 21
   entries; one documented attribution override for TimesFM). The family ledger
   in the migrated store is materialized against this same pin, so every counter
   is reproducible from the artifact.
2. **Events, not edits.** Each v1 candidate becomes an immutable idea card plus a
   `MIGRATED` event (DISCOVERED → INGESTED), followed by the events that replay
   its v1 history: `RANKED` (v1 ordinal rank), then `SHORTLISTED`,
   `BLOCKED-DATA`, or `DEDUPE_REJECT` → `REJECTED`. Nothing was silently
   upgraded or downgraded: terminal states below match the v1 record, with one
   documented classification choice (ranks 5–6, see below).
3. **Historical gaps are recorded on the cards, never papered over.** V1 did not
   capture canonical content hashes, so migrated cards carry
   `content_hash: null` + `content_hash_note` and `extractor_version: "none-v1"`.
   Phase A validation forbids those nulls for *new* intake only.

## Per-candidate mapping

| IDEA ID | v1 source | Family | Events | Terminal state |
|---|---|---|---|---|
| IDEA-2026-0001 | DRAFT-20261013-IH01 | overnight_intraday_decomposition | MIGRATED, RANKED 1 | SHORTLISTED |
| IDEA-2026-0002 | DRAFT-20261013-IH02 | lottery_max | MIGRATED, RANKED 2 | SHORTLISTED |
| IDEA-2026-0003 | DRAFT-20261013-IH03 | volume_premium | MIGRATED, RANKED 3 | SHORTLISTED |
| IDEA-2026-0004 | DRAFT-20261013-IH04 | anchoring_momentum | MIGRATED, RANKED 4, ADJACENCY_FLAG | SHORTLISTED |
| IDEA-2026-0005 | DRAFT-20261013-IH05 | intraday_momentum | MIGRATED, RANKED 5, BLOCKED | BLOCKED-DATA |
| IDEA-2026-0006 | DRAFT-20261013-IH06 | volatility_forecast | MIGRATED, RANKED 6, BLOCKED | BLOCKED-DATA |
| IDEA-2026-0007 | HARVEST_20261013 rejected list (no draft existed) | ml_price_forecasting | MIGRATED, DEDUPE_REJECT | REJECTED |
| IDEA-2026-0008 | HARVEST_20261013 rejected list (no draft existed) | trend_momentum | MIGRATED, DEDUPE_REJECT | REJECTED |

Classification choice, stated plainly: ranks 5 and 6 sat in the v1 shortlist with
an explicit "data prerequisite unmet" caveat. The design (§3.1) names exactly
these two as the `BLOCKED-DATA` archetype, so they migrated to `BLOCKED-DATA`
with the v1 caveat as the recorded reason and the shortlist history preserved in
the event reasons. They were **not** erased from the shortlist record — the
`RANKED` events and reasons carry it.

## Parked-source consequences (review fix applied to history)

- IDEA-2026-0001 (LSE repository, source class #4), IDEA-2026-0002 and
  IDEA-2026-0005 (Papers With Backtest, #5): cards carry
  `parked_primary_source: true` and a limitation stating a primary source of
  record must replace the summary/mirror before the card can be *newly*
  shortlisted on that primary alone. Their v1 SHORTLISTED state stands as
  history.
- IDEA-2026-0004 rests on a secondary summary (the primary, George & Hwang
  JF 2004, was not itself fetched in v1): `is_primary: false`, recorded on the
  card as a limitation, not hidden.
- IDEA-2026-0008 has `source.url: null` with a `url_note`: v1 recorded no URL
  for the rejected generic momentum claim class.

## Finding recorded during migration

Family-vocabulary drift: the registry records the CRT family as
`candle_range_sweep_return_intraday`; the v1 spec/harvest use the shorthand
`crt_sweep_return`. Both strings are in the killed-ideas seed so the mechanical
match fires under either vocabulary, and the drift itself is now a recorded
fact here and in the seed entry. No registry edit was made to "fix" it —
that would be a separate human-approved bookkeeping step.

## Verification (done at build time)

- Queue hash chain verifies end-to-end in `store/`.
- Drafts materializer regenerated from the log reproduces
  `store/drafts/intake_draft_20261013.json` byte-identically (4 entries:
  the four SHORTLISTED ideas; BLOCKED-DATA ideas correctly absent).
- Ledger materializer regenerated against the pinned registry reproduces
  `store/ledger/family_ledger.json` byte-identically.
- Closed families derived from the backfill + ledger:
  `candle_range_sweep_return_intraday`, `ml_price_forecasting`.

## What cutover (Phase F — NOT part of Phase A) would still need

- Point the existing `idea-harvest-weekly` cron's writer at this store layout
  in a live location, adopt `migration/store/` (or a fresh store seeded with
  these events) as the live queue, and run the first live Phase A harvest
  with a diff vs v1 behavior reviewed before it counts. None of that is done
  here: no scheduler change, no live queue.
