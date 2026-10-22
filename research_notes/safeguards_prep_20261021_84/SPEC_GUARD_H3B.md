# SPEC — H3b: CONSTRUCTOR DUPLICATE-INDEX FAIL-CLOSED GUARD (scoped spec + fixture-proven candidate)

**Task:** QF-TD-SAFEGUARDS-PREP-20261021-84, Part A.
**Authority:** ChatGPT QF NEXT ACTION (Slack TS 1792627306.219339) +
Mike's direction (chat 2026-10-21 20:02 ET): "Prepare the constructor
guard and split-event producer, using isolated tests without changing
production."
**Status: CANDIDATE — spec + isolated module + synthetic fixtures.
NOT integrated, NOT adopted, no pinned file modified.**

## 1. The defect this guards against

The -82 item-5 fixtures (package `claude_cp1_repair_20261021_82`,
commits d2cca9c/43bb235) proved the pinned constructor
(`construct_4h.py`, sha256 d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd):

- passes an exact index-equality assertion on valid input (T1);
- runs clean under warnings-as-errors (T2);
- does **NOT** reject duplicate 1H timestamps (T3): it sorts and
  aggregates, so a duplicated bar is silently merged — fixture 09:30
  bin Volume **507 vs the single-copy expectation 406** — and its
  OHLC enters the bin's first/max/min/last. Deterministic, but a
  duplicated vendor bar would silently corrupt volume and range in
  every constructed frame downstream.

Duplicate safety today lives only in the validator layer
(`validate_input_v3_dstfix.py`, pin ca3bafd8…), which the cleared
entrypoint runs before construction. The constructor's own docstring
warns that calling it directly bypasses validation. Any future
assembly point that reaches the constructor without the validator
re-opens the hole. H3b is defense-in-depth AT the constructor
boundary.

## 2. Where the guard sits

```
vendor bars ──► validator (ca3bafd8…) ──► [ H3b GUARD ] ──► constructor (d47e8df1…)
                        ▲                        │                     │
                        └─ existing layer        └─ candidate          └─ output index
                           (unchanged)              pre-check             re-checked
                                                    on INPUT 1H           (post-check)
```

- **Pre-check (the H3b substance):** before `construct_4h` is
  invoked, the input frame's index is scanned for duplicated
  timestamps. Any duplicate → refusal (see §3). The constructor is
  never invoked on refused input (fixture G6 proves this with a spy).
- **Post-check (defense in depth):** the constructed frame's index
  is scanned the same way, so a future constructor regression that
  emitted duplicates would also fail closed instead of propagating.
- The guard is a **wrapper**, not a patch: it calls the constructor
  module's `construct_4h` unchanged and returns its output unmodified
  on valid input (fixture G3: byte-identical output vs the unguarded
  path).

## 3. Failure semantics

- Named error: `DuplicateTimestampError`, stable machine-readable
  code **`CONSTRUCTOR_GUARD_DUPLICATE_TIMESTAMP`**, carrying the
  stage (`input_1h` / `output_4h`), the count of duplicated rows,
  and the duplicated timestamps in first-appearance order.
- **Never merge, never drop, never deduplicate silently.** The
  guard's only behaviors are: pass the frame through untouched, or
  refuse the whole construction. There is no partial output.
- **Deterministic:** two runs over the same input bytes produce
  byte-identical refusal messages (fixture G1, repeat-run).
- Identical-copy duplicates and conflicting duplicates (same
  timestamp, different OHLCV) refuse identically (fixtures G1, G2) —
  the guard does not adjudicate which copy is "right"; that is a
  data-provenance question and guessing is exactly the failure mode
  being closed.

## 4. Why the pinned constructor must NOT be edited in place

The constructor's sha256 is not an implementation detail — it is a
load-bearing pin in an evidence chain:

- The route manifest candidate (`ROUTE_MANIFEST_CANDIDATE_V2`,
  sha 9573118c…) binds the constructor pin d47e8df1… together with
  the entrypoint (84ccd2c6…), CLI-guard constructor (3f432e7e…),
  validator (ca3bafd8…), adapter/driver/gate/executor r5 set and
  supplement v2.
- The -49…-58 route proof (gate 46/46, clock 20/20, NLQUAL 28/28)
  was executed against THOSE bytes; the -82 hardening fixtures cite
  the same pin; the -78 CP1 bundle carries the constructor at this
  pin for Claude's review.

Editing the file in place — even to add a two-line guard — changes
the hash and silently invalidates every one of those references:
each downstream claim ("the route that passed is the route that
runs") would become false without anything visibly changing. The
lane's standing rule is that pinned bytes are immutable evidence.
H3b therefore ships as a **candidate wrapper module** here; adoption
means minting a **new constructor version** (guard folded in or
bound as a named chain element) with **new pins** and a **full route
re-proof** — the sequence is specified in `REPROOF_PLAN.md` and is
NOT executed by this task.

## 5. Candidate module + fixture evidence

- Module: `guard/constructor_guard.py` (`GUARD_VERSION =
  "h3b-candidate-1"`): `assert_no_duplicate_timestamps`,
  `assert_index_equality` (the -82 H1 assertion as a callable),
  `guarded_construct_4h` wrapper, the two named errors.
- Suite: `guard/test_constructor_guard.py`, run against the
  pin-verified byte-copy of the pinned constructor (the suite
  refuses to run if the copy's hash ≠ d47e8df1…). The G1 input is
  the exact -82 T3 construction; the unguarded reference in the same
  run reproduces the -82 merge value (bin Volume 507) before the
  guarded path refuses it.
- **Result: 12/12 checks PASS, repeat-identical**, under the pinned
  env (CPython 3.12.3 / pandas 2.2.3, `unshare -n`). Full output:
  `TEST_EVIDENCE.md`, Part A.

Checks: G1 T3 input refused + named error + deterministic message ·
G2 conflicting duplicate refused · G3 clean output byte-identical
to unguarded (csv sha 077e0c6b…) + frame-equal · G4 index-equality
holds through the guard + negative control (wrong expected index
raises) · G5 warnings-as-errors clean through the guard + engagement
control · G6 constructor never invoked on refusal (spy, 0 calls);
clean path invokes exactly once.

## 6. Scope limits of this candidate

- The guard checks the frame index as handed to the constructor.
  It does not re-validate OHLCV semantics, session membership, or
  anything the validator owns — it is one check, at one boundary.
- It is proven only on synthetic fixtures against the byte-copy.
  Nothing here runs on real bars, and adoption on real data follows
  the re-proof plan, not this package.
