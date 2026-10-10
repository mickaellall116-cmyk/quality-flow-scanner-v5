# Twelve Data Stage-0 — Offline Verification Report (2026-10-10)

**Task:** QF-TD-STAGE0-OFFLINE-20261010-01 (Issue #1 comments 6097910497 / 6097915716)
**Evidence pin:** commit 4a4680e (Stage-0 execution)
**Scope:** read-only on private snapshots. ZERO vendor calls, ZERO new credits, ZERO performance computations.
**Actual effort:** ~14 minutes.

## 1. Snapshot integrity — VERIFIED

SHA-256 recomputed locally against the committed manifest (`stage0_manifest.json`):

| Snapshot | Expected | Result |
|---|---|---|
| `aapl_1h_2026-09-08_2026-10-06.json` | `c9c19656afaa8d624934ce6eacf0173876109ed367beb4f5186079e8bd1e18dc` | **MATCH** |
| `aapl_4h_2026-09-08_2026-10-06.json` | `3bea69e28dc8af14ec6ee296041a8989735dd0e637d2b0a613b3d9089b85210b` | **MATCH** |

## 2. Derived coverage (counts and ranges only — no raw bars)

- **1h:** 140 bars, 20 trading days, 7 bars/day, labels `09:30, 10:30, 11:30, 12:30, 13:30, 14:30, 15:30` (America/New_York). First day 2026-09-08, last day 2026-10-05.
- **4h:** 40 bars, 20 trading days, 2 bars/day, labels `09:30, 13:30`. First day 2026-09-08, last day 2026-10-05.
- **Gaps:** none. Sep 8 → Oct 5 contains exactly 20 NYSE trading days (Labor Day Sep 7 precedes the window); all 20 present with full bar counts. 140/140 and 40/40.
- Response shape: `{"meta", "values", "status"}` with `status: "ok"`; `meta` carries symbol/interval/currency/exchange_timezone/exchange/mic_code/type. No interval-end column, no per-bar session flags.

## 3. Boundary question — end_date=2026-10-06, last bars Oct 5

**Established (single-observation, this response only):** the date-only `end_date=2026-10-06` behaved as **exclusive** — coverage ends with the Oct 5 session. 2026-10-06 was a Tuesday and a full NYSE session (no holiday), and the request executed 2026-10-10, four days after the Oct 6 close, so a data-lag explanation is implausible. The missing Oct 6 bars are therefore a boundary-semantics effect, **not** a vendor failure. Not a vendor-wide guarantee — recorded as observed behavior for this call.

## 4. Interval semantics — UNKNOWN; construction INSUFFICIENT

The validator (`pilot_harness/validate_input.py`) operates on a canonical interval-end contract: bars keyed by NY tz-aware start, ends derived from expected session boundaries (09:30 anchor), with an optional vendor-documented `interval_end` column that Twelve Data does not supply — its payload has only `datetime`.

Whether Twelve Data's `datetime` is interval-start or interval-end is **not established** by the response:
- Evidence direction favors interval-start (first label 09:30 aligns with session open; an interval-end reading would imply 08:30–09:30 pre-market coverage and a missing 15:30–16:00 hour).
- But a label pattern is not a vendor contract, and the 15:30 bar's post-close extent under an interval-start reading is itself unresolved.

Per the frozen rule (never invent semantics): **`pilot_build.py` was NOT applied** to the snapshots. Construction status: **INSUFFICIENT** pending a documented interval-label contract (vendor docs or a second labeled source). The as_of=2026-10-07T00:00:00-04:00 gate was not exercised.

## 5. Known wrapper gaps (recorded for the future — no fix in this task)

1. Manifest carries no interval-start/end evidence per bar.
2. No straddle disposition recorded (bars spanning session boundaries, e.g. a 15:30 1h bar under interval-start semantics).
3. No per-request receipt timestamps (request sent / response received wall-clock).
4. Wrapper permits overwrite and manual rerun (not idempotent / fail-closed against rerun).

## 6. Failures

None. All checks completed within scope.

## 7. Reproduction

```bash
cd ~/workspace/quality-flow-scanner-v5
python3 - <<'EOF'
import hashlib, json
for iv, exp in [('1h','c9c19656afaa8d624934ce6eacf0173876109ed367beb4f5186079e8bd1e18dc'),
                ('4h','3bea69e28dc8af14ec6ee296041a8989735dd0e637d2b0a613b3d9089b85210b')]:
    p = f'research_notes/twelve_data_stage0/snapshots/aapl_{iv}_2026-09-08_2026-10-06.json'
    h = hashlib.sha256(open(p,'rb').read()).hexdigest()
    assert h == exp, (iv, h)
    v = json.load(open(p))['values']
    print(iv, len(v), 'bars', v[0]['datetime'], '->', v[-1]['datetime'])
EOF
```

Environment: repo at 2b32f61 (working tree; evidence pin 4a4680e), python3 stdlib only.
