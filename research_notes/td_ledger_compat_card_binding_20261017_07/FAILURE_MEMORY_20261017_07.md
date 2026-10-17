# Failure memory — QF-TD-LEDGER-COMPAT-AND-CARD-BINDING-20261017-07

Searchable entries for two failure classes found by the -06 live-evidence
pass and independently verified in Issue #1 comment 6230110894. Recorded
so neither recurs silently.

## TOKEN_CARD_WINDOW_DRIFT

- **What:** A token-request card assembled by copying fields out of a
  frozen evidence object carried dispatch-window epochs stale by exactly
  1,200 s (card `1792212067..1792233667` vs frozen
  `1792213267..1792234867`), while its human-readable ISO labels matched
  the frozen values. The card's claim to carry "the exact
  `make_dispatch_token` inputs bound to the frozen bytes" was false; the
  card was rejected independently of every other gate.
- **Root cause:** hand-copied fields; no derivation, no binding check.
- **Cure (this package):** the canonical card is DERIVED from the frozen
  bytes — every field is read from the same bytes, ISO labels are
  computed from the epochs they label, and verification regenerates the
  card and demands exact equality. Any copied/stale/mutated field HOLDs
  (`token_card.py`; suite C01–C05, incl. the exact 1,200 s drift as a
  reproduced test case against the preserved -06 fixture
  `bcda33d7…`).
- **Rule:** never copy a bound field. Derive it from the canonical bytes
  and re-derive on verification.

## LEDGER_SCHEMA_GENERATION_MISMATCH

- **What:** The shared pilot credit ledger is valid data in the legacy
  `rate_limiter.py` v3 schema (`{"day","spent","window"}`), but the r2
  dispatch gate and the integrated live driver consume a reservations
  schema (`{"reservations":[{"rid","ts","day","weight"}]}`), so gate 4
  read it as `LEDGER_CORRUPT_OR_UNREADABLE`. Not corruption — two schema
  generations, never migrated.
- **Cure (this package):** a separate-output, dry-run-only compatibility
  converter (`ledger_compat.py`): the source ledger is preserved
  byte-identical; the emitted candidate preserves or conservatively
  overcounts both the current-UTC-day spent total and the active
  rolling-60-second weight, and fails closed on malformed / future /
  duplicate / negative / ambiguous source states. Suite L01–L15.
- **Rule:** a schema mismatch is a migration task with a conservation
  proof, never an in-place rewrite and never a silent reset. A corrupt-
  reading gate is correct behavior until the migration is adjudicated.
