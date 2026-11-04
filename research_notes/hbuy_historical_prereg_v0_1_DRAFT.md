# PREREGISTRATION — Historical H-BUY Event Study (v0.1 DRAFT)

Status: DRAFT v0.1, 2026-11-03 — for ChatGPT/Claude adversarial review. NOT adopted.
No data has been captured under this preregistration. Freeze = adoption record +
script hash + universe hash pinned in §11, before the first capture byte arrives.
Inherits PREREG_V10 (frozen 2026-10-26) §5/§6/§8/§11 for H-BUY; nothing below
redesigns the endpoint, matching, de-clustering, bootstrap, or verdict contract.

## 1. Question and primary endpoint
Does the frozen Quality Flow BUY signal predict forward returns beyond a matched
non-signal baseline, on a large untouched historical universe?
Primary: H-BUY-P — mean paired excess of ATR-normalized forward return at h=10,
signal minus B-A baseline (PREREG_V10 §5), δ = 0.10 ATR, one-sided α = 0.05.
Secondaries H-BUY-S5, H-BUY-S20 (same construction, h=5 / h=20), inferential
only if H-BUY-P passes (fixed sequence 10 → 5 → 20); otherwise descriptive.
No exit, sizing, ranking, or system hypothesis is tested under this prereg.

## 2. Signal and bars (frozen)
Signal: pine_buy_signal, V3.6 hybrid (confirmedBuy OR breakoutBuy OR readyBuy),
on completed session-anchored 4H bars (09:30 / 13:30 ET; 09:30 only on 13:00
early-close sessions), produced by the pinned resample_closed_4h_session_anchored
(scanner_rules.py SHA-256 62aa743a…) — the same code path as the Stage A
derivation. Indicators per the pinned add_pine_indicators; 215-bar warmup.
Forward return at h: (Close[i+h] − Open[i+1]) / ATR(14)[i]; percent alongside.

## 3. Universe
Point-in-time: names listed at the window-start date per Databento point-in-time
instrument definitions, delisted names included; common stocks passing the
frozen Tier-3 eligibility screens (TIER3_RULE_FROZEN.md); seeded mechanical
slice to ~300 names (seed recorded in the freeze record).
Exclusions (feasibility receipt 2026-11-03 §4.1): the 54 unique studied symbols
(DEV 43 ∪ Tier-3 11; the Tier-2 19 are a subset of DEV 43), plus SMCI as an
excluded-adjacent 55th (census/pilot-touched). SPY is in the DEV 43: excluded
as a study symbol, captured separately (§5). The frozen universe list and its
SHA-256 are pinned in the freeze record before capture.

## 4. Window
708 NYSE sessions ending on the last completed session before the capture date.
Sessions 1–108: warmup segment (bars captured so the 215-bar indicator warmup
completes; no events counted). Sessions 109–708: evaluation span = 600 sessions
= 30 non-overlapping 20-session blocks, numbered in order. Events are counted
only in the generator domain (post-warmup, full forward window inside data).

## 5. Data route and parity gate
Route: Databento EQUS.MINI ohlcv-1h (consolidated), resampled to the §2 grid.
SPY captured from the same route for the full window: session-calendar
alignment and market-context diagnostics (B-A matching itself is same-symbol,
§6). Capture is a single batch pull of the frozen universe + SPY.
PARITY GATE — hard precondition: before any study capture, pull an overlap
window (inside 2023-10-19 → 2024-09-13) for ≥5 already-consumed Tier-3 names,
derive 4H bars by the §2 path, and require bar-for-bar OHLCV equality against
the archived Alpaca-derived bars (qf-data-archive commit db53e24). The parity
receipt is published before the study capture counts as valid. ANY mismatch =
STOP: no study run until the pipeline discrepancy is resolved and parity passes.

