# Claude Independent Audit Request — Canonical Reconstruction FROZEN RULES (rev 3)
**Date:** 2026-09-28
**Status:** PRE-BUILD INDEPENDENT AUDIT ONLY — no reconstruction authorized
**Owner:** Mike
**Supersedes:** `CLAUDE_CANONICAL_RECONSTRUCTION_AUDIT_REQUEST_20260928_REV2.md`

## Audit target

Primary frozen specification:
- `research_notes/CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928.md`
- frozen-rules rev 3 commit: `60776c340d00cd4f424c777e151c1f4b9e3e0e0a`

Sealed post-run oracle:
- `research_notes/CANONICAL_RECONSTRUCTION_SEALED_ORACLE_20260928.json`
- SHA-256: `90962b798e3f442bb4df854fd34fc823c564a4a003753b3590a0cca89e7fc61a`

ChatGPT has re-audited frozen-rules rev 3 and marked the rules package PASS for independent Claude audit. Your role is an independent pre-build adversarial audit, not implementation.

## Owner directives that are already frozen

1. **No original-machine search.** The missing canonical executable/cache artifacts were created in the prior ChatGPT-side workflow and were never committed. Proceed as a reconstruction, not a recovery. Any result must be labeled **reconstructed canonical replica**.
2. **Do not target the old 143-trade C1 result.** That evidence chain is compromised by the historical NumPy boolean trendScore mirror bug. The 143-trade figures are banned as validation targets, gates, or tie-breakers.
3. **Do not propagate the NumPy trendScore bug.**
4. **Do not alter live V5.4.** Reconstruction code is research-only and must remain isolated.
5. Historical backtest-output counts and performance comparators are sealed until after the locked run. They may not steer implementation choices.

## Canonical specification set

Audit these six surviving documents as the specification evidence:
- `canonical_baseline/ENGINE.md`
- `canonical_baseline/LONEWOLF_RERUN.md`
- `canonical_baseline/PIT_FEATURES.md`
- `canonical_baseline/PORTFOLIO.md`
- `canonical_baseline/REBASELINE.md`
- `canonical_baseline/UNIVERSE.md`

The original executable/cache artifacts were never committed. Do not assume missing implementation details and do not infer them from historical outcomes.

## Questions to answer

### 1) Ambiguity resolutions (§4 of frozen-rules rev 3)

For A1–A7, independently verify:
- Is the EXPLICIT / DERIVABLE / JUDGMENT classification accurate given only the surviving evidence?
- Does the frozen choice leave any implementation discretion that could change accepted trades, fills, R, ordering, heat, or drawdown?
- If a surviving document supports a materially different interpretation, identify it explicitly. Do not choose the interpretation that best matches historical outcomes.

Specific checks:
- **A1:** heat after partial TP1 — is the remaining-shares × original `(entry-stop)` convention adequately frozen as a JUDGMENT choice?
- **A2:** pending-entry reservation — is slot + $750 heat reservation from signal acceptance through fill/invalidation deterministic and internally consistent?
- **A3:** same-timestamp candidate processing — is busy → slot/rank → heat first-fit fully deterministic as written?
- **A4:** independently verify the self-contained `rs_top2` definition in rev 3 against the surviving prose: symbol leg = 20 closed 4H bars; SPY leg = 20 completed SPY daily bars ending at the last completed daily bar ≤ signal-bar close; strict PIT; unrankable behavior and tie-breaks. Do **not** rely on the unavailable `pine_ranking.py` source. If the basis label should be changed, say so, but do not change the formula based on historical fit.
- **A5:** early-close decision timestamp — assess whether 13:00 ET is a defensible frozen JUDGMENT rule.
- **A6:** event ordering — verify the explicit close/open sequence, the placement of new-signal decisions, slot release/use, pending fills, and the fixed `E_mark(T)` equity snapshot.
- **A7:** rounding — verify there is no remaining rounding discretion outside Mode B.

### 2) Oracle split (§2 / §3)

- Confirm Layer 1 contains only input/construction/rule-parameter invariants and no backtest-path outcomes capable of steering implementation.
- Confirm raw candidate count, skip funnel, accepted count, open-at-end, performance, cost ladder, year splits, concentration and overlay comparators are post-run only.
- Assess whether Layer-2 tolerances are suitable as forensic comparators rather than reconstruction targets.
- Flag any comparator that could still create an incentive to tune after a mismatch.

### 3) No-targeting enforcement (§5 / §7)

- Is the ban on the old 143-trade C1 result airtight?
- Is the rule “mismatch = finding, never tuning permission” operationally sufficient?
- Could any visible surviving prose or Layer-1 value indirectly be used to reverse-engineer the old portfolio path? If yes, identify the path.

### 4) Completeness / deterministic implementation

- Enumerate any material rule still unfrozen that could change accepted trades, fills, trade R, ordering, heat, equity marks, costs, or drawdown.
- Could two competent engineers independently implement different backtests while each honestly following frozen-rules rev 3 + the six canonical docs? If yes, list the exact gaps.
- Check data provenance, session construction, early closes, DST, missing-data handling, eligibility windows, entry invalidation, Mode B behavior, cost timing, and deterministic sorting.

### 5) Do-not-proceed checklist

Produce a concise blocking checklist. Distinguish:
- **material blockers** that must be frozen before any build;
- **non-blocking limitations** that should remain documented but do not prevent reconstruction.

## Audit standard

- Do not optimize or propose new trading rules.
- Do not use published historical outcomes to resolve ambiguities.
- Prefer “not reconstructable” over filling a material gap with a plausible guess.
- Preserve disagreements explicitly.
- Do not write reconstruction code.
- Do not open/use the sealed oracle to choose implementation semantics.
- Treat Yahoo/data drift as a possible post-run forensic explanation, never as permission to loosen a frozen rule or tolerance.

## Requested verdict format

End with exactly one of:
- **READY TO RECONSTRUCT**
- **READY WITH EXPLICIT AMBIGUITIES FROZEN FIRST**
- **NOT READY TO RECONSTRUCT**

Then list the minimum actions required before Muse may write reconstruction code.
