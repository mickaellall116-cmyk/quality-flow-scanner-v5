# Data-Feed Sample-Evaluation Spec — draft for ChatGPT adversarial review

Date: 2026-10-06. Status: **PROPOSAL ONLY — no purchase, no build, no frozen-system change, no holdout spend.**
Author: Muse. Reviewer: ChatGPT. Decider: Mike.

## Context

Two bottlenecks, worked in parallel:
1. **Data:** Yahoo outages/revisions interrupt the forward test and complicate reproducibility (recurring 175–187/250-symbol degraded cycles; Sep 30 13:30 AAPL bar rewritten post-snapshot — fail-closed HALT on V3.6 runner).
2. **Testing machinery:** inconsistent bar construction (the 06:30/10:30/14:30 ET candle failure), missing source files, stale evidence — handled separately by the bounded CP1 evidence-closure lane already running.

This spec defines what "a replacement feed meets our requirements" means, **before anything is bought**. It extends the Sep-28 Yahoo-reliability proposal's P3 alternate-vendor parity gate (redline §R5) with explicit qualification checks. Any feed that passes is a candidate for the forward-test data path; any feed that fails any check in §C1–C4 is disqualified for backtest/forward use regardless of price.

## Sample design (small, read-only, before buying)

- **Symbols:** ~12–20, chosen adversarially: one with an in-window split, one with an in-window dividend, one low-liquidity name, one delisted symbol, plus liquid large-caps for baseline.
- **Window:** overlapping our existing Yahoo 1H cache so every comparison is session-for-session against a known reference.
- **Cost:** use only free tiers/trials; no paid commitment until §Gate.
- **Vendor list (free/low-cost first):** Tiingo IEX intraday (already an observer, see §Tiingo note), EODHD, Benzinga (both named in the earlier free/low-cost tasking), and any other candidate ChatGPT names. Mike has declined $950/mo Intrinio/Zacks — do not propose them as the answer.

## Qualification checks

**C1 — Session construction (hard gate).** Feed must supply historical 1H bars from which we build 09:30/13:30 ET 4H sessions ourselves (never accept vendor 4H bars as given — the fixed-UTC-grid failure is the reason this is a hard gate). Verify:
- Timestamp semantics documented: bar labeled at open or close? Exchange-local (America/New_York) or UTC?
- Session-slot parity vs our Yahoo reference on identical symbol-days: same bar count, same OHLCV within tolerance (see C2).
- Early-close days (e.g., day-after-Thanksgiving, July 3): half sessions produce a single 09:30 bar and NO fabricated 13:30 bar.
- DST boundaries: spring-forward/fall-back sessions produce correct bar counts and labels (the parity gate must span a DST boundary, per the standing rule).
- Completed-bar causality: no bar labeled with information not yet available at its timestamp.

**C2 — Bar integrity and revisions (hard gate).**
- Gaps: missing 1H bars must be observable (flagged/absent), never silently filled or interpolated.
- OHLCV parity vs Yahoo reference on overlapping sessions: max |diff| ≤ 0.2% on all four fields (the Tiingo observer's observed agreement band, tighter if ChatGPT requires).
- Revision policy: does the vendor ever rewrite history? If yes: is the revision delivered as a detectable event (new marker/version), or as a silent overwrite? **Silent overwrites disqualify for retained-history use** — our never-rewrite guard cannot defend a feed that mutates its own past.

**C3 — Adjustment rules (hard gate).** Splits/dividends documented with exact rules (splits scale OHLC + volume; dividends scale OHLC only — the Yahoo contract). Require: raw unadjusted OHLCV **and** the actions stream (or equivalent) in the same response; a frozen local `apply_adjustment()` must reproduce the vendor's adjusted output byte-identically on a corpus containing in-window splits and dividends (mirrors the Sep-28 P1 G1 gate). If adjustment math is opaque or irreproducible, the feed is disqualified for adjusted-history use.

**C4 — Snapshot retention (hard gate).** License must permit us to retain downloaded snapshots unchanged and hash-anchor them (the never-rewrite discipline only works if the contract allows immutable retention). No retention right = disqualified for the retained-history path.

**C5 — Historical universe coverage (needed for longer-history stock research).** Delisted-symbol 1H/daily coverage, and point-in-time constituent availability (or a documented feasible proxy) so multi-year backtests are not survivorship-biased. Report coverage honestly; absence is a scope limit, not a disqualifier for the forward-test use case — but any claim about "what works period" on multi-year data must pass through this check.

**C6 — Provenance and budget.** Document: exchange coverage (IEX-only vs consolidated), bar timestamps vs trade timestamps, rate limits and cost at our scale (250 symbols × 180d 1H refresh + incremental 5d/1h cadence). A feed that passes C1–C5 but cannot serve the cadence budget is viable for research snapshots, not the live forward-test path.

## Gate

A feed proceeds to pricing **only if it passes C1–C4** (C5/C6 scope its use). Pricing is requested after qualification, not before. Mike decides whether any paid tier is worth it; the default answer remains free/low-cost or nothing.

## §Tiingo note (what the observer has and hasn't established)

The Tiingo degraded-mode observer (Mike's approved design, local-only, hourly cron) has: filled 67–69 symbols across Oct 1 degraded cycles from IEX intraday; shown bar-level agreement with Yahoo within ~0.16% on sampled parity comparisons; hit its 400/day budget cap Oct 1. This establishes **gap-fill feasibility on the 4H live path**. It has NOT established: adjustment-rule documentation (C3), revision policy (C2), early-close/DST session semantics (C1), snapshot-retention rights (C4), or delisted/universe coverage (C5). Tiingo enters the sample evaluation as a candidate on the same terms as every other feed — no incumbency credit.

## Review questions for ChatGPT

1. Are C1–C4 the right hard gates, or is any of them too weak/strict (e.g., the 0.2% parity band)?
2. Is C5 correctly scoped as a scope-limit rather than a disqualifier for the forward-test path?
3. Any candidate vendors to add to the free/low-cost sample list — and any to exclude?
4. Does the sample design (§Symbols/~12–20, overlapping Yahoo cache) give enough power to detect a vendor that silently revises history, or is a dedicated fault-injection step needed?
5. Any conflict between this lane and the Sep-28 P3 parity gate (§R5) or the running CP1 evidence-closure lane?

No code, no vendor calls, no purchases until the spec clears review and Mike approves the sample evaluation.
