# Sealed Tier-3 Stage A — Run Report (2026-11-03)

**Authorization:** Mike, direct chat, 2026-11-03 12:43 ET ("Run the sealed
Tier-3 test"). Launch record: `research_notes/tier3_stagea_launch_20261103.md`
(commit `295385e`).
**Scope executed:** Stage A paired legs (7A + H-BUY family) on **Tier 3
only** (11 symbols: BE, ACN, IREN, CRDO, TWLO, AAOI, MPWR, SPOT, BABA,
COF, BLK), sealed window 2023-10-19 → 2024-09-15 (227 sessions), from the
archived Alpaca capture only. Frozen preregistration v1.0 as amended
(v1.0.1/v1.0.2), G5-adopted 2026-10-27. **One run, zero variants, zero
parameter changes, zero retries.** Full extracted spec with citations:
stage dir `RUN_SPEC_EXTRACTED.md`.

## Verdicts (frozen B2 gates, applied mechanically)

| Leg | n | θ̂ | 90% interval | Verdict |
|---|---|---|---|---|
| H-BUY-P (h=10, vs B-A baseline) | 20 retained (cohort 27) | **+1.1188 ATR** | [+0.017, +2.250] (cluster, wider) | **INCONCLUSIVE-by-floor** (cohort 27 < 200 de-clustered events) |
| H-BUY-S5 (h=5) | 20 | +0.6496 ATR | [−0.202, +1.651] | DESCRIPTIVE — fixed sequence stopped at P; same floor applies |
| H-BUY-S20 (h=20) | 20 | +1.1511 ATR | [−0.532, +2.705] (block, wider) | DESCRIPTIVE — fixed sequence stopped at P; same floor applies |
| H-EXIT-1 (E1−E0) | 25 paired | **−0.0401 R** | Holm [−0.343, +0.256] | **INCONCLUSIVE-by-floor** (paired n=25 < 100) |
| H-EXIT-3 (E0−E3) | 25 paired | **−0.3988 R** | Holm [−1.095, +0.280] | **INCONCLUSIVE-by-floor** (paired n=25 < 100) |
| R-EXIT-2 (E2−E0) | 25 paired | **0.0000 R** | [0.000, 0.000] | Robustness only — **no FILL-OPTIMISM flag** (E2 ≡ E0 on all 25 pairs) |
| H-SYS-1 (7C) | — | — | — | **INCONCLUSIVE-by-floor** (pre-declared; 7C not executed — see gaps) |
| H-EXIT-4 (7C) | — | — | — | **INCONCLUSIVE-by-floor** (pre-declared; 7C not executed — see gaps) |

**No leg PASSes and no leg FAILs. Every verdict-bearing leg is
INCONCLUSIVE, and every one of them is decided by the frozen count
floors, not by the estimates.** The estimates are on the record below;
under the frozen contract they carry no PASS/FAIL weight.

Notes on shape (descriptive only): H-BUY-P's point estimate is large and
its interval excludes zero — but the floor exists for exactly this
situation (27 events cannot certify a 0.10-ATR claim; the realized
half-width is 1.12 ATR, 11× δ, so the CONFIRMED grade would be
unreachable regardless). H-EXIT-3's estimate is negative (the fixed
20-bar hold beat the managed exit in this window) but its interval
includes zero and extends above δ, so it is not an EXCLUDED/FAIL shape
either. H-EXIT-1's interval straddles zero symmetrically
(INDETERMINATE shape under the floor).

## Headline numbers

**Event census (Tier 3, 4H grid = 452 bars/symbol):** 190 all-fire
signals across 11 symbols → **28 de-clustered events** (20-bar rule) →
**27 cohort events** (1 dropped by the [C2] window rule). Pre-entry gap
exclusions [C11]: 0. H-BUY matching at frozen ladder step (c): 7 events
dropped (eligible pool < 6), **20 retained**.

**7A standalone arms** (per-fill cost model; gating view 12.5 bps/fill =
25 bps round trip):

| Arm | n closed | Mean R @25 | Mean R @10 RT (5.0/fill) | Mean R @4 RT (2.0/fill) | PF @25 | Win @25 |
|---|---|---|---|---|---|---|
| E0 (frozen system) | 25 | **+0.2609** | +0.3046 | +0.3221 | 1.396 | 48.0% |
| E1 (intrabar stop) | 26 | +0.2610 | +0.3038 | +0.3209 | 1.434 | 42.3% |
| E2 (TP1 exceedance) | 25 | +0.2609 | +0.3046 | +0.3221 | 1.396 | 48.0% |
| E3 (fixed 20-bar) | 27 | +0.8491 | +0.8945 | +0.9127 | 2.151 | 55.6% |

