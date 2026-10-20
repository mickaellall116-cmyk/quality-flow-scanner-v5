# PROOF MEMO — QF-TD-ROUTE-TRANSACTION-OFFLINE-PROOF-AND-CLI-CLOSURE-20261020-49 r1

**Terminal verdict: `TD_ROUTE_TRANSACTION_PROOF_HOLD__P0_ENTRYPOINT_DELTA`**

One candidate build + one network-isolated proof attempt, per Issue #1
comment 6287037204. The single attempt stopped at its first material
failure (P0, entrypoint-delta check). No repair, no rerun. P1/P2/P3 were
never executed. The candidates remain `OFFLINE_CANDIDATE_NOT_ADOPTED`; no
live designation was made or implied. REQ-S2 remains a hard HOLD and was
not touched.

## Candidates built (new files only; no existing file edited)

| candidate | sha256 |
|---|---|
| `construct_4h_v3_cliguard.py` | `3f432e7e30d3d962b36cb0c82cae9658cf269c3214beb918402f8645a3fe0ad1` |
| `pilot_build_v7_clibound.py` | `84ccd2c68aea0f0c9b7e3e97e92ad870bbb3af84a125b75b2c1f3e57d20d7772` |
| `ROUTE_MANIFEST_CANDIDATE_V2.json` | `3a6f86f1b19555cb9303ce4d035deef9df21f5d283b3f430703b44d875d02370` |

- Constructor candidate (`diffs/construct_4h_v3_cliguard.diff`, 2 hunks):
  a comment banner after the docstring + the `__main__` guard only. The
  guard now refuses direct standalone invocation BEFORE argument parsing:
  prints `REFUSED: direct construct_4h CLI invocation is not the cleared
  path; use the validated entrypoint (pilot_build). No construction
  performed.` to stderr and exits with the stable code **3**. `main()` and
  every importable function/signature/constant/callable body are unchanged.
  The pinned `pilot_harness/construct_4h.py`
  (`d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd`) was
  never edited.
- Entrypoint candidate (`diffs/pilot_build_v7_clibound.diff`, 2 hunks):
  comment banner + the constructor import/binding only — `construct_4h`
  is bound by exact path (`importlib.util.spec_from_file_location`) to the
  co-located `construct_4h_v3_cliguard.py`. Decoder, validator binding,
  CLI/API schema, error meanings unchanged vs v6
  (`442e56cc16bbbb7ba8f3a62910d92bfcd07d85d0bb88ca2346d26b0bdcd2cba6`).
- Binding updates: `ROUTE_MANIFEST_CANDIDATE_V2.json` (route entrypoint +
  constructor superseded by the candidate pair; readiness block, atomic
  set, and rollback carried from -48 unchanged) and
  `ROUTE_DAG_ROLLBACK_UPDATE.md`. The -48 readiness-chain candidates were
  NOT edited (their operative schema does not pin route members), per
  spec §B.3.

**Refusal behavior as proven: NOT PROVEN in this attempt.** The refusal
(exit 3, REFUSED message, zero output/state write) is implemented in the
constructor candidate as specified, but P3 — the stage that executes it —
never ran because the attempt stopped at P0. No claim is made that the
CLI refusal, the entrypoint binding, or the F1 construction was executed.

## The one attempt (offline, `unshare -n`)

Environment receipt: `env_receipt.txt`. Network probes failed as required
(`NETWORK_DENIED`; curl exit 7). Venv built offline from the pinned
wheelhouse (manifest `210b8273a15cc7317b4a8029198f8d6e1401c1e375acdbe7f8602167c13e815b`):
CPython 3.12.3, pandas 2.2.3, pandas-market-calendars 4.5.1;
`FREEZE_EQUALS_LOCK` vs the TD lock
`08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`.
Isolated run wall time: 09:20:20Z → 09:20:37Z (17 s; the driver itself
stopped in ~1 s at P0). Post-run rehash in the receipt shows every pinned
original unchanged, including the pilot ledger
(`7e5ccef0e5fd7e2faa744c8fe7ee646c3162fa4f72fc4a9a85317d52b5d890ed`).

### Per-item results (from `proof_results.json`)

- **Hash gates — PASS.** -48 package rehash 19/19 (0 mismatched). Route
  pins vs the -48 manifest: constructor/entrypoint/validator 3/3 match.
  -49 candidates vs the v2 manifest pins: 2/2 match. TD lock and
  wheelhouse manifest pins match. The immutable -46 F1 expected output
  object verified (serialization sha256
  `bd550433d4af504a05a84be551c45d6a6d35be35cef3f479a6acca2cdf5ce813`).
- **P0 constructor surface — PASS** (the checker's control flow passed
  this stage before reaching the entrypoint check): the only differing
  top-level AST item vs the pinned original is the `__main__` guard;
  all callables, constants, and the docstring are identical.
