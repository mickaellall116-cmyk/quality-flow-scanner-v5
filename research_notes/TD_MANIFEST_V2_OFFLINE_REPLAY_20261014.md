# TD Manifest V2 + Offline Replay of the Preserved AAPL Receipt

**Task:** QF-TD-MANIFEST-V2-OFFLINE-REPLAY-20261014-11 r1 — offline
only. **Zero vendor/API calls, zero credits, zero spend.** No Twelve
Data contact of any kind (the only network reads were public
Nasdaq/ISO reference files, archived as evidence).
**Basis:** ChatGPT adjudication, Issue #1 comment `6171097855` — the
-09 r2 AAPL XNAS→XNGS mismatch is a V1 declaration-granularity
defect; findings in `TD_VENUE_IDENTITY_ADJUDICATION_20261014.md`
(task -10 r1). Correction channel per the pinned collector's frozen
doctrine: identity corrections are effected by a revised manifest,
never by in-run continuation, and never by editing the collector.

## Verdict

- **Manifest V2 built and validated.** V1 preserved byte-identical
  (sha256 `66a31e10…` before and after). V2 changes **only**
  provenance fields and the `mic_code` of the 39 NASDAQ-pinned
  requests — machine-generated exact diff: **45 differing fields
  (6 provenance + 39 mic_code), 0 disallowed differences**; the 10
  NYSE/XNYS and 2 Cboe BZX requests are deep-equal to V1.
- **Segment MICs resolved for 14/14 NASDAQ symbols, 0 unresolved**,
  each backed by archived authoritative sources (below). No value
  was guessed.
- **Collector validation of V2: 0 manifest errors; preflight: 0
  prerequisite failures** (pinned collector `bd003c3c…`, unmodified).
- **Offline replay: the preserved AAPL receipt now PASSES the venue
  gate under V2 and validates to terminal classification
  `COMPLETE`** (validation scope `session_1h`; the standing
  `CONSTRUCTION_HOLD` for interval semantics INSUFFICIENT was
  emitted, as designed — the 1H→4H construction leg remains held,
  the receipt itself is complete). Details in §4.

## 1. Manifest V2

| Item | Value |
|---|---|
| Path | `research_notes/td_acquisition_adapter_preflight_evidence_20261013/acquisition_manifest_v2.json` (same location/naming convention as V1) |
| manifest_id | `TD-ACQUISITION-MANIFEST-V2-20261014` |
| sha256 | `4a6e3a55ba6cacf80d60c26870817a272534d62cd73eb09d1dfc889d571c547d` |
| Supersedes | `TD-ACQUISITION-MANIFEST-V1-20261013` (V1 file + pin recorded in the `supersedes` field) |
| Status | SPEC ONLY — not executed; supersedes V1 venue_identity mic_code granularity only; dispatch requires separate authorization |

