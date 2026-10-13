# IDEA HARVEST — SPEC v1 (reduced v1, approved scope)

Status: ACTIVE. Mike GO 2026-10-13 15:03 EDT. ChatGPT conditional pass, Issue #1 comment 6152443038.
Scope is FIXED for v1: **harvest → dedupe → ranked shortlist → report / registry DRAFT.**
Test execution, backtests, and registry merges are OUT of scope and stay manual, separately approved steps.

## Purpose

Mike is no longer the idea pipeline. A weekly automated harvest pulls candidate trading
strategies from public research, dedupes them against everything we have already tested
or killed, ranks them by whether we can test them honestly, and delivers a short menu.
Mike taps one or ignores it. Nothing in the harvest runs a test.

## Sources (public web only; zero vendor API calls, zero spend)

1. **Quant papers / abstracts** — arXiv (q-fin), SSRN abstracts, journal pages
   (Journal of Finance, Journal of Financial Economics, Review of Financial Studies),
   author pages, and open-access working-paper PDFs (e.g. LSE Research Online, EconPapers).
2. **Open-source strategy repos** — GitHub repositories that document a strategy rule,
   a preregistration, or a replication of a published claim (spec/idea notes in repos
   count as secondary confirmation, never as the primary source for a claim).
3. **Published research summaries** — reputable secondary write-ups of a primary paper
   (factor-research blogs, papers-with-backtest style summaries). A summary may support
   intake notes but the shortlist entry must cite the primary paper.

Every candidate must carry a URL that was actually fetched during the harvest run.
If a source cannot be verified (page unreachable, claim not found in the source),
the candidate is dropped, not carried on memory.

## Intake fields (required per candidate)

| Field | Content |
|---|---|
| `claim` | The strategy claim in one line, in plain words. |
| `source` | Primary source: authors, title, venue/year. |
| `source_url` | The exact URL fetched in this run. |
| `timeframe` | Formation/holding timeframe the claim names (e.g. daily formation, monthly hold; intraday 30-min windows). "Unspecified" fails intake. |
| `mechanically_definable` | yes/no — can the rule be written as exact code with no discretionary judgment? |
| `pit_data` | yes / no / unknown — can the inputs be obtained point-in-time (as they were known at decision time) from sources we can actually access? Name the inputs. |
| `strategy_family` | Short family tag (e.g. `overnight_intraday_decomposition`, `lottery_max`, `volume_premium`, `anchoring_momentum`, `intraday_momentum`, `volatility_forecast`). |
| `why_testable` | One or two lines: what data, what universe, what the frozen gate would look like. |
| `dedupe_result` | PASS (novel) or REJECTED with the matching registry entry / killed idea named. |

## Dedupe rule (hard gate, applied before ranking)

A candidate is REJECTED if any of these match an existing record in
`research_notes/research_loop/registry.json` (compare against the `experiments[]` fields
`title`, `hypothesis`, `attempted_variations[]`, `failure_strategy_family`), or the
standing killed-ideas record in research notes / MEMORY:

1. Same claim already tested (any state: PASS, FAIL, HOLD, CLOSED).
2. Same strategy family as a closed/killed experiment, where the candidate is a
   re-parameterization (different lookback, threshold, universe, or exit) rather than
   a different mechanism. Goalpost moves and retunes of a dead claim stay dead.
3. Matches a known killed idea from the audit record, including: TOP-50 / quarterly /
   composite ranking filters; laggard veto; DEMA/TEMA/ALMA/VIDYA/FRAMA moving-average
   probes; short-side daily systems; path-signature spike; CRT sweep-and-return
   (`EXP-20261012-CRT-4H`, family `crt_sweep_return`); TimesFM / zero-shot ML price
   forecasting (`EXP-20261012-TIMESFM-SPIKE`); ORB timing-edge claims beyond the
   existing HOLD record (`EXP-20261007-ORB-15M`); VCP fundamental-momentum selection
   beyond the existing Phase 1A record (`EXP-20261007-VCP-1A-*`).

Family adjacency alone is not an automatic reject when the mechanism is genuinely
different (e.g. anchoring-based nearness-to-high vs trailing-return momentum), but the
adjacency must be flagged in `why_testable` and costs novelty points in ranking.

## Ranking rubric (applied in order)

1. **Testability (dominant).** All three required for top tier:
   timeframe named AND mechanically definable AND PIT data obtainable = yes.
   Partial data (e.g. intraday history we cannot yet source at length) demotes.
2. **Novelty** vs our tested families. Untested mechanism > family-adjacent > variation.
3. **Lane fit.** Our lanes: 4H intraday, daily, weekly. A candidate that fits an
   existing lane with data we already handle outranks one needing a new data route.

Output: ranked shortlist of **5–8 candidates maximum**, plus a short
"rejected at dedupe" list showing the rule working. Shortlist quality beats quantity;
fewer than 5 is acceptable if sources don't verify.

## Deliverables per run

- `research_notes/idea_harvest/HARVEST_YYYYMMDD.md` — the ranked shortlist with all
  intake fields filled and per-candidate dedupe results.
- `research_notes/idea_harvest/intake_draft_YYYYMMDD.json` — registry-DRAFT entries
  for the shortlisted candidates, mirroring the registry `experiments[]` field shape,
  every entry marked `"draft": true, "state": "DRAFT-INTAKE-NOT-MERGED"`.
  **The harvest never edits `registry.json` itself.** Merging a draft into the
  registry is a separate, human-approved bookkeeping step.

## Standing bounds

- No test execution, no backtests, no data pulls from vendors, no purchases.
- No changes to scanner, forward-test, or any production code.
- A shortlisted candidate is an *offer*, not a task. A test starts only after Mike
  picks one and a preregistration with a frozen gate is written and reviewed.
- Registry edits happen only via python json load/dump with `indent=2,
  ensure_ascii=False`, and only in the separate approved merge step — never by the harvest.

## Schedule

Weekly, Mondays ~08:15 America/New_York, cron job `idea-harvest-weekly`:
run this spec end to end and deliver the shortlist to the main chat.
