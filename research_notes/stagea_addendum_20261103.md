# Stage A Audit Addendum — 2026-11-03

**Status:** Non-gating audit addendum to the Tier-3 Stage A report (2026-11-03).
Built from the preserved run artifacts ONLY. Nothing was re-run: no strategy
evaluation, no data pull, no regeneration of any figure by execution. All
statistics below are arithmetic on the existing ledgers. The original report
and ledgers are immutable and unchanged.

**Source artifacts (SHA-256, as preserved in `~/workspace/tier3_stagea_run/`):**

| Artifact | SHA-256 |
|---|---|
| results.json | `c872a0e8b0d8c5642db088e39fdcbe9676a726a5cb99af2ed023d52b00916d8d` |
| ledger_7a.json | `77a792fc95f0014f52211b9aee80202031d56316e9c011110e7992ddff77cf1f` |
| ledger_hbuy.json | `093dc29c19dec58511dcee9e03f7ce2f234aa85d14f6d53fd8168c67a470441d` |
| ledger_7b.json | `d56dc85303c1269e21393cd3c25082b0f42674a7a2157d0cca13e1b33ece5754` |
| STAGEA_REPORT.md | `6fc8b3f5999cd31944511348c0109dfeeb5759b4a98479c7aba5c0d4bf4cdb70` |

Sanity anchors (recomputed from the ledgers, matching results.json exactly):
H-BUY-P θ = mean of the 20 retained `excess["10"]` values = **+1.118811 ATR**
(results.json: 1.1188106210105808). E0 @25bps net = **+6.521908R** over 25 closed
trades (results.json `diagnostics.e0_net_R_gate`: 6.521907982391022).

---

## 1. Relabels — H-SYS-1 and H-EXIT-4 are NOT EXECUTED

The Stage A report's endpoint table labels H-SYS-1 and H-EXIT-4
"INCONCLUSIVE-by-floor." That label is corrected here:

- **H-SYS-1: NOT EXECUTED.**
- **H-EXIT-4: NOT EXECUTED.**

