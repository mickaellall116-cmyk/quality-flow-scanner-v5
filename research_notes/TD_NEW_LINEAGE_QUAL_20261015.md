# TD new-lineage calendar qualification (QF-TD-NEW-LINEAGE-QUAL-20261015-01 r1)

Date: 2026-10-15. Canonical spec: GitHub Issue #1 comment `6183159994`
(preserved verbatim in the evidence dir). Basis: the accepted
NEW_LINEAGE_ONLY lineage record `f95dc0e`
(`TD_CALENDAR_LINEAGE_20261014.md`). Mode: offline/synthetic
qualification only — zero market-data/vendor/model calls, zero credits,
zero spend, zero backtests, zero live-state changes. The live V5.4
harness/state and the standing Python environment were not touched; the
only install target was a disposable venv under `/tmp`, outside the
repo. Wall time ≈ 25 minutes of the ≤60-minute budget; **repair minutes
used: 0** (no repair was needed; every step passed on its first run).

## Verdict: NEW_LINEAGE_CALENDAR_PASS

A disposable environment reproducing the exact proven -12 lock passes
Gate N in full: FX-01..FX-05 with exact equality, twice
byte-identically, and the original `f64d12f` real-calendar integration
suite reproduces 16/16 against immutable source bytes.

**Scope of this verdict, stated plainly: this is a
calendar-qualification verdict for the new lineage only. TD P2 remains
HOLD. P2 v1 remains UNMET. REQ-SPT-08 remains NOT ATTEMPTED. -11
remains UNKNOWN.** Nothing here is a P2 passage, a feed qualification,
or permission for a vendor call.

## 1. N0 environment freeze

Disposable venv: `/tmp/tdqual/venv` (outside the repo, not the standing
environment), built from `/usr/bin/python3`.

| Element | Value |
|---|---|
| Interpreter | CPython **3.12.3** (same patch as the independent -12 rerun; the -12 author used 3.12.14 with identical outcomes) |
| Lock | `integration_requirements.lock` @ `f64d12f`, sha256 `08b38cfa…` (byte-identical copy in evidence) |
| Install method | `pip download` of the exact lock → sha256 captured per artifact → `pip install --no-index --find-links wheels`, so the installed bytes are exactly the hashed bytes. All 11 entries resolved as wheels at the pinned versions; no sdists, no substitutions, no resolver drift. |
| `pip freeze` | Exactly the 11 lock entries, nothing else (evidence `pip_freeze.txt`) |

Resolved versions (all exact): pandas_market_calendars **4.5.1**,
pandas 2.2.3, numpy 1.26.4, pytz 2024.2, python-dateutil 2.9.0,
exchange-calendars 4.13.2, tzdata 2026.5, korean_lunar_calendar 0.4.0,
pyluach 2.3.0, six 1.17.0, toolz 1.2.0.

Wheel sha256 (full list in evidence `wheel_hashes.txt`):
pandas_market_calendars-4.5.1 `7b4f3478…`, pandas-2.2.3 `fffb8ae7…`,
numpy-1.26.4 `675d61ff…`, tzdata-2026.5 `b683bd1b…`,
exchange_calendars-4.13.2 `fc5a2ad0…`, pytz-2024.2 `31c7c181…`.

**tzdata actually in force (recorded, not assumed):** the lock's pip
`tzdata` 2026.5 is installed, but on this box stdlib `zoneinfo`'s
TZPATH is `('/usr/share/zoneinfo', '/usr/lib/zoneinfo',
'/usr/share/lib/zoneinfo', '/etc/zoneinfo')` — i.e. zoneinfo lookups are
served by **OS tzdata 2026c** (dpkg `2026c-0ubuntu0.24.04.1`), with the
pip package present but not on the stdlib search path. The mechanism
itself (`xnys_schedule` via pmc 4.5.1) computes session times through
pytz 2024.2's bundled database. All three tz sources agree on every
2025–2026 US session/DST fact exercised below — that agreement is not
asserted, it is demonstrated by the exact-equality fixture results in
§2. Mechanism under test: `validate_input.py` from the immutable
`f64d12f` tree, sha256 `1b83cdcd…` — exactly the pinned mechanism hash.

## 2. Gate N fixtures (FX-01..FX-05) — exact equality, fail closed

