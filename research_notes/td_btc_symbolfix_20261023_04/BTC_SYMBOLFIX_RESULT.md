# QF-TD-BTC-SYMBOL-FIX-20261023-04 — RESULT

**Verdict (BTC stamp phase alone): HOLD — NOT CONFIRMED.** The symbol-form
fix is proven for transport, but the first chunk fails qualification on
two independent grounds (absent volume field; stamp phase not the pinned
S-C phase). Run stopped at the first defect; chunks 2–6 never attempted.

**Authorization:** Mike's standing rule (chat 2026-10-23 12:21 ET,
"Go dont wait for me anymore") applied to this bounded corrective task
(Issue #1 comment 6369892556). This was a NEW pinned request form, not an
in-place retry of -03.

## The fix (only change vs Card A)

- Explicit one-to-one transport alias, pinned in the amended manifest:
  internal universe token `BTC-USD` → Twelve Data request symbol
  `BTC/USD`. Frozen UX51 membership unchanged (sorted digest
  `b5d8877ee7d6ddd105904d7f4ca35901ebb611dac7afeab2f7676529c112e6a2`,
  ordered digest `8f0778df2502e31d4dc0bfeaec42cb51c209e38bf8d91195c61270c3a7ba16c0`).
  No other symbol's request form changes; unmapped symbols raise.
- Manifest lineage (correction by lineage; prior packages/archives
  byte-untouched): parent readiness root
  `79ccdd128e0b36537f56f8ae36a731b719e989b9756f65856b7dc47344327122`
  (edc44d9) → NEW amended root
  `23042e30ddfd3a5a233e832a011de3cdfc2b9e28f78542e6b547258fe9bccb52`.
  Every manifest leg and every receipt carries BOTH identifiers.
- `meta.symbol` is checked against the provider form `BTC/USD`, not the
  internal token (fixture-proven both directions).

## Phase 0 — offline (before any vendor call)

Offline suite **30/30 PASS** under `unshare -n` (pinned venv), network
disabled: alias accepted/rejected forms, exact six Card A windows +
expected rows, outputsize 5000, meta provider-form check, spring-forward
(23h day, no 02:30 stamp) and fall-back (25h day, repeated 01:30 resolved
on UTC instants) grid fixtures, gap/off-grid/duplicate detection,
5000-row truncation, volume missing/null → SCHEMA_COVERAGE_HOLD,
receipt-chain recompute + tamper, scope guard. One test was corrected
during Phase 0 for precision (a substring check matched the inherited
failure-class label "SMCI-class"; the check now tests symbol literals —
the driver requests only BTC/USD, independently proven by the
build_params tests). Log: `offline_test_log.txt`.

## Phase 1 — execution

Preflight `/api_usage` (1 read, never retried): `daily_usage=14`,
`plan_daily_limit=800` on the DAILY fields (per-minute `plan_limit=8`
not used) — PASS.

| Chunk | Request symbol | HTTP | Rows | Verdict |
|---|---|---|---|---|
| BTC-USD/HO-C1 | BTC/USD | 200 | 4992 (= expected) | **ABORT — SCHEMA_COVERAGE_HOLD** (quarantined, no receipt) |
| BTC-USD/HO-C2 | — | — | — | not attempted |
| BTC-USD/DEV-C1..C4 | — | — | — | not attempted |

**Defect 1 (abort reason) — volume absent:** the BTC/USD `/time_series`
response contains NO volume field on any of the 4992 rows (keys are only
datetime/open/high/low/close; meta: exchange Binance, type Digital
Currency). Under the frozen checker requirements, missing/null volume is
a SCHEMA/COVERAGE HOLD — it is not zero and not evidence of no-trade;
OHLCV was not synthesized; no schema waiver is authorized. Body preserved
byte-exact in the archive `quarantine/` (sha256
`9c5a0487569aa159ed51960bb22f94261c3ecb2be30c39ca37056f9855e20598`,
522,073 bytes). No receipt was fabricated for the failed leg.

**Defect 2 (independent, same bytes) — stamp phase:** returned stamps
are genuine ET wall stamps (fall-back day 2023-11-05 has 25 wall bars
with 01:00 duplicated; spring day 2024-03-10 has 23, no 02:00) but the
phase is **ET calendar-day 00:00-anchored** (stamp minutes {00}; first
2023-10-19 00:00:00, last 2024-05-13 23:00:00) — NOT the pinned S-C
continuous session [09:30 ET, +09:30 ET) with :30 bar-opens. So even
apart from volume, the bytes do not sit on the frozen S-C1..S-C6 phase.
Timestamps were not shifted and no calendar relabeling was applied.

**Credits:** 3 incremental request-counted (preflight + 1 attempt +
closing `/api_usage` read) of the 15 hard max. Provider daily counter
14 → 16 across the run window (provider counts calls differently than
the conservative request-counted ledger — both preserved, not asserted
identical). Program TD total 21 → 24. $0 free tier, no paid upgrade.

## Storage

- Private archive `qf-data-archive` commit `ba4105a`, NEW namespace
  `captures/td_pilot_btc_fix_20261023/` (amended manifest, preflight,
  evidence, quarantined HO-C1 body, HOLD.md, SHA256SUMS) — 7/7 verified
  by fresh re-fetch, byte-identical to the local store
  (~/workspace/qf_td_btc_fix_20261023/store). The -03 refusal namespace
  `captures/td_pilot_btc_20261023/` is untouched.
- This package: amended manifest, driver (`capture_btc_fix.py`),
  manifest builder, offline tests + log, run evidence.

## Bounds kept

BTC only — no equity/SMCI/other-crypto legs; no full capture; no
performance or holdout analysis; no production or frozen-strategy change
— PAUSED production pins re-verified identical before/after (harness
`ce7c902c…`, scanner_rules `62aa743a…`, masterscanner_api `c3e95b25…`,
v54_engine `bde32883…`, v54_rules `1b55dedc…`; PAUSE_NEW_ENTRIES
present, no RESUME file); no shadow launch. Single-dispatch check was
clean before staging.

**Open (not executed):** the BTC route now has two provider-side facts
to adjudicate — (1) crypto `/time_series` returns no volume field under
this request form, and (2) its stamp phase is 00:00-anchored rather than
the pinned 09:30 S-C phase. Either a checker/schema disposition or an
S-C redefinition would be a separate governed decision; neither was
taken here. SMCI disposition and all other gates unchanged (HOLD).
