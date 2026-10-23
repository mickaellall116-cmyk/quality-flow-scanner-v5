# TD PILOT — ACTUAL-BYTE ADJUDICATION — QF-TD-PILOT-ADJUDICATION-20261023-02

**States:** pilot SENT (Issue #1 comment 6366485895) → ACK (Slack
1792765630.868999) → pilot RESULT (scanner commit `5d129fb`, archive
`45496f8`) → ChatGPT independent verdict + this task (Issue #1
comment 6367690741) → this package. Independent PASS/HOLD on THIS
package is ChatGPT's/Claude's step, not claimed here.

**Authorization:** ChatGPT's bounded offline follow-up in comment
6367690741, under Mike's standing research-loop auto scope. OFFLINE
ONLY — already-captured bytes; no API/vendor call, no credits, no
retry, no new acquisition, no holdout/performance use, no
production change, no launch. Pilot HOLD stands; nothing here
converts the incomplete pilot into a route PASS.

## Instruments (pinned, fail-closed)

- Checker: `checker-v3-candidate-2` (task -94 lineage), copied
  byte-identical from `research_notes/repair_94_20261022/` on
  origin/main — `checker/tsla_completeness_check.py` sha256
  `4fdc31cbfc4b1a96baaabe775d883135cf64a4f7dc2606c7b679756da1e7d936`,
  `checker/crypto_session_model.py` sha256
  `248442f17add6e58fa31b1e3aa847f0519dd3b21efbd564c38460d8e6da1e5e9`.
  CANDIDATE, not adopted (adoption = G4, Mike's GO).
- Calendar: the adopted pinned session table
  `research_notes/shadow_closeout_20261022/session_table.json`,
  sha256 `00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f`,
  version `XNYS-751-UNION-20261021` (751 sessions: HO window 227 =
  2023-10-19→2024-09-13; DEV window 524 = 2024-09-16→2026-10-16).
  The driver refuses to run on a pin mismatch.
- Bytes: the pilot's local store `~/workspace/qf_td_pilot_20261023/store`,
  verified `sha256sum -c SHA256SUMS` 22/22 OK before the run and
  byte-identical to the private archive (pilot RESULT §Receipt
  integrity). Raw vendor bars are NOT in this public package —
  counts, stamps, and verdicts only.

## The admission rule (one generic rule)

A vendor row is ADMITTED iff its bar-open instant belongs to the
expected bar-start set of its session date under the pinned table
(the checker's own `_expected_starts`: hourly starts from 09:30 up
to the pinned close — 16:00 normal, 13:00 early close). The rule
consults the calendar ONLY: no symbol list, no date list, no OHLCV
shape test. Post-close rows fail membership and are excluded.

## Result 1 — the early-close phantom exclusion FIRES on actual bytes

On raw bytes, the checker's COUNT lane flags exactly the phantom
rows as extra bars; the admission rule excludes exactly the same
rows; admitted counts then equal the receipt expectations exactly.

| Leg | Raw rows | Excluded by the rule | Admitted | Receipt expected | Admitted COUNT | Admitted ANOMALY |
|---|---|---|---|---|---|---|
| NVDA/HO | 1,583 | 0 | 1,583 | 1,583 | PASS | PASS (0) |
| NVDA/DEV | 3,654 | 1 | 3,653 | 3,653 | PASS | PASS (0) |
| TSLA/HO | 1,583 | 0 | 1,583 | 1,583 | PASS | PASS (0) |
| TSLA/DEV | 3,655 | 2 | 3,653 | 3,653 | PASS | PASS (0) |
| AAPL/HO | 1,583 | 0 | 1,583 | 1,583 | PASS | PASS (0) |
| AAPL/DEV | 3,655 | 2 | 3,653 | 3,653 | PASS | PASS (0) |
| SPY/HO | 1,583 | 0 | 1,583 | 1,583 | PASS | PASS (0) |
| SPY/DEV | 3,655 | 2 | 3,653 | 3,653 | PASS | PASS (0) |
| SMCI/HO (quarantine) | 1,584 | 1 | 1,583 | — (unreceipted) | PASS | **FAIL (19)** |

Every excluded row, enumerated (all are 15:30 bar-opens on 13:00
early-close dates, all flat O=H=L=C; volumes differ — the rule is
shape-blind and catches the zero-volume and nonzero-volume variants
alike):

- NVDA/DEV: 2024-11-29 15:30 ET (vol 511,735)
- TSLA/DEV: 2024-11-29 15:30 ET (385,982); 2024-12-24 15:30 ET (840,124)
- AAPL/DEV: 2024-11-29 15:30 ET (100,855); 2024-12-24 15:30 ET (0 — also
  classed NO_TRADE_FLAT by the raw ANOMALY lane, a market-fact class,
  not a defect)
- SPY/DEV: 2024-11-29 15:30 ET (0 — NO_TRADE_FLAT on raw); 2024-12-24
  15:30 ET (131,302)
- SMCI/HO: 2024-07-03 15:30 ET (145,460)

Admitted grid endpoints are identical on every leg of a window —
HO: 2023-10-19 09:30 ET → 2024-09-13 15:30 ET; DEV: 2024-09-16
09:30 ET → 2026-10-16 15:30 ET. No missing bars, no missing
sessions, STRUCTURAL PASS on all 9 series (no duplicate instants,
no order violations, session-zone tz throughout). **All eight
receipted legs are completeness-QUALIFIED at candidate-2 on the
admitted bytes.** Nothing was relabeled or special-cased: remove
the rule and the DEV legs fail COUNT; apply it and they pass —
that is the proof the exclusion does the work.

Price-convention lanes on admitted bytes: STEP (declared boundary
NVDA 2024-06-10, factor 10) classifies CONTINUOUS_ADJUSTED, PASS,
observed step 0.993671, volume note UNSCALED, no basis mismatch —
the `adjust=splits` basis is verified in force on actual bytes.
STEP-ALL finds **zero** factor-shaped undeclared-boundary steps on
all 9 series.

**VBASIS disclosure (not waived, not tuned):** the checker's
composite overall prints CONVENTION_BREAK_SUSPECT on every leg,
driven SOLELY by the VBASIS lane (flagged boundaries: NVDA 32/90,
TSLA 12/91, AAPL 32/108, SPY 44/94, SMCI 66; HO/DEV). VBASIS flags
any boundary where the 5-session median volume ratio exits
[1/1.5, 1.5]. On actual bytes this lane is non-discriminative:
SPY — no split or basis event in either window — flags 44
boundaries in HO alone; NVDA/HO's flagged ratios form a continuum
(0.528–1.950, median 1.565) hugging the 1.5 band edge, the shape of
gradual volume-regime drift, not a discrete basis rescaling (which
would print at the split factor, ~10 or ~0.1, at one boundary).
Disposition: completeness qualification (this task's gate) does not
rest on VBASIS; the price-side convention evidence (STEP PASS,
STEP-ALL 0) shows no basis break; whether VBASIS at this
calibration belongs in the adopted instrument is a G4 adoption
question for adjudication. The lane's output is reported exactly
as printed in `checker_report.json`; no threshold was adjusted.

## Result 2 — SMCI/HO classification: NOT_EVALUABLE_PROVIDER_VOLUME

The quarantined SMCI/HO body (archive sha256
`737cb24ad6dcb6185529dd629177cd34f6f1f5988b0dda86fb45131c898f43d3`)
was run through the identical pipeline. After the generic admission
rule removes its one phantom row (2024-07-03 15:30), COUNT is exact
(1,583 admitted, 0 missing, 0 missing sessions) — and ANOMALY still
fails on **19 price-moving zero-volume bars**, independently
reproduced here at the same stamps ChatGPT enumerated: 2024-04-08
×4 (12:30, 13:30, 14:30, 15:30), 2024-04-09 ×1 (10:30), 2024-04-10
×6 (10:30–15:30), 2024-04-12 ×4 (09:30, 10:30, 11:30, 13:30),
2024-04-15 ×2 (09:30, 15:30), 2024-04-17 ×2 (11:30, 15:30).

**Classification: `NOT_EVALUABLE_PROVIDER_VOLUME`** — fail-closed,
per the TSLA C2 precedent (-76): zero-volume bars WITH nonzero OHLC
range are missing/zeroed provider volume, not no-trade bars. No imputation, no retry, no alternate
window, no silent symbol removal, no performance use. The defect
survives the only legitimate generic repair (session admission),
which is exactly what makes the leg not evaluable rather than
merely unfiltered. Coverage consequences: COVERAGE_IMPACT.md.

## Result 3 — regression fixtures (synthetic shapes, no raw values)

`fixtures/test_pilot_artifact_regressions.py` — all prices/volumes
invented; only shapes carry over (an early-close date's 13:00
pinned close; the April pattern's per-date counts 4/1/6/4/2/2):

- F-PH1 / F-PH2: a post-close 15:30 stub in both observed shapes
  (flat zero-volume; nonflat nonzero-volume) is COUNT-flagged on
  raw bytes and excluded by the same admission rule the driver
  uses (imported, not copied); admitted bytes pass.
- F-ZV: 19 synthetic price-moving zero-volume bars are ANOMALY-
  flagged on raw AND admitted bytes (admission cannot cure the
  class), a flat zero-volume control stays NO_TRADE_FLAT, and the
  class maps to NOT_EVALUABLE_PROVIDER_VOLUME.

4/4 fixture groups PASS; the -94 checker suite re-run against the
copied module passes 18/18. Full commands/output: TEST_EVIDENCE.md.

## Result 4 — continuation card (NOT EXECUTED)

`CONTINUATION_CARD.md`: two SEPARATE cards — (a) BTC stamp-phase
pilot, (b) SMCI disposition — each requiring its own future GO,
neither bundled into full capture. Nothing in this package
executes or authorizes either.

## Bounds kept

No vendor/API call of any kind (all runs under `unshare -n`);
program Twelve Data total unchanged at 18 credits; no capture; no
holdout strategy use (pilot W-HO bytes used for qualification
classification only, as the task specifies); no performance; no
production/frozen-strategy change — PAUSED production pins
re-verified identical before/after (v54_forward_harness.py
`ce7c902c…`, scanner_rules.py `62aa743a…`, masterscanner_api.py
`c3e95b25…`, v54_engine.py `bde32883…`, v54_rules.py `1b55dedc…`;
PAUSE_NEW_ENTRIES present); no shadow launch. The -94 package and
the pilot package are untouched; this package supersedes nothing.

— Muse
