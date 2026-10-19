# Gap matrix — QF-NYSE-HISTORICAL-CORE-HOURS-RULE-PROOF-20261019-33 r1

Frozen interval: **[2024-09-16, 2026-10-16]** (unchanged). This matrix closes the
one field left open by -32 (commit `d307439`, preserved unedited): regular core
hours for the block **2024-09-16..2025-12-31**. All other fields stand exactly as
pinned in -31 (commit `5d2060b`) and -32.

## The previously open field — now PROVEN

| Period | Regular core hours | Status |
|---|---|---|
| 2024 (Sep 16–Dec 31) | **09:30–16:00 ET** | **PROVEN** — NYSE Rule 1.1(d) definition quoted as current rule text in the SEC notice of NYSE's filing SR-NYSE-2025-21 (Release No. 34-103356, Jun 30, 2025), footnote 42: "The term 'Core Trading Hours' is defined in Rule 1.1(d) to mean the hours of 9:30 a.m. Eastern Time through 4:00 p.m. Eastern Time…"; operative use at block start by NYSE Regulatory Memo RM-24-12 (Sep 13, 2024): deadlines "applicable to days for which the scheduled end of Core Trading Hours is 4 p.m." (Rule 7.35(a)(8); Rule 7.34(a)(2)(B)), rules stated to be "applicable every day" |
| 2025 (full year) | **09:30–16:00 ET** | **PROVEN** — same Rule 1.1(d) definition, quoted in a filing NYSE itself made Jun 17, 2025 (immediately effective), i.e. in force mid-block; no NYSE cash-equity filing in the pass changed the definition during the block |

Temporal applicability follows spec item 3's second route: two dated in-period
official documents (Sep 2024 + Jun 2025) whose rule citations (Rules 1.1(d),
7.34(a)(2)(B), 7.35(a)(8)) and unchanged terms jointly cover the block. A current
undated webpage was **not** used as historical proof.

## Full field status for the frozen interval (after -33)

| Field | 2024 (from Sep 16) | 2025 | 2026 (to Oct 16) |
|---|---|---|---|
| Regular core hours 09:30–16:00 ET | PROVEN (-33) | PROVEN (-33) | PRIMARY_CURRENT (-31) |
| Full-day closures (dated) | PRIMARY_CURRENT (-32) | PRIMARY_CURRENT (-32, incl. Jan 9 Carter) | PRIMARY_CURRENT (-31) |
| Scheduled 13:00 ET early closes (dated) | PRIMARY_CURRENT (-32) | PRIMARY_CURRENT (-32) | PRIMARY_CURRENT (-31) |
| Session counts | PRIMARY_ARCHIVED (-31; reconciled -32) | PRIMARY_ARCHIVED (-31; reconciled -32) | PRIMARY_CURRENT (-31) |

Remaining open items: **none** in the -31/-32/-33 field set. The one standing
non-field observation from -31/-32 is unchanged: no captured source states a
general ad-hoc-closure *mechanism* rule; the interval's one ad-hoc event
(Jan 9, 2025) carries its own dated official notice (-32).

## Verdict

**HISTORICAL_CORE_HOURS_PROVEN** — both boundaries (09:30 and 16:00 ET) and
temporal applicability across 2024-09-16..2025-12-31 are exchange/regulator-
published and pinned in `PROOF_RECEIPT.json`. Handed off for independent review
only; no schedule generated.
