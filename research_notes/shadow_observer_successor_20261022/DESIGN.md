# DESIGN — shadow signal-only observer (successor to task -80)

Status: CANDIDATE, **NOT LAUNCHED**. Prepared under ChatGPT's
expedite assignment (Issue #1 comment 6353427339) after its
independent inspection of the pinned -80 package (7d7d6b7) found
the -80 runner undeployable despite its 6/6 synthetic suite. The
-80 package is untouched and its safety record stands (S1–S6
re-run ALL PASS at this build); this package is its bounded
successor, not a rebuild and not a revision of -80's evidence.

## What stage 1 is

A launchable, signal-only observer: on each cycle it runs the
frozen V5.4 signal path (250-name cohort, closed 4H bars) and
appends every qualified signal to a timestamped, append-only,
idempotent `SHADOW_OBSERVATION` log (`counts_as_trade: false`).
It records NO hypothetical entries, exits, or fills of any kind —
the assignment's first gate, chosen so prospective signal
collection is not blocked on hypothetical-fill fidelity. It is
diagnostic forward observation, not a trading-edge test.

## The four -80 blockers, closed by construction

| # | -80 blocker | successor construction |
|---|---|---|
| B1 | `main()` unconditionally raised "design-stage module" | `shadow_signal_runner.main()` is operational: `--dry-run` runs a full cycle on a synthetic fixture (exercised end-to-end by the suite); live mode is gated by a `LAUNCH_AUTHORIZED.json` artifact (Mike's GO), refusing BEFORE any adapter use or write if absent/mismatched |
| B2 | `market_ok=True` set unconditionally; market-frame failure swallowed | core defaults `market_ok`/`scan_complete` to False unless positively supplied; the live adapter derives `market_ok` from an actual market-frame fetch in the same cycle; a blind/incomplete cycle is appended as DEGRADED with named reasons and records nothing |
| B3 | no comparison of `signal_bar_close_at` to a frozen prospective launch instant — stale/backfill possible | launch watermark T0 is frozen into `launch_manifest.json` in the shadow root at first initialization and can never move (different T0 = refusal); a signal records only if T0 < bar_close ≤ cycle instant; pre-T0 = PRELAUNCH_SIGNAL refusal, unclosed bar = PARTIAL_BAR_NOT_CLOSED refusal; refusals are appended as evidence; off-grid bar starts and naive/unparseable stamps are refused by name |
| B4 | crash between log append and state save could strand a signal (seen, but lifecycle lost) | there is NO state file and NO lifecycle at this stage; the log is the only artifact and the seen-set is rebuilt from it at every startup; appends are fsync'd; a torn final line (interrupted append) is detected, truncated as never-committed, and the recovery is itself logged |

## Isolation

- The core imports ONLY the standard library. The runner imports
  production modules lazily, inside the live adapter/universe
  functions only; importing either module loads no production code
  (suite I1, subprocess-verified). The production harness and log
  writer are never imported by either module.
- The Mode B exit tracker is deliberately NOT pinned or loaded —
  a disclosed divergence from -80: stage 1 simulates nothing, so
  the tracker would be dead weight and a needless import surface.
  If lifecycle mode is ever proposed, it returns as a separate
  candidate with its own catch-up-fill and crash-seam tests.
- All writes are rooted at the shadow namespace (`v54_shadow/`
  by default): exactly `launch_manifest.json` + `shadow_log.jsonl`
  (suite F2). Production hashes/sentinels are unchanged across
  cycles in the sandbox (suite F1).
- Pin discipline: `verify_pins()` hashes the six frozen-stack
  modules the live adapter uses BEFORE any fetch and refuses on
  mismatch. All six pins were re-verified 2026-10-22 against the
  running stack and match -80's recorded pins byte-for-byte.
- Workload bound: one cycle = one cohort scan pass + one
  market-frame fetch (the ordinary production scan cost), no
  retries, no extra symbols, no publishing (suite J2 counts
  exactly one fetch per cycle, after pins).

## Deliberate divergences from production (disclosed)

1. Signal-only: no entries are simulated, so none of -80's
   lifecycle divergences (blind-entry rule, etc.) exist here.
2. Per-signal refusals are recorded even on HEALTHY cycles
   (evidence of the T0/grid gates working); a DEGRADED cycle
   records no per-signal anything — degraded data is never
   reinterpreted.
3. Serial, single-process, no scheduler entry, no GitHub
   publishing in stage 1 (as -80).

## Exact commands (candidate rehearsal)

```
python3 -B shadow_signal_runner.py \
  --repo-root <repo> --root <shadow_root> \
  --t0 2026-10-22T00:00:00+00:00 \
  --dry-run --fixture <fixture.json>
python3 -B tests/test_shadow_signal_observer.py   # acceptance suite
```
