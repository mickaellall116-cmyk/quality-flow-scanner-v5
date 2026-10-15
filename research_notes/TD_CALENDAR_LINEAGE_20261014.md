# TD calendar lineage — dependency provenance review (QF-TD-CALENDAR-LINEAGE-20261014-01 r2)

Date: 2026-10-14. Canonical spec: GitHub Issue #1 comment `6182378288` (fetched 2026-10-14 via the unauthenticated public API, HTTP 200 — no fetch limitation). Design basis: ChatGPT's provenance analysis, Issue #1 comment `6180155845` (also fetched). Mode: OFFLINE / READ-ONLY inspection only — zero installs, zero vendor calls, zero data pulls, zero backtests, zero code edits, zero live-state changes. The live V5.4 harness and state were not touched. Both source comments are preserved verbatim in the evidence dir.

## Verdict: NEW_LINEAGE_ONLY

The historical -11/-12 lineage is **not** jointly proven, and the classifier supplement's pin matches **neither** historical run — so no historical-parity claim is available. Any future qualified calendar environment is a **new lineage**, to be qualified on its own fixtures under a separately versioned P2-SPOT v2 protocol, with explicit non-equivalence to -11/-12. Sub-findings (each proven below):

- **-12 (2026-10-13) is PROVEN at `pandas_market_calendars` 4.5.1** — two independent contemporaneous machine records plus the lockfile agree exactly.
- **-11 (2026-10-12) is UNKNOWN** — no record shows a real calendar library executing for -11 at any version: the independent review environment had the library *absent*, and the author's own tests stubbed it. -11's outcomes never depended on a real calendar in any recorded environment, so there is nothing to rehabilitate.
- **The supplement's 5.5.0 pin is PROVEN only for a different lineage** — the CP1 scanner-recovery audit environment of 2026-10-04 — not for any TD run. The pin's basis conflated the CP1 environment with the TD pilot lineage (the exact laundering risk comment `6180155845` flagged).
- The verdict is not BLOCKED: the records are sufficient to decide all of the above. It is not HISTORICAL_LINEAGE_PROVEN: -11 is UNKNOWN and the current pin contradicts the one proven historical version.

## 1. Lineage matrix (element × classification × evidence)

Classifications per comment `6180155845`: PROVEN = exact contemporaneous pin/record; INFERRED = bounded plausible range; UNKNOWN = no pin/record. No element is classified INFERRED — every element either has a contemporaneous machine record or has none.

### A. TD pilot lineage — declared pins

