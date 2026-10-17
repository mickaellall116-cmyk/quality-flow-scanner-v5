# Live Dispatch Checklist — r2 Addendum (2026-10-16)

Addendum to `LIVE_DISPATCH_CHECKLIST.md` in
`td_fresh_full_manifest_preflight_evidence_20261016/` (that file is
unchanged). It records only the two steps whose mechanics changed
under `QF-TD-FRESH-LIVE-DISPATCH-GATE-20261016-05` r2; every other
checklist gate, cap and stop rule stands as written there.

## Amended step — gate 8 (sole ownership), lease-first ordering

The executor does not merely *evaluate* sole ownership. With all 12
gates green, the wrapper first acquires the nonblocking owner lease
for the exact namespace identity
(`<namespace-abspath>.dispatch_lease`, binding: run id + manifest
digest + evidence digest + namespace path), re-probes the namespace
invariant while holding it, and only then writes the PASS receipt
and constructs any transport. The lease stays held until the runner
has closed.

Operator checks at execution time:

- A `HOLD` receipt whose gate 8 reads `OWNER_LEASE_HELD` means
  another live process owns this run identity: do not retry, do not
  delete the lease artifact, and do not start a second flow — find
  the owner first.
- `OWNER_LEASE_BINDING_MISMATCH` means a lease artifact exists for a
  different identity than this dispatch: stop; that is foreign state,
  not contention.
- The lease artifact remaining on disk after a run is expected; its
  presence alone is not a lock. Ownership is the held flock, which
  the OS releases if the owner process dies.

## Amended step — gate 9 (credential boundary), helper preflight

Before PASS, the wrapper imports `dynamic_credentials` in the
execution process and verifies `url_with_surrogate_query_param` is
present, callable, and carries the allowed-host binding — without
invoking it and without reading any credential material.

Operator checks at execution time:

- `CREDENTIAL_HELPER_UNAVAILABLE` in the live process means the
  platform helper is not importable there. This is **live-process
  state, not an offline defect**: the offline proof covers the gate
  logic plus a stubbed surface; the real helper can only be confirmed
  in the process that will execute the screen. Stop and surface it —
  do not substitute another credential route.
- `CREDENTIAL_HELPER_CALLABLE_MISSING` /
  `CREDENTIAL_HELPER_BINDING_MISMATCH` mean the injected module is
  not the expected helper surface: stop; never adapt the gate to a
  different helper.
