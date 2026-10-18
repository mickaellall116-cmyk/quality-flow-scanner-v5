# QF-VALIDATION-CONTRACT-CONSOLIDATION-20261018-21 r1

**Spec:** GitHub Issue #1 comment 6251622925 (2026-10-18T15:22:20Z)
**Mode:** OFFLINE, existing committed records only. No repair/rerun.
**Package:** this memo + `validation_contract_consolidation_20261018_21/READINESS_MATRIX.json` + `validation_contract_consolidation_20261018_21/SHA256_MANIFEST.txt`
**Consolidated at HEAD:** `220a0866c315f7a73706700eb5701ce31ff1f59a`

## Verdict

**CONTRACT_CONSOLIDATION_COMPLETE_WITH_BLOCKERS** — 27 contract fields graded:
**18 PASS / 5 PROSE_ONLY / 4 MISSING / 0 CONFLICT.**

The strategy core is fully pinned in executable committed bytes (signal,
integer trendScore, parameters, rs_top2 admission rule, sizing, caps, exits,
warm-up, cost application, fill/gap/same-bar semantics, session-anchored
constructor). The blockers are concentrated in three sibling modules that the
pinned bytes import but that were never committed to git — `pine_exposure`
(sector map), `pine_ranking` (RS feature computation), and
`pine_signal_quality` (benchmark loader) — plus the unpinned exact holdout
window. No identity was inferred, substituted, or reconstructed; every
non-PASS field names the single minimal action that closes it.

## 1. Baseline input identity

- **UNIVERSE_X (51 symbols) — PASS.** `pine_backtest.py` bytes
  (archival_sources_v1, sha256 `447a9a13bb2ec7ab…`) define
  `UNIVERSE_X = UNIVERSE_15 + [36 symbols]`; the set was verified
  programmatically to equal `complete_manifest_rev2.json` `universe.symbols`
  (51/51; manifest `definition_sha256 d139d7bf…`; manifest file sha256
  `1b0535ab6ddff52c…`, both committed copies byte-identical).
- **Benchmark symbol (SPY) — PROSE_ONLY.** Named only in prose: the
  corrected-baseline docstring ("20-bar return minus SPY") and prereg rev2 §7
  (SPY regime labels). No committed executable byte designates it.
- **Benchmark loader bytes — MISSING.** `pine_signal_quality.load_benchmarks`
  is imported by both `pine_stack.py` and the corrected baseline; the module
  is absent from git entirely.
- **Frozen sector mapping — MISSING (BLOCKED).** The manifest pins the map's
  identity — source `pine_exposure.pine_exposure.SECTOR`, count 51, canonical
  sha256 `9bab23b72dcb18d04935071f2bec94955cb8fa9df96f50dc11b72990dcd7fbb9` —
  but that is a digest whose preimage is not committed: `pine_exposure.py`
  bytes exist nowhere in the repo, and no committed record lists any
  UNIVERSE_X symbol's sector. The sector cap therefore cannot be executed as
  frozen until bytes hashing to that pin are recovered. (The SECTOR_2022
  overlay additions in `pine_stack.py` — COST/WMT→STAPLES, JPM→BANKS — are
  pinned bytes but cover 2022-window symbols, not UNIVERSE_X.)
- **Sector cap rule — PASS.** Max 2 concurrent open positions per sector
  (`simulate_stack` bytes).

## 2. Unchanged-strategy identity (all executable bytes unless noted)

- **Signal** `pine_buy_signal` — PASS. Confirmed / breakout / ready paths,
  evaluated on completed bars only (pine_backtest.py `447a9a13…`).
- **Integer trendScore** — PASS. The pinned bytes are the *corrected*
  implementation (each Boolean cast to `int` before summing, true 0–5 count;
  defect explained in-code). The buggy numpy-boolean variant is not pinned.
- **Parameters** — PASS. EMA 9/21/55/200, ATR 14, ADX 14, volume MA 20,
  breakout 10 bars; TP 2.0 / SL 1.5 / TRAIL 2.5 / HOT 1.5 ATR multiples.
- **RS feature computation — MISSING.** `pine_ranking.compute_features` is
  imported by the pinned stack/baseline bytes; the module is absent from
  git. The formula (20-bar return − SPY) survives only as docstring prose.
- **rs_top2 admission** — PASS. On contested bars, admission stops once
  `taken_at_t >= min(2, free slots)` (pine_stack.py `839e4800…`). The rule is
  pinned; the RS values it consumes depend on the missing module above.
- **Risk** — PASS. 1% per trade (`RISK_PCT=0.01`); drawdown-gate state halves
  risk (`RISK_PCT/2`) in stack bytes.
- **Portfolio stack** — PASS. Max 5 concurrent, 5% portfolio-risk cap,
  mark-to-market drawdown — constants in pine_backtest bytes, enforced in
  both simulators. (The live V5.4 forward harness's max-6-open is a different
  artifact, outside this C1 contract; no in-contract disagreement.)
- **Exits** — PASS. TP1 = 50% intrabar limit at entry + 2.0·ATR; initial stop
  = signal-bar close − 1.5·ATR; post-TP1 runner trail at close − 2.5·ATR;
  EMA55-break / trend-bear exits are close-evaluated. The C1 bytes contain
  **no** 30-bar max-hold and **no** +1R profit-protect rule.
- **Warm-up** — PASS. 215 4H bars (`WARMUP=215` bytes; prereg rev2 §3).

## 3. Execution contract

- **Cost, 4 bps one-way — PASS.** `_outcome` bytes subtract the cost exactly
  once per completed trade (`net_ret = gross_ret − cost`); the corrected
  baseline header pins "4bps one-way cost via pb._outcome". Legs: 4 bps
  reference, **25 bps primary adjudication**, 30/35 bps stress (prereg rev2
  §6; `COSTS` dict bytes carry 4/25). The corrected baseline's reported run
  used the 4 bps leg — two defined legs, not a disagreement.
- **Fill timing — PASS.** Signal on closed bar *i* → entry at next bar open;
  close-based exits → next bar open; TP1 intrabar limit (bytes + constructor
  spec §5).
- **Gaps — PASS.** Next-bar open ≤ stop ⇒ trade skipped (`skipped_gap`).
- **Same-bar ambiguity — PASS (determined).** TP1 is the only intrabar
  order; stop/trail/EMA exits are close-evaluated only (the script never
  passes a stop order), so no intrabar stop-vs-TP1 race exists in the frozen
  semantics.
- **Split / corporate-action handling — PROSE_ONLY.** Prereg rev2 §2 freezes
  the policy as prose (Yahoo 1H `auto_adjust=False`, `prepost=False`, "frozen
  split-exclusion protocol", retroactive-adjustment LIMIT
...[truncated 3395 chars]