| Element | Class | Evidence |
|---|---|---|
| `pilot_harness/requirements.txt` (2026-10-07): pandas 2.2.3, numpy 1.26.4, **pandas_market_calendars 4.5.1**, pytz 2024.2, python-dateutil 2.9.0 | PROVEN (as the lineage's declared pin) | sha256 `812c526f…`; byte-identical in the main tree and in all three -11 evidence snapshots (`td_integration_review_evidence_20261012/{orig,run,run_h}`) |
| Mechanism module `pilot_harness/validate_input.py::xnys_schedule` | PROVEN | sha256 `1b83cdcd…` — exactly the supplement's `mechanism_module_sha256`; source-verified: imports `pandas_market_calendars`, XNYS schedule per date, returns (open, close) in America/New_York or `None` if closed |

### B. -11 run (2026-10-12, integration review of PR #8 candidate `af49bf4`; memo `TD_INTEGRATION_REVIEW_20261012.md`)

| Element | Class | Evidence |
|---|---|---|
| Review interpreter | PROVEN: CPython 3.12.3 | -11 memo env record |
| Review env pandas / numpy / pytest | PROVEN: 2.1.4 / 1.26.4 / 9.1.1 | -11 memo |
| Review env `pandas_market_calendars` | PROVEN ABSENT (`ModuleNotFoundError`; recorded as a coverage gap) | -11 memo |
| Author-side test env calendar version | UNKNOWN | -11 memo: the candidate's own 19 tests "stubbed every accepted dependency"; no version recorded anywhere |
| **-11 actual runtime calendar version** | **UNKNOWN** | No contemporaneous record of a real library executing for -11 exists. A declared pin (A) is not an execution record. |
| -11 tzdata | UNKNOWN | No record (`pins/` and `prereq.json` in the -11 evidence dir contain no calendar/tzdata pin) |

### C. -12 run (2026-10-13, pinned-dependency integration, commit `f64d12f`; memo `TD_PINNED_INTEGRATION_REVIEW_20261013.md`)

| Element | Class | Evidence |
|---|---|---|
| **pandas_market_calendars** | **PROVEN: 4.5.1** | Lock `integration_requirements.lock` @ `f64d12f`, sha256 `08b38cfa…`; author `integration_results.json` @ `f64d12f`, sha256 `ba8000ec…`; independent `rerun_results.json`, sha256 `8a093a43…` (matches the -12 memo's declared pin) — all three record 4.5.1 |
| pandas / numpy | PROVEN: 2.2.3 / 1.26.4 | Same three artifacts |
| pytz / python-dateutil | PROVEN: 2024.2 / 2.9.0 | Same |
| exchange_calendars | PROVEN present: 4.13.2 (in the freeze; not the mechanism's engine — `xnys_schedule` imports only `pandas_market_calendars`) | Same |
| tzdata (pip package) | PROVEN: 2026.5 | Same |
| Interpreter | PROVEN: author CPython 3.12.14; independent rerun CPython 3.12.3; identical outcomes | Author results + rerun results + -12 memo note 1 |
| Stubs / vendor calls | PROVEN: `dependency_stubs=false`, vendor_calls 0, credits 0 (both records) | Same |
| Real-calendar behavior | PROVEN exercised: real XNYS early-close and spring/fall DST tests passed, 16/16, under 4.5.1 | -12 memo + both results files |

### D. CP1-era records (2026-10-04, scanner 4H-recovery lineage — NOT the TD pilot lineage)

| Element | Class | Evidence |
|---|---|---|
| CP1 audit environment `pandas_market_calendars` | PROVEN: **5.5.0** (for the CP1 audit run only) | `recovery_4h_20261004/cp1_followup/audit_52symbol.json`, sha256 `983d962b…`, records `mcal.__version__=5.5.0` |
| QF-R2 pre-run shell `pandas_market_calendars` | PROVEN: **5.4.0** (installed via pip, 2026-10-04, a different shell the same day) | `research_notes/qf_r2/PRE_RUN_PACKAGE_20261004.md` line 56 |

Two different CP1-era versions on the same day, in different shells, neither of them a TD -11/-12 record.

### E. -14 ephemeral venv (2026-10-14)

| Element | Class | Evidence |
|---|---|---|
| `pandas_market_calendars` 4.5.1 in `/tmp/td14_venv` | PROVEN as recorded (direct filesystem inspection, recorded same-day in the -17 memo §5 correction); artifact itself DESTROYED | -17 memo; verified today: `/tmp/td14_venv` no longer exists (VM replacement; `/tmp` does not persist) |
| Venv provisioning source (what was installed from) | UNKNOWN | No surviving record in the -14 evidence searched |

### F. Standing environment (today, direct inspection 2026-10-14)

CPython 3.12.3 (`/usr/bin/python3`); pandas 2.1.4+dfsg; numpy 1.26.4; pytest 9.1.1; `pandas_market_calendars` ABSENT (import → `ModuleNotFoundError`); pip `tzdata`/`exchange_calendars` ABSENT; system tzdata 2026c (dpkg `2026c-0ubuntu0.24.04.1`). All PROVEN by direct inspection. The standing environment is not any historical environment and proves nothing about -11/-12.

## 2. The 4.5.1-vs-5.5.0 question — RESOLVED as lineage fact

The TD lineage's proven version is **4.5.1** (-12: lock + two independent run records). **5.5.0 is proven only for the unrelated CP1 audit environment.** The supplement (`p2_spot_supplement_v2.json` @ `ab254c34`, sha256 `cccd5226…` — verified today) states its basis verbatim: *"Most recent in-repo recorded run of the pinned mechanism (CP1 audit 2026-10-04 records mcal.__version__=5.5.0). The -11/-12 runtime library version was not recorded…"*. The second sentence was the state of knowledge when -17 was written; the -12 record itself (§1C) supersedes it for -12. For -11 it stands: not recorded because, on the evidence, never really executed.

What remains is a **decision, not a fact gap**, and it is not this memo's to make: (a) re-pin the supplement to 4.5.1 and qualify a new environment anchored to the proven -12 lock, or (b) pin a newer version as an explicitly new lineage. Either path is NEW_LINEAGE_ONLY qualification (§3): changing the pin does not create historical parity for -11, and even the proven -12 environment must pass the fixture tier before any classifier relies on it. This memo re-pins nothing; the -17 candidate and its HOLD are untouched.

## 3. Qualification fixture specification (DESIGN ONLY — not executed)

Two gates, per the split-gate design in comment `6180155845`. No fixture below was run against any environment in this task.

### Gate H — historical-lineage claims (about -11/-12)

- **H1.** A claimed historical environment is admissible only with a contemporaneous machine record: a lockfile **and** a run-results artifact carrying a dependency block with `dependency_stubs=false`. Memos and recollection alone are insufficient. (-12 meets H1; -11 cannot.)
- **H2.** The only admissible historical anchor is the -12 set: lock sha256 `08b38cfa…`, author results `ba8000ec…`, rerun results `8a093a43…`. An environment claiming "-12 equivalence" must install exactly that lock and reproduce the -12 suite's real-calendar outcomes (regular 1H completion, early close, spring + fall DST) identically.
- **H3.** -11 is closed as UNKNOWN. No fixture can rehabilitate it; protocol text implying -11 calendar parity is prohibited.

### Gate N — new-lineage qualification (the only path to classifier reliance)

A future environment (any `pandas_market_calendars` version) qualifies only under a separately approved, isolated, offline task by passing **all** of:

- **N0 — environment freeze.** Record: exact interpreter version; full `pip freeze` with hashes; the pmc version; the tzdata source **and** version actually in force (pip `tzdata` vs OS tzdata — the -12 lineage used pip tzdata 2026.5; the standing box has OS tzdata 2026c and no pip tzdata — these are different evidence and must not be substituted silently); `validate_input.py` sha256 (current pin `1b83cdcd…`, or a successor mechanism with its own supplement version bump).
- **N1 — session fixtures.** For each date, `xnys_schedule` output is compared on **UTC open/close instants and the full 1H bar-start label set (ET and UTC)** — exact equality, no tolerance; a Boolean open/closed check is insufficient. Expected values (derived 2026-10-14 from IANA America/New_York rules via Python `zoneinfo` against OS tzdata 2026c; machine-readable copy in evidence `fixture_expectations.json`):
  - **FX-01 spring DST:** 2025-03-07 FULL, open 14:30Z, close 21:00Z, starts UTC 14:30–20:30 · 2025-03-10 FULL, open 13:30Z, close 20:00Z, starts 13:30–19:30Z. The one-hour UTC shift across the 2025-03-09 transition is the assertion.
  - **FX-02 fall DST:** 2025-10-31 FULL, open 13:30Z, close 20:00Z · 2025-11-03 FULL, open 14:30Z, close 21:00Z (transition 2025-11-02).
  - **FX-03 mixed Thanksgiving window (frozen SPT-05/06 window):** 2025-11-26 FULL (14:30Z/21:00Z, 7 bars) · 2025-11-27 CLOSED (`xnys_schedule → None`, 0 bars) · 2025-11-28 EARLY CLOSE (open 14:30Z, close 18:00Z; exactly 4 starts — ET 09:30/10:30/11:30/12:30 = UTC 14:30/15:30/16:30/17:30; final bar ends at the 18:00Z close).
  - **FX-04 closed-day window (frozen SPT-07/08 window):** 2026-07-02 FULL (13:30Z/20:00Z, 7 bars) · 2026-07-03 CLOSED (None, 0 bars — Independence Day observed; 2026-07-04 is a Saturday) · 2026-07-04/05 weekend non-sessions (None) · 2026-07-06 FULL (13:30Z/20:00Z). Includes the classifier's multi-day conjunct shape: `None` for **every** date in [2026-07-03, 2026-07-05].
  - **FX-05 negative controls:** any fixture date the candidate environment reports open that is specified closed (or vice versa) = FAIL; any UTC instant differing by any amount = FAIL; failure to resolve the `XNYS` calendar at all = FAIL (closed), never a substitute calendar.
- **N2 — determinism.** The fixture suite runs twice in the frozen environment; outputs byte-identical (the -12 rerun standard).
- **N3 — non-equivalence labeling.** The qualified environment is recorded as a NEW LINEAGE with its own version tag. It may claim equivalence to the -12 lock only if the exact -12 lock was installed **and** H2 was reproduced; it may never claim -11 equivalence.

## 4. What does not change

P2 v1 remains **UNMET**; REQ-SPT-08 remains **NOT ATTEMPTED**; the -17 classifier candidate remains **HOLD** on its own terms (this memo neither re-pins its supplement nor qualifies any environment); six receipts plus the SPT-07 HTTP 400 do not qualify the feed (comment `6180155845` decision boundary, reaffirmed); no credits spent; Tiingo untouched (quarantine stands). A P2-SPOT v2 protocol, if ever proposed, is a separate adjudicated act that must carry the §3 Gate N fixtures as its calendar-qualification section.

Evidence: `research_notes/td_calendar_lineage_evidence_20261014/` — both GitHub comments verbatim, `pilot_harness_requirements.txt`, `integration_requirements_lock_f64d12f.txt`, `author12_integration_results_f64d12f.json`, `rerun12_results.json`, `fixture_expectations.json`, `SHA256_MANIFEST.txt`. Deliverables left uncommitted in the worktree for the parent to commit/push/post.
