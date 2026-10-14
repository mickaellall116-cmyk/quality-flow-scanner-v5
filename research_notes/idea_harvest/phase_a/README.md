# Phase A — idea-intake pipeline (schema/store only)

QF-IDEA-PIPELINE-PHASE-A-20261013-01 r1. Implements
`../PHASE1_DESIGN_PACKAGE_20261013.md` Phase A as amended by the review fixes
in Issue #1 comment `6155160682`. **Schema/store only**: no network fetcher,
no scheduler changes, no live queue, no experiments, no registry writes.

## Layout

| Path | What |
|---|---|
| `store.py` | The store: card validators, immutable cards, append-only hash-chained JSONL event log, atomic lease, state machine, deterministic draft + family-ledger materializers. Zero network code. |
| `killed_ideas_seed.json` | Versioned killed/held-idea seed (data, not code). |
| `sources.json` | Source registry: `access_basis` defaults; #2 SSRN, #4 OA repositories, #5 Papers With Backtest are `PARKED-SOURCE`; `SOURCE_CHAT` is an intake channel that enters only through the single writer. |
| `state_mapping.json` | Queue ↔ registry state mapping. Vocabularies are separate; joined only by `idea_id` in materialized drafts. |
| `tests/test_store.py` | 20 unit tests (validators, transitions, lease, chain, materializer determinism). Output: `tests/tests_output.txt`. |
| `fixtures/run_fixtures.py` | Fixtures F1–F5 (design §6) + F6 chain tamper, F7 adjacency flag, F8 SOURCE_CHAT channel. Outputs: `fixtures/fixtures_output.txt`, `fixtures/fixtures_rerun_output.txt` (independent rerun, byte-identical). |
| `migration/migration_events.py` | Builds the registry backfill + migrates Harvest #1 into a store via MIGRATED events. |
| `migration/registry_backfill.json` | Family index over the pinned registry blob, with explicit coverage limits. |
| `migration/store/` | The migrated store instance (8 cards, hash-chained log, materialized drafts + ledger). |
| `migration/MIGRATION_PLAN.md` | Migration approach, per-candidate mapping, parked-source consequences, findings. |

## Store layout (any store instance)

```
ideas/IDEA-YYYY-NNNN.json     immutable cards — write-once, never edited
queue/queue_log.jsonl         append-only, hash-chained events (system of record)
drafts/intake_draft_*.json    materialized per run — regenerable, byte-stable
ledger/family_ledger.json     materialized family ledger — regenerable
pipeline.lock                 single-writer lease (present only during a run)
```

## Key semantics

- **Cards** require `source.access_basis` (an inferred `license` key is a
  validation error), a canonical-text `content_hash` (extractor
  `canon-extract/1.0.0`, version recorded on the card), non-empty
  `limitations`, a named timeframe, and a non-parked primary source class.
- **Idempotency**: `dedup_key = sha256(claim_normalized | primary source
  key)`. Re-ingesting an existing key appends `DUPLICATE_SEEN` citing the
  existing idea and its state — no new card, no new ID.
- **Dedupe is mechanical, never semantic**: killed-seed / closed-family
  matches reject with the matched record cited; with a recorded
  materially-different-mechanism justification, or for known open families,
  the match becomes an `ADJACENCY_FLAG` for human confirmation. No automated
  same/different verdict exists anywhere in the code.
- **State machine**: DISCOVERED → INGESTED → RANKED → SHORTLISTED /
  PARKED / BLOCKED-DATA; REJECTED and SHORTLISTED are terminal.
  PREREGISTERED / ELIGIBLE transitions are refused and logged as ERROR
  events (fixture F5). Queue and registry state vocabularies stay separate
  (`state_mapping.json`); only SHORTLISTED materializes a registry-shaped
  draft marked `DRAFT-INTAKE-NOT-MERGED`.
- **Lease**: `pipeline.lock` via `O_CREAT|O_EXCL` with pid + run_id +
  timestamp. A live lease refuses a second writer. A stale lease (>2 h or
  dead pid) may be broken; the break is logged as a `LOCK_BROKEN` event.
  Run/event IDs are unique per attempt and sequenced from the log tail.
- **Crash safety**: events are single-line appends with flush + fsync; the
  writer verifies the hash chain before appending and aborts on mismatch —
  it never repairs the log silently (fixture F6).
- **Materializers are pure functions** of (queue log + pinned registry
  read). Delete and regenerate at any time; output is byte-stable.

## Run the checks

```bash
cd research_notes/idea_harvest/phase_a
python3 tests/test_store.py        # 20 tests
python3 fixtures/run_fixtures.py   # 8 fixtures, exit 0 iff all pass
python3 migration/migration_events.py   # rebuild backfill + migration store
                                        # (refuses to overwrite an existing one)
```

## Hard bounds (structural, not by convention)

No network code exists in `store.py`; there is no registry write path
(`Store.guard_registry_write` raises); harvested external code is never
executed; Tiingo is not referenced; the weekly cron `idea-harvest-weekly`
is untouched — cutover is a later, separately approved phase.
