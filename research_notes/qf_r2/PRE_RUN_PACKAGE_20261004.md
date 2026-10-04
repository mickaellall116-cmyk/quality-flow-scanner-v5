# PRE-RUN PACKAGE — QF-R2-BRK-VOL-4H-001 (4H high-volume breakout confirmation)
Date: 2026-10-04
From: Muse (Research Engineer)
Status: **PREFLIGHT COMPLETE — PERFORMANCE HELD.** No market data was read for performance; raw-evidence paths are empty (0 bytes). `--run` hard-held (exits 2 "PERFORMANCE HELD" unless `QF_R2_ALLOW_RUN=1`).
Local branch/commit: `qf-r2-preflight-20261004` / `308552b` (local only at handoff time)

## Hashes (sha256)
- Prereg `qf_r2_brk_vol_4h_prereg_20261004.md`: `82c7f732a1c8ca2534afc3522f0aa108a0a08e6548ada8a6a4a0629219be239b` — verbatim transcription of Issue #1 comment #5981881915 (raw comment sha256 c62c95e2…a15f7887, created 2026-10-04T16:02:50Z)
- Runner `qf_r2_runner.py`: `d3924ace9d0ff3720f1ea04bbc984c729d3725197081fda9e563150b50a75e9d`
- Fixtures `qf_r2_fixtures.py`: `671cf6218d574be4cc8a27cee6803792845c19b194dc23a5843fd51f70cd12c6`
- Manifest `qf_r2_manifest.json` — spec/runner/fixtures/input/module hashes, constants, raw paths, evidence tier

## Fixtures: 12/12 PASS (directive's 12 pre-run checks)
1. Manifest committed with matching hashes
2. 225/225 frozen 1H inputs hash-verified; missing input raises (fail closed, no Yahoo substitution)
3. prior_high20 excludes current bar
4. vol/minute + same-slot classification; duration-only change cannot flip class (caught and fixed a real `bar_minutes` bug: opening bar was 390 min instead of 240)
5. Early-close signal bars excluded (verified 2024-11-29 = 13:00 close)
6. Next-4H-open entry only; missing open → excluded with reason
7. Causal suppression applied before volume classification
8. Matching uses event-time fields only + deterministic tie-break + no replacement
9. Stop-first ambiguity; gap-through-stop fills at worse open
10. Each of G0–G5 individually flips the verdict
11. All 7 raw-output paths exist
12. Evidence tier = COMPUTED; no REPRODUCED claim

## Exact definitions implemented
- Breakout at completed 4H bar t: `prior_high20 = max(High[t-20:t-1])` (current bar excluded); `Close[t] > prior_high20`; `strength = (Close[t]−prior_high20)/ATR14[t]` (Wilder RMA-14, same formula as `pine_backtest.atr` default)
- 4H bars: frozen constructor `scanner_rules.resample_closed_4h_session_anchored` (the function `top_broad_performance.build_4h` used). Session slots: 09:30 = opening (240 min), 13:30 = closing (150 min), from XNYS calendar; early-close days excluded from events and baseline bars
- Volume: `vol_rate = Volume/bar_minutes`; baseline = median of prior 20 completed normal-session same-slot bars (strictly causal); `volume_ratio ≥ 1.50` → HIGH; <20 baseline bars → ineligible
- Trade: entry = next 4H open (missing → excluded, reason logged); stop = prior_high20 − 0.5·ATR14; R≤0 → invalid; TP = entry+2R; 20-bar max hold; stop-first on same-bar stop+TP; gap-through-stop fills at worse open; costs 25bps primary / 4bps diagnostic round-trip
- Matching: exact strata (slot, calendar quarter, SPY regime), then nearest ATR_pct decile, then nearest strength; tie-break |ts| distance → symbol α → earlier ts; greedy without replacement, HIGH events processed in (ts, symbol) order
- Null: weekly block sign-flip, 10,000 permutations, two-sided p; 95% CI from 10,000 weekly block bootstraps, seed 20261004
- Gates G0–G5 wired exactly per spec. Verdict precedence: PASS only if all pass; FAIL if sample sufficient and any G1–G5 fails; INSUFFICIENT if G0 or required G4 counts fail

## Cost assumption
Round-trip bps applied on entry notional in R units: `cost_R = bps·entry/initial_R` (spec does not define the cost basis — flagged as ambiguity 4 below)

## Raw evidence locations
`research_notes/qf_r2/raw_evidence/` — events.csv, matches.csv, ledger.csv, inference_in.csv, inference_out.csv, gates.json all 0 bytes (EMPTY); code_data_manifest.json holds the manifest copy.

## Execution timing
`--verify` (225 hash checks) ~1s; full fixture suite ~6s.

## Unresolved spec ambiguities (need ChatGPT/Mike before any run)
1. SPY regime PIT: same-day daily close unknowable at a 13:30 bar close → implemented prior-trading-day `Close_SPY > EMA200_SPY` uniformly (from frozen `d1_SPY.pkl`). Needs confirmation.
2. ATR_pct decile population unnamed → pooled eligible events, `pd.qcut` 10 bins.
3. Calendar week unnamed → ISO week (Monday start).
4. Cost basis unnamed → entry-notional convention above.
5. Matching order unnamed → greedy in (ts, symbol) order; result is order-dependent.
6. Sign-flip p uses `mean(|perm| ≥ |obs|)`; permutation RNG seeded 20261004 (spec only fixed the bootstrap seed).

## Parity / provenance notes
- `pine_backtest.py` and `top_broad_performance.py` match the TOP-vs-BROAD recorded code_hashes exactly.
- `scanner_rules.py` had NO recorded hash in that evidence stack — recorded its current hash (`62aa743a…`) as the frozen value in the QF-R2 manifest. (Relevant to the pending scanner-hardening package.)
- Environment: installed `pandas_market_calendars 5.4.0` via pip (required by the frozen constructor's session-close logic; was missing in this shell).
- No frozen files modified (scanner_rules imported read-only; `--verify`/fixtures only read inputs). Development pool = 218 symbols (225 manifest files minus the 7 TOP-vs-BROAD exclusions).

**STOP.** Awaiting the bounded source review before any performance execution.
