# QF-EQUITY43-CORRECTED-FORWARD-PARITY-BUILD-20261023-15 — RESULT

**Verdict: OFFLINE_PARITY_READY** (the build). **Launch: HOLD** — the
narrow next-launch gate in `readiness/S1_S2_READINESS.md` is unmet
(FEED_NOT_READY + G4/VBASIS unadopted; T0 unset). Nothing was activated:
no prospective T0, no shadow launch, no paper or live entries, no vendor
calls, no credits (program TD total stays 115 desk), no holdout access,
no tuning, no performance run of any kind in this task. PAUSED
production untouched and re-proved (harness `ce7c902c…`,
PAUSE_NEW_ENTRIES present, RESUME absent — before AND after).

Authority: Mike GO relayed by ChatGPT, Issue #1 comment 6376747198
(Slack TS 1792797916.849259). Single-dispatch check was CLEAR. This lane
ran in parallel with -14 (forensic lane) and stayed strictly inside the
-15 build scope; -14's work was neither redone nor touched. Legacy V5.4
06:30-grid trades and the staged 250-name shadow were used as parity
evidence for NOTHING.

## What was built

`EQUITY43-CORRECTED-FWD-v1` (contract: `CONTRACT.md`) — an isolated
candidate forward observer (`observer/fwd_observer.py`): streaming 1h
feed admission against the pinned 751-session table, corrected
session-anchored 4H bar construction, a streaming candidate state
machine with the -13 successor censoring semantics, an append-only
hash-chained journal with an external anchor, snapshot/restore restart
state, and an armed-mode PAUSED-sentinel gate. Strategy semantics are
NOT re-implemented: indicators, signals, ranking features and both
portfolio simulators are the pinned -13 successor engine sources,
byte-identical (P0-verified); all new code is confined to the
observer/parity layer. Plus the decision-parity harness
(`observer/decision_compare.py`), the adversarial suite
(`tests/test_fwd_parity.py`, 18 tests), and the two-stage readiness
spec (`readiness/S1_S2_READINESS.md`): S1 corrected signal-only
observation and S2 prospective paper validation (50 interim / 100 full
observations, 25bps preregistered) as two clearly separated,
UNACTIVATED stages.

