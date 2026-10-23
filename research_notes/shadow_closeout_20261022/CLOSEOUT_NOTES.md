# Shadow closeout — manifest pin binding + session-table admission (2026-10-22)

Final bounded OFFLINE code/test closeout requested by ChatGPT's
independent verdict on the V5/V8 repair (Issue #1 comment
6356610693; Slack TS 1792725800.602239). That verdict: V5
fast-exit PASS, V8 hash-chain PASS (source), launch HOLD on
data/parity items. Items 3 and 4 of the verdict are the two
code/test items; this package closes exactly those, in a NEW
candidate copy (schema `shadow-signal-v3`):

- `research_notes/shadow_observer_successor_20261022/`
  (798de18) and `research_notes/shadow_successor_repair_
  20261022/` (4130e74) are byte-untouched.
- No LiveAdapter wiring changes (the runner's adapter is
  byte-identical to the repair's; the only runner deltas are
  in observe_once / --verify-log, below). No Yahoo load, no
  vendor calls, no capture, no holdout, no performance, no
  production change, NO LAUNCH: no authorization artifact was
  created, no shadow root exists in the repo, no scheduler.

## 1. Manifest pin binding (verdict item 4)

The v2 manifest bound only T0/cohort/mode. The v3 manifest
additionally carries `pins` — the full frozen set from
`shadow_closeout_pins.EXPECTED_PINS`:

- `candidate_commit`: 4130e74 (the repair lineage this
  successor is cut from; a self-referential own-commit pin is
  impossible — the launch-day re-pin, already a named launch
  step in the verdict, replaces it);
- `stack_pins`: the six live-stack pins, unchanged from the
  successor/repair lineage;
- `module_hashes`: sha256 of this package's core + runner as
  shipped (the pins module itself is excluded — self-reference
  — and is pinned by the package SHA256_MANIFEST + git);
- `universe`: count 250, ordered digest `77381fe4…` (sha256
  of LF-joined ordered symbols + trailing LF), shipped
  universe.json hash, 25 crypto / 225 equity split;
- `calendar`: version `XNYS-751-UNION-20261021`, shipped
  session_table.json sha256 `00c5555c…`, 751 sessions;
- `rule_version`: `2026-09-15-v54`;
- `authorization`: artifact name, `artifact_sha256: null`,
  state `NOT_AUTHORIZED` — the slot is frozen into the bound
  set; no artifact exists or was created.

Binding mechanics (core, verified at EVERY startup alongside
the hash-chain genesis binding, which still derives from the
raw manifest bytes):

- the manifest carries `manifest_digest` = sha256 over the
  canonical manifest without the digest field; startup
  recomputes it — any altered manifest byte refuses;
- startup requires manifest `pins` to equal EXPECTED_PINS
  exactly — a swapped/added/dropped pin refuses (fixtures
  recompute the digest after swapping, so the pin-equality
  control itself is what fires);
- startup recomputes the on-disk candidate module hashes
  against the pins — a swapped module file refuses even with
  an intact manifest (fixture M9, subprocess against a copied
  package with altered runner bytes);
- EVERY record appended carries `manifest_digest` (verdict:
  "make every cycle record carry the manifest digest");
- `verify_universe_digest()` binds the runtime cohort: the
  runner's observe_once verifies the adapter-reported
  expected universe against the pinned ordered digest before
  the cycle — a reordered cohort refuses (M7b/M7c);
- external anchor at startup: SignalObserver(anchor_path=…)
  refuses on a missing anchor file (M8a) or a stale anchor
  (M8c) and opens on an exact match (M8b); the runner's
  `--verify-log --anchor` exits 0 on match, 2 on missing
  anchor or mismatch (CLI-proven during this build).

## 2. Session-table admission (verdict item 3)

`_validate_candidate` no longer admits on start-wall +
implicit duration. Symbol class comes from the pinned,
digest-verified universe artifact. Admission is exact
start AND end, by class:

- EQUITY — the pinned adopted session table (session_table.
  json: the 751-session XNYS union of XNYS_SESSION_SCHEDULE_V2
  + the -81 extension, adopted 2026-10-21 in the three-gate
  freeze, hash-verified at import). Ordinary session bars:
  09:30->13:30 and 13:30->16:00. 13:00 early-close sessions:
  exactly ONE bar, 09:30->13:00. Non-session date refuses
  (NON_SESSION_DATE). The duration trap is fixture E4: a
  09:30->13:30 bar on the 2025-11-28 early close refuses
  SESSION_TABLE_CLOSE_MISMATCH — admission is by table
  lookup, not by bar duration.
