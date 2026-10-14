# PHASE A BUILD RESULT — QF-IDEA-PIPELINE-PHASE-A-20261013-01 r1

Status: **COMPLETE within budget.** Schema/store only, per
`PHASE1_DESIGN_PACKAGE_20261013.md` Phase A as amended by the review fixes in
Issue #1 comment `6155160682`. Authorization: ChatGPT conditional-PASS work
order; Mike's standing rule (2026-10-13 20:49 EDT) that the Muse↔ChatGPT
research loop is auto. Location: `research_notes/idea_harvest/phase_a/`.
Commit-ready only — nothing committed by the builder.

## What was built

| Component | File(s) | Notes |
|---|---|---|
| Store core | `store.py` (store `phase-a-store/1.0.0`) | Validators; immutable write-once idea cards; append-only hash-chained JSONL queue (single-line append + fsync); atomic lease (`O_CREAT|O_EXCL`, stale break logged as `LOCK_BROKEN`); legal-transition state machine; deterministic draft + family-ledger materializers (byte-stable, verified). Zero network code — no socket/urllib/requests anywhere. |
| Killed-ideas seed | `killed_ideas_seed.json` (`killed-seed/1.0.0`) | 10 entries from the v1 standing list (TOP/composite filters, laggard veto, MA probes, short-side daily, path-signature, CRT, TimesFM family, trend-momentum reparam, ORB-beyond-HOLD, VCP-beyond-1A) as versioned data. |
| Source registry | `sources.json` (`sources/1.0.0`) | All 7 design sources + `SOURCE_CHAT`; #2 SSRN, #4 OA repositories, #5 Papers With Backtest marked `PARKED-SOURCE` with reasons; `SOURCE_CHAT` is an intake channel that enters only through the single writer. |
| State mapping | `state_mapping.json` (`state-mapping/1.0.0`) | Queue and registry vocabularies separate; only SHORTLISTED maps to a registry-shaped draft (`DRAFT-INTAKE-NOT-MERGED`); PREREGISTERED/ELIGIBLE are named forbidden targets. |
| Unit tests | `tests/test_store.py`, output `tests/tests_output.txt` | 20 tests: canonical-text/hash stability, dedup-key normalization, all validators, ingest/transitions, lease, chain tamper, materializer determinism, registry-write refusal. **20/20 PASS.** |
| Fixtures | `fixtures/run_fixtures.py`, outputs `fixtures/fixtures_output.txt` + `fixtures/fixtures_rerun_output.txt` | F1–F5 (design §6) + F6 chain-tamper refusal, F7 adjacency flag, F8 SOURCE_CHAT channel. **8/8 PASS**, and a clean independent rerun produced a **byte-identical** output file (same sha256). |
| Registry backfill | `migration/registry_backfill.json` | Family index over the pinned registry blob (sha256 `86600c0775bccb9d…`, 90,606 B, 21 experiments) with explicit coverage limits: 3 entries lack `experiment_id`; family field populated for only 7/21; one attribution override (TimesFM → `ml_price_forecasting`). Derived closed families: `candle_range_sweep_return_intraday`, `ml_price_forecasting`. |
| Harvest #1 migration | `migration/store/` (8 cards, queue log, drafts, ledger) + `migration/MIGRATION_PLAN.md` + `migration/migration_events.py` | MIGRATED events replay the v1 record: 4 SHORTLISTED, 2 BLOCKED-DATA (v1 ranks 5–6, documented classification), 2 REJECTED (the v1 dedupe rejects, now permanent failure memory). Chain verifies; both materializers regenerate byte-identically. `registry.json` asserted sha-identical before/after. |

## Review fixes — how each was implemented

1. **`access_basis`, never inferred licenses** — card field renamed; a
   `license` key in `source` is a hard validation error.
2. **Canonical-text content hash + extractor version** — `canon-extract/1.0.0`
   (tag-strip, NFC, casefold, whitespace-collapse); hash + extractor version
   recorded on every new card; raw bytes never hashed.
3. **No automated semantic verdict** — dedupe outcomes are exact-key
   DUPLICATE_SEEN, mechanical seed/closed-family rejects with the matched
   record cited, or `ADJACENCY_FLAG` for human confirmation. There is no
   similarity scoring anywhere in the code.
