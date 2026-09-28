# Canonical QF Reconstruction Plan — Pre-Build
**Date:** 2026-09-28  
**Status:** PROPOSED — NO RECONSTRUCTION AUTHORIZED YET  
**Owner:** Mike  
**Architect/reviewer:** ChatGPT  
**Independent audit:** Claude request already frozen at `research_notes/CLAUDE_CANONICAL_RECONSTRUCTION_AUDIT_REQUEST_20260928.md`

## Purpose
The original canonical executable/output/data artifacts were never committed. Only six canonical specification documents survive in Git:
- `canonical_baseline/ENGINE.md`
- `canonical_baseline/LONEWOLF_RERUN.md`
- `canonical_baseline/PIT_FEATURES.md`
- `canonical_baseline/PORTFOLIO.md`
- `canonical_baseline/REBASELINE.md`
- `canonical_baseline/UNIVERSE.md`

This plan defines how to recover or reconstruct the historical canonical environment without reverse-engineering choices from the published performance result.

No production/live V5.4 file may be changed by this work.

---

## 0. First action: one final ORIGINAL-MACHINE recovery pass
Before writing reconstruction code, search the originating machine/session filesystem. Exact recovery is strictly preferable to reconstruction.

Search read-only for:
- any directory named `canonical_baseline`;
- `simlib.py`, `run_portfolio.py`, `modeb_engine.py`, `analyze.py`, `run_ablation.py`;
- `universe.json`, `portfolio_results.json`, `canonical_trades.json`;
- `candidate_pool.json`, `addv_ranking_20230930.json`, `addv_unrankable.json`, `new_listings_eval.json`, `coverage_report.json`;
- `d1_*.pkl`, `h4_*.pkl`, parquet/feather/h5/arrow/sqlite equivalents;
- old worktrees/clones, editor backup/history folders, notebooks, Downloads, temp folders, `/tmp`, `/mnt/data`, workspace directories, shell-history references, and any retained GitHub Actions artifact downloads.

Also inspect any still-accessible local worktree that produced the canonical docs. Git archaeology proved the files were never pushed; it does NOT prove they never existed on local disk.

**Gate R0:** if any exact artifact is found, hash it, preserve it read-only, and stop reconstruction of that artifact. Recovery outranks recreation.

---

## 1. Freeze the historical source-code anchor before rebuilding anything
The canonical docs were committed sequentially on 2026-09-25. The first canonical doc commit, `e77bb161891c6534c11b36a37b5002a8430ccbe0` (ENGINE.md), has parent:

`de01ff70a13e680c5468ae5e6e81177c981832e0`

Use **that parent commit** as the repository-tree anchor for reconstructing:
- the candidate-pool membership from “every symbol referenced in the repo”;
- historical scanner/signal code references;
- watchlists/universe source files;
- any surviving helper implementation referenced by the docs.

Do NOT build the candidate pool from current main; later repo additions could contaminate a rule defined as “union of symbols referenced anywhere in the repo.”

Caveat: this historical Git tree cannot prove what uncommitted local files existed when the canonical run was originally executed. Any recovered local artifact from Step 0 takes precedence.

---

## 2. Build an EXPECTED-RESULTS ORACLE before implementation
The missing JSONs are outputs, not source inputs. Do not hand-create them.

Before coding, copy the surviving documented invariants into a frozen oracle file. At minimum:

### Universe/data invariants
- candidate pool: 272 names;
- rankable in the 2023-06-30→2023-09-30 ADDV window: 229;
- unrankable: 43;
- top-120 cutoff: #120 DVN ≈ $375.7M/day; #121 DAL ≈ $373.2M/day;
- 15 post-cutoff listing candidates;
- 11 admitted: ARM, BMNR, CRWV, DRAM, GEV, GLXY, NBIS, RDDT, SNDK, SPCX, TEM;
- 4 rejected: CORZ, NNE, RBRK, UMAC;
- final universe: 131;
- 4H cache target: 137 symbols = 131 universe + 6 overlay outsiders;
- documented 4H effective history approximately 2023-10-26→2026-09-24;
- session labels 09:30 / 13:30 ET, one bar on documented early-close days;
- documented coverage/quality checks.

### Signal/portfolio invariants
- candidate V5.4 signals: 4,127;
- busy skipped: 622;
- slot/rank skipped: 744;
- heat skipped: 2,387;
- accepted: 374;
- max open: 6;
- 6 positions still open at sample end.

