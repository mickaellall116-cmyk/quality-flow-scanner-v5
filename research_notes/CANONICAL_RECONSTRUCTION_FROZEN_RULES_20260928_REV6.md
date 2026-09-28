# Canonical Reconstruction — FROZEN RULES rev 6 (DRAFT)

**Date:** 2026-09-28
**Status:** DRAFT rev 6 — implements the Rev-6 mandate (GitHub
Issue #1, comment `5879344325`, 2026-09-28: Claude's rev-5 independent
audit returned DRAFT; Mike independently accepted both blockers D-1/D-2 —
**ACCEPTED**).
**Supersedes:** rev 5 (`CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV5.md`,
commit `fd9f8f1`), which had ChatGPT's rev-5 mechanical PASS
(comment `5878839583`) but was returned to DRAFT by Claude's independent
rev-5 audit. Mike gave no final sign-off on any rev; final sign-off is
reserved for the post-Claude rev-6 gate. Rev 5's audit history is retained
for the record; rev 5 is not operative.
**NO BUILD AUTHORIZED.**
**NO BUILD AUTHORIZED.**

## What changed in rev 6 (mandate D-1/D-2 + non-blocking corrections)

Rev 6 is a **narrow audit/spec correction only**: no strategy semantics are
changed to improve historical results, and no reconstruction build/run is
authorized. The closed items from the Rev-6 mandate (R-1 B-first grade
precedence, M3 raw-vs-rounded buy-zone, M4 no V5.4 RISK-OFF veto, M5
recovered-file provenance/hashing, M7 canonical PORTFOLIO pin, PIT /
early-close / MTF availability split, and the rev-5 no-Layer-2-steering
conclusion) are **not reopened**.

- **D-1 (Gate D — D6 added):** new **D6 independent portfolio-selection
  differential oracle** (§10). D4/D5 prove eligible-signal identity is
  independent of legacy score/regime logic; D6 proves contested-slot
  portfolio selection (A3 admission sequence + A4 ranking) is likewise
  independent of legacy `score`/`rank_score`. Includes synthetic
  contested-slot fixtures where an injected legacy-score ordering conflicts
  with the A4 RS ordering — D6 must still reproduce A4/A3 exactly and fail
  if selection follows the injected ordering. Proof line: D1/D2
  supplementary guards; D4/D5 = eligibility proof; **D6 = selection proof**.
- **D-2 (M1/M2 rationale corrections; frozen choices retained):**
  M1 — removed "SessionVWAP unavailable by construction": the underlying 1H
  OHLCV can support session-VWAP reconstruction, so rolling-50 VWAP is a
  JUDGMENT choice with disclosed sensitivity (can change above_vwap /
  protection / entry eligibility), not a technical impossibility — §2.2.
  M2 — removed "205-bar gate dominates seed sensitivity": disclosed the
  exact ewm weight math (first observation retains ≈13% weight at bar 205,
  ≈8% around bar 250); PIT_FEATURES establishes the warmup/seeding need,
  not the all-history resolution; all-history seeding labeled JUDGMENT with
  early-sample EMA200/`trend_bull` sensitivity disclosed — §3.
- **Non-blocking corrections:** A5 freezes the D4/D6 identity-key timestamp
  convention on half-days (13:00 ET decision-availability, not tracked
  13:30 `bar_close_at`); §4 removes the nonexistent "14:00 ET decision"
  on early-close days; D4 scope = the rebuild's decision points after the
  §3 eligibility floor; D5 twin perturbation frozen (last-bar-only,
  asserted structural invariance — the uniform 3x-volume twin is
  forbidden); P22 distinguishes SHA-256 `8ddc1e61…` from git blob
  `4356f732…`; support commit `48579180` dated 2026-09-14T23:15:42Z with a
  no-change record through canonical commit `368fa2e`; §5B relabeled a
  consistency check (not an independent ranking); D5-c relabeled (not a
  minimal-score threshold test).

## What changed in rev 5 (mandate M1–M7 + non-blocking corrections)

The exact local V5.4 wrapper/grader files were recovered (untracked,
2026-09-15) and hashed **before any further read**:
`v54_engine.py` → `bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb`,
`v54_rules.py` → `1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a`.
Byte-identical copies + provenance record are in the Claude audit bundle
(`research_notes/claude_audit_bundle_rev5/`). Every §2 rule is now
classified **COPY / DERIVABLE / JUDGMENT** against those bytes (ledger:
Appendix P).

