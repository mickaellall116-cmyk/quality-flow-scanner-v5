# STACK_SPEC.md — Combined portfolio-risk stack test on Pine V3.6

**Status: FROZEN before any runs. Written 2026-09-18.**

Final sizing/exposure study. After this, the stack locks and no more variants are run.

## The three rules (previously validated individually; NOT re-derived or re-tuned here)

- **R1 ranking (rs_top2)** — at any 4H bar where valid V3.6 signals outnumber free
  slots (max 5 positions, exits processed first), rank contenders by 20-bar return
  minus SPY and take top min(2, free slots). Uncontested bars take all.
  Verification target: reproduce the ranking study's rs_top2 —
  154 trades, +0.324R, +52.78% return, DD 32.65% @4bps.
- **R2 sector cap (E1)** — at each entry event (after same-timestamp exits), skip
  the candidate if ≥2 positions in its sector are already open, using the
  pine_exposure frozen sector map (2022: extended with COST/WMT→STAPLES,
  JPM→BANKS, exactly as that study's validation). Verification target:
  reproduce E1 — 143 trades, 0.299R, +42.29%, DD 29.68% @4bps.
- **R3 drawdown gate (S4)** — base risk 1.00% per trade; at each entry, if marked
  equity ≤ 90% of running peak, risk halves to 0.50% for that trade; full risk
  restores at ≥ 95% of peak. Verification target: S4 — 29.49% return,
  DD 29.86% @4bps.

Ordering at each entry event: exits → rank ordering → rank cap (R1, contested
bars only) → free-slot check → sector cap (R2) → portfolio 5% risk check →
drawdown gate sets risk_pct (R3) → size. A candidate skipped by the sector cap
does not consume a rank slot (taken_at_t counts takes only).

## Four cases, exact same trades and costs

- **C0** baseline: V3.6 as quoted. Fidelity check: reproduce 263 trades / +0.195R @4bps.
- **C1**: R1 + R2 (ranking + sector cap).
- **C2**: R1 + R3 (ranking + drawdown gate).
- **C3**: R1 + R2 + R3 (all three).

Conventions: UX51 4H 2024-09-16→2026-09-14, V3.6 entries/exits byte-identical
(candidate engine imported from pine_ranking), 4bps and 25bps cost legs,
next-bar-open entries, stop-first ambiguity, one consistent accounting for all
four cases (synthetic blended exit price via pb._outcome — documented; absolute
returns may differ slightly from the historically quoted +35.3%, but every
case sits inside the same accounting so all comparisons are valid).

## Metrics per case (both costs)

return%, expectancy R/trade, PF, maxDD%, Calmar, trades taken, % of entries
executed at 0.5% risk (C2/C3 only), trades skipped by the sector cap (C1/C3
only), and the incremental comparison: C3 vs C1 and C3 vs C2 (extra DD cut in
pp, return sacrificed in pp).

## 2022 validation

All four cases on the 2022 window, same framework/caches as every prior study
(v6_short_v2/cache + pine_exit_fix/cache_2022, signals ≥ 2022-01-01, EOD
liquidation). Report whether any case degrades vs its 2022 baseline; note
where gates never engage.

## Pre-registered decision rule

- **Complementary → adopt full stack C3** if C3 cuts drawdown materially vs
  BOTH C1 and C2 (≥3pp vs each) while sacrificing ≤3pp of return vs the better
  of C1/C2. "Better" = higher Calmar.
- **Redundant → keep the better single brake** (higher Calmar of C1/C2) if
  C3's extra DD cut vs the better single-brake case is <3pp, or costs >3pp
  of return.
- If neither C1 nor C2 beats C0 — report that plainly instead of forcing an
  adoption.
- No new rules, no tuning, no fifth case.

## Locked-stack statement target

After the verdict, the production stack is stated exactly, and sizing/exposure
research is declared closed.
