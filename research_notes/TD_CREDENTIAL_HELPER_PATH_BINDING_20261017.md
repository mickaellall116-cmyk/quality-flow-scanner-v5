# TD credential-helper path binding (-08 r1) — memo

Task: QF-TD-CREDENTIAL-HELPER-PATH-BINDING-20261017-08 r1 (Issue #1 comment 6230977909).
Bases: a82d720 (dispatch gate r2), 2f312a1 (ledger compat + card binding), Stage-0 source.
Mode: offline, network denied (`unshare -n`) for probe and both matrix runs.
Elapsed: ~16 min of the ≤25 cap; one repair used (~6 min of the ≤8 allowance);
failed attempts preserved (attempt 0: 37/40 — matrices `dispatch_matrix_attempt0_failed.json`;
attempt 1: 39/40 — `dispatch_matrix_attempt1_failed.json`; trial trees kept alongside).

## Verdict

`CREDENTIAL_HELPER_PATH_BINDING_TARGETED_PASS_OFFLINE` (targeted offline PASS only).
The sanctioned path is PRESENT and surface-valid — the -06 conclusion is corrected
(see below). This accepts no live execution: TD live remains HOLD on fresh account
evidence (gate 3) and separately adjudicated ledger-candidate adoption, unchanged.

## Step 1 — probe of the sanctioned path (read-only; helper never invoked)

Full record: `td_credential_helper_path_binding_20261017_08/probe_record.json`.

- Sanctioned directory `/opt/hatch/skills/skill-creator/bin` EXISTS; the module
  `dynamic_credentials.py` EXISTS there (7,675 bytes), resolved absolute path
  `/opt/hatch/skills/skill-creator/bin/dynamic_credentials.py`, SHA-256
  `8b1f42e80a76710edf0ff2abf8a51b0cde35b06474af865de108a7ca27d6728d`.
- Surface classification: **SURFACE_PASS** — import-for-inspection succeeds offline;
  `url_with_surrogate_query_param` present and callable with signature
  `(url: str, credential_name: str, *, entry_name: str = 'access_token', allowed_hosts: Iterable[str]) -> str`;
  the allowed-host binding is enforced inside the helper via `ensure_allowed_url`.
- The precise restatement of the -06 fact: the helper is **absent from the default
  `sys.path`** (`ModuleNotFoundError` re-verified today) — it was never absent from
  the sanctioned platform path. The r2 gate and the -04 driver both imported by
  name from the default path only; the Stage-0 runner added the sanctioned
  directory explicitly and completed two HTTP-200 requests. Integration regression,
  now bound (below).
- A second byte-identical copy exists at
  `/opt/hatch/workflow-skills/custom-connector-setup/bin/dynamic_credentials.py`
  (same SHA-256). It is NOT the sanctioned origin and the binding never uses it;
  trial P03 proves a relocation to it without a seam pin is refused.

## Step 2–3 — the shared resolver + gate/driver binding

`credential_resolver.py` is the single resolution route. It loads the helper ONLY
from an exact file path (default: the sanctioned path) via
`spec_from_file_location` under a private module name — it never consults
`sys.path`, never prepends a working directory, and never accepts a same-named
module from elsewhere. Resolution = verify file exists
(`CREDENTIAL_HELPER_PATH_ABSENT`) → SHA-256 == pin (`CREDENTIAL_HELPER_TAMPERED`)
→ import that exact file (`CREDENTIAL_HELPER_UNAVAILABLE` on import error) →
module origin == exact path (`CREDENTIAL_HELPER_ORIGIN_MISMATCH`) → callable
present/callable (`CREDENTIAL_HELPER_CALLABLE_MISSING`) → signature carries the
allowed-host binding (`CREDENTIAL_HELPER_BINDING_MISMATCH`, same rule as r2).
The returned `VerifiedHelper` handle is never invoked by the resolver and carries
no credential material; `handle.reverify()` re-hashes the file
(`CREDENTIAL_HELPER_SWAPPED_POST_GATE`).

- Gate candidate `dispatch_gate_r3.py` (copy of the r2 gate; r2 package untouched):
  gate 9 resolves through the resolver (live route = sanctioned path + pinned
  hash; the r2 module-object seam is removed — the test seam is now exact
  `helper_path` + `helper_sha256` relocated together, and a path relocation
  without its seam pin refuses `CREDENTIAL_HELPER_ORIGIN_MISMATCH`;
  `paths_override` remains refused wholesale in live mode). After the lease is
  acquired and before the receipt is written, the gate re-verifies the handle
  (post-gate swap amends gate 9 to FAIL) and, on the arming path only, checks
  the handoff slot: a foreign module already occupying the `dynamic_credentials`
  import name refuses `CREDENTIAL_HELPER_SHADOW_INSTALLED`. On PASS it installs
  the verified module under that name, so the pinned -04 driver's by-name import
  can only land on the verified origin (the driver file itself is unchanged —
  its pin 5fed4524… stands).
- Driver candidate `live_driver_r3.py` (copy of the -04 driver; -04 untouched):
  `LiveHttpsTransport(armed=True, helper_handle=...)` consumes ONLY the
  gate-verified handle — no by-name import exists in the candidate — refuses
  `CREDENTIAL_HELPER_UNAVAILABLE` without a handle and re-verifies the handle
  before use. Adoption of either candidate is a separate decision, as in -04/-05.

## Step 4–5 — negatives + matrix (twice, network denied, byte-identical)

Suite: `run_dispatch_gate_trials_r3.py` — the full r2 matrix (32 trials) adapted
to the path seam, with H05's premise corrected, plus targeted cases P01–P08.
**40/40 trials, 293/293 checks, twice under `unshare -n`, matrices byte-identical**
(sha256 `cc54d6deed809f043d87da64fe1ff6c2e1ddecfb924ecf628d07beca2333fc4b`).
Real pilot ledger and old SPOT8 state unchanged (matrix safety flags true);
helper invocation count zero everywhere (no `calls.jsonl` was ever written).

- H05 (corrected): no seam override → gate resolves the REAL sanctioned path →
  all 12 gates PASS (dry-run), origin == sanctioned path, hash == pin.
- P01 absent sanctioned path → HOLD `CREDENTIAL_HELPER_PATH_ABSENT`, zero effects.
- P02 shadow module planted first on `sys.path` → never imported (import marker
  absent); gates pass via the sanctioned origin.
- P03 wrong origin (byte-identical copy, no seam pin) → HOLD
  `CREDENTIAL_HELPER_ORIGIN_MISMATCH`.
- P04 signature mismatch (callable without positional credential parameter) →
  HOLD `CREDENTIAL_HELPER_BINDING_MISMATCH`. (Non-callable/absent callable remain
  covered by H02/H03 → `CREDENTIAL_HELPER_CALLABLE_MISSING`; import failure by
  H01 → `CREDENTIAL_HELPER_UNAVAILABLE`.)
- P05 post-gate swap (seam file rewrites itself at import, after the hash check)
  → pre-arm reverify HOLDs `CREDENTIAL_HELPER_SWAPPED_POST_GATE`, factory never
  called, lease released.
- P06 tampered bytes vs pin → HOLD `CREDENTIAL_HELPER_TAMPERED`.
- P07 driver handoff: no handle → refusal even with a same-named module
  installed (no fallback import; marker callable unused); handle identity
  verified; post-issuance tamper → pre-call reverify refusal.
- P08 foreign module occupying the import name at the arming instant → HOLD
  `CREDENTIAL_HELPER_SHADOW_INSTALLED` before construction.
- Every negative HOLDs before armed construction / reservation / namespace /
  shared-ledger effects (asserted per trial: no transport, ledger byte-identical,
  namespace not created, no lease acquired or lease released).

Repair record (the one allowed repair, ~6 min): attempt 0 failed 3 trials, all
defects in the new -08 harness/candidate glue, none in the pinned bases —
(1) the handoff-slot shadow check also fired on dry-runs, where no driver import
can occur (fixed: arming path only); (2) the adapted runner's default seam pin
silently merged into the P03 no-pin case (fixed: explicit NO_PIN sentinel);
(3) two whitespace/paren defects in the generated holder/contender copies
(fixed). Attempt 1 (39/40) failed only C01 on the last holder indentation defect;
fixed and re-run fresh, twice.

## What remains live-only (stated plainly)

- The helper's presence in the LIVE execution process is now verified as a
  surface at the sanctioned path from this sandbox; an actual live dispatch
  still runs only under a separately adjudicated execution task with its own
  token — none was issued or used here.
- Gate 3 (fresh, timestamped account evidence) remains open and untouched;
  the ledger-compat candidate (-07) remains unadopted at the live shared path.
- The r3 gate / r3 driver are candidates: not merged, not adopted; the pinned
  r2 gate and -04 driver remain the operative bases until adjudicated otherwise.

## Scope confirmation

Offline throughout; zero credential material resolved/read/logged/printed (the
helper was imported for inspection only, its callable invoked zero times);
zero account/vendor/model/API calls beyond the spec fetch; zero installs,
downloads, spend, ledger writes (real ledgers hash-read only), token issuance,
time-series calls, backtest/performance, holdout, production/trading, Issue #9,
merge/adoption, PARKED reuse. All prior packages byte-identical (git status clean
for the r2, -04, -06, -07 package paths). Deliverables uncommitted.
