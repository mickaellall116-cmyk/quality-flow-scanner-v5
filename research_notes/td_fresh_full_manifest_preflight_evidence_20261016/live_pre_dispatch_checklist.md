# Future live pre-dispatch checklist — TD fresh full-manifest run

Run identity: `TD-FRESH-FM-20261016-03-R1` · Manifest: `TD-ACQUISITION-MANIFEST-V2-FRESH-20261016`
Canonical digest / file sha256: `71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db`
Fresh supplement sha256: `3cbdbf63fd49b021dc74f63727098551753949f8684967981c65f66101f95a86`

Every gate must pass in the live process **before transport is constructed**.
Any unknown, missing, expired, or insufficient item → **HOLD before any request**.
No gate may be waived by the operator of the run.

1. **Adjudicated execution packet.** A separate execution packet, adjudicated
   after this preflight (`FRESH_FULL_MANIFEST_PREFLIGHT_PASS`), names this run
   id, the manifest digest above, the supplement hash above, the state
   directory, the adapter/driver pins, the exact 51-credit ceiling, and the
   dispatch window. Without it, no dispatch.
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
   8/min cap. Live account/credit state was UNKNOWN at preflight time and
   must fail closed: unknown or insufficient → HOLD.
4. **Shared limiter state.** Read the shared persisted limiter ledger
   (`RollingCreditLimiter(8, 800)`, module sha256 `06ad383d…`) immediately
   before dispatch. Ledger corrupt or unreadable → HOLD (never reset it).
   The day's prior reservations count against the same 800/day cap.
5. **Environment reproduction.** The NL environment of record (rebuild commit
   `0923db7`, `NL_ENV_REBUILD_PASS`) is present: CPython 3.12.3,
   `pip freeze` byte-equal to lock `08b38cfa…` (11 packages), all wheel
   hashes equal to the qualified records, `pandas_market_calendars` ==
   4.5.1, mechanism `validate_input.py` sha256 `1b83cdcd…`. Any drift,
   absence, or version mismatch → HOLD; it also disables closed-session
   classification (fail-closed).
6. **Manifest / supplement / source hashes.** Recompute immediately before
   dispatch: fresh manifest file sha256 == canonical digest ==
   `71aade8b…`; supplement sha256 == `3cbdbf63…`; collector commit
   `ab254c3…` / bytes `b683d277…`; adapter contract `ec877a04…`; pinned
   prerequisites `038ccaf3…` confirmed still current. Any mismatch → HOLD.
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
   written by this run; its bytes remain preserved untouched.
9. **Credential / proxy boundary.** The API key comes only from Secure
   Vault `custom.twelvedata` inside the live driver, is held in memory
   only, is never written to disk/argv/logs/events/exceptions, and is sent
   last as `apikey`. Vault-surrogate requests use the sanctioned proxy
   substitution path only; absent/malformed proxy or failed CONNECT →
   fail closed, no direct fallback.
10. **Adapter contract.** Only the V2-bound adapter contract
    (`ec877a04…`) is used: callable `(req) -> (status, body)`, GET, fixed
    parameter order, one attempt, no retries, HTTPS with certificate
    verification, response cap, sanitized exceptions, no adapter logging.
11. **Stop rules armed.** First HTTP error, identity/venue mismatch, hash
    or budget breach, or unknown-credit outcome stops the batch at that
    request; all later requests remain NOT ATTEMPTED. Raw/error/closed
    evidence is preserved write-once. A STARTED request without durable
    completion after any crash is AMBIGUOUS and is never redispatched.
12. **Retention limits acknowledged.** TD bytes are private screen evidence
    only, retained only while permitted (see memo §6): no claim of
    indefinite retention, no redistribution, no dataset-scale adoption.
    Storage stays private, write-once, and hash-pinned for the permitted
    screen-evidence scope.

After the run: results are reported and adjudicated before any further
step. The screen opens no backtest, performance, or dataset work.
