# TD PROBE REV7 (R7) — RESULT

Task: QF-TD-PROBE-REV7-20261101-R7
Authorization: Mike's fresh GO in direct chat 2026-11-01 ("And can
we do the r7"). Scope: R7 leg ONLY of the S2 split probe — the
/api_usage preflight plus the two frozen REV7 re-pulls from the
accepted -74 candidate manifest (sha256 1bb86e17…). Expected 3
credits, HARD ceiling 6 for the whole run. R30 NOT authorized
(and not eligible until 2026-11-20T21:33:00Z). No other symbols,
no Tier-3/holdout access, no production changes.

## TERMINAL

TD_PROBE_R7_EXECUTED__C5_PASS_BOTH_LEGS__BYTES_IDENTICAL

Eleven days after Day-1 (-75, 2026-10-21 21:33Z), Twelve Data
returned byte-identical responses for both re-pulled windows.
C5 (revision byte-compare, -74 analyzer, unmodified): PASS on
NVDA and PASS on TSLA. Sampled-window verdicts only; no global
KEEP/REPLACE S2 verdict (never this task's to issue); no
performance computed. C5 for the full probe still awaits R30,
which needs its own GO on/after 2026-11-20T21:33:00Z.

## GATES, IN ORDER

- G-PIN PASS — manifest sha256 1bb86e17… verified byte-exact;
  the runner verified the frozen pilot pins itself
  (pilot_acquire.py acf39bbd…, rate_limiter.py 06ad383d…).
- G-CLK PASS — host UTC vs google.com HTTPS Date header:
  offset ≈ −1.7s, inside the 5s threshold used at Day-1.
- TEMPORAL GATE PASS — proven by the runner against the
  byte-pinned Day-1 base receipts before any transport
  construction: REQ-ADJ-01 base receipt_ts_ms 1792618380707 →
  eligible 2026-10-28T21:33:00.707Z; REQ-ADJ-02 base
  receipt_ts_ms 1792618381355 → eligible 2026-10-28T21:33:01Z;
  run now_utc_ms 1793584669810 (2026-11-02T01:57:49Z). Base
  receipt+snapshot integrity (sha256/bytes/params) re-verified
  by the gate.
- G-CRED PASS — credential attached at fetch time only via
  the sanctioned helper dynamic_credentials.py
  (url_with_surrogate_query_param, custom.twelvedata,
  api.twelvedata.com only). The raw key never entered the
  process and was never printed, logged, or written.
- G-USE PASS — /api_usage preflight: 1 attempt, HTTP 200,
  verdict PASS, commit_state "1". Live body: current_usage=1,
  plan_limit=8 (minute bucket), daily_usage=1,
  plan_daily_limit=800, plan_category basic (131 bytes). The
  frozen daily gate evaluated 1 + required_headroom 4 ≤ 800 —
  PASS. Header reconciliation: api-credits-used 1 ==
  current_usage 1; 1 + api-credits-left 7 == plan_limit 8 —
  PASS. The data-transport backstop verified the committed
  D7 PASS before its first fetch.

## CREDITS — EXACT, RECONCILED

- This execution: **3 calls** = 1 /api_usage (1 attempt,
  HTTP 200) + 2 /time_series (1 attempt each, both HTTP 200).
  Retries: 0. Expected 3 — exact. Hard ceiling 6 — the
  binding's process-wide counter capped total fetches at 6
  pre-transmission and was never approached.
- Vendor counter cross-check: api-credits-used headers
  incremented 1 (usage) → 2 (NVDA) → 3 (TSLA), confirming one
  credit per call in the vendor's own accounting.
- daily_usage read 1 at the preflight: the vendor's daily
  counter for the new UTC day (2026-11-02) counted this run's
  usage call first; reset semantics remain a standing
  unknown, recorded as consistency, not proof.
- Program live Twelve Data usage to date: 8 (through -75)
  + 3 = **11 credits**.

## PER-LEG RECEIPTS (all HTTP 200, 1 attempt, ASC, 1h,
America/New_York, outputsize 5000, zero pagination)

- REQ-ADJ-01R7 NVDA splits 2023-12-13→2024-06-21: 116,908 B,
  sha256 69b87f0359f63f13fbde8b9b72e1ea03026e4ff55b9bfdf061c1
  cfec3e36fe95, 917 rows.
- REQ-ADJ-02R7 TSLA splits 2022-03-07→2022-09-09: 117,690 B,
  sha256 c5f701886e7c63db8ecdf5ec9d9e42a629cf79395bcace867719
  9bb67a5c2e2d, 911 rows.

## BYTE COMPARISON vs DAY-1 (-75 BASE RECEIPTS)

- NVDA: base REQ-ADJ-01 sha256 69b87f03… / 116,908 B —
  R7 sha256 identical, bytes identical (cmp clean). C5 PASS.
- TSLA: base REQ-ADJ-02 sha256 c5f70188… / 117,690 B —
  R7 sha256 identical, bytes identical (cmp clean). C5 PASS.

Both comparisons are full byte diffs against the retained
Day-1 raw payloads in the local store, not hash-only checks
(the hashes also match, independently).

## DISCLOSURES

1. Transport binding changes vs -75 (forced by this task's
   terms, binding source included in this package): ceiling
   12 → 6; single-attempt enforcement — any retryable outcome
   (429/502/503/504 or transport error) is sidecar-logged to
   r7_transport_failures.jsonl and raised as a hard stop
   (RuntimeError), so the frozen candidate's retry path can
   never transmit twice; backstop reads the D7 (not D1) usage
   receipt. No retryable outcome occurred; the sidecar file
   was never created.
2. The AAPL dividend control (REQ-ADJ-03) has NO revision leg
   in the frozen manifest and was not re-pulled — by design,
   not omission.
3. The TSLA C2 verdict from Day-1 (DATA_UNQUALIFIED — 166
   zero-volume pre-split bars) is untouched by this result:
   R7 proves the bytes are stable, not that they are complete.
   The revision test answers "does TD revise history"; the
   completeness question remains ChatGPT's adjudication.

## STORAGE

- Local store ~/workspace/qf_td_probe_d1_20261021/store holds
  the R7 raw payloads alongside Day-1 (REQ-ADJ-01R7.json,
  REQ-ADJ-02R7.json, per-leg receipts + attempts logs, the D7
  usage body bytes + committed receipt, the limiter ledger) —
  the Day-1 package's own retention pattern, same store.
- Archive repo mickaellall116-cmyk/qf-data-archive: R7 raw
  payloads + receipts pushed under
  captures/td_probe_rev7_20261101/ (see the archive line in
  the bridge post for the commit).
- This package (scanner repo): the transport binding, the
  analysis driver, analysis_results.json, gate_evidence.json,
  the sanitized D7 usage receipt, the two sanitized leg
  receipts, and the runner stdout/stderr. Sanitized only; no
  raw bars, no key material.