**R-1 — grade-precedence reversal (the one substantive rule change vs rev 4).**
Rev 4 froze unknown→C first (ChatGPT C1, adopted by Mike). The recovered
`v54_rules.v54_grade` bytes and the frozen handoff brief
(`chatgpt_handoff_brief.md`: "Daily+Weekly both aligned **and/or market
CONFIRM**" → B) both show **B-first**: `(daily==confirmed and
weekly==confirmed) or gate==CONFIRM` → B; then unknown → C; else A.
Rev 5 freezes the bytes' literal order as COPY. Consequence: unknown MTF +
CONFIRM gate → **B**, not C. The C1 order is superseded — it was adopted
without the bytes. Flagged here and in Appendix R for the rev-5 audits to
scrutinize.

- **M1 (VWAP):** frozen to the 50-bar rolling VWAP on the rebuilt 4H
  series, labeled JUDGMENT; the live-preferred SessionVWAP alternative is
  recorded and rejected (unavailable in the OHLCV-only rebuild) — §2.2.
- **M2 (indicator seeding):** all-history seeding from
  `first_available_4h_bar` retained, labeled JUDGMENT; the live-faithful
  finite-window alternative (180d trailing window, per
  `v54_scan_symbols` defaults) is recorded — §3.
- **M3 (buy-zone rounding):** frozen — the engine computes entry with raw
  bounds; the hard gate re-checks the **rounded serialized** zone
  (`_inside_buy_zone` parses the `.2f` string) — COPY from the bytes — §2.3/§2.4.
- **M4 (RISK-OFF veto):** resolved by the bytes, not by JUDGMENT — the V5.4
  path contains no RISK-OFF veto (the engine re-derives entry from pure
  triggers; `v54_rules.py` explicitly disavows the V5.3 veto imports). The
  legacy `classify_symbol` RISK-OFF→WATCH is recorded as V5.3-only — §2.6.
- **M5 (wrapper/grader provenance):** files recovered, hashed, bundled;
  per-rule classification in §2 basis notes + Appendix P.
- **M6 (Gate D):** strengthened with **D4** (independent differential
  oracle: identical eligible signal identity set across every evaluated
  bar) and **D5** (synthetic anti-score fixtures: BUY + PULLBACK +
  RISK-OFF-context cases); D1/D2 kept as supplementary guards only — §10.
- **M7 (PORTFOLIO.md):** pinned to committed blob
  `8ddc1e61fb0a8b85939fad547da0d73428bcc4299ce554731db30e4634f8d5ab`
  at commit `368fa2e594da154d72327b5d92bba2d31b20c5c7`; the rev-3 bundle's
  differing copy is documented as noncanonical and superseded — §1.
- Non-blocking corrections: grading-only vs portfolio acceptance (§2.6);
  QQQ 4H early-history correction (§2.7); early-close daily-availability
  reconciliation (§4 vs §2.8); MTF EMA21 rising frozen as `>=` (§2.8);
  `E_mark(T)` uses `remaining_shares` (§7/A6); Layer-1 rewritten
  non-circular (§5); dividend-adjustment limitation of archival
  `auto_adjust=True` MTF pulls (§11); SEALED filename declared legacy
  (§15); authorship normalized — ChatGPT authored R1–R4, Mike adopted
  them (throughout).

---

## §0. What this exercise is (reframed per Claude audit)

This is an **unblinded replication** producing a **reconstructed canonical
replica** — not a "sealed-oracle" reconstruction. The Claude audit's
stop-level finding is accepted: the mandatory source documents
(`PORTFOLIO.md`, `REBASELINE.md`, and prior revs' §3) already disclose the
historical path and results, so no claim of investigator blinding is made or
implied. The word "sealed" no longer appears as a blinding claim anywhere in
this spec.

What replaces blinding is **process control** (§9):
no historical outcome may choose among frozen resolutions; comparators are
examined only after code hash-lock and Run 1; any mismatch is a finding, never
tuning permission; reruns follow the §10 protocol. The comparator file's
SHA-256 (§15) is an **integrity commitment** to that file's bytes, not a
blinding device.

Original-machine recovery remains **cancelled** per Mike's directive
2026-09-28. Whatever the rebuild produces is labeled **reconstructed
canonical replica**, never "recovered original."

---

## §1. Frozen source anchor + provenance controls

- Specification set (only these six docs are canonical spec):
  `canonical_baseline/ENGINE.md`, `LONEWOLF_RERUN.md`, `PIT_FEATURES.md`,
  `PORTFOLIO.md`, `REBASELINE.md`, `UNIVERSE.md`.
- **PORTFOLIO.md pin (M7).** Canonical bytes: SHA-256
  `8ddc1e61fb0a8b85939fad547da0d73428bcc4299ce554731db30e4634f8d5ab`
  (SHA-256 of the file bytes; the git blob at
  `368fa2e594da154d72327b5d92bba2d31b20c5c7` is
  `4356f732a9a9fe2698e852d66b8a11d91212d810` — the two hashes are
  different objects and must not be conflated),
  (2026-09-25; verified identical locally). The rev-3 bundle carried a
  differing local/bundled copy of PORTFOLIO.md — that copy is
  **noncanonical** (no later canonical commit changed the file between the
  rev-3 spec commit `60776c3` and rev 4) and is **superseded**. The pinned
  blob above is the only canonical PORTFOLIO.md for this exercise.
  (The pinned PORTFOLIO.md itself documents the historical method as
  "frozen V5.4 logic (`v54_engine.v54_classify`), all grades A/B/C, strict
  PIT (structural contract, ADX>=20, no scores)" — consistent with §2.)
- Repository tree anchor for candidate-pool sources: commit
  `de01ff70a13e680c5468ae5e6e81177c981832e0` (parent of first canonical-doc
  commit `e77bb16`). Do NOT source symbols from current main.
- **V5.4 wrapper/grader provenance (M5).** The exact local files used for
  the §2 transcription were recovered and hashed **before any further
  read or edit** (2026-09-28):
  - `v54_engine.py` (368 lines, mtime 2026-09-15 12:31:22 -0400):
    `bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb`
  - `v54_rules.py` (196 lines, mtime 2026-09-15 12:30:45 -0400):
    `1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a`
  - Byte-identical copies + `PROVENANCE.md` are in the Claude audit bundle
    (`research_notes/claude_audit_bundle_rev5/`); the originals remain
    untouched and uncommitted at the repo root. No commit ref exists for
    them; the version pin is `V54_RULE_VERSION = "2026-09-15-v54"`
    (declared in `v54_rules.py`).
  - **Per-rule classification:** every §2 basis note states whether the
    rule is **COPY** (verbatim from those bytes), **DERIVABLE** (follows
    from those bytes or the pinned tracked code with no material
    discretion), or **JUDGMENT** (frozen reconstruction choice, recorded as
    such). Consolidated ledger: Appendix P.
- **Untracked-file quarantine (process control).** Local untracked files under
  `canonical_baseline/` are **not** canonical spec. The only implementation
  sources are the six docs, this frozen spec, the audit-bundle provenance
  files (evidence, not implementation sources), and the **whitelisted
  non-performance input artifacts** below. Everything else untracked under
  `canonical_baseline/` (`simlib.py`, `modeb_engine.py`, `run_portfolio.py`,
  `canonical_trades.json`, `portfolio_results.json`, data pickles, etc.)
  must **not** be opened, read, or consulted for any implementation choice:
  their provenance is unverified, and consulting them would be
  outcome-targeting through another channel, violating Mike's "never
  present a reconstruction as the record" directive.
- **Whitelist — non-performance input artifacts (may be read; SHA-256
  hashed before use, hashes recorded in the run log):**
  - `canonical_baseline/candidate_pool.json` — 272-name candidate pool.
  - `canonical_baseline/addv_ranking_20230930.json` — ADDV ranking
    (229 rankable; top-120 cutoff).
  - `canonical_baseline/addv_unrankable.json` — 43 unrankable names.
  - `canonical_baseline/new_listings_eval.json` — 15 post-cutoff listing
    candidates (11 admitted / 4 rejected).
  - `canonical_baseline/universe.json` — final 131-symbol universe
    (**check target** for the §5B independent reconstruction, never a
    check source).
  - `canonical_baseline/universe_overlay_14.json` — the 14-name overlay
    identities (6 non-universe outsiders) for the overlay reporting leg.
  - `canonical_baseline/coverage_report.json` — per-symbol
    `effective_4h_from`, expected/actual 4H bar counts, missing%, quality
    flags. Input-data manifest only.
  - The comparator file (`research_notes/
    CANONICAL_RECONSTRUCTION_SEALED_ORACLE_20260928.json`), opened only
    under the §12 discipline (after semantics frozen, code hash-locked,
    Run 1 complete, Layer-1 passed).
  - Rebuilt 4H/daily caches and the MTF archival pull are **outputs** of the
    rebuild per §11 provenance rules, not consulted sources.
  Provenance note: these files' construction is described in UNIVERSE.md;
  their byte-level provenance is unverified, which is why they are hashed
  before use and why every Layer-1 check re-derives the documented counts
  from them (a mismatch is a finding, never a patch license).
- **Live-code provenance for the transcribed signal logic (§2).** The six
  docs cite the live V5.4 implementation with file:line references. Tracked
  live files (`scanner_rules.py`, `masterscanner_api.py`) are pinned to the
  verifiable support commit `48579180d21fda07339fa9305d30828bffef0bc3`.
  Blob pins at 48579180 (verified locally): `masterscanner_api.py` →
  `6d8d6670fe89e7bc1c901816a18e7fff2a90dc00`; `scanner_rules.py` →
  `08dbcc519efc97425778cad83dc01fa07e7cb7f8`. Commit `48579180` is dated
  **2026-09-14T23:15:42Z** (verified locally). Independent compare of
  `4857918` through the canonical commit `368fa2e` shows **no changes**
  to `masterscanner_api.py` or `scanner_rules.py` (verified 2026-09-28);
  the pinned blobs are therefore valid for the whole canonical-doc
  window.
- **Authorship note (normalized per mandate):** the four redlines R1–R4
  were **authored by ChatGPT** and **adopted by Mike** (they are not Mike's
  authorship). ChatGPT's mechanical re-audit produced C1–C3; Mike's F1
  identified the MTF weekly-window impossibility. Nothing in this work
  modifies any live file; V5.4 production stays frozen.

---

## §2. Signal generator — FROZEN (B1)

The canonical baseline's signals are the frozen V5.4 classifier
(`v54_engine.v54_classify`, rule version `2026-09-15-v54`), all grades A/B/C,
strict PIT, no scores in any decision path (PORTFOLIO.md). The complete logic
is transcribed here so the rebuild does not depend on any uncommitted file;
basis notes classify each rule against the recovered bytes (Appendix P).

### §2.1 Historical adapter + decision/cycle-time semantics

- **Decision points.** For each universe symbol, every **completed** 4H bar
  close inside the symbol's eligible window is a signal-evaluation point
  (the backtest analog of live hourly cycles, which score the last completed
  bar each cycle — PIT_FEATURES.md).
- **Evaluation at decision point T (bar `i` close).** Run the full pipeline
  below on 4H bars `[0..i]` only, plus daily/weekly/15m context as of T per
  §4 and §2.8. A signal is **complete at signal-bar close**; its stamped
  timestamp is the bar-close wall time: **13:30 / 16:00 ET**, or **13:00 ET**
  on NYSE early-close days (A5). The fill price (next completed bar's open)
  is unknowable at signal time.
- **Forming-bar exclusion.** No 4H bar with `bar_close_at > T` may be read by
  any feature, indicator, or exit rule (`scanner_rules.py:86-88`, commit
  48579180).
- **Fill.** Paper entry fills at the **next completed 4H bar's open** after
  the signal bar; skipped if `entry ≤ stop` at fill time (gap-through-stop
  invalidation — PIT_FEATURES.md, ENGINE.md assumption 2). Pending-entry
  fills re-check `entry > stop` at fill; invalidated pendings release slot +
  heat (A2/A6).
- **Signal price on the record** = signal-bar close.
- Basis: DERIVABLE (PIT_FEATURES.md rules; the completed-bar predicate
  `signal_bar_is_closed` / `bar_close_at` is COPY from the tracked
  `scanner_rules.py` and `v54_rules.py` bytes).

### §2.2 Indicator math (all causal, closed bars only)

On 4H OHLCV (`masterscanner_api.add_indicators`):
- `EMA(l) = Close.ewm(span=l, adjust=False).mean()`; l ∈ {9, 21, 55, 200}.
- `ATR(14)`: true range = max(High−Low, |High−Close₁|, |Low−Close₁|);
  Wilder smoothing `ewm(alpha=1/14, adjust=False)`.
- `ADX(14)`: Wilder +DM/−DM smoothed `ewm(alpha=1/14, adjust=False)`,
  DX = 100·|+DI−(−DI)| / (|+DI| + |−DI|) (0/0 → NaN), then
  `ADX = DX.ewm(alpha=1/14, adjust=False)`.
- `VOL_BASE` = Volume.rolling(50).mean().
- **`VWAP` (M1 — FROZEN):** the 50-bar rolling VWAP on the rebuilt 4H
  series: `VWAP = (typical×vol).rolling(50).sum() / vol.rolling(50).sum()`
  with `typical = (High+Low+Close)/3` and `vol = Volume` with 0 → NaN
  (COPY of `rolling_vwap(df, 50)` in `masterscanner_api.py`, commit
  48579180). `above_vwap = (price > VWAP)` if VWAP is not NaN else `False`
  (COPY of `v54_engine.py`).
  **Label: JUDGMENT.** The tracked `add_indicators` prefers
  `SessionVWAP` when the column is present and uses rolling-50 only as
  fallback; the tracked `resample_closed_4h` defines SessionVWAP exactly
  (regular US session filter, cumulative session VWAP from typical price
  × volume, grouped by local session date, carried through the 4H
  resample at the 09:30 session offset). SessionVWAP is therefore
  **reconstructible in principle**: the underlying 1H OHLCV can support
  session-VWAP reconstruction, so the rolling-50 VWAP is a **JUDGMENT
  choice**, not a technical impossibility (the rev-5 phrase "unavailable
  by construction" is removed). The honest basis: the canonical
  historical 4H cache specification (UNIVERSE.md, §11) and the surviving
  evidence are OHLCV-oriented and do not uniquely establish that the
  historical reconstructed path used live SessionVWAP; the canonical
  cache specification freezes OHLCV-only bars, so the rebuild follows the
  tracked fallback (`rolling_vwap(df,50)`). **Disclosed sensitivity:** the
  choice can change `above_vwap`, Profit-Protect eligibility, and entry
  eligibility (VWAP is a hard-gate/protection input). The choice must not
  be revisited on Layer-2 fit. Live SessionVWAP remains the stronger
  live-path alternative.
- `rvol = Volume / VOL_BASE` (0 if VOL_BASE ≤ 0) — observational only.
- Triggers read index `i` (and `i−1` for crosses) only — never `i+1`.
- Constants: `FAST_EMA=21, SLOW_EMA=55, TREND_EMA=200, ACCEL_EMA=9`;
  `ADX_LEN=14, ATR_LEN=14, ATR_BASE_LEN=50, VOL_BASE_LEN=50, VWAP_LEN=50`;
  `ADX_MIN=18` (trigger-level), `HOT_ADX=30`,
  `PULLBACK_NEAR_EMA_PCT=2.5`, `HOT_EXTENSION_PCT=6.0`,
  `BUY_ZONE_ATR_WIDTH=0.45`, `STOP_ZONE_ATR_BUFFER=0.65`,
  `TP_ZONE_ATR_EXTENSION=2.50`, `MIN_ADX=20.0` (V5.4 hard gate).
  Basis: COPY (constants and `add_indicators`/`rolling_vwap` transcribed
  from `masterscanner_api.py` at commit 48579180 and the v54 bytes).

### §2.3 Structural contract — pure setup triggers (M3 resolved)

With `price=Close[i]`, `e9/e21/e55/e200` as above, `adx=ADX[i]`,
`vwap=VWAP[i]`, `atrv=ATR[i]`, all comparisons on numpy scalars coerced
with explicit `bool()` (D3):
- `trend_bull = price > e200`
- `ema_bull = e21 > e55`
- `accel_bull = e9 > e21`
- `fast_rising = EMA21[i] > EMA21[i-1]` (strict `>`); `accel_rising =
  EMA9[i] > EMA9[i-1]` (strict `>`)
- `fresh_buy = (e21[i] > e55[i]) and (e21[i-1] ≤ e55[i-1]) and trend_bull`
  (EMA21/55 bull cross)
- `early_buy = trend_bull and accel_bull and fast_rising and
  accel_rising and price > e21 and e21 ≤ e55×1.015` (state only — never
  entry-eligible)
- `pullback_buy = trend_bull and ema_bull and price ≥ e21 and
  |safe_pct(price,e21)| ≤ 2.5 and adx ≥ 18`,
  where `safe_pct(a,b) = 0 if b==0/NaN else (a−b)/b×100`
- `exit_signal = (price < e55) or (e21[i] < e55[i] and e21[i-1] ≥ e55[i-1])`
  (price under EMA55, or EMA21/55 bear cross)
- State: `EXIT` if exit_signal; `BUY` if fresh_buy; `PULLBACK BUY` if
  pullback_buy; `EARLY BUY` if early_buy; else `NEUTRAL`.
- Protection: `EXIT` if exit_signal; `LOCK GAINS` if hot/extended
  (`hot = trend_bull and ema_bull and adx ≥ 30 and extension ≥ 6.0`,
  `extension = safe_pct(price, e21)`); `SAFE` iff
  `trend_bull and ema_bull and price ≥ e21 and above_vwap`;
  `WARNING` iff `trend_bull and price < e21 and price > e55`; else `WARNING`.
- Zone: `zone_low = max(0, e21 − ATR×0.45)`, `zone_high = e21 + ATR×0.45`.
  The row serializes `buy_zone = f"{zone_low:.2f}-{zone_high:.2f}"`.
- **Entry `YES` iff** `state ∈ {BUY, PULLBACK BUY}` **and**
  `protection == "SAFE"` **and** `above_vwap` **and** `in_zone_raw`,
  where `in_zone_raw = (zone_low ≤ price ≤ zone_high)` on full-precision
  bounds. **The hard gate (§2.4) then re-checks the ROUNDED serialized
  zone** (`_inside_buy_zone` parses the `.2f` string — M3): a signal is
  eligible only if `price` is inside the rounded zone. Both steps are
  frozen; the rounded re-check can only narrow, never widen, eligibility.
  Basis: COPY (`v54_engine._pure_setup_triggers` / `v54_classify` and
  `scanner_rules._inside_buy_zone` at commit 48579180; no score appears in
  any condition — see §10/B9).

### §2.4 Hard gates (eligibility)

`v54_hard_gates_pass`: the §2.3 structural contract
(`entry=="YES"`, `protection=="SAFE"`, `state ∈ {BUY, PULLBACK BUY}`,
`above_vwap is True`, price inside the **rounded serialized** buy zone —
`scanner_rules.is_structural_candidate`, which parses
`buy_zone` via `_inside_buy_zone`) **plus** `ADX ≥ 20.0` evaluated at
signal bar `i`, never revised (`adx` coerced: non-numeric → 0.0 → gate
fails). Rows failing the gates are recorded as ineligible (grade None) —
they are not signals.
Basis: COPY (`v54_rules.v54_hard_gates_pass` bytes; the structural
contract it wraps is in the tracked `scanner_rules.is_structural_candidate`,
commit 48579180; ADX ≥ 20 is `MIN_ADX` in the bytes and the frozen handoff).

### §2.5 Stop / TP1 levels

`stop, tp1 = trade_levels(zone_low, zone_high, ATR)` on **full-precision**
(raw) zone bounds:
- `stop = max(0.0, zone_low − ATR × 0.65)`
- `tp1 = zone_high + ATR × 2.50`
Computed from **signal-bar** values only, never revised (PIT_FEATURES
rule 5). Basis: COPY (`scanner_rules.trade_levels`, commit 48579180;
called with raw bounds in `v54_engine.py`).

### §2.6 Grading inputs (actually used) + grade map — CORRECTED per bytes (R-1)

Grading consumes only these context fields — never raw dataframes
(`v54_rules.v54_grade`):
- `daily_trend`, `weekly_trend` ∈ {confirmed, not_confirmed, unknown}
  (§2.8).
- `market_gate` ∈ {BLOCK, CAUTION, CONFIRM, UNKNOWN} (§2.7).
- **Not grading inputs:** 15m confirmation and premarket — observational
  only, recorded on the signal record, never gating or grading (frozen
  spec; `v54_rules.py` docstring). No auxiliary input vetoes a signal:
  MTF/daily/weekly/15m/premarket/market-gate are grading context only.
  The only gates are §2.4.
- **No RISK-OFF veto in V5.4 (M4 — resolved by the bytes).** The legacy
  `classify_symbol` (V5.3 path, `masterscanner_api.py:269`, commit
  48579180) contains `if regime==RISK-OFF and entry==YES: entry=WATCH`.
  The V5.4 path does not: `v54_engine.v54_classify` re-derives
  state/entry/protection from pure triggers with no regime check, and
  `v54_rules.py`'s docstring explicitly states it "never imports the V5.3
  veto logic". The RISK-OFF→WATCH downgrade is recorded as **V5.3-only
  legacy behavior**, rejected for V5.4. (D5 includes a RISK-OFF-context
  fixture proving the veto's absence.)
- **Grade map — literal precedence from the bytes (R-1):**
  1. Hard gates fail → ineligible (grade None).
  2. Else if `(daily==confirmed and weekly==confirmed) or
     gate==CONFIRM` → **B** (CONFIRMED).
  3. Else if `daily==unknown or weekly==unknown or gate==UNKNOWN`
     (i.e. not context_known) → **C** (OBSERVATION).
  4. Else → **A** (EARLY).
  Consequences: `unknown` MTF **never yields A**; it yields **B** iff the
  market gate is CONFIRM (step 2 runs first), otherwise **C**. A CONFIRM
  gate yields B whenever daily/weekly context is known — even when the
  MTF pair is not both-confirmed. The handoff's "weaker" (as distinct from
  "unknown") has no deterministic definition and currently grades A —
  flagged, not invented (standing memory 2026-09-15).
  **Supersedes:** rev 4's unknown-first order (ChatGPT C1, adopted by Mike
  without the bytes) — see Appendix R.
  Basis: COPY (`v54_rules.v54_grade` bytes; the B-first order with
  `or gate==CONFIRM` matches the frozen handoff brief verbatim:
  "Daily+Weekly both aligned and/or market CONFIRM").
- **Grading-only vs portfolio acceptance (non-blocking correction).** The
  frozen spec grades every qualified signal A/B/C and logs all of them
  ("every hard-gate-qualified signal is logged, including C" — handoff;
  `v54_qualified_signals` keeps every eligible row). Grades are
  informational and never veto. The canonical portfolio accepts **all
  grades A/B/C** (PORTFOLIO.md: "all grades A/B/C"). No grading-only
  component (MTF state, market gate/regime, 15m, premarket, RVOL, R:R)
  affects portfolio acceptance. Per the `v54_rules.py` docstring, no
  signal may be demoted to C on accumulated soft negatives (BLOCK + low
  RVOL + mediocre R:R, etc.): C represents grading uncertainty, not a
  soft-penalty bucket.

### §2.7 Market gate computation (grading context)

On QQQ closed 4H bars at decision time T (timestamped, never backfilled —
PIT_FEATURES rule 7; morning-cycle staleness is correct behavior):
- `score = 35×(Close>EMA200) + 35×(EMA21>EMA55) + 15×(EMA21 rising) +
  15×(Close>EMA21)` (max 100).
- `_session_return = safe_pct(last closed bar Close, prior date's last
  closed bar Close)` for QQQ and SPY.
- `gate = BLOCK` if `qqq_ret ≤ −0.75` or
  (`qqq_ret ≤ −0.40` and `spy_ret ≤ −0.40`); `CAUTION` if `qqq_ret < 0` or
  `spy_ret < 0` or `score < 75`; else `CONFIRM`.
- `regime = RISK-ON (score≥75) / CAUTIOUS (≥50) / RISK-OFF`.
- If QQQ 4H history < 205 bars: `regime UNKNOWN, gate BLOCK`
  (`get_market_regime` returns
  `{"regime": "UNKNOWN", "risk_on": False, "score": 0, "gate": "BLOCK"}`).
  **Corrected (non-blocking):** QQQ 4H warmup **can** be < 205 bars early
  in the sample (the 4H cache starts ≈ 2023-10-26; 205 4H bars ≈ 103
  trading days, so the sub-205 window runs into Q1 2024). During that
  window the frozen rule above applies mechanically — it is not a corner
  case to hand-wave.
  Basis: COPY (`masterscanner_api.get_market_regime`, commit 48579180).

### §2.8 MTF trend states (grading context)

`confirmed | not_confirmed | unknown` per timeframe
(`v54_engine._v54_trend_state` + `scanner_rules.timeframe_trend_confirmed`,
`closed_higher_timeframe`):
- Drop the unfinished bar first (`closed_higher_timeframe` with now=T):
  today's daily bar before **16:00 ET** (no early-close exception in the
  tracked helper — see §4 reconciliation); the unfinished weekly bar
  (week ends Friday 16:00 ET).
- `df` None/empty or < 205 completed bars → `unknown`.
- Else `confirmed` iff `Close > EMA200 and EMA21 > EMA55 and EMA21 rising`
  with EMAs = `Close.ewm(span, adjust=False).mean()` on timeframe closes
  and **EMA21 rising frozen as `>=`** (`ema21[-1] >= ema21[-2]`, matching
  the tracked code); else `not_confirmed`.
- (The wrapper trims for the 205-count, then `timeframe_trend_confirmed`
  trims again internally and applies the rule — redundant but harmless;
  frozen as written.)
- `unknown` grading consequence: per the §2.6 precedence, unknown MTF
  yields **B** iff the market gate is CONFIRM, otherwise **C**; it never
  yields A. Missing auxiliary input is **never gating** — it is grading
  context only.
  Basis: COPY (tracked `scanner_rules.py:217-260`, commit 48579180; the
  confirmed/not_confirmed/unknown labeling wrapper
  `v54_engine._v54_trend_state` bytes).

---

## §3. Warmup / first signal-eligible bar — FROZEN (B2)

- **Indicator seeding horizon (M2 — FROZEN).** Indicators are computed
  causally from each symbol's **`first_available_4h_bar`** (first actual
  bar in the fetched series) — never from `effective_4h_from`.
  `ewm(adjust=False)` needs no explicit seed bars; the `min_bars` gate
  below provides stability. Warmup bars are for indicator seeding only,
  never for signal evaluation (PIT_FEATURES rule 6). Pre-`effective_4h_from`
  bars are NOT sliced away before warmup.
  **Label: JUDGMENT.** **Recorded alternative (not chosen):** the
  live-faithful finite window — `v54_scan_symbols` defaults to
  `period="180d"`, so live 4H indicator frames were trailing-180d windows,
  not all-history. The all-history choice is frozen for deterministic
  reconstruction; freezing a finite window would require inventing a
  window convention the historical backtest may not have used. No claim
  is made that PIT_FEATURES specifies full-cache seeding — it establishes
  the warmup/seeding need, not this exact resolution (rev-5's "205-bar
  gate dominates seed sensitivity" claim is removed as inaccurate).
  **Disclosed sensitivity:** with pandas `ewm(span=200, adjust=False)`,
  the first observation retains ≈13% weight at bar 205
  (`(1−2/201)^204`) and ≈8% around bar 250; all-history seeding can
  therefore materially differ from a finite live window early in the
  sample, with downstream sensitivity in EMA200 and `trend_bull`. The
  choice must not be revisited on Layer-2 fit.
- **Per-symbol minimum.** `v54_classify` returns None unless the 4H frame
  holds `min_bars = max(TREND_EMA, ATR_BASE_LEN, VOL_BASE_LEN, VWAP_LEN) + 5
  = 205` bars. The 205-bar count runs on the raw series. Basis: COPY
  (v54 bytes; constants COPY from `masterscanner_api.py`).
- **`effective_4h_from` is an eligibility floor, not the data start.**
  UNIVERSE.md: "backtests should use `max(eligible_from,
  effective_4h_from)`." The raw 4H series may begin earlier (e.g.
  GEV/RDDT/TEM: raw 4H from 2024-09-26, but `effective_4h_from` = their
  60th 4H bar ≈ 2024-11-07, recorded per-symbol in
  `coverage_report.json`). Signal evaluation is floored at
  `effective_4h_from`; indicator seeding is not.
- **First signal-eligible bar (operational).** For each symbol, the earliest
  4H bar at which a signal may be evaluated is the earliest bar satisfying
  ALL of: (a) ≥205 bars of that symbol's raw 4H history exist through it;
  (b) its timestamp ≥ universe `eligible_from` (UNIVERSE.md);
  (c) its timestamp ≥ `effective_4h_from` (coverage_report.json).
- **ARM / new-listing ambiguity — RESOLVED.** The 30-trading-day
  (≈60 4H bars) post-listing rule governs *universe eligibility*
  (UNIVERSE.md step 5); the 205-bar rule governs *signal eligibility*.
  Both apply; the later binds. For ARM (4H series starts 2023-10-26 per the
  Yahoo 1H cap): the binding constraint is the 205-bar warmup, so ARM's
  first signal-eligible bar is its 205th 4H bar (≈ late March 2024), not
  30 trading days after its 2023-09-14 IPO. Same logic for all 11 admitted
  new listings (BMNR, CRWV, DRAM, GEV, GLXY, NBIS, RDDT, SNDK, SPCX, TEM).
  Basis: DERIVABLE (`v54_classify` min_bars + UNIVERSE.md eligibility).

---

## §4. Daily-bar availability — FROZEN (B3), reconciled with §2.8 helper

- A daily bar dated D becomes **available** at the actual regular-session
  close: **16:00 ET** (or **13:00 ET** on NYSE early-close days). Midnight
  date labels are never availability timestamps.
- At decision point T, usable daily bars are those with date < T.date(),
  plus date == T.date() only if T ≥ that date's session close.
  Consequences (PIT_FEATURES rule 2): a 13:30-close signal bar uses
  **yesterday's** daily bar as the latest daily input; a 16:00-close signal
  bar may use today's (session complete); a 13:00 early-close signal bar
  may use today's.
- **Reconciliation with the §2.8 MTF helper (non-blocking correction).**
  The tracked `closed_higher_timeframe` helper — which governs the **MTF
  daily trend read only** — drops today's daily bar whenever T < 16:00 ET,
  with **no early-close exception** in the tracked code. Both rules are
  frozen: the MTF trend read follows the helper literally (on an
  early-close day, the 13:00 ET decision still excludes that day's daily
  bar from the MTF read), while §4's 13:00 early-close availability governs
  daily inputs consumed **outside** the MTF helper (rs_top2 SPY leg,
  regime join, sector work). The helper takes precedence for MTF; neither
  rule is "fixed" to match the other.
- Applies to every daily-resolution input consumed **outside** the MTF
  helper: rs_top2 SPY leg, regime join, sector work. The MTF daily trend
  read follows `closed_higher_timeframe` literally (see reconciliation
  above), not this §4 availability rule. Basis: EXPLICIT (PIT_FEATURES
  rules 2, 8) + COPY (helper semantics, `scanner_rules.py:217-244`).

---

## §5. Layer-1 comparator — PRE-RUN structural/specification checks (visible)

Rewritten per mandate (non-blocking correction): **§5A checks source-input
integrity; §5B runs consistency checks — it reconstructs what the docs
describe from frozen inputs and checks the prebuilt artifacts as targets,
never as sources.** §5B is a consistency check, not an independent
ranking: it consumes whitelisted input artifacts (e.g. the documented
ranking inputs) and compares the documented reconstruction outputs to
their targets. Nothing in §5
consults outcomes or the comparator file.

### §5A. Source-input integrity (no reconstruction)

Each whitelisted input artifact (§1) is present, its SHA-256 is recorded in
the run log, and its documented internal counts are exact:
- `candidate_pool.json`: **272** names exact.
- `addv_ranking_20230930.json`: **229** rankable in the 2023-06-30→2023-09-30
  ADDV window; `addv_unrankable.json`: **43** unrankable. 229 + 43 = 272.
- Top-120 cutoff: #120 DVN ≈ $375.7M/day, #121 DAL ≈ $373.2M/day (±2% on
  dollar values; identities exact).
- `new_listings_eval.json`: **15** post-cutoff listing candidates;
  **11** admitted (ARM, BMNR, CRWV, DRAM, GEV, GLXY, NBIS, RDDT, SNDK, SPCX,
  TEM); **4** rejected (CORZ, NNE, RBRK, UMAC) — identities exact.
- `coverage_report.json`: per-symbol `effective_4h_from`, expected/actual
  4H bar counts, missing%, quality flags present for every universe symbol.
- `universe_overlay_14.json`: 14 identities, of which 6 are non-universe
  outsiders (overlay reporting leg only).

### §5B. Consistency checks (prebuilt files are targets)

- **Universe reconstruction.** Starting from the §5A inputs and the
  UNIVERSE.md documented steps (ADDV ranking → top-120 cutoff → new-listing
  admissions per `new_listings_eval.json`), independently rebuild the
  131-symbol universe. The reconstruction must equal the identities in
  `universe.json` **exactly** — `universe.json` is the check target, never
  an input to the reconstruction. Any identity divergence is a finding;
  stop.
- **4H cache construction.** Rebuild the 4H cache per §11 (137 symbols =
  131 universe + 6 overlay outsiders). Check against
  `coverage_report.json`'s expected bar counts (tolerance: documented
  missing-bar exceptions only): effective 4H history ≈ 2023-10-26→2026-09-24
  (start within ±5 trading days; any divergence recorded with cause);
  session labels 09:30 / 13:30 ET; exactly one bar on NYSE early-close
  days.
- **Known Yahoo missing-bar exceptions** (documented, not calendar errors):
  single 4H bar on full trading days **2026-01-30** and **2026-02-02**
  (market-wide 1H gap, visible in AAPL); early-close single-bar days
  2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28,
  2025-12-24 (UNIVERSE.md).

### §5C. Rule parameters and frozen conventions (not outcomes)

- Max concurrent open positions: **6** (rule parameter, PORTFOLIO.md).
- **Mixed return bases recorded:** rs_top2 symbol leg uses 4H closes from
  split-adjusted (not dividend-adjusted) intraday bars; the SPY daily leg
  uses split- **and** dividend-adjusted daily closes (AdjClose/Close
  scaling). The resulting small systematic basis difference is a known,
  frozen imperfection — not a defect to "fix" mid-run.
- **Headline gap convention: `realistic_gaps=False`** (live-faithful:
  stop filled AT the stop on gap-through bars — optimistic, quantified at
  ≈ −0.04R vs realistic; TP1 filled AT the TP1 level on gap-through —
  conservative. ENGINE.md assumptions 5–8.)

---

## §6. Layer-2 comparator — POST-RUN checks (unblinded)

The historical outcomes below live in
`research_notes/CANONICAL_RECONSTRUCTION_SEALED_ORACLE_20260928.json`
(legacy filename — see §15; no blinding meaning).
The builder works **unblinded** (§0): the file's SHA-256 (§15) is an
integrity commitment to its bytes, not a blinding device. It is opened
only **after** the implementation semantics are frozen (§2–§4, §7–§8),
the code is hash-locked (§10), Run 1 completes, and Layer-1 (§5) passes —
not to preserve blinding (impossible here) but to enforce the
no-targeting process order: semantics first, comparison after.

Frozen tolerances (all must be met; any miss is a finding, never tuning
permission):
- Backtest decision counts: raw candidates **4,127** exact; skip funnel **622**
  busy / **744** slot-rank / **2,387** heat / **374** accepted exact; max concurrent
  **6** exact; open at sample end **6** exact.
- Headline E: −0.0013 ± 0.05 R/trade; win 39.8% ± 3pp; PF 1.00 ± 0.10.
- Max DD: −40.7R ± 10R; total return negative and |return| < 5%.
- Cost ladder strictly decreasing in cost (25bps E > 50bps E > 75bps E > 100bps E),
  each rung within ±0.05R of documented value.
- Year splits: 2024 E < 0 < 2025 E and 2024 E < 0 < 2026 E; each within ±0.10R.
- Concentration: ≥6 of the 10 documented top-trade identities appear in the
  rebuild's top-15 trades by R.
- 14-name overlay: n = 151 exact; E within ±0.10R of +0.4489; PF within ±0.15.

---

## §7. The seven ambiguities — FROZEN (reconciled per Claude audit)

Basis codes: EXPLICIT = pinned by surviving docs; DERIVABLE = follows from an
explicit rule with no meaningful discretion; JUDGMENT = frozen choice, recorded
as such, never revisited after the run; COPY = verbatim from the recovered
v54 bytes or the pinned tracked code.

### A1. Heat numerator after partial TP1 — FROZEN
`heat_dollars = Σ_pending(750) + Σ_open(actual_risk_dollars)`,
`heat = heat_dollars / E_mark(T)`, where for an open position
`actual_risk_dollars = remaining_shares × (entry − stop)` and `E_mark(T)` is
the §7/A6 snapshot. After the 50% TP1 scale-out, the position contributes
only its runner's risk. Odd-share split (B4): `tp1_shares = shares // 2`
(floor), `runner_shares = shares − tp1_shares`; the runner's remaining risk
uses `runner_shares`.
Basis: JUDGMENT (odd-share floor-split frozen per Claude B4).

