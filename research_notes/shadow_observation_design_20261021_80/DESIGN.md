# ISOLATED SHADOW-OBSERVATION DESIGN — TASK -80

**Status: DESIGN ONLY. Nothing in this package is launched, installed, or
scheduled.** Launch requires the completed LAUNCH_READINESS.md checklist,
ChatGPT adjudication of this package, and Mike's explicit launch GO.

**Authority:** Mike's two-track directive, chat 2026-10-21 19:29 ET.
Track 1: get forward observation running again as a *separately labeled
shadow cohort* — record new signals without opening positions, preserve
the frozen strategy, timestamp every signal, log what the hypothetical
entry/exit rules would have done. Track 2 (historical validation)
proceeds in parallel and does not block read-only observation. Governing
constraints from the same directive: shadow evidence is **not** a proven
trading edge; paper entries do **not** restart until the pause and
data-integrity gates are satisfied; Nov 20 is a data-quality checkpoint,
not a start date.

**Why a new design is required (verified from the repo, 2026-10-21):**
under the -37 pause gate (deployed harness sha256 `ce7c902c…`, sentinel
`forward_test/PAUSE_NEW_ENTRIES` present, resume control absent) the
production harness logs **no new signals at all** — post-gate cycles are
exit-management only (reconciliation memo
`research_notes/FORWARD_TEST_RECONCILIATION_20261021.md`, commit
`6af7632`). The artifacts that do still accumulate (the scan output and
the fvg/lonewolf sidecar logs) are not the frozen V5.4 signal path, and
the reconciliation rules that such sidecar events must **never** be
retroactively counted as trades. The cohort classification is frozen
(commit `e429331`): audit ledger 24 closed / +10.0547R; validation cohort
21 closed / +13.0547R. The shadow cohort defined here is a **third,
disjoint record** that can never merge into either.

---

## 1. Architecture

```
                    frozen stack (pinned, read-only)
   ┌──────────────────────────────────────────────────────────┐
   │ v54_engine ──► signal rows      masterscanner_api ──►    │
   │ (scan/classify)                 Yahoo closed 4H bars     │
   │ v54_rules (gates/grades)        scanner_rules (bar math) │
   └───────────────┬──────────────────────────┬───────────────┘
                   │ qualified rows           │ bar frames (in memory)
                   ▼                          ▼
            shadow_runner.py  ──►  shadow_core.ShadowObserver
            (launch-time binding)     │  records + hypothetical
                                      │  lifecycles via the PINNED
                                      │  v54_exit_tracker.ModeBTracker
                                      ▼
                        v54_shadow/  (the ONLY writable root)
                          shadow_log.jsonl    (append-only)
                          shadow_state.json   (atomic replace)
```

Three pieces, all in this package:

- **`shadow_core.py`** — the observer: record schema + labeling, the
  append-only shadow log, the shadow state store, dedup, cycle
  orchestration, fail-closed degradation handling, and the lifecycle
  driver. Imports only the standard library plus the one pinned
  production module it executes (§2).
- **`shadow_runner.py`** — the launch-time binding: pin verification,
  the frozen universe, detection via the frozen engine, bar-frame
  construction, per-bar EXIT-state evaluation, health assembly. It is
  *reviewed code*, never executed by the safety suite (statically
  checked only), and its `main()` refuses to run at design stage.
- **`safety_checks/`** — the offline proof suite (S1–S6) and its
  committed results.

The production harness is a **separate process** and is never imported,
patched, subclassed, or invoked by either shadow module.

## 2. (a) Signal source — the frozen V5.4 signal logic, in observation mode

Detection runs the frozen signal path itself, in the shadow's own
process: `v54_engine.v54_scan_symbols(universe, themes, "4h", "180d")`
followed by `v54_engine.v54_qualified_signals(rows)` — the same
functions, the same closed-bar construction, the same hard gates
(`v54_rules`: structural candidate + ADX ≥ 20) and the same A/B/C
grading (rule version `2026-09-15-v54`). The universe is the frozen 250:
UX51 from `hybrid_exit_test.UNIVERSE_X` (51) + the X2 cohort from
`v54_universe_x2.UNIVERSE_X2` (199), themes `Forward-UX51` /
`Forward-X2`, assembled exactly as the production cycle assembles them.

