# THREE-GATE DECISION PACKET — SUMMARY (task -87)

**Purpose.** One consolidated, evidence-pinned packet preparing three
gates for simultaneous adjudication, in dependency order, per
ChatGPT's assignment (Slack TS 1792630429.286729, 2026-10-21 20:53:49
ET) and Mike's Option A universe ruling (freeze commit `2705c02`).
**This packet decides NONE of the gates.** Each gate below carries a
proposed ruling in signable freeze text, the evidence pin for every
claim, the unresolved risks stated plainly, the minimal synthetic
tests (executed where small — **42/42 checks PASS**, outputs in
`fixtures/output_*.txt`), and the exact separate GO that adopts it.
Gates take effect in the order 1 → 2 → 3: a later gate's ruling is
not operative until its predecessors are adopted.

**Standing constraints honored:** offline documentation + isolated
synthetic fixtures only; no vendor calls, spend, captures, backtests,
or holdout access; no production or pinned-file edits; no shadow
activation; Option A UX51 intact (`b5d8877e…`); all prior FAIL/HOLD
verdicts and pins untouched.

---

## The three proposed rulings

**GATE 1 — CALENDAR ADOPTION.** Adopt the -81 candidate extension
(sha256 `8d659dde…`, 227 sessions, 2023-10-19→2024-09-15) as the
qualified companion to `XNYS_SESSION_SCHEDULE_V2` (sha256
`3358f2d9…`, 524 sessions) — the qualified calendar becomes the
disjoint union, **751 sessions (744 regular + 7 early-close)** —
carrying the 2023 core-hours sub-gap as disclosed assumption **CH-1**
(in-era dated proof of 09:30–16:00 for 2023 is absent; retiring
evidence is named), AND adopt the **crypto continuous-calendar
specification S-C1…S-C6** (ET-anchored sessions, six 4H bins per
date, 09:30/13:30 anchors shared with the equity grid, DST absorbed
in overnight bins, strict isolation from the XNYS constructor) as
the Option A calendar contract for the 7 crypto pairs.
→ Detail: `GATE1_CALENDAR_ADOPTION.md`. Fixtures: 13/13 + 8/8 PASS.

**GATE 2 — E3 SPLIT-EVENT TIMING.** Freeze **mode A (decision-time)**
as the E3 rule: a split event may affect a decision only if its
independently sourced `announced_at` ≤ the decision instant;
later-announced events are excluded and ledgered; unknown timing
refuses; mode B text is provided in full as the alternative (its
basis is labeled RETROSPECTIVE_NON_TRADABLE and can never serve as
the baseline's primary basis). **Recommendation: A** — the corrected
baseline exists to answer a tradability question, and a
retrospective event set cannot answer it. E3 is split-event timing
only; the universe axis is UPIT (-86 F6) and is not touched here.
→ Detail: `GATE2_E3_SPLIT_EVENT_TIMING.md`. Fixtures: 11/11 PASS
against the -84 producer core.

**GATE 3 — S2 DISPOSITION.** **Recommendation: REJECT** REQ-S2
(split-adjacent session exclusion) as a requirement for the
corrected baseline — retire it as a documented non-requirement with
automatic reopen triggers T1–T3. Ground, per Mike's governing
purpose test (demonstrated data-quality purpose, never returns):
-62 found S2 inherited prose-only with **zero** demonstrated
contamination; -75 then supplied the first direct vendor evidence
and found Twelve Data adjusting **uniformly** (prices and volume,
factor-exact, flipping on the effective date) — the mixed-basis
corruption S2 guards against did not occur where it was actually
looked for; the only defect ever observed (TSLA) was a completeness
failure S2 does not address; and the residual mixed-basis risk is a
**detectable** defect class (convention/completeness checker), while
adopting S2 would make the whole baseline hostage to a split-event
producer + qualified source that **do not exist** (GATE-E1 unmet,
`/splits` is paid-tier and excluded). Under REJECT, the GATE-E1…E5
producer is **not** a baseline predecessor; under ADOPT it is, and
the -85 earliest-qualified estimate does not survive.
→ Detail: `GATE3_S2_DISPOSITION.md`. Fixtures: 10/10 PASS.

## The three GOs (each separate, each Mike's alone)

1. **GO — Gate 1** (calendar adoption + CH-1 + crypto spec S-C1…S-C6).
   Unlocks: a qualified 751-session calendar; the capture manifest
   can be written against real session/bin definitions for all 51
   symbols.
2. **GO — Gate 2** (freeze E3 mode A — or, by Mike's substitution,
   mode B). Unlocks: the producer/assembly design point is frozen;
   any future event-fed component has a timing rule.
3. **GO — Gate 3** (REJECT S2 with triggers T1–T3 — or ADOPT, or
   HOLD, each with stated consequences). Unlocks under REJECT: the
   producer drops off the baseline's critical path; the remaining
   chain is the R1–R5+A1–A4 freeze (G2-extended), guard/checker
   adoption, and the capture authorization per -85.

## What remains after all three gates

The -85/-86 chain, unchanged: S2's removal from the path leaves the
R7 (≥2026-10-28T21:33:00Z) / R30 (≥2026-11-20T21:33:00Z) revision legs
as evidence instruments (and as S2's reopen triggers), the session-
policy freeze, the constructor-guard and checker adoptions, then
capture authorization (proposed ceiling 300 credits) — earliest
qualified dataset ≈ Nov 27 – Dec 1, 2026 (estimate, -85).
