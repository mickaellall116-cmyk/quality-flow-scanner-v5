# TD PROBE MONOTONIC-COMMIT — task -73 r1 RESULT

Task: QF-TD-PROBE-MONOTONIC-COMMIT-20261021-73 r1
Spec: Issue #1 comment 6321936574 (-72 adjudication: PASS
terminal NOT accepted — _tombstone_unproven_commit silently
discards OSError, so the double-failure branch can leave a
reusable PASS; P12 tested only the tombstone-success branch).
Basis: -72 package (precommit fcb5a10, result d4df199),
immutable. -68 through -72 untouched. Scope: ONE bounded
OFFLINE successor, new additive package only. ONE formal
execution attempt after a pushed precommit; first-failure
stop; no repair and no repeat in-run. No vendor/API/data
calls (the only network use was the read-only spec fetch),
no credentials, zero credits, synthetic data only. Day 1
NOT re-run. REQ-S2 HOLD; entries PAUSED.

Precommit: edc225e870368e477ab37904248cfc5a3d64b0da
(pushed and ancestry-verified against origin/main BEFORE
execution; includes CASE_EXPECTATION_AUDIT.md, SHA-256
a9d75a09…). Note: the first push raced a
newer origin/main commit (b9db31d, an unrelated harness
"KAMA shadow log" update); the precommit was rebased onto it
inside the temp worktree only — package bytes unaffected.

## TERMINAL

TD_PROBE_MONOTONIC_COMMIT_HOLD__Q06_PERSIST_COMMIT_OFFSET_ASSERT

The single formal attempt stopped at case 6 of 67
(first-failure stop): Q01–Q05 PASS, Q06 FAIL. Cases Q07–M04
(61 cases) were NOT RUN and carry no outcome.
QUALIFICATION_RESULTS.json is the attempt's exact stdout
(SHA-256 964a4e2c…); exit 1; stderr empty (e3b0c442…).
Elapsed ≈8 min of the ≤30 cap (spec fetch → result
commit); repair minutes 0 — no in-run repair was attempted.

## First failure — diagnosis (source + arithmetic, not rerun-verified)

Q06 (usage 503x2 must abort before data) recorded
`AssertionError: ` with an empty message. The only bare
assert on that path is inside the NEW -73 code,
`DailyUsageSession._persist_outcome`: the commit-byte offset
is computed as

    commit_offset = receipt_bytes.index(_COMMIT_MARKER) \
        + len(_COMMIT_MARKER) - 1

`_COMMIT_MARKER` is the 19-byte sequence `"commit_state":
"0"` — its LAST byte is the closing quote, not the `0`. The
formula lands on the quote; the `0` sits at len − 2.
Verified arithmetically outside the suite: byte at len−1 is
`b'"'`, byte at len−2 is `b'0'`. The very next line's
invariant assert (byte at offset == "0") therefore failed on
the first receipt ever persisted (Q06 is the first
session-persist case in the order), raising AssertionError,
which `__call__` does not catch (it converts only OSError),
so it propagated and aborted the day run at the preflight.

Consequences, stated plainly:
- FAIL-CLOSED IN EFFECT: the failure occurred before
  activation and before any data transport; no receipt was
  committed by this code path, and the assert is precisely
  what prevented the activation from flipping the wrong
  byte (the closing quote) and corrupting the receipt JSON.
- The design (PENDING publication + monotonic activation +
  reader invariant) is neither proven nor refuted by this
  run: cases exercising it (P12 re-expressed, M01–M04, and
  every later cached-receipt case) never executed. The
  defect is a one-constant arithmetic error in MY offset
  formula, in the candidate, found by the candidate's own
  invariant assert on its first execution.
- Successor fix (for adjudication, NOT applied): compute
  the offset to the value byte, e.g.
  `index + len(b'"commit_state": "')` (the prefix through
  the opening quote of the value), or `len(_COMMIT_MARKER)
  - 2`. A successor should also desk-audit the assert's
  failure MODE: an invariant AssertionError propagates as a
  crash rather than converting to a session HOLD — the
  outcome here was still fail-closed (abort before data),
  but whether persist-path invariants should raise OSError
  so `__call__` returns USAGE_RECEIPT_PERSIST_FAILED is a
  design question for the reviewer.

