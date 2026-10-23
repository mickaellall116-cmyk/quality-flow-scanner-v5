# CONTINUATION CARD — QF-TD-PILOT-ADJUDICATION-20261023-02

## NOT EXECUTED / USER GO REQUIRED — TWO SEPARATE CARDS

Nothing in this package authorizes or executes a vendor call. The
two continuations below are SEPARATE: a GO for one is not a GO for
the other, and NEITHER is bundled into, or a substitute for, the
Step-2 full capture (146 expected / 289 worst program totals,
ceiling 300 vs ~320 — that decision still binds only at the
capture GO). Credit math is BLOCK-BRACKET-10 (repair -91: unit
cost 1 credit/call; sequential blocks of ≤10 attempts; one
`/api_usage` read opens a phase and one closes every block, chained;
phase total = attempts + (blocks + 1) reads; ≤2 attempts per leg).
Program Twelve Data spend to date: **18 credits** (Day-1 probe 8,
pilot 10). Free tier, 800/day, $0, existing vault key sufficient
for both cards.

## Card A — BTC stamp-phase pilot (its own GO)

- **Purpose:** close pilot gate criterion (iv), the only pilot
  criterion left undetermined: confirm on actual bytes that
  BTC-USD 1h bar stamps sit on the adopted S-C1…S-C6 session grid
  ([D 09:30 ET, D+1 09:30 ET), absolute-instant expectations,
  checker candidate-2 crypto mode) before any crypto leg of a
  full capture is contemplated.
- **Scope:** BTC-USD only, the 6 manifest chunks (HO-C1, HO-C2,
  DEV-C1…C4), `/time_series` 1h, `adjust=splits` (provider form as
  piloted), `outputsize=5000`, order ASC, timezone
  America/New_York — request form identical to the equity pilot.
- **Credits (BLOCK-BRACKET-10):** expected — 6 attempts, 1 block,
  2 reads = **8**; worst — 12 attempts, 2 blocks, 3 reads = **15**.
  Program total after Card A: 26 expected / 33 worst-case-to-date.
- **Destination:** qf-data-archive `captures/td_pilot_btc_<date>/`
  (append-only, SHA256SUMS re-fetch verified) + byte-identical
  local store; receipts hash-chained to the manifest root
  `79ccdd12…` lineage via the pilot receipt schema.
- **Abort conditions (any one stops the run; partial bytes are
  quarantined UNQUALIFIED, never silently completed):**
  `/api_usage` shows `plan_daily_limit` ≠ 800 (fields
  `daily_usage`/`plan_daily_limit` read explicitly — the -69
  misread check); any chunk returns exactly 5000 rows (truncation
  defect); any leg exhausts its 2-attempt bracket; any
  receipt-chain break; any chunk whose stamps do NOT land on the
  adopted grid (that is the test failing — verdict FAIL, bytes
  quarantined, no relabeling to a midnight grid); any
  price-moving zero-volume anomaly class on a chunk (the SMCI
  rule, generalized) → quarantine + stop.
- **What Card A does NOT do:** no other crypto pair (ETH/SOL/
  DOGE/AVAX/LINK/XRP remain untested after Card A), no SMCI leg,
  no full capture, no performance, no shadow launch.

## Card B — SMCI disposition (a DECISION, then at most one leg)

SMCI/HO stands classified **NOT_EVALUABLE_PROVIDER_VOLUME**
(ADJUDICATION.md Result 2). That classification is not undone by
spending credits: a re-ask of the same leg is a retry of a
documented provider-volume failure and is **not offered** on this
card. The decision Mike/adjudication owns, with consequences
stated in COVERAGE_IMPACT.md:

- **B1 — Accept and proceed at baseline time with disclosed
  43/44 HO coverage.** Zero credits. Membership frozen; the
  exclusion-by-classification is written into the baseline's own
  record; C1 comparability break disclosed. This decision is
  needed only when a baseline GO is drafted — it does not have
  to be taken now.
- **B2 — Elect SMCI/DEV-only capture** (1 leg, same request form,
  DEV window 2024-09-16→2026-10-16). Credits (BLOCK-BRACKET-10):
  expected — 1 attempt, 1 block, 2 reads = **3**; worst — 2
  attempts, 1 block, 2 reads = **4**. Stated plainly: **B2 does
  not cure the HO hole and has no qualification value until a
  B1/B3 disposition for HO exists** — it only pre-positions the
  DEV leg. Same abort conditions as Card A, plus the SMCI rule:
  a price-moving zero-volume finding on the DEV leg quarantines
  it and extends the classification by evidence, not by analogy.
- **B3 — Defer SMCI entirely** pending an SMCI/HO evidence route
  that does not currently exist (see COVERAGE_IMPACT.md §2b).
  Zero credits. The coverage record stands as the blocker.

## What neither card includes

No Step-2 full capture; no adoption of guard v3 / checker v3
(G3/G4 stay separate GOs); no holdout strategy use (any W-HO bytes
remain qualification-only and the holdout stays sealed); no
performance computation; no production or frozen-strategy change;
no shadow launch; no purchase or paid upgrade.

— Muse
