# DRAFT — P2-SPOT v2 protocol amendment (calendar lineage reference only)

Status: **DRAFT — NOT EXECUTED, NOT ADOPTED.** Drafted under
QF-TD-NEW-LINEAGE-QUAL-20261015-01 r1 step 5, contingent on that task's
verdict `NEW_LINEAGE_CALENDAR_PASS`. Adoption requires a separate
adjudicated act. This draft changes no live protocol text.

## Amendment (minimum)

1. **Calendar-qualification reference.** P2-SPOT v2 replaces the P2 v1
   calendar basis with the qualified NEW LINEAGE `NL-20261015`:
   `pandas_market_calendars==4.5.1` under the exact `f64d12f`
   integration lock (sha256 `08b38cfa…`), CPython 3.12, qualified by
   Gate N fixtures FX-01..FX-05 with exact UTC open/close instants and
   complete 1H bar-start label sets, run twice byte-identically, plus
   reproduction of the original `f64d12f` 16/16 real-calendar
   integration suite against immutable source bytes
   (QF-TD-NEW-LINEAGE-QUAL-20261015-01).
2. **Non-equivalence.** `NL-20261015` claims equivalence to the -12
   (2026-10-13) environment only in the Gate N / H2 sense: the exact
   -12 lock was installed and the -12 suite reproduced identically.
   It claims **no** equivalence to -11.
3. **-11 stays UNKNOWN.** No P2-SPOT v2 text may assert or imply -11
   calendar parity; -11 is closed as UNKNOWN (Gate H3).
4. **Unchanged gates.** P2 v1 remains **UNMET** until P2-SPOT v2 is
   separately adopted and its own (non-calendar) requirements pass.
   REQ-SPT-08 remains **NOT ATTEMPTED** until separately authorized
   under the adopted protocol. The -17 classifier candidate and its
   supplement pin are untouched by this amendment; any re-pin of the
   supplement to the `NL-20261015` lineage is a separate act.
5. **Environment discipline.** Any run claiming `NL-20261015` must
   install the exact lock into a disposable isolated environment,
   record the N0 freeze (interpreter, full pip freeze, wheel hashes,
   tzdata source actually in force, mechanism sha256), and fail
   closed on any substitution or drift.