The Tier-3 capture contains no SPY bars and the frozen sector map covers none
of the 11 Tier-3 symbols (the report's own gap §4 and RUN_SPEC_EXTRACTED.md
both state this). The 7C complete-system legs therefore never ran — there was
no test whose sample fell short of a floor. **The complete-system test did not
occur.** No statement about complete-system edge, in either direction, is
supported by the Stage A run. (Item M5 of Claude's forensic audit.)

## 2. Concentration — leave-one-out tables from the existing ledgers

### 2a. H-BUY-P (h=10), leave-one-SYMBOL-out — 20 retained matched events

Full sample: n=20, Σ excess = +22.3762 ATR, θ = **+1.1188 ATR**.

| Dropped symbol | Symbol n | Symbol Σ excess (ATR) | Remaining n | θ without (ATR) |
|---|---|---|---|---|
| AAOI | 1 | +2.8024 | 19 | +1.0302 |
| ACN | 1 | +1.2392 | 19 | +1.1125 |
| BABA | 2 | +6.8818 | 18 | +0.8608 |
| BE | 2 | −3.5923 | 18 | +1.4427 |
| BLK | 1 | +0.6724 | 19 | +1.1423 |
| COF | 2 | −0.8554 | 18 | +1.2906 |
| **CRDO** | **3** | **+13.5467** | **17** | **+0.5194** |
| IREN | 2 | +0.3764 | 18 | +1.2222 |
| MPWR | 2 | −2.1396 | 18 | +1.3620 |
| SPOT | 3 | +2.7553 | 17 | +1.1542 |
| TWLO | 1 | +0.6894 | 19 | +1.1414 |

Single-event check: the CRDO event of **2024-05-23** (session ordinal 149,
excess +12.3161 ATR) is **55.0%** of the entire excess sum. Dropping that one
event alone: n=19, θ = **+0.5295 ATR**. All three CRDO events together are
60.5% of the excess sum.

**Verification of Claude's audit figures:** drop CRDO 2024-05-23 event →
Claude +0.529 ATR, recomputed **+0.529** ✓. Drop all CRDO → Claude +0.519 ATR,
recomputed **+0.519** ✓.

### 2b. H-BUY-P (h=10), leave-one-SESSION-out — 16 distinct event sessions

Each row removes ALL retained events in that session (ordinals are session
indices in the 227-session capture calendar).

| Dropped session | Events | Session Σ excess (ATR) | Remaining n | θ without (ATR) |
|---|---|---|---|---|
| 108 | 1 | +3.6284 | 19 | +0.9867 |
| 112 | 2 | −1.4348 | 18 | +1.3228 |
| 127 | 1 | −0.9108 | 19 | +1.2256 |
| 132 | 1 | +6.4019 | 19 | +0.8408 |
| 137 | 1 | −0.1826 | 19 | +1.1873 |
| 148 | 1 | −1.9570 | 19 | +1.2807 |
| **149** | **2** | **+13.6974** | **18** | **+0.4822** |
| 157 | 1 | −2.1372 | 19 | +1.2902 |
| 162 | 1 | −3.3718 | 19 | +1.3552 |
| 170 | 1 | +1.6605 | 19 | +1.0903 |
| 171 | 1 | +0.6724 | 19 | +1.1423 |
| 183 | 1 | +0.4798 | 19 | +1.1524 |
| 186 | 3 | +1.0740 | 17 | +1.2531 |
| 187 | 1 | +0.6894 | 19 | +1.1414 |
| 191 | 1 | +1.2641 | 19 | +1.1112 |
| 216 | 1 | +2.8024 | 19 | +1.0302 |

Session range: θ without any single session runs from **+0.4822** (dropping
session 149, which holds the CRDO event) to **+1.3552** (dropping session
162). One session of 16 carries the majority of the headline figure.

### 2c. E0 system arm (ledger_7a, 25 bps view = 12.5 bps/fill), leave-one-SYMBOL-out

Full sample: n=25 closed trades, net +6.5219R, mean **+0.2609R**.

| Dropped symbol | Symbol n | Symbol net (R) | Remaining n | Mean without (R) |
|---|---|---|---|---|
| ACN | 1 | −1.5744 | 24 | +0.3373 |
| BABA | 2 | +0.2601 | 23 | +0.2723 |
| BE | 4 | −0.7630 | 21 | +0.3469 |
| BLK | 2 | +0.2811 | 23 | +0.2713 |
| COF | 2 | −2.7936 | 23 | +0.4050 |
| **CRDO** | **4** | **+9.5340** | **21** | **−0.1434** |
| IREN | 2 | +4.1243 | 23 | +0.1042 |
| MPWR | 3 | −3.0278 | 22 | +0.4341 |
| SPOT | 4 | +0.4117 | 21 | +0.2910 |
| TWLO | 1 | +0.0694 | 24 | +0.2689 |

(AAOI has no closed E0 trade — its single cohort event is E0-censored — so it
does not appear.) CRDO's four E0 trades net +9.5340R against a whole-sample
net of +6.5219R: the remaining 21 trades net −3.0121R.

**Verification of Claude's audit figure:** E0 without CRDO → Claude −0.143R,
recomputed **−0.1434R** ✓.

## 3. Effective span — 109 sessions, ≈ 5 blocks, not 12

Verified from the ledgers: the cohort events' `session_ordinal` values span
**108 to 216** (both the 27-event cohort and the 20 retained matched events),
i.e. **109 sessions** of the 227-session capture. The frozen 215-bar warmup
(RUN_SPEC_EXTRACTED.md: `WARMUP = 215 bars`) consumed the first 108 sessions
before the first event could fire.

109 sessions contain **five** non-overlapping 20-session blocks (109 / 20 =
5.45), not the ~12 implied by dividing the full 227-session window. This is
corroborated inside results.json itself: the endpoints' `mean_blocks_per_rep`
is 5.31–5.41. **The honest block count for Stage A inference is ≈ 5.**

## 4. Matching drop rate — 7 of 27 = 25.9%, above the 15% flag

Verified from ledger_hbuy.json: 27 cohort-event records; 7 carry
`dropped: "pool_below_min_step_c"` (ACN ×1, BE ×2, BLK ×1, CRDO ×1, MPWR ×1,
SPOT ×1); 20 retained with matched excess values. **7 / 27 = 25.9%**, above
the 15% attrition flag. (Matches results.json `counts`:
`hbuy_dropped_pool_below_min: 7`, `hbuy_retained: 20`.)

## 5. Ledger_7a exit fields — NOT RECOVERABLE from preserved outputs

Searched for per-trade `exit_time`, `hold_bars`, exit `reason`, and `tp1_hit`:

- ledger_7a.json records contain exactly: `symbol`, `signal_idx`, `ts`,
  `session_ordinal`, `entry`, `stop`, `tp1`, `censored`, `R`. No exit fields.
- The run wrote exactly four JSON outputs (stage_run.py, write block at the
  end of `main()`): results.json, ledger_7a.json, ledger_hbuy.json,
  ledger_7b.json. Full-text search of every preserved Stage A output
  (those four, plus STAGEA_REPORT.md, RUN_SPEC_EXTRACTED.md,
  parity_report.json) for `exit_time` / `hold_bars` / `tp1_hit` /
  `exit_reason`: **zero hits**. derived_1h.json is bar data only. No run log
  or state file exists in the stage directory.
- Why: for the 7A cohort events, the E0–E3 arm simulators returned fill lists
  that were reduced to R values before the record was written; exit fields
  were never placed in the record. The one place exit fields were computed —
  the 7B candidate generator — built trade dicts containing them in memory,
  but the written cand_records preserved only `symbol`, `signal_idx`,
  `signal_time`, `e0_censored_candidate`, `R_gate`. (Those are also a
  different trade set: 42 C1-style candidates, not the 7A cohort events.)

**Conclusion: the 7A exit fields are NOT RECOVERABLE from any preserved
output.** Per the sharpened audit instruction, they have NOT been regenerated
— recovering them would require re-running the consumed test, which is
prohibited. No `ledger_7a_extended.json` is emitted. Execution-path checks
that need exit time, hold length, exit reason, or TP1-hit flags are NOT
REPRODUCIBLE from the portable bundle; these fields must be captured
prospectively in future runs. (Item M4.)

## 6. Not recomputable from the portable ledger

The H-BUY percent excess (results.json:
`hbuy_descriptive_pct_excess_minus_25bps_h10` = +1.732%) cannot be
recalculated from ledger_hbuy.json: the ledger stores ATR-denominated excess
only, with no per-event percent-excess, entry-price, or ATR-level field.

---

## Closing statements

- **Tier-3 v1.0 remains CONSUMED** under preregistration §13. This addendum
  changes no verdict and re-opens nothing.
- The relabels in §1 stand: H-SYS-1 and H-EXIT-4 are **NOT EXECUTED**, and the
  complete-system test did not occur.
- **Inference caution (item M1):** with ≈ 5 effective blocks and 11 symbol
  clusters, the Stage A intervals are too fragile for confirmatory reading.
  The H-BUY-P lower bound sitting above zero is **not** edge evidence and
  must not be promoted as such. §2 shows why in one line: removing one event
  (CRDO, 2024-05-23) cuts θ from +1.119 to +0.529 ATR, and removing one
  symbol flips the E0 system mean from +0.261R to −0.143R.
- The frozen §12 leave-one-out routine was a stub in the original run; these
  tables are therefore the first published LOO diagnostics for Stage A and
  are marked as an addendum product, not an original-run output (item M3).

*Addendum prepared 2026-11-03 by Muse, from preserved artifacts only.*
