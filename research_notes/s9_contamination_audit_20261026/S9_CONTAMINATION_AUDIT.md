# §9 Holdout Contamination Audit — Quality Flow Preregistration v0.3

**Audit date:** 2026-10-26 · **Auditor:** Muse (build lane; will not run the Stage A test)
**Spec:** PREREG_V03_DRAFT §9 (commit `b65696a`), checks A1–A5 · **Checklist item:** B1
**Holdout:** 2023-10-19 → 2024-09-15, UX51 symbols, 4H — designated and sealed 2026-10-03
(`forward_test/holdout_protocol_v2_20261003.md`; dates recovered by record 2026-10-18,
`a600940` / proposal v3 `f054ff7`).
**Method:** metadata, hashes, timestamps, commit/receipt history, and study documents
ONLY. No holdout price or performance data was opened, parsed, computed on, or
downloaded for this audit. Where a source document itself states an aggregate result,
the audit records that the read occurred and what it decided — it does not republish
window-specific figures, and none exist on record.

---

## Outcome (evidence-supported; joint decision still required)

# PARTLY CONTAMINATED

§9 requires the outcome to be **decided jointly by Mike and Muse and logged before
any access**. This audit supplies the evidence and the supported outcome; the joint
logging is the remaining governance step (see Gaps).

**What this means under §11's pre-specified branches:** Tier 2 is reported as
supplementary with **no PASS or FAIL standing**; Stage A runs on **Tier 3 only**
(holdout window); the edge rule reads "Stage A not to FAIL" on the Tier-3-only
analysis; confirmatory weight rests on Tiers 3 and 4.

**Consequence for the B1 REDUCED decision (Mike + ChatGPT, 2026-10-26):** B1 was
adopted *subject to a Clean §9 audit*. The audit outcome is **not Clean**, so B1's
stated condition is not met as worded. The defect census behind REDUCED is unaffected
(19 evaluable Tier-2 names — an outcome-blind bar-quality census), but under the
Partly branch those names carry supplementary standing only. The reduced-universe
mechanics remain the right basis for the **Tier 3** list construction (mechanical,
outcome-blind), which is where Stage A's confirmatory weight now sits. This fork is
flagged for Mike's logging decision with the outcome; nothing in this audit opens,
spends, or retires the holdout by itself.

**Why not Clean:** check A2's contamination test is met in its research-influence
limb (finding F-A2-1). Before the window was designated, a full-portfolio performance
aggregate of the frozen stack was computed over data spanning the window and read by
the team, and it demonstrably informed research decisions. A protocol that then
claimed the window was untouched would be claiming something the record contradicts.

**Why not Contaminated:** no frozen component was designed, selected, or adjusted
using holdout-window data (A4 clean); no window-specific outcome — no trades, P&L,
aggregate, or chart for 2023-10-19→2024-09-15 as a slice — was ever computed or
viewed; the spanning read predates the designation; the seal's byte integrity
verifies exactly (A3); and post-designation discipline for the Quality Flow rule set
is documented at every step (captures qualification-only, DEV runs hash-fenced from
HO files, EXP-14B inputs DEV-only and hash-pinned).

---

## A1 — Data lineage · Verdict: COMPLETE (two documented lineage gaps, neither overlapping)

Full table: `evidence/dataset_lineage.csv`. Every cache/archive used in any earlier
study, with spans and hashes where they survive:

| Dataset | Span | Overlaps holdout? | State |
|---|---|---|---|
| D1 `backtest_cache/v3` (52 files, 75,311 bars) | 2024-09-16 → 2026-09-15 | **No** | Destroyed (VM replacement); CP1 pins survive, hash-verified |
| 2022 stress-leg cache | Calendar 2022 | **No** | Bytes unretained; stored figures re-run 2026-10-03, matched exactly |
| Canonical reconstruction cache (137 files) + daily cache | 4H 2023-10-26 → 2026-09-24; daily 2023-06-01 → 2026-09-24 | **Yes** | Untracked/quarantined; traced through A2/A4 |
| D6 re-baseline runtime inputs (131 sym) | Oct 2023 → Sep 2026 | **Yes (aggregate)** | Never archived |
| D2 watchlist 4H cache (14 sym) | 2023-10-25 → 2026-09-23 | **Yes** | Present; traced through A2 |
| D3 Tiingo EOD daily (444 sym) | 2009 → 2026-09-30 | Yes (daily) | Present, terms HOLD |
| BOSWaves / SA-VWAP daily study data | ~18 years | Yes (daily, other systems) | Study records only |
| TD probes/screens (Oct 13–23) | Probe windows only | No strategy read | Archive, append-only |
| TD captures W_DEV / W_HO (Oct 23) | DEV 2024-09-16→2026-10-16 / HO = the window | HO legs **are** the designated bytes | Archive; qualification-only; hash-verified |
| P7b inventory + EXP-14 exec prices | DEV only (44,849 bars) | **No** | Private archive |
| Yahoo clean capture (Oct 15–16) | — | No capture landed | Preflight only |

