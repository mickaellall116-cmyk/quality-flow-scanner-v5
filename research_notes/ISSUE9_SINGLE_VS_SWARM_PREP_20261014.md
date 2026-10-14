# Issue #9 — Single-Model vs Role-Swarm Feasibility: OFFLINE PREP

**Status: PREP_READY** (prep only — not SWARM_PROVEN, not an execution authorization)
**Date:** 2026-10-14 · **Lane:** secondary/backlog, executed after Yahoo feed repair
QF-YAHOO-FEED-REPAIR-20261014-01 r1 per ChatGPT's sequencing (Slack 2026-10-14 16:01 EDT).
**Package:** `research_notes/issue9_single_vs_swarm_prep_20261014/` (hashes: `SHA256_MANIFEST.txt` inside).
**Calls made by this prep: zero** — no model/provider/API/vendor calls, no installs, no spend.

## 1. The question (as specified in Issue #9)
Does **structured multi-role ideation** add unique, falsifiable, nonduplicate Quality Flow
strategy hypotheses versus **one strong-model adversarial brainstorm**, at equal total
inference/review budget? Arm A (control): one capable model proposes, then critiques its
own proposals adversarially under one fixed prompt. Arm B (treatment): the same underlying
model/provider in four segregated roles (proposer, skeptic, feasibility specialist,
synthesis/deduplicator), capped rounds. Explicitly **not** a profitability study: no
return/Sharpe/drawdown/backtest claims; the output unit is the accepted *test specification*.
Sources: Issue #9 (opened 2026-10-14T20:01:11Z); dispatch Issue #1 comment 6177187528;
prior non-authorizing analysis Issue #1 comment 6175664023 (MiroFish critique, PARK/IDEA ONLY).

## 2. What a fair comparison requires (frozen in `comparison_protocol.json` v1.0.0)
- **Same everything except structure:** identical model/provider/version pin for both
  arms; identical fact sheet + killed-family registry + schema; the same seed prompts.
  Role diversity is not model independence and is never reported as independent votes.
- **Three frozen seeds:** S1 4H breakout/RS entries · S2 exits retaining runners while
  controlling adverse excursion · S3 cross-sectional selection/regime filters. Chosen
  without consulting outcome data; holdout data and strategy returns are forbidden inputs.
- **Budgets (per arm per seed, frozen):** ≤120,000 billed tokens (input+output+**reasoning**,
  counted in full — the OmniRoute pilot showed reasoning tokens can consume an entire
  budget); ≤45 min wall; **$0.00 incremental cost, verified before any call**; ≤8 cards.
  Call caps differ structurally (A ≤8, B ≤16) — disclosed; fairness anchors on identical
  token/cost/time caps. >5%-of-cap billed-token divergence on a pair → that pair is
  BUDGET_MISMATCH/inconclusive, reported rather than compared.
- **Blinded rubric (all five gates must pass):** G1 machine-testable + measurable outcome
  with explicit null · G2 no lookahead/survivorship violation (or a precisely specified
  feasible PIT route) · G3 data available for 4H timing, else parked DATA_BLOCKED ·
  G4 not equivalent to a killed/tested family · G5 realistic execution with costs and
  unambiguous timestamps. Synonyms count once; a mechanism accepted from both arms belongs
  to both accepted sets and is incremental for neither (cluster accounting, protocol §rubric).
- **Primary metric:** incremental accepted unique test specifications per total inference
  resource + auditor review time, on paired seeds; absolute numerator and complete budgets
  reported separately. **Stop rules:** zero incremental uniques across 3 pairs, or no strict
  efficiency improvement → PARK/FAIL the swarm approach; >20% untestable cards → close;
  immediate stop on leakage, unverified spend, unauthorized calls, or any backtest/promotion
  trigger. No prompt changes after inspecting outcomes in this version. 3 seeds support
  no statistical generalization.
- **Decisive vs inconclusive:** decisive = all 3 pairs complete in-budget, blind-scored,
  fully ledgered, and a park/fail rule fires or B strictly improves the primary metric.
  Inconclusive = budget mismatch, model substitution/fallback, blinding breach, <3 pairs,
  unresolved grader disagreement, or cost verification impossible.

## 3. Inventory — what exists, what is live, what is a dead end
**Already in the repo (no build needed):**
- **Killed-family registry:** `idea_harvest/phase_a/killed_ideas_seed.json` (seed v1.0.0,
  10 entries with Phase A dedupe semantics) + `research_loop/registry.json` (21 experiment
  records: CRT and TimesFM CLOSED-FAIL; ORB and VCP held) + `research_loop/failure_memory.md`.
  Exported frozen for this study as `killed_family_registry_export.json` (10 mechanical
  entries + 2 context supplements; source hashes inside).
- **Idea-intake infrastructure:** `idea_harvest/phase_a/store.py` with fixtures and
  adversarial test suites — candidate intake/dedupe already exists as a pattern; the swarm
  study feeds it, it does not need a new orchestrator.
- **Fixture discipline precedent:** the OmniRoute utility pilot (2026-10-14) — fixtures +
  ground truth hashed before calls, scoring against ground truth, budgets enforced,
  unspent budget deliberately left unspent. This prep follows the same discipline.

