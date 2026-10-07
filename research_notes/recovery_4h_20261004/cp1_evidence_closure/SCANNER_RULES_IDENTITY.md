# scanner_rules.py — Source Identity Mapping

**Date:** 2026-10-06
**Question:** FULL_MANIFEST.json `sources` entry expects SHA-256
`7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac`
for `scanner_rules.py`, but a different version (SHA-256
`62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c`,
Git blob `063c4e3c920cf60e6858ad3eed5d447196e89301`) was observed.
Which is correct?

## Finding: branch divergence, not corruption

Two distinct versions of `scanner_rules.py` exist on two different
development lines. Both hashes are genuine; they refer to different
source states.

| Version | SHA-256 (first 16) | Bytes | Found at |
|---------|-------------------|-------|----------|
| **A (forensic line)** | `7db282ddfc150c9e` | 22,892 | Local working tree; branch `recovery-4h-20261004` (HEAD `b18a010`); commit `b3a7251` ("Candle fixes") |
| **B (hardening line)** | `62aa743ac28f05de` | 23,625 | Remote `main` branch (blob `063c4e3c920c`); branch `hardening-20261004` (commits `0faaa6c`, `03753c4`, "Hardening 2026-10-04") |

Commit `0faaa6c` is **not** an ancestor of the current HEAD (`b18a010`) —
the hardening line was never merged into the recovery/forensic line.

## Which does the manifest reference?

The manifest's expected hash (`7db282dd…`) matches **Version A** — the file
present in the local working tree on the `recovery-4h-20261004` branch,
which is the line the entire CP1 forensic analysis was performed against.

Verified 2026-10-06:
- `sha256sum scanner_rules.py` (working tree) = `7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac` ✅ matches manifest SHA-256
- `git hash-object scanner_rules.py` (working tree) = blob SHA-1 `087dd3a5da82e925b0fa31516763be08c2ceed8d` (SHA-1, not SHA-256 — corrected 2026-10-07)
- Remote `main` blob = `063c4e3c920c…` = SHA-256 `62aa743a…` ❌ different line

## Interpretation

- The manifest is **internally consistent**: its expected hash refers to the
  exact source version the forensic evidence was collected against. No
  overwrite of the expected hash is warranted.
- Version B (`62aa743a…`) is the Oct 4 hardening revision (doc clarifications,
  invariant tests, "zero decision drift" per commit message). It postdates the
  forensic line's branching and was never part of CP1 evidence collection.
- Any claim that "scanner_rules.py does not match the manifest" based on
  observing Version B (e.g., reading remote `main`) is comparing across
  branches. The correct comparison is working-tree file vs manifest, which
  matches.

## Boundary

- Claims depending on `scanner_rules.py` content are **verifiable** against
  Version A (the manifest-pinned bytes, present locally).
- Version B's content has not been forensically examined in the CP1 line;
  no claims are made about it here.
- If a future CP2 preflight needs to reconcile the hardening changes
  against the forensic baseline, that is a separately scoped diff review,
  not part of this closure.
