# Slice 6 — Part-B Reconciliation (paper-only)

**Status:** PASS — 16/16 tests green, full suite run 2026-09-18
(6m05s). Two failures on the first full run were root-caused and fixed
(see Result); the re-run is fully green.
**Scope:** `pine_live/` only. Read-only and causally inert. No real alerts, no orders, no trading integration, no real money.

## Contract

Independently replay every live entry and exit packet against the canonical
reference. **PASS requires exactly zero category 2–7 mismatches.**

Seven buckets (docs/PARITY_SPEC.md):

| # | Bucket | Meaning |
|---|--------|---------|
| 1 | Data/vendor only | Same code, different input bars (vendor revision). Counted, digested; never fails the run. |
| 2 | Bar construction | 4H session/timezone/premarket handling differs. LOGIC BUG. |
| 3 | Indicator values | Same bars, different indicators or signal decision. LOGIC BUG. |
| 4 | Ranking | rs_score, contested flag, or take/skip differs. LOGIC BUG. |
| 5 | Sector cap | Sector label, count, or skip differs. LOGIC BUG. |
| 6 | State/slot | Position-slot accounting, exit-walk logic, strategy contamination. LOGIC BUG. |
| 7 | Alert delivery | Right decision, wrong/late/duplicated/missing alert. DELIVERY BUG. |

V3.6 has **no time-based exit** (that is V5.4 Mode B). Any time-keyed exit is
category-6 strategy contamination.

## What the job does

`pine_live/reconcile.py::run_reconciliation` (paper-only, read-only):

1. **Signal packets** — replays each signal packet through the canonical
   signal replayer on its pinned bars (categories 2/3), then compares the
   pinned bars against the reference bars. A genuine vendor revision lands
   in category 1 only; the signal-level replay on the packet's own bars
   still applies.
2. **Signal set** — the live signal-id set must equal the reference set
   (category 2).
3. **Portfolio + exit chain** — re-derives the full portfolio state over
   the live run's settlement timeline (from the reconciliation manifest),
   replaying every exit through the canonical exit walk on its pinned
   snapshot (category 6), checking trigger reasons against the V3.6
   allowlist, and comparing every economic state field against the
   packets' pinned pre/post states exactly.
4. **Delivery audit** — reads packet, dedup, and paper-outbox records;
   never invokes delivery (category 7).

## Settlement timeline (the manifest)

The live engine visits timestamps that produce no packets: reference exit
times for trades the stack never took still run `advance_clock` +
`settle`, marking equity and moving `peak`/`max_drawdown`. Replaying only
packet timestamps therefore under-reconstructs drawdown.

`_run_window_live_exits` writes a causally-inert
`reconciliation_manifest.json` (the exact ordered timeline it visited).
The job walks that timeline, cross-checks every packet timestamp against
it, and requires the reference entry/exit times to be covered. Gaps are
integrity errors, never silently papered over.

Live ordering mirrored by the chain, per timestamp:

1. Pre-state check (pre-advance, as pinned).
2. `advance_clock(t)` — before exits, so `open_time` accrues on the
   positions carried into `t`.
3. Exits (sequential pre/post checks; packets pin the pre-advance clock).
4. Portfolio decision replay.
5. `settle(t)` — marks equity at every timestamp, packeted or not.

## Custody

Every reconciled packet pins in the report (`result["custody"]`):

- packet SHA-256,
- bar-snapshot SHA-256 (signal + exit packets),
- pre-state SHA-256 and post-state SHA-256 (exit packets).

A snapshot whose hash does not verify, or a missing snapshot, is an
integrity error and always fails the run.

## Determinism

Every collection is sorted; the report body is canonical JSON. With
identical inputs (and a fixed `now`), the written report file is
byte-identical across runs. `result["report_sha256"]` self-verifies the
result section.

## Test gates (pine_live/tests/test_slice6.py)

1. Full-window historical replay → PASS, zero category 2–7.
2. Delivery-disabled replay → PASS.
3. Vendor-revision drill → category 1 only, still PASS.
4. First divergence reproducible from stored artifacts (no download path).
5. Read-only (input hashes unchanged) + import-graph isolation.
6. Deterministic: repeated runs byte-identical.
7. Corruption drills: tampered snapshot and mutated packet field detected
   and localized; plus ranking (cat 4), sector-label (cat 5), and
   portfolio-state (cat 6) mutation drills.
8. Time-exit contamination → category 6.
9. Static + behavioral proof that frozen V3.6 has no time exit.

## Result

**Verdict: PASS.** Full-window historical replay: zero category 2–7
mismatches. Paper/live packet replay: zero category 2–7. Data/vendor
differences isolated as category 1 only. First divergence reproducible
from stored artifacts alone (no download path). Repeated runs produce
byte-identical reports. Deliberately corrupted packets detected and
localized to the exact packet, timestamp, and bucket. V3.6/V5.4
distinction pinned: frozen V3.6 has no time-based exit (the 30-bar max
hold is V5.4 Mode B); a time-keyed exit is reported as category-6
strategy contamination.

Two failures on the first full run, both fixed before sign-off:

1. `test_mutated_ranking_score_detected_as_category_4` — real job bug.
   The settlement chain replayed entries with the packet's *claimed*
   `rs_score`; a tampered claim leaked into the open-event log and
   poisoned every downstream state comparison (category-6 cascade on
   top of the correct category-4). Fix (`reconcile.py::_chain_contender`):
   the chain now replays ranking features from the reference (ground
   truth) — the packet's claims are audited separately in 3b. Exception:
   category-1 symbols keep the packet's claimed score, because their
   bars genuinely differ and the reference cannot reproduce what the
   engine computed. No-op in the unmutated case (packet scores already
   equal reference scores exactly).
2. `test_vendor_revision_isolated_as_category_1` — test-setup bug. The
   drill pointed `exit_packet_log` at a path the engine never created
   (`live_exits=False`); the job correctly raises on a missing file
   (a missing log must stay a configuration error, never a silent
   zero-exit PASS). Fix: the test plants the empty exit log.