Key span proofs (metadata): CP1 bundle `bar_timestamps_raw.json` — D1 AAPL first bar
**2024-09-16 09:30 ET**, 993 bars, 52 files pinned in `h4_cache_hashes.json`; CP1
forensic — reconstruction AAPL 1,451 bars **from 2023-10-26**, written 2026-09-25 by
`fetch_4h.py`, a different file set from D1. The C1 baselines therefore never touched
holdout-window bars; the reconstruction set did span it and is traced below.

**Lineage gaps (documented, not repaired):** (i) D1's exact invoking script is
unrecoverable (CP1 permanent gap) — immaterial here: its span is pinned by surviving
timestamps. (ii) The 2022 leg's bytes are unretained — immaterial: calendar 2022
precedes the window by construction.

## A2 — Access history · Verdict: CONTAMINATION TEST MET (one limb, pre-designation)

Search log: `evidence/access_history_search_log.md` (14 searches).

- **F-A2-1 (material, pre-designation).** The 2026-09-24 canonical re-baseline ran a
  full portfolio replay of the frozen stack on 4H data from Oct 2023 (374 trades,
  costs to 100 bps, component decomposition) and its results were read by Mike, Muse,
  ChatGPT and Claude and **did inform research**: the old +0.239R baseline was
  discarded, the lone-wolf candidate was removed, the forward checkpoint was
  re-anchored to ~0R, and the hypothesis queue was reset against it. The span
  includes 2023-10-26→2024-09-15 — inside the window later designated. **No
  window-specific slice was computed or viewed, and no rule or parameter was changed
  by it** (the frozen stack was the object measured, not adjusted). Under §9's
  wording — a read of holdout outcomes (an aggregate containing window trades) "that
  could have informed research or rule selection" — the research limb is met. This
  single finding is what bars a Clean outcome.
- **F-A2-2 (pre-designation, no outcomes).** The 2026-09-28/30 canonical
  reconstruction designed a Gate D differential oracle over signal-identity sets
  across the reconstruction window (including the window portion) — parity evidence,
  no P&L — under written governance forbidding outcome-driven rule changes and
  banning the old C1 figures from validation.
- **F-A2-3 (post-designation, different rule family).** October 2026 creator-claim
  sweeps (`pine_claims_crt`, `pine_claims_inside_bar`, `pine_claims_outside_bar`) and
  the entry-timing work computed trade outcomes on the D2 cache (14 watchlist
  symbols) with by-year and pre-2025 splits; those aggregates include trades entered
  inside the holdout window. Different strategy family, Quality Flow rules already
  frozen and untouched by them, no QF decision taken from them. Disclosed because the
  bytes overlap, not because influence is plausible.
- **F-A2-4 (daily lane).** BOSWaves (v3 rerun 2026-10-04) and SA-VWAP (2026-10-03/04)
  computed multi-year daily aggregates spanning the window for different systems;
  they informed daily-lane direction only. Tier-0 context per §2.
- **F-A2-5 (negative, post-designation, QF rule set).** No read of holdout outcomes
  for the Quality Flow rule set exists anywhere in the record after 2026-10-03:
  repo history (7 holdout-mentioning commits, all governance/calendar/capture),
  archive history (only the two capture commits ever touch HO paths; the sole later
  archive commit is the DEV-only P7b inventory), the -13 RESULT's hash-only HO
  contact statement, EXP-14B's four DEV-only hash-pinned inputs, CP1's
  forensic-only scope statement, and the 2026-10-15 readiness map ("no holdout files
  exist on this VM; nothing opened" — true of the designated dataset until the
  Oct 23 qualification capture).

## A3 — Seal integrity · Verdict: PASS

Evidence: `evidence/capture_hash_verification.txt`, `evidence/quarantine_census.json`.

- Recomputed this audit: capture store `SHA256SUMS` verify **158/158 OK**
  (equity39-continue) and **13/13 OK** (equity39 first capture); CP1 bundle 3/3 OK.
- Receipt chain: `qualification.json` chain verification **ok = true** — 54 receipts
  chained from GENESIS (child root `c5628652…`, parent `ca498920…`); this audit
  spot-verified raw-file SHA-256 == qualification-recorded SHA-256 for AMD/HO and
  AMAT/DEV (exact matches). The -13 run independently re-verified 158/158 + 22/22
  and the full 54/54 chain on 2026-10-23.