Pinned modules (sha256 recorded 2026-10-21 from the running stack;
verified by the runner before any download — a mismatch is a hard
fail-closed stop, no observation under unverified code):

| Module | sha256 | Role in the shadow |
|---|---|---|
| `v54_engine.py` | `bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb` | scan + classify + qualified-signal selection |
| `v54_rules.py` | `1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a` | frozen hard gates + A/B/C grading |
| `v54_exit_tracker.py` | `3ee92864f1afe98ce543803b8b844c1677a6d0e0ce1a6e61d1b7ea74b329a9e0` | frozen Mode B state machine (the only module the core executes) |
| `scanner_rules.py` | `62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c` | canonical session/bar math used by the engine |
| `masterscanner_api.py` | `c3e95b25b114a50c4129360f24f4fd27471b000a7749fe750abf038f1abf0a21` | data downloads + indicator math used by the engine |
| `v54_universe_x2.py` | `44b0d8ba5a7ea6415652fdfa1e89a0f9bb57d191bfb0d66c578f9d7a3f5880c9` | frozen X2 cohort |
| `hybrid_exit_test.py` | `9140504f6449cafe62e1647ccbacaa384427a56ff111cab8c6e9298a220cf45b` | frozen UX51 universe |

For reference only (never imported by the shadow): the production
harness `v54_forward_harness.py` at `ce7c902c…` (the -37 pin) and the
production log writer `v54_forward_log.py` at `9e9b686a…`.

"Observation mode" means precisely: the engine's outputs are consumed
as *records and simulation inputs* in the shadow process. No signal the
shadow sees can stage a pending entry, open a position, append to the
production log, or reach the AI Observer — those code paths live in the
harness module, which is outside the shadow's import graph (proved by
S3). The shadow takes **all** qualified signals (including C grades,
exactly as the frozen anti-drop rule requires); it applies **no**
portfolio caps — caps are portfolio construction, and applying them
would post-select an observation record. One production behavior *is*
mirrored, because it is part of the observable lifecycle semantics: the
one-open-lifecycle-per-symbol rule (§5).

## 3. (b) State isolation

- **Namespace:** a single new directory, `v54_shadow/`, at the repo
  root — a sibling of the production state directory, sharing no files
  with it. (The pre-existing `forward_test/kama_shadow.json` is an
  unrelated KAMA sidecar artifact, not this design.)
- **Files:** exactly two, both inside the namespace:
  `shadow_log.jsonl` (append-only audit log — the source of truth) and
  `shadow_state.json` (observer state, written atomically via
  temp-file + `os.replace`, mirroring the production state writer's
  discipline). Nothing else is created: the process is launched with
  bytecode writing disabled (`python -B`), so imports leave no
  `__pycache__` anywhere (enforced and verified in S1).
- **Process isolation:** a separate OS process and its own scheduler
  entry at launch, offset from the production hourly cycle so the two
  never contend for the data route at the same minute. The shadow has
  no GitHub publishing in v1 (no snapshot, no push) — its outputs are
  local files only.
- The core's constructor takes the writable root as an explicit
  argument; there is no default path and no production path literal
  anywhere in the shadow code (S3 literal scan).

## 4. (c) Labeling — a third, self-identifying record

Every record the shadow writes carries, by construction:

```json
{
  "record_kind": "shadow_signal | shadow_event | shadow_close | shadow_cycle",
  "schema": "shadow-obs-v1",
  "cohort": "SHADOW_OBSERVATION",
  "counts_as_trade": false,
  "logged_at": "<UTC ISO>",
  "shadow_id": "shadow:v54:<SYM>:4h:<bar-close ISO>:2026-09-15-v54"
}
```

- The **id namespace is disjoint**: shadow ids are the source signal
  ids under a `shadow:` prefix, so a shadow record can never collide
  with, or be mistaken for, a production `v54:` signal id.
