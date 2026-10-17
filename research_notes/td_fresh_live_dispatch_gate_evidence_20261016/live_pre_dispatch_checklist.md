# ENFORCEMENT ADDENDUM (-05 r1): the 12 gates below are now enforced executably by dispatch_gate.py in this package (see TD_FRESH_LIVE_DISPATCH_GATE_20261016.md). The wrapper consumes one canonical hash-bound evidence object, writes the canonical gate receipt durably BEFORE any transport construction, and constructs LiveHttpsTransport(armed=True) only on a PASS receipt plus a dispatch token bound to run/manifest/evidence/ledger/window. Text below is the -04 checklist, unchanged.

# Future live pre-dispatch checklist — TD fresh full-manifest run (updated by -04 r1)

Run identity: `TD-FRESH-FM-20261016-03-R1` · Manifest: `TD-ACQUISITION-MANIFEST-V2-FRESH-20261016`
Canonical digest / file sha256: `71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db`
Fresh supplement sha256: `3cbdbf63fd49b021dc74f63727098551753949f8684967981c65f66101f95a86`

**Integrated candidate pins (QF-TD-FRESH-LIVE-DRIVER-INTEGRATION-20261016-04 r1):**
- Entrypoint: `research_notes/td_fresh_live_driver_integration_evidence_20261016/live_driver.py`, sha256 `5fed45242eb5ec465266c4d4c4258485f01a8c5bfdfdda2fb81295d3cf6d9c00`
- Trial harness: `run_integration_trials.py` sha256 `a5697ccba3147db9211904a3ae29e55d83d6877c54d8dc9cb2435ba4c8323cda`; ledger worker `ledger_worker_i.py` sha256 `81f4fbea59a9376a841f537aea750e06cbb71b8882ffa48bdbb8c81392041ab5`
- Integration matrices (twice, byte-identical): sha256 `1c3c76c2a0d219187e85776826aa177002632d06f9af74d3487a1ccc2341e894`
- Collector: commit `ab254c3458697dd450356146abcf4ad4f75ecef4`, bytes sha256 `b683d277cc02a8d27dabc4541ba70a45e5988b5447a28ded5c4aa02ec4cc5d2c`
- Pilot transport source: `pilot_harness/pilot_acquire.py` sha256 `acf39bbd98f7174a4205019e754fc714ca420b4a7df43c815ea158a6fad67c59`; `pilot_harness/rate_limiter.py` sha256 `06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64`
- NL mechanism: `pilot_harness/validate_input.py` sha256 `1b83cdcd4f6e2aaa8f844cb6ca690cd05449ad5985e178967dba49ef1f360f58`; NL env lock sha256 `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`
- Adapter contract: `ec877a04d12e6b0c69378dba245be07ab60279a15c9eb78cc50e8b0c705e166b`
- Live transport binding (in `live_driver.py` constants): endpoint `https://api.twelvedata.com/time_series`; credential ref `custom.twelvedata`; allowed hosts `["api.twelvedata.com"]`; response cap 33,554,432 bytes; timeout 30 s.

Every gate must pass in the live process **before transport is constructed**.
Any unknown, missing, expired, or insufficient item → **HOLD before any request**.
No gate may be waived by the operator of the run.

1. **Adjudicated execution packet.** A separate execution packet, adjudicated
   after this integration (`FRESH_LIVE_DRIVER_INTEGRATION_PASS_OFFLINE`),
   names this run id, the manifest digest above, the supplement hash above,
   the state directory, **the integrated entrypoint pin above**, the exact
   51-credit ceiling, and the dispatch window. Without it, no dispatch.
2. **Authority — do not re-request.** Mike's standing capped free-screen
   authority (2026-10-14 rule) already covers a scoped/capped $0 vendor screen
   inside an adjudicated task. The old direct eight-credit SPOT8 grant is NOT
   the governing ceiling for this separately pinned 51-credit task, and the
   standing authority must not be re-asked. This checklist item records the
   authority basis; it is not a request.
3. **Account plan / status / capacity (live re-verification).** Confirm the
   Twelve Data account is on the Basic plan and in good standing; record the
   plan evidence with a timestamp. Confirm remaining daily capacity ≥ 51
   credits for the dispatch day and minute capacity consistent with the
   8/min cap. Live account/credit state was UNKNOWN at integration time and
   must fail closed: unknown or insufficient → HOLD.