- **Exactly what the evaluability adjudication inspected** (the finding §9 flagged):
  per-bar `datetime` (admission against the pinned 751-session table), the
  `volume == 0` predicate, and the `high > low` range boolean — timestamps plus two
  boolean bar-quality predicates. Outputs recorded: defective-bar **timestamps and
  counts only** (no prices in any quarantine record): 123 price-moving zero-volume
  bars across 23 HO legs, all 2024-04-04→04-22 (`-11`); PLTR/HO 3 bars, Apr 9–10
  2024 (`-10`); SMCI/HO 19 bars across 6 April-2024 dates with admitted count exact
  at 1,583 (`-02`, SMCI_RESOLUTION.md: "No performance use"). No trades, returns,
  P&L, or outcome aggregates were computed from holdout bytes at any point.
- Determination: hashes do not differ, and the inspection was the metadata-class
  quality check A3 itself commissions — A3's contamination limb ("bars, not only
  metadata, were examined" in the outcome sense) is **not** met. Full disclosure:
  `high`/`low`/`volume` are bar fields; the predicates over them are boolean quality
  tests whose only outputs are the defect census that the (outcome-blind) reduced
  universe rests on.

## A4 — Rule genealogy · Verdict: CLEAN (no component designed/selected/adjusted on window data)

| Frozen component | Designed/selected on | Window-data input |
|---|---|---|
| Signal constants (`pine_buy_signal`) | Mike's production Pine system (V5.4/V3.7), Python port pre-Sep 2026; only change 2026-09-20 = int() bug fix restoring intended semantics (both figures exactly reproduced in forensics) | None |
| Exits — Mode B (structural stop, TP1, +1R Profit Protect, 30-bar cap) | Production configuration, frozen for forward test 2026-09-15/19; evaluated (not adjusted) on D1 + 2022 leg 2026-10-03; exit research formally closed — no standalone exit experiment ever run | None |
| Ranking `rs_top2` | Adopted 2026-09-20 from `pine_ranking` backtests on D1-span data; the Sep-24 "ADX beats rs_top2" observation was **not** adopted | None |
| Sector cap, 5% risk gate, position caps | STACK_SPEC / PORTFOLIO production rules; pinned 2026-09-28 by transcription (COPY) from production docs | None |
| Sector map (51-entry SECTOR literal) | Production code artifact; canonical digest `9bab23b7…` hash-pinned | None |
| Benchmark policy (SPY as-of D−1) | Pinned 2026-10-25 (-30, P3) from timestamp mechanics | None |
| Market gate (QQQ/SPY score) | Production `masterscanner_api` (commit `48579180`), copied; grading context only | None |
| Universe UX51 | 2026-vintage composition — hindsight-selection limitation **disclosed** in v0.3 §2 and the 2026-10-04 proposal; G6 Option A adopted with survivorship disclosed. A standing limitation, not an access event | n/a |

The one spanning measurement (F-A2-1) measured already-frozen components and
changed none of them; the candidates it killed (old baseline, lone-wolf overlay)
are not components of the frozen rule set.

## A5 — Human exposure · Verdict: PARTIAL (attestations incomplete)

- **Muse (agent), attested from the record:** executed the Oct-23 captures
  (quality predicates only), the -13 DEV run and EXP-14B (DEV-only, hash-pinned
  inputs), and CP1 forensics (D1 window only). Never computed or viewed
  holdout-window trades, P&L, aggregates, or charts for the Quality Flow rule set.
- **Claude (external reviewer):** received the CP1 bundle (contains the C1
  240-trade ledger — D1 window only) and DEV aggregates in the blind-review packet.
  No holdout outcomes on record.
- **ChatGPT:** adjudications on record address metadata, DEV results, and the
  spanning aggregates above; no window-slice exposure on record.
- **Mike:** **attestation outstanding** (gap G1). His TradingView familiarity with
  2023–24 price action is the class §9 names as unauditable public knowledge —
  disclosed here as the standing residual limitation.

## Evidence gaps

- **G1.** Mike's written A5 attestation not yet collected; ChatGPT/Claude
  attestations documented indirectly, not as signed statements. A5 closes when
  Mike's attestation is logged with the joint outcome.
- **G2.** No OS-level file-access logs exist; A2 rests on git/receipt/bridge
  records (see search log limitation). An unlogged pre-designation look at
  D2/D3/reconstruction bytes cannot be excluded by method — only attested.
- **G3.** The Sep-24 re-baseline's trade count *inside* the window was not computed
  (would require its unarchived ledger; the handover documents the spanning span
  and aggregate, which is what A2 turns on).
- **G4.** D1 generator script and 2022-leg bytes unretained (A1 gaps; spans pinned
  by surviving records; neither can overlap the window).

## Bottom line for the v1.0 assembly

Outcome **Partly contaminated** (evidence-supported), §11 Partly branch applies:
Tier 2 supplementary, Stage A = Tier 3 only on the holdout window, Tier 2's absence
from the confirmatory pool disclosed in every verdict report. Remaining to close B1:
(1) Mike + Muse joint logging of this outcome, (2) Mike's A5 attestation (G1).
The holdout remains **SEALED** — this audit grants no access.
