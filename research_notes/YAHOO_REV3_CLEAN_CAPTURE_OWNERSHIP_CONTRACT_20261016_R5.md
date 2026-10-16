# Rev3 clean capture executor — persistent-ownership contract (r5)

Task: QF-YAHOO-REV3-CLEAN-CAPTURE-OWNERSHIP-CONTRACT-20261016-19 r5
Canonical spec: GitHub Issue #1 comment 6218183861 (fetched first via the
public API; followed exactly).
Claimed verdict: **REV3_OWNERSHIP_CONTRACT_READY** — a PROPOSED contract.
Nothing is adopted, deployed, or implemented by this package; no existing
source file was edited. Design/model only, offline, synthetic.

## Why this round exists

The executor's ownership primitive was never specified; it was
reverse-engineered one attack at a time — r2 (lock = separate pathname
file: symlink/path-replacement), r3 (lock = one journal fd: empty-file
replacement still split the journal), r4 (lock = control-dir fd + fences:
three adjudication gaps remained). r5 therefore specifies ownership as a
contract FIRST, compares designs against an explicit adversary model,
and models journal/control replacement deterministically instead of
waiting for the next fixture to find the next hole.

The three r4 adjudication gaps, restated as contract requirements:

1. Journal replacement still loses restart truth: `fail()` appends the
   HOLD to the still-open old inode, a restart resolves the canonical
   NAME (possibly the empty replacement), opens empty history, and can
   issue the same request again.
2. The promised pre-call fence is absent: `_assert_fences()` runs before
   the ATTEMPT append; between ATTEMPT fsync and `transport(req)` there
   is no fence, so a control/journal swap in that window permits a call.
3. Publication check/use windows: `_write_once_fd()` stats the temp
   inode then unlinks BY PATHNAME (substitution deletes a foreign
   dirent); the final is verified once and can be replaced before
   COMPLETE, which then blesses a replaced name.

## The recommended contract (design (f); normative text: ownership_contract.json)

**Objects.** (i) A dedicated immutable **identity object**
`<capture_id>.identity.json` in the archive parent directory — OUTSIDE
the control dir and the capture root — created O_EXCL and fsync'd before
any ATTEMPT, binding {capture_id, creation nonce, control (dev,ino),
journal (dev,ino), genesis_hash, adopted rev3 pin}. It is the object the
spec now permits *as a proposal*; prior rounds forbade a third file,
which is exactly what made restart truth undecidable. (ii) The journal,
record 0 = GENESIS self-binding {capture_id, nonce, its own (dev,ino),
control (dev,ino)}, hash-chained with exact-key schemas. (iii) The
pinned control-dir fd, whose flock is the only ownership token — there
is no lock file anywhere.

**Invariants.**
- **I1** single transport owner: flock on the pinned control-dir fd.
- **I2** ATTEMPT immediately precedes a call: between ATTEMPT append+
  fsync and the transport call, ONLY the F-PRECALL fence may run; fence
  failure ⇒ no call.
- **I3** durable/reachable restart truth: resolution is identity-first
  (OC-7); no unverified/empty/copied/recycled journal is ever treated
  as fresh history; a consumed ATTEMPT/HOLD in the true journal binds
  every later process.
- **I4** fencing after replacement: journal name, control-dir name, or
  identity-object replacement fences the owner out — live via fences,
  across exit via identity resolution. (The flock alone never proved
  this; it excludes only cooperative contenders while the owner lives.)
- **I5** publication identity: COMPLETE only after F-COMPLETE
  re-verifies the final's (dev,ino) AND content hash; the executor
  NEVER unlinks/renames a dirent it cannot prove is its own via a held
  fd — unprovable dirents are abandoned in place as evidence.

**Verification points.** At open: identity object exists/parses; pinned
component-wise O_NOFOLLOW traversal; flock; single openat of the
journal; GENESIS self-binding + genesis_hash == identity object; full
chain + schema revalidation; F-OPEN namespace identity. Per append:
F-APPEND fence. Per call: F-PRECALL fence after ATTEMPT fsync. Per
finalize: F-FINALIZE temp-identity re-verification → renameat2
(RENAME_NOREPLACE) → F-COMPLETE final re-verification before COMPLETE.
Every post-ATTEMPT failure routes through the single durable HOLD
append on the held journal fd (OC-11); if that append fails →
HOLD:JOURNAL_DURABILITY and the cause is not claimed recorded.

