# BUILD RESULT — QF-TD-PROBE-COMMIT-OFFSET-CLOSURE-20261021-74 r1

**Terminal: `TD_PROBE_COMMIT_OFFSET_CLOSURE_READY__FRESH_USER_GO_REQUIRED`**

Spec/adjudication: Issue #1 comment 6322868425. Offline only:
zero vendor/API/data calls, zero credentials, zero credits;
Day 1 NOT re-run. Elapsed ≈7 min of the ≤20 cap; repair
minutes 0 (the single formal attempt passed; no in-run repair).

## Commits (remote-verified ancestors of origin/main)

- Precommit: `b2235959c2b1f39af75a223b97a0f84a5172af85`
  (pushed + ancestry-verified BEFORE execution; contains
  CASE_EXPECTATION_AUDIT.md).
- Result: this commit (single result commit — memo + results
  JSON + refreshed pyc-free manifest; file list verified
  pre-push against the manifest: 67 package files, 66
  manifest entries).

## The closure (spec §1–§4)

1. **Offset via the value prefix.** `_COMMIT_PREFIX =
   b'"commit_state": "'` (17 bytes);
   `commit_offset = receipt_bytes.index(_COMMIT_PREFIX) +
   len(_COMMIT_PREFIX)` = index + 17 → the value byte `0`
   (0x30). The -73 formula (index + len(marker) − 1 = index +
   18) landed on the closing quote (0x22). Byte map recomputed
   in CASE_EXPECTATION_AUDIT.md §1 and machine-checked at
   build time (len(prefix)=17, len(marker)=19, marker[17]=
   b'0', marker[18]=b'"').
2. **Explicit layout invariants.** Both bare asserts in
   `_persist_outcome` are replaced by runtime checks raising
   `OSError("USAGE_COMMIT_LAYOUT_INVALID: ...")` (marker count
   != 1; byte at the computed offset != pending value).
   `__call__` converts them to `USAGE_RECEIPT_PERSIST_FAILED`.
   No `assert` remains in account_preflight.py; behavior is
   identical under normal Python and `python -O` (proven by
   case O01 below).
3. **L01 exact-layout case** — on real persisted PASS and
   REFUSE receipts (pre-activation bytes captured by a scoped
   spy on `_activate_commit`): marker and prefix each occur
   exactly once; the offset equals prefix-index + 17 and names
   the `0` byte; activation changes EXACTLY that one byte
   (diff == [offset]); the activated receipt parses with
   `commit_state == "1"` and the expected verdict.
4. **L02 invariant-failure case** — a scoped `json.dumps`
   seam duplicates the commit marker in the staged receipt:
   structured `USAGE_RECEIPT_PERSIST_FAILED` /
   `USAGE_COMMIT_LAYOUT_INVALID`, zero finals published,
   store dir never created, no reusable receipt, and no
   AssertionError (one would escape `__call__` and fail the
   case as an unexpected exception type).

## Formal attempt — ONE invocation, full pass + repeat

Command: `python3 -W error::Warning tests_qualification.py`
(warnings-as-errors also enforced per case inside the
harness). Exit 0; stderr empty (sha256 of empty =
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855).
Stdout SHA-256:
`c030a4c200248189b6e6cc319866418d271824f410fd21c037124e739831a5fc`
(== committed QUALIFICATION_RESULTS.json).

**70/70 entries PASS**, in order: the 67 preserved -73 cases
(Q01–Q20, A01–A10, B01–B08, U01–U13, P01–P12, M01–M04 —
M01–M04 EXECUTED and passed, including the double-failure
proof), then L01_commit_layout_exact,
L02_commit_layout_invalid, and the harness-generated
O01_python_O_layout_invariant (L01/L02 re-run under
`python -O --focused-o` inside the same single invocation:
exit 0, exact case names, all pass).

Byte-identity repeat (permitted only after the full pass):
exit 0, stdout byte-identical (cmp clean, same SHA-256),
stderr empty.

## Diff vs -73

Changed: `account_preflight.py` (module docstring -74 note;
`_COMMIT_PREFIX` constant + comment; the layout-check block —
nothing else), `tests_qualification.py` (docstring -74 note;
L01/L02 + FOCUSED_O + `_run_cases`/`_main_focused_o`/
`_focused_o_entry` machinery; CASES appends L01/L02; harness
label `td74_qualification_r1`), `CASE_EXPECTATION_AUDIT.md`
(new -74 audit). Byte-identical to -73 (cmp/diff-verified):
`probe_runner.py`, `probe_analyzer.py`, `temporal_gate.py`,
`make_fixtures.py`, `probe_manifest.json`, and all 56 fixture
files. The -73 monotonic design and all quota/limiter/
ceiling/retry/no-pagination semantics are preserved.

## Disclosures

1. The spec fetch via the public GitHub API hit the shared
   egress rate limit on the first two attempts (HTTP 403
   payload, no body); the spec text relied on is the complete
   comment 6322868425 body already read and verified by the
   parent agent and reproduced in the tasking — every closure
   item §1–§6 was executed as written there. Nothing was
   guessed: where the relayed spec and the -73 source could
   be cross-checked (marker bytes, assert sites, `__call__`
   conversion), they agreed exactly.
2. `python3 -m py_compile` (static syntax check only — not a
   test execution) was run on the two edited files before the
   precommit; the `__pycache__` it created was removed before
   the manifest was generated. Run-created `__pycache__` was
   likewise removed before the result manifest was finalized.
3. The -74 pre-formal desk audit (CASE_EXPECTATION_AUDIT.md)
   recomputed the offset arithmetic byte-by-byte and
   reconciled L01/L02/O01 expectations against the source;
   it found no further demonstrably wrong expectation, and
   the formal run agreed with the audit at all 70 entries.
4. Main working tree never touched (its pre-existing
   `UU forward_test/kama_shadow.json` state is intact); all
   work happened in the detached temp worktree
   /tmp/qf_td74_wt, removed after the result push. No stashes
   created, popped, or dropped.
