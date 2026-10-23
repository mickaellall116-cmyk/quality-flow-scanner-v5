# Shadow successor repair — V5 fast-exit + V8 hash chain (2026-10-22)

Bounded corrective implementation requested by ChatGPT (Issue #1
comment 6356126182, following the d5a4fe6 parity verification
HOLD and comment 6356026005's read-only intake delta). This
package is a CANDIDATE COPY: `research_notes/
shadow_observer_successor_20261022/` (798de18) and
`research_notes/shadow_parity_verify_20261022/` (d5a4fe6) are
byte-untouched. Nothing here launches anything; LAUNCH remains
HOLD pending Mike's separate GO, and launch gates in
LAUNCH_READINESS.md (copied unchanged) still apply.

Scope discipline: ONLY the two decisive defects are repaired.
ChatGPT's third item — exact symbol-specific grid/close
assertions from a pinned session table (regular 13:30→16:00 2.5h
final bin, 13:00 early close, crypto on its own adopted
continuous calendar) — was graded HOLD, not FAIL, and is NOT in
this bounded repair; it remains an open HOLD item (§4).

## 1. V5 — market-frame fast-exit (shadow_signal_runner.py)

Defect (successor @798de18): `LiveAdapter.fetch()` computed
`market_ok=False` on market-frame failure, then called
`v54_scan_symbols` over the full 250-name cohort anyway.

Repair: after the market-frame fetch, if `market_ok` is not
positively True (exception, None, or empty frame), `fetch()`
returns `([], health)` immediately — `market_ok: False`,
`scan_complete: False`, `scan_skipped: "MARKET_FRAME_NOT_OK"` —
and `v54_scan_symbols` is never called. The core already records
such a cycle DEGRADED and records no signals; the blind cycle now
costs exactly one market fetch instead of a 250-name scan.

Proof (tests/test_v5v8_repair.py, the verification's own stub-spy
method — fake engine/universe modules in sys.modules, scan
counter on v54_scan_symbols, driving the REAL LiveAdapter):

- market raises → scan_calls **0**, symbols_scanned **0**
- market returns None → scan_calls **0**, symbols_scanned **0**
- market returns empty → scan_calls **0**
- positive control (market OK) → scan_calls 1, symbols 250,
  market_ok True (the spy demonstrably sees scans when they
  happen; the zeros are evidence, not a vacuous stub)

Cross-proof: the verify package's own V5 check, re-run against
this repaired copy (VERIFY_REGRESSION_RESULTS.json):
`market_raises {scan_calls: 0, symbols_scanned: 0}`,
`market_returns_none {scan_calls: 0, symbols_scanned: 0}` —
the exact two results that FAILED at 1/250 against 798de18.

## 2. V8 — hash-chained journal (shadow_signal_core.py, schema v2)

Defects (@798de18): `_append()` wrote no prev-hash or record
hash (verify V8: 0/7 records carried any chain field);
`_load_log()` truncated from the FIRST malformed line anywhere,
so mid-log tampering could silently erase later intact records.

Repair (schema bumped to `shadow-signal-v2`):

- Every record carries `prev_hash` + `hash`; hash = sha256 over
  (prev_hash + canonical JSON of the record without the chain
  fields). Genesis prev-hash = sha256(domain ‖ launch-manifest
  bytes) — the chain is bound to the frozen T0 manifest.
- Startup verifies the ENTIRE chain before any append. A
  hash/prev-hash mismatch anywhere, or an unparseable line
  anywhere except the final line, raises ShadowError and alters
  NO bytes. Only a torn FINAL line is truncated + recovered,
  preserving the v1 crash-seam guarantee (acceptance case E2).
- External anchor procedure: `core.verify_chain(log, manifest)`
  recomputes the chain standalone and returns
  {ok, records, genesis, tail_hash, failures};
  `core.check_anchor(report, anchor)` compares against an
  externally recorded anchor; `SignalObserver.chain_anchor`
  exposes the live anchor; the runner gains a read-only
  `--verify-log` mode (exit 0 / 2).
- Disclosed limit, stated in the code: a hash chain alone cannot
  detect suffix truncation (deleting whole tail records leaves a
  self-consistent prefix). The external anchor comparison is the
  control; the test suite proves both halves of that statement
  (prefix verifies; anchor mismatches).
- A legacy unchained v1 log fails verification and refuses
  (this candidate has never launched; no v1 log exists).

Proof (tests/test_v5v8_repair.py, 21 cases): every record
chained; first prev_hash = genesis; linkage exact; external
verify OK and equal to the live observer's anchor; field tamper
detected + startup refuses + bytes unchanged; record deletion
detected; mid-log corruption refuses + bytes unchanged; torn
tail recovers, chain still verifies, recovery record itself
chained; legacy log refused. Cross-proof via the verify
package re-run: V8 `records_with_any_hash_chain_field` =
**7/7** (was 0/7).

## 3. Test evidence (all offline, pinned venv, `unshare -n`)

| Suite | Result |
|---|---|
| NEW tests/test_v5v8_repair.py | **21/21 PASS** |
| Successor acceptance suite (byte-copy of 798de18's, vs repaired modules) | **24/24 PASS** |
| Verify package verify_all.py vs repaired copy | exit 0; V1 8/8, V3 38/38 pin-match, V5 **0/0 both modes**, V6 250 unique, V7 T0 strict, V7b suite 24/24, V8 **7/7** |
| ChatGPT passive auditor suite (655345b, read-only extract) | **11/11 PASS** |
| ChatGPT passive auditor CLI on the actual file | exit 2 HOLD by design; reasons in TASK_A_EVIDENCE §5 |

Full verify-package output against this copy:
VERIFY_REGRESSION_RESULTS.json (in this package).

## 4. What remains HOLD (unchanged by this package)

- **Bin-close / symbol-specific grid assertions** (ChatGPT item
  3): `_validate_candidate` still checks bar-start opens only;
  session-table-derived closes (13:30→16:00 2.5h bin, 13:00
  early close) and the crypto continuous-calendar admission
  path are NOT implemented here. Equity OFF_GRID handling and
  the crypto UNQUALIFIED labeling question stay exactly as the
  verification left them. A valid crypto signal still cannot
  pass the equity-only grid in this candidate — disclosed, not
  silently fixed, because the fix needs the pinned calendar
  decision, which is Mike/ChatGPT-gated.
- **Launch**: HOLD. No LAUNCH_AUTHORIZED.json exists or was
  created; no shadow root was created in the repo; no scheduler.
- **Passive intake route**: the ordinary-cycle output is
  legacy-grid; per comment 6356026005 it is diagnosis-only until
  a corrected-grid producer + independent attestation exist.
- **RAW_1H_NOT_AVAILABLE** for offline corrected-grid cohort
  construction (TASK_A_EVIDENCE §6); the gated capture routes
  named there are not authorized by this package.
- Task A also surfaced a representation mismatch for the desk:
  harness coverage writes `market_data_gap: ""` where ChatGPT's
  auditor accepts only False/None — the auditor's
  COMPLETE_COHORT_AND_MARKET_NOT_PROVEN reason on an otherwise
  healthy, fully-covered cycle traces to this.

## 5. Production integrity

PAUSED production untouched. The 7 code modules, sha256 before
this task and after (identical):

```
ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d  v54_forward_harness.py
bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb  v54_engine.py
1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a  v54_rules.py
62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c  scanner_rules.py
c3e95b25b114a50c4129360f24f4fd27471b000a7749fe750abf038f1abf0a21  masterscanner_api.py
44b0d8ba5a7ea6415652fdfa1e89a0f9bb57d191bfb0d66c578f9d7a3f5880c9  v54_universe_x2.py
9140504f6449cafe62e1647ccbacaa384427a56ff111cab8c6e9298a220cf45b  hybrid_exit_test.py
```

All work was done in a stage directory outside the repo; the
only repo writes are this package's commit and the bridge
entry, both via git temp-index. The pre-existing UU state on
forward_test/kama_shadow.json was never touched; no foreign
stashes were popped.