**Restart resolution (OC-7), the clause that closes gap 1.** Trust the
identity object, not the pathname: resolve the control dir by binding
(canonical name whose (dev,ino) equals the binding; else scan the
archive parent for the binding inode → found renamed:
HOLD:CONTROL_REPLACED with the journal located inside it; not found:
HOLD:CONTROL_REPLACED). Resolve the journal name inside the control
dir: (dev,ino) == binding AND nonce/genesis/chain verify → proceed;
symlink → HOLD:PATH_TYPE; different inode → scan control-dir entries
for the binding inode: found under another name →
HOLD:JOURNAL_RENAMED; not found → HOLD:JOURNAL_REPLACED; empty file →
no GENESIS → HOLD:JOURNAL_REPLACED. (dev,ino) alone NEVER suffices
(OC-12): nonce + genesis hash + chain continuity are required, which
is what makes inode recycling decidable.

**Recovery (all out-of-band, separately authorized; the executor never
self-rebinds).** R-1 OWNER_BUSY: wait. R-2 renamed-but-located:
verify the located inode's genesis+nonce+chain against the identity
object; append REBIND; issue a NEW versioned identity object. R-3
replaced-and-not-located: the capture is dead; consumed attempts stand
consumed; retry = new capture_id. R-4 JOURNAL_DURABILITY: all attempts
of the run are consumed-ambiguous until R-2/R-3 disposition.

**Fail-closed codes:** OWNER_BUSY, IDENTITY_MISSING, IDENTITY_MISMATCH,
JOURNAL_REPLACED, JOURNAL_RENAMED, JOURNAL_CORRUPT, JOURNAL_CONFLICT,
JOURNAL_DURABILITY, CONTROL_REPLACED, PATH_TYPE, PATH_RACE,
TEMP_SUBSTITUTED, FINAL_SUBSTITUTED, FINAL_COLLISION,
ATTEMPT_CONSUMED_AMBIGUOUS.

**Platform assumptions.** Linux local filesystem (ext4-class): flock
advisory semantics, fsync durability, renameat2 NOREPLACE, openat /
O_NOFOLLOW component traversal. NFS/network filesystems are OUT of
assumption. (dev,ino) stable per live inode, never trusted across
free/realloc. Adversary = local pathname manipulation between syscalls
(the demonstrated lineage threat), not kernel compromise or pre-setup
identity-object forgery. The contract deliberately buys integrity with
liveness: every attack still costs a HOLD, never a second call.

## Design comparison (full matrix: attack_matrix.json)

Six designs against eleven attacks (journal replace empty/copied/
foreign/symlink, control-dir replace mid-window, component swaps, kill/
restart, two live processes, inode recycling, temp substitution, final
substitution). What each can and cannot prove, in one line each:

- (a) pathname + lock-file flock (r2): proves mutual exclusion only
  while the lock path keeps denoting the same inode; proves nothing
  about the journal.
- (b) single journal fd + flock (r3): proves one writer on one inode;
  cannot prove which inode is canonical after exit (empty split).
- (c) pinned dir fd + fd-relative opens + re-assertion (r4): proves
  live exclusion and live detection; cannot prove restart truth after
  replacement across exit, and its fence misses the ATTEMPT→call
  window.
- (d) identity/genesis binding: proves restart-time authenticity and
  canonicity (replacement, copying, recycling all decidable); proves
  nothing during a run — no lock, no fences.
- (e) hash chain alone: proves content authenticity of a given file;
  cannot prove canonicity — a stale-but-genuine prefix chain verifies
  perfectly (split-brain undecidable), and a fully forged chain from a
  forged genesis verifies too.
- (f) combination (c)+(d)+(e) + identity-bound publication:
  RECOMMENDED — each mechanism covers another's blind spot, and it is
  the only design that survives the full matrix.

## Model evidence (run_ownership_model.py → model_results.json)

A deterministic discrete-event model (abstract inode/dentry/fd/flock
filesystem with inode-number recycling; three executor designs:
A_CONTRACT = (f), B_CHAIN_ONLY = (e), C_R4_LIKE = (c)) over nine traces:
T1 journal→empty live+restart, T1b journal→stale copy, T1c journal→
symlink, T2 control dir replaced between ATTEMPT fsync and call, T3
temp substitution check→unlink, T4 final substitution verify→COMPLETE,
T5 two live owners, T6 inode recycling with forged genesis, T7 benign
kill/restart. ONE run (spec: one run unless the first fails — it did
not fail). Results:

