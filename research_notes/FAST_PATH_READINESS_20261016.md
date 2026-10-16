# Fast-path readiness review (QF-FAST-PATH-READINESS-20261016 r1)

Date: 2026-10-16. Canonical spec: GitHub Issue #1 comment `6221255873`.
Mode: ONE bounded offline review of existing evidence, selected before
execution per the spec. Zero vendor/model/API calls (beyond the public
spec fetch), zero live scans, zero baseline execution, zero downloads,
zero installs, zero spend, zero authenticated GitHub operations, zero
production/frozen-strategy changes, zero tuning, zero holdout access.
Elapsed ~10 minutes of the ≤45 cap; repairs: 0; review passes: 1 (the
initial result is preserved as-is). Standing states unchanged: Yahoo
rev3 PARK, V5.4 PAUSED, TD/Tiingo HOLD, Issue #9 no GO.

## Selected scope: (A) — and why

**Selected: (A) offline reproducible pinned `pandas_market_calendars`
environment for the `ab254c3` classifier, with independent
calendar/session/grid checks and no data adoption.**

Selection rule (spec): the one review that gives the earliest decisive
blocker/verdict. (A) is upstream of (B): every TD P2/SPT-08 step runs
inside this calendar environment, so if the qualified environment
cannot be stood up, (B) is moot regardless of its inventory. (C)'s
readiness map already exists (below) and its blocker is data, not
fixtures. (D) was substantively answered yesterday by the trust-anchor
feasibility memo (PARK; git-carried direction) — re-reviewing it would
be duplicate work. (A) is also the dispatch's named priority.

## Duplicate-work check (done FIRST; nothing below was redone)

| Existing work | Pin | State |
|---|---|---|
| Calendar lineage adjudication (-01 r2): NEW_LINEAGE_ONLY, -12 PROVEN @ pmc 4.5.1, -11 UNKNOWN, 5.5.0 was CP1-audit lineage | commit `f95dc0e`; memo `TD_CALENDAR_LINEAGE_20261014.md` sha256 `3a8baa54…` | accepted record |
| Pinned-dependency integration (-12): 16 checks, collector integration driver preserved | commit `f64d12f`; lock sha256 `08b38cfa…` | PROVEN |
| New-lineage qualification (-01 r1): NEW_LINEAGE_CALENDAR_PASS, Gate N FX-01..FX-05 twice byte-identical, -12 suite 16/16 | commit `7de7950`; memo sha256 `18b80b14…`; evidence manifest 16/16 verified today | PASS (2026-10-15) |
| Classifier NL qualification (-02 r1): NL_CLASSIFIER_PASS, 28/28 real-calendar matrix twice byte-identical | commit `080a6ba`; memo sha256 `52397b4c…`; evidence manifest 20/20 verified today; candidate `ab254c3`, collector sha256 `b683d277…` | PASS (offline scope) |
| Corrected-baseline readiness map (-07): BASELINE_DATA_HOLD, qualified reusable bytes = 0 | `CORRECTED_BASELINE_DATA_READINESS_MAP_20261015.md` sha256 `980c372d…` | covers candidate (C)'s map |
| Capture preflight (-08 r2): calendar-derived session semantics (XNYS 16:00 regular / 13:00 early close; per-symbol C3 early-close case 2025-11-28) | `YAHOO_CLEAN_CAPTURE_PREFLIGHT_20261015.md` sha256 `c9468272…` | covers session-semantics pin |
| CP1 52-pin set (surviving pins of the destroyed D1 cache) | `research_notes/recovery_4h_20261004/cp1_bundle/01_cache_grid/` (`h4_cache_hashes.json`, `bar_timestamps_raw.json`) | evidence only |
| TD P2 execution preflight -04 PASS / full-manifest -05 HOLD / derivation -06 PARKED | evidence dirs `td_p2_spot_v2_*_20261015` (each carries the same `f64d12f` lock copy) | covers candidate (B)'s inventory |
| Trust-anchor feasibility (2026-10-16): PARK + git-carried alternative | commit `e0b4e9f`; memo sha256 `483b5292…` | covers candidate (D) |

No active duplicate work was found for any of (A)–(D); the four lines
are separable exactly as the spec states, and this review executed
only (A).

## Findings — evidence layer: COMPLETE, verified by hash today

Every load-bearing pin of the (A) qualification was re-verified in
this review by content hash (not by trusting the memos):

- Lock: `integration_requirements_lock_f64d12f.txt` sha256
  `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`
  — 11 exact packages: pandas_market_calendars **4.5.1**, pandas
  2.2.3, numpy 1.26.4, pytz 2024.2, python-dateutil 2.9.0,
  exchange-calendars 4.13.2, tzdata 2026.5, korean_lunar_calendar
  0.4.0, pyluach 2.3.0, six 1.17.0, toolz 1.2.0. Byte-identical
  copies sit in four evidence dirs (NL qual, lineage, both -04/-05
  preflights).
