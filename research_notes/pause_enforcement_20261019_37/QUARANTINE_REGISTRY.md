# QUARANTINE REGISTRY — pause-era cohort (descriptive only)

Created under QF-V54-PAUSE-ENFORCEMENT-20261019-37 r2 (closure-only), per the -36
adjudication (Issue #1 comment 6272331269) and the -37 r2 GO (comment 6275360908).
This registry is an annotation record only. It does not alter `state.json`, the
original JSONL, the closed ledger, position management, or strategy logic, and it
does not decide any item's accounting — the count/void ruling remains Mike's.

## PAUSE_CONTAMINATED — quarantined from qualified performance

| Item | Form | Record |
|---|---|---|
| MRNA | Open position (B) | Opened Mon 2026-10-19 via the harness's ordinary pending-fill path while entries stood paused (opened event 14:54:35.343Z; entry 217.27, stop 205.13, TP1 246.02). Labeled **PAUSE_CONTAMINATED**. |
| TEAM | Open position (B) | Opened Mon 2026-10-19 via the same path (opened event 14:54:35.369Z; entry 208.11, stop 199.60, TP1 221.90). Labeled **PAUSE_CONTAMINATED**. |
| MSFT | Pending entry (B) — never filled | Signal + `pending_entry` created Mon 2026-10-19 14:54:35Z (price 533.97, stop 526.76, TP1 552.33). Its fill was blocked by the deployed pause gate at the 18:56:01Z cycle (`pending_fill_blocked_pause`, intended fill bar 2026-10-19T10:30:00-04:00, intended open 534.09). Remains pending and unfilled. Labeled **PAUSE_CONTAMINATED**. |

## Pause-era cohort — status disclosed, accounting NOT decided here

| Item | Form | Record |
|---|---|---|
| GOOGL | Closed −1.0R | Filled and closed during the enforcement-absence window, before -37. |
| RBRK | Closed −1.0R | Same window. |
| MELI | Closed −1.0R | Same window. |
| SHOP | Open position (B) | Opened in the same window (entry 171.45); still open, exit management continuing under the frozen Mode B rules (the pause gate does not gate exits). |

The six names above plus MSFT are the full pause-era cohort identified by the -36
static audit (commit `9ff4295591eeabd93129f36c63803b0630a95f01`). Whether the cohort's
results count toward the forward-test verdict ledger is Mike's pending ruling; this
registry records the contamination labels and the facts only.