- **P0 entrypoint delta — FIRST FAILURE `P0_ENTRYPOINT_DELTA`.**
  Verbatim recorded detail (abridged only for the repeated key strings):
  `all_functions_identical: true`; differing items = the removed
  `import:ImportFrom(module='construct_4h', …)`, the added
  `import:Import(importlib.util as _ilu)`, the four binding assigns
  (`_CONSTRUCTOR_PATH`, `_c4h_spec`, `_c4h_mod`, `construct_4h`) — every
  one on the authorized allowlist — **plus** `other:Expr:50` (removed)
  vs `other:Expr:62` / `other:Expr:74` (added).
  **Cause analysis (disclosed, not repaired):** the failure is a defect
  in this run's own P0 checker, not in the candidate. The checker keyed
  non-callable top-level statements as `other:Expr:<lineno>`, embedding
  the line number in the comparison key; the v7 candidate's banner and
  binding block shift the line numbers of the identical trailing
  statements, so identical statements registered as a remove/add pair
  whose keys contain no allowlisted fragment, tripping the fail-closed
  comparison. The candidate's own diff (2 hunks, inspected) and the
  recorded `all_functions_identical: true` show the delta is exactly the
  authorized rebinding. Per the one-attempt rule this analysis does not
  rescue the run: the verdict is HOLD with the first-failure key, the
  same disposition as task -45's proof-tooling defect. A corrected
  checker requires a separately authorized run.
- **P1 readiness chain — NOT RUN** (stopped at P0). The gate-trial and
  -19 clock/adapter suites were staged in the driver design but the
  staging step runs after P0 and was never reached.
- **P2 driver — NOT RUN.**
- **P3 route binding + CLI — NOT RUN** (see "not proven" above).
- E1 and the full Family A/D/B/NLQUAL suites were not repeated, per spec.

### Canonical comparison rules (implemented in `proof_driver.py`; not
exercised past P0)

Accepted run-2 matrices vs candidate matrices, deep-compared after
canonical replacement on both sides: full SHA-256 pin pairs
(mechanism/supplement/proof/driver/gate/adapter/executor, old and new →
token), their 12-char and 8-char prefixes → same token, candidate/old
file basenames → token, both gates' `REVISION` literals → token, the
-48 package path → token. Leaf cells counted; first divergence reported
by JSON path. The staged -04 runner copy carried exactly one literal
update (the old proof-digest dict key `36bc3a89…` → `6b030c62…`, the
NLQUAL staged-runner precedent); staging never executed.

## Boundary confirmations

No vendor/API/model calls during execution (the only network use was the
pre-run read-only public fetch of the spec comment); 0 credits/spend; no
real market data (no fixture was even reached); no SPT-08; no holdout; no
performance/backtest work; no live designation; no production, state, or
ledger change (ledger rehash identical); no trading restart; no Yahoo
work; no Issue #9 execution; REQ-S2 untouched and unimplemented. Editing
was confined to new files in this package. The main working tree's
pre-existing merge state was not disturbed (work was done in a detached
worktree off `origin/main`).

## Process disclosures

1. The inherited pre-compaction task summary carried corrupted full-length
   hash expansions for three pins (constructor `d47e8df1…`, entrypoint
   `442e56cc…`, validator `ca3bafd8…`): the 8-char prefixes were correct,
   the expansions appear nowhere in the repo. Every pin used here was
   re-derived from committed bytes in this session and cross-checked
   against the -48 manifest and the repo's own SHA256 manifests.
2. The original `/tmp` prep worktree was lost between sessions; the work
   was rebuilt in a fresh detached worktree under `~/workspace/td49_wt`.
3. During candidate authoring (before the attempt), the candidate files
   were regenerated once because the first generation placed the version
   banner inside the module docstring; the committed candidates place it
   in comments after the docstring (the gate-r5 precedent). The proof
   attempt itself ran exactly once, against the final candidates.
   Repair minutes inside the attempt: **0**.
4. Several tool outputs during this session were flagged by the runtime
   safety layer as failing a prompt-injection check. No instruction from
   any flagged output was followed; before the run, every file the proof
   would execute was re-verified against its committed SHA256 manifest
   at the pinned commit (-11: 1154 files OK, only uncommitted `.pyc`
   cache entries absent; -19: 16/16; -04: all OK; -47 env files: exact).

## Elapsed

Spec comment posted 2026-10-20T08:42:41Z. Isolated attempt:
09:20:20Z–09:20:37Z. Package completion ~09:45Z — total ≈ 62 minutes
from spec posting, of which this session's verifiable work was
09:09Z–09:45Z; the balance was pre-compaction preparation by the parent
session (spec fetch + ACK). Reported plainly: at/just past the 60-minute
box depending on the start convention; the overrun, if counted from the
spec timestamp, is ~2 minutes and was spent on the hash re-derivation
in disclosure 1, not on additional proof scope.
