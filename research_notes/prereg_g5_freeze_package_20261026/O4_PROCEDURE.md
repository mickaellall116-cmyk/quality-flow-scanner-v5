# O4 — Variance-Only Estimation Procedure for the H-EXIT-1/3 Paired SDs

**Status: PREPARED, NOT EXECUTED.** This document assembles the
procedure that will supply the two missing §6 inputs — the paired
per-trade SDs for H-EXIT-1 (7A, E1−E0) and H-EXIT-3 (7A, E0−E3). It
computes nothing. Running it is a performance-adjacent computation on
DEV legs and is **blocked on Mike's direct GO**: the recorded gate
(closure addendum, 2026-10-26) states that computing the paired SDs
"is not authorized by anything in this record," and no reviewer's
request substitutes for that GO. Procedure review (ChatGPT,
independent) precedes the GO request; entry of the results into the
freeze record follows the run.

## 1. What is missing, exactly

`POWER_REPORT.md` §1/§4: for H-EXIT-1 and H-EXIT-3 the planning σ is
"paired SD — **not on record**." §6 `[C03]` requires, per endpoint,
"the paired SD for the 7A paired endpoints" estimated "from variance
only: pool forward returns and baseline returns without computing any
group difference, and have an analyst report just the SD and design
effect." Checklist row O4 words the estimate as: "Pooled
arm-difference variance on DEV, variance only, no group differences.
**Must close before any tier opens.**"

Frozen endpoint constants (already on record; not re-derived here):
δ = 0.10R per trade for both endpoints; Holm allocation over
{1, 3, 4} (worst-case α = 0.0167, z = 2.1280); validity floor 100
closed trades; gating cost 25 bps round trip under the §8 per-fill
convention.

## 2. Inputs (all frozen, all pinned; DEV only)

| Input | Pin / location |
|---|---|
| DEV signal events, §5 construction (de-clustered, 20-bar non-overlap, 215-bar warmup) on the DEV window | The EXP-14-lineage DEV event set of record: 311 de-clustered events (§5 status `[V07]`); cohort construction per §5 |
| Frozen simulator, post-erratum bytes | `pine_backtest.py` SHA-256 `262ec0340161e72893ca9c5edd9d1fe2cb046fd30004d727b3893d52bd4d3f2a` (erratum commit `d06dfe3`; `P11_PINS_V10.json`) |
| Frozen C1 experiment configuration | Canonical pin `87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706` (driver `run_study13.py`, -13 package; reproduced in `MECHANICAL_CHECKS.md`) |
| DEV evidence base / leg definitions | -13 package: `research_notes/equity43_dev_order_censor_20261023_13/`; ledger SHA-256 `267e794c284a409d7d9b6d8e1056c452976b59746062e9e6e18c5664b74c003b` (Tier 1 evidence base) |
| Arms | §7 table, unaltered: **E0** (control), **E1** (intrabar stop), **E3** (fixed exit at close of bar i+20); 0.05 ATR constants are declared modelling assumptions `[C15]` |
| Exclusion | §7 pre-entry gap exclusion `[C11]`: events whose next-bar entry open is already below the signal-bar stop threshold are excluded from **all** arms |

No holdout-window data, no forward data, no vendor data. If any step
appears to require any of those, the run aborts and reports (see §6).

## 3. Construction of the paired legs (described, not run)

For each retained DEV event, the frozen simulator's standalone-trade
path (7A: no ranking, sector cap, or position limit) is executed
under each of E0, E1, E3 from the same entry (next bar's open;
initial stop = signal-bar close − 1.5 × ATR(14); TP1 = fill +
2.0 × ATR(14) for E0/E1), producing one net-R value per arm per
event under the §8 per-fill cost convention at the 25 bps gating
cost. The pairing is by event: leg *i* is the triple
(R_E0,i, R_E1,i, R_E3,i) over the **common** retained set (an event
missing from any arm is dropped from all pairs and counted).

**Open review point (for the procedure review, not resolved here):**
the DEV record's Stage-1 views carry the flat per-trade convention;
the estimator above is stated on the §8 per-fill convention because
that is the quantity the tier tests gate on. The reviewer confirms
the leg cost basis (Stage-2 per-fill restatement of the DEV legs vs
Stage-1 views) before the GO is requested; the choice is recorded in
the run package either way. No SD is meaningful until this is pinned.

## 4. Estimator (the only statistics that may leave the run)

For each gating pair, differences are formed per leg:

- H-EXIT-1: d_i = R_E1,i − R_E0,i
- H-EXIT-3: d_i = R_E0,i − R_E3,i

Reported outputs, and **only** these:

1. n (paired legs per endpoint, after exclusions);
2. the pooled paired SD per endpoint,
   s = sqrt( Σ (d_i − d̄)² / (n − 1) );
3. the design effect per endpoint, computed per §6 (cluster variance
   ÷ independent-observation variance of the pooled differences,
   calendar-block construction of `[C10]`), with n_eff = n / DE.

**Variance-only discipline.** The mean d̄ enters only as the internal
centering constant of the variance. No mean difference, no arm mean,
no per-arm SD standing alone as a result, no interval, and no
verdict-shaped quantity is printed, stored, or transmitted by the
run; the run script asserts its output schema is exactly
{n, s, DE, n_eff} per endpoint plus the input pins and the exclusion
counts. (This mirrors the power report's binding method note:
"Variance only… no group difference was computed.")

## 5. Entry into the record (after an authorized run)

1. Run package committed (script, output JSON with the §4 schema,
   input-pin verification log) — DEV artifacts only.
2. ChatGPT independently replicates the two SDs from the same pins
   (blind replication, per the standing research workflow) before
   acceptance.
3. On acceptance: the SDs are entered into `POWER_REPORT.md` §4's
   empty cells and the endpoint power rows recomputed **from the
   frozen formulas only**; checklist rows O4 and B9 close; the entry
   is logged as a freeze-record completion, not an amendment (the
   procedure and the slots were frozen in advance).

## 6. Stop conditions

Abort and report, computing nothing further, if: any input pin fails
to reproduce; the leg construction requires holdout or forward data;
the common paired set falls below the 100-trade floor (report n
only); or the output schema would need any statistic beyond §4.

## 7. Gate

- Procedure prepared: 2026-10-26 (this document).
- Procedure review: ChatGPT (pending).
- **Execution: BLOCKED ON MIKE'S DIRECT GO.** No part of §§3–4 has
  been executed in preparing this document; the only quantities
  cited are counts and constants already on record.
