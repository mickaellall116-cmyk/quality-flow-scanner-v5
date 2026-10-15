# QF-YAHOO-CLEAN-CAPTURE-PREFLIGHT-20261015-08 r2 — bounded repair

Spec: GitHub Issue #1 comment `6192334316` (review of r1 at `52ee790`).
Scope unchanged: offline/local only; zero Yahoo/vendor/API/model calls,
downloads, installs, spend, backtests, holdout access, or live changes
(the only network fetch was the spec comment itself). Even a PASS would
authorize no Yahoo call; this verdict is HOLD (see G4).

## Verdict: `YAHOO_CLEAN_CAPTURE_PREFLIGHT_HOLD`

Gaps G1–G3 are closed and proven. G4 (durability) is **not** closable
offline on the available evidence and, per the spec's own instruction,
is returned as HOLD with the exact missing storage decision and a
proposed second-copy procedure — durability is not claimed.

## Repair minutes

Repair work began at the spec fetch (~12:56Z) and the repaired suite
passed at 12:58:55Z: **≈3 repair minutes** of the ≤10-minute allowance;
total r2 delivery well inside the original ≤45-minute envelope.
Trials: one suite version, run twice, **11/11 checks both runs,
byte-identical result files**. No failed trials.

## Per-gap closure

### G1 — publication primitive (CLOSED)
r1's `exists()` + `os.rename` is replaced by `os.link(tmp, final)`:
hard-link creation is atomic and raises `FileExistsError` if the final
path exists — no check-then-act window, an existing final can never be
replaced. Temp file is fsync'd before linking; temp is unlinked and the
directory fsync'd after. `os.rename` is no longer used for publication
and is nowhere labeled O_EXCL (the r1 manifest claim is corrected in
`capture_manifest.json`). Proof: **C8**, a real two-process collision —
two child processes concurrently publish different payloads to the same
final path; exactly one returns PUBLISHED, the loser returns
`WRITE_ONCE_COLLISION`, and the final bytes hash to the winner's hash.
C5 re-proves the sequential collision/no-overwrite path on the new
primitive.

### G2 — attempt journal (CLOSED)
Implemented in the fixture-proven code path: `journal_attempt()` appends
an fsync'd JSONL attempt record (plus directory fsync) **before** any
request; `reconcile()` on restart returns `SKIP_VERIFIED` (final file
present, hash matches), `HOLD:FINAL_MISMATCH` (final present, hash
differs), `ATTEMPT_CONSUMED_AMBIGUOUS` (journal entry, no final file —
zero re-request eligibility), or `ELIGIBLE` (neither). Proof: **C9**
exercises all four states, including a journaled-then-crashed attempt.

### G3 — calendar-aware qualification (CLOSED)
`qualify()` no longer hard-codes 7 rows. Expected rows derive from the
pinned session schedule: XNYS full session = 7 hourly bars, 13:00 early
close = 4; crypto uses its separate UTC policy (24 rows/day). Proof:
**C10** — a final 2025-11-28 early-close session with 4/4 rows
QUALIFIES (r1 falsely held this PARTIAL), a truncated 3/4 early close
HOLDs `PARTIAL`, and a 24-row crypto day on the same date qualifies
under the crypto policy. All seven r1 defect cases (C6) still HOLD under
the repaired qualify, including a genuinely partial full session (3/7).

### G4 — durability (NOT CLOSED → HOLD)
Pinned evidence (`archive_mount_evidence_r2.txt`): the absolute archive
root `/home/hatch/workspace/data_archive/yahoo_1h_clean/<capture_id>/`
is on `/dev/mapper/rv`, a 100G block-device volume mounted at
`/home/hatch` — a different persistence class from the overlay root
filesystem and from tmpfs `/tmp`.

That evidence does **not** demonstrate survival across VM replacement:
the destroyed D1 dataset (`backtest_cache/v3`) also lived under this
same home volume, inside the repo working tree, and did not survive the
VM replacement. Offline, the loss mechanism (volume replacement vs.
working-tree restoration discarding non-committed bytes) cannot be
distinguished, so presence on this volume cannot honestly be promoted
to demonstrated replacement-survival. Per the spec, durability is not
claimed.

**Exact missing storage decision:** whether the platform home volume is
guaranteed replacement-persistent for non-git-tracked paths, or whether
an off-VM second copy is required before any capture bytes are treated
as durable.

**Proposed zero/known-cost immutable-copy procedure (for separate
authorization; NOT executed here):** after a capture completes and its
`SHA256SUMS` manifest is pinned, (1) commit `SHA256SUMS` + the capture
manifest to `main` in this repo (hashes only — trivial size), and
(2) push a byte-for-byte copy of the capture directory (est. ~20–30 MB,
every file far under the 100 MB per-file limit) to a dedicated
append-only branch of the existing GitHub repo, making the remote the
immutable off-VM second copy at zero incremental cost. Rollback/
abandon semantics from r1 are unchanged.

## Suite result

`run_preflight_fixture_r2.py`: C0–C7 retained from r1 (C5/C6 on the
repaired mechanisms), C8–C10 new. **11/11 matched, run twice,
byte-identical** (`fixture_results_r2.json` ==
`fixture_results_r2_run1.json`). Socket denial installed before any
code ran; `yfinance` never imported; no engine modules loaded.

## Files (this package)

- `run_preflight_fixture_r2.py` — revised fixture source
- `fixture_results_r2.json`, `fixture_results_r2_run1.json` — results ×2
- `archive_mount_evidence_r2.txt` — G4 mount/persistence-class evidence
- `capture_manifest.json` — revised (publication primitive corrected;
  false O_EXCL and durability claims removed)
- `SHA256_MANIFEST.txt` — regenerated over the full package
- r1 files (`run_preflight_fixture.py`, `fixture_results.json`,
  `fixture_results_run1.json`) retained unchanged as the trial record.
