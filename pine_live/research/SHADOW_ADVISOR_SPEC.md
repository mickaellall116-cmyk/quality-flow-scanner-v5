# Shadow Hold/Sell Advisor — Pre-registered Specification (v1)

**Status:** FROZEN for the paper phase. This document is the complete,
deterministic definition of the shadow advisor. There is no ML, no
discretion, no tuning loop, and no path by which this advisor can affect
a paper position, fill, runner decision, gate threshold, or alert.

**Purpose (observation only):** classify each open paper position once per
research run as HOLD / PROTECT / WEAKENING / EXIT-CANDIDATE, log the
classification with its rule inputs, and — after canonical close —
compute the HYPOTHETICAL R of acting on the first EXIT-CANDIDATE bar.
The research question is: *would the guidance have improved realized R
versus canonical exits, without clipping the tail winners that carry
expectancy?*

**What this advisor is NOT:** it is not a strategy change, not an exit
rule, not a filter, and not a recommendation to Mike. Its output is log
data for later analysis. V3.6 entries/exits remain frozen regardless of
what the shadow log says.

---

## 1. Inputs (per open position, per run)

`compute_inputs(position, bars)` where `bars` is the ascending 4H OHLC
series with `t > entry_time` (bars observable since entry; read-only
download, never paper state):

| field | definition |
|---|---|
| `r_now` | `(last_close - entry_px) / (entry_px - stop_px)` — current R multiple |
| `dist_to_stop_frac` | `(last_close - stop_px) / (entry_px - stop_px)` — 1.0 at entry, 0.0 at stop |
| `mae_r` | `min(0, min over bars of (close - entry_px) / risk)` — worst adverse excursion in R |
| `mfe_r` | `max(0, max over bars of (close - entry_px) / risk)` — best favorable excursion in R |
| `bars_held` | number of bars in the series (4H bars since entry) |
| `bar_time` | ISO time of the last bar (the bar the classification is *about*) |

If `bars` is missing/empty, position fields are missing/non-finite, or
`entry_px <= stop_px`, inputs are `None` and the run logs the sentinel
label `INSUFFICIENT_DATA` (not one of the four classifications).

## 2. Classification rules (evaluated in fixed precedence order)

Precedence: **EXIT-CANDIDATE > PROTECT > WEAKENING > HOLD**.
The first matching rule fires; its rule id is logged alongside the label.
Identical inputs always produce the identical (label, rule) — the
function is pure and deterministic.

### EXIT-CANDIDATE
- **EC1** — `r_now <= -0.75` — three-quarters of the way to the stop.
- **EC2** — `bars_held >= 60` and `r_now < 0.25` — stale loser: ten trading
  days held without reaching a quarter-R of profit.
- **EC3** — `mae_r <= -0.90` and `r_now < 0.0` — near-death bounce: almost
  stopped, recovered only weakly.

### PROTECT
- **P1** — `r_now >= 1.50` — strong winner; a protect mindset is warranted.
- **P2** — `mfe_r >= 2.00` and `(mfe_r - r_now) >= 1.00` — gave back ≥1R
  from a ≥2R peak.

### WEAKENING
- **W1** — `bars_held >= 20` and `r_now < 0.25` — drifting: five trading
  days without traction.
- **W2** — `mae_r <= -0.50` and `r_now < 0.50` — deep adverse excursion
  with only partial recovery.

### HOLD
- Fires when no rule above matches (rule id `None`).

## 3. Logging

Append-only `pine_live/research/shadow_log.jsonl`. One record per
`(signal_id, bar_time)`; re-runs never duplicate. Record:

```
{ts, bar_time, signal_id, symbol, label, rule_id,
 inputs: {r_now, dist_to_stop_frac, mae_r, mfe_r, bars_held}}
```

`INSUFFICIENT_DATA` records carry `label="INSUFFICIENT_DATA"`,
`rule_id=null`, `inputs=null`, deduplicated per `(signal_id, run_date)`.

## 4. Counterfactual accounting (HYPOTHETICAL only)

When a paper position closes on the canonical path:

1. Find the earliest `shadow_log.jsonl` record for its `signal_id` with
   `label == "EXIT-CANDIDATE"` and `bar_time < exit_time`.
   - None found → log `status="no_candidate"`, all hypothetical fields null.
