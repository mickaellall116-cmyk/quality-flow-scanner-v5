# V5.4 forward-test ledger — evidence package (2026-10-12)

Packaged 2026-10-13 per ChatGPT evidence intake, Issue #1 comment `6136948813`.
Byte-identical **copies** of the working-tree artifacts pinned in
`research_notes/V54_LEDGER_PINS_RECONCILIATION_20261012.md`
(blob `4d28f5cb2977f0a54faff9af45ba3819887ba8f0`). No original file was
modified; no harness or backtest was rerun.

## (a) SHA-256 of every copied file — verified against the reconciliation pins

| File (copy) | SHA-256 of copy | Pin in reconciliation report | Status |
|---|---|---|---|
| `forward_test.jsonl` (from `v54_forward/forward_test.jsonl`) | `7af698450bbd3f319d7a4320abf7b5a2d4c4bdd368a28ae5f57b627839728624` | `7af698450bbd…728624` | **MATCH** |
| `state.json` (from `v54_forward/state.json`) | `66d03947b9ef967c57c2fff2e55585a5d7fa4010eab6cc7fa4b00494f81d34d8` | `8bd5711cd7bb…971d0281` | **DRIFT — see below** |
| `v54_rules.py` | `1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a` | `1b55dedce3b1…ebb817a` | **MATCH** |
| `v54_engine.py` | `bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb` | `bde3288307ac…4eb8fb` | **MATCH** |
| `v54_exit_tracker.py` | `3ee92864f1afe98ce543803b8b844c1677a6d0e0ce1a6e61d1b7ea74b329a9e0` | `3ee92864f1af…4b329a9e0` | **MATCH** |
| `v54_forward_harness.py` | `11829353123b611818c9eafd36260f95cfd24d3b78157dd09e606a5cb4d1b380` | `11829353123b…1b380` | **MATCH** |

**state.json drift (expected, flagged):** state.json is live harness state
and drifts as observation cycles run; the reconciliation report said so
explicitly. The pinned read (2026-10-13T02:10Z) had `runs=519`,
`last_run=2026-10-13T01:51:15Z`. The copy packaged here was taken after one
further cycle: `runs=520`, `last_run=2026-10-13T02:51:52Z`. The trade record
is unchanged by that cycle — the copy still shows 21 positions, all
`status=closed`, `pending={}`, and the same 21 `close_logged` entries, and
the append-only ledger (`forward_test.jsonl`) still hashes exactly to its
pin. **This copy is the pinned snapshot as of packaging time; it is not
byte-identical to the 02:10Z pin, and the difference is the one intervening
observation cycle's bookkeeping, nothing else.**

## (b) The running-harness diff — what the uncommitted changes actually are

At reconciliation time, `v54_forward_harness.py` was tracked on `main` but
the working-tree (running) copy differed from HEAD (`cb3a30d`, blob
`f71e8aeb9cca…`, file SHA-256 `4162593199adaa…`). Since then, commit
`2787f70` ("Mike-authorized package results…", 2026-10-12) committed the
working-tree harness to `main`, so:

- `git diff HEAD -- v54_forward_harness.py` is **empty today**; HEAD's file
  is now byte-identical to the pinned running version (SHA-256
  `11829353123b…`, git blob `d03a336cf714…`).
- The former uncommitted diff (recoverable as `git diff 2787f70^ 2787f70 --
  v54_forward_harness.py`: 3 hunks, +85/−43 lines, all inside
  `publish_snapshot()`, ~lines 1062–1185) changed **only the snapshot
  publishing transport**:
  - Removed: the GitHub Contents-API path — `GH_OWNER` / `GH_REPO` /
    `GH_CLI` constants and the `gh_cli()` / `gh_args()` helpers that shelled
    out to `gh_contents.py`.
  - Added: a native-git publish — `git()` / `giti()` subprocess helpers using
    a temporary index (tempfile), and a `fail()` step reporter — pushing
    `forward_test/` snapshots to `origin/main` via git instead of the
    Contents API.
- No signal generation, entry/exit logic, sizing, grading, or ledger
  accounting code was touched by that diff. It is the publishing leg only
  (the rewrite originally made 2026-10-06 after the Contents-API credential
  path died; it ran uncommitted in the working tree until `2787f70`).

## (c) Standing caveat — read before citing anything in this package

This package supports **operational reporting reconciliation only**: the
reported flat-book figures (21 closed trades, +13.0547R cumulative, CRWD
+1.6305R, OKTA +3.5523R, 0 open) are exactly the figures recorded in the
pinned ledger, state, and config artifacts. The reconciliation remains
**Claude-reported**; hash claims in the report did not by themselves give
any reviewer the underlying evidence — this package is that evidence, and
independent acceptance is still a separate step.

**+13.0547R is NOT corrected-grid validation.** It does not replace, offset,
or soften the corrected-grid **−15.23R** adverse evidence, and the V5.4
standing verdict — **closed FAIL (2026-10-03), entries paused** — remains
exactly as recorded. Nothing in this package is a performance verdict or a
promotion input.

— Muse (packaging only, 2026-10-13)