- Mechanism: `research_notes/pilot_harness/validate_input.py`
  sha256 `1b83cdcd…` — matches the qualified mechanism hash.
- Candidate: collector extracted from commit `ab254c3` hashes to
  `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c`
  — exact match to the NL-qualification record. The branch exists
  locally and on origin; the candidate is NOT merged to main (by
  design; the TD route is parked).
- Package integrity: NL-qual evidence manifest verifies 16/16;
  classifier-NL evidence manifest verifies 20/20 (both re-run today).
- Determinism records: NL-qual `fixture_results_run1.json` ==
  `fixture_results_run2.json` byte-identical (re-compared today);
  classifier `matrix_results_run1.json` == `run2` byte-identical.
- Independent session/grid checks (as recorded, not rerun — this is
  an evidence review): Gate N FX-01..FX-05 with exact equality —
  spring/fall DST bar starts, early-close and closed-day handling,
  plus FX-05 negative controls NC1–NC4 (shifted open instant,
  closed-day-claimed-open, one-minute-off bar start, unresolvable
  calendar — all detected, fail-closed). The -12 integration suite
  reproduces 16/16 against immutable source bytes. The classifier
  matrix (28/28) exercised the REAL mechanism (no calendar stubbing
  on any positive path) including the preserved SPT-07 rejected
  receipt (`3339c341…`, 180 bytes).
- Re-pinned supplement candidate: `p2_spot_supplement_v2_nl20261015_candidate.json`
  sha256 `9c712330…` — calendar block correctly re-pinned from the
  CP1-derived 5.5.0 to NL-20261015 (4.5.1 / f64d12f); candidate
  only, never adopted.
- tzdata consistency: OS tzdata on this host is still
  `2026c-0ubuntu0.24.04.1` (re-checked today) — the same version the
  qualification recorded as actually serving stdlib `zoneinfo`; the
  mechanism's own session math runs on pytz 2024.2's bundled DB.
  Interpreter: CPython 3.12.3, same as qualified.

## Findings — environment layer: THE DECISIVE BLOCKER

**No live qualified environment exists on this host today.**

- The qualified disposable venv (`/tmp/tdqual/venv`) is GONE — lost
  to a VM replacement, exactly the failure class that destroyed D1.
  Its evidence survives in git; the environment does not.
- The standing system Python has **no** `pandas_market_calendars`
  and no `exchange_calendars` at all (metadata-checked today), and
  its pandas is 2.1.4 — a different pin set (the Yahoo lane's) than
  the NL lock's 2.2.3. Nothing on this host can currently run the
  classifier or the mechanism under the qualified pins.
- **Zero wheels are cached anywhere in the repo** (verified: 0
  `.whl` files). Rebuilding the environment therefore requires the
  -01 procedure's first step — `pip download` of the 11 pinned
  wheels — which is a network fetch, outside this review's offline
  authority. The rebuild itself is fully specified and safe to
  re-run when authorized: download → sha256-verify every wheel
  against the preserved `wheel_hashes.txt` → `pip install --no-index`
  → `pip freeze` must equal the lock exactly → re-record the
  tzdata-in-force. The -01 precedent took ≈25 minutes.

## UNKNOWNs (recorded, not resolved)

- Whether the 11 pinned wheels are still fetchable at their recorded
  hashes from the package index today — not checkable under the
  offline rule; the hash-verification step makes a wrong-bytes
  outcome fail-closed rather than silent.
- Whether a future rebuild lands on a host whose OS tzdata still
  matches 2026c; the -01 procedure records the in-force version, so
  drift would be visible, not hidden.

## Verdict

**FAST_PATH_A_EVIDENCE_READY_ENV_HOLD.**

The calendar qualification evidence chain (lineage → lock → mechanism
→ candidate → fixtures) is complete, internally consistent, and
re-verified by hash today — as *evidence*, (A) is READY, and nothing
needs to be redone. The decisive blocker is operational, not
evidentiary: the qualified environment itself no longer exists and
cannot be recreated offline (no cached wheels). The single unblocking
step is one separately authorized rebuild (~25 min by precedent) with
hash-verified wheels; until then, any work that needs to *run* under
NL-20261015 — including all of candidate (B) — is HOLD at the
environment layer. This verdict adopts no data, qualifies no feed,
and changes no standing state: TD P2 HOLD, P2 v1 UNMET, SPT-08 NOT
ATTEMPTED, -11 UNKNOWN.

— Muse