| design | verdict | failing traces |
|---|---|---|
| A_CONTRACT (f) | PASS (9/9) | — |
| B_CHAIN_ONLY (e) | FAIL | T1b, T2, T3, T4, T5, T6 |
| C_R4_LIKE (c), i.e. r4 | FAIL | T1, T1b, T2, T3, T4, T6 |

Acceptance assertions hold for the recommended design on every trace:
no symbol transported twice; no restart ignored a consumed ATTEMPT
(T1/T1b/T6 restart under (c)/(e) re-called S1 — the model reproduces
r4 adjudication gap 1 deterministically: C's live owner detects the
swap, appends its HOLD to the old inode, exits, and the restart opens
the empty canonical journal as FRESH history); no cleanup unlinked a
foreign inode ((f) has no unlink operation at all); no COMPLETE
survived a final-name identity change; no call followed a control-dir
replacement (T2: (f) F-PRECALL → HOLD:CONTROL_REPLACED with zero calls,
and the restart locates truth in the renamed dir and still makes zero
calls). Under (f), T6 is the sharpest trace: the forged journal reuses
the EXACT freed inode number, so its (dev,ino) is identical to the
original — it is rejected on nonce/genesis-hash alone.

## r2–r4 defect → contract clause map

| defect (round) | clause(s) that would have prevented it |
|---|---|
| Separate lock file follows symlinks / can be path-replaced (r2) | OC-8 + OC-4: no lock file exists; the flock lives on the pinned dir fd |
| Journal reopened by pathname per append (r2→r3 finding) | OC-4: single openat, held fd for all appends |
| os.rename overwrites a raced destination (r2) | OC-9: renameat2(RENAME_NOREPLACE) → HOLD:FINAL_COLLISION, destination untouched |
| Post-ATTEMPT failures bypass the durable HOLD record (r2) | OC-11: single durability route for EVERY post-ATTEMPT failure class |
| Forged COMPLETE byte-total accepted / recomputation corrected instead of rejecting (r2 evidence → r3 defect 1) | OC-3: recomputation verifies; record/file mismatch = JOURNAL_CONFLICT, never a silent correction |
| Empty-file journal replacement splits truth (r3) | OC-1 + OC-2 + OC-7: identity-first resolution; empty file has no GENESIS → HOLD:JOURNAL_REPLACED |
| Journal identity = (dev,ino) alone (r3) | OC-12: nonce + genesis_hash + chain required beyond (dev,ino) |
| fail() appends HOLD to old inode while restart trusts the canonical name (r4 gap 1) | OC-7 (+ OC-1): restart never resolves by name alone; renamed true journal is located by binding scan and HELD, not lost |
| No fence between ATTEMPT fsync and transport call (r4 gap 2) | OC-5 F-PRECALL + I2: the fence is the ONLY thing between fsync and the call |
| _write_once_fd stat-then-unlink-by-pathname deletes foreign dirent (r4 gap 3a) | OC-10: the executor has NO pathname unlink operation; unprovable dirents are abandoned in place |
| Final verified once, replaceable before COMPLETE (r4 gap 3b) | OC-5 F-COMPLETE + OC-9: (dev,ino) + content-hash re-verified at COMPLETE time; COMPLETE binds identity, not the name |

## Trials, elapsed, scope

One model run, passed first attempt (27 trace-design cells: 9 traces ×
3 designs); no repairs (design/model task — no repair extension per
spec); zero failures attributable to the recommended design; the B/C
FAILs are the intended comparison evidence, preserved in
model_results.json. Elapsed ≈6 minutes of the ≤30 cap (spec fetch
1792162643 → package manifest sealed 1792162997, epoch seconds). Package commits: design package under
research_notes/yahoo_rev3_ownership_contract_20261016_r5/ + this memo,
left UNCOMMITTED for the parent agent's commit step; evidence commits
cited: r1 298a85e, r2 c82495e, r3 0cdc8cf, r4 94d28f9 (executor
39df9b93…), rev3 candidate 0f562d9, accepted publisher 53bdc67 line.
Scope: offline/synthetic only — no Yahoo/vendor/network/model/API calls
beyond the single public spec fetch; no downloads, installs, spend,
authenticated ops, adoption, capture, publication, backtest, holdout,
or production changes; U-1 remains HOLD, unprobed; no existing source
file was edited (all writes are the new package + this memo); all prior
packages verified byte-identical after the run (frozen rev2 manifest
634c4541… included).

— Muse
