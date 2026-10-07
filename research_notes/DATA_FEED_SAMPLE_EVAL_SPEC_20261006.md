# Data-Feed Sample-Evaluation Spec — draft for ChatGPT adversarial review

Date: 2026-10-06. **Amended 2026-10-07** per ChatGPT amendment 6028744990.
Status: **PROPOSAL ONLY — no purchase, no build, no frozen-system change, no holdout spend.**
Author: Muse. Reviewer: ChatGPT. Decider: Mike.

## Context

Two bottlenecks, worked in parallel:
1. **Data:** Yahoo outages/revisions interrupt the forward test and complicate reproducibility (recurring 175–187/250-symbol degraded cycles; Sep 30 13:30 AAPL bar rewritten post-snapshot — fail-closed HALT on V3.6 runner).
2. **Testing machinery:** inconsistent bar construction (the 06:30/10:30/14:30 ET candle failure), missing source files, stale evidence — handled separately by the bounded CP1 evidence-closure lane already running.

This spec defines what "a replacement feed meets our requirements" means, **before anything is bought**. It extends the Sep-28 Yahoo-reliability proposal's P3 alternate-vendor parity gate (redline §R5) with explicit qualification checks. Any feed that passes is a candidate for the forward-test data path; any feed that fails any check in §C1–C4 is disqualified for backtest/forward use regardless of price.

## Amendments (2026-10-07)

Six corrections applied per ChatGPT's bounded amendment. Each is marked
**[A1]**–**[A6]** at the point of application below.

## Sample design (small, read-only, before buying)

- **Symbols:** ~12–20, chosen adversarially: one with an in-window split, one with an in-window dividend, one low-liquidity name, one delisted symbol, plus liquid large-caps for baseline.
- **Window:** overlapping our existing Yahoo 1H cache so every comparison is session-for-session against a known reference.
- **Cost:** use only free tiers/trials; no paid commitment until §Gate.
- **Vendor list (free/low-cost first):** Tiingo IEX intraday (already an observer, see §Tiingo note), EODHD, Benzinga (both named in the earlier free/low-cost tasking), and any other candidate ChatGPT names. Mike has declined $950/mo Intrinio/Zacks — do not propose them as the answer.
- **[A5]** A 12–20-symbol pilot **cannot establish the absence of silent
  rewrites**. The pilot is a discrepancy screen, not a revision-policy proof.
  The spec therefore requires, in addition to the pilot: (a) **planned
  repeated snapshot comparisons** — re-pull the same symbol-days at T+7d and
  T+30d and diff against the retained first snapshot, reporting any changed
  bar as a revision event; (b) **synthetic revision/missing-bar detection
  tests** — inject known revisions and known missing bars into a local copy
  and verify the comparison harness flags them (fault-injection calibration
  of the detector itself). Where the vendor's revision policy cannot be
  evidenced after these steps, report **"revision policy: UNPROVEN"**
  explicitly rather than implying safety from a clean pilot.

## Qualification checks

**C1 — Session construction (hard gate).** Feed must supply historical 1H bars from which we build 09:30/13:30 ET 4H sessions ourselves (never accept vendor 4H bars as given — the fixed-UTC-grid failure is the reason this is a hard gate). Verify:
- Timestamp semantics documented: bar labeled at open or close? Exchange-local (America/New_York) or UTC?
- **[A1]** Session-slot parity vs our Yahoo **comparator** on identical
  symbol-days: same bar count, same OHLCV within tolerance (see C2).
  **Yahoo is a comparator with known defects, not ground truth** — it has
  outages, revisions (Sep 30 AAPL rewrite), and its own adjustment quirks.
  Every observed discrepancy must be triaged into exactly one bucket:
  (i) **candidate-feed discrepancy** (feed differs from comparator on clean
  comparator data), (ii) **reference revision** (the comparator itself
  changed between pulls — evidenced by our retained Yahoo snapshots), or
  (iii) **engine/session error** (our construction or session logic, not the
  feed — e.g., the 06:30-grid class of defect). A discrepancy is only
  chargeable to the candidate feed under bucket (i).
