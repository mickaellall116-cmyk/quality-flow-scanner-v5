# Claude independent re-audit — request (rev 5)

**From:** Mike
**Date:** 2026-09-28
**Re:** independent re-audit of the Canonical Reconstruction FROZEN RULES rev 5
**Audit package (Mike relays):**
- `research_notes/CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV5.md` (the spec)
- `research_notes/claude_audit_bundle_rev5/` — byte-identical copies of the
  recovered local `v54_engine.py` /
  `v54_rules.py` + `PROVENANCE.md` (SHA-256 hashes, mtimes, role statement)
- this request

## Context

Rev 4 (ChatGPT final PASS 20:13Z + Mike's final re-audit PASS) was returned
to DRAFT by the accepted Claude-audit reconciliation (issue #1, comment
`5877927506`, 2026-09-28): ChatGPT independently re-checked the material
findings against the pinned support code and found its own rev-4 PASS too
permissive on provenance/behavior contradictions. Rev 5 implements that
mandate's M1–M7 plus all listed non-blocking corrections. **No
reconstruction code has been written; no build is authorized.**

The exact local V5.4 wrapper/grader files were recovered and hashed before
any further read: `v54_engine.py` →
`bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb`;
`v54_rules.py` →
`1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a`.
Every §2 rule carries a COPY/DERIVABLE/JUDGMENT basis note; the consolidated
ledger is Appendix P. Authorship: the four redlines R1–R4 were authored by
ChatGPT and adopted by Mike; ChatGPT's mechanical re-audit produced C1–C3;
Mike's F1 identified the MTF weekly-window impossibility.

## What changed vs rev 4 (verify each)

1. **R-1 — grade-precedence reversal.** Rev 4 froze unknown→C first (ChatGPT
   C1). Rev 5 freezes the bytes' literal order as COPY
   (`v54_rules.v54_grade`: B-first incl. `or gate==CONFIRM`, then
   unknown→C, else A — Appendix P, P8; the handoff brief's "and/or market
   CONFIRM" corroborates). Is the reversal correctly grounded, and is the
   C1 supersession honestly recorded (Appendix R)?
2. **M1 (VWAP, §2.2):** frozen to rolling-50 on the rebuilt 4H series,
   labeled JUDGMENT, SessionVWAP alternative recorded/rejected. Is the
   freeze exact and the rejected alternative fairly stated?
3. **M2 (seeding, §3):** all-history from `first_available_4h_bar`,
   labeled JUDGMENT; the live-faithful 180d alternative recorded. Exact
   enough to build from?
4. **M3 (buy-zone rounding, §2.3/§2.4):** engine entry uses raw bounds;
   the hard gate re-checks the rounded serialized zone (COPY). Is the
   two-step freeze faithful to the bytes and `_inside_buy_zone`?
5. **M4 (RISK-OFF veto, §2.6):** veto absence now proven by the bytes
   (P9), not JUDGMENT; legacy veto recorded as V5.3-only. Does the
   evidence support this?
6. **M5 (provenance):** bundle hashes match the stated files; per-rule
   classifications (Appendix P) accurate?
7. **M6 (Gate D, §10):** D4 differential oracle (independent
   implementation, identical eligible identity set across every evaluated
   bar); D5 synthetic anti-score fixtures (BUY + PULLBACK + RISK-OFF cases,
   fixture/twin identity); D1/D2 demoted to supplementary. Are D4/D5
   specified tightly enough to actually prove score-absence, or do they
   leave gaps?
8. **M7 (PORTFOLIO.md, §1):** pinned to blob `8ddc1e61…` at `368fa2e`;
   rev-3 bundle's differing copy declared noncanonical/superseded. Sound?
9. **Non-blocking corrections:** grading-only vs acceptance (§2.6); QQQ
   early-history (§2.7); §4/§2.8 early-close reconciliation; EMA21 rising
   `>=` (§2.8); `E_mark(T)` → `remaining_shares` (§7/A6); non-circular
   Layer-1 (§5A/§5B); dividend-adjustment limitation (§11); SEALED legacy
   filename (§15); authorship normalization (§1). Any missed or
   mishandled?

## Audit verdict requested

**READY** (no unresolved material ambiguity — the spec may be signed off) or
**DRAFT** (list every unresolved material ambiguity or honesty problem;
be specific, cite the §/rule). Partial verdicts are not useful: this audit
gates the build, so ambiguity either blocks or it doesn't.

Also confirm: (a) if the spec is built exactly as frozen, would Gate D
(D4+D5) as written actually catch a rebuild that accidentally reintroduced
score dependence or the RISK-OFF veto? (b) Does any frozen JUDGMENT choice
(M1/M2) or reversal (R-1–R-5) look like it was steered by Layer-2 fit
rather than source evidence?

Required order remains: **ChatGPT rev-5 audit → Claude rev-5 independent
audit → Mike explicit final sign-off → §13 Phase-0 amendment → build.**
No build, no Layer-2 targeting, no production V5.4 change.
