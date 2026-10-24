# QF-EQUITY43-S1-STAGING-ISOLATION-PREFLIGHT-20261024-19 r1 — RESULT

**Verdict: PREP_READY / LAUNCH_HOLD**

PREP_READY is a staging verdict only — not a launch, not edge evidence,
not S1/S2 activation, not a T0. The staged observer has never touched a
market feed and cannot: the bundle contains no network/vendor adapter
and its only processing path is reachable solely in synthetic-test
namespaces.

Governing text: GitHub Issue #1 comment 6382675021 (ChatGPT's
independent -18 adjudication, BOUNDED PASS, + this task). ACK: Slack TS
1792835888.133469; bridge ACK commit 22a79cb6f74dbfbbb2f8421b4a63e6155a48a6c1.
Single-dispatch CLEAR before any file operation: no `qf_td19_stage`,
no -19 package path, no pre-execution commits for this ID on
origin/main (head 454cf34 at check time).

## What was built

An immutable staging bundle (`bundle/`, 23 files, byte-identity
inventory in `INVENTORY19.json`) assembled from the passed -17 r2
observer/strategy contract (package 5ed79cd) and the passed -18
calendar candidate (package 19cd5ae):

- `observer/fwd_observer17.py` — the -18 fork copy, byte-identical to
  the -17 package file (SHA `929c1bc4…`);
- `engine/` — the 6 pinned successor-engine sources the observer's
  contract consumes + `asof_benchmark.py`;
- `lineage/` — the 6 fork09/orig pinned sources, carried for inventory
  completeness; NOT imported by any bundle entry point;
- `calendar/` — the adopted 751-session table (byte copy, SHA
  `00c5555c…`), the -18 extended candidate (SHA `86a1d4ea…`, 1,054
  sessions, 751-row prefix row-identical to the qualified table), the
  repin record, and the -18 generator (provenance; not executed);
- `config/` — experiment config (canonical hash recomputes to the
  -17 r2 pin `87b8285a…`) and the exact 43-symbol universe;
- `pins/PINS19.json` — the full pin inventory: all 20 -17 r2
  structured-inventory fields (observer, 14 source pins, config,
  sector, 3 manifest roots, chain/receipt/archive evidence values,
  PAUSED pins) + the -18 calendar binding (exact commit/manifest/table
  SHA adoption rule). Chain-evidence values are carried verbatim from
  the committed -17 r2 artifact and bound by this bundle's manifest;
- `staging_gate19.py` — stdlib-only gate, the bundle's only entry
  point; `DEPENDENCY_LOCK.json` — environment of record (Python
  3.12.3, pandas 2.1.4, numpy 1.26.4; nothing installed).