Runner: evidence `gate_n_fixtures.py`, driving the pinned mechanism
(`xnys_schedule` + `expected_1h_starts`) against the frozen
`f95dc0e` expectations (`fixture_expectations.json`). For every open
date the full UTC open/close instants and the complete 1H bar-start
label sets (ET and UTC) must equal the frozen values exactly; closed
dates must return `None` with 0 bars.

| Fixture | Dates | Result |
|---|---|---|
| FX-01 spring DST | 2025-03-07 FULL 14:30Z–21:00Z · 2025-03-10 FULL 13:30Z–20:00Z (one-hour UTC shift across 2025-03-09 asserted) | **PASS / PASS** |
| FX-02 fall DST | 2025-10-31 FULL 13:30Z–20:00Z · 2025-11-03 FULL 14:30Z–21:00Z | **PASS / PASS** |
| FX-03 Thanksgiving window | 2025-11-26 FULL (7 bars) · 2025-11-27 CLOSED (None, 0 bars) · 2025-11-28 EARLY CLOSE 14:30Z–18:00Z, exactly 4 starts (ET 09:30–12:30 = UTC 14:30–17:30) | **PASS / PASS / PASS** |
| FX-04 closed-day window | 2026-07-02 FULL · 2026-07-03 CLOSED · 2026-07-04/05 weekend None · 2026-07-06 FULL; **multi-day all-None conjunct over [2026-07-03, 2026-07-05]: TRUE** | **PASS ×5 + conjunct PASS** |
| FX-05 negative controls | NC1 open instant shifted +1h → detected FAIL · NC2 closed day claimed open → detected FAIL · NC3 one bar start off by one minute → detected FAIL · NC4 unresolvable calendar name raises → FAIL closed, no substitution | **PASS (all 4 controls behave fail-closed)** |

**N2 determinism:** the suite ran twice into fresh outputs;
`fixture_results_run1.json` and `fixture_results_run2.json` are
**byte-identical** (sha256 `3cc0ae06…` each).

## 3. H2 reproduction — original `f64d12f` integration suite

Source bytes were taken from the immutable commit itself
(`git archive f64d12f`) and verified **before** running: all 8
author-pinned `source_sha256` entries from the `f64d12f`
`integration_results.json` match the extracted tree exactly. The suite
was then run unaltered with the disposable environment
(`test_pinned_integration.py --output-dir <fresh dir>`); no accepted
collector/mechanism code was modified in any way.

Result: **16/16 PASS, exit 0** (`integration_results.json`,
`integration_test_output.txt` in evidence). The passed-test set is
identical to both the author record and the independent rerun record;
the dependency block is identical to the author's; the 4 additional
`pilot_harness` files present at `f64d12f` hash-match the independent
rerun's record; `vendor_calls=0`, `credits=0`, `dependency_stubs=false`.
The one runtime warning disclosed in the -12 memo (pandas reindex of
the constructor keep-mask) reproduced identically and remains
disclosed, not repaired. Machine comparison: evidence
`integration_comparison.json`.

## 4. P2-SPOT v2 amendment draft

Per spec step 5, contingent on the PASS above, the minimum amendment
draft is in evidence (`p2_spot_v2_amendment_draft.md`): it references
this new lineage as `NL-20261015`, claims -12 equivalence only in the
Gate N / H2 sense, keeps **-11 UNKNOWN**, keeps **REQ-SPT-08 NOT
ATTEMPTED**, leaves P2 v1 UNMET and the -17 supplement untouched.
**Draft only — not executed, not adopted.**

## 5. Trials and failures disclosure

No failed trials: download, install, freeze, both fixture runs, and
the integration reproduction each succeeded on the first attempt.
Repair allowance (≤15 min) unused: **0 repair minutes**. The only
warning emitted anywhere was the pre-disclosed pandas reindex
UserWarning from the accepted constructor (§3).

Evidence: `research_notes/td_new_lineage_qual_evidence_20261015/` —
spec comment verbatim, lock copy, download report, wheel hashes,
install report, pip freeze, environment probe, fixture runner +
both run outputs, integration output/results/comparison, amendment
draft, `SHA256_MANIFEST.txt`. Deliverables left uncommitted in the
worktree for the parent to commit/push/post.