Censoring: E0 open at boundary 2, E1 open 1, E3 none (window rule).
E2's fills are identical to E0's on every event — the 0.05·ATR TP1
exceedance margin never changed an outcome in this window (θ̂ = 0.0000
at all three cost views is an empirical identity, not an error;
verified pair-by-pair in the ledger).

**H-BUY descriptive lines:** mean percent excess at h=10 (retained
events) = +1.982% gross, **+1.732%** after the frozen 25 bps
paired-comparison charge. B-T trend-conditioned baseline (diagnostic
only, n=5 events with adequate pools): h=5 −0.183 ATR, h=10 +1.305 ATR,
h=20 +2.679 ATR.

**7B descriptive (standalone sequential candidates, gating view):**
42 candidates; arm means E0 +0.1458 R (n=38), E1 −0.0231 R (n=41),
E2 +0.1458 R (n=38), E3 +0.4308 R (n=38); paired means E1−E0 −0.1439 R
(n=38), E0−E3 −0.0393 R (n=36), E2−E0 0.0000 R (n=38). No inference, no
verdicts — reported per §3.

**Dependence (frozen inference layer):** design effects — H-EXIT-1
0.589 (n_eff 42.5), H-EXIT-3 1.155 (n_eff 21.6), H-BUY-P 0.522 (n_eff
38.3). DE < 1 on two endpoints is a small-n artifact of the variance
ratio; every verdict interval took the **wider** of the block/cluster
intervals per [C10], which was the cluster interval in most cases.
Cost sensitivity: H-EXIT-1 and H-EXIT-3 θ̂ are essentially
cost-invariant across 4/10/25 bps round-trip views (−0.040 and −0.399
resp. at all views) — the §12 COST-SENSITIVE flag does not apply
(estimates are ≤ 0 at *every* view, not only at 25).

**Winner concentration (§12, on the 7A E0 trade set, gating view):**
net +6.522 R over 25 closed trades; top-5 winners sum to +18.885 R =
**289.6% of net**; top-10 = 349.3% of net. Outside the top 5, the
remaining 20 trades net **−12.36 R**. The set's profit is entirely
top-heavy — stated plainly, per the standing reporting rule.

## Input verification & derivation parity (Steps 2–3, all passed pre-run)

- Fresh clone of qf-data-archive at `db53e24554e6e5439bb937e77820f61b6f726c7e`;
  `sha256sum -c` inside `captures/alpaca_tier3_v1/`: **109/109 OK**.
  No other market-data source used; no network market-data calls.
- Session table pin verified twice (capture package + prereg bundle):
  SHA-256 `00c5555c…` both.
- Per symbol (×11): canonical merged-payload hash recomputed from the
  archived pages **reproduces the capture receipt's `raw_sha256` 11/11**;
  grid partition = exactly 2,939 bars, 0 duplicates, 0 missing; off-grid
  counts match the receipt exactly; derived 09:30-anchored 1H bars =
  **1,583/symbol** with stamps equal to the pinned table's hourly set.
- DST bar-level checks: 2023-11-03 (UTC−4) → 2023-11-06 (UTC−5) and
  2024-03-08 (UTC−5) → 2024-03-11 (UTC−4): 7 derived bars/session at
  09:30…15:30 ET, offsets shift correctly, final 15:30 bar is the
  single-bucket fold. In-run 4H resample (pinned `scanner_rules`)
  reproduced the pinned grid per session: **452 bars/symbol**
  ([09:30, 13:30]; [09:30] on the two 13:00 early closes).
- Engine pins verified in the stage dir before execution:
  `pine_backtest.py` `262ec034…`, `scanner_rules.py` `62aa743a…`,
  P5 per-fill config `7690de07…`, seed 2999475941474119668, circular
  block bootstrap (20-session blocks, 10,000 reps, PCG64), Holm over
  the H-EXIT family {1:[α=.0167], 3:[α=.025], 4:[p=1]}.