4. **Shared limiter state.** The account-shared limiter ledger is the ONE
   ledger at the operator-pinned path **outside every run namespace**,
   named in the adjudicated execution packet, transacted under its own
   interprocess flock (as proven in I14/I15). Read it immediately before
   dispatch. Ledger corrupt or unreadable → HOLD (never reset it). The
   day's prior reservations count against the same 800/day cap.
5. **Environment reproduction.** The NL environment of record (rebuild commit
   `0923db7`, `NL_ENV_REBUILD_PASS`) is present: CPython 3.12.3,
   `pip freeze` byte-equal to lock `08b38cfa…` (11 packages), all wheel
   hashes equal to the qualified records, `pandas_market_calendars` ==
   4.5.1, mechanism `validate_input.py` sha256 `1b83cdcd…`. Any drift,
   absence, or version mismatch → HOLD; it also disables closed-session
   classification (fail-closed).
6. **Manifest / supplement / source hashes.** Recompute immediately before
   dispatch: fresh manifest file sha256 == canonical digest ==
   `71aade8b…`; supplement sha256 == `3cbdbf63…`; entrypoint sha256 ==
   `5fed4524…`; collector commit `ab254c3…` / bytes `b683d277…`;
   pilot_acquire `acf39bbd…`; rate_limiter `06ad383d…`; adapter contract
   `ec877a04…`; pinned prerequisites `038ccaf3…` confirmed still current.
   The entrypoint itself re-verifies the manifest digest and the
   supplement's exact-byte SHA before parsing/use, and
   `reconcile_supplement()` re-validates every fresh-schema binding field
   before any namespace/ledger/transport access. Any mismatch → HOLD.
7. **Calendar proof re-derivation.** In the verified environment, re-derive
   the closed-session expectation for 2026-07-03 from the real XNYS
   mechanism: the date must resolve exchange-closed, matching the pinned
   calendar-proof record (digest `36bc3a89…`) bound in the supplement for
   REQ-SPT-07 / REQ-SPT-08 (both `expected_bars = 0`). Mismatch →
   classification stays disabled and any closed-shaped response HOLDs.
8. **Clean namespace, zero prior attempts, sole owner.** The output
   namespace for this run id is new and empty (or contains only this run's
   own durable state from an interrupted attempt of THIS run), the owner
   lock is acquirable by exactly one process, and no request shows a prior
   attempt. The old SPOT8 state directory is not read into, copied, or
   written by this run; its bytes remain preserved untouched (the
   integration suite re-verified them byte-identical, I02).
9. **Credential / proxy boundary.** The credential is referenced only as
   Secure Vault `custom.twelvedata`; the key material is never read by the
   entrypoint, never written to disk/argv/logs/events/exceptions, and is
   attached only at call time by the platform surrogate helper
   (`url_with_surrogate_query_param`, allowed_hosts pinned to
   `api.twelvedata.com`). Absent/failed surrogate path → fail closed
   (`CREDENTIAL_HELPER_UNAVAILABLE`), no direct fallback. The transport
   must be constructed **armed** only inside the adjudicated live process;
   the disarmed candidate refuses `TRANSPORT_NOT_ARMED` (I18).
10. **Adapter contract.** Only the V2-bound adapter contract
    (`ec877a04…`) is used, as implemented by the bound transport design:
    callable `(req) -> (status, body)`, GET, fixed parameter order
    (`build_url`), one attempt, no retries, HTTPS with certificate
    verification, response cap, sanitized exceptions, no adapter logging.
    The closed-response contract is the real vendor schema: HTTP 400,
    keys exactly `{code, message, status, meta}`, `meta` exactly
    `{symbol, interval, exchange: ""}`, no `values` (I03).
11. **Stop rules armed.** First HTTP error, identity/venue mismatch, hash
    or budget breach, or unknown-credit outcome stops the batch at that
    request; all later requests remain NOT ATTEMPTED. Raw/error/closed
    evidence is preserved write-once. A STARTED request without durable
    completion after any crash is AMBIGUOUS and is never redispatched.
12. **Retention limits acknowledged.** TD bytes are private screen evidence
    only, retained only while permitted (see -03 memo §6): no claim of
    indefinite retention, no redistribution, no dataset-scale adoption.
    Storage stays private, write-once, and hash-pinned for the permitted
    screen-evidence scope.

After the run: results are reported and adjudicated before any further
step. The screen opens no backtest, performance, or dataset work.
