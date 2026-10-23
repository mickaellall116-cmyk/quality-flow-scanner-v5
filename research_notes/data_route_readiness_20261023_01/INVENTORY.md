# EXISTING-BYTE INVENTORY — QF-DATA-ROUTE-READINESS-20261023-01

Enumerated from the live filesystem this run (2026-10-23); full
machine-readable detail in `inventory.json` (per-file rows, spans,
SHA-256). Sealed holdout *content* was not read — inventory records
metadata (path, span, row count) only.

## What exists

**1. Twelve Data Day-1 probe bodies (5 legs, 3 symbols).**
`~/workspace/qf_td_probe_d1_20261021/store/REQ-ADJ-*.json` — NVDA
917 bars 2023-12-13→2024-06-21 (adjusted + unadjusted pair), TSLA
911 bars 2022-03-07→2022-09-09 (pair), AAPL 903 bars
2026-02-19→2026-08-24. Provenance: IMMUTABLE — byte-identical copies
in qf-data-archive `captures/td_probe_day1_20261021/` (commit
`2f223cf`, re-fetch verified 20/20), each with its probe receipt.
**Reuse as cohort bytes: NO.** Probe windows only; NVDA's window
overlaps sealed-holdout dates (qualification-evidence use only, by
the standing disclosure); TSLA's legs carry the C2 NOT_EVALUABLE
label (volume completeness failure); AAPL's window sits outside
both capture windows.

**2. Canonical Stage C raw 1h set (Yahoo, fetched 2026-09-29).**
`~/workspace/canonical-stage-a/canonical_stage_c/raw_1h/` — 137 CSVs
(`t,o,h,l,c,v`, ET-offset stamps), e.g. AAPL 5,073 rows
2023-10-31→2026-09-29, fetched via yfinance `period="730d"`,
`auto_adjust=False`, per-symbol fetch manifest + STAGE_C_REPORT.
**UX51 coverage: equities 38/44** (missing MSTR, APP, NET, ASTS,
LUNR, NU), **crypto 0/7**. Provenance: local mutable worktree only —
no per-response receipts, no hash chain, never archived; Yahoo
serves no as-of/versioning evidence and silently restates bars.
Window: oldest bar 2023-10-31 is 8 sessions after the 2023-10-19
window start. **Reuse as cohort bytes: NO** — fails coverage,
provenance, and window independently.

**3. Absent (verified this run).** D1 `backtest_cache/` does not
exist (destroyed with the prior VM; 52 SHA-256 pins survive, bytes
do not). `pine_1h/` holds a fetch script only. `~/workspace/
data_archive/yahoo_1h_clean/` is an empty directory — the parked
Yahoo capture lane never executed. The forward harness persists no
raw 1h frames (in-memory prefetch only); `v54_forward_1h/` holds
status/log files only.

## Verdict

**RAW_1H_NOT_AVAILABLE** for the frozen cohort — confirming the
-80/repair-lane finding against the current filesystem, with one
correction of scope: raw 1h bytes *do* exist locally (Stage C), but
none are reuse-eligible. No existing artifact set can serve as
corrected-grid cohort bytes; a capture remains necessary.
