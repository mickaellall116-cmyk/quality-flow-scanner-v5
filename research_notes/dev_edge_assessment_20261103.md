# DEV Edge Assessment — Lane A (2026-11-03)

**Scope:** Decision-grade assessment from EXISTING, already-committed DEV evidence only.
No new backtests, no new variants, no rule changes, no holdout access, no vendor calls.
Every figure below was verified against the committed artifact named beside it (ledger
figures recomputed directly from the pinned `-13` trade ledger; package-extracted bytes
match the `-13` package's own `SHA256_MANIFEST.txt` exactly).

**Subject:** the single frozen-C1 DEV run `QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13`
("-13"): 43 DEV equities (UX51 equities minus SMCI, pre-declared excluded — no DEV bytes
exist), DEV window 2024-09-16 → 2026-10-16 (cutoff 2026-10-16 17:30 ET), frozen C1
configuration (config sha256 `87b8285a…`), corrected successor engine, one execution with
byte-identical replay. The run's own governing labels, carried through every successor
package: **EQUITIES-ONLY DEV EXPLORATORY / G4 UNADOPTED / NOT VALIDATED EDGE.** Inputs are
candidate-grade (G4/VBASIS convention-break suspect, unadopted) — a qualification ceiling
on everything below, independent of the numbers.

---

## (a) Evidence table

### Run reconciliation (all views, closed taken trades only; terminal opens excluded from R stats, included in equity)

| Metric | Value | Source artifact | Artifact SHA-256 / commit |
|---|---|---|---|
| Candidates | 590 total = 586 closed + 4 censored (CRM/SHOP/MRNA/PFE) | `-13` `results.json` (P4) | `42b05ce3…` / commit `521980ab` |
| Taken / closed, gross view | 191 taken / 188 closed | `-13` `results.json`; `-29` `per_view_summary.json` | `42b05ce3…`; `5535bfa4…` / `2cf06fca` |
| Taken / closed, 4bps view | 191 taken / 187 closed | same | same |
| Taken / closed, 25bps view | 189 taken / 185 closed | same | same |
| C0 fidelity (control vs stack) | 193 taken, 190 exit cash flows, 0 diffs, equity 12,321.3876 both paths | `-13` `RESULT.md` / `results.json` (P4) | `b9e91b14…` / `521980ab` |
| Independent ledger audit | ChatGPT audit reconciles 15/15 figure groups exactly | `-14` forensic `RESULT.md` | `25ca913f…` / `f2b9ca4e` |

### Expectancy / PF / win rate by cost leg (recomputed from the pinned ledger; matches `-29` reconciliation exactly)

| Metric | Value | Source artifact | Artifact SHA-256 / commit |
|---|---|---|---|
| Expectancy, gross (n=188) | **+0.14990R** (sum +28.1812R) | `-13` `trade_ledger.json`, recomputed | `267e794c…` / `521980ab` |
| Expectancy, 4bps (n=187) | **+0.17373R** (sum +32.4873R) | same; `-29` `per_view_summary.json` mean_r 0.17373 | `267e794c…`; `5535bfa4…` |
| Expectancy, 25bps (n=185) | **+0.10751R** (sum +19.8892R) | same; `-29` mean_r 0.10751 | same |
| Expectancy, 50bps | **NOT MEASURED** — no 50bps view exists in any `-13`-lineage artifact | — | — |
| Profit factor, gross / 4bps / 25bps | 1.239 / **1.283** / 1.166 | ledger recomputation; `-13` `RESULT.md` (rounded 1.24 / 1.28 / 1.17) | `267e794c…` |
| Win rate, 4bps | **48.13%** (90/187); gross 46.81%, 25bps 47.03% | ledger recomputation; `-29` | `267e794c…` |
| Avg winner / avg loser, 4bps | +1.637R / −1.184R | `-13` `results.json` | `42b05ce3…` |
| Gross-vs-4bps inversion explained | Δ +4.3061R = friction **−2.2992R** on 182 common trades + allocation **+6.6053R** (path-dependent taken sets; per-trade, costs never helped) | `-14` forensic `RESULT.md` §2 | `25ca913f…` / `f2b9ca4e` |

### Concentration

| Metric | Value | Source artifact | Artifact SHA-256 / commit |
|---|---|---|---|
| Top-5 trades, 4bps | SNOW +8.0874, INTC +6.4172, AMD +5.9181, QCOM +5.3470, LRCX +4.8903 = **+30.6600R = 94.37%** of +32.4873R | `-14` forensic `RESULT.md` (recomputed here: 94.377%) | `25ca913f…` / `f2b9ca4e` |
| Ex-top-5 expectancy, 4bps | **+0.0100R** (182 trades, +1.8273R — flat) | `-14`; ledger recomputation | same |
| Ex-top-5 expectancy, gross / 25bps | **−0.0138R / −0.0473R** per trade (negative) | ledger recomputation | `267e794c…` |
| Sector net R, 4bps (ledger sectors) | SEMIS **+25.95R** (41 trades, 79.9% of net); AI_SOFTWARE **+19.31R** (26); SEMIS+AI_SOFTWARE = **139% of total net**; FINTECH **−12.24R** (21, only net-negative sector); CONSUMER −6.61R; ETF −2.92R; SPACE −0.78R; HEALTHCARE +5.63R; CRYPTO +4.15R | `-13` `trade_ledger.json`, recomputed | `267e794c…` |
| Entry-year split, 4bps | 2025: 95 trades, mean **+0.036R**; 2026: 92 trades, mean **+0.316R** (+29.11R of +32.49R total). At 25bps the 2025 slice is **negative** (−0.022R) | `-13` `results.json` | `42b05ce3…` |

### Losses beyond −1R and stop overshoot (close-triggered stop design)

| Metric | Value | Source artifact | Artifact SHA-256 / commit |
|---|---|---|---|
| Oversized losses | **66 trades** with gross R < −1.0, combined **−92.0847R** gross (64 stop-route + 2 ema55-break; 0 reached TP1). On the 4bps-net basis the set is 67 (AMZN boundary trade disclosed) | `-24` failure forensics `MEMO.md` §0 | `96c1addd…` / `f980f901` |
| Stop overshoot | All 64 stop-route fills printed **below** the initial stop; below-stop distances sum to **25.9849R** (median 0.3093R, max 2.1113R) = exactly the group's excess beyond −1R. Worst single loss −3.1113R gross / −3.128R @4bps | `-23` supplement; `-24` §1 | `2769386a…` / `1a05fa71`; `96c1addd…` |
| Intrabar stop breaches | **87 of 187 (46.5%)** trades touched the initial stop intrabar pre-TP1 and were held by the close-based rule; breach set net −83.8852R (10 recovered positive); never-breached set +116.3725R. **0 dual-touch bars** (TP1 and stop in same bar) — same-bar ordering ambiguity did not occur | `-23` anatomy `MEMO.md` §5 | `b64da221…` / `0581bf86` |
| Close-vs-gap split of overshoot | **NOT MEASURED** — trigger-bar close was never persisted; the 64 are evidenced as close-triggered exits with fills below stop, split unknown | `-23` supplement §3 | `2769386a…` |

### Drawdown / exposure / turnover

| Metric | Value | Source artifact | Artifact SHA-256 / commit |
|---|---|---|---|
| Max drawdown, all-bar (corrected measurement) | gross 25.5756% / **4bps 26.1840%** / 25bps 26.7035% (supersedes event-sampled 23.97% / 24.61% / 25.40% in `-13` `results.json`) | `-29` P1 `mtm_dev.json` | `e629850f…` / `c1035402` |
| Exposure (gross notional ÷ equity, full-grid corrected) | peak **2.7859x**, mean **1.1203x**, max single-position 1.6453x; max concurrency 5 (the cap). Upper-bound caveat: full notional held to exit (TP1 partial timing not in ledger) | `-31` P6 `MEMO.md` | `67cf95b7…` / `848f75d6` |
| Market exposure / avg hold | 94.8% of event span; avg hold 16.7 bars (4bps) | `-13` `results.json` | `42b05ce3…` |
| Turnover | **NOT MEASURED** — no turnover statistic exists in any `-13`-lineage artifact | — | — |

### Dependence-adjusted inference (O4, independently replicated)

O4 measured **paired exit-variant difference** dispersion — not the strategy's own
expectancy — so its SDs do not directly price the `-13` mean. What transfers is the
**design effect** (dependence inflation) O4 measured on DEV trades of this same frozen
config, via 20-session circular block bootstrap, 10,000 reps. The interval below uses the
`-13` ledger's own trade-R SD with O4's design-effect range applied to the trade count.
This is a stated approximation, labeled as such; O4 itself was variance-only by design and
issued no interval on any expectancy.

| Metric | Value | Source artifact | Artifact SHA-256 / commit |
|---|---|---|---|
| O4 H-EXIT-1 (E1−E0) | n=308, s=**1.2786R**, DE=1.4565, n_eff=211.47 | `o4_output.json` | `f9215a58…` / `703111a3` |
| O4 H-EXIT-3 (E0−E3) | n=308, s=**2.1757R**, DE=1.8915, n_eff=162.83 | same | same |
| O4 input integrity | 44,849 DEV bars, 0 mismatches; census 2,892; E0 fidelity 586/586 vs `-13` ledger; session-table bytes pinned at commit `70ef3679` | `o4_output.json`; commit `703111a3` | — |
| O4 blind replication | ChatGPT independent replication **PASS**, endpoints matched exactly (2026-10-31; Issue #1 comment `6551795500`) | Issue #1 | — |
| `-13` trade-R SD, 4bps | 1.8024R (ledger recomputation) | `-13` `trade_ledger.json` | `267e794c…` |
| Naive 95% interval, 4bps expectancy | **[−0.085R, +0.432R]** — includes zero even assuming independence (t = 1.32) | computed from the two rows above | — |
| Dependence-adjusted 95% interval, 4bps | n_eff = 187 / DE → **128 (DE 1.4565) to 99 (DE 1.8915)**; interval **[−0.138R, +0.486R]** to **[−0.182R, +0.529R]** — includes zero (t ≈ 0.96–1.09) | computed; method stated above | — |
| Dependence-adjusted 95% interval, 25bps | **[−0.200R, +0.415R]** to **[−0.242R, +0.458R]** — includes zero (t ≈ 0.60–0.69) | computed | — |
| Power context (frozen) | H-SYS-1 PASS needs ≈**693 independent closed trades** for 80% power at δ; this sample's n_eff ≈ 99–128 | Preregistration v1.0 / POWER_REPORT (program record) | — |

---

## (b) NOT MEASURED list

Every item below is absent from the committed artifacts. None is estimated, none is a PASS.

1. **50bps (or any higher) cost leg** for the `-13` DEV run — only gross / 4bps / 25bps views exist.
2. **Turnover** — no turnover statistic in any `-13`-lineage artifact (exposure and hold time are recorded instead; they are not turnover).
3. **Close-trigger vs next-open-gap split** of the 25.9849R stop overshoot (trigger-bar close never persisted).
4. **Per-trade indicator state at signal** — ADX, trendScore, VWAP relation, relative volume, EMA geometry: never persisted (only `rs` was). The FINTECH-tilt and ADX hypotheses frozen in `-24` are therefore UNTESTED, and stay that way on this data.
5. **MAE / closest TP1 approach / per-bar paths** — bar paths not persisted in the ledger.
6. **Per-date market/benchmark state** for the loss dates — no benchmark series is a recorded field.
7. **A direct O4 interval on the `-13` expectancy** — O4 is variance-only on paired exit differences by design; the interval in (a) is a labeled approximation built from the ledger SD × O4 design effects, not a pinned O4 endpoint.
8. **SMCI** — absent from the DEV universe entirely (no DEV bytes; pre-declared exclusion). Nothing in this assessment says anything about SMCI.
9. **Out-of-sample / second-regime performance** — the DEV window is a single span whose 2025 slice is ~flat (negative at 25bps); no second regime exists in the evidence.

---

## (c) Verdict

**NO ROBUST EDGE / EVIDENCE INSUFFICIENT.**

The point estimates are positive at every recorded cost leg (+0.150R gross, +0.174R at
4bps, +0.108R at 25bps; PF 1.24 / 1.28 / 1.17), and the bookkeeping underneath them is as
solid as this program has produced: the ledger reconciles exactly under an independent
audit (15/15), the two simulator paths agree trade-by-trade, and the replay is
byte-identical. None of that rescues the inference. The 95% interval around the expectancy
includes zero **even under a naive independence assumption**, and under the dependence
structure O4 actually measured (n_eff ≈ 99–128 of 187 trades) the estimate sits at
t ≈ 1 — roughly one standard error from nothing. The positive mass is five trades:
remove the top 5 and the remaining 182 trades are flat at 4bps (+0.010R) and negative at
25bps and gross. Two sectors (semis + AI software) account for 139% of the net; one
sector (fintech) is net negative; and nearly all of the net R was earned in 2026, with the
2025 slice flat-to-negative — a single-regime result. The headline 4bps-beats-gross
inversion is itself an allocation-path artifact (+6.6R allocation vs −2.3R friction on
common trades), not a cost anomaly in the strategy's favor. Under the program's own
economics-first rule (B2: point estimate ≥ δ **and** the interval excluding zero), this
evidence fails the interval leg at every cost view and every dependence assumption.
This verdict is **not** a proof of no edge: the same intervals are also consistent with a
small real edge (up to ~+0.4–0.5R). The correct statement is that the existing DEV
evidence cannot distinguish the two — which is precisely what "development-only,
not validated" has meant on this run's labels since the day it executed.

**Falsification criteria.**
- *Toward an edge:* the sealed Tier-3 holdout test, run once under the frozen
  preregistration, returning expectancy ≥ δ with its dependence-adjusted interval
  excluding zero at the 25bps leg — or a forward shadow cohort accumulating enough
  independent closed trades (order of the ~693-trade power figure, not another ~190) with
  ex-top-5 expectancy materially above zero at 25bps.
- *Toward no edge:* the same sealed test returning a point estimate at or below zero, or
  an interval whose upper bound sits below δ; or forward evidence in which the ex-top-5
  expectancy stays ≤ 0 at 25bps as the independent-trade count grows past ~300.
- *What changes nothing:* re-slicing this same DEV window (new sector cuts, filters fit
  to the 66 oversized losses, exit-variant replays on DEV bytes). The `-24` hypothesis
  register (FINTECH tilt, ADX band) stays frozen and untested until genuinely new data
  exists; tuning on this window would manufacture the appearance of evidence, not evidence.

**Provenance note:** the `-13` package commit `521980ab` is present in the repository
object store but is not an ancestor of this working tree's current `main` HEAD; the
figures were verified against the package's own `SHA256_MANIFEST.txt` (all extracted
hashes match) and cross-tied by the `-29` reconciliation package, which reproduces the
same ledger hash (`267e794c…`) and the same per-view figures independently.
