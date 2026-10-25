# -31 — P6 full-grid exposure sampling repair (bounded, P6 only)

Governing: ChatGPT's independent -30 verdict (Slack thread TS
1792945625.327969, 2026-10-25 12:27 ET) — P8 / P2 / P3 / P9 PASS
(bounded); **P6 HOLD**. Successor to
`equity43_dev_measurement_fixes_20261025_30/`; the -30 package is
byte-untouched (its code and artifact hashes are pin-checked by
this package's verifier).

## The defect (as held)

The -30 `exposure_report.py` states the reporting contract at its
lines 13–19 — exposure at **each event timestamp** — but its
`compute_exposure()` defined `samples` as the distinct **entry
times only**. Exit and equity-mark timestamps were omitted. A loss
realized at an exit reduces the equity denominator while other
positions remain open, so entry-only sampling can miss the true
peak and distort the mean and the maximum single-position share.
The reported peak 2.7859x and mean 1.18x were therefore not
qualified as the run-level exposure statistics.

## The repair (sampling only — no sizing, no strategy change)

`code/exposure_report.py` (successor) reconstructs positions
exactly as -30 did (entry notionals from the -13 ledger entry/stop
+ the frozen sizing rule; sizing bases A/B unchanged) and changes
only the sampler:

- **Full committed grid.** Samples = the union of every entry
  timestamp, every exit timestamp, and every timestamp of the
  committed -29r all-bar equity series (the repaired,
  session-table-binned series): **964 timestamps** (173 entry,
  148 exit, 63 coincident entry+exit; every entry/exit timestamp
  is also a series timestamp, so the union is the series grid).
- **Convention — POST-EVENT at coincident timestamps**, stated in
  the code and in the artifact: a position is open at t iff
  `entry_time <= t < exit_time` (an exit stamped at t is closed,
  an entry stamped at t is open), and equity at t is the last
  committed-series mark at or before t **in committed order** —
  where a bar_close mark and an event mark share a timestamp
  (340 such timestamps), that is the event mark: equity after the
  events stamped at t, realized exit P&L included. Disclosure:
  the -30 sampling equity resolved coincident timestamps to the
  larger of the two mark values (an artifact of sorting
  (timestamp, value) tuples); the artifact's `convention_bridge`
  block isolates that tie-break's effect (below).
- **Fail-before fixture** (`tests/test_p6_grid.py`, 16 checks):
  position A (notional 600) exits at t2 realizing a loss that
  drops equity 1000 → 400 while position B (notional 900) remains
  open. The pinned -30 sampler (executed in-lane) reports peak
  **1.5** — it misses the exit-timestamp peak entirely; the
  full-grid sampler measures **2.25** at t2 exactly. A second
  fixture pins the coincident convention (exit + entry at one
  timestamp, bar_close 1000 / event 800 marks: the sample is
  300/800 = 0.375 — exiting position excluded, entering position
  included, event-mark equity).

## Corrected figures (full grid) beside the superseded ones

| statistic (basis A) | superseded (entry-only, -30) | corrected (full grid, -31) | Δ |
|---|---|---|---|
| peak gross | 2.785866740650797x | 2.785866740650797x | 0 |
| mean gross | 1.1822885544580082x | 1.1202922016126184x | −0.061996x (−5.24%) |
| max single share | 1.6453419557868878x | 1.6453419557868878x | 0 |
| samples | 173 | 964 | — |

Basis B: peak 2.779227887117067x (Δ 0), mean
1.1179686987168116x (Δ −0.061642x), max single unchanged.
Flat-equity cross-check: peak 2.833707416691979x (Δ 0; vs the
recorded 2.83x proxy), mean 1.1541143407516874x (superseded
1.200280616412446x). Max concurrency 5 throughout.

Decomposition of the basis-A mean delta (−0.061996x), via the
bridge (entry-only grid under the successor's committed-order
equity: mean 1.1838047460685641x): the coincident-timestamp
tie-break contributes **+0.001516x**; the grid completion
contributes **−0.063512x**. On this record the peak and the max
single share sit at an entry timestamp (2025-09-08 09:30 ET, 5
open) and no exit or bar-mark sample exceeds them, so the
entry-only peak happened to land on the same value — it was
nevertheless unqualified, because the estimator never measured
the grid it claimed; the mean was materially overstated. The
corrected figures are now measured on the full grid the contract
specifies.

## Retained caveat (verbatim in substance from -30)

Full entry notional is held until exit_time: after a TP1 partial
the runner is half size, TP1 timing is not in the ledger, so the
intra-hold exposure path is an **upper bound**; the exact path is
UNVERIFIABLE from the committed record. The grid repair makes the
sampled statistics the statistics of the full committed grid; it
does not cure the intra-hold bound. Heat is never reported as
exposure.

## Verification

`code/verify_package.py` PASS: manifest integrity; -30 code +
artifact byte-untouched (pins f219f342… / d2da4b45…); the
regenerated artifact equals a fresh recomputation exactly; the
superseded block equals the committed -30 artifact (reproduced
by executing the pinned -30 module, hash asserted before import);
battery 16/16 exit 0.

## Bounds

P6 measurement only. No strategy or simulator edits (pinned
sources read, never modified); no performance run; holdout
SEALED; no vendor calls; pilot / S1 / G4 untouched; production
PAUSED. P8's PASS does not authorize prospective launch. The
original C1 FAIL stands; DEV remains exploratory, not validated
edge evidence.
