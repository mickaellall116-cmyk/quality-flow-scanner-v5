# -38 r1 — INTERFACE & DEPENDENCY MATRIX

Companion to `PREFLIGHT_MEMO.md`. All citations are to immutable commit `ab254c3458697dd450356146abcf4ad4f75ecef4` unless stated otherwise. Static reading only; nothing executed.

## §1 Calendar import / validation call graph (pinned at `ab254c3`)

```
td_min_collector.py  (b683d277…)
  Collector._handle_response(req, status, body)          [non-200 → classify]
    └─ Collector._classify_closed_session(req, status, body)   → proof dict | None
         conjunct (2) wire: HTTP 400; JSON keys exactly {code,message,status,meta};
                      code is int 400; status "error"; message == CLOSED_SESSION_MESSAGE
                      ("No data is available on the specified dates. …");
                      meta exactly {symbol, interval, exchange:""} matching req
         conjunct (1) supplement: sup.supplement_id=="P2-SPOT", sup.version=="v2",
                      sup.base_manifest_digest == collector.manifest_digest,
                      entries[req.request_id].expected_bars == 0 (int),
                      entries[req.request_id].request_digest == canonical_digest(req)
         conjunct (3) calendar (td_min_collector.py lines ~524–546):
                      import pandas_market_calendars as mcal
                      str(mcal.__version__) == sup.calendar.expected_library_version   # "5.5.0"
                      import validate_input
                      sha256(Path(validate_input.__file__).read_bytes())
                          == sup.calendar.mechanism_module_sha256                      # 1b83cdcd…
                      for each date d in [req.start_date .. req.end_date]  (span ≤ 366 d):
                          validate_input.xnys_schedule(pd.Timestamp(d)) is None        # all closed
                      proof = {mechanism, library_version, mechanism_module_sha256, per_date}
                      proof_digest = canonical_digest(proof)
                      → _preserve_closed_day + emit CLOSED_DAY_EVIDENCED(calendar_proof_digest, …)
         any mismatch / exception / unavailability → None → existing HOLD path, byte-for-byte

validate_input.py  (1b83cdcd…)  ::xnys_schedule(day)     [lines 54–64]
    import pandas_market_calendars as mcal               (deferred, in-function)
    xnys = mcal.get_calendar("XNYS")
    sched = xnys.schedule(start_date=day.date(), end_date=day.date())
    sched.empty → None
    else → (Timestamp(row["market_open"]).tz_convert("America/New_York"),
            Timestamp(row["market_close"]).tz_convert("America/New_York"))
```

**Pin carriers.** `p2_spot_supplement_v2.json` (cccd5226…): `calendar.expected_library="pandas_market_calendars"`, `calendar.expected_library_version="5.5.0"`, `calendar.mechanism="pandas_market_calendars:XNYS via pilot_harness/validate_input.py::xnys_schedule"`, `calendar.mechanism_module="research_notes/pilot_harness/validate_input.py"`, `calendar.mechanism_module_sha256=1b83cdcd…`, `base_manifest_id="TD-ACQUISITION-MANIFEST-V2-SPOT8-20261014"`, `base_manifest_digest=748ca957…`, entries REQ-SPT-07 (`a259901e…`) / REQ-SPT-08 (`f547d8fe…`), `status="OFFLINE_CANDIDATE_NOT_ADOPTED"`.

**Version-pin evidence.** Supplement `expected_library_version_basis` → CP1 audit 2026-10-04: `recovery_4h_20261004/cp1_followup/audit_52symbol.json` (`"mcal_version": "5.5.0"`), `cp1_evidence_closure/RESAMPLER_XNYS_EVIDENCE.md:91` (XNYS v5.5.0, market_open/market_close consulted). -11/-12 runtime version not recorded (per supplement).

**Test-side stubbing (why no real 5.5.0 semantics have ever run).** `test_closed_session_classifier.py` installs a fake `pandas_market_calendars` module (`__version__='5.5.0'`, no `get_calendar`) and a stub `validate_input` whose `__file__` points at the real pinned path (so the byte-hash conjunct passes against real bytes) but whose `xnys_schedule` is a fixture function over `CLOSED_DATES={'2026-07-03','2026-07-04','2026-07-05'}`. N10 perturbs the stub (version `'9.9.9'`; module deleted) to prove fail-closed. Families: provenance 1, F1–F2, N1–N12, S1–S3 = 18 tests.

## §2 Compatibility matrix — classifier gate vs qualified `XNYS_SESSION_SCHEDULE_V2` (sha256 `3358f2d9…`, -35 r2 package commit `9c62e25`)

