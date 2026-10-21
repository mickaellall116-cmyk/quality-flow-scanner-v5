# LAUNCH READINESS — shadow observation (TASK -80)

**This task does not launch anything.** No shadow process is running,
no namespace exists in the production tree, no scheduler entry was
created, and no production file was touched. This checklist is what a
*future* launch decision must verify, in order. Every box must be
checked and evidenced before the first shadow cycle runs.

## A. Design evidence (must be green on the committed bytes)

- [ ] `safety_checks/run_safety_checks.py` re-run against the final
      committed package: **S1–S6 all PASS**, results regenerated and
      committed (`SAFETY_CHECK_RESULTS.md` + `results.json`).
- [ ] Package manifest (`SHA256_MANIFEST.txt`) verifies: every file in
      the package matches its recorded hash.
- [ ] The design's disclosed divergences are accepted as-is (no silent
      fixes): the stricter blind-entry rule, serial unhardened
      downloads, no AI Observer in v1, no portfolio caps.

## B. Independent review

- [ ] ChatGPT adjudication of the -80 package recorded (Slack +
      bridge), including the S3 static-isolation scope and the S5
      hand-computed fixtures.
- [ ] Any adjudication-required changes are made as a **new package
      version** with the suite re-run — the adjudicated bytes are the
      launched bytes.

## C. Mike's launch decision

- [ ] Mike's explicit launch GO, naming the **prospective start**
      (date/time). Observation begins at that instant; bars and
      signals before it are never recorded or simulated (no backfill).
- [ ] The GO is understood to be observation-only: it does **not**
      unpause entries, does not touch the -37 gate, and creates no
      paper positions anywhere.

## D. Launch-day verification (before the first cycle)

- [ ] Pin verification passes against DESIGN.md §2's table
      (`shadow_runner.verify_pins` + the tracker's pin in the core):
      engine, rules, exit tracker, scanner rules, data module, both
      universe modules — all hashes match the running stack.
- [ ] Namespace created **empty**: `v54_shadow/` with no pre-existing
      log or state. A pre-existing non-empty namespace aborts the
      launch (it would mean observation already started, or state is
      ambiguous).
- [ ] Production untouched at T-0: hashes of the production state
      file, production log, status output, and both sentinel paths
      recorded; the pause sentinel present, the resume control absent.
- [ ] Process setup: separate process from the production harness;
      invoked with `python -B` (no bytecode writes); its own
      scheduler entry offset from the production hourly cycle; the
      design package's `shadow_core.py` / `shadow_runner.py`
      installed beside the pinned stack (repo root) *by copy from the
      adjudicated package*, with their hashes re-verified after
      copying.

## E. First-cycle supervision

- [ ] First cycle run supervised; its `shadow_cycle` record inspected
      (status, coverage lists, new-signal count).
- [ ] Post-cycle verification: production hashes and sentinels from
      D are re-checked and unchanged; the only new files on disk are
      inside `v54_shadow/`; every record in `shadow_log.jsonl`
      carries the `SHADOW_OBSERVATION` label and
      `counts_as_trade: false`.
- [ ] The launch (start instant, first-cycle summary, verification
      results) is reported to Mike and recorded on Slack + the bridge
      before the observer is left running unattended.

## F. Standing rules once running

- Observation is reported as observation: never as a proven edge,
  never merged into the audit ledger or the validation cohort, never
  counted toward the forward test's sample-size verdicts.
- A pin change, a design change, or a suite failure on re-run stops
  the observer pending re-adjudication (frozen means frozen).
- Stopping the observer is stopping its process; it holds nothing
  that needs unwinding. Deleting the namespace is Mike's call only.

— Muse (design worker, TASK -80), 2026-10-21
