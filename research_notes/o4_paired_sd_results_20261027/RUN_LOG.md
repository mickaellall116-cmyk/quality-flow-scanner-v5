# O4 — H-EXIT paired-SD computation: run log

**Status: COMPLETE.** Executed once under Mike's direct authorization
(chat, 2026-10-27), exactly per the pinned procedure
`research_notes/prereg_g5_freeze_package_20261026/O4_PROCEDURE.md`
(G5 freeze package commit `5037311`, addendum `4988f15`) with the cost
basis of the addendum's `O4_BASIS_PIN.md`: Stage-1 FLAT views of the
frozen C1 config, 25 bps gating view. The §8 per-fill convention was
NOT used. DEV data only; **no holdout access** (the sealed
2023-10-19→2024-09-15 window was not opened, read, or computed on);
**no performance run** — a variance computation over artifacts already
on record, as the procedure defines.

## Outputs (the only statistics produced — procedure §4)

| endpoint | definition | n | s (paired SD, R) | DE | n_eff |
|---|---|---|---|---|---|
| H-EXIT-1 | d_i = R_E1,i − R_E0,i | 308 | 1.2785820379274944 | 1.4565054126614172 | 211.46505692498818 |
| H-EXIT-3 | d_i = R_E0,i − R_E3,i | 308 | 2.175709106680485 | 1.8915097057960606 | 162.8328943045921 |

Exclusion counts (procedure §4): cohort events 311; pre-entry gap
[C11] exclusions 1; window-incomplete 0; unclosed in E0 at the data
boundary 2; unclosed in E1 0; **common paired set n = 308** (≥ the
frozen 100 floor). No mean difference, arm mean, per-arm SD, interval,
or per-event value was printed, stored, or transmitted (variance-only
discipline); the run script asserts each endpoint's output keys are
exactly `{n, s, DE, n_eff}`.

Design effect: DE = (calendar-block resample variance of the mean) ÷
(independent-observation variance of the mean), blocks of 20 sessions,
10,000 replications, circular block bootstrap over DEV-relative
session ordinals — the [C10] construction, following the program's
EXP-14-lineage implementation (block starts drawn uniformly from the
ordinals present in the items; a block covers 20 consecutive ordinals
circularly over the observed span and contributes every value whose
ordinal it covers; blocks drawn until ≥ n values; statistic = mean of
the first n). RNG PCG64, seed 2999475941474119668 = first 8 bytes
(big-endian) of the frozen preregistration's SHA-256 (PREREG_V10.md
`29a0477a…`). Mean blocks per replication 19.3805.

## Input pins — all verified before computing (details: verification_log.json)

| input | sha256 | result |
|---|---|---|
| simulator pine_backtest.py (post-erratum, -14 successor) | `262ec0340161e72893ca9c5edd9d1fe2cb046fd30004d727b3893d52bd4d3f2a` | OK |
| C1 config canonical (from committed -13 driver) | `87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706` | OK |
| -13 DEV ledger trade_ledger.json | `267e794c284a409d7d9b6d8e1056c452976b59746062e9e6e18c5664b74c003b` | OK |
| EXP-14 frozen cohort (corr2, 311 events) | `35690b806e51eefe388fadf35b04baf5ed4c52f8e30ac193a38cf88246332824` | OK |
| P7b inventory p7b_inventory.jsonl | `a6bbd19a702120cafd48cd01ee4c8ff59b838a8bd6439822415d6c18278ef02f` | OK |
| adopted session table (751) | `00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f` | OK |
| scanner_rules.py (resample) | `62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c` | OK |
| -13 driver run_study13.py (stage copy + committed blob) | `4962e30d8b42124ebc317aab647351521d107b600c01a42905fce4c41ce4b22b` | OK |
| capture manifest roots (child `c5628652…`, parent) | recomputed = committed | OK |
| archive SHA256SUMS, both namespaces (td_pilot_20261023, td_capture_equity39_continue_20261023) | full verify | OK, 0 mismatches |

## Data-path verification (all gates passed before any leg was built)

- DEV bars rebuilt through the executed -13 pipeline (admission →
  session-anchored 4H resample → pinned-engine indicators):
  3,653 admitted 1h bars and 1,043 4H bars per symbol, all 43 symbols.
- Reconciliation vs the P7b every-bar inventory: 44,849 bars —
  close / ATR / EMA21 / EMA55 / EMA200 / signal flag / session ordinal,
  **0 mismatches**; signal census 2,892 fires = the P7 census 2,892.
- Cohort: all 311 events — timestamp and signal flag verified bar by
  bar; session ordinals agree with the inventory.
- **E0 fidelity gate:** the anchored single-trade E0 implementation
  reproduced the -13 ledger's on-record net R (25 bps flat view) for
  all **586/586** closed candidates (max |ΔR| = 4.99e-05, the ledger's
  4-decimal rounding), with entry/stop/exit/TP1/hold/reason metadata
  identical, and returned unclosed for all 4 censored candidates.

## Arm constructions (frozen §7; implementation in o4_run.py)

- E0: the pinned simulator's standalone-trade path (close-evaluated
  trailed stop; TP1 intrabar at the limit; EMA55/trend-bear close
  exits at next open; 50/50 blend), net of the flat 25 bps view.
- E1: intrabar stop at the level in force entering the bar, fill
  min(open, level) − 0.05 ATR [C15], stop-first on a same-bar TP1
  touch; other exits as E0. Disclosed choices: the 0.05 ATR slippage
  is taken on the signal-bar ATR (the trade's construction ATR), and
  E1 is managed over the same bars as frozen E0 (entry bar through
  bar n−2), so a boundary-open trade is unclosed for that arm.
- E3: fixed exit at the close of bar i+20; R denominated by the
  frozen initial risk (entry − stop0), the common R unit.
- [C11]: entry ≤ stop0 excludes the event from all arms (counted: 1).

## Command / environment

```
PYTHONPATH=~/workspace/qf_td17_stage/pylibs python3 o4_run.py
```
Run from the staging directory; inputs read from origin/main blobs and
the -13 stage environment (untouched). Script sha256:
`9a14d1869bb0665eea68c003be83530f1ab375cdef274de2ee31bfc29b730a06`.

Aborted attempts before the successful run (disclosed; none produced
any statistic): (1) STOP — `pandas_market_calendars` missing from the
default environment (the PYTHONPATH above is the program's stage
library path); (2) harness crash in the fidelity gate (the pinned
generator returns a `(trades, skipped_gap)` tuple — unpacking bug in
the gate code, fixed); (3) STOP — fidelity gate key name (`tp1_hit`).

## Standing of the result

These SDs are the missing 7A variance inputs for the H-EXIT cells of
POWER_REPORT §4. Per procedure §5 they enter the freeze record
(completing checklist item O4 / gate items B9/G3) only after ChatGPT's
**blind replication** from this committed package. They are variance
inputs only; they change no verdict and authorize nothing further.
The frozen §7 posture stands: paired SDs of this size are what the
power arithmetic already assumed — the H-EXIT family remains a
multi-year confirmation path at reachable DEV event rates.