### A2. Pending-entry reservation — FROZEN
An accepted signal reserves one slot and its $750 planned risk in heat from
the decision timestamp (signal-bar close) until fill or invalidation. A
pending entry makes its symbol busy. A new signal on a pending symbol is
busy-skipped. **Reservation→actual transition (B4):** at fill, the $750
reservation converts to actual risk `shares × (entry_fill − stop)`; any
difference is released back to heat capacity immediately. Pending entries
from prior bars already occupy slot + heat before the A3 batch.
Basis: JUDGMENT.

### A3. Same-timestamp evaluation sequence — FROZEN
At each signal-bar close, process that bar's candidate batch in this order:
1. Drop busy symbols (open or pending).
2. If survivors exceed free slots, rank by rs_top2 and keep the top-N by
   (rs_top2 desc, signal timestamp, symbol asc).
3. Heat check in that same rank order, first-fit: accept candidate k iff
   `(heat_dollars + 750) / E_mark(T) ≤ 0.05`; the rest are heat-skipped.
   Heat arithmetic is unambiguous: dollar sums over dollar equity, compared
   `≤ 5%` (Claude reconciliation).
Pending entries from prior bars already occupy their slot and heat before step 1.
Basis: JUDGMENT.

### A4. rs_top2 benchmark formula — FROZEN
`rs_top2 = (symbol 20-bar 4H return) − (SPY 20-bar daily return)`, where:
- symbol leg = `Close4H[i] / Close4H[i−20] − 1` over the 20 closed 4H bars
  ending at signal bar `i` (strict PIT — no bar with timestamp > signal-bar
  close);
