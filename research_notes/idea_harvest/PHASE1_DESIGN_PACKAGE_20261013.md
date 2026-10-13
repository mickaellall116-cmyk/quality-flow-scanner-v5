# PHASE 1 DESIGN PACKAGE — Research Idea-Intake Pipeline

Status: **DESIGN ONLY — submitted for ChatGPT architecture review. No implementation
authorized by this document.** Drafting authorized by Mike directly (main chat,
2026-10-13 16:37 EDT). Requirements source: Issue #1 comment `6153029272`
(fetched and read verbatim, 2026-10-13). Baseline: reduced v1, live since
2026-10-13 (spec `research_notes/idea_harvest/IDEA_HARVEST_SPEC_v1.md`, harvest #1
`HARVEST_20261013.md`, cron `idea-harvest-weekly`).

---

## 1. ACK + scope statement

ACK: Phase 1 = a hardened version of the v1 harvest. V1 already does
harvest → dedupe → ranked shortlist → registry DRAFT. Phase 1 adds the four things
v1 does by hand and cannot prove: **(a)** primary-source intake with provenance
(URL, access date, license, evidence excerpt, limitations, content hash);
**(b)** stable idea IDs + mechanical/semantic dedupe against the registry and the
killed/failed record; **(c)** an append-only queue with idempotency, single-writer
locking, and failure memory; **(d)** a family-level multiple-testing ledger.

Phase 1 is **NOT**, and its code must make structurally impossible:

- No autonomous experiments, no backtests, no test execution of any kind.
- No promotion of any idea to `PREREGISTERED` or `ELIGIBLE`. The pipeline's
  terminal success state is `SHORTLISTED` (handed to Mike). Everything past that
  is the existing human process, outside the pipeline.
- No execution of harvested external code. External repos are read as text
  evidence only; their code is never run.
- No data pulls, no vendor API calls, no spend. Public web pages only.
- No Tiingo use, in any form.
- No changes to production/frozen code, scanner, or forward test; no contact
  with sealed validation data.
- No Claude invocation.
- No edits to `research_notes/research_loop/registry.json`. The pipeline writes
  drafts only; registry merges remain a separate human-approved step (unchanged
  from v1).

