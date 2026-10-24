# EQUITY43-CORRECTED-FWD-v1 — identity / fidelity contract

**Task:** QF-EQUITY43-CORRECTED-FORWARD-PARITY-BUILD-20261023-15 r1.
**Status:** offline candidate build. NOT activated. No T0 is set (see
`readiness/S1_S2_READINESS.md` — the launch gate is unmet).

This contract freezes the identity of a *future* corrected forward cohort
so that any later activation decision names exactly one configuration.
It grandfathers nothing: the legacy V5.4 forward test (06:30-anchored
grid) and the staged 250-name shadow observer are **not** parity evidence
for this cohort and are not part of it.

## 1. Universe (exact)

The 43-equity W_DEV universe of QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13
(package `521980a`), in the -13 canonical universe order:

NVDA, TSLA, AAPL, SPY, PLTR, SOFI, AMD, MSFT, META, COIN, MSTR, AVGO,
GOOGL, AMZN, NFLX, CRM, MU, INTC, LRCX, AMAT, QCOM, ARM, HOOD, APP,
NET, SNOW, DDOG, CRWD, SHOP, RKLB, ASTS, LUNR, PYPL, NU, MELI, IWM,
SMH, ARKK, XLF, NIO, MRNA, PFE, F

(the -13 `universe_43_order`, verbatim). The authoritative membership is
the -13 driver's construction — `PILOT + [W_DEV legs of the child
manifest c5628652…]` — reproduced and asserted (43 unique) by the
parity harness at runtime; the list above is descriptive. **SMCI is EXCLUDED, pre-declared, and never imputed** (no DEV
bytes exist; TD SMCI/HO is NOT_EVALUABLE_PROVIDER_VOLUME). No crypto. No
199-name extension. No 250-symbol scan.

## 2. Configuration pin (from -13, package `521980a`)

| Element | Pin |
|---|---|
| -13 experiment config | sha256 `87b8285a522ba0e3…` (frozen in `run_study13.py`) |
| Successor `pine_backtest.py` | `874d2a9b1d99171a4d3db709ece9ce4719b4d108a70f7e95b4a082692cc0c99d` |
| Successor `pine_stack/pine_stack.py` | `8d4a964fd7bb08b4a98a55eb7fae222157ae27f1a768f255e7cbc152c9d15b03` |
| Pristine -09 fork `pine_backtest.py` | `becea0824486003daef386b49e137a83ffdf22c1e2d145136498919102fc42f2` |
| Pristine -09 fork `pine_stack.py` | `30594231ffc3bac27303f96310e8f274229415c890c371f4dbdfcdb54156cda4` |
| `asof_benchmark.py` (-09 fork) | `f0f4582c4a8aee484c24d330658b0c4ae6e2a169c19f3bf2b1475c2dc2ce2017` |
| `scanner_rules.py` (shared, unchanged) | `62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c` |
| `pine_ranking.py` (shared, unchanged) | `77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6` |
| `pine_signal_quality.py` (shared) | `b1b39ee8d0bd4bbb1387b3ce54c7345c1f8dd622f94a5ed390c989fed1d39e69` |
| `pine_exposure.py` (shared; SECTOR map) | `9f646161c27f6b28febe0980d03665bc9c1502fb844d37be6fd1d72ee45102be` |
| Frozen original `pine_backtest.py` | `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5` |
| Session table (751 sessions) | `00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f` |
| -13 driver `run_study13.py` | `4962e30d8b42124ebc317aab647351521d107b600c01a42905fce4c41ce4b22b` |
| Child receipt-chain root | `c5628652c5bf59d870103e41fd7e22a23fe4d811c61662fda78a8790abd0444f` |
| Parent capture-manifest root | `ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64` |
| Pilot manifest root | `79ccdd128e0b36537f56f8ae36a731b719e989b9756f65856b7dc47344327122` |
| Archive | qf-data-archive @ `bb644db9a05968cdf8f8d760b3af937c0a9d1958` |

Strategy sources are byte-identical to the -13 pins. The ONLY new code
in this build is the observer/parity layer (`observer/fwd_observer.py`,
`observer/decision_compare.py`, `tests/test_fwd_parity.py`).

## 3. Decision rules (the corrected semantics)

* **Bars.** 1h ET bars admitted iff their bar-open stamp belongs to the
  pinned session table's expected hourly set for the date
  ([09:30, close)); corrected 4H wall bins **09:30→13:30** and
  **13:30→16:00** (single **09:30→13:00** bin on 13:00 early closes),
  assigned by ET wall-clock session time — never by a UTC-anchored
  resample. Aggregation: O = first open, H = max, L = min, C = last
  close, V = sum; SessionVWAP cumulative within the session.
* **Decision time.** A bar is actionable only at its bin CLOSE
  (13:30 / 16:00 / 13:00 ET). No decision may use an unfinished bar.
* **Benchmark.** SPY daily bars stamped at session COMPLETION (16:00 ET,
  uniform — early closes stamped 16:00 too: conservative, can only delay,
  never leak). RS = 20-bar return minus SPY return over the same span,
  selected by the frozen `bench_ret` rule (last daily bar ≤ t). The
  midnight-stamped construction is the proven B1 defect and is forbidden.
* **Marking.** Portfolio marks use the last COMPLETED 4H bar at or before
  the mark instant (successor completed-bar marking; the unfinished-bar
  mark is the proven B2 defect and is forbidden).
* **Candidate generation.** Frozen V3.6 hybrid `pine_buy_signal`
  (WARMUP 215 bars), entry at next bar open, stop = signal close −
  1.5·ATR, TP1 = entry + 2.0·ATR, trailing runner 2.5·ATR after TP1,
  exits: stop / ema55-break / ema55-bear at next bar open — exactly the
  frozen `gen_candidates` semantics, field-verified.
* **Canonical order.** Candidates are processed in canonical
  `(symbol, signal_idx)` ascending order in BOTH simulator paths
  (adjudicated Ruling A, -13). Input list order must never change an
  outcome.
* **Portfolio gates (frozen C1 configuration).** R1 rs_top2 ranking at
  contested timestamps, R2 sector cap (max 2 open per sector), no R3;
  max 5 concurrent positions; 1% risk per position; 5% portfolio risk
  cap; exits processed before entries at shared timestamps.
* **Terminal censoring (Ruling B).** A position still open at the window
  end is a right-censored candidate: it enters the identical time-local
  selection; if taken it is held to the cutoff and valued at the
  last-completed-bar as-of mark; if skipped it is ledgered with its gate
  reason. No exit, cash flow, or trade R is ever fabricated for it.
* **Costs.** Views: gross (0), 4bps, 25bps per the frozen
  `pb.COSTS` + gross convention of -13.
* **Signal-event key.** `(symbol, signal_idx)` — unique per candidate;
  the journal additionally keys every event by chain sequence.

## 4. Input policy (prospective)

* Adjustment: split-adjusted (`adjust=splits` per the capture receipts);
  volume as reported by the vendor on admitted bars.
* A price-moving zero-volume bar on an admitted stamp poisons the leg
  (whole-leg quarantine class, capture precedent -10/-11).
* Post-close stamps on a pinned session date are excluded by admission
  (the phantom class), never admitted, never filled.
* **G4 / VBASIS: UNADOPTED.** The convention remains
  CONVENTION_BREAK_SUSPECT (checker candidate-2). This build does NOT
  adopt a basis convention; the -13 inputs are candidate-grade
  (`CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED`), NOT QUALIFIED. Any future
  activation must name the adopted convention as gate evidence.

## 5. Journal / provenance

Append-only JSONL journal, hash-chained from
`GENESIS:EQUITY43-CORRECTED-FWD-v1`; records carry market time + sequence
only (no wall clock), so replays are byte-identical. The chain head is
anchored after every session seal to a SEPARATE anchor store outside the
journal file; verification detects record tampering, truncation and
anchor divergence. Restart state is snapshot/restore against the
verified journal head — a divergent journal is refused, never repaired.

## 6. What this contract is not

Not an activation. Not a feed qualification. Not evidence about the
legacy cohort, the 250-name shadow, or the sealed holdout (untouched).
The -13 historical result keeps its labels: EQUITIES-ONLY DEV
EXPLORATORY / G4 UNADOPTED / NOT VALIDATED EDGE.