Provenance changes (the only non-mic_code class): `manifest_id`,
`task` (this task), `status`, `supersedes`, and the revision-delta
list — V1's `revision_deltas_vs_r3` key is replaced by
`revision_deltas_vs_v1` (same convention as V1's own naming: deltas
vs the immediate predecessor), recording the granularity reason and
anchors (-10 report, Issue #1 comment 6171097855, this task).
Endpoint, budget (51 requests / 51 credits), windows, identities,
bounds, and every non-NASDAQ request are identical to V1 — proven by
the exact diff, not asserted: `exact_diff_v1_v2.json` (45 differing
fields total; transitions XNAS→XNGS ×31, XNAS→XNMS ×6, XNAS→XNCM
×2; `disallowed_differences: []`; `non_nasdaq_requests_deep_equal:
true`; verdict PASS).

## 2. Per-symbol segment MICs — all evidence-backed

Sources (fetched 2026-10-14 15:01–15:02Z; exact bytes archived in
the evidence dir with hashes in `reference_sources.json`):

1. **Nasdaq Trader official symbol directory**
   `nasdaqlisted.txt` (sha256 `53fcf024…`; file creation footer
   2026-10-14 10:01 ET) — per-symbol **Market Category**.
2. **Nasdaq Trader specification** `nasdaq_symdir_definitions.pdf`
   (sha256 `188df57e…`), Enhanced Nasdaq Symbol Directory —
   Definitions & Data Fields (p.19): **Q = Nasdaq Global Select
   Market, G = Nasdaq Global Market, S = Nasdaq Capital Market**.
3. **ISO 10383 MIC registry** `ISO10383_MIC.csv` (sha256
   `09a0d07b…`): XNAS is the operating MIC (OPRT, "NASDAQ - ALL
   MARKETS"); **XNGS** (SGMT of XNAS) = NASDAQ GLOBAL SELECT MARKET;
   **XNMS** (SGMT of XNAS) = NASDAQ GLOBAL MARKET; **XNCM** (SGMT
   of XNAS) = NASDAQ CAPITAL MARKET — all ACTIVE.

| Symbol | Directory security name | Market Category | Listing tier | Segment MIC in V2 | Requests |
|---|---|---|---|---|---|
| AAPL | Apple Inc. - Common Stock | Q | Global Select | **XNGS** | 7 |
| AMD | Advanced Micro Devices, Inc. - Common Stock | Q | Global Select | **XNGS** | 2 |
| GOOGL | Alphabet Inc. - Class A Common Stock | Q | Global Select | **XNGS** | 2 |
| HOOD | Robinhood Markets, Inc. - Class A Common Stock | Q | Global Select | **XNGS** | 2 |
| META | Meta Platforms, Inc. - Class A Common Stock | Q | Global Select | **XNGS** | 2 |
| MSFT | Microsoft Corporation - Common Stock | Q | Global Select | **XNGS** | 2 |
| NVDA | NVIDIA Corporation - Common Stock | Q | Global Select | **XNGS** | 3 |
| PLTR | Palantir Technologies Inc. - Class A Common Stock | Q | Global Select | **XNGS** | 2 |
| SMCI | Super Micro Computer, Inc. - Common Stock | Q | Global Select | **XNGS** | 2 |
| SOFI | SoFi Technologies, Inc. - Common Stock | Q | Global Select | **XNGS** | 2 |
| SPCX | Space Exploration Technologies Corp. - Class A Common Stock | Q | Global Select | **XNGS** | 2 |
| TSLA | Tesla, Inc. - Common Stock | Q | Global Select | **XNGS** | 3 |
| QQQ | Invesco QQQ Trust, Series 1 | G | Global Market | **XNMS** | 6 |
| ONDS | Ondas Inc - Common Stock | S | Capital Market | **XNCM** | 2 |

**Resolved 14/14; unresolved 0.** AAPL's XNGS is independently
proven by the live -09 r2 receipt itself (`meta.mic_code: XNGS`) and
agrees with the directory. Two values are worth an adjudicator's
eye precisely because they are *not* the top tier: **QQQ → XNMS**
(the official directory lists the QQQ trust as Market Category G)
and **ONDS → XNCM** (Category S). Both are what the authoritative
sources state; neither was "rounded up" to XNGS.

## 3. Collector validation of V2 (pinned bytes, unmodified)

Run from a self-contained `git archive` export of candidate
`7ec0f0e` (export collector sha256 verified `bd003c3c…`;
prerequisites = the candidate's recorded `prerequisites.json`;
archival sources verified by the collector's own
`verify_directory`):

- `validate-manifest` → `{"manifest_errors": [], "requests": 51}`,
  exit 0. (`validate_manifest_v2_output.txt`)
- `preflight` → `{"manifest_errors": [], "prerequisite_failures":
  [], "dispatch": "BLOCKED (zero-call build: no vendor
  transport)"}`, exit 0. (`preflight_v2_output.txt`)

## 4. Offline replay of the preserved receipt under V2

**Receipt (verified before any use):**
`research_notes/twelve_data_stage0/snapshots/acquisition_state/receipts/REQ-P1H-01.rejected.bin`,
sha256 `c47bf899422e4585bcd37055c0e9788c96697b6b47482133e4675bf5cb8dbc18`
= expected pin. ✓

**Setup.** Disposable state dir + disposable limiter ledger under
`/tmp` (both created fresh, both discarded with /tmp). The collector
was constructed exactly as the live run constructs it
(`semantics_status="INSUFFICIENT"`, the candidate's recorded
prerequisites), with the manifest = **V2 reduced to the single
request REQ-P1H-01** — the same single-request reduction the -09
live screen used — and a **local stub transport** that returns the
preserved bytes verbatim. The pinned collector build contains no
vendor transport at all (its built-in transport raises
`TransportDisabled` by construction); the stub replaces only the
`(status, body)` source, and every validation step that ran is the
collector's own production code path (`_handle_response` →
`_validate_bars` → `validate_input.validate`).

**Network isolation (two independent layers).** (1) The replay ran
under `unshare -n` — a network namespace with no external
interfaces. (2) An in-process socket guard replaced
`socket.socket.connect/connect_ex/create_connection` with a
recording blocker. Result: **zero socket connect attempts** during
the entire replay (recorded in `replay_output.json`). No transport
to any vendor was constructed; no DNS, no HTTP, nothing.

**Why not `_verify_receipt` directly (step-8 disclosure).** The
collector's receipt-revalidation entry point requires a prior
RECEIVED + COMPLETED lifecycle pair bound to the manifest digest;
rejected evidence has neither (by design it can never be
"revalidated" into acceptance in place). The `run()`-with-stub
replay above is the closest faithful equivalent: it drives the
identical response-validation path that produced the -09 HOLD. As a
cross-check, after the replay a fresh Collector instance ran
`_verify_receipt` on the receipt the replay produced: **(True,
"ok")**, and that receipt is **byte-identical** to the preserved
payload (sha256 `c47bf899…`).

**Outcome — terminal classification `COMPLETE`:**

| Stage | Result |
|---|---|
| Venue gate (V2: NASDAQ / **XNGS** / USD vs meta) | **PASS** — the -09 HOLD does not recur |
| Values checks | 910 rows; < outputsize 5000; ≤ one-response bound 1323 |
| Bar validation (`validate_input.validate`, scope `session_1h`) | **PASS** — full session-completeness validation over the window |
| Lifecycle | CREDIT_RESERVED → STARTED → RECEIVED (910 rows) → CONSTRUCTION_HOLD → **COMPLETED** |
| Run summary | `{"dispatched": 1, "reused": 0, "completed": 1, "outcome": "COMPLETE"}` (dispatched = to the local stub) |
| Terminal pilot state (disposable) | status ACTIVE, completed [REQ-P1H-01], hold_reason null |

Counts/timestamps only (no bar data anywhere): **910 values**,
first bar **2026-04-01 09:30:00**, last bar **2026-10-06 15:30:00**
— consistent with §6 of the -10 report.

**Standing caveat, unchanged by this result:** COMPLETED carries
`validation_scope: session_1h` and the collector emitted its named
`CONSTRUCTION_HOLD` event ("interval-start semantics INSUFFICIENT
(A6.1); native 4H diagnostic only"). The 1H→4H construction leg
remains held by design; this replay validates the 1H receipt, it
does not un-hold construction and is not a feed or strategy
verdict. (Operational note: full-window bar validation is
CPU-heavy — the replay took ~7.6 min wall, nearly all of it inside
`validate_input.validate`; a re-run's duration is not a hang.)

## 5. Live state untouched — proof

Read-only hashes of the live acquisition state and the live ledger,
taken before and after all work (the replay never opened them
read-write; the receipt was read once, after hash verification):

| File | Before | After |
|---|---|---|
| `pilot_harness/credit_ledger.json` | `4ba4cf6f…` | `4ba4cf6f…` (identical) |
| `acquisition_state/pilot_state.json` | `8c59a56c…` | identical |
| `acquisition_state/lifecycle.jsonl` | `fbdbd1c3…` | identical |
| `acquisition_state/manifest_binding.json` | `324a69ba…` | identical |
| `acquisition_state/receipts/REQ-P1H-01.rejected.bin` | `c47bf899…` | identical |
| V1 manifest | `66a31e10…` | identical |

The live state dir still sits at its -09 terminal state (REQ-P1H-01
attempts 1, status HOLD). **This task does not reconcile it.** Per
the -10 recommendation, a future V2 run must reconcile that
started/HOLD state under the collector's started-state rules, under
a candidate bound to V2, and only with fresh authorization from
Mike for any new credit. Nothing here authorizes a dispatch.

## 6. Unresolved / out of scope

- **None for the NASDAQ segment MICs** (14/14 resolved, evidenced).
- NYSE/XNYS (10 requests) and Cboe BZX/BATS (2, DRAM) are unchanged
  in V2 by design — flagged in -10 as unproven/unresolved, not
  defective; no receipts exist for them and correcting them was out
  of this task's scope.
- V2 requires ChatGPT re-adjudication (it supersedes an adjudicated
  manifest). No candidate is bound to V2 yet; no live use is
  authorized by this task.

## Scope honored

Zero vendor/API calls; zero credits; zero spend (the replay's single
credit reservation hit only the disposable /tmp limiter ledger).
Reference fetches were read-only public Nasdaq/ISO files, archived
with hashes. No changes to V1, the collector, adapter, driver, live
state/store/ledger, or any production/frozen file; no merge.
Deliverables: the V2 manifest (path in §1), this report, and
`research_notes/td_manifest_v2_offline_replay_evidence_20261014/`
(archived reference files + `reference_sources.json`,
`symbol_mic_evidence.json`, `exact_diff_v1_v2.json`, validator/
preflight outputs, `replay_output.json`, `replay_driver.py`).
Secret-isolation scan over all deliverables: **CLEAN** (no
credential, surrogate, or `apikey` value; no bar data — counts and
timestamps only).

**Status: Manifest V2 BUILT + VALIDATED (0 errors); offline replay
COMPLETE under V2. Live acquisition remains HOLD — V2 awaits
ChatGPT re-adjudication, a V2-bound candidate, live-state
reconciliation, and Mike's fresh authorization before any new
dispatch.**