- SPY leg = return over the **20 completed SPY daily bars** ending at the
  last completed daily SPY bar with timestamp ≤ signal-bar close per §4
  (strict PIT; daily-bar availability by session close, not midnight label).
Ranked at signal bar `i`. Signals with fewer than 20 closed 4H bars are
unrankable and sort last. Ties broken by signal timestamp, then symbol asc.
Entry unaffected (next-bar open).
**Relabeled JUDGMENT per Claude reconciliation** (was "EXPLICIT in prose" in
rev 3): the surviving docs admit conflicting readings — PIT_FEATURES
pins the symbol leg (20 closed 4H bars) and the SPY-leg *endpoint* (last
completed daily bar ≤ signal-bar close), but the 20-daily-bar *lookback*
is a frozen choice, and the live path's own RS (20 closed 4H bars vs QQQ,
score use only) is a different definition that must not be mixed in
(PIT_FEATURES rule 11). The formula above is kept unless a stronger
surviving source appears.
Basis: JUDGMENT.

### A5. Early-close availability timestamp — FROZEN
The single 09:30 bar on NYSE early-close days becomes available at **13:00 ET**
actual (session-local close). Signals evaluated on it carry bar-close timestamp
13:00 ET. **Recorded alternative:** a live half-day 13:30 stamping
interpretation exists in the clock-convention discussion; it is **rejected**
in favor of the 13:00 exchange-close convention (NYSE calendar semantics).
**Identity convention for D4/D6:** identity keys on half-days use the
13:00 ET decision-availability timestamp (frozen serialization); the
tracked `bar_close_at` 13:30 half-day behavior is a separate tracked
detail and must not cause false D4/D6 mismatch.
Basis: JUDGMENT.

