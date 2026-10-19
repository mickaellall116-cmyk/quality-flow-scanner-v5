# QF-TD-CALENDAR-INTEGRATION-PREFLIGHT-20261019-38 r1 — PREFLIGHT MEMO

**RETURN VERDICT: `DEPENDENCY_ARTIFACT_MISSING__HOLD`**

Static / read-only preflight, one pass over existing committed bytes only. Spec: Issue #1 comment `6278086101` (the -35 r2 adjudication, which dispatched this task). Nothing was installed, imported, executed, fetched, or called. The classifier and validator were read, never run.

**The one missing artifact, named exactly:** the `pandas_market_calendars==5.5.0` distribution wheel (py3-none-any) **and** its transitive pin/hash closure evidence. Neither exists anywhere on this host or in the repository (inventory in `INTERFACE_DEPENDENCY_MATRIX.md` §3). Acquiring it is a network act, explicitly outside this preflight; per spec step 3, any missing exact artifact returns HOLD. Everything else the spec asked for — the interface pin, the compatibility matrix, and the integration-proof preregistration — is complete in this package, so the HOLD rests solely on the dependency artifact.

Elapsed: ~13 min of the ≤45 cap. Repair minutes: 0.

---

## Q1 — The classifier and its pinned calendar interface (at immutable commit `ab254c3458697dd450356146abcf4ad4f75ecef4`)

The classifier is the **EXPECTED_EMPTY_CLOSED_SESSION front-gate** inside the TD lifecycle-repair candidate, branch `td-closed-session-classifier-20261014` (never merged to main; the package directory does not exist on `origin/main`):

| Component | Path (at `ab254c3`) | sha256 (file bytes) |
|---|---|---|
| Classifier / collector | `research_notes/td_lifecycle_repair_candidate/td_min_collector.py` | `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c` |
| Classifier fixture suite | `research_notes/td_lifecycle_repair_candidate/test_closed_session_classifier.py` | `3122bdfc5df432932395948216e4ec6cc50e438abe2518cd0a5984154c4d71d0` |
| P2-SPOT v2 supplement (the pin carrier) | `research_notes/td_lifecycle_repair_candidate/p2_spot_supplement_v2.json` | `cccd52260b2c80a7110559ed100111cf3634e7901daef2f883c6517b68255b31` |
| Pinned validator (mechanism module) | `research_notes/pilot_harness/validate_input.py` | `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58` |

**The pinned validator SHA — what it pins and where it lives.** `1b83cdcd…` is the sha256 of the exact file bytes of `validate_input.py`. The pin lives in the supplement (`calendar.mechanism_module_sha256`) and is independently recorded in the -16 package's `integration_results.json` `source_sha256` map (same value — consistent). At classification time the collector hashes the resolved module file and refuses (returns `None`, fail-closed) on any mismatch.

**Exact calendar call graph** (`td_min_collector.py::_classify_closed_session`, conjunct 3, invoked from `_handle_response` on any non-200 response; returns a calendar-proof record iff EVERY conjunct holds, else `None` and the caller falls through to the existing HOLD path byte-for-byte):