4. **Registry backfill with explicit blob/coverage limits** — see above;
   limits are data in the artifact, not fine print.
5. **Harvest #1 migration via MIGRATED events** — see above; nothing edited,
   everything replayed as events over immutable cards.
6. **Sources #2/#4/#5 PARKED-SOURCE** — enforced by the validator for new
   intake; migrated cards resting on parked primaries are flagged
   (`parked_primary_source`) with the consequence recorded as a limitation.
7. **SOURCE_CHAT only through the single writer** — channel record in
   `sources.json`; the store has exactly one ingest path, exercised under the
   lease; fixture F8 checks this structurally.
8. **Existing cron reused** — `idea-harvest-weekly` untouched; no scheduler
   change, no cutover, no live queue (the migration store is a data
   artifact, not a live queue).
9. **Separate queue/registry vocabularies** — `state_mapping.json`; joined
   only by `idea_id` in materialized drafts.
10. **Unique per-attempt run/event IDs** — run IDs sequenced from the log
    (`RUN-YYYYMMDD-NNN`, store refuses reuse via the log record); event IDs
    globally monotonic (`EVT-YYYYMMDD-NNNNN`).
11. **DUPLICATE_SEEN semantics** — exact-key re-ingestion appends
    `DUPLICATE_SEEN` citing the existing idea + state; no card, no ID
    (fixture F1, and F4a for a rejected original).
12. **Safe atomic lease/lock** — `O_CREAT|O_EXCL` lockfile with pid/run/
    timestamp; stale = >2 h or dead pid; break is logged (fixture F2);
    a live lease refuses a second writer (unit test).
13. **Crash-safe JSONL/hash-chain writes** — append + flush + fsync per
    event; chain verified before every append; tamper aborts the run, never
    silently repaired (fixture F6).
14. **Tests in every phase** — 20 unit tests + 8 fixtures cover this phase's
    surface (the only phase in this work order).

## Fixture results (scratch stores, canned inputs, injected clocks)

- **F1 Duplicate ingestion — PASS.** 3 submissions → 1 card, 2
  `DUPLICATE_SEEN` events, no extra IDs, chain verifies.
- **F2 Restart idempotency — PASS.** Simulated crash (no RUN_END, stale
  lease) → lease broken + `LOCK_BROKEN` logged, ID sequence recovered from
  the log tail (next ID 0002, no reuse), crashed idea kept exactly once,
  log prefix byte-preserved (append-only).
- **F3 Source failure — PASS.** `SOURCE_DOWN` logged, run completes;
  parked-source candidate and unverifiable (non-primary) candidate dropped;
  exactly 1 healthy card.
- **F4 Rejected idea — PASS.** Identical claim → DUPLICATE_SEEN of the
  rejected record; re-parameterized variant → DEDUPE_REJECT citing
  `KILLED-ML-PRICE-FORECASTING`; original rejection event byte-identical
  before/after; nothing reaches the shortlist.
- **F5 Blocked gate — PASS.** PREREGISTERED and ELIGIBLE transitions
  refused + logged as ERROR events; registry write attempt raises
  ScopeViolation; idea remains SHORTLISTED; scratch registry hash unchanged.
- **F6 Chain tamper — PASS.** One edited log line → hash-chain mismatch →
  writer aborts.
- **F7 Adjacency flag — PASS.** Known-family candidate ingested with
  `ADJACENCY_FLAG`; no verdict produced.
- **F8 SOURCE_CHAT channel — PASS.** Structural: channel record present
  with the single-writer rule; store has one ingest path and no network code.

## Effort vs cap

- **Cap: 3 agent-hours, incl. ≤30 min local repair. Used: well under cap**
  (single build session; all runs local and sub-second). One repair pass
  was used, all local corrections, no schema or state-machine change:
  (a) fixture F3 exposed that a non-primary candidate could be carded —
  the validator now requires `is_primary = true` for new intake (a claim
  not verifiable from a primary source is dropped, per design);
  (b) two migration-script bring-up fixes (an f-string quoting error and
  an unused-field KeyError), after which the partial migration store from
  the crashed run was deleted and rebuilt cleanly.
