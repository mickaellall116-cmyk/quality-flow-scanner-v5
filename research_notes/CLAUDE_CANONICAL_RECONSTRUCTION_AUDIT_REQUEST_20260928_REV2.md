# Claude Independent Audit Request — Canonical Reconstruction FROZEN RULES (rev 2)
**Date:** 2026-09-28
**Status:** PRE-BUILD AUDIT ONLY — no reconstruction authorized
**Owner:** Mike
**Supersedes:** `CLAUDE_CANONICAL_RECONSTRUCTION_AUDIT_REQUEST_20260928.md`

## What changed since rev 1 (owner directives 2026-09-28)

1. **No original-machine search.** Mike cancelled it: the canonical files were
   created on the ChatGPT-side workflow and never pushed to GitHub. Proceed as a
   reconstruction; the result will be labeled a reconstructed canonical replica.
2. **No targeting of the old 143-trade result.** Mike ruled the C1 evidence chain
   compromised (numpy boolean trendScore bug — breakout-only entries). The old
   143-trade numbers (+0.337R/trade, +52.25%, ~31.63% DD) are banned from
   validation. The rebuild must come from the surviving specs alone.
3. **Frozen spec exists.** The primary audit target is now:
   `research_notes/CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928.md`
   (commit `22f85ae`), with the sealed Layer-2 oracle at
   `research_notes/CANONICAL_RECONSTRUCTION_SEALED_ORACLE_20260928.json`
   (SHA-256 `2656855d79c3d516d01c4a4b698b298c0fc2c2b2fd6df327f84dbbd5095f1546`).

## Source documents (unchanged)

Audit these six files as the canonical specification set:
- `canonical_baseline/ENGINE.md`
- `canonical_baseline/LONEWOLF_RERUN.md`
- `canonical_baseline/PIT_FEATURES.md`
- `canonical_baseline/PORTFOLIO.md`
- `canonical_baseline/REBASELINE.md`
- `canonical_baseline/UNIVERSE.md`

The original executable/cache artifacts were never committed. Do not assume any
missing implementation detail. Do not propagate the numpy trendScore bug.

## Questions to answer

### 1) Ambiguity resolutions (§4 of the frozen rules)
For each of A1–A7, independently verify the claimed basis against the six docs:
- Is the EXPLICIT / DERIVABLE / JUDGMENT classification correct?
- For A4 (rs_top2): does PIT_FEATURES.md:34 plus `pine_ranking/pine_ranking.py:95-114`
  really pin the frozen formula, including the daily-bar SPY leg?
- For each JUDGMENT item (A2, A5, A6, A7): is the frozen choice the most
  defensible one, and is there a surviving-doc alternative the drafter missed?
- For A1 and A3 (DERIVABLE): does the derivation actually follow, or does it
  smuggle in discretion? Propose the correction if so.

### 2) Oracle split (§2 / §3)
- Is the Layer-1 vs Layer-2 line drawn correctly — i.e., does Layer-1 contain
  anything that could bias an implementation choice toward historical outcomes?
- Are the frozen Layer-2 tolerances honest (neither so tight that Yahoo data
  drift guarantees failure, nor so loose that a wrong implementation passes)?

### 3) No-targeting enforcement (§5)
- Does the frozen spec contain any indirect path by which the historical
  outcomes could steer implementation choices?
- Is the "mismatch = finding, never tuning" rule airtight as written?

### 4) Completeness
- Enumerate any material rule the frozen spec leaves unfrozen that could change
  accepted trades, fills, trade R, ordering, or drawdown.
- Could two competent engineers implement different backtests from the frozen
  spec + six docs while each believing they followed it? If yes, list the gaps.

### 5) Do-not-proceed checklist
Produce the blocking checklist as before. In particular: is the spec now tight
enough that a rebuild is meaningful, or does it remain NOT READY?

## Audit standard (unchanged)
- Do not optimize anything. Do not propose new trading rules.
- Do not use any published headline to reverse-engineer choices.
- Prefer "not reconstructable" over filling a gap with a plausible guess.
- Preserve disagreements explicitly.
- Final output is a reconstruction audit, not code.

## Requested verdict format
End with exactly one of:
- **READY TO RECONSTRUCT**
- **READY WITH EXPLICIT AMBIGUITIES FROZEN FIRST**
- **NOT READY TO RECONSTRUCT**

Then the minimum actions required before Muse may write code.