- `counts_as_trade: false` is the machine-readable non-trade flag. The
  log writer is defense-in-depth: it *refuses* to write any record
  lacking the cohort label or carrying anything but
  `counts_as_trade: false`.
- Record kinds mirror the production log's shape (signal / event /
  close) under shadow names, so the two logs are structurally
  comparable but never interchangeable.

## 5. (d) Timestamping

Every signal record carries **both** clocks, always:

- `signal_bar_start_at` and `signal_bar_close_at` — the signal bar's
  exchange-local (ET) ISO timestamps exactly as emitted by the frozen
  engine. Bar identity and labels come from the pinned closed-bar
  construction (`scanner_rules` session-bar math, 09:30-anchored
  session grid) — the same functions the production cycle uses, so
  shadow bars are the same bars, labeled the same way; the design
  introduces no new grid (the Oct-3 candle-parity lesson).
- `detected_at_utc` — the wall-clock instant (UTC) at which the shadow
  recorded the signal. Lifecycle events and closes carry
  `detected_at_utc` for the cycle that computed them; every record
  additionally carries `logged_at` (UTC).

## 6. (e) Hypothetical lifecycle simulation — the frozen stack itself

The simulation is **not** a reimplementation. The core drives an
in-memory instance of the pinned `ModeBTracker` from
`v54_exit_tracker.py` — the identical state machine the production
harness drives — with the tracker's event sink feeding the shadow log
and `close_summary` producing the frozen-schema close record (wrapped
in the shadow label). Fidelity is therefore by construction, and S5
demonstrates it against hand-computed fixtures.

Frozen semantics, as implemented by the pinned tracker and exercised
by S5:

- **Hypothetical entry:** the open of the first completed bar after
  the signal bar (the production pending-fill convention). Entry at
  or below the structural stop is invalid (no lifecycle); an entry
  gapping to/above TP1 closes immediately (`gap-above-target`) — both
  exactly as in production.
- **Stop:** a bar low touching the structural stop fills **at the stop
  price**; the stop is checked **before** TP1 (stop wins same-bar
  ties). The stop never moves.
- **TP1:** first touch realizes 50% at the TP1 price
  (`partial_r = 0.5 · R(TP1)`); the runner continues on the structural
  stop. No EXIT evaluation happens on the TP1 bar itself.
- **Profit Protect:** a bar high reaching **+1R** arms it (sticky).
  A scanner EXIT state closes a position **only when armed**, filled
  at the **next bar's open** (`scanner-exit` / `runner-exit`).
- **Time exit:** at 30 bars held, close at that bar's close
  (`time` / `runner-time`).