2. Take the first 4H bar with `t > candidate_bar_time` (read-only
   download); its **open** is the hypothetical fill.
   - No later bar, bar time beyond `exit_time`, or non-finite prices →
     `status="insufficient_data"`, nulls. Never infer.
3. **Hypothetical exit = full position at that next-bar open.**
   (Simplification, documented: the canonical path blends 50/50 with the
   TP1 leg; the counterfactual prices a clean full exit. It measures
   "what if we had just sold," nothing more.)
4. `hypothetical_net_r` at 4bps and 25bps via `pine_backtest._outcome`
   (same R definition as canonical). Deltas:
   `delta_r = hypothetical_net_r - actual_canonical_net_r`
   (positive = the guidance would have *added* R).

Every number in this section is labeled **HYPOTHETICAL** in code, logs,
and any future report. There is no order path in this namespace and
there never will be.

## 5. Evaluation: pre-registered PASS/FAIL standard (IN POTENTIA)

The evaluation below is fully pre-registered now but runs only once a
sufficient sample exists. Until then both studies accumulate data and
report `INSUFFICIENT_SAMPLE` — never a verdict. Implementation:
`pine_live/research/evaluate.py`.

**Sample floor:** `MIN_EVAL_TRADES = 30` closed, evaluable paper trades
(a trade is evaluable when its counterfactual record carries finite
actual and hypothetical net R on the 25bps leg). Below 30 →
`INSUFFICIENT_SAMPLE`, no criteria applied.

The shadow advisor **PASSES** only if ALL of the following hold:

- **(a) Mean hypothetical R improves:** mean `hypothetical_net_r_25bps`
  per evaluable trade is strictly greater than mean
  `actual_net_r_25bps` (canonical realized, 25bps leg).
- **(b) Top-decile capture is not materially degraded:** let the top
  decile be the top 10% of evaluable closed trades by actual canonical
  net R (25bps leg). *Capture* of a set of trades = the fraction the
  advisor's guidance would have kept through at least the canonical exit
  (hypothetically) — i.e. the fraction with NO `EXIT-CANDIDATE`
  classification at a `bar_time` earlier than the trade's `exit_time`.
  Canonical capture is 1.0 by construction (every closed trade was kept
  through its own canonical exit). Require:
  `hypothetical_top_decile_capture >= 1.0 - TOLERANCE_TOP_DECILE_DEGRADATION`,
  with `TOLERANCE_TOP_DECILE_DEGRADATION = 0.10` (no more than 10 points
  of capture lost). The advisor fails its purpose if it adds small-R
  efficiency while clipping the monster winners that carry expectancy.
- **(c) No populated regime degrades:** for every regime bucket with
  `>= 10` closed evaluable trades (`REGIME_MIN_TRADES = 10`), require
  mean(`hypothetical_net_r_25bps` − `actual_net_r_25bps`) within the
  regime to be `>= -REGIME_UNDERPERF_TOL_R`, with
  `REGIME_UNDERPERF_TOL_R = 0.10`. Regimes below 10 trades are skipped
  (reported as insufficient sample, not as passes); if no regime
  qualifies, (c) passes vacuously with that noted.

**"Average hypothetical R improved" alone is NOT a pass.** A positive
(a) with a failing (b) is a FAIL — efficiency gains that clip tail
winners are exactly the failure mode this standard exists to catch.

To make (b) joinable later, every `counterfactual.jsonl` record carries
`signal_id`, `actual_net_r_4bps/25bps`, `hypothetical_net_r_4bps/25bps`,
`exit_candidate_before_exit` (bool), and `regime` (nullable until regime
tagging exists).

## 6. ANTI-TUNING RULE

The advisor's classification rules (§2, constants in `shadow.py`) and
the delay-study bucket definitions (`DELAY_STUDY_SPEC.md`, constants in
`delay.py`) are **frozen at pre-registration**. No tuning the advisor
from early outcomes. No redefining buckets to make results look better.
Any change to either requires the full change-control bar: a documented
failure mode, a pre-registered test, and out-of-sample validation —
before anything downstream may use it.

No finding from this namespace is ever promoted into production (paper
or real) without going through that process. This namespace is read-only
with respect to production by design — it cannot place orders, send
alerts, or mutate `pine_live/paper_state/` — and that must stay true.

## 7. Change control

These rules are frozen for the paper phase. Any change requires a spec
edit with a new version header and rationale — it never alters paper
behavior, because nothing in this namespace can.