One defect was found and fixed during assembly, disclosed: the sector
pin's hash construction is `json.dumps(..., sort_keys=True)` with
default separators (the -17 r2 emitter's exact form), not the compact
canonical form used for the config pin. The gate now mirrors the
emitter byte-for-byte; both constructions are documented in PINS19.

## Proofs (battery `tests/test_staging19.py`: 38/38 PASS)

- **Namespace isolation.** Designated staging namespace
  `~/workspace/qf_td19_stage/runtime/staging` is disjoint by canonical
  realpath from the production tree and every protected production
  namespace. Traversal into production → STOP_NAMESPACE_OVERLAP; a
  namespace inside production → STOP_NAMESPACE_OVERLAP; a symlink
  inside the namespace escaping it → STOP_NAMESPACE_ESCAPE; symlinked
  namespace path components refused.
- **No production writes.** The gate opens production files read-only
  for identity checks only. Shadow-root tests prove the check itself:
  a one-line harness mutation → STOP_PAUSED_PIN_DRIFT; a removed
  PAUSE sentinel → STOP_PAUSED_PIN_DRIFT. Live production re-proved
  identical before and after this task (below).
- **Signal-only.** Static audit of all 16 bundle modules
  (`STATIC_AUDIT19.json`): zero network imports, zero vendor imports,
  zero order-surface tokens; the gate imports stdlib only; the observer
  imports hashlib/json/os/pandas. Simulator functions exist inside the
  pinned engine sources (byte-identical, uneditable under the pins) —
  the execution trace of a full synthetic replay proves none of them
  runs, while the signal primitives (`add_pine_indicators`,
  `pine_buy_signal`) do. The observer class exposes no order/broker/
  submit/fill surface. Emitted S1 records carry exactly
  {symbol, signal_time, entry_time, entry, stop, tp1, kind} — no exit,
  R, equity, sizing or performance field exists in the output path.
  A planted fake vendor adapter (`import requests`) in a bundle copy
  is flagged by the audit and STOPs preflight (STOP_AUDIT_SURFACE).
- **No network.** A counting socket replacement during a full
  synthetic replay recorded 0 connection attempts.
- **Exact pins, fail-closed.** Preflight recomputes: observer SHA,
  14/14 source pins, experiment-config canonical hash, sector map
  (recomputed from the bundled engine over the pinned universe),
  both calendar file SHAs, the generator SHA, 751-row prefix identity,
  and the repin cross-check. A one-byte drift in the extended table
  copy → STOP_PIN_DRIFT; a 44-symbol universe (SMCI added) →
  STOP_UNIVERSE.
- **Crash / restart / tamper / lock.** A synthetic replay (140
  appended-range sessions, 2 symbols) journals 2,790 records /
  1,065,893 bytes, head `f344d122…`, and yields 2 signal records.
  Replaying the same stream in a second namespace is byte-identical.
  A snapshot + verified journal resume mid-stream continues to a
  final journal byte-identical to the uninterrupted run. A truncated
  (mid-write crash) journal tail fails verification and resume is
  refused; a single flipped payload character is detected at its
  exact sequence (chain break, seq 10). A held namespace lock makes a
  second preflight STOP_LOCK_HELD; after release, boot is clean.
- **Fail-closed launch posture.** Staging-namespace processing is
  unreachable (STOP_LAUNCH_HOLD). A pre-populated journal →
  STOP_JOURNAL_PREPOPULATED. A KILL file STOPs boot, and a mid-run
  KILL halts processing with the journal-so-far still verifying
  against its anchor. Bars stamped on unknown calendar dates
  (2026-10-18, a Sunday; 2028-06-01, beyond the table) are rejected
  UNKNOWN_SESSION. Launch-authority handling: absent →
  T0_AUTHORITY_ABSENT; malformed JSON → T0_AUTHORITY_MALFORMED; a
  well-formed but forged authority still leaves LAUNCH_HOLD in force
  (G4_VBASIS_UNADOPTED + FEED_RIGHTS_UNQUALIFIED stand).

## Launch hold (unchanged, structural)

Hold reasons at preflight: `G4_VBASIS_UNADOPTED`,
`FEED_RIGHTS_UNQUALIFIED` (live latency UNMEASURED), `T0_AUTHORITY_ABSENT`.
`RUNBOOK_SUPERVISED_FIRST_CYCLE.md` lists the five still-human gates
in order — G4 adoption; qualified prospective feed rights/latency;
calendar adoption binding the exact -18 commit/manifest/table SHA;
a declared future T0; explicit Mike GO + observer supervision — plus
the supervised-first-cycle checklist. It is documentation only.

## Bounds held

Offline only; 0 vendor calls/credits; no performance figures; no
holdout or SMCI reads; no G4 adoption/waiver; no production change;
no S1/S2 activation; no T0; no trades; no scheduler/cron armed for
the bundle. The -15/-16/-17/-18 packages are untouched; strategy
sources byte-identical (that is the pin result above).

PAUSED production, before and after (identical): harness
`ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d`,
PAUSE_NEW_ENTRIES present, RESUME_NEW_ENTRIES absent.

Elapsed: ACK 06:18 ET → RESULT 10:05 ET, Oct 24 2026 (~3.8 h wall,
including inter-step latency; battery itself ~11 s).

— Muse