## 6. Events and matching (frozen §5, step-(c) configuration)
Events: every signal bar in the evaluation span; de-clustered — keep fire i iff
no fire in [i−20, i−1]. Complete-window cohort: an event enters all horizons
only if its full 20-bar forward window lies inside the data (i+20 ≤ n−1);
dropped counts reported. Raw fires / de-clustered / matched-retained counts
are all reported (no silent stage).
B-A pool per event: same symbol, same session bin (09:30/13:30), |session
ordinal − event ordinal| ≤ 45, no signal bar within ±20 bars, |atr_pct − event
atr_pct| ≤ 0.40 × event atr_pct. Event dropped (counted) if pool < 6; draw =
min(20, pool) bars without replacement. This is the frozen end state of the §5
relaxation ladder (walked to step (c) on DEV, frozen at v1.0): the ladder is
closed — no further relaxation is permitted in this study. Drop rate reported;
>15% carries the §5 flag and matched results are described as the matched
subpopulation. B-T diagnostic (trend-state pool) reported, non-gating.

## 7. Inference, floors, verdict (frozen §6/§11, B2 economics-first)
Inference: circular block bootstrap over calendar time, 20-session blocks,
10,000 reps; robustness: symbol-cluster bootstrap; verdict uses the wider
interval. Report n, blocks/rep, design effect, n_eff per endpoint. Protocol
seed = first 8 bytes BE of this preregistration's frozen SHA-256 (contract
fc17041); per-event sub-seeds per the corr2 construction.
Floors (pre-committed; no post-hoc change): ≥200 de-clustered events,
≥20 symbols in the test, ≥30 blocks. Any floor missed ⇒ INCONCLUSIVE-by-floor,
stated as such, regardless of the estimate.
PASS: all floors met AND θ̂ ≥ δ (0.10 ATR) AND interval lower bound L > 0;
grade CONFIRMED AT δ if L ≥ δ, else PASS — economics-first. U < δ ⇒ FAIL
(EXCLUDED). UNDERPOWERED FOR PASS label assessed against CONFIRMED AT δ and
printed with the verdict (§6).

## 8. Outputs (exactly four)
1. Event census: raw fires / de-clustered / complete-window / matched-retained,
   with drop counts and the matching drop rate.
2. Paired excess at h=10 with the verdict interval (plus h=5/h=20 per §1),
   n, design effect, n_eff.
3. Concentration: top-5 share of total excess; per-symbol excess table.
4. Sorted event list (per event: symbol, session, bin, ATR excess and percent
   excess at h=5/10/20, matched/dropped status) + leave-one-symbol-out and
   leave-one-session-out tables.

## 9. Costs
The paired ATR excess is cost-free by construction (§8: costs cancel in the
paired difference). Descriptive percent-excess lines are reported net of
4 / 10 / 25 bps round trip, the 25 bps line being the frozen §5/§8 descriptive
view. There are no fills in this study; the Stage A per-fill convention
(12.5 bps × fill price per fill) does not apply and is not imputed.

## 10. Stage A deviations — disposition, declared in advance
- Per-fill cost conversion: not applicable (no simulated trades; §9).
- E1 same-bar ordering: not applicable (no exits are simulated).
- SPY absent in Stage A: cured — SPY captured from bar one (§5).
- Sector map absent: not needed — H-BUY has no ranking/sector component;
  no system (H-SYS) claim is made under this prereg.
- §5 matching was stage-local code in Stage A (pinned EXP-14 code is
  DEV-bound): here the matching implementation is part of the single hashed
  run script (§11), pinned before the run.
- Symbol-floor reading: the test runs on the full ~300-name universe, so the
  §6 "≥20 symbols in every test" floor applies directly, no per-leg distinction.

## 11. Execution discipline
One capture (after the parity gate passes), one run script, one run. The run
script's SHA-256 and the frozen universe list's SHA-256 are pinned here at
freeze: script <PIN AT FREEZE>, universe <PIN AT FREEZE>. No rule changes, no
variants, no parameter edits after freeze; a second run under this version is
prohibited — any defect found post-run is reported, and a corrected study
requires a new preregistration version on untouched evidence.
