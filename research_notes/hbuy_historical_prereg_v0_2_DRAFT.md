# PREREGISTRATION — Historical H-BUY Event Study (v0.2 DRAFT)

Status: DRAFT v0.2, 2026-11-03 — revised once per Claude's adversarial review
of v0.1 (2026-11-03; 4 blocking + 4 non-blocking items, all resolved below and
marked [R#]). Ready to freeze on reviewer confirmation; freeze executes after
the §5 parity gate passes. NOT adopted. No data has been captured under this
preregistration. Freeze = adoption record + script hash + universe hash
pinned in §11 in the order §11 declares, before the first capture byte arrives.
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
[R1] VOLUME IS A SIGNAL INPUT: all three components require
volume_ok = Volume > SMA20(Volume) (pine_backtest.py, pinned engine). Volume
therefore gates parity through the signal-level test in §5.
[R4] ADJUSTMENT STATE: bars on BOTH routes are raw — split- and
dividend-UNADJUSTED (the Stage A basis; Alpaca adjustment=raw). The REQ-S2
split-exclusion transform is NOT applied (S2 was retired as a basis
requirement 2026-10-21). A split inside an event's forward window distorts
that event's raw-bar return; this is the frozen basis, inherited deliberately
and disclosed here rather than corrected into a new one. The parity gate
compares raw-to-raw (§5).

## 3. Universe
Point-in-time: names listed at the window-start date per Databento point-in-time
instrument definitions, delisted names included; common stocks passing the
frozen Tier-3 eligibility screens (TIER3_RULE_FROZEN.md); mechanical slice to
~300 names drawn with the fixed literal seed declared here, before the list
exists: **UNIVERSE_SLICE_SEED = 20261103** [R2]. This seed depends on nothing
in this document's hash; the document hash seeds only the bootstrap (§7).
[R3] IDENTITY: names are keyed throughout by Databento instrument_id, not
symbol; symbols are display labels only. Delisted tickers are reused by later
issuers, so every name is the (instrument_id, listing-window) pair from the
point-in-time definitions.
Exclusions (feasibility receipt 2026-11-03 §4.1): the 54 unique studied symbols
(DEV 43 ∪ Tier-3 11; the Tier-2 19 are a subset of DEV 43), plus SMCI as an
excluded-adjacent 55th (census/pilot-touched). SPY is in the DEV 43: excluded
as a study symbol, captured separately (§5). The frozen universe list and its
SHA-256 are pinned in the freeze record before capture (§11 order).

## 4. Window
708 NYSE sessions ending on the last completed session before the capture date.
Sessions 1–108: warmup segment (bars captured so the 215-bar indicator warmup
completes; no events counted). Sessions 109–708: evaluation span = 600 sessions
= 30 non-overlapping 20-session blocks, numbered in order. Events are counted
only in the generator domain (post-warmup, full forward window inside data).
[R5] OVERLAP DISCLOSURE: this window overlaps market days used by the DEV
studies and the Tier-3 sealed window. The study names are new (none of the 55
excluded names is present), but the signal itself was selected with knowledge
of those market days. Events whose sessions fall inside the DEV evaluation
window or the Tier-3 sealed window (2023-10-19 → 2024-09-13) are reported as
a separate stratum beside the rest in Outputs 1 and 2.

## 5. Data route and parity gate
Route: Databento EQUS.MINI ohlcv-1h (consolidated), resampled to the §2 grid.
SPY captured from the same route for the full window: session-calendar
alignment and market-context diagnostics (B-A matching itself is same-symbol,
§6). Capture is a single batch pull of the frozen universe + SPY.
PARITY GATE — hard precondition, redefined [R1]: before any study capture,
pull an overlap window (inside 2023-10-19 → 2024-09-13) for the four
already-consumed Tier-3 names with archived reference bars (AAOI, BE, MPWR,
CRDO — SPY was never in the Tier-3 capture and is not a parity name; the
v0.1 "≥5 names" wording is corrected here), derive 4H bars by the §2 path in
the same raw adjustment state (§2), and require, against the archived
Alpaca-derived bars (qf-data-archive commit db53e24, reference file archived
2026-11-03 at 4aeab9c):
  (a) exact bar count and exact timestamps;
  (b) OHLC agreement within one tick ($0.01) on every bar;
  (c) SIGNAL-LEVEL PARITY: the pinned pine_buy_signal fires on the identical
      bar set in both derivations.
Volume differences are reported per bar in the parity receipt but are not
gated directly; because volume is a signal input (§2), any volume difference
large enough to matter fails (c) by construction. The parity receipt is
published before the study capture counts as valid. Failure of (a), (b), or
(c) = STOP: no study run until the pipeline discrepancy is resolved and
parity passes.

## 6. Events and matching (frozen §5, step-(c) configuration)
Events: every signal bar in the evaluation span; de-clustered — keep fire i iff
no fire in [i−20, i−1]. Complete-window cohort: an event enters all horizons
only if its full 20-bar forward window lies inside the data (i+20 ≤ n−1);
dropped counts reported. Raw fires / de-clustered / matched-retained counts
are all reported (no silent stage).
[R3] DELISTING ACCOUNTING: events dropped for incomplete forward windows are
reported in two separate counts — (i) names that delisted inside the window
(by instrument_id), (ii) all other causes (window-edge truncation). The
verdict text (§7) states the bias this construction creates.
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
fc17041); per-event sub-seeds per the corr2 construction. (The document hash
seeds ONLY this bootstrap [R2]; the universe was drawn under §3's literal
seed, which precedes the document hash.)
Floors (pre-committed; no post-hoc change): ≥200 de-clustered events,
≥20 symbols in the test, ≥30 blocks. [R6] "Symbols in the test" means symbols
with at least one matched-retained event. Any floor missed ⇒
INCONCLUSIVE-by-floor, stated as such, regardless of the estimate.
PASS: all floors met AND θ̂ ≥ δ (0.10 ATR) AND interval lower bound L > 0;
grade CONFIRMED AT δ if L ≥ δ, else PASS — economics-first. U < δ ⇒ FAIL
(EXCLUDED). UNDERPOWERED FOR PASS label assessed against CONFIRMED AT δ and
printed with the verdict (§6).
[R3] BIAS STATEMENT (printed with the verdict): the complete-window cohort
excludes events truncated by delisting, which removes disproportionately
negative outcomes; the matched estimate is therefore biased UPWARD by this
construction. The delisting-drop count (§6) is printed beside the verdict
so the size of the excluded tail is visible with the number it affects.

## 8. Outputs (exactly four)
1. Event census: raw fires / de-clustered / complete-window / matched-retained,
   with drop counts (split per §6 [R3]) and the matching drop rate; the
   DEV/Tier-3-overlap stratum (§4 [R5]) reported beside the rest.
2. Paired excess at h=10 with the verdict interval (plus h=5/h=20 per §1),
   n, design effect, n_eff — overall and for the overlap stratum.
3. Concentration: top-5 share of total excess; per-symbol excess table.
4. Sorted event list (per event: symbol, session, bin, ATR excess and percent
   excess at h=5/10/20, matched/dropped status) + leave-one-symbol-out and
   leave-one-session-out tables.
[R7] Every output table prints the verdict grade line (CONFIRMED AT δ /
PASS / FAIL (EXCLUDED) / INCONCLUSIVE-by-floor) — not only the verdict text.

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
- Symbol-floor reading: [R6] the ≥20-symbol floor counts symbols with at
  least one matched-retained event (§7); no universe-level reading.

## 11. Execution discipline
One capture (after the parity gate passes), one run script, one run. No rule
changes, no variants, no parameter edits after freeze; a second run under
this version is prohibited — any defect found post-run is reported, and a
corrected study requires a new preregistration version on untouched evidence.
[R8] FREEZE ORDER (binding, resolves the seed circularity): (1) the run
script is finalized; (2) the universe list is generated under §3's literal
seed; (3) the script SHA-256 and universe-list SHA-256 are computed; (4)
both hashes are inserted here — script <PIN AT FREEZE>, universe <PIN AT
FREEZE>; (5) only then is this document hashed, and that frozen hash is the
protocol-seed source (§7). No hash is ever inserted after step (5).