### A6. Marked-equity / event ordering — FROZEN (completed per B5)

**At each 4H bar close** (bar `i` completes at timestamp T), process in this order:
1. Finalize the Mode B engine for bar `i` — all intrabar events (stop, TP1,
   Profit-Protect arming, timeout scheduling) are engine-internal; each leg's
   cost deducted immediately at its event. **Exits realized in bar `i` free
   the symbol's busy status for the same-T signal batch below** (B5 — frozen
   explicitly: a close exit does free same-T busy).
2. **Snapshot:** `E_mark(T) = cash(T) + Σ_open(remaining_shares × close_i)`,
   where `cash(T)` starts at $75,000 and reflects every fill and every
   leg-cost deducted through bar `i`'s close, and `remaining_shares` is the
   position's shares still held at T (post-TP1: the runner's shares only —
   corrected per mandate; the TP1 leg's proceeds are in `cash(T)`).
   This snapshot is the heat denominator for every decision stamped T and
   is never recomputed within T.
   **Missing-bar rule (frozen 2026-09-28):** a symbol with no bar at T
   receives **no Mode-B processing at T** — no stop/TP1/Profit-Protect/EXIT
   evaluation, no signal detection, and its 30-bar timeout clock does not
   increment (`bars_held` counts processed bars only; entry bar = #1 per
   ENGINE.md). The stale last-available close is used **only** for the
   equity-marking snapshot `E_mark(T)` (flagged stale in outputs); it never
   generates fills, signals, or timeout progress. A missing bar never blocks
   the run.