### Headline @50bps
- E = -0.0013R/trade;
- n = 374;
- win = 39.8%;
- PF = 1.00;
- max DD ≈ -39.8% / -$30,504 / -40.7R;
- total return ≈ -0.9%.

### Cost ladder
- 25bps: +0.1029R;
- 50bps: -0.0013R;
- 75bps: -0.1056R;
- 100bps: -0.2099R.

### Year split @50bps
- 2024: n=117, E=-0.2538R;
- 2025: n=128, E=+0.0610R;
- 2026: n=129, E=+0.1658R.

### Concentration checks
- top-10 total = +58.48R;
- ex-top-10 E ≈ -0.162R (n=364);
- best year = 2026;
- ex-2026 E ≈ -0.0893R (n=245);
- preserve the documented top-trade identities/R values as secondary checks.

### Overlay check
- 14-name overlay @50bps: n=151, E≈+0.4489R, PF≈1.77.

These are validation targets only. They must NEVER be used to choose between ambiguous implementations after results are seen.

---

## 3. Reconstruction dependency order

### Stage A — candidate pool + daily PIT data
Rebuild the 272-name candidate pool from the frozen Git tree at `de01ff70...`, following `UNIVERSE.md`:
- union of symbols from the documented repo sources;
- include CYBR and SQ/XYZ handling;
- exclude crypto and leveraged/inverse ETFs from the ADDV ranking exactly as documented.

Then rebuild the daily cache first, because universe membership depends on historical ADDV and new-listing liquidity.

Daily recipe explicitly pinned by `UNIVERSE.md`:
- source: yfinance;
- requested window: 2023-06-01→2026-09-24;
- `auto_adjust=False`;
- scale OHLC by AdjClose/Close;
- raw Volume;
- America/New_York;
- ranking window: 63 trading days ending 2023-09-30 (2023-06-30→2023-09-30);
- rankable requires ≥30 daily bars;
- new listings: listing + 30 trading days / ~60 4H bars, plus trailing-20-day ADDV ≥ $25M/day.

**Gate A:** the pool/ranking/listing invariants in Section 2 must match before universe.json is frozen. If they do not, stop. Do not alter rules to force a match.

### Stage B — regenerate `universe.json`
Only after Stage A passes:
- select top 120;
- add the 11 mechanically admitted new listings;
- preserve eligibility dates and documented ticker/corporate-action handling;
- keep delisted names through last trading day when data exists;
- record the documented CYBR limitation if historical data is still unavailable.

`universe.json` is an input generated from the frozen universe recipe, not manually recreated.

### Stage C — 4H PIT cache
Once the 131 names are known, build:
- 131 universe 4H histories;
- the six 14-name-overlay outsiders needed for overlay reproduction;
- required benchmark histories (SPY/QQQ if not already in the set).

Pinned construction:
- yfinance 1H source;
- regular US session only;
- explicit per-session wall-clock aggregation;
- 09:30–13:30 and 13:30–16:00 ET;
- no overnight-spanning bars;
- OHLCV first/max/min/last/sum;
- session-local DST-safe construction;
- one bar on NYSE early-close days;
- effective eligibility = max(rule eligibility, actual recoverable 4H coverage).

Do **not** use the known production `scanner_rules.resample_closed_4h` global-resample DST behavior as the canonical-cache implementation. The canonical docs explicitly describe DST-safe session-local bars.

Hash every regenerated cache file and retain fetch provenance.

**Gate C:** coverage and bar-label invariants must match the docs closely enough to reproduce the documented universe/candidate population. If current Yahoo history revisions change material bars, record the divergence; do not call the cache “exact historical recovery.”

---

## 4. Rebuild the Mode B engine BEFORE simlib/portfolio
The executable `modeb_engine.py` is also absent even though it is not in the short six-item missing list. Reconstruct it first because all trade outcomes depend on it.

`ENGINE.md` pins the execution semantics unusually tightly:
- next-4H-open entry supplied by caller;
- entry <= stop invalid;
- entry open >= TP1 => immediate 0R gap-above-target close;
- entry bar counts as bar #1;
- structural stop always active;
- live-faithful gap-through stop fills at stop;
- realistic variant fills gap-through stop at open;
- TP1 exact-level fill in live-faithful mode; open improvement in realistic variant;
- stop wins same-bar stop/TP1 conflict;
- 50% TP1 scale-out;
- TP1 bar gets no subsequent stop/EXIT evaluation;
- +1R arms Profit Protect permanently;
- armed scanner EXIT schedules next-bar-open exit;
- pending PP fill takes precedence on its fill bar;
- runner retains structural stop;
- timeout on 30th processed bar at close;
- MFE/MAE includes entry bar;
- R conventions and 4-decimal output rounding as documented.