## Design as built (unproven beyond Q01–Q05)

- PENDING representation: the receipt dict is stamped
  `commit_state: "0"` before serialization; both artifacts
  are staged (write-all + fsync, 0600 same-dir temps),
  body published first (hard link + dir fsync), receipt
  published last (hard link + dir fsync) — all still
  PENDING, so fsync-#4 failure needs no cleanup: the
  on-disk receipt is unreusable by construction.
- Activation: only after fsync #4 succeeds,
  `_activate_commit` opens the published receipt
  O_RDWR|O_SYNC, lseeks to the commit offset, and flips
  the byte 0 -> 1 through the write-all loop — the
  synchronous checked write is itself the durability
  barrier (no separate activation fsync, no ambiguous
  landed-but-unfsynced state). No error in this path is
  caught or swallowed. The -72 `_tombstone_unproven_commit`
  is DELETED.
- Reader rule: `__call__` checks `commit_state == "1"`
  FIRST — before the body check, before the REFUSE/PASS
  branches — and returns USAGE_COMMIT_UNCERTAIN for
  missing/malformed/zero/unknown states, before any
  transport. A source-level invariant note is in the
  module docstring and at the constants.
- Double-failure proof (M01, UNRUN — no outcome claimed):
  fsync #4 fails with every post-failure write rigged
  unavailable; the expected state is the untouched PENDING
  receipt and a reopen HOLD. The mechanism needs no
  post-failure write at all, which is the structural
  answer to the -72 finding — but it carries no test
  evidence from this run.

## Desk audit (pre-formal, source-only)

CASE_EXPECTATION_AUDIT.md (committed in the precommit)
reconciled: the _bound_usage_receipt fixture change (gains
commit_state "1" — it models an already-committed receipt;
A05–A09/B07/P10 expectations unchanged), the P12
re-expression (PENDING receipt, reopen USAGE_COMMIT_
UNCERTAIN), and M01–M04 expectations against the source,
including the fsync-numbering analysis (activation is an
O_SYNC write, not an _fsync call, so #1–#4 are unchanged).
DISCLOSED GAP IN THE AUDIT ITSELF: the audit verified the
marker-uniqueness argument and the offset's EXISTENCE but
did not recompute the offset arithmetic byte-by-byte — the
exact one-byte error the formal run then caught. The
audit-first step remains sound; its -73 execution missed
the arithmetic it most needed to check.

## Changed-file diff vs -72

- account_preflight.py — CHANGED: -73 docstring + invariant
  note; COMMIT_STATE_* constants + _COMMIT_MARKER;
  _persist_outcome stamps PENDING, computes the commit
  offset (defective, above), removes the tombstone branch
  (fsync #4 failure now propagates), calls
  _activate_commit on success; _tombstone_unproven_commit
  deleted; _activate_commit added; __call__ commit gate
  added before the body check.
- tests_qualification.py — CHANGED: -73 header section;
  harness label td73_qualification_r1;
  _bound_usage_receipt gains commit_state "1"; P12
  re-expressed (PENDING expectations); M01–M04 appended;
  CASES gains the four M entries (67 total).
- CASE_EXPECTATION_AUDIT.md — new (-73 audit).
- Byte-identical to -72 (sha256-verified, 61 files):
  probe_runner.py, probe_analyzer.py, temporal_gate.py,
  make_fixtures.py, probe_manifest.json, and all 56
  fixture files.

## Disclosures

1. The formal attempt's failure is in the NEW candidate
   code (my offset formula), not in a harness case — the
   mirror image of -67/-70/-71. The candidate's own
   invariant assert caught it on first execution.
2. The precommit push required a rebase onto a concurrent
   origin/main commit (b9db31d) inside the temp worktree;
   the main working tree was never touched (its
   pre-existing UU forward_test/kama_shadow.json state is
   intact), no stashes were popped or dropped, and the
   temp worktree was removed after the result push.
3. Run imports created __pycache__ in the package; removed
   before the result manifest was finalized — the manifest
   is pyc-free and sha256sum -c verified.
4. This result commit is the SINGLE result commit (memo +
   results JSON + manifest), file list verified pre-push.