1. Wire/supplement conjuncts first (exact HTTP-400 error-body schema; supplement `P2-SPOT`/`v2` bound to the collector's manifest digest; request preregistered by exact request digest with `expected_bars == 0`).
2. `import pandas_market_calendars as mcal`; **`str(mcal.__version__)` must equal the supplement's `calendar.expected_library_version` = `"5.5.0"`** (exact string equality), else disabled.
3. `import validate_input`; sha256 of its resolved file bytes must equal `calendar.mechanism_module_sha256` = `1b83cdcd…`, else disabled.
4. For **every** date in the request window (`req["start_date"]`..`req["end_date"]`, window ≤ 366 days, iterated day by day): `validate_input.xnys_schedule(pd.Timestamp(date))` must return `None` (closed). Any open date, any exception, any unavailability → `None` (classification disabled, fail-closed).
5. On success the proof record binds `{mechanism, library_version, mechanism_module_sha256, per_date}` under `canonical_digest`.

**The validator's own PMC interface** (`validate_input.py::xnys_schedule`, lines 54–64): deferred `import pandas_market_calendars as mcal`; `mcal.get_calendar("XNYS")`; `xnys.schedule(start_date=day.date(), end_date=day.date())`; empty frame → `None`; otherwise returns `(pd.Timestamp(row["market_open"]).tz_convert("America/New_York"), pd.Timestamp(row["market_close"]).tz_convert("America/New_York"))`. The classifier consumes only the None-vs-tuple distinction; the wider validator (`validate()`, `expected_1h_starts`) consumes the tuple for session-bin construction.

**Evidence for exact PMC 5.5.0 (all committed):** the supplement's `expected_library_version_basis` states the pin derives from the most recent in-repo recorded run of the pinned mechanism — the CP1 audit of 2026-10-04: `research_notes/recovery_4h_20261004/cp1_followup/audit_52symbol.json` records `"mcal_version": "5.5.0"` / `"calendar": "XNYS (pandas_market_calendars 5.5.0); mcal.__version__=5.5.0"`, corroborated by `cp1_evidence_closure/RESAMPLER_XNYS_EVIDENCE.md` ("pandas_market_calendars XNYS v5.5.0, consulting market_open/market_close"). The supplement records that the -11/-12 runtime library version was **not** recorded; any mismatch disables classification (fail-closed).

**Schema/coverage expectations of the classifier:** no schedule file, no coverage window, no artifact input of any kind. Its calendar expectation is purely functional: a live library at the pinned version, a pinned mechanism module, and a per-date closed/open oracle over the request window. Its offline suite (F1–F2 positives, N1–N12 negatives, S1–S3; `test_closed_session_classifier.py`) stubs BOTH the library (a fake module with `__version__ = '5.5.0'`) and `xnys_schedule` — so the real PMC 5.5.0 semantics have never been executed against this classifier. N10 covers calendar-unavailable and version-mismatch (`'9.9.9'`, module removal) failing closed — against the stubs.

## Q2 — Compatibility: the qualified V2 artifact vs the classifier gate

**Verdict: the classifier requires live PMC 5.5.0 semantics through the pinned validator. The qualified `XNYS_SESSION_SCHEDULE_V2` artifact cannot serve this gate, and no adapter can change that without re-pinning the supplement.**

- The classifier has **no artifact input**. Its calendar truth arrives only via `mcal.get_calendar("XNYS").schedule(...)` called from the pinned validator module. The V2 artifact (a JSON file: header `{artifact, exchange, timezone, coverage_start, coverage_end}` + `sessions[]` of `{date, open "HH:MM", close "HH:MM"}` local-time strings, open days only, closed days encoded by absence) is consumed by a different lane's consumer (fold materializer v3, `e1b0dfed…`).
- **An adapter is structurally barred, not merely unbuilt.** Any module that read the artifact instead of the library would be a *different mechanism module*: its bytes would not hash to `1b83cdcd…`, and the classifier's own conjunct 3 would refuse it. Substituting the artifact therefore requires a new supplement version (new `mechanism_module_sha256`, new adjudication) — a governance act, not an integration detail.
- **Where 4.5.1 / 5.5.0 / the artifact meet:** they do not meet. PMC 4.5.1 is the calendar-*generation* environment pin (NL lock `08b38cfa…`, wheelhouse manifest `210b8273…`) and produced the qualified artifact for the fold lane. PMC 5.5.0 is the classifier's *runtime* pin, inherited from the CP1 audit environment. The classifier's exact-string gate returns "disabled" under 4.5.1 by design. Neither pin contradicts the other; they govern different lanes, and nothing in the TD classifier path reads the generation environment's outputs.
- Field/type/boundary detail: `INTERFACE_DEPENDENCY_MATRIX.md` §2. In brief: semantic correspondence exists (date set + open/close times), types differ (tz-aware `America/New_York` Timestamps vs local `HH:MM` strings), the closed-day encoding inverts (empty schedule frame → `None` vs absence from a list), and the artifact's frozen coverage boundary (2024-09-16 → 2026-10-16) has no counterpart concept in the classifier, which iterates whatever window a request carries (≤366 days).
- One statically unverifiable semantic: whether PMC 5.5.0's `get_calendar("XNYS")` resolves the same way as under 4.5.1 (per the -30 audit, PMC's `XNYS` key is the exchange_calendars call-through mirror; PMC's native key is `NYSE`). With the 5.5.0 wheel absent, its resolution path cannot be inspected. The preregistered proof (below) makes this an explicit probe item rather than an assumption.

## Q3 — PMC 5.5.0 offline availability: **NO**

- Persistent wheelhouse `~/workspace/td_nl_wheelhouse_20261016/wheels` holds exactly the 11-wheel **4.5.1** closure (incl. `pandas_market_calendars-4.5.1-py3-none-any.whl`, sha `7b4f3478…`), identical to the committed `integration_requirements.lock` at `ab254c3` (exchange_calendars 4.13.2, numpy 1.26.4, pandas 2.2.3, PMC 4.5.1, pytz 2024.2, tzdata 2026.5, …).
- A filesystem-wide search found **no** `pandas_market_calendars` 5.5.0 artifact anywhere; every other wheel copy on the host (trial wheelhouses in the TD evidence packages, `pf06_scratch`) is also 4.5.1.
- **Transitive closure evidence for 5.5.0 is likewise absent:** no committed lock, manifest, or freeze records PMC 5.5.0's `Requires-Dist` set or any 5.5.0 wheel hash. That set cannot be inventoried without the wheel itself and is not reconstructed here from memory.
- Therefore the integration proof's environment **cannot be built offline today**. Acquiring the exact wheel + closure is a network act requiring its own authorization (see Q5).

## Q4 — The separately versioned offline integration proof (preregistered, NOT executed)

Full preregistration: `INTEGRATION_PROOF_PREREGISTRATION.md`. Shape: a new pinned wheelhouse for the exact 5.5.0 closure (the 4.5.1 wheelhouse and NL lock are **not** modified); an isolated no-network environment; hash gates on every input byte before any execution; a real-mechanism run of the -17 fixture families with the calendar stubs removed in a separately versioned test file; mechanism-probe assertions on synthetic schedule expectations sourced from already-committed primary-record evidence; version/tamper negative family; single-attempt, first-failure-stops, zero repair minutes; family-level accounting fixed in advance (**29 checks**: F2 + N12 + S3 + V4 + P8; any other total = HOLD).

## Q5 — Separability from the live TD lane, and open blockers

**Fully separable.** The proof consumes only committed candidate bytes at `ab254c3` and a new wheelhouse. It does not touch: executor r4 (`e792b8b2…`), the live dry-run adapter (`e8605669…`), Policy A (digest `5d9d82ca…`, Mike's 52-credit ceiling), the source ledger (`7e5ccef0…`) or candidate ledger (`79ff4844…`), the UNUSED -20 transaction, the FRESH manifest (`71aade8b…`), the -04 live driver (`5fed4524…`), or the V5.4 harness (PAUSED/pinned). Zero credits, zero vendor calls, by construction.

**Two binding caveats:**
1. The pinned supplement binds manifest `TD-ACQUISITION-MANIFEST-V2-SPOT8-20261014` (digest `748ca957…`) and preregisters only REQ-SPT-07 / REQ-SPT-08. Even a passed proof qualifies the classifier **only** for that SPOT8-scoped P2-SPOT v2 purpose. Use against the FRESH 51-request manifest would require a new supplement version (new base digest + request entries), separately adjudicated.
2. The classifier + supplement status is `OFFLINE_CANDIDATE_NOT_ADOPTED`. A passed proof is evidence toward adoption; it is not adoption.

**Blockers / decisions only a live step or Mike/ChatGPT can resolve — named, not solved:**
- **B1 (the HOLD):** acquisition of the exact PMC 5.5.0 wheel + transitive closure with hashes — a network act needing a separate explicit GO and its own bounded task.
- **B2:** PMC 5.5.0's `get_calendar("XNYS")` resolution semantics (mirror/call-through vs native) — statically unverifiable with the wheel absent; the preregistered proof probes it, nothing else can.
- **B3:** whether the 5.5.0 pin (a record of a lost CP1 environment) remains the right pin, versus re-pinning the supplement to a qualifiable version — an adjudication question for ChatGPT/Mike; the proof cannot answer it.
- **B4:** adoption of the classifier candidate into any live lane, and any supplement re-versioning for the FRESH manifest — Mike/ChatGPT decisions, downstream of a passed proof.
- **B5 (independent, unaffected):** the TD lane's -20 clearance re-delivery remains pending on its own track; this preflight neither advances nor blocks it.

**Minor evidence note:** the -17 test docstring points to a "-17 evidence directory, real_env_probe" for the real-environment absence probe; no distinct artifact by that name exists in the `ab254c3` tree. The absence behavior is nonetheless established by the code path itself (import failure → `None`) and by N10's module-removal case. Not a blocker; recorded for completeness.

## Prohibitions — confirmation

No package install, import, or execution; no classifier or validator execution; no TD/vendor/API/model call; no credentials, credits, tokens, or spend; no market/OHLC/real-timestamp data read or used (the V2 artifact's committed header/session schema was read as an interface document only — it was not consumed or copied into any TD run); no holdout access; no corrected performance/backtest/tuning; no production/trading/state/ledger mutation; no Issue #9 work. Files changed: only the four new files of this package.