Recreate the 31 synthetic unit tests described in ENGINE.md before using this engine in portfolio research.

Historical `122/122` live decision-packet parity is an expected historical record. If the exact old decision packets/state are no longer recoverable, do not claim that historical 122/122 was re-executed; instead run the rebuilt engine against any preserved forward packets available and record the narrower parity claim honestly.

**Gate D:** all recreated rule-path unit tests must pass before simlib is allowed to call the engine.

---

## 5. Rebuild `simlib.py`: signals/PIT logic only after data + Mode B are stable
The sim library should be a thin, deterministic research adapter, not a new strategy implementation.

Pinned behaviors:
- frozen V5.4 structural signal logic;
- all grades A/B/C;
- ADX >= 20;
- no Pine trendScore gating;
- completed 4H bars only;
- signal evaluated at signal-bar close;
- entry at next completed 4H bar open;
- entry skipped when fill <= structural stop;
- stop/TP1 frozen from signal-bar values;
- PIT_FEATURES.md rules 1–11;
- no earnings/event data;
- timezone America/New_York.

Important: the old numpy-boolean trendScore bug belongs to earlier C1/Pine-mirror history and must NOT be introduced here. Canonical V5 is the V5.4 structural-contract path documented in REBASELINE/PORTFOLIO, not the old 143-trade C1 reproduction.

**Gate E:** before portfolio sizing/ranking, the regenerated raw candidate set must equal the documented **4,127** candidates. A mismatch blocks portfolio reconstruction.

---

## 6. Freeze the few remaining portfolio ambiguities BEFORE first run
Most portfolio rules are explicit:
- initial book $75,000;
- fixed $750 planned risk/trade in Phase 0;
- shares = floor(750 / (entry-stop));
- no notional/capital cap in historical V5;
- max 6 open;
- about 5% heat cap;
- one position per symbol / busy rule;
- rs_top2 when signals exceed free slots;
- unrankable last;
- tie-break signal timestamp then symbol;
- costs = (bps/2) × sum of entry/exit leg notionals;
- marked equity at 4H closes;
- costs charged on event legs;
- open positions marked, not force-closed.

Before coding `run_portfolio.py`, explicitly resolve and freeze any item not fully determined by the docs. The highest-risk ambiguities are:

1. **Heat numerator after partial TP1:** whether “current position risk” shrinks with remaining shares after the 50% scale-out, and the exact mark used in the heat denominator.
2. **Pending-entry reservation in the historical V5:** the docs pin same-bar rank/slot competition but do not state as explicitly as the new Phase-1 prereg whether risk/slot is reserved before next-bar fills.
3. **Exact same-timestamp evaluation sequence:** busy → rank/slot → heat is implied by the documented funnel, but the batch mechanics must be frozen before seeing output.
4. **rs_top2 benchmark definition:** PORTFOLIO calls it 20-bar 4H return minus SPY, while PIT_FEATURES describes the symbol leg as 20 closed 4H bars and references a strict-PIT benchmark leg. If a surviving historical helper resolves this, use the helper; otherwise freeze the exact formula before running.
5. **Half-day decision timestamp:** docs require one 09:30 bar on early-close days, but historical code references are not fully explicit about whether its availability time is actual 13:00 ET or a generic 13:30 close calculation. Freeze this from exchange-calendar semantics or recovered implementation before the first run.
6. **Marked-equity event ordering:** exact ordering of entry/exit costs, partial fills, and 4H close marks when multiple events share a timestamp.
7. **Rounding policy outside Mode B:** shares are floored, but intermediate equity/cost rounding should not be guessed if a surviving helper can resolve it.

These are PRE-RUN specification questions. They may not be chosen after looking at which variant better matches -0.0013R.

---

## 7. Rebuild `run_portfolio.py`
After Stages A–E and ambiguity freeze:
- generate all candidates once;
- process decision timestamps deterministically;
- enforce busy/slot/rank/heat semantics exactly as frozen;
- call the rebuilt Mode B engine;
- run 25/50/75/100bps from the same accepted-trade mechanics;
- run both live-faithful and realistic-gap execution variants;
- preserve every skip reason and decision packet.