**Routing options (honest status):**
- **Claude direct** — live and reliable (it is the executing/reviewing route today), but it
  exposes no per-call token metering, so it cannot fill the resource ledger comparably for
  two arms. Fails protocol pin requirement (ii) as the *measured* route.
- **OpenRouter direct via the vault-surrogate key** — a real keyed route (custom connector
  on file); free-tier models exist with catalog-verified $0 pricing (the pilot verified one
  pin's 0/0 pricing). This is the only currently plausible execution route, subject to the
  execution-time pin checks (identical model both arms, per-call usage incl. reasoning
  tokens, same-day $0 verification).
- **OmniRoute — DEAD END, adjudicated FAIL/PARK** (utility pilot 2026-10-14, Issue #1
  comment 6176343781): the one zero-cost route returned HTTP 200 with **empty content on
  3/3 jobs** (reasoning model exhausted the token cap); its internal cost ledger is empty
  and proves nothing about charges; 4 of 5 zero-config routes failed outright in setup
  (OpenCode 403 client-lock, Cloudflare Playground 502, zcode 502, uncloseai 499).
  Recorded here as considered-and-closed; the protocol **forbids** it as the route.
- **MiroFish / Zep-style swarm platforms — PARK/IDEA ONLY** (Issue #1 comment 6175664023):
  not installed, not part of this design; Arm B is a role protocol on one model, not a
  third-party swarm product.

**Execution blocker (stated plainly):** today no route is *pre-verified* to satisfy all
four pin requirements simultaneously. That verification is an execution-time act; if it
fails on the day, the run does not start and the comparison is reported blocked — the prep
does not paper over this.

## 4. The prep package (all in `issue9_single_vs_swarm_prep_20261014/`)
| file | contents |
|---|---|
| `comparison_protocol.json` | Frozen design: question, arms, seeds, budgets, rubric, metrics, stops, decisive/inconclusive, authorization boundary |
| `fact_sheet.md` | The identical factual input for both arms (system, available vs unavailable data, standing rules, decided families) |
| `seed_prompts.md` | Registered verbatim prompts: shared framing, S1/S2/S3, Arm A self-critique, Arm B's four role prompts, order rule |
| `killed_family_registry_export.json` | Frozen dedupe export from the two canonical repo sources, with source hashes |
| `hypothesis_schema.json` | Card schema — Issue #9's required field list verbatim + screening declarations block |
| `resource_ledger_schema.json` | Per-arm-seed token/cost/wall-time/reviewer ledger schema |
| `grader_packet.md` | Blinding procedure, role separation, scoring worksheet, hash-order blinding evidence, fail-closed controls |
| `fixtures/` | 7 synthetic prewritten S1 cards (both arms) + expected verdicts — authored to exercise every verdict path |
| `tools/validate_and_grade.py` | Offline stdlib validator + blind grader + dedupe screen; refuses non-synthetic fixtures |
| `dry_run/` | Anonymized packet, blinding key, results, zero-call ledger example (reproducible: byte-identical across runs) |
| `SHA256_MANIFEST.txt` | sha256 of every package file + this memo |

## 5. Dry-run result (synthetic fixtures — pipeline evidence only)
7 cards graded blind (packet verified free of arm labels; shuffle seed 9):
**2 PASS** (one is the survivor of a cross-arm duplicate cluster), **1 DUPLICATE_OF**,
**1 DEDUPE_REJECT** (composite ranking filter → KILLED-TOP-COMPOSITE-FILTERS),
**1 FAIL** (G2: same-bar-close entry on reported EPS — leakage, no PIT route),
**1 DATA_BLOCKED** (level-2 order-book data unavailable), **1 SCHEMA_INVALID**
(missing null + falsification test). All 7 matched the pre-registered expected verdicts.
Two defects were found and fixed during the dry-run itself: validation must run on raw
cards *before* anonymization strips a schema-required field, and cross-arm duplicate
credit must be set-based, not packet-order-based (both now encoded in tool + protocol).
The dry run says nothing about whether a swarm out-ideates a single model — the cards
were authored to hit each verdict path. It proves the *measurement pipeline* works
end-to-end before any real output exists to measure.

## 6. What this prep does NOT authorize
Any provider/model/API call of any kind · running Arm A or Arm B · OmniRoute use ·
installations or new accounts · any spend · backtests or performance evaluation of any
generated or fixture idea · holdout access or unsealing · forward/live trading ·
production or frozen-strategy changes · treating fixture cards as real hypotheses
(they are synthetic test data, tagged as such).

## 7. What a run would need (next authorization boundary)
1. ChatGPT review/adjudication of this prep packet (per Issue #9's review loop).
2. Mike's **explicit execution authorization** for the comparison run (Issue #9 requires
   separate execution authorization; prep approval does not carry over).
3. An execution-time model pin satisfying all four protocol requirements, with
   zero-incremental-cost verification evidence recorded in a fresh run manifest
   (order coin, prompt hashes, budget block) **before** the first call.
4. Even after a run: any backtest of surviving specifications needs its own fresh
   approval plus the qualified historical feed, clean bar grid, untouched holdouts,
   cost model, multiple-testing accounting, and portfolio replay. Nothing auto-deploys.

**Blockers for prep: none. Status reported: PREP_READY.**