3. **New-signal batch evaluation:** run signal detection on completed bar `i`,
   then the A3 batch competition (busy → rank → heat first-fit) using
   `E_mark(T)` and slots freed by exits realized in bar `i`; pending entries
   from prior bars already occupy slot + heat.
4. Accepted signals become pending entries (reserve slot + $750 heat) stamped T.

**At each 4H bar open** (bar `i+1`):
1. Engine-scheduled fills execute first (e.g. armed Profit-Protect exits),
   symbol-asc; each leg's cost deducted immediately.
2. Pending-entry fills execute in rank order; re-check the entry > stop
   invalidation at fill time. Entry-leg cost deducted immediately. Invalidated
   pendings release their slot + heat reservation.
3. No equity marking at opens (marks happen only at closes, step 2 above).

Costs are deducted at the leg's event, never batched or deferred.
**Gap-above-target accounting (B5):** entry bar opens at/above TP1 →
immediate close at entry price, `blended_r = 0.0`, `bars_held = 0`, reason
`GAP_ABOVE_TARGET` (ENGINE.md); both legs' costs deducted (entry full-size
leg + exit full-size leg = 2 leg-equivalents → `cost_$ = bps × entry
notional`).
Basis: JUDGMENT (explicit close/open split + `E_mark(T)` snapshot; B5
completions frozen per Claude).

### A7. Rounding / P&L / costs outside Mode B — FROZEN (completed per B4)
- No intermediate rounding **except the frozen buy-zone serialization**:
  `buy_zone = f"{zone_low:.2f}-{zone_high:.2f}"`, and the §2.4 hard gate
  parses that rounded string (M3 — COPY). `shares = floor(750 /
  (entry − stop))` (integer). `shares == 0` (stop wider than $750 risk) →
  signal skipped, logged as `zero-share skip`; no trade. (Entry ≤ stop →
  invalid skip, §2.1.)
- Dollar P&L is computed from **full-precision (unrounded) prices** and
  actual share counts. R multiples round to 4dp and dollars to 2dp **only
  at write time** (ENGINE.md `_round4` convention; live stores raw while open).
- **Net-R / cost denominator (B4):** `cost_$ = (bps/2) × Σ leg notionals`
  (entry = full-size leg at entry price; TP1 = half-size leg at TP1 price;
  runner = half-size leg — or full-size leg if no TP1 — at runner exit
  price; PORTFOLIO.md). `R_net(trade) = (gross_$_pnl − cost_$) /
  planned_risk_$`, where `planned_risk_$ = shares × (entry − stop)`.
  Headline expectancy E = mean `R_net` over accepted trades.
- Blended-R convention (gross): full-position exits report R on the full
  position; post-TP1 runner exits report
  `(tp1_shares×R(tp1) + runner_shares×R(runner_exit)) / shares`
  (ENGINE.md §2, generalized to the B4 odd-share split).
Basis: JUDGMENT, except the buy-zone serialization which is COPY (M3).

---

## §8. Scanner EXIT — FROZEN (B7)

- **Definition.** `exit_signal = (Close_i < EMA55_i) or
  (EMA21_i < EMA55_i and EMA21_{i-1} ≥ EMA55_{i-1})`
  (price under EMA55, or EMA21/55 bear cross — §2.3).
- **Price input:** 4H close of the completed bar `i`.
- **EMA construction/seeding:** `ewm(span, adjust=False)` on 4H closes,
  causal from the symbol's series start; the §3 205-bar gate covers
  seeding stability (55-bar EMA needs no separate warmup rule).
- **Bar timing:** evaluated at completed-bar close; the scanner EXIT sets a
  pending exit **only if Profit Protect is already armed**; the pending exit
  fills at the **next bar's open** and takes precedence over stop/TP1/EXIT
  evaluation on the fill bar (ENGINE.md assumptions 9, 13).
- In `classify`, `exit_signal` also sets protection/state EXIT, but the
  backtest consumes scanner EXIT **only** through the PP-armed pending-exit
  path above.
  Basis: COPY (ENGINE.md §1/§3; the trigger phrasing matches
  `v54_engine._pure_setup_triggers` bytes).

---

## §9. No-targeting + unblinded-replication process controls (owner directive)

- The old 143-trade C1 numbers (+0.337R/trade, +52.25%, ~31.63% DD) are
  **banned from validation** — compromised selected-sample evidence (numpy
  boolean trendScore bug, owner ruling 2026-09-28). They must not appear as
  targets, gates, or tie-breakers anywhere in the rebuild.
- The numpy-boolean trendScore bug must NOT be reintroduced. Canonical V5 is
  the V5.4 structural-contract path (no scores), per REBASELINE/PORTFOLIO.
  Gate D proves its absence (§10).
- **No historical outcome — Layer-1 or Layer-2 — was used to choose among
  the §7 resolutions.** Each records its basis. If a basis is later shown
  wrong by a surviving document, the correction is recorded as a finding;
  the run is not re-tuned. (The M1/M2 JUDGMENT labels and the recorded
  rejected alternatives exist precisely so a stronger source can overturn
  them through the finding process — never through Layer-2 fit.)
- **Untracked-file quarantine** (§1): no implementation choice may be
  sourced from, or validated against, the untracked
  `canonical_baseline/` implementation/data files.
- **Comparator discipline:** the §6 comparator file is opened only after
  semantics are frozen (§2–§4, §7–§8), code is hash-locked (§10), Run 1
  completes, and Layer-1 passes. Any mismatch analysis cannot change
  implementation semantics unless it maps to a pre-existing frozen rule
  and independent review approves the fix (B8).

---

## §10. Bug-fix / rerun governance + Gate-D trendScore-absence test

**B8 — replaces "execute once":**
1. Before Run 1: SHA-256 hash-lock this frozen spec, the six docs, all
   rebuild code, and the cache manifest. Record the hashes in the run log.
2. Exactly one locked Run 1 per stage; outputs written once.
3. Any post-Run-1 code change must (a) cite the frozen rule/invariant it
   restores, (b) be independently reviewed (ChatGPT or Claude) **before**
   any rerun, and (c) leave both Run 1 and rerun outputs retained and
   reported. **No result-driven semantic changes**: a change motivated by
   a Layer-2 miss is forbidden unless it maps to a pre-existing frozen
   rule and passes (b).
4. A failed gate stops the rebuild (record cause; do not adjust rules to
   force a pass).

**B9 — Gate D (runs before the portfolio sim): the rebuild must prove the
historical numpy trendScore bug / score-based mirror logic is absent from
both signal eligibility and contested-slot portfolio selection.**
D1/D2 are **supplementary guards only — not proof**. Proof is D4 + D5
(eligibility) + D6 (selection).

- **D1 (static, supplementary):** the rebuilt signal module contains no
  reference to legacy per-symbol score fields — `trendScore`,
  `rank_score`, or per-symbol `score` — in any entry-decision path
  (mechanical grep assertion over the rebuild tree; such fields may exist
  as logged-only columns, never as conditions). **Carve-out:** the
  market-regime score (§2.7 — the QQQ 0–100 score used only for
  BLOCK/CAUTION/CONFIRM gate computation, a grading-context input) is a
  legitimate frozen input and is explicitly excluded from this ban.
- **D2 (behavioral, supplementary):** entry YES/NO decisions are invariant
  to legacy score perturbation — re-run signal generation with all logged
  legacy per-symbol score fields randomized/shuffled; the accepted-signal
  set must be byte-identical. The market-regime score is excluded from the
  perturbation (frozen grading-context input, not an entry input).
  Rationale for supplementary status: shuffling logged columns cannot
  detect internally recomputed score dependence (accepted M6 finding).
- **D3 (bug-class):** all trigger conditions coerce numpy scalars with
  explicit `bool()` on scalar comparisons; no bare numpy boolean arrays
  appear in conditionals (the historical bug class: numpy-boolean
  `trendScore` silently altering entry selection).
- **D4 (differential oracle — proof):** a minimal independent implementation
  of the frozen structural entry contract (§2.3 + §2.4: pure triggers →
  protection → state → entry → hard gates incl. the rounded-zone re-check
  and ADX ≥ 20, plus the completed-bar rule) must produce the **identical
  eligible signal identity set** — `{(symbol, signal_bar_close)}` —
  **across every evaluated bar** in the reconstruction window.
  Independence requirements: written solely from this spec (no imports
  from the rebuild tree, `scanner_rules`, `masterscanner_api`, or the v54
  files); contains no score computation of any kind; consumes the
  rebuild's frozen indicator frame as input (isolating the trigger/gate
  logic from indicator math). Any divergence in the identity set fails
  Gate D and stops the rebuild. **Scope (frozen):** D4 evaluates exactly
  the rebuild's decision points — every completed 4H bar close inside the
  symbol's eligible window (§2.1) — after the §3 eligibility floor (bars
  before a symbol's first signal-eligible bar are not evaluated).
  **Identity serialization (frozen, A5):** identity keys use the A5
  decision-availability timestamp — on NYSE early-close days the 09:30
  bar's key is `13:00 ET`, not 13:30. This convention must be explicit in
  both the rebuild and the oracle to avoid false mismatch against the
  tracked `bar_close_at` 13:30 half-day behavior (decision semantics
  remain the actual early close; only the identity serialization is
  frozen).