Do not include the new 1% minimum stop, 100% single-position cap, or 100% gross cap in Phase 0. Those belong to Phase 1 only.

**Gate F:** the portfolio funnel must reconcile to 4,127 → 622 busy skips → 744 slot skips → 2,387 heat skips → 374 accepted before aggregate performance is considered.

---

## 8. Regenerate the two missing JSON outputs — never recreate them manually
`canonical_trades.json` and `portfolio_results.json` must be GENERATED by the locked reconstructed run.

Correct procedure:
1. reconstruct/freeze inputs and mechanics;
2. execute once;
3. write the regenerated JSONs;
4. compare them to the frozen expected-results oracle.

Do not directly synthesize either JSON from the prose tables. They are outputs.

---

## 9. Phase-0 reproduction gate
The published -0.0013R headline is NOT enough.

A rebuilt canonical environment is accepted only if, without post-result tuning, it passes a multi-layer gate:

### Data/universe layer
- documented candidate-pool/ranking/listing/final-universe invariants;
- documented 4H session/coverage invariants.

### Signal layer
- 4,127 raw V5.4 candidates.

### Portfolio-decision layer
- skip funnel 622 / 744 / 2,387;
- 374 accepted;
- max 6 concurrent;
- 6 open at end.

### Outcome layer
- cost ladder;
- 2024/2025/2026 counts and expectancies;
- win/PF/DD/return near documented values;
- top-trade/concentration identities broadly reconcile;
- 14-name overlay check.

If the original `canonical_trades.json` is recovered in Step 0, add exact trade-by-trade reconciliation and require it.

If it is NOT recovered, exact historical trade-by-trade reconciliation is impossible because there is no surviving expected ledger to compare against. Matching several independent decision and outcome invariants is the strongest honest substitute; it must be labeled **reconstructed canonical replica**, not recovered original artifact.

---

## 10. Does the frozen validation prereg change?
**Phase 1 does not change at all.** Its economic/risk hypotheses remain frozen:
- 1% minimum actual fill-to-stop;
- max single-position notional 100% marked equity;
- max total gross 100%;
- actual risk used for heat;
- pending risk/notional reservation;
- sensitivity 150%/200% gross and 2% min-stop;
- missing rs_top2 null/unrankable;
- required analyses unchanged.

However, Phase 0 currently says:
> “The reproduced headline must reconcile trade-by-trade to the published baseline.”

If the original canonical trade ledger is not recovered, that literal requirement cannot be executed.

Therefore:
- **If Step 0 recovers the old ledger:** no prereg amendment needed.
- **If Step 0 does NOT recover it:** make one narrow procedural amendment BEFORE reconstruction stating that Phase 0 must reconcile against the frozen multi-invariant oracle above, with exact trade-by-trade reconciliation required only if an original ledger becomes available.

That amendment changes no trading rule, threshold, dataset outcome, or performance gate. It only replaces an impossible verification artifact with a preregistered reconstruction-validation procedure.

---

## 11. Do-not-proceed conditions
Muse must NOT start reconstruction code if any of these remain unresolved:
- original-machine recovery has not been attempted;
- historical repo source anchor is not frozen;
- candidate pool cannot reproduce the documented 272-name / boundary invariants;
- daily data cannot reproduce the universe/listing decisions without unexplained material differences;
- 4H session clock/half-day convention is unfrozen;
- rs_top2 formula is unresolved;
- heat-after-partial / same-timestamp sequencing is unresolved;
- Mode B unit-path tests are not specified;
- the Phase-0 verification procedure has not been amended if the old ledger remains unavailable;
- Claude raises a material ambiguity that is still unresolved.

---

## Recommended decision
**READY WITH EXPLICIT AMBIGUITIES FROZEN FIRST.**

The six docs are strong enough to support a disciplined reconstruction, but not strong enough to justify silently guessing the remaining portfolio sequencing/data details.

Minimum actions before Muse writes code:
1. complete the read-only original-machine recovery pass;
2. freeze the historical repo source anchor at `de01ff70...`;
3. freeze the expected-results oracle;
4. resolve the seven listed ambiguity items from surviving source/recovered artifacts, or explicitly preregister the choice before results;
5. if no original trade ledger is recovered, add the narrow Phase-0 procedural amendment;
6. reconcile Claude's independent audit with this plan and record any disagreement;
7. Mike + ChatGPT approve the frozen reconstruction spec.

Only then may Muse rebuild.
