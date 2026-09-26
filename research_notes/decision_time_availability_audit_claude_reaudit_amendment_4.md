## Amendment 4 — Final Specification-Level Adversarial Audit

**1. Executive Verdict: NOT READY**

**2. N-7: CLOSED**
§1 replaces the stale-enumeration risk with a self-updating rule ("READY always points to the version-controlled current suite, never a stale historical enumeration") and states the current suite explicitly (T1–T14, T2C, T15, with T12/T14 pinned to their Amendment 3 semantics). This is a correct fix, not a restatement.

**3. N-8: PARTIALLY CLOSED**
The anchor mechanism genuinely defeats the specific vulnerability it was built for: git commit dates are self-reported and can be forged via rebase/force-push, whereas a GitHub Issue comment's timestamp is server-assigned at posting time and can't be backdated. T15's listed attack vectors (history rewrite, force-push, branch recreation, backdated new commit) are all correctly caught, because tampering with the manifest content or commit will no longer match the externally-anchored SHA256.

But this moves the trust assumption rather than eliminating it — it doesn't close N-8 outright. "GitHub Issue #1" is on the *same platform and under the same account/repo custodian* as the manifest commit itself. The spec protects against rewriting *git history* but says nothing about tampering with the *anchor artifact itself*: editing or deleting the anchor comment after the fact, transferring/deleting the repo, or an account compromise, none of which T15 tests. §2.5 correctly notes a signature "does not prove a commit predated inspection" — the identical critique applies to an editable/deletable comment on the same account: its mere existence today doesn't prove its content was never altered, absent either (a) a genuinely external, non-editable mirror (e.g., the notification copies sent to Issue watchers, or a real third-party timestamp service), or (b) a test specifically targeting anchor-comment tampering. The spec treats the GitHub-issue anchor as sufficient on its own ("minimum accepted anchor") when it has only partially escaped the single-custodian problem the whole mechanism exists to solve.

**4. N-9: CLOSED**
Not prescribing one universal numeric tolerance is the right call, not a discretion gap: default is bitwise equality, any nonzero value must be justified with datatype/library context and frozen *before* inspection, and explicit language forbids selecting it based on whether the invariance test passes. The remaining "how generous is too generous" question is a per-family judgment inherently suited to independent review at audit time, not something a single global constant could correctly capture across heterogeneous feature types.

**5. N-10: CLOSED**
Both components are now concretely specified: an accepted/rejected evidence list for vendor delivery-sequence claims (explicitly excluding lexicographic ordering, file row order, ingestion order, and inferred monotonicity — closing exactly the loophole Amendment 2's original tie-break exploited), and a fully enumerated sparse-stratum fallback (minimum-per-stratum, deterministic merge order, maximum merge breadth, sector-vs-size/liquidity drop order, explicit REVIEW trigger), with no post-hoc invention permitted.

**6. Newly introduced finding**
**N-11 — MATERIAL** — No tamper-evidence protection or test exists for the anchor artifact itself (the GitHub Issue #1 comment), only for the manifest/commit it anchors. As specified, an actor with account/repo access could edit or delete the original anchor comment and nothing in the framework would detect or reject that, since T15 only re-derives content-vs-hash mismatches on the manifest side. This is the one gap actually named by the audit request — the "minimum accepted anchor" is intra-platform separation of trust domains, not genuine third-party independence.

**7. Minimum additional amendment required**
Either:
(a) elevate a genuinely external, non-editable timestamp (independent timestamping service, or the notification-delivery copies sent to Issue watchers, captured and retained as supplementary evidence) from optional to mandatory as the primary anchor, with GitHub Issue #1 demoted to a convenience/coordination copy rather than the sufficient proof; or
(b) if the GitHub-issue anchor is to remain sufficient on its own, require it be posted to a locked/immutable issue (or one where edit/delete permissions are disabled for all parties, verifiably, e.g. via an org-level audit log if available) and add a T16 test analogous to T15 that specifically simulates anchor-comment edit/deletion and confirms it is either prevented or independently detectable.