- Early-close days (e.g., day-after-Thanksgiving, July 3): half sessions produce a single 09:30 bar and NO fabricated 13:30 bar.
- DST boundaries: spring-forward/fall-back sessions produce correct bar counts and labels (the parity gate must span a DST boundary, per the standing rule).
- **[A3]** Completed-bar causality, with four separated timestamps per bar:
  **bar label** (what the vendor stamps), **interval end** (when the
  underlying period closes), **actual availability** (when the bar is
  first retrievable from the vendor), and **revision time** (when a
  rewritten bar was last modified, if ever). Causality is judged on
  *availability*, not on the label: **a start label is not look-ahead if
  the bar is only used after its completion/delivery**. Any check that
  conflates "labeled 09:30" with "known at 09:30" is mis-specified.
  Record all four timestamps in the parity corpus.

**C2 — Bar integrity and revisions (hard gate).**
- Gaps: missing 1H bars must be observable (flagged/absent), never silently filled or interpolated.
- **[A2]** OHLCV parity vs Yahoo comparator on overlapping sessions, with
  **per-field tolerances — not one band for everything**:
  - **Denominators stated:** OHLC diffs as |diff| / max(|reference|, floor)
    with the price floor documented (e.g., $1.00) so penny-stock ratios
    don't explode; volume diffs as |diff| / max(reference volume, 1).
  - **Zero-value handling:** explicit rule for zero-volume bars and
    zero-spread (OHLC equal) bars — never divide by zero, never silently
    drop the bar; report the handling in the parity log.
  - **Raw vs adjusted basis:** parity is computed on **raw** OHLCV unless
    both sides document identical adjustment math; adjusted-basis parity
    requires passing C3 first.
  - **IEX vs consolidated scope:** a feed covering IEX-only prints is
    compared against the comparator on IEX-comparable fields only; do not
    penalize an IEX feed for consolidated-volume differences or apply
    the OHLC tolerance to a structurally different volume denominator.
  - **Per-field tolerances (proposed, ChatGPT to adjudicate):** Open/High/
    Low/Close ≤ 0.2% (the Tiingo observer's observed band); Volume ≤ 2%
    on consolidated scope, reported-not-gated on IEX scope; bar-count
    and session-slot mismatches are hard fails regardless of field
    tolerances.
  - **Decision-impact checks:** any parity breach, however small, is
    re-run through the frozen signal logic on the affected symbol-days;
    a breach that flips a BUY/NO decision is a hard fail even inside
    tolerance.
  - **P3 mapping:** the Sep-28 P3 alternate-vendor parity gate (§R5)
    required session-slot parity across a DST boundary with no silent
    fills. This spec **preserves** P3 and extends it: no conflict —
    P3's slot/count requirements are subsumed by C1, and P3's tolerance
    language is superseded by the per-field table above (explicitly
    stricter on volume denominators, looser nowhere).
- **[A5]** Revision policy: does the vendor ever rewrite history? Evidence
  required (not assertion): the repeated-snapshot comparisons and the
  fault-injection calibration from §Sample design. If revisions are
  observed, is each delivered as a detectable event (new marker/version),
  or as a silent overwrite? **Silent overwrites disqualify for
  retained-history use** — our never-rewrite guard cannot defend a feed
  that mutates its own past. If no revision is observed but the evidence
  is thin, report **"revision policy: UNPROVEN"** — do not upgrade a
  clean pilot into a safety claim.

**C3 — Adjustment rules (hard gate).**
- **[A4]** Splits/dividends: document the vendor's **corporate-action
  contract** explicitly — which events adjust prices, the ex-date vs
  pay-date convention, whether splits scale volume, whether cash dividends
  (and what yield threshold) adjust OHLC, and how the vendor handles
  spinoffs. Do not assume the Yahoo contract (splits scale OHLC + volume;
  dividends scale OHLC only) transfers.
- **Freeze the adjustment math:** require raw unadjusted OHLCV **and** the
  actions stream (or equivalent) in the same response; a frozen local
  `apply_adjustment()` must reproduce the vendor's adjusted output on a
  corpus containing in-window splits and dividends (mirrors the Sep-28 P1
  G1 gate).
- **Byte identity is reserved** for retained bytes and deterministic local
  replay (our frozen `apply_adjustment()` on frozen inputs). **Vendor
  comparisons use justified fixed numerical tolerances**, not byte
  identity: state the tolerance per field, the denominator, and why that
  tolerance cannot flip a signal decision (ties to the C2
  decision-impact check). If adjustment math is opaque or irreproducible,
  the feed is disqualified for adjusted-history use.

**C4 — Snapshot retention (hard gate).** License must permit us to retain downloaded snapshots unchanged and hash-anchor them (the never-rewrite discipline only works if the contract allows immutable retention). No retention right = disqualified for the retained-history path.

**C5 — Historical universe coverage (scope limit for longer-history research; separate forward-use requirement).**
- **[A6]** C5 as written is a **historical-research scope limit**: delisted-symbol 1H/daily coverage and point-in-time constituent availability (or documented feasible proxy) so multi-year backtests are not survivorship-biased. Absence remains a scope limit, not a forward-use disqualifier.
- **Forward use has a separate requirement:** a **prospectively pinned
  universe** — the exact symbol list (with additions/removals timestamped)
  that the forward test trades, fixed before the evaluation window and
  versioned thereafter. A feed that covers the pinned universe going
  forward passes the forward-use universe check even with zero delisted
  history; a feed with deep delisted history but no pinned-universe
  discipline does not.
- **Retention rights and operational budget must be evidenced** (C4 license
  terms in hand; C6 rate-limit/cost worksheet completed at our scale)
  **before** any feed is declared usable — "passes C1–C4 on the pilot"
  is necessary but not sufficient for a usability declaration.

**C6 — Provenance and budget.** Document: exchange coverage (IEX-only vs consolidated), bar timestamps vs trade timestamps, rate limits and cost at our scale (250 symbols × 180d 1H refresh + incremental 5d/1h cadence). A feed that passes C1–C5 but cannot serve the cadence budget is viable for research snapshots, not the live forward-test path.

## Gate

A feed proceeds to pricing **only if it passes C1–C4** (C5/C6 scope its use) **and** the [A6] forward-use requirements are evidenced (pinned universe, retention rights in hand, budget worksheet complete). Pricing is requested after qualification, not before. Mike decides whether any paid tier is worth it; the default answer remains free/low-cost or nothing.

## §Tiingo note (what the observer has and hasn't established)

The Tiingo degraded-mode observer (Mike's approved design, local-only, hourly cron) has: filled 67–69 symbols across Oct 1 degraded cycles from IEX intraday; shown bar-level agreement with Yahoo within ~0.16% on sampled parity comparisons; hit its 400/day budget cap Oct 1. This establishes **gap-fill feasibility on the 4H live path**. It has NOT established: adjustment-rule documentation (C3), revision policy (C2 — **UNPROVEN** per [A5], not merely "not established"), early-close/DST session semantics (C1), snapshot-retention rights (C4), or delisted/universe coverage (C5). Tiingo enters the sample evaluation as a candidate on the same terms as every other feed — no incumbency credit.

## Review questions for ChatGPT

1. Are C1–C4 the right hard gates, and are the [A2] per-field tolerances (0.2% OHLC / 2% consolidated volume / IEX volume reported-not-gated) correctly set — too weak/strict anywhere?
2. Is C5 correctly split into the historical-research scope limit and the forward-use pinned-universe requirement ([A6])?
3. Any candidate vendors to add to the free/low-cost sample list — and any to exclude?
4. Does the [A5] repeated-snapshot + fault-injection plan adequately calibrate the revision detector, or is a further step needed?
5. Any conflict between this lane and the Sep-28 P3 parity gate (§R5) or the running CP1 evidence-closure lane? (The [A2] P3 mapping asserts none — confirm or correct.)
6. Are the four separated timestamps in [A3] (label / interval end / availability / revision time) sufficient for the causality check, or is a fifth needed?

No code, no vendor calls, no purchases until the spec clears review and Mike approves the sample evaluation.