- Stop conditions: none triggered. No prohibited-list need arose.

## Deviations and findings (stated plainly)

1. **Event-type additions** beyond the design §2.2 enum, all required by
   the review fixes: `DUPLICATE_SEEN`, `ADJACENCY_FLAG`, `LOCK_BROKEN`,
   `MIGRATED`, `RECHECKED`, `ERROR`. Documented in `store.py`.
2. **Ranks 5–6 classification**: v1 shortlisted both with a data caveat;
   migrated as `BLOCKED-DATA` per the design §3.1 archetype, with the
   shortlist history preserved in event reasons (see MIGRATION_PLAN.md).
3. **Family-vocabulary drift found**: registry records the CRT family as
   `candle_range_sweep_return_intraday`; v1 docs use `crt_sweep_return`.
   Both strings are seeded so mechanical matching fires under either.
   No registry edit was made.
4. **Migrated-card nulls**: `content_hash: null` (+ note) and one
   `source.url: null` (rank-8 rejected generic claim) — v1 never captured
   them; new-intake validation forbids both.
5. Nothing else deviates: no fetcher, no scheduler change, no live queue,
   no Phase B work, no registry modification.

## File pins (sha256, build outputs)

```
2443dfa14d0c0b9ca756732221daa6d39545c636bafeba1d3bc46457f07f19ee  store.py
a314f16e8586bcee1bdc7f1a1ae415b45f56c178ea07923bb8545d09dcc05625  killed_ideas_seed.json
0e9b62e81d9a1f3d66e58f984e360dec0c8084c6c945eba09762781a987e044f  sources.json
d4000a7466f637b67b65409eb935886d63d3d3d8c18129a4da629cf2604f702d  state_mapping.json
2d196fec521f8f20c93db8d67d4e2fe314c105f96a9c5c8cc0243cb27c85eb17  tests/test_store.py
785ea50238e406c011545704fc147a25f78c51af8dbcbd41fdc1b194fe87011e  tests/tests_output.txt
b63049e20e0f196ff36f4118f7136d1963cfa8350a1df381c2a4728112bdecd8  fixtures/run_fixtures.py
43fb2f39a6cd258edf861ea7d7cea79898e2efa6fd638fe93ec10431eccae290  fixtures/fixtures_output.txt
43fb2f39a6cd258edf861ea7d7cea79898e2efa6fd638fe93ec10431eccae290  fixtures/fixtures_rerun_output.txt
fb4d031ec70411d49e8a742befcccd98216e4a7e56a240ad6f8fd51a94952df4  migration/migration_events.py
961eccafff3aa257a8a94c6762e9357ebc85127b3937404caf4f9fab00bbd1e3  migration/registry_backfill.json
f77d4d01705f9c283694926d855057c7550dfdb021b7b6e1005d95e4e1a0a138  migration/MIGRATION_PLAN.md
1ce04c5b4182dbd013482c5e11faa4a7d0dd3be54df3839abf27e856f4d1113e  migration/store/queue/queue_log.jsonl
39b5515814dc0b3deff594b5eca1598ff8249f25588fd154b36e0abb163c8d74  migration/store/drafts/intake_draft_20261013.json
b5038ec97ad9c4c7850d384b3ef5d06a380cfd1973dfb0d87f822c1518e75d78  migration/store/ledger/family_ledger.json
1dc90539bb10d0de4ff57259a0cde285eb8c77bc174be65c7ab8c3be863f8ef6  README.md
86600c0775bccb9d… (registry pin, unchanged)                        ../research_loop/registry.json
```

Migration store cards `migration/store/ideas/IDEA-2026-000{1..8}.json` are
pinned in the sha256 listing produced at build time (see MIGRATION_PLAN.md
verification section); the queue log pin above covers their event history.

## Acceptance route

Delivered for independent review before acceptance, per the design §5
pattern (pins + outputs, TD/TimesFM style). Suggested reviewer checks:
rerun `tests/test_store.py` and `fixtures/run_fixtures.py` from the pins;
verify the migration store's chain and materializer determinism;
confirm `registry.json` still hashes to the pin above.
