# Claude independent re-audit request — rev 4

**To:** Claude (independent replication / code auditor)
**From:** Mike (owner)
**Date:** 2026-09-28
**Subject:** Second independent audit — Canonical Reconstruction FROZEN RULES rev 4

## Context

You audited rev 3 and found it materially deficient: the exercise could not
honestly be called a "sealed-oracle" reconstruction because the mandatory
source documents expose the historical results; the audit therefore failed and
rev 3 returned to DRAFT. Rev 4 is the rebuild of the spec under the audit's
reconciliation plus the full rev-4 mandate (GitHub issue #1, comment
`5876792377`, 2026-09-28T19:16:58Z). Rev 4 is at:

- `research_notes/CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV4.md`

I re-audited rev 4 and found four redlines (posted to issue #1); all four are
patched in this revision, and everything else passed my review. Your audit
is the second independent check. Gate order from here: ChatGPT adversarial
re-audit → your re-audit → my final sign-off. Nothing may be built until
all three clear.

## What changed in rev 4 (verify each)

1. **Reframing.** "Sealed oracle" is gone as a blinding claim. Rev 4 calls
   the exercise an **unblinded replication** producing a **reconstructed
   canonical replica** (§0). The oracle-file SHA-256 (§15) is an integrity
   commitment to the comparator file's bytes only — not a blinding device.
   Is this framing honest, and does any residual text still imply blinding?
2. **§2 — full signal-generator transcription.** Rev 4 now transcribes the
   complete V5.4 classifier (historical adapter + decision/cycle-time
   semantics, indicator math with constants, structural contract, protection
   states, entry-YES rule, hard gates, stop/TP1 formulas, grading inputs
   and map, market-gate computation, MTF trend states). Verify the
   transcription against the six canonical docs
   (`canonical_baseline/ENGINE.md`, `LONEWOLF_RERUN.md`, `PIT_FEATURES.md`,
   `PORTFOLIO.md`, `REBASELINE.md`, `UNIVERSE.md`) and the cited live-code
   refs. Flag anything transcribed that the six docs do not support.
3. **A4 → JUDGMENT.** Rev 3's "EXPLICIT in prose" for rs_top2 is relabeled
   JUDGMENT (§7/A4): the source docs pin the symbol leg and the SPY-leg
   endpoint but admit conflicting readings on the SPY-leg lookback, and the
   live path's own RS definition must not be mixed in. Is the JUDGMENT label
   correct, and is the frozen formula still the best supported choice?
4. **B4 completions (§7/A1, A2, A7):** odd-share TP1 floor-split,
   reservation→actual risk transition at fill, zero-share skip,
   full-precision internal math with write-time-only rounding, net-R cost
   denominator (`planned_risk_$ = shares × (entry − stop)`).
5. **B5 completions (§7/A6):** intrabar/close exits free same-T busy,
   explicit `E_mark(T)` snapshot formula, no-bar-at-T stale marking,
   gap-above-target cost accounting (2 leg-equivalents).
6. **B6 completions (§2.6, §2.8):** insufficient daily/weekly history →
   `unknown` → grade C (never A/B); 15m/premarket observational only; no
   auxiliary input gates or vetoes a signal.
7. **B7 completions (§8):** scanner EXIT definition, price input (4H close),
   EMA construction/seeding, bar timing, next-bar-open semantics,
   PP-armed-only path.
8. **B8 (§10):** rev 3's "execute once" replaced with the full rerun
   governance — hash-lock before Run 1, post-run changes cite the frozen
   invariant they restore, independent review before any rerun, Run 1 and
   rerun both retained and reported, no result-driven semantic changes.
9. **B9 (§10, Gate D):** static + behavioral + bug-class tests proving the
   rebuild is independent of the historical numpy-boolean `trendScore` bug
   and score-based mirror logic. Are these tests sufficient and sound?
10. **§1 untracked-file quarantine:** the rebuild may not consult local
    untracked `canonical_baseline/` implementation/data files (unverified
    provenance). Is this quarantine correctly scoped — does it block
    outcome-targeting without blocking legitimate spec sources?

## Audit verdict requested

**READY** (no unresolved material ambiguity — the spec may be signed off) or
**DRAFT** (list every unresolved material ambiguity or honesty problem;
be specific, cite the §/rule). Partial verdicts are not useful: this audit
gates the build, so ambiguity either blocks or it doesn't.

Also confirm: if the spec is built exactly as frozen, would Gate D as
written actually catch a rebuild that accidentally reintroduced a
score-dependent entry path?
