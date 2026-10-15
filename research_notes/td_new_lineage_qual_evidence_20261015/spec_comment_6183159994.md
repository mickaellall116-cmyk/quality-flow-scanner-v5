REVIEW / DECISION — TD calendar lineage `f95dc0e` and Yahoo observation pin `d516d2f`

I reviewed the immutable commits and compared the TD lineage package against the original `f64d12f` integration record.

**1) TD calendar lineage: scoped PASS / NEW_LINEAGE_ONLY accepted.**
- The `f95dc0e` manifest is internally consistent with the preserved `f64d12f` lock and author results: `pandas_market_calendars==4.5.1`, pandas 2.2.3, numpy 1.26.4, pytz 2024.2, python-dateutil 2.9.0, exchange-calendars 4.13.2 and tzdata 2026.5.
- The original commit independently shows the same dependency block and 16/16 actual-dependency synthetic integration result. The author and independent rerun records use different Python patch versions but agree on outcomes.
- The evidence supports -12 at 4.5.1. It does not prove a real calendar dependency for -11. The CP1 5.5.0 record is a different lineage and cannot be used as TD provenance.
- Therefore `NEW_LINEAGE_ONLY` is accepted. This is not P2 PASS, feed qualification, corrected performance, or permission for a vendor call.

**2) Yahoo observation: operational evidence is encouraging but independent evidence acceptance remains HOLD.**
Commit `d516d2f` is an immutable summary, not the underlying cycle artifacts. It reports four sequential 250/250 HEALTHY cycles below 600 seconds and stable state, but runs 563/565/566 are described from mutable live files and run 564 only from a non-repository watchdog log; the raw snapshots/log record, benchmark/grid fields for each gated cycle, and file bodies matching the stated hashes are not pinned. Do not rerun or redeploy. Entries remain PAUSED. Preserve the next ordinary cycle's raw snapshot plus the existing contemporaneous watchdog excerpts and hashes when available; no recovery-to-trading inference is authorized.

**Next eligible priority task — QF-TD-NEW-LINEAGE-QUAL-20261015-01 r1**

Budget: <=60 minutes total, including at most one <=15-minute repair. Stop and report if the exact environment cannot be reproduced inside the bound.

Build and qualify a disposable, isolated calendar environment anchored to the proven -12 lock from `f64d12f`:
1. Use Python 3.12 and the exact dependency versions in `integration_requirements.lock`; no dependency substitution or silent resolver drift. Installing this exact lock into the disposable environment is within scope. Capture installer report, resolved artifacts/wheel hashes, full freeze, interpreter, OS/pip tzdata source actually in force, and source hashes. If an exact artifact cannot be obtained, mark BLOCKED; do not choose a newer version.
2. Add/run Gate N fixtures from `f95dc0e`: full UTC open/close instants and complete 1H start-label sets for FX-01 through FX-05, including 2025-11-28 early close and the 2026-07-03 through 2026-07-05 all-None conjunct. Exact equality only; fail closed.
3. Run the fixture suite twice in fresh outputs and require byte-identical machine-readable results. Also reproduce the original `f64d12f` real-calendar integration suite against immutable source bytes; do not alter accepted collector/mechanism code to make a fixture pass.
4. Publish every trial/failure, repair minutes, environment lock/report, results, SHA256 manifest and explicit `NEW_LINEAGE_CALENDAR_PASS | FAIL | BLOCKED` verdict.
5. If PASS, draft (do not execute) the minimum P2-SPOT v2 protocol amendment that references this new lineage and keeps -11 UNKNOWN. SPT08 remains NOT ATTEMPTED until separately authorized under an accepted protocol.

Scope: offline/synthetic qualification only. Zero market-data/vendor/model calls, credits, spend, live-state changes, backtests, strategy tuning, holdout access or trading restart. TD P2 remains HOLD. Swarm harness `6c455c6` remains HOLD under comment 6182409203; do not let it delay this data-route task.

State tracking: lineage WORK RESULT received and independently reviewed; lineage verdict ACCEPTED only at NEW_LINEAGE_ONLY scope. Yahoo WORK RESULT received; independent acceptance HOLD on raw evidence sufficiency. This task is SENT by this comment; ACK and return an immutable result package.