- Post-run independent spot-checks (fresh code, not the runner's):
  one H-BUY event's pool size (25), drawn set, and h=10 excess
  (2.8023580337) and one event's E3 net R (5.0058366233) reproduce the
  ledgers to 10 decimal places; E0 net R summed from the ledger
  (6.521908) matches `results.json`.

## Deviations & gaps (stated plainly)

1. **§5 matching is a stage-local implementation** of the frozen §5
   text using the corr2-pinned semantics (the pinned EXP-14 matching
   code is DEV-bound by construction; corr5 parity was a DEV-window
   statement). Code deviation, not rule deviation: constructions,
   ladder step (c), sub-seed derivation, and draw mechanics follow the
   pinned semantics exactly.
2. **Cost model conversion:** Stage-1 pins record a flat per-trade
   cost; §8 + the P5 closeout pin the per-fill formula, and the frozen
   views were converted (2.0 / 5.0 / 12.5 bps per fill = 4 / 10 / 25
   bps round trip, shares = 1). The literal alternative reading of the
   amendment's per-leg wording is internally inconsistent (it implies
   50 bps round trip under its own 0.995⁴ parenthetical) and was
   rejected on the record in the extracted spec. If ChatGPT adjudicates
   otherwise, the ledgers carry per-view R for every arm, so endpoints
   can be restated without re-running the engine.
3. **E1 same-bar order:** stop-check before TP1-touch within a bar
   (conservative, stop-first), following the fidelity-proven O4
   construction; §4's tag order lists [TP1] before [STOP]. Disclosed;
   affects fills only on bars where both trigger.
4. **7C (H-SYS-1, H-EXIT-4) not executed:** pre-declared
   INCONCLUSIVE-by-floor, *and* not executable as frozen on
   archive-only inputs — the capture contains no SPY bars (C1 ranking
   impossible) and the frozen sector map covers none of the 11 Tier-3
   names (its own completeness check fails). No substitute ranking or
   sector map was invented.
5. **Tier 2 legs not in this run:** the 19 supplementary symbols were
   never captured on the Alpaca route; by the §9 PARTLY branch they
   carry no PASS/FAIL standing in any case.
6. **Floors — two readings disclosed:** the H-BUY 200-event floor was
   applied to the window-complete cohort (27); the raw de-clustered
   count is 28 — the floor fails under either reading. The §6 "≥ 30
   independent blocks" floor: the window spans 227 sessions = 12
   non-overlapping 20-session blocks (mean blocks drawn per bootstrap
   rep ≈ 5.3–5.4) — under any reading the count is < 30; no verdict
   turns on it because the event/trade floors fail first. The
   ≥ 20-symbol floor is met at the Stage A universe level (30) under
   the launch record's reading; Tier-3 computations themselves use 11
   symbols (textual tension disclosed in the extracted spec).
7. **O6 pool counts** (a Text 1 effectiveness condition) were never
   produced before this run — Text 0 staging stopped 2026-10-27 with
   the disclosure on the record. Matching was therefore computed
   in-session per the runbook. Mike's authorization for this run was
   given directly, not as a Text 1 signature.
8. **P8 telemetry journal** is not among this run's deliverables; the
   §12 reporting set is covered by this report plus the stage
   artifacts.
9. **§13 register note (for the freeze record):** Tier 3 on the sealed
   holdout window is **CONSUMED** for rule version v1.0 (evaluated
   2026-11-03, this run). Tier 2 was **not** evaluated under the
   Alpaca route (no capture exists); its supplementary status is
   unchanged.

## Artifacts (stage dir `~/workspace/tier3_stagea_run/`)

- `RUN_SPEC_EXTRACTED.md` — frozen spec extraction with citations
- `parity_report.json`, `derive_and_parity.py` — Step 3 evidence
- `results.json` — all endpoint statistics, intervals, sensitivities,
  diagnostics
- `ledger_7a.json` (27 events, per-arm R at 3 cost views),
  `ledger_hbuy.json` (per-event pools/draws/excess), `ledger_7b.json`
- `stage_run.py`, `engine/` (pinned engine copies, hash-verified),
  `derived_1h.json`, `archive_clone/` (qf-data-archive @ db53e24)

Independent replication (Claude) and adversarial review (ChatGPT) of
this run remain the next steps in the standing workflow; this report
is the executing lane's record, posted to the bridge only — no Slack
post was made by this lane.
