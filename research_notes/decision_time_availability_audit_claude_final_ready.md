## Amendment 5 — Final Specification-Level Audit

**1. Executive Verdict: READY**

**2. N-11: CLOSED**

Amendment 5 correctly diagnoses what N-11 actually was: not "GitHub is untrustworthy" but "one platform under one custodian's control isn't independent of itself." Requiring a second, structurally different service (external email, outside GitHub) with content cross-referencing the first (Anchor B must embed Anchor A's comment ID) closes the exact vulnerability — an actor with control of the GitHub account/repo can no longer unilaterally rewrite provenance, because doing so would leave the email-anchored record disagreeing with the altered state, and any mismatch is a defined FAIL (§2.4, T16e).

The design holds up under adversarial pressure on its own stated terms:
- **Deletion is handled correctly** — "does not preserve confirmatory status" (T16a/T16b) rather than silently passing.
- **Cross-anchor swapping is closed** — B must reference A's specific comment ID, so an attacker can't pair a stale A with a freshly-fabricated B (T16e).
- **Retroactive validation is explicitly blocked** — T16d correctly states that later-created anchors (A2/B2) can't backdate validity onto an earlier, already-inspected result; it becomes a new manifest version, not a repair of the old one.
- **"External" is defined narrowly enough to matter** — the explicit exclusion list (self-authored files, repo artifacts, draft/unsent email, screenshots, copied timestamps) rules out the obvious ways someone could fake a second anchor without actually leaving an independent record.

**3. Newly introduced finding: none rising to CRITICAL or MATERIAL.**

One **MINOR** housekeeping gap, noted for completeness rather than as a blocker: Amendment 5 supersedes Amendment 4 "only where it allowed GitHub Issue #1 to be sufficient by itself," but doesn't state what happens to any manifest that was already single-anchored under Amendment 4 before Amendment 5 existed — whether such a manifest's confirmatory status is grandfathered, or requires retroactive dual-anchoring to remain confirmatory. Given the framework's own precedent elsewhere (dated amendments retain prior history rather than erasing it), this is a one-sentence transition clause to add whenever a real manifest is affected — it doesn't weaken the control Amendment 5 just built, and as of this audit no candidate has reached confirmatory status under the single-anchor regime, so it's not urgent.

**4. Is the two-service threat model reasonable for this research program? Yes.**

The explicit scoping in §5 is the right move, not a hedge: it states plainly what the control defends against (accidental or motivated single-domain manipulation — a researcher editing their own git history or their own local files after seeing results) versus what it doesn't (a fully compromised, colluding two-platform attack), and accepts the latter as outside the reasonable threat model. That's an honest, proportionate line for a research-integrity control whose actual adversary is self-deception and post-hoc rationalization by the research team itself, not an external nation-state-grade attacker. Escalating to a third-party cryptographic timestamping service, as §5 notes, would be defense-in-depth, not a fix for an actual remaining hole — correctly not required for specification READY.

**5. Minimum additional amendment required: none required for specification READY.**

Optional (MINOR, non-blocking): a one-line transition clause addressing whether pre-Amendment-5, single-anchor-only manifests retain or lose confirmatory status.

---

With N-7 through N-11 all closed and no unresolved CRITICAL or MATERIAL specification gap remaining, the combined governance framework (original spec + Amendments 1–5) is **READY** at the specification level. As Amendment 4 §6 and Amendment 5 §6 both correctly state: this is specification READY only — no candidate (including ERD) may receive an availability PASS until the full T1–T16/T2C deterministic suite actually passes in implementation and dual-anchor validation succeeds in practice.