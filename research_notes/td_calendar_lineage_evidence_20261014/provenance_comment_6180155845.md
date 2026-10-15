# GitHub Issue #1 comment 6180155845 (author mickaellall116-cmyk, created 2026-10-14T22:44:05Z, fetched 2026-10-14 via unauthenticated public API)

## Independent ChatGPT research — TD calendar provenance recovery plan (no Muse runtime, no vendor calls)

While Muse handles QF-ISSUE9-ROUTE-READINESS-20261014-02 r1, I independently reviewed the immutable TD closed-session design memo at `3b47426` (`research_notes/TD_CLOSED_SESSION_SEMANTICS_20261014.md`) and the later classifier HOLD adjudication at #6178015013. **New distinction that must not be lost: reproducing a calendar in a newly pinned environment is not proof of the calendar version actually used in -11/-12.** Installing whichever current `pandas_market_calendars` version works would risk laundering an unknown historical dependency into a purported provenance match.

### Independent decision / next offline lane — QF-TD-CALENDAR-LINEAGE-20261014-01

**Scope:** research/design-only, no vendor requests, no package install, no mutable acquisition state, no SPOT8 replay, no protocol amendment, no corrected backtest. This is an independent specification, **not a duplicate Muse assignment while swarm readiness is active**.

1. **Historical lineage evidence tier:** search existing immutable -11/-12 invocation manifests, lockfiles, wheel hashes, pip freeze records, CI/build logs and recorded environment hashes for the *actual* `pandas_market_calendars` version **and its calendar-data dependencies**. Distinguish exact contemporaneous pin (PROVEN), bounded plausible range (INFERRED), and no pin (UNKNOWN). An ephemeral -14 venv does not establish -11/-12 identity.
2. **Reproducible *new* environment tier:** if historical version remains UNKNOWN, select a clearly new version-locked qualification environment and name it as a **new lineage**, not a reconstruction of -11/-12. Lock interpreter, dependency versions, hashes and XNYS calendar provenance. Keep acquisition response bytes untouched.
3. **Calendar behavior fixture tier:** under a future separately approved isolated offline test, verify all dates in the frozen SPT05/06 (2025-11-28 early close) and SPT07/08 (2026-07-03 closed) windows, both DST transitions, and at least one mixed open/closed window. Compare UTC open/close instants and expected bar labels, not just a Boolean closed/open. Fail closed on timezone/library drift or unknown venue.
4. **Decision boundary:** exact historical dependency pin + deterministic replay can support a historical-lineage parity claim; otherwise only **new-version qualification** is eligible, with explicit non-equivalence and a separately versioned P2-SPOT v2 protocol. In neither case do six receipts plus SPT07 HTTP 400 qualify the feed; SPT08 remains unattempted, and closed-day evidence is never a wire-verified identity receipt.

**Practical acceptance packet:** a table of each claimed environment, evidence source/hash, provenance grade, XNYS version/dependency lock, dates tested and exact session/bar expectations, regression fixture results, and an explicit `HISTORICAL_LINEAGE_PROVEN | NEW_LINEAGE_ONLY | BLOCKED` verdict. Preserve P2 v1 UNMET and zero additional credits until a separate live authorization. Do not ask Muse to abandon its currently assigned swarm task; queue this only after that work or pursue independent read-only analysis in the next coordination cycle.

This is a research contribution/decision framework only; no claim that the missing dependency is resolved or that a corrected baseline is available.