| # | Aspect | Classifier gate requires | V2 artifact provides | Compatibility |
|---|---|---|---|---|
| C1 | Input channel | Live Python import of `pandas_market_calendars`; version string equality vs pin | A JSON file; no library; produced under PMC 4.5.1 | **None** — the classifier has no file/artifact input for calendar truth |
| C2 | Mechanism identity | Exact module bytes, sha256 `1b83cdcd…`, function `xnys_schedule(day)` | Data, not code | **None** — any artifact-reading substitute module fails the byte pin by construction |
| C3 | Calendar key | `mcal.get_calendar("XNYS")` (PMC: EC call-through mirror per -30 audit at 4.5.1; 5.5.0 resolution unverified) | Header `exchange="XNYS"` (a label, not a callable) | Label agrees; semantics not transferable |
| C4 | Per-date oracle | `xnys_schedule(date) is None` ⇔ closed, for every date in the request window | Open days listed; closed days = absence from `sessions[]` | Semantically inter-derivable; **not consumable** by the pinned code path |
| C5 | Open/close values | tz-aware `pd.Timestamp` in `America/New_York` (`market_open`/`market_close` tz-converted) | `"HH:MM"` local-time strings (`"09:30"`, `"16:00"`, `"13:00"`) | Type mismatch (string vs tz-aware Timestamp); values correspond for the dates both cover |
| C6 | Early closes | Reflected in `market_close` (13:00 ET) of the schedule frame | `close="13:00"` rows (exactly five in coverage) | Correspond; informational only |
| C7 | Coverage / boundary | No coverage concept; iterates the request window, span ≤ 366 days, all dates must be closed | Frozen coverage 2024-09-16 → 2026-10-16, 524 sessions, boundary enforced by its own consumers | No shared boundary semantics; the SPOT8-era windows fall inside the artifact's coverage, which is moot — the gate never consults it |
| C8 | Library version | Exactly `"5.5.0"` | Artifact generated under PMC **4.5.1** (qualified env, NL lock `08b38cfa…`) | **Gate fails by design under 4.5.1** — classification disabled, HOLD path |
| C9 | Consumer | TD collector front-gate (SPOT8-scoped supplement) | Fold materializer v3 (`e1b0dfed…`), validation-contract lane | Different lanes; no shared consumer |

**Matrix conclusion:** field-level semantic correspondence (C4–C6) does not create a substitution path (C1–C2, C8). The classifier requires **live PMC 5.5.0 semantics**; the artifact is a non-substitute by construction, not an incompatible-format candidate. Hence this preflight's HOLD is dependency-shaped (`DEPENDENCY_ARTIFACT_MISSING__HOLD`), not `INTERFACE_INCOMPATIBLE__HOLD`.

## §3 Dependency inventory — PMC 5.5.0 and transitive pins (committed / local evidence only)

| Item | Required by | Present? | Evidence |
|---|---|---|---|
| `pandas_market_calendars==5.5.0` wheel | Supplement pin `expected_library_version="5.5.0"`; classifier conjunct (3) | **NO — MISSING** | Filesystem-wide search: zero 5.5.0 artifacts. Persistent wheelhouse `~/workspace/td_nl_wheelhouse_20261016/wheels` (manifest `210b8273…`) holds **4.5.1** (`pandas_market_calendars-4.5.1-py3-none-any.whl`, `7b4f3478…`); all trial/scratch wheel copies on host are 4.5.1 |
| 5.5.0 transitive closure (its `Requires-Dist`: versions + wheel hashes) | Any reproducible 5.5.0 environment build | **NO — MISSING** | No committed lock/freeze/manifest records a 5.5.0 closure. The only committed TD lock, `integration_requirements.lock` at `ab254c3`, is the **4.5.1** closure: exchange_calendars 4.13.2, korean_lunar_calendar 0.4.0, numpy 1.26.4, pandas 2.2.3, pandas_market_calendars 4.5.1, pyluach 2.3.0, python-dateutil 2.9.0, pytz 2024.2, six 1.17.0, toolz 1.2.0, tzdata 2026.5 |
| 5.5.0 runtime record (historical) | Basis for the pin | YES (record only) | CP1 audit 2026-10-04 (`audit_52symbol.json`, `RESAMPLER_XNYS_EVIDENCE.md`) — records the version as *observed then*; the environment itself is lost and no wheel survives from it |
| Pinned validator bytes | Classifier conjunct (3) | YES | `validate_input.py` at `ab254c3` hashes to exactly the pinned `1b83cdcd…` |
| Classifier + supplement + suite bytes | Proof inputs | YES | At `ab254c3`: `b683d277…`, `cccd5226…`, `3122bdfc…` (see PREFLIGHT_MEMO Q1) |
| Supporting pilot_harness pins (limiter/verifier/constructor) | Full-loop proof runs | YES | `integration_results.json` at `ab254c3`: `rate_limiter.py 06ad383d…`, `verify_sources.py a0bd2e4c…`, `construct_4h.py d47e8df1…` (that package ran under the 4.5.1 lock, PMC calendar path not exercised — its README states full calendar integration was not run) |

**Inventory conclusion:** exactly one dependency artifact class is missing — the PMC 5.5.0 wheel and its transitive pin/hash evidence. Per spec step 3: named here, HOLD returned, no fetch/download/install/import/substitution performed or proposed within this preflight.