- CRYPTO — never the equity table. The adopted S-C1..S-C6
  continuous calendar (same spec as the -94 model): session
  [D 09:30 ET, D+1 09:30 ET), six wall-anchored 4H bins
  09:30/13:30/17:30/21:30/01:30/05:30 ET (fold=0), the 01:30
  overnight bin absorbing DST. Fixtures: ordinary bins incl.
  overnight (K1-K3); admission on Thanksgiving, an equity
  non-session (K5); spring session 2025-03-08 — span 23
  elapsed hours, absorbing bin 3h admitted, the 4h-elapsed
  trap refused (K8-K10); fall session 2025-11-01 — span 25
  elapsed hours, absorbing bin 5h admitted, the
  wrong-offset close refused (K12-K13). (The verdict's
  "23/24/25" figures are the sessions' elapsed hours —
  equivalently their 1h-bar counts under S-C2; at 4H the
  sessions hold six bins each, with the absorbing bin at
  3/4/5 elapsed hours. K0 asserts all three spans.)
- Wrong class both directions: an equity closing bin
  (13:30->16:00) on BTC-USD refuses CRYPTO_BIN_CLOSE_MISMATCH
  (K4); a crypto-only bin (17:30->21:30) on NVDA refuses
  OFF_GRID_BAR_START (E8). Unknown symbol refuses
  SYMBOL_CLASS_UNKNOWN (K6).

Disclosed divergence from the v2 candidate: dates outside
the adopted table's coverage (after 2026-10-16) now refuse
NON_SESSION_DATE for equity instead of passing a wall-clock
grid check. That is the verdict's intent (session-table-
derived admission), and the launch-day re-pin must extend
the table before any launch — listed in LAUNCH_READINESS.

## 3. Finding (plain) — cross-tzinfo datetime equality

The first draft of the crypto geometry returned ET
datetimes, and its own fall-session fixtures refused every
bin: in this CPython, an ET datetime and a fixed-offset
datetime for the SAME repeated-hour instant (equal
timestamps, equal hashes, zero difference) compare UNEQUAL
with `==`, and subtracting two datetimes that share one
tzinfo object is wall-clock arithmetic (the 25h fall span
read 24.0). This is the same failure class as -94's F-2
(instant vs wall-clock confusion). Fixed before evidence:
all admission geometry is computed and compared on UTC
instants — the -94 model's discipline — and the mechanism
is documented in the code at crypto_session_bins. The
spring/fall fixtures (K0, K8-K13) are the regression proof.

## 4. Test evidence (offline, pinned venv, `unshare -n`)

| Suite | Result |
|---|---|
| NEW tests/test_shadow_closeout.py (M/E/K/P groups) | **39/39 PASS** (run twice, identical) |
| Runner CLI --verify-log / --anchor (one-off, recorded here) | exit 0 / exit 0 with matching anchor / exit 2 with missing anchor |

Regressions against PRISTINE prior packages (byte-untouched;
run in extracted copies):

| Suite | Result |
|---|---|
| Repair suite test_v5v8_repair.py (4130e74 copy) | **21/21 PASS** |
| Successor acceptance test_shadow_signal_observer.py (repair copy) | **24/24 PASS** |
| Verify package verify_all.py (vs repair copy) | exit 0 — V1 8/8, V3 38/38 pin-match, V5 spy (repair copy), V6 250 unique, V7 T0 strict, V7b 24/24, V8 7/7 chained |
| -94 checker suite test_completeness_check_v94.py | **18/18 PASS** |

Full closeout stdout: test_shadow_closeout_stdout.txt.
Regression detail: REGRESSION_RESULTS.json.

## 5. Production integrity

PAUSED production untouched and re-proved: the 7 pinned
module hashes are identical before and after this task
(same table as the repair package's §5; harness ce7c902c
intact). All work was done in a stage directory outside the
repo; the only repo writes are this package's commit and
the bridge entry, both via git temp-index. The pre-existing
UU state on forward_test/kama_shadow.json was never
touched; no foreign stashes were popped.