## Acceptance criteria — per-criterion verdicts

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Exact -13 configuration pinned (43 names, SMCI absent/not imputed; corrected decision rules; frozen C1 rules/caps/exits; strategy sources byte-identical, deltas confined to observer/parity layer) | **PASS** | `CONTRACT.md` pin table; compare-harness inventory: ref P0 pins (successor/fork/original engines, session table, archive SHA256SUMS 158/158 + 22/22) and P1 receipt chains (child root `c5628652…` recomputed MATCH, 54/54 receipts re-walked from GENESIS, pilot receipts field-verified) |
| 2a | 09:30/13:30 grid formation | **PASS** | Synthetic T01; real-byte bars parity: **44,849 bars, 0 mismatches** (OHLCV exact, SessionVWAP max abs diff 0.0) |
| 2b | Early closes + DST transitions | **PASS** | T02 (13:00 single bin), T07 (phantom post-close excluded), T04/T05 (wall-anchored bins; UTC offsets −5→−4 spring, −4→−5 fall; decision instants exact) |
| 2c | As-of SPY correctness (no same-day close leak) | **PASS** | T13 (×40 mutation of the unfinished day's close: as-of RS invariant, midnight construction swings 0.191→46.65); real-byte benchmark parity exact over 524 sessions; RS feature mismatches vs -13 ledger: **0 / 590** |
| 2d | Cost views | **PASS** | T14 + real-byte taken flags identical at gross / 4bps / 25bps for all 590 candidates |
| 2e | Ranking / sector / risk / cap enforcement | **PASS** | T14 contested scenario (4bps skips: rank 5, sector-gate 1; dispositions identical cross-implementation and input-order-invariant); real-byte 4bps C1 dispositions **590/590 identical**; C0 counts observer == -13 (taken 193, cap skips 323, risk skips 74) |
| 2f | Terminal censoring into inventory / marks | **PASS** | T18 (mark == last completed close, no fabricated exit/cash flow); real-byte: the 4 censored candidates (CRM/SHOP/MRNA/PFE) identical, terminal-inventory symbol sets identical per view |
| 2g | Incomplete/corrupt bar refusal (fail-closed, no scan-on-failure) | **PASS** | T08 (price-moving zero-volume poisons one symbol, the other unaffected, zero candidates), T09 (missing hour → session gap, no bars), T03/T06/T11 (holiday / legacy-grid / duplicate / out-of-order refused); on clean DEV bytes the observer rejected **0** of 157,086 rows and excluded exactly the 61 known post-close phantom stamps |
| 2h | No-backfill after outage | **PASS** | T10 (late bar for a finalized session refused LATE_BAR; no bars, no retroactive signal) |
| 2i | Restart / idempotency | **PASS** | T15 (snapshot + verified journal resume mid-feed → final journal **byte-identical** to the uninterrupted run; duplicate re-feed refused; candidates identical) |
| 2j | Externally anchored append-only hash-chained journal | **PASS** | T16 (intact verifies; tampered record and truncated journal both detected against the external anchor); real-byte journal: **69,439 records, chain verified** against its anchor |
| 3 | Offline decision comparison vs -13 on the permitted DEV bytes (events only — no R, no equity, no returns produced) | **PASS** | `compare_results.json`: bars 44,849 exact; candidates **590/590, 0 mismatches, max term diff 0.0** (identity, entry/stop/TP1, entry/exit times, exit reason, hold bars, TP1-hit, censoring); skipped-gap 1 == 1; portfolio decisions 0 mismatches (taken flags ×3 views, 4bps dispositions, terminal sets, C0 counts) |
| 4 | Two separated stages; S2 specified unactivated (50/100 obs, 25bps preregistered) | **PASS** | `readiness/S1_S2_READINESS.md` — S1 signal-only (zero positions/orders/cash/P&L), S2 separately gated with frozen targets, failure criteria, regime stratification; neither launched |
| 5 | Feed readiness for a prospective route | **BLOCKER (launch only)** | **FEED_NOT_READY**: no prospective 1h route is qualified under the contract's bar/basis policy on actual bytes; G4/VBASIS remains UNADOPTED (CONVENTION_BREAK_SUSPECT). T0 therefore **UNSET** — not invented |

**Synthetic suite: 18/18 PASS, exit 0** (`test_stdout.txt`).
**Decision comparison: exit 0, DECISION_PARITY_PASS**
(`compare_stdout.txt`, `compare_results.json`), run offline under
`unshare -n`.

## Launch blocker table

| Blocker | Class | What clears it |
|---|---|---|
| FEED_NOT_READY | S1 gate 2 | A prospective 1h route for the 43 names evidenced on actual bytes against the contract's input policy |
| G4_UNADOPTED (VBASIS CONVENTION_BREAK_SUSPECT) | S1 gate 2 / S2 gate 2 | A governed adoption of the basis convention (not this build's to make) |
| T0_UNSET | S1 gate 3 | Follows from the two above: first XNYS session the qualified feed can fully observe, named in the activation record |
| S2_NOT_AUTHORIZED | S2 | Its own later record (readiness §S2 gates 1–8) after S1 completes |

## Recommended next action (one)

Adjudicate a prospective-feed qualification step for the 43 names
(actual-byte evidence against CONTRACT.md §4, with the G4/VBASIS
disposition named) — it is the only path that can ground a T0; every
engineering prerequisite on the observer side is now proven offline.

## Reproduction

Stage layout (this build's stage): engine trees + manifests +
`reference_run_study13.py` + fresh archive clone @ `bb644db`, all pins
re-verified at runtime by the harness's inventory section.
Commands (venv = the -08 lineage venv, Python 3.12 / pandas 2.2.3):
`python tests/test_fwd_parity.py <stage>` (exit 0);
`unshare -n python observer/decision_compare.py <stage>` (exit 0).
The observer journal/anchor from the comparison run are stage artifacts
(`work/compare_journal.jsonl` — 69,439 records, ~15 MB — and
`work/anchors/compare_anchor.json`), verified in-run and retained in
the stage, not committed (size only; every verdict above is reproducible
from the committed harness + pinned inputs).

**Bounds held:** no activation/T0/shadow/paper/live entries; no vendor
calls or credits; HO bytes touched only as SHA256SUMS hashes and
receipt-chain metadata (never parsed); no tuning or performance
sensitivity; no G4 waiver; no 250-symbol scan; production PAUSED and
pin-identical before/after; -12/-13 records immutable. Elapsed ≈ 40 min
including the 14-minute offline comparison execution.

— Muse
