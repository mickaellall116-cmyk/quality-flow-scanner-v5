# THREE-GATE FREEZE — calendar adopted, E3 mode A frozen, S2 rejected (Mike, 2026-10-21)

**Decision:** Mike, in chat 2026-10-21 22:01 ET: "Adopt all three gates as
proposed." The proposals are those of the -87 decision packet
(`research_notes/three_gate_decision_packet_20261021_87/`, commit 186aa0a;
fixtures 42/42). This record executes the three GOs. Nothing else is
authorized by it.

## Gate 1 — CALENDAR ADOPTED

- The -81 candidate extension (artifact sha256 `8d659dde…`, 227 sessions,
  2023-10-19→2024-09-15) is ADOPTED as the qualified companion to
  `XNYS_SESSION_SCHEDULE_V2` (`3358f2d9…`, 524 sessions). The qualified
  calendar of record for the corrected baseline is the union: **751 sessions
  (744 regular + 7 early-close)**.
- **CH-1 carried:** the absence of in-era documentary proof of 09:30–16:00
  core hours for 2023 stands as a DISCLOSED ASSUMPTION on the baseline, with
  the retiring evidence named in -87 Gate 1. Any readout spanning 2023 states
  CH-1.
- **Crypto continuous-calendar spec S-C1…S-C6 is ADOPTED** as the Option A
  contract for the 7 crypto pairs: session = ET calendar date (every date a
  session); six 4H bins anchored 09:30/13:30/17:30/21:30/01:30/05:30 ET
  wall-clock (bins 0–1 ≡ the equity grid year-round); DST absorbed in one
  overnight bin (23/25-bar sessions; absorbing bin is stamp-phase-dependent);
  cross-asset joins key on bin-start labels only; crypto bars never enter the
  XNYS constructor.

## Gate 2 — E3 FROZEN: MODE A (decision-time)

- E3 is frozen as **mode A**: a split event is in a decision's event set iff
  its independently sourced `announced_at` ≤ the decision instant (equality
  inside). Events announced later are excluded and ledgered. Unknown timing
  REFUSES (fail-closed; the switch has no default, per the -84 core).
- Mode B (retrospective) survives ONLY as a fenced diagnostic, labeled
  RETROSPECTIVE_NON_TRADABLE wherever it appears; it is never the primary
  basis of a baseline readout.
- E3 governs split-event timing only. The universe point-in-time axis is
  UPIT (-86 F6) and is untouched by this freeze.

## Gate 3 — S2 REJECTED for the corrected baseline

- REQ-S2 (split-session exclusion) is **REJECTED** as a requirement of the
  corrected baseline and retired as a documented non-requirement, on the
  demonstrated-purpose test: zero demonstrated contamination (-62 audit);
  Twelve Data adjusted uniformly (prices and volume, factor-exact) on the
  only probed split (-75 NVDA); the one observed defect class (TSLA zero
  volume) is completeness, outside S2's domain; the residual mixed-basis risk
  is detectable by the completeness/convention checker.
- **Automatic reopen triggers** — any one reopens S2 for re-adjudication:
  T1 an R7/R30 leg shows a basis revision; T2 checker STEP-ALL/VBASIS lanes
  fire on real captured data; T3 any other vendor non-uniformity evidence.
- Consequence: the split-event producer is **NOT** a predecessor of the
  corrected baseline. The -84 producer core stands as a candidate artifact,
  unadopted. Session handling follows the -82 R1–R5 draft as amended by -86
  A1–A4 (incl. the SPLIT_SPANNING reporting subset), pending the R1–R5
  freeze (G2 extended).

## What this freeze does NOT authorize

No capture, vendor call, spend, backtest, or performance run; no R1–R5
freeze; no guard-v2 or checker-v2 adoption; no shadow activation; no trading
change. Those remain separate gates: R1–R5 freeze → guard v2 → checker v2 →
R7 GO (eligible 2026-10-28) → R30 GO (eligible 2026-11-20) → capture
authorization (ceiling 300) → Phase-1 GO → corrected-baseline run GO.