- **R accounting:** `R(px) = (px − entry) / (entry − stop)` (the
  tracker's fraction form is algebraically identical); a runner close
  blends `0.5 · R(TP1) + 0.5 · R(exit)`. MFE/MAE tracked per bar.
- **Per-bar EXIT input:** the scanner state as of each bar, computed
  from data truncated at that bar (the production information rule) —
  never from future bars.
- **Bars walked:** starting with the entry bar itself, every new
  completed bar in order; re-fed bars are no-ops (the tracker's
  processed-bar idempotence), which is what makes restart safe.
- **One lifecycle per symbol:** a signal arriving while a lifecycle
  for the same symbol is awaiting entry or open is still *recorded*
  (observation completeness) and its lifecycle is marked
  `skipped_symbol_busy` with an explanatory event — mirroring
  production's signal + skip-event pattern.
- **Blind-entry rule (deliberate, documented divergence):** if a
  symbol's data was degraded in any cycle after its signal and before
  its entry bar is processed, the hypothetical entry is marked
  `hypothetical_entry_unexecutable` and never simulated. Production
  has a narrower timing exception for a single-blip deferral whose
  fill bar completed after the last blind attempt; the shadow does
  not replicate it. The divergence is one-directional and safe: the
  shadow may simulate *fewer* fills than production would have, never
  more, and never one whose fill bar completed while blind.

## 7. (f) Data route — read-only by construction

The shadow reads market data through the same recovered Yahoo route
the production cycle uses — `masterscanner_api.download_data` (the
entry point `v54_engine` calls) returning **closed** 4H bars — but it
does so in its own process, into memory, and **writes nothing outside
its namespace**. Precisely:

- It **reads**: Yahoo bars via the pinned data modules (network GETs);
  the pinned stack files (hash verification at startup); its own
  state/log files.
- It **never opens for writing**: the production state file, the
  production append-only log, the pause/resume sentinels, the observer
  log/export, the status/closed-trade outputs, or any Git remote.
  There is no code path that could: the harness and production-log
  modules are absent from the import graph (S3), the only production
  module executed (the exit tracker) imports nothing but the standard
  library's typing helpers and performs no I/O (verified in S3), and
  the writable root is an explicit constructor argument (verified
  dynamically in S1/S2).
- **Known v1 limitation, disclosed:** the production cycle's download
  hardening (batch prefetch of the intraday shapes, provider-health
  accounting, bounded retries) lives in the harness module and is
  therefore *not* reused. The shadow downloads serially through the
  unpatched entry points. Observation is not time-critical — a slow or
  failed download degrades the cycle (§8) instead of corrupting the
  record — so v1 accepts this. Any future hardening must be built
  inside the shadow's own modules, never by importing the harness.

## 8. (g) Feed degradation — fail-closed

A cycle is **DEGRADED** when any of: the market frame is unusable; the
universe scan is incomplete (any of the 250 symbols errored or
missing — the Guard-1 analogue: never decide on partial data); any
symbol the cycle's work touches lacks a usable frame; or any lifecycle
had to be deferred. A DEGRADED cycle:

- records **zero new signals** — and does not consume them. Detection
  re-runs over the same closed bars on the next healthy cycle, and
  id-based dedup prevents doubles, so a degraded cycle loses nothing
  and invents nothing;
- writes an explicit `shadow_cycle` record with `status: "DEGRADED"`,
  the expected/degraded symbol lists, and counts — a degraded cycle is
  never reported as "no signals";
- advances lifecycles **only** on symbols with valid frames; a
  lifecycle on a degraded symbol gets an explicit
  `shadow_data_deferred` event and is not advanced on invented data
  (exits are never assumed), with the blind-entry rule of §6 applying
  to awaiting entries.

Every cycle — healthy or degraded — writes exactly one `shadow_cycle`
record, so the log is a complete, gap-free account of the observer's
own health.

## 9. (h) Dedup, restart, resume

- **Dedup** is by `shadow_id` (derived from the frozen engine's
  signal id), persisted in the state file's seen set. A signal is
  recorded exactly once, ever; re-detection after an outage or a
  restart is a no-op.
- **Writes are ordered log-first, state-second** each cycle (the log
  is the source of truth, the same rule as the production log). On
  startup the observer **reconciles from the log**: signal ids in the
  log are unioned into the seen set and any lifecycle the log already
  closed is marked closed — so a crash between append and state save
  can produce neither a duplicate signal nor a duplicate close
  (exercised in the suite's S1/S4 scenario, which rolls the state
  back mid-close before restarting).
- **Tracker rehydration:** tracker positions are plain dicts stored
  in the shadow state; on restart they are reloaded into a fresh
  tracker instance, and already-processed bars no-op on re-feed.
- **Corrupt state fails closed:** an unreadable state file or a
  cohort-label mismatch raises and the cycle does not run. A missing
  state file means *first launch only* — creating one is a launch
  act, not a runtime recovery (see LAUNCH_READINESS.md).
- **No backfill, ever:** observation begins at the declared launch
  instant. Bars completed before it are never simulated, and signals
  from before it are never recorded (mirrors the forward test's
  no-backfill rule).

## 10. (i) Governance invariants

- **G1 — Disjoint forever.** The shadow cohort is a third record. It
  is not the audit ledger, not the validation cohort, and no tool may
  merge, sum, or re-label it into either. Any analysis that touches
  shadow records must cite the `SHADOW_OBSERVATION` cohort label.
- **G2 — Never retroactively trades.** Per the reconciliation ruling,
  shadow/sidecar events must never be counted as forward-test trades —
  not at launch, not later, not by re-interpretation. If a future
  paper forward test is authorized, it starts from its own declared
  prospective start under its own preregistration (the reconciliation
  memo's §4 route); the shadow log is not a substitute and not a
  feeder.
- **G3 — Not an edge claim.** Shadow results are prospective
  *observation* under frozen rules. They must never be reported as a
  proven trading edge, and they cannot satisfy the forward test's
  ~50-signal interim / ~100-signal verdict rule, which belongs to a
  real paper cohort.
- **G4 — The pause is untouched.** The shadow does not read, modify,
  or interact with the -37 gate or its sentinels, and its running is
  not an unpause. Paper entries remain governed solely by the gate
  plus Mike's separate decision.
- **G5 — Frozen means frozen.** The shadow observes the strategy
  exactly as pinned. Any pin change is a new design version requiring
  re-verification (S1–S6), re-adjudication, and a new GO — never a
  silent edit.
- **G6 — Kill switch.** Stopping the shadow is stopping its process.
  It holds no position, no pending state, and no control over
  production; nothing needs unwinding.
- **G7 — Append-only.** The shadow log is never edited or rewritten;
  corrections are new records. Deletion of the namespace is Mike's
  call only.
- **G8 — Launch is a decision, not a default.** §11 lists what must
  be true, and whose approval is required, before the first cycle.

## 11. What must be true before a launch

1. This package's safety suite green on the exact committed bytes
   (S1–S6 PASS in `safety_checks/SAFETY_CHECK_RESULTS.md`).
2. ChatGPT adjudication of this design (Track-1 review), including
   the disclosed divergences (blind-entry rule, no download
   hardening, no AI Observer in v1).
3. **Mike's explicit launch GO** naming the prospective start —
   observation begins at that instant, with no backfill (§9).
4. At launch: pin re-verification against §2's table, the namespace
   created empty, the first cycle supervised, and a post-first-cycle
   verification that production hashes and sentinels are untouched.
5. The -37 pause gate remains in force throughout; nothing in a
   launch changes any production file, schedule, or state.

## 12. Safety evidence (this package, offline)

| Check | What it proves | Result |
|---|---|---|
| S1 | A fixture run writes only inside the shadow namespace (whole-tree diff) | PASS |
| S2 | Production state hashes identical before/after (byte-identical sandbox replica of the real files) | PASS |
| S3 | No import or call path from the shadow runtime to the production harness's staging/opening/state/publishing functions; the one executed production module is I/O-free | PASS |
| S4 | Every emitted record carries the cohort label, the non-trade flag, and (for signals) both bar timestamps + detection instant; dedup and exactly-one-close hold across a crash + restart | PASS |
| S5 | The lifecycle simulation reproduces the frozen Mode B stack on three hand-computed trades: stop-out −1.0000R; TP1 + runner-exit +1.9000R (EXIT on the TP1 bar correctly ignored; no close before the next-bar-open fill); 30-bar time exit +0.2000R | PASS |
| S6 | A degraded cycle yields zero signals + a DEGRADED marker, and the un-consumed signal is recorded by the next healthy cycle | PASS |

Full machine-readable detail: `safety_checks/results.json`;
human summary: `safety_checks/SAFETY_CHECK_RESULTS.md`.
Reproduce: `python3 safety_checks/run_safety_checks.py` (offline,
synthetic fixtures only; the suite resolves the pinned tracker from the
repo and verifies its hash before importing it).

## 13. Known limitations of v1 (disclosed, deliberate)

- No AI Observer assessments (the observer is part of the forward-test
  protocol; adding it to the shadow is a design amendment, not a
  default).
- No portfolio construction: no slot caps, no ranking, no theme
  limits — deliberately, to keep the observation record unselected.
- Serial (unhardened) downloads; a slow feed degrades cycles rather
  than corrupting data (§7/§8).
- The blind-entry rule is stricter than production's (§6): the shadow
  may under-simulate fills after outages, never over-simulate.
- Shadow R is hypothetical-fill R under the frozen conventions (next-
  bar-open fills, stop-at-price) — an observation statistic, not
  execution evidence.

— Muse (design worker, TASK -80), 2026-10-21