- **D5 (synthetic anti-score fixtures — proof):** deterministic synthetic
  4H OHLCV fixtures (≥210 bars each; generator + fixtures committed before
  the run) satisfying **every** frozen structural/hard-gate condition
  while deliberately producing **low legacy score components**
  (`volume_score=0` via rvol<1.10, `rs_score=0` via 20-bar RS vs QQQ ≤ 0,
  `risk_score=−10` via RISK-OFF regime, minimal momentum). **Twin
  perturbation (frozen):** each fixture's high-score twin applies a
  **last-bar-only volume transformation** (plus a frozen RS-leg flip and
  regime flip) that genuinely moves the legacy score components — e.g.
  last-bar volume scaled so rvol crosses the legacy 1.10 threshold
  (0.8 → ≥1.5) while all earlier bars are byte-identical. A uniform
  whole-series volume×3 twin is **forbidden**: it leaves rvol invariant
  and therefore does not test the intended anti-score condition. The
  committed generator **asserts per fixture/twin pair** that the intended
  structural inputs are unchanged: rolling-50 VWAP within a frozen
  tolerance, EMA21/55 cross identity unchanged, `above_vwap` unchanged,
  zone membership unchanged, and the 20-bar RS **symbol leg** trigger
  geometry unchanged (only the RS-leg comparison value and regime context
  may differ). Entry/eligibility decisions must be **identical** between
  fixture and twin, and every fixture must be **eligible** under the
  rebuilt V5.4 contract:
  - **D5-a (PULLBACK, sub-legacy-threshold):** pullback_buy + ADX ≥ 20 +
    SAFE + in-zone + above_vwap(rolling-50), with EMA21 ticking down
    (`fast_rising` False → legacy `trend_score`=60), rvol=0.8, RS≤0,
    RISK-OFF, e9≤e21 flat (momentum=10). Legacy score = 60+10+0+0−10 = 60
    **< 65** → legacy `classify_symbol` would NOT emit PULLBACK BUY.
    Rebuild must mark eligible.
  - **D5-b (BUY, RISK-OFF veto contrast — M4 case):** fresh EMA21/55 cross
    + all hard gates, regime=RISK-OFF (injected context: daily=confirmed,
    weekly=confirmed, gate=BLOCK). Legacy forces entry→WATCH via the
    RISK-OFF veto (`masterscanner_api.py:269`); V5.4 has no such veto
    (§2.6/M4). Rebuild must mark entry YES and eligible.
  - **D5-c (BUY, zeroed legacy discretionary components — anti-score
    contrast, not a threshold test):** fresh cross via EMA55-decline
    (`fast_rising` False) + all hard gates, rvol=0.8, RS≤0, RISK-OFF,
    e9≤e21. Legacy score = 60 (every discretionary component zeroed).
    Rebuild must mark eligible, identically to its high-score twin.
    (D5-c is **not** a "minimal score" threshold test: under the frozen
    hard gates there is no score threshold in the rebuild's entry path;
    D5-c demonstrates entry invariance to zeroing every legacy
    discretionary component.)
- **D6 (independent portfolio-selection differential oracle — proof):**
  D4/D5 prove eligible-signal *identity* is independent of legacy score /
  regime logic; D6 proves **contested-slot portfolio selection** (the A3
  admission sequence + A4 ranking) is likewise independent. D6 must:
  1. Consume the rebuild's **pre-portfolio eligible candidate stream** at
     every decision T (the A3 step-1 input: post-busy-drop candidates with
     their frozen features).
  2. Independently recompute A4 ranking from frozen inputs/formula only:
     symbol 20 completed-4H-bar return; minus SPY 20 completed-daily-bar
     return ending at the last daily bar available by T (§4); unrankable
     last; frozen deterministic tie-break (rs_top2 desc, signal timestamp,
     symbol asc).
  3. Independently replay the A3 portfolio admission sequence at each T:
     same-T exits / busy state as frozen; rank top-N / rs_top2; slot
     availability; first-fit heat check against the frozen 5% rule and the
     §7/A6 `E_mark` semantics (including pending-entry reservation);
     fully deterministic ordering.
  4. Compare the independent result with the rebuild **at every evaluated
     decision point**: ranked order of competing eligible candidates;
     busy rejections; slot-rank rejections; heat rejections; accepted
     candidate identities/order.
  5. Require byte-/identity-equivalent outcomes under a frozen canonical
     serialization (same serialization discipline as D4; half-day
     identity keys use the frozen A5 13:00 ET convention).
  6. **Independence:** the D6 implementation must not import/call the
     rebuild's ranking/portfolio-selection implementation and must not
     read legacy `score`, `rank_score`, regime veto/grade fields, or
     Layer-2 outcome metrics.
  7. **Synthetic contested-slot fixtures:** deterministic fixtures where a
     deliberately injected legacy score/`rank_score` ordering
     **conflicts** with the A4 RS ordering at a contested decision point.
     D6 must still reproduce A4/A3 exactly, and must **fail** if portfolio
     selection changes to the injected legacy-score ordering (the fixture
     is a trap: a selection implementation that consulted legacy scores
     would diverge and be caught).
- Gate D (D1–D6) must pass before any portfolio simulation may run.
  A D4/D5/D6 divergence or D5 ineligibility is a finding and stops
  the rebuild — it is never patched by adjusting the fixtures.

---

## §11. Provenance / data rules

- Daily cache: yfinance, window 2023-06-01→2026-09-24, `auto_adjust=False`,
  OHLC scaled by AdjClose/Close, raw Volume, America/New_York.
- 4H cache: yfinance 1H source, regular US session only, explicit per-session
  wall-clock aggregation (09:30–13:30, 13:30–16:00 ET), OHLCV first/max/min/last/sum,
  session-local DST-safe construction, one bar on early closes. Do NOT reuse the
  production `resample_closed_4h` global-resample behavior (which carries
  SessionVWAP — unavailable to the rebuild by construction, §2.2/M1).
- **MTF-context historical adapter (F1, frozen 2026-09-28, Mike).**
  MTF daily/weekly context is **separate from the general daily cache**
  above. The tracked live path fetched MTF context per decision as
  `download_confirmation_data(symbol, "1d", "2y")` and
  `download_confirmation_data(symbol, "1wk", "5y")`
  (`masterscanner_api.py:297-303`, commit 48579180) — i.e. 2y of daily /
  5y of weekly as-of each decision time. A frozen 2023-06-01→2026-09-24
  weekly window cannot satisfy the 205-completed-weekly-bar rule (≈171
  weekly bars), so weekly trend would be `unknown` for the whole sample by
  construction. The reconstruction therefore uses a deterministic
  historical adapter equivalent to the live calls:
  - One archival vendor pull per symbol: daily 1d and weekly 1wk,
    2018-01-01→2026-09-24, `auto_adjust=True`, `dropna()`,
    America/New_York (2018-01-01 covers T−1825d for every T ≥ 2023-01-01).
  - At each decision time T the adapter presents daily = bars in
    [T−730d, T] and weekly = bars in [T−1825d, T] — the same spans
    yfinance `period="2y"` / `period="5y"` return as-of T.
  - No bar with timestamp > T is visible to the adapter (no lookahead);
    the `closed_higher_timeframe` trim (§2.8) applies with now=T.
  - **Known limitation (non-blocking correction, recorded):**
    `auto_adjust=True` bakes **later** corporate actions into pre-T prices
    — a dividend paid after T retroactively lowers the pre-T adjusted
    closes in the archival pull (lookahead in the adjustment, not in the
    bars). Splits are unaffected in any material way for trend purposes.
    The 205-bar EMA trend is insensitive to single-digit dividend
    adjustments, but the limitation is frozen as a known imperfection,
    not patched mid-run.
  - The 205-completed-bar rule is unchanged: 2y daily ≈ 504 sessions and
    5y weekly ≈ 260 bars both satisfy it for mature names; new listings
    (ARM, SPCX, GEV/RDDT/TEM) correctly yield `unknown` → grade C (or B
    iff CONFIRM gate) per the §2.6 precedence order. Basis: DERIVABLE
    (tracked live code).
- Every cache file: SHA-256 + fetch timestamp logged; no hand edits, ever.
- Deterministic order everywhere: timestamp asc, then symbol asc. No dict-order
  or thread-order dependence.
- Rebuild stages A→G in plan order; gates A–F must pass in sequence; a failed
  gate stops the rebuild (record cause; do not adjust rules to force a pass).
- 31 Mode B synthetic unit tests (ENGINE.md) recreated and passing before the
  engine may be called (Gate C), in addition to Gate D (§10).

---

## §12. Post-run procedure (unblinded)

1. Execute the hash-locked rebuild; write outputs once.
2. Check Layer-1 (§5). Any miss: record as a finding with cause; stop —
   do not proceed to Layer-2, do not tune.
3. Verify the comparator-file hash (§15), open it, check Layer-2 (§6). Any
   miss: finding, not tuning permission.
4. If Yahoo data revisions explain a miss, label the result **non-exact**
   (data-drifted), never loosen a tolerance afterward.
5. Whatever passes is labeled **reconstructed canonical replica** from an
   **unblinded replication**.

---

## §13. Narrow Phase-0 procedural amendment (pre-authorized text)

