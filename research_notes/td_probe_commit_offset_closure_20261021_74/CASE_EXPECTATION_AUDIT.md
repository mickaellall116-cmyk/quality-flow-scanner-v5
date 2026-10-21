# CASE EXPECTATION AUDIT — task -74 r1 (pre-formal, source reading only)

Spec: Issue #1 comment 6322868425. This audit was written BEFORE
the precommit and before any execution of the -74 harness. No
dress-rehearsal run of any case was performed; every expectation
below is derived from the pinned source text and explicit byte
arithmetic (the -73 lesson: its audit verified the marker's
existence/uniqueness but did not recompute the offset — the gap
the -73 formal run caught at Q06).

## 1. The offset, recomputed byte by byte

`_COMMIT_PREFIX = b'"commit_state": "'`:

| rel. byte | char | hex |
|---|---|---|
| +0 | `"` | 0x22 |
| +1..+12 | `commit_state` (12 chars) | — |
| +13 | `"` | 0x22 |
| +14 | `:` | 0x3A |
| +15 | ` ` | 0x20 |
| +16 | `"` (value opening quote) | 0x22 |

`len(_COMMIT_PREFIX) = 1 + 12 + 1 + 1 + 1 + 1 = 17`.

`_COMMIT_MARKER = _COMMIT_PREFIX + b'0"'`, length 19:
byte +17 = `0` (0x30, the commit value), byte +18 = `"` (0x22,
the closing quote).

- -73 formula: `index(marker) + len(marker) − 1 = index + 18`
  → lands on the CLOSING QUOTE (0x22). WRONG — this is the Q06
  defect, confirmed arithmetically.
- -74 formula: `index(_COMMIT_PREFIX) + len(_COMMIT_PREFIX)
  = index + 17` → lands on `0` (0x30). CORRECT.

`index(_COMMIT_PREFIX) == index(_COMMIT_MARKER)` at the point
of use: the marker begins with the prefix, the explicit count
check (`count(_COMMIT_MARKER) != 1` → OSError) runs FIRST, and
the raw prefix bytes cannot occur anywhere else in
`json.dumps` output — a `"` inside a serialized string value
is escaped (`\"`), so the unescaped prefix can only be the
field itself. L01 additionally asserts `count(prefix) == 1`
on real persisted bytes for both verdicts.

## 2. The invariant path (source: account_preflight.py)

`DailyUsageSession.__call__` wraps `_persist_outcome` in
`except OSError` and returns
`USAGE_RECEIPT_PERSIST_FAILED: {e}` (the ONLY exception type it
converts). -74 raises
`OSError("USAGE_COMMIT_LAYOUT_INVALID: ...")` from both layout
checks, BEFORE `store_dir.mkdir`, staging, or any publish —
so a layout failure produces: structured refusal reasons,
zero finals, zero temps, zero data transport, and no reusable
receipt. No `assert` remains anywhere in
account_preflight.py (grep-verified at audit time: the two
-73 asserts at the layout site are the only ones replaced;
no other assert exists in the file), so behavior is identical
under `python -O`.

## 3. New-case expectations, reconciled against source

- **L01_commit_layout_exact** — drives `_direct_session`
  (GOOD_USAGE → PASS; `{current_usage: 1, plan_limit: 8}` →
  REFUSE per U08's established shape) with a scoped spy on
  `DailyUsageSession._activate_commit` capturing the published
  receipt bytes and the offset argument BEFORE the real
  activation runs. Expected: `count(marker) == 1`,
  `count(prefix) == 1`, captured offset ==
  `pre.index(prefix) + 17`, `pre[off] == b'0'`, post-activation
  bytes differ from pre at EXACTLY `[off]`, `post[off] == b'1'`,
  equal lengths, `json.loads(post)["commit_state"] == "1"`,
  verdict matches. (Activation is the only post-publish write
  in the persist path — `_activate_commit` writes exactly one
  byte via `_write_all` — so a single-byte diff is the exact
  expectation, not an approximation.)
- **L02_commit_layout_invalid** — a scoped `ap.json.dumps`
  wrapper duplicates the commit field ONLY in the receipt
  serialization (guard: dict with `commit_state == "0"` and a
  `sha256` key — the shape unique to `_persist_outcome`'s
  receipt dict; usage-response and marker dumps in the path do
  not match). Expected: the count check fires (2 != 1) →
  OSError → session returns reasons containing BOTH
  `USAGE_RECEIPT_PERSIST_FAILED` and
  `USAGE_COMMIT_LAYOUT_INVALID`; no finals; store dir never
  created (layout check precedes mkdir). An AssertionError
  anywhere would escape `__call__` and fail the case as an
  unexpected exception — its absence is thus proven by the
  structured result itself.
- **O01_python_O_layout_invariant** (harness-generated final
  entry, not a CASES member) — main() re-invokes this file as
  `python -O <file> --focused-o`, which runs ONLY L01/L02 via
  the same `_run_cases` path. Expected: exit 0,
  `all_pass == true`, case names exactly
  `[L01_commit_layout_exact, L02_commit_layout_invalid]`.
  Case detail strings are static (no paths, no wall clock),
  so the byte-identity repeat covers this entry too.

## 4. Preserved expectations

The 67 -73 cases (Q01–Q20, A01–A10, B01–B08, U01–U13,
P01–P12, M01–M04) run in the original order with unchanged
expectations; `main()`'s per-case loop is refactored into
`_run_cases` with identical semantics (warnings-as-errors,
first-failure stop, same result dicts). The harness label
becomes `td74_qualification_r1`. Only two files change vs
-73: `account_preflight.py` (docstring -74 note, the
`_COMMIT_PREFIX` constant, the layout-check block) and
`tests_qualification.py` (docstring, L01/L02/O01 machinery,
label). All other package files are byte-identical copies of
the -73 package (sha256-verified against the -73 manifest at
build time; see BUILD_RESULT.md).
