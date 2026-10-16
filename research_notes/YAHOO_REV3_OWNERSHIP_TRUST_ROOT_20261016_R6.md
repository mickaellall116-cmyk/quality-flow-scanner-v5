# Rev3 ownership trust-root correction (-19 r6) — REV3_OWNERSHIP_TRUST_ROOT_READY (offline contract scope)

Spec: Issue #1 comment 6219711702. Design/model only; nothing implemented, adopted, or run live. U-1 HOLD.

## The trust-root defect, stated precisely

r5's identity object (`<capture_id>.identity.json`, commit e18ebea) is a pathname object in the same mutable archive-parent namespace it polices. `O_EXCL` gives creation exclusivity, not post-creation immutability: nothing prevented later rename/replacement. Restart resolution (OC-7) read the canonical identity pathname and trusted the bindings, nonce and genesis hash found inside it. After owner exit, a coherent replacement of identity + control + journal therefore presents a self-consistent new world and is accepted as fresh. The anchor itself needed an anchor — the circularity was moved up one file, not removed. (r5's own model also smuggled an oracle: the expected nonce was a module-level constant. r6 removes it in every design — the expected nonce/genesis come only from the trusted identity artifact under test.)

## Model (r5 engine + traces T1–T7 reused verbatim; T8/T9/T10 added)

Four designs, identical r5-(f) machinery (hash-chained journal, dirfd flock, fences at open/append/pre-call/complete, abandon-never-unlink), differing ONLY in the identity trust root: **A_CONTRACT** = r5 baseline (pathname identity); **D_ROOT_NS** = identity anchor in a privileged, adversary-non-writable namespace; **E_SIGNED** = data-tree identity + detached signature under a pinned verification key; **F_VERITY** = data-tree identity + fs-verity, expected digest sourced from the journal GENESIS.

- **A_CONTRACT: FAIL — T9, T10.** T9 (coherent forged bundle after owner exit): restart returns ok → `DOUBLE_CALL:S1`. T10(b) (prior-generation bundle after capture-id reuse): accepted as current → `DOUBLE_CALL:S2`. This deterministically confirms the adjudication.
- **D_ROOT_NS: PASS 12/12.** T8: anchor replacement attempts are EPERM, state unchanged. T9: `HOLD:CONTROL_REPLACED` (consumed state read from the anchored journal inode; replacement world never adopted). T10: prefix replay `HOLD:JOURNAL_REPLACED`; prior-generation replay `HOLD:CONTROL_REPLACED`.
- **E_SIGNED: FAIL — T10 only.** T9 closes (`HOLD:IDENTITY_SIGNATURE` — the adversary cannot forge the signer role's signature). T10(b) fails: a *genuine* older signed bundle verifies perfectly and is accepted as current → `DOUBLE_CALL:S2`. **A signature proves authenticity, not freshness.** Closing replay under (B) requires an external monotonic registry — design A's namespace by another name.
- **F_VERITY: FAIL — T9, T10.** fs-verity authenticates a file against a digest whose provenance, in this construction, is the adversary-writable journal: the forged bundle is self-consistent on both sides of the comparison. Verity only becomes a root if its digest is pinned in a privileged store — at which point the design has silently become design A with extra machinery (plus ext4/btrfs + kernel constraints, and the append-only journal can never be verity-protected at all).

## Recommended minimal design: privileged anchor namespace (D)

Full checkable rules in `trust_root_contract.json` (TR-1…TR-8). In one paragraph: the anchor is installed **only by a privileged setup role**, O_EXCL, in a root/anchor-uid-owned directory (0755 dir, 0444 file) where the executor and the path adversary hold **no write or rename rights** — replacement is a kernel EPERM, not an application-level detection. The anchor binds capture_id, nonce, journal/control (dev,ino), genesis hash, status and head. It is never replaced in place; the only transitions are privileged **seal** (finalizer records the terminal chain head) and **retire**. Restart trusts only the namespace copy (TR-4/TR-5); a missing or mismatched anchor is `HOLD:ANCHOR_MISSING`, recovery is out-of-band under separate authority, and the executor never self-rebinds. The word "immutable" is retired in favor of created-by / writable-by / replaceable-by / verifiable-at (TR-8).

## Residual trust assumptions (contract clauses TCB-1…TCB-6)

Kernel uid/permission enforcement and privileged-account integrity (a hostile root is explicitly outside the model — against it, nothing holds, and the contract says so); honesty of the setup/finalizer roles at install/seal; the anchor-namespace path resolved at process start from deployment configuration (parent-component games fail closed: missing anchor or binding mismatch, never silent acceptance); (dev,ino) never trusted alone (inode recycling — always + genesis hash + nonce from the anchor); local POSIX fs only; live-run in-memory state between fences as bounded in r5. **When the root itself is contested, nothing about restart state is provable from filesystem artifacts alone** — the contract's answer is HOLD with zero transport calls pending out-of-band adjudication: safety preserved, availability explicitly not claimed.

## Readiness separation (per spec)

- **Offline contract readiness: READY** (this package).
- **Privileged setup required: NOT DONE** — anchor namespace + setup/finalizer roles do not exist on the host; creating them is a production change needing separate authority.
- **Executor implementation readiness: HOLD.**
- **Live acquisition/adoption authority: HOLD** (rev3 adoption, U-1, any capture — unchanged).

## Runs and trials (all preserved)

- Run 1 (`model_results_run1.json`): all four designs FAIL T4 — a **harness artifact**: r5's T4 hard-coded its own design name for the pre-COMPLETE re-verify path, misrouting the three new r6 designs. Attack and assertion unchanged; the branch was parameterized on the design's declared fences (`"complete" in fences`) and nothing else was touched.
- Run 2 (`model_results_run2.json`, copied to `model_results.json`): D_ROOT_NS PASS 12/12; A FAIL T9/T10; E FAIL T10; F FAIL T9/T10. Model verdict: `REV3_OWNERSHIP_TRUST_ROOT_MODEL_PASS`.

Elapsed ≈19 min of the ≤20 cap (incl. one transient GitHub rate-limit retry on the spec fetch — same public route, succeeded). Evidence base verified byte-identical; no existing source file edited; package uncommitted.
