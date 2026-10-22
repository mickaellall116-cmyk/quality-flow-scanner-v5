# REPROOF PLAN — what adoption of the H3b guard / split-event producer would require

**Task:** QF-TD-SAFEGUARDS-PREP-20261021-84. **Status: PLAN ONLY —
nothing in this document is executed by this task.** Both candidates
are OFFLINE_CANDIDATE_NOT_ADOPTED. Adoption of either is a separate
governance sequence ending in Mike's GO; this plan enumerates the
pins that would change and the re-proof each change triggers, so the
cost of adoption is known before anyone proposes it.

## A. H3b constructor guard — adoption impact

Adoption form (per SPEC_GUARD_H3B §4): a NEW constructor version —
the guard folded into a successor of `construct_4h.py`, or the guard
bound as a named chain element the entrypoint must call — minted
under its own adjudicated task. Never an in-place edit.

### Pins that CHANGE on adoption

| element | current pin | on adoption |
|---|---|---|
| constructor `construct_4h.py` | d47e8df14ec5… | NEW pin (successor file) |
| route manifest `ROUTE_MANIFEST_CANDIDATE_V2` | 9573118c… | superseded by a successor manifest binding the new constructor pin |
| entrypoint `pilot_build_v7_clibound.py` | 84ccd2c6… | changes ONLY if its bytes change (wrapper-binding form); unchanged in the folded form only if the entrypoint already delegates — assume it changes and re-proof either way |
| fixture copies citing d47e8df1… (-82 suite, this package's guard suite) | — | re-extracted at the new pin; suites re-run; the -82 T3 expectation inverts (merge → refusal) under the guard and must be re-baselined as a NEW expectation, never edited in the old packages |

### Pins that do NOT change (verify, don't assume)

validator ca3bafd8… · CLI-guard constructor 3f432e7e… · adapter
6980b5b3… / driver d11c6b58… / gate 94ef967c… / executor bbc23616…
(r5 set) · supplement v2 55ad6f40… · calendar artifact 3358f2d9… ·
fold materializer / inference layer — all unchanged unless their
bytes change; the re-proof must VERIFY each pin against the
successor manifest rather than trusting this table.

### Re-proof sequence (adoption, in order)

1. Successor constructor + successor route manifest drafted as
   CANDIDATE (old pins remain the live evidence; nothing is
   overwritten).
2. Full offline route-proof suite re-run against the successor
   chain (the -49…-58 class gates: constructor/validator/entrypoint
   cases, clock, NLQUAL) — all must pass on the new bytes.
3. **Candle parity gate** (standing rule, from the 2026-10-03
   failure): backtest-path and live-path construction from
   identical inputs compared as actual OHLCV bars — byte-identical —
   spanning a DST boundary and two different window lengths, now
   WITH the guard active on both paths; plus a duplicate-injection
   parity case proving both paths refuse identically.
4. The -82 hardening fixtures re-run at the new pin (T1/T2
   unchanged; T3 re-baselined per above) + this package's guard
   suite re-pointed at the successor.
5. Independent review (Claude targeted re-review + ChatGPT
   adjudication) of the successor package.
6. **Mike's adoption GO.** Until then the successor remains a
   candidate and the d47e8df1… chain remains the only cited route.

## B. Split-event producer — adoption impact

Adoption form: the producer is a NEW component (no existing file is
modified by its existence). Integration additionally requires the
assembly point (SPEC_SPLIT_PRODUCER §7) — also new — and a qualified
event source (§3/§9 of the spec), which does not exist yet.

### Pins created (none exist today)

| element | on adoption |
|---|---|
| producer core module | NEW pin (successor of this candidate, after source binding) |
| event-source acquisition leg (endpoint, request manifest, receipt schema) | NEW pins — GATE-E1; the source itself needs its own qualification task |
| producer envelope schema (`split-events-v1`) | frozen as a versioned contract at adoption |
| assembly module (bars + envelope + entries → S2) | NEW pin |
| calendar artifact used by the producer | the pinned artifact of record at adoption time (today: 3358f2d9…, forward window; a holdout-window run would use the -81 candidate extension ONLY if separately adopted — it is CANDIDATE_NOT_ADOPTED) |

### Pins that do NOT change

S2 transform 7791ca91… (consumes the envelope's events unchanged —
its six required fields are a subset of the producer schema) ·
the constructor chain (all pins in §A's "current" column) ·
validator · fold materializer · inference layer. S2 integration
changes the ASSEMBLY, not the transform.

### Prerequisites that are NOT pins (governance, in dependency order)

1. **Qualified event source** selected + authorized (Mike) and
   qualified against GATE-E1/E2 (coverage attestation bound into a
   pinned receipt). The documented TD `/splits` route is Grow+
   paid-tier and excluded — selecting any source is a fresh
   decision with cost/terms on the table.
2. **E3 PIT freeze** (Mike): (A) decision-time vs (B) retrospective.
   The producer refuses to run unset; integration cannot be
   proposed before the freeze.
3. **S2 purpose disposition** (adjudication): the -62/-82 question
   of S2's demonstrated data-quality purpose must be resolved or
   the gate re-scoped before integration is proposed.
4. Assembly built + fixture-proven (envelope-state check, E2
   set-equality check, E5 calendar-pin check, frozen-mode check)
   on synthetic data, then independent review.
5. **Mike's integration GO.**

## C. What this task did NOT do

No pin above was changed, minted, or re-proven. No production or
pinned file was edited. The candidates in this package cite the
current pins as evidence and will themselves need re-basing if any
adoption step above is ever executed.