Relationship to v1: Phase 1 **extends** v1. The v1 intake fields, dedupe rule,
and ranking rubric carry over unchanged (schema §2 maps them 1:1). The weekly
cron `idea-harvest-weekly` is reused — Phase 1 adds no new schedule (per the
comment's "No new automation").

CRT bookkeeping dependency: task `QF-CRT-REGISTRY-CLOSE-20261013-02 r1` is
already closed and verified on `origin/main` (registry blob `bd2fd37f…`);
nothing in this design reopens it, and no CRT rerun is contemplated anywhere
in Phase 1.

Exit deliverables (implementation phase only, not this document): immutable
code/fixture/registry pins and actual effort, delivered for independent review
before acceptance — same pattern as the TD and TimesFM evidence packages.

---

## 2. Minimal schema

Three record types. All stored as JSON; all timestamps ISO-8601 with timezone;
all hashes SHA-256 lowercase hex. `R` = required, `O` = optional.

### 2.1 Idea card (`ideas/IDEA-*.json`, one file per idea, written once at ingestion, never edited in place — corrections are new queue events, §3)

| Field | Type | R/O | Notes |
|---|---|---|---|
| `idea_id` | string | R | Stable ID, §2.4. Assigned once by the single writer; never reused, never reassigned. |
| `dedup_key` | string (sha256) | R | Hash of normalized claim + primary-source key, §3.3. The idempotency key. |
| `claim` | string | R | The strategy claim in one line, plain words. (V1 field, unchanged.) |
| `claim_normalized` | string | R | Lowercased, whitespace/punctuation-collapsed claim used for dedup comparison. |
| `hypothesis` | string | R | Falsifiable form of the claim, mirroring the registry field of the same name. |
| `strategy_family` | string | R | Family tag (v1 field). Must match an existing family string when the family already exists in the registry/ledger — no synonym drift. |
| `timeframe` | string | R | Formation/holding timeframe as named by the source. "Unspecified" fails intake (v1 rule). |
| `mechanically_definable` | boolean | R | V1 field; `false` ⇒ cannot rank top tier, flagged at intake. |
| `pit_data` | enum `yes/no/unknown` | R | V1 field; when `yes`, `pit_inputs` must name the inputs. |
| `pit_inputs` | string[] | O | Required when `pit_data = yes`. |
| `source` | object | R | See sub-fields below. |
| `source.authors` | string | R | |
| `source.title` | string | R | |
| `source.venue` | string | R | Journal / repo / publisher + year. |
| `source.url` | string (URL) | R | The exact URL fetched in this run. Must have been fetched; no from-memory URLs (v1 rule). |
| `source.accessed_at` | string (datetime) | R | When the fetch happened. |
| `source.license` | string | R | License/access basis of the fetched material (e.g. `open-access author manuscript`, `publisher abstract page — abstract only`, `repo MIT license — text evidence only`). `unknown` is allowed but demotes ranking. |
| `source.evidence` | string | R | Short verbatim excerpt or close paraphrase of the passage that states the claim. This is what makes the card auditable without re-fetching. |
| `source.content_hash` | string (sha256) | R | Hash of the fetched source content, §3.3 note + Open Question 2. |
| `source.is_primary` | boolean | R | Primary source for the claim. Summaries may support but never serve as primary (v1 rule); `false` cards cannot be shortlisted alone. |
| `limitations` | string[] | R | Known weaknesses of the claim/source as stated at intake (data caveats, sample limits, our-lane mismatches). May be a non-empty list only — an empty limitations list fails intake review. |
| `lane_fit` | enum `4H/daily/weekly/none` | R | Which of our lanes the claim fits (v1 ranking input). |
| `created_at` | string (datetime) | R | Ingestion timestamp. |
| `created_by` | string | R | `idea-harvest-weekly` (scheduled run) — the only writer identity in Phase 1. |

Worked example — real candidate, Harvest #1 rank #1:

```json
{
  "idea_id": "IDEA-2026-0001",
  "dedup_key": "sha256:9f2c…(64 hex, over claim_normalized + source key)",
  "claim": "Recent overnight and intraday return components carry opposite, persistent premia.",
  "claim_normalized": "recent overnight and intraday return components carry opposite persistent premia",
  "hypothesis": "High recent overnight-return names keep earning overnight and reverse intraday; each leg is separately predictable.",
  "strategy_family": "overnight_intraday_decomposition",
  "timeframe": "Daily bars; ~1-month component formation, monthly hold",
  "mechanically_definable": true,
  "pit_data": "yes",
  "pit_inputs": ["daily open", "daily close"],
  "source": {
    "authors": "Lou, Polk & Skouras",
    "title": "A Tug of War: Overnight versus Intraday Expected Returns",
    "venue": "Journal of Financial Economics 134 (2019), 192–213",
    "url": "https://researchonline.lse.ac.uk/id/eprint/87481/",
    "accessed_at": "2026-10-13T15:06:00-04:00",
    "license": "open-access author manuscript (LSE Research Online)",
    "evidence": "Working-paper record and abstract state the overnight/intraday expected-return decomposition and its persistence.",
    "content_hash": "sha256:41ab…(64 hex, over extracted canonical text)",
    "is_primary": true
  },
  "limitations": [
    "Long-only legs only for us: short-side daily is a known structural loser here; intraday-reversal leg usable only as avoid/underweight.",
    "Claim is a cross-sectional premium, not a timing signal; needs the broad universe, not the 14-name watchlist."
  ],
  "lane_fit": "daily",
  "created_at": "2026-10-13T15:06:00-04:00",
  "created_by": "idea-harvest-weekly"
}
```

### 2.2 Queue / registry-draft record (`queue/queue_log.jsonl` — append-only event log; `drafts/intake_draft_YYYYMMDD.json` — materialized drafts per run)

The queue log is the system of record for state (§3). Each line is one event:

| Field | Type | R/O | Notes |
|---|---|---|---|
| `event_id` | string | R | `EVT-YYYYMMDD-<seq4>`, monotonic within a run; globally unique. |
| `event_type` | enum | R | `INGESTED`, `DEDUPE_PASS`, `DEDUPE_REJECT`, `RANKED`, `SHORTLISTED`, `REJECTED`, `BLOCKED`, `PARKED`, `SOURCE_DOWN`, `RUN_START`, `RUN_END`. |
| `idea_id` | string | R* | Required for all idea events; null allowed only for `RUN_*` / `SOURCE_DOWN`. |
| `run_id` | string | R | `HARVEST-YYYYMMDD` — ties the event to one harvest run. |
| `from_state` / `to_state` | enum | R* | Required for transition events; must match a legal transition in §3.1. |
| `reason` | string | R* | Required for `DEDUPE_REJECT`, `REJECTED`, `BLOCKED`: the rule or record that fired (e.g. registry experiment ID, killed-idea name). No silent rejections. |
| `rank` | integer | O | Set by `RANKED`; 1-based position in that run's ranking before shortlist cut. |
| `score_breakdown` | object | O | `{testability, novelty, lane_fit}` sub-scores per the v1 rubric — ranking must be reconstructible from the record. |
| `actor` | string | R | `idea-harvest-weekly` for all automated events. (Human overrides are out of Phase 1 scope; if ever added they are separate event types, never edits.) |
| `at` | string (datetime) | R | Event timestamp. |
| `prev_event_hash` | string (sha256) | R | Hash of the previous queue line — a tamper-evident chain over the append-only log. |
| `event_hash` | string (sha256) | R | Hash of this line (excluding `event_hash` itself). |

The materialized draft file keeps the v1 shape (registry `experiments[]` field
shape, `"draft": true, "state": "DRAFT-INTAKE-NOT-MERGED"`) and adds two fields:
`idea_id` (join key to the idea card) and `queue_run_id`. Drafts are regenerated
from the queue log, never hand-edited; regeneration must be byte-stable for the
same log (idempotent materialization).

Worked example — the Harvest #1 ML-forecasting rejection, as a queue event:

```json
{
  "event_id": "EVT-20261013-0007",
  "event_type": "DEDUPE_REJECT",
  "idea_id": "IDEA-2026-0007",
  "run_id": "HARVEST-20261013",
  "from_state": "INGESTED",
  "to_state": "REJECTED",
  "reason": "Family match: supervised ML price/trend forecasting = EXP-20261012-TIMESFM-SPIKE family (CLOSED-FAIL); variation, not a new mechanism (v1 dedupe rule 2).",
  "actor": "idea-harvest-weekly",
  "at": "2026-10-13T15:06:00-04:00",
  "prev_event_hash": "sha256:…",
  "event_hash": "sha256:…"
}
```

### 2.3 Family-level multiple-testing ledger (`ledger/family_ledger.json`, one record per strategy family)

Purpose: make the number of looks at each family a recorded fact, so a family
cannot accumulate silent retries. Counters are **derived** from the queue log +
registry state at materialization time, never hand-incremented.

| Field | Type | R/O | Notes |
|---|---|---|---|
| `strategy_family` | string | R | Same family vocabulary as idea cards and registry `failure_strategy_family`. |
| `intake_count` | integer | R | Ideas ingested into this family (all runs, all time). |
| `dedupe_reject_count` | integer | R | Rejected at dedupe as same-claim/variation. |
| `shortlisted_count` | integer | R | Reached `SHORTLISTED`. |
| `tests_run` | integer | R | Experiments in the registry for this family (any state). Sourced from `registry.json` at materialization; the pipeline reads the registry read-only for this count. |
| `tests_failed` | integer | R | Of `tests_run`, those closed FAIL. |
| `tests_passed` | integer | R | Of `tests_run`, those passed/accepted. |
| `last_test_ref` | string | O | Registry `experiment_id` of the most recent test in the family. |
| `family_state` | enum `open/caution/closed` | R | `closed` = a test closed FAIL and no materially-new-mechanism exception has been recorded; `caution` = ≥1 fail with open questions; `open` = untested. Derived by the stated rule, not by opinion. |
| `updated_at` | string (datetime) | R | Last materialization. |

Worked example — the forecasting family after TimesFM:

```json
{
  "strategy_family": "ml_price_forecasting",
  "intake_count": 2,
  "dedupe_reject_count": 1,
  "shortlisted_count": 1,
  "tests_run": 1,
  "tests_failed": 1,
  "tests_passed": 0,
  "last_test_ref": "EXP-20261012-TIMESFM-SPIKE",
  "family_state": "closed",
  "updated_at": "2026-10-13T15:06:00-04:00"
}
```

(Intake 2 = TimesFM itself via the original route + the E-TRENDS LSTM candidate
rejected at dedupe in Harvest #1. A future candidate in a `closed` family is
auto-flagged at intake and can only proceed with a recorded
materially-different-mechanism justification in its `limitations`/dedupe record —
the v1 adjacency rule, made mechanical.)

### 2.4 Stable ID scheme

- Idea IDs: `IDEA-<YYYY>-<seq4>`, assigned sequentially by the single writer at
  first ingestion, recorded in the `INGESTED` event. IDs are stable for life:
  an idea that is rejected, parked, or later merged into the registry keeps its
  `idea_id`; the registry draft carries it as the join key.
- Sequence state lives in the queue log itself (last `INGESTED` event), not in
  a side counter file — restart-safe by construction (§3.3).
- No ID is ever reused, including for ideas rejected in the same run they were
  ingested.

---

## 3. State-transition procedure

### 3.1 Lifecycle states and legal transitions

```
DISCOVERED ──► INGESTED ──► SHORTLISTED
                  │              ▲
                  ├──► REJECTED (terminal)
                  ├──► BLOCKED-DATA (→ PARKED or, if data route changes, → INGESTED re-check)
                  └──► PARKED (→ INGESTED re-check on a later run, max once per quarter)
```

- `DISCOVERED` exists only inside a run (fetched candidate, not yet carded).
  Nothing persists in `DISCOVERED`.
- `INGESTED`: card written, dedup key computed. From here the idea is permanent
  record, whatever happens next.
- Dedupe runs at ingestion: fail ⇒ `REJECTED` (terminal, with reason). Pass ⇒
  ranking in the same run.
- `RANKED` is a transient in-run state recorded by event; a ranked idea ends the
  run as `SHORTLISTED` (top 5–8), `PARKED` (passed dedupe, below the cut or
  deferred), or `BLOCKED-DATA` (testable in principle, PIT data route unmet —
  Harvest #1 candidates 5 and 6 are the archetype).
- `SHORTLISTED` is the pipeline's terminal success state. There is **no**
  transition out of `SHORTLISTED` inside Phase 1 — selection, preregistration,
  and anything after are human steps outside the pipeline.
- `REJECTED` is terminal and permanent (failure memory, §3.4).
- Illegal transitions (anything not shown) must be refused by the writer and
  logged as a run error, not silently coerced.

### 3.2 Who/what may move an idea

- The **single writer** is the weekly `idea-harvest-weekly` run. It is the only
  process that writes idea cards, queue events, drafts, or the ledger.
- Everything else — Mike, Muse in chat, ChatGPT, ad-hoc scripts — is
  **read-only** against the pipeline store in Phase 1. A human override (e.g.
  Mike un-parking an idea) is expressed as a request in chat and executed by the
  next run as a recorded event, never as a hand edit. (See Open Question 6.)
- Ranking uses the v1 rubric unchanged; the `score_breakdown` on the `RANKED`
  event is the audit trail for every placement.

### 3.3 Idempotency and locking

- **Dedup key:** `dedup_key = sha256(claim_normalized || "|" || primary_source_key)`
  where `primary_source_key` is the source's DOI if present, else its canonical
  URL. Before writing an `INGESTED` event, the writer checks the key against
  every existing card. A hit ⇒ no new card, no new ID; the run logs a
  `DEDUPE_REJECT` (reason: `duplicate ingestion of IDEA-…`) or, if the existing
  idea is live, a no-op note event. Re-running a harvest is therefore safe:
  the second run converges to the same store.
- **Content hash:** `source.content_hash` is taken over the extracted canonical
  text of the fetched page (title + abstract/body text), not raw HTML bytes —
  raw bytes change with ads/timestamps and would break idempotency. Raw-byte
  hash is kept as an optional secondary field when the fetch is a static PDF.
  (Reviewer ruling requested: Open Question 2.)
- **Locking:** a lockfile (`pipeline.lock`, writer PID + run ID + timestamp) is
  taken at `RUN_START` and released at `RUN_END`. A second writer that finds a
  live lock exits and logs nothing. A stale lock (older than 2 hours, or PID
  not running) is broken only at the start of a scheduled run, and the break is
  itself the first event of the new run's log segment.
- **Restart behavior:** the queue log is append-only and hash-chained (§2.2).
  On restart, the writer verifies the chain tail (last `event_hash` recomputes
  correctly) before appending; a chain mismatch aborts the run and surfaces an
  error — it never "repairs" the log silently. Sequence counters (idea IDs,
  event IDs) are recovered from the log tail, so a crash mid-run cannot reuse
  an ID. Events from a crashed run are not rolled back: a half-finished run
  leaves its ideas in their last recorded state, and the next run re-checks
  from the log, which is exactly what the fixtures in §6 test.
- **Materialization:** drafts and the family ledger are pure functions of
  (queue log + registry read). They can be deleted and regenerated at any time;
  they are never a source of truth.

### 3.4 Failure memory

- Every rejection records its reason and the record it matched (registry
  experiment ID, killed-idea name, or ledger family state). "Rejected" without
  a named reason fails intake review.
- Rejected ideas are re-checked on later runs **only** as dedup targets — they
  make future duplicates reject faster; they are never auto-resurrected.
  Resurrection is a human decision, recorded as a new idea with a new ID whose
  card cites the rejected predecessor.
- The family ledger (§2.3) is the second layer: even a *new* claim in a
  `closed` family is flagged at intake, so failure memory works at family
  level, not just claim level. This is the mechanical guard against silent
  retesting and goalpost drift.
- Killed-ideas list: the v1 standing list (TOP/composite filters, laggard veto,
  MA-variant probes, short-side daily, path-signature, CRT family, TimesFM
  family, ORB beyond HOLD, VCP beyond 1A) is seeded as data (a versioned JSON
  file), not hard-coded, so additions are reviewed diffs, not code changes.

---

## 4. Exact proposed sources

V1 source classes, tightened to named sources. All public web, fetched over
HTTPS by the harvest run; no accounts, no keys, no spend. For every source:
what is captured, the license/access basis recorded in `source.license`, and
the failure behavior. **Universal failure rule:** a failed source never blocks
the run and never gets substituted by an unverified mirror; the run logs a
`SOURCE_DOWN` event, drops that source's would-be candidates, and continues.
Two consecutive weekly failures of the same source ⇒ flagged in the run report
to Mike; the source is not silently removed from this list.

| # | Source (named) | Access method | Captured | License/access basis | On failure |
|---|---|---|---|---|---|
| 1 | **arXiv q-fin** (export.arxiv.org listing + abs pages; arXiv PDFs) | Public listing pages + abstract pages | Title, authors, abstract, arXiv ID | arXiv non-exclusive distribution license; abstracts/metadata freely reusable — recorded as `arXiv abstract, metadata reuse OK` | `SOURCE_DOWN`; skip; continue |
| 2 | **SSRN eLibrary** (abstract pages only) | Public abstract pages, low rate | Title, authors, abstract, SSRN ID | Publisher/author abstract page — `abstract only; full text not fetched`. No bulk scraping (SSRN ToS); if rate-limited or blocked, that is a failure, not a cue to retry harder | `SOURCE_DOWN`; skip; continue; repeated blocks flagged after 2 runs |
| 3 | **Journal article pages** — Journal of Finance, JFE, RFS (publisher/DOI pages) | Public article landing pages | Title, authors, abstract where openly shown | `publisher abstract page — abstract only`. Paywalled full text is never fetched or circumvented; a claim not verifiable from the abstract or an open-access version is dropped (v1 rule) | Page unusable ⇒ candidate dropped, not the whole source |
| 4 | **Open-access repositories & author pages** — LSE Research Online, EconPapers/RePEc, university author pages (e.g. Duke faculty pages) | Public record pages + author PDFs | Full working-paper text where openly posted | Repository/author-posted manuscript — recorded per-repo (e.g. `open-access author manuscript`) | `SOURCE_DOWN` per repository; skip; continue |
| 5 | **Papers With Backtest** (paperswithbacktest.com paper pages/PDFs) | Public pages | replication summary + link to primary | Secondary source only — may support intake notes; the shortlist card's primary must be the paper itself (sources 1–4). Repo/site terms as posted | Skip; never blocks a card whose primary verified elsewhere |
| 6 | **GitHub public repositories** (strategy documentation, replications, preregistrations) | Public repo pages/README | Text documentation as secondary confirmation | Per-repo license recorded verbatim (e.g. `MIT — text evidence only`); **code is never executed** (hard scope rule) | Skip; secondary-only, so no card depends on it |
| 7 | **Factor-research summaries** (e.g. established factor-research blogs/write-ups) | Public pages | Pointers to primary papers | Secondary only, same rule as #5 | Skip |

Out of scope as sources (explicitly): social-media reels/posts (Mike's manual
finds can still enter via chat, outside the pipeline), vendor data terminals,
any site requiring login or payment, and Tiingo in any form.

---

## 5. Bounded implementation budget

Estimates are agent work-hours to build Phase 1 **on top of the live v1**,
in separately-approved steps. No step starts until the previous step's pins
are delivered. **Stop conditions are part of the budget, not fine print.**

| Phase | Work | Estimate |
|---|---|---|
| A | Schema + store layout: idea cards, queue log with hash chain, drafts materializer, ledger materializer, killed-ideas seed file | 2–3 h |
| B | Intake hardening: fetch + canonical-text extraction, content hash, license/access capture, `SOURCE_DOWN` handling, drop-on-unverifiable | 3–4 h |
| C | Dedupe engine: dedup-key idempotency, rule matches vs registry + killed list, family matching, claim normalization | 3–4 h |
| D | State machine + locking: legal-transition enforcement, lockfile + stale-lock rule, restart/chain verification, ID recovery from log | 2–3 h |
| E | Synthetic fixtures (§6, all five) + dry-run acceptance on a scratch store; pins + effort report for independent review | 2–3 h |
| F | Cutover: point `idea-harvest-weekly` at Phase 1, first live run, diff vs v1 behavior reviewed before the run counts | 1–2 h |
| | **Total** | **13–19 h** |

**Stop conditions (any one halts the build and returns to review):**

1. Any phase exceeds its estimate by >50%.
2. A fixture in Phase E fails and the fix is not a local correction (i.e. it
   implies a schema or state-machine change) — back to design review.
3. Any step discovers it needs something on the prohibited list (vendor call,
   spend, registry write, new schedule, external code execution). That is a
   scope break, not a problem to engineer around.
4. Chain-verification failure on the real queue log at cutover.

**What cannot be bounded, stated plainly:** *semantic* dedup beyond the
mechanical layer. Dedup-key matching, family matching, and rule matches
against named records are deterministic and inside the estimates above. A
general "is this claim semantically the same idea as that one?" judgment is
**not** mechanically boundable — there is no fixed-cost procedure that proves
two differently-worded claims are or aren't the same mechanism. The design's
answer is to **not automate that layer**: near-matches surface as flagged
adjacency (as v1 already does — cf. the 52-week-high candidate) and a human
confirms at shortlist time. If the reviewer requires automated semantic
similarity (e.g. embeddings), that is a new design decision with its own
tooling/budget question — see Open Question 3 — and Phase 1 as budgeted here
does not include it.

Also not in this budget: backfilling history. The queue starts at cutover;
Harvest #1's six v1 drafts are migrated or frozen per Open Question 5.

---

## 6. Synthetic fixtures plan

Plans only — no fixture code in this document. All fixtures run against a
**scratch store** (temporary copies of the schema files), never the live
queue. Each fixture is deterministic: fixed synthetic inputs, no network
(source responses are canned snapshots), no clock dependence beyond injected
timestamps.

### F1 — Duplicate ingestion
- **Setup:** Scratch store containing one live idea card (known `dedup_key`).
- **Input:** The same candidate submitted twice in one run, and again in a
  second run (three submissions total, identical canonical claim + source).
- **Expected behavior:** Exactly one card, one `idea_id`. Submissions 2 and 3
  produce dedupe/no-op log events citing the existing `idea_id`; no new ID is
  allocated; shortlist contains the idea at most once.
- **Pass criterion:** Store diff after run 2 is empty except the log events
  themselves; ID sequence has no gaps created by duplicates.

### F2 — Restart idempotency
- **Setup:** Scratch store mid-run state: lockfile present, queue log ending
  mid-sequence (some `INGESTED` events, no `RUN_END`), simulating a crash.
- **Input:** A fresh run started against that store.
- **Expected behavior:** Writer verifies the hash chain, recovers ID/event
  sequences from the log tail, handles the stale lock per §3.3 (breaks it only
  under the stated rule and logs the break), and completes without duplicating
  any idea or reusing any ID. Ideas left mid-state by the crash are re-checked
  from the log, not re-ingested.
- **Pass criterion:** Final store contains each synthetic idea exactly once;
  chain verifies end-to-end; no ID collisions; the log shows the crash
  boundary and the recovery explicitly.

### F3 — Source failure
- **Setup:** Canned source set where one named source returns an error/timeout
  snapshot and one returns a page whose text does not contain the expected
  claim (unverifiable).
- **Input:** A normal harvest run over the canned set.
- **Expected behavior:** Run completes. A `SOURCE_DOWN` event is logged for
  the failed source; the unverifiable candidate is dropped (not carded, not
  carried on memory); candidates from healthy sources are processed normally.
  No retries beyond the source's stated behavior, no substitute mirrors.
- **Pass criterion:** Run report lists both failures; zero cards reference the
  failed source or the unverifiable claim; all healthy-source cards are
  present and correct.

### F4 — Rejected idea (failure memory)
- **Setup:** Store seeded with a `REJECTED` idea whose rejection reason cites
  a closed registry experiment (synthetic analogue of the TimesFM-family
  rejection), plus the family marked `closed` in the ledger.
- **Input:** (a) The identical claim resubmitted; (b) a re-parameterized
  variant (different lookback/threshold, same mechanism/family).
- **Expected behavior:** (a) rejects at dedupe citing the original rejection;
  (b) rejects or intake-flags under the family rule with the closed-family
  reason recorded. Neither reaches ranking. The original rejection record is
  unchanged (append-only: new events, no edits).
- **Pass criterion:** Both inputs absent from the shortlist; both log events
  carry named reasons referencing the seeded records; original rejection event
  byte-identical before/after.

### F5 — Blocked gate (scope enforcement)
- **Setup:** Store with a `SHORTLISTED` idea; a canned instruction attempts
  the transitions Phase 1 forbids.
- **Input:** Requests to (a) transition the idea to `PREREGISTERED` or
  `ELIGIBLE`; (b) write a merged entry into a scratch copy of the registry;
  (c) attach a data-pull/vendor step to the idea.
- **Expected behavior:** Every attempt is refused by the writer as an illegal
  transition / out-of-scope write, logged as a run error. The idea remains
  `SHORTLISTED`; the scratch registry is untouched.
- **Pass criterion:** Zero state changes, zero registry writes, three refusal
  events logged with reasons. This fixture is the mechanical proof of the §1
  scope statement.

---

## 7. Open questions for the reviewer

1. **License field semantics.** Is recording the access basis per card (as in
   §2.1) what "license" means in the comment, or is a formal license taxonomy
   wanted? And is abstract-only capture from publisher/SSRN pages acceptable
   as the *evidence* for a card when the full text is paywalled, provided the
   claim is verifiable from the abstract or an open-access version?
2. **Content hash basis.** §3.3 proposes hashing extracted canonical text, not
   raw fetched bytes (raw HTML is unstable across fetches and would break
   idempotency). Confirm, or specify the byte basis you want pinned.
3. **Semantic dedup depth.** The budget assumes mechanical dedup (key +
   family + named-record rules) with human confirmation of flagged
   adjacencies. Does acceptance require automated semantic similarity? If so,
   that is a separate tooling/budget decision — please rule before build.
4. **Ledger scope at cutover.** Should the family ledger be backfilled from
   the full registry history (21 experiments) at materialization — the design
   assumes yes, since counters are derived from the registry read-only — or
   should it count pipeline-era activity only?
5. **Harvest #1 migration.** Migrate the six v1 intake drafts into Phase 1
   cards/queue (assigning `IDEA-2026-…` IDs retroactively), or freeze the v1
   artifacts as-is and start the queue fresh at cutover?
6. **Human overrides.** §3.2 makes everything except the weekly run read-only,
   with overrides executed as recorded events by the next run. Is that
   acceptable for Phase 1, or is an ad-hoc manual-ingestion path (Muse in
   chat, on Mike's word) required in scope?
7. **Schedule confirmation.** Confirm Phase 1 reuses `idea-harvest-weekly`
   (Mondays ~08:15 ET) with no new automation, per the comment — and that the
   harvest's delivery target remains the main chat shortlist post.
8. **State vocabulary.** The draft records reuse the registry-facing state
   string `DRAFT-INTAKE-NOT-MERGED` (v1). Should the queue's internal states
   (§3.1) map onto registry `state` values at materialization, or stay a
   separate vocabulary joined only by `idea_id`?
9. **Acceptance route for fixtures.** Are the five §6 fixtures accepted on
   Muse's delivered pins + outputs (TD/TimesFM pattern), or does ChatGPT
   intend an independent fixture rerun before acceptance?
10. **Build-step authorization.** This package is design-only under Mike's
    2026-10-13 authorization to draft it. The design assumes the build itself
    needs a fresh, explicit Mike GO after this review — please confirm that
    assumption matches the comment's intent, so no claimed or relayed
    authorization is doing silent work at build time.

---

*End of design package. No code, no fixtures, no schedule changes, and no
registry edits accompany this document. Next step is the reviewer's ruling on
§7 and the scope in §1; implementation, if approved, proceeds phase-by-phase
under §5's stop conditions.*
