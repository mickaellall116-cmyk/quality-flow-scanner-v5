# Outcome-Blind Feasibility / Readiness Result — Preregistration v0.3

**Method (binding).** This result uses **only existing committed metadata and census counts**. No forward returns were computed; no group differences were examined; no rules were changed; no new data was acquired. Planning parameters (μ, σ, δ) below are the **already-frozen planning constants carried from v0.2** (per-trade σ = 1.8R from the ledger; paired-excess σ = 2.6 ATR, Claude's estimate; planning μ = +0.17R; δ = 0.05R / 0.10R / 0.10 ATR), cited as planning constants, **not re-estimated** here. Feasibility is therefore assessed on: accrual rates, required-n under the corrected arithmetic, measurement readiness, and calendar coverage — nothing else.

## 1. Known event counts (committed census)

| Quantity | Value | Source |
|---|---|---|
| All-fire BUY signals, DEV window (ALL_SIGNAL_FIRE) | **2,892** | -29 `allfire_summary.json` (commit `539e0a9`) |
| — matched standalone candidates | 590 | same |
| — suppressed-overlap fires | 2,301 | same |
| — gap-ineligible entries | 1 | same |
| — unclassified | 0 | same |
| Portfolio candidates (ledger rows) | 590 | -13 ledger, sha `267e794c…` |
| Taken, by cost view (own taken sets) | gross 191 · 4 bps 191 · 25 bps 189 | -29 `per_view_summary.json` (commit `2cf06fc`) |
| Closed, by cost view | gross 188 · 4 bps 187 · 25 bps 185 | same |
| Censored at DEV boundary, by view | 3 / 4 / 4 | same |
| Dispositions (4 bps C1) | taken 191 / skipped_rank 326 / skipped_risk 45 / skipped_gate 28 | -30 semantic pins (commit `d077532`) |

## 2. Accrual rates (DEV realized, outcome-blind counts only)

DEV window: 2024-09-16 → 2026-10-16 = **25.0 months**.

| Rate | Value | Derivation |
|---|---|---|
| Candidates | ≈23.6 / month (≈283 / year) | 590 / 25.0 months |
| Closed trades | **≈7.5 / month** | 187 / 25.0 months (4 bps view) |
| Raw signal fires | ≈115.7 / month | 2,892 / 25.0 months (before de-clustering/suppression; context only) |

**Floor projections at the DEV realized closed-trade rate** (forward Tier 4 accrual is prospective and may differ; these are planning projections from counts alone):

- H-SYS / H-EXIT floor, 100 closed trades: **≈13–14 months** of forward collection (corrects v0.2's 6–8 months, which was projected from the candidate rate).
- H-BUY floor, 200 de-clustered events: sooner than the closed-trade floor under every recorded rate; the exact de-clustered forward accrual is measured by the P8 journal once collection starts.

## 3. Required-n under the corrected arithmetic (before design effect)

Conventions: one-sided α = 0.05 (z = 1.6449), 80% power (z = 0.8416), sum 2.4865. All figures are independent-observation approximations; the dependence-aware requirement is larger by the design effect, which §6's power report must publish per endpoint.

| Requirement | H-SYS-1 (δ = 0.05R, σ = 1.8R) | H-BUY-P (δ = 0.10 ATR, σ = 2.6 ATR) |
|---|---|---|
| vs-zero test at μ = +0.17R | ≈693 trades | — (no planning μ declared in v0.2) |
| Strict confirmation L ≥ δ at μ = +0.17R | **≈1,392 trades** | — |
| Interval half-width = δ | ≈3,506 trades | ≈1,829 events |
| Strict confirmation at true effect 2δ | **≈8,013 trades** | **≈4,179 events** |

**Feasibility reading (arithmetic only).** At the DEV realized accrual of ≈7.5 closed trades/month, ≈1,392 independent H-SYS trades correspond to ≈15 years of single-universe forward collection; even the ≈693 vs-zero figure is ≈7–8 years. Dependence (design effect > 1) lengthens both. The binding constraint on confirmatory H-SYS power is therefore **accrual time**, not measurement. The predeclared consequences, already in the draft (§6): tests below the requirement are labelled **UNDERPOWERED FOR PASS** (they can still FAIL or be INCONCLUSIVE), and the expand-vs-accept decision (add Tier 3 symbols, widen the universe, or accept the label) is the user's freeze decision (checklist B4) — it is **not** taken here.

## 4. Measurement readiness

| Layer | State | Evidence |
|---|---|---|
| P1 all-bar MTM + session-table binning | PASS (bounded) | -29 `c103540`; -29r `70ef367` |
| P2 rank semantics · P3 benchmark as-of | PASS (bounded) | -30 `d077532` |
| P4 simulator docstring fidelity | PASS | -29 `d06dfe3` |
| P6 full-grid exposure | PASS | -31 `848f75d` |
| P7 all-fire journal | PASS | -29 `539e0a9` |
| P8 telemetry (transactional append; availability split) | PASS (bounded; no launch implied) | -29 `fa2f474`; -29r `70ef367`; -30 `d077532` |
| P9 parity incl. per-view ledgers (R19) | PASS | -29 `2cf06fc`; -30 `d077532` |
| P5 cost convention | Specified (draft §8); config-hash evidence due at freeze | v0.2 §8; draft §3 P5 |
| P10 data-rights/session/adjustment audit | **OPEN** (freeze-path) | Checklist C2 |
| P11 immutable version pins | **OPEN** (freeze-path) | Checklist C3 |

Closure of the measurement package is recorded in Issue #1 comment `6400814802`: measurement readiness only — not edge validation, not a freeze, not run authority.

## 5. Calendar coverage

| Table | Sessions | Range | Pin |
|---|---|---|---|
| Adopted calendar of record | 751 | 2023-10-19 → 2026-10-16 | sha `00c5555c…` |
| Extension (versioned) | 303 | 2026-10-19 → 2027-12-31 | sha `d2fa788d…` |
| Union (loader) | 1,054 | 2023-10-19 → 2027-12-31 | -30 commit `d077532` |

Coverage is sufficient for the DEV window, the holdout window (metadata purposes), and forward collection through 2027. Dates past 2027-12-31 fail closed by design; a further extension is a new versioned artifact when needed.

## 6. Matched-control (H-BUY) pool-size check — runnability

**Verdict as delivered (2026-10-25): RUNNABLE from committed metadata, without computing forward returns and without changing rules.** The check v0.2 §5 specifies (pool sizes only, per event, under B-A rules 1–5) needs, per event: symbol, time-of-day (session bin), ATR%, signal-bar exclusion windows, and the session calendar. All are present in committed artifacts:

| Input | Committed field / artifact |
|---|---|
| Event identity + timing | `allfire_journal.json`: `symbol`, `signal_idx`, `signal_time` (2,892 records) |
| ATR for the ±25% band | `atr` per fire (journal); ledger ATR fields |
| Signal-bar exclusion (no signal within 20 bars) | journal is the complete fire census — exclusion windows are computable from it |
| Session distance (within 30 sessions) | adopted session table (751; sha `00c5555c…`) + extension |
| Entry/stop reference (context fields) | `signal_close`, `stop0`, `entry_next_open`, `tp1_level` per fire |

The check was **not executed** in this deliverable (documentation-only bounds); it runs as part of the freeze procedure (draft §5/§15), where its outcome-blind outputs — pool sizes, dropped-event count, and the event-mix composition summary at the frozen relaxation step — are recorded. No blocker to runnability was found. The relaxation ladder, if reached, is the fixed predeclared one in §5 (a)–(c); reaching a step is recorded and frozen for every tier.

> **AMENDMENT A1 `[C26]` — §6 verdict CORRECTED (2026-10-25, after delivery).** The verdict above is **withdrawn as stated**. The cited committed metadata cannot run the B-A pool-size check: `allfire_journal.json` carries rows **only where the BUY signal fired** (with ATR at those rows); it cannot enumerate non-signal same-symbol bars or supply their ATR%, and it carries no per-bar Close/EMA21/EMA55/EMA200 for the B-T diagnostic. The claim "All are present in committed artifacts" is wrong for every non-fire bar. Corrected verdict: **the pool-size check was BLOCKED/UNPROVEN on the committed metadata as cited** (ChatGPT independent review, Issue #1 comment `6401471382`, HOLD 1; Claude Final-Gate Review, relayed in comment `6405097569`, item M1). **Closure:** the missing prerequisite — an outcome-blind every-observed-bar inventory (P7b: every DEV bar with Close, ATR, ATR%, EMA21/EMA55/EMA200 and the frozen signal flag, reconciled to the 2,892-fire census) — has been built from the existing committed DEV capture bytes and hash-pinned, and the pool-count check has been executed outcome-blind against it under the pinned EXP-14 script, in the companion preparatory package `research_notes/equity43_dev_buy_prep_m1m2_20261025/`. The correction changes no rule, threshold, or design element; it corrects the evidence basis for runnability and records that the check is now executed, not merely runnable.

## 7. Missing prerequisites (complete list)

1. §9 contamination audit — not run (outcome is a joint user+Muse decision; checklist B1).
2. §11 contract adoption, horizon, feasibility and stage-design decisions (checklist B2–B6).
3. P10 audit record and P11 freeze pins, incl. the numeric bootstrap seed (checklist C2–C3).
4. §6 power report (variance-only) — not yet published (checklist C4).
5. Tier 3 list rule and generated list (checklist C5).
6. Independent review of this v0.3 package (checklist C1).

**Bottom line.** Measurement is ready; the calendar is ready; the pool-size feasibility check is runnable from committed metadata. Confirmatory power at the frozen planning constants is **not** reachable on any near-term forward accrual — that is an arithmetic fact about counts and rates, stated outcome-blind, and the decision it forces (expand the sample or accept UNDERPOWERED FOR PASS) belongs to the user at freeze.

> **Amendment A1 `[C26]` applies to the sentence above as well:** "runnable from committed metadata" is corrected per §6 A1 — the check required the P7b inventory first; it has since been executed outcome-blind under EXP-14 (companion package `research_notes/equity43_dev_buy_prep_m1m2_20261025/`). No other sentence in this bottom line changes.