In `research_notes/CANONICAL_QF_VALIDATION_PREREG_20260928.md`, Phase 0,
replace:
> "The reproduced headline must reconcile trade-by-trade to the published baseline."
with:
> "Phase 0 reconciles against the frozen multi-invariant comparator in
> `CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV5.md` (§5 pre-run, §6
> post-run). Exact trade-by-trade reconciliation is required only if an
> original trade ledger becomes available. The rebuild result is labeled a
> reconstructed canonical replica from an unblinded replication, not a
> recovered original."

This amendment changes no trading rule, threshold, dataset, or performance gate.
Apply it when (not before) Claude + ChatGPT + Mike approve this frozen spec.

---

## §14. Remaining gates — DO NOT BUILD until all clear

1. ChatGPT adversarial re-audit of rev 5.
2. Claude independent re-audit of rev 5 (Mike relays the rev-5 audit
   package: rev-5 spec + rev-5 request + `claude_audit_bundle_rev5/`).
3. Mike's explicit final sign-off on the frozen spec.
4. The §13 amendment applied to the validation prereg.

Build starts only after 1–4. Any material finding returns this document to DRAFT.

---

## §15. Freeze attestation + comparator commitment

- [ ] ChatGPT re-audit: PASS on rev 5
- [ ] Claude re-audit: READY (no unresolved material ambiguity)
- [ ] Mike final sign-off
- [ ] §13 amendment applied to validation prereg
- [ ] Code + spec + cache-manifest SHA-256 hash-lock recorded before Run 1

Comparator-file integrity commitment (NOT a blinding device):
SHA-256: `90962b798e3f442bb4df854fd34fc823c564a4a003753b3590a0cca89e7fc61a`
File: `research_notes/CANONICAL_RECONSTRUCTION_SEALED_ORACLE_20260928.json`
**Filename note (non-blocking correction):** "SEALED_ORACLE" is a **legacy
filename** retained for byte-continuity with the committed comparator
(hash above); it carries **no blinding meaning** — §0 explicitly reframes
this exercise as unblinded replication, and the hash is an integrity
commitment only.

---

## Appendix P. Per-rule provenance ledger (M5)

| # | Frozen rule | § | Classification | Source |
|---|---|---|---|---|
| P1 | Pure setup triggers (trend/ema/accel/crosses) | §2.3 | COPY | `v54_engine._pure_setup_triggers` bytes |
| P2 | `fast_rising`/`accel_rising` strict `>` | §2.3 | COPY | v54 bytes (`last["EMA21"] > prev["EMA21"]`) |
| P3 | State precedence EXIT>BUY>PULLBACK>EARLY>NEUTRAL | §2.3 | COPY | v54 bytes |
| P4 | Protection incl. hot/extension, SAFE/WARNING defs | §2.3 | COPY | v54 bytes |
| P5 | Entry YES iff state∈{BUY,PULLBACK} ∧ SAFE ∧ above_vwap ∧ in_zone(raw) | §2.3 | COPY | v54 bytes |
| P6 | `buy_zone` serialized `f"{low:.2f}-{high:.2f}"`; hard gate parses the rounded string | §2.3/§2.4 | COPY | v54 bytes + `scanner_rules._inside_buy_zone` (48579180) |
| P7 | Hard gates: structural contract + ADX ≥ 20; adx coerce→0 | §2.4 | COPY | `v54_rules.v54_hard_gates_pass` bytes |
| P8 | Grade precedence B-first (`or gate==CONFIRM`), then unknown→C, else A | §2.6 | COPY | `v54_rules.v54_grade` bytes + handoff brief |
| P9 | No RISK-OFF veto in V5.4; legacy veto is V5.3-only | §2.6 | COPY/DERIVABLE | v54 bytes contain no regime check; `v54_rules.py` docstring disavows veto imports; legacy veto at `masterscanner_api.py:269` |
| P10 | 15m/premarket observational only; no soft-demotion to C | §2.6 | COPY | `v54_rules.py` docstring + handoff brief |
| P11 | Market-gate formula; sub-205 QQQ → UNKNOWN/BLOCK | §2.7 | COPY | `masterscanner_api.get_market_regime` (48579180) |
| P12 | MTF wrapper: trim, 205-count, `timeframe_trend_confirmed`; EMA21 rising `>=` | §2.8 | COPY | `v54_engine._v54_trend_state` bytes + `scanner_rules.py:217-260` |
| P13 | Stop/TP1 from raw zone bounds; `bar_close_at` | §2.5/§2.1 | COPY | `scanner_rules.trade_levels`/`bar_close_at` (48579180); raw-bounds call in v54 bytes |
| P14 | Indicator math (EMA/ATR/ADX/VOL_BASE), constants | §2.2 | COPY | `masterscanner_api.add_indicators` (48579180) |
| P15 | VWAP := rolling-50 on the rebuilt 4H series | §2.2 | JUDGMENT | `rolling_vwap(df,50)` is the tracked fallback; the rebuild cannot produce SessionVWAP (§11); alternative recorded |
| P16 | Indicator seeding from `first_available_4h_bar` (all-history) | §3 | JUDGMENT | live-faithful 180d alternative recorded (`v54_scan_symbols` default) |
| P17 | `min_bars` = 205; `effective_4h_from` as eligibility floor | §3 | COPY/DERIVABLE | v54 bytes (`max(...)+5`); UNIVERSE.md `max(eligible_from, effective_4h_from)` |
| P18 | Daily availability incl. 13:00 early-close; MTF helper literal 16:00 | §4 | EXPLICIT+COPY | PIT_FEATURES rules 2,8; `closed_higher_timeframe` bytes |
| P19 | A1–A7 portfolio mechanics | §7 | JUDGMENT | reconciled per Claude audit; A6 `remaining_shares` corrected per mandate |
| P20 | Scanner EXIT via PP-armed pending-exit path | §8 | COPY | ENGINE.md §1/§3; trigger phrasing matches v54 bytes |
| P21 | MTF-context historical adapter (2y/5y as-of T) | §11 | DERIVABLE | `masterscanner_api.py:297-303` (`download_confirmation_data` calls) |
| P22 | PORTFOLIO.md canonical blob | §1 | COPY | SHA-256 `8ddc1e61…` (≠ git blob `4356f732a9a9fe2698e852d66b8a11d91212d810`), at `368fa2e` |

## Appendix R. Reversal / change log (rev 4 → rev 5 → rev 6)

### Rev 5 → rev 6 (mandate `5879344325`; no strategy semantics changed)
- **D-1 (D6 added).** Rev 5's Gate D proved eligibility independence only
  (D4/D5). Rev 6 adds D6: an independent portfolio-selection
  differential oracle proving contested-slot selection (A3 admission +
  A4 ranking) is independent of legacy `score`/`rank_score`, with
  synthetic contested-slot fixtures where injected legacy-score ordering
  conflicts with A4 RS ordering. Gate D is now D1–D6.
- **D-2 (M1/M2 rationale corrections).** M1: removed "SessionVWAP
  unavailable by construction" — 1H OHLCV can support session-VWAP
  reconstruction; rolling-50 is a JUDGMENT choice with disclosed
  sensitivity. M2: removed "205-bar gate dominates seed sensitivity" —
  disclosed exact ewm weight math (≈13% at bar 205, ≈8% at bar 250);
  PIT_FEATURES establishes warmup/seeding need, not the all-history
  resolution; labeled JUDGMENT with early-sample EMA200/`trend_bull`
  sensitivity disclosed. Frozen choices retained in both.
- **Non-blocking corrections:** A5 D4/D6 identity-key convention (13:00 ET
  on half-days); §4 removes the nonexistent "14:00 ET decision"; D4 scope
  = rebuild decision points after the §3 floor; D5 twin perturbation
  frozen (last-bar-only, asserted structural invariance; uniform 3x-volume
  twin forbidden); P22 distinguishes SHA-256 `8ddc1e61…` from git blob
  `4356f732…`; support commit `48579180` dated 2026-09-14T23:15:42Z with
  no-change record through `368fa2e`; §5B relabeled a consistency check;
  D5-c relabeled (not a minimal-score threshold test).

### Rev 4 → rev 5

- **R-1 (grade precedence).** Rev 4: unknown→C first (ChatGPT C1, adopted
  by Mike). Rev 5: B-first per the recovered bytes and handoff brief
  (P8). The C1 order was adopted without the bytes and is superseded.
  Effect: unknown MTF + CONFIRM gate → B (was C in rev 4).
- **R-2 (buy-zone rounding).** Rev 4 (A7): "no intermediate rounding."
  Rev 5: the `.2f` buy-zone serialization + rounded re-check are frozen as
  COPY (P6) — the rev-4 statement was wrong; the bytes round-trip through
  the string.
- **R-3 (RISK-OFF veto).** Rev 4: veto dropped, labeled JUDGMENT-adjacent
  ("without proving V5.4 removed this behavior"). Rev 5: veto absence
  proven by the bytes (P9) — no longer JUDGMENT.
- **R-4 (early-close daily helper).** Rev 4 §4 implied the 13:00 rule
  covered MTF reads. Rev 5: the tracked helper's literal 16:00 rule (no
  early-close exception) governs MTF reads; §4's 13:00 rule governs other
  daily inputs (§4 reconciliation).
- **R-5 (QQQ early history).** Rev 4 called sub-205 QQQ a corner case.
  Rev 5: the sub-205 window (Oct 2023 → Q1 2024) is real; the
  UNKNOWN/BLOCK rule applies mechanically (§2.7).
