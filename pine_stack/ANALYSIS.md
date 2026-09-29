# ANALYSIS.md — Combined portfolio-risk stack test

Spec: STACK_SPEC.md (frozen before runs). Final sizing/exposure study — the stack
locks after this. V3.6 entries/exits byte-identical throughout; all four cases
run on the exact same 263 candidate trades (UX51 4H 2024-09-16→2026-09-14),
one consistent accounting (synthetic blended exit price via pb._outcome —
absolute returns comparable WITHIN this study only).

## Verification legs (all before the four cases)

- C0 fidelity vs pb.simulate_portfolio: PASS (263 / +0.195R reproduced exactly).
- R1-only: 154 / +0.324R / 52.78% / DD 32.65% — reproduces the ranking study's
  rs_top2 to the cent.
- R1+R2: 143 / +0.337R / 52.25% / DD 31.63% — reproduces the exposure study's
  stacked_C1 to the cent.
- R3-only: 167 trades, 32.59% / DD 29.64% vs the sizing study's S4
  (29.49% / 29.86%). DD matches; the return gap is the documented accounting
  difference between studies (their S0 was 31.27% where my C0 is 35.30%).
  In relative terms the gate behaves identically: DD cut ~6pp vs own control,
  return ratio ~0.92–0.94 of own control. (R3-only takes 167 vs C0's 160
  because halved risk passes the 5% portfolio-risk check more often.)

## Bull window, @4bps (taken trades)

| Case | n | exp R | PF | ret% | DD% | Calmar | entries@0.5% | sector skips |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| C0 baseline | 160 | 0.239 | 1.35 | 35.30 | 35.17 | 1.00 | 0% | 0 |
| C1 = R1+R2 (rank+sector) | 143 | 0.337 | 1.49 | 52.25 | 31.63 | 1.65 | 0% | 16 |
| C2 = R1+R3 (rank+gate) | 157 | 0.300 | 1.43 | 40.26 | 26.86 | 1.50 | 92.4% | 0 |
| C3 = R1+R2+R3 (all) | 143 | 0.273 | 1.39 | 35.45 | 27.14 | 1.31 | 95.1% | 17 |

@25bps: C0 19.92%/37.16% (Calmar 0.54); C1 39.64%/33.79% (1.17);
C2 31.88%/28.35% (1.12); C3 28.16%/29.96% (0.94). Same ordering.

## Incremental comparison (the decision)

- C3 vs C1: DD cut 4.49pp (31.63→27.14) ✓ ≥3pp, but return sacrificed
  16.80pp (52.25→35.45) ✗ (>3pp allowed).
- C3 vs C2: DD 27.14 vs 26.86 — C3 is 0.28pp WORSE ✗ (no incremental cut).
- At 25bps: C3 vs C1 cuts DD 3.83pp but costs 11.48pp return; C3 vs C2 worse
  on both. Consistent.

Both C1 and C2 beat C0 on return, drawdown, and Calmar — the "neither beats
C0" clause does not trigger.

## 2022 validation (same framework as every prior study, 32 symbols)

- C0 = C1: 37 trades, +0.376R, 11.21%, DD 21.28% — ranking never contested a
  bar and the sector gate never engaged (secskip=0). No harm, skill
  unconfirmed — same pattern as both parent studies.
- C2 = C3: 37 trades, +0.376R, 7.39%, DD 16.36%, 40.5% of entries at half
  risk. The gate engaged and did exactly its job: −4.9pp DD for −3.8pp
  return. No degradation, no blowup.
- No case degrades vs its 2022 baseline in a harmful way.

## Verdict: REDUNDANT — keep the better single brake (C1)

Per the pre-registered rule, C3 fails both prongs: vs C1 the extra DD cut
costs far too much return; vs C2 there is no extra DD cut at all. The gate
works (C2 alone is a good case), and the sector cap works (C1 alone is the
best case), but stacked they solve overlapping problems — the sector cap
trims the clustered losers that the gate would otherwise spend half-risk
entries grinding through.

"Better single brake" = higher Calmar → C1 (1.65) over C2 (1.50), at both
cost legs.

## Locked production stack (exact)

1. **V3.6 signals and exits** — frozen, unchanged.
2. **R1 rs_top2 ranking** — at any 4H bar where valid V3.6 signals outnumber
   free slots (max 5 positions, exits processed first), rank contenders by
   20-bar return minus SPY and take top min(2, free slots). Uncontested bars
   take all; lone signals never deleted.
3. **R2 E1 sector cap** — at each entry event (after same-timestamp exits),
   skip the candidate if ≥2 positions in its sector are already open
   (frozen sector map).

**Not adopted into the stack:** R3 drawdown gate (S4). Archived as a validated
standalone option — it was Mike's strong adopt candidate, and it remains a
legitimate single brake (C2: 40.26% / DD 26.86% / Calmar 1.50), but the
combined test shows it is redundant once the sector cap is in place.

**Sizing/exposure research is now CLOSED.** No more variants. Remaining
sequence item: execution/slippage (last). Engineering requirements
(scanner parity, data integrity, live/backtest reconciliation, logging,
production monitoring) are separate from strategy research.

## Files

- STACK_SPEC.md (pre-registered), ANALYSIS.md (this file)
- stack_results.json (bull window, both costs, verification legs)
- stack_results_2022.json (2022, both costs)
- pine_stack.py, pine_stack.log
