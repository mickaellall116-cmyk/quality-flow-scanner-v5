# Yahoo publish-snapshot design — QF-YAHOO-PUBLISH-SNAPSHOT-DESIGN-20261015-10 r1

**Verdict: `SNAPSHOT_DESIGN_READY`** (design only; authorizes nothing)

Spec: GitHub Issue #1 comment `6200869297` (ChatGPT final adjudication of the
executor r2 amendment `530b120`). This packet is a **replacement architecture**,
not a patch. The parked executor (`execute_capture.py`, amended bytes sha256
`8fe97abd…`; verdict `CAPTURE_EXECUTOR_PREFLIGHT_HOLD_PARK`; final repair
allowance consumed; no r3) is **not edited, extended, or fixture-run** by this
task. Any implementation is a future, separately adjudicated task against
this design.

Scope of this task: design only, offline/read-only. Zero Yahoo/vendor/API/
model calls, zero sockets, zero downloads (spec-comment fetch excepted), zero
installs, zero spend, zero repository publication, zero backtests, zero
holdout access, zero production/live-state changes. ~14 minutes of the
≤30-minute budget.

---

## 1. Problem statement (the two adjudicated bypasses)

The parked publisher fails two load-bearing invariants:

- **B-1 — frozen-entry binding is caller-bypassable.**
  `publish_capture(..., entries=None)` accepts a caller-supplied `entries`
  and only loads/verifies the frozen capture manifest when the argument is
  omitted. A caller can publish a different 52-entry object set while the
  archive manifest merely carries the expected frozen-manifest hash.
- **B-2 — validation and upload do not bind the same bytes.**
  `validate_complete_archive()` hashes path contents and returns only a
  `path → hash` map. After three remote calls, `publish_capture()` re-opens
  each mutable path and uploads whatever bytes are then present; its
  re-fetch comparison is against the hash of those later-read bytes, not
  against the validated `SHA256SUMS`. A mutation between validation and
  read therefore publishes bytes that disagree with the pinned
  sums/manifest while still returning `PUBLISHED_FAKE`.

The design below makes both bypasses **structurally impossible**, not merely
unlikely: after bundle construction there is no code path that reads payload
bytes from the filesystem, and no parameter through which a caller can
influence the object set.

## 2. Architecture: one immutable snapshot bundle

### 2.1 Components

| Component | Role |
|---|---|
| `FrozenManifest` | Loaded **internally** from the pinned `capture_manifest.json` (schema `qf.yahoo_clean_capture.manifest/1`, sha256 `634c4541…`). Hash-verified against a constant compiled into the publisher at task time (as `EXPECTED_MANIFEST_SHA256` is today), schema-checked, order-verified. The **only** source of entries. |
| `SnapshotBuilder` | Reads the completed local archive **once**, under the drift discipline of §4, and produces a `SnapshotBundle`. |
| `SnapshotBundle` | Immutable in-memory object: the exact 158 payloads (156 objects + `SHA256SUMS` + `manifest.json`), each as pinned `bytes`, plus its own digest index. The sole input to upload. |
| `Uploader` | Sends bundle bytes only. Has no filesystem access to payload paths (see §2.4). |
| `RefetchVerifier` | Fetches every remote object and compares against the **bundle's pinned hashes** — never against hashes of any later local read. |
| `PublicationJournal` | Append-only local record of the publication attempt (states per object, remote head SHAs, final verdict). Evidence, never an input to decisions about payload bytes. |

### 2.2 Entry derivation — no caller control

- The publisher's public entry point has the signature
  `publish(cap_dir, capture_id, remote)`. There is **no** `entries`,
  `expected_repo`, paths-list, or options parameter that can alter the
  object set, its order, or the target. The target repo is a compiled-in
  constant (`mickaellall116-cmyk/qf-data-archive`), cross-checked against
  `remote.full_name()` and `remote.visibility() == "private"` before any
  upload (retained from the parked design).
- Entries are derived exclusively by `FrozenManifest`:
  `request_order` sorted by `i`, `i` sequence exactly `1..52`, symbols
  unique, count equal to `call_budget.max_requests_total` (52). Any
  deviation → `HOLD:ORDER_DRIFT` / `HOLD:MANIFEST_DRIFT`, before any remote
  call.
- The expected object set is a pure function of those entries:
  for each symbol `S`: `raw/S.csv`, `actions/S.actions.csv`,
  `meta/S.request.json` → exactly **156 objects**, no more, no fewer.
- A design-level conformance test (T-01, §7) must demonstrate that the
  module exposes no other public path to upload: an API-surface audit
  (introspect the module: exactly one publish entry point, no mutable
  module-level object-set state) is part of the required evidence.

### 2.3 Bundle construction and invariants

Construction happens in one pass, in this order:

1. **Pre-checks (no payload reads):** `INCOMPLETE_HOLD.json` absent;
   capture-id matches; frozen manifest verified (§2.2).
2. **Membership census:** walk `cap_dir` exactly as the parked
   `verify_object_set` does. The on-disk set must equal the 156 expected
   object rels plus the allowed top-level set
   {`attempt_journal.jsonl`, `file_ledger.jsonl`, `SHA256SUMS`,
   `manifest.json`}. Any extra, missing, or temp file → `HOLD:OBJECT_SET`.
3. **Single-read load:** for each of the 158 payloads (156 objects in frozen
   sorted order, then `SHA256SUMS`, then `manifest.json`), read the file
   **once** into memory under the drift discipline of §4 (open by handle,
   `fstat` before/after, hash the exact bytes read). The bytes read are the
   bytes kept; they are never re-read.
4. **In-bundle validation (against memory, not disk):**
   - sha256 of each in-bundle object must equal the corresponding line of
     the in-bundle `SHA256SUMS` (strict parse: exactly 156 unique
     well-formed lines) → else `HOLD:SUMS_INVALID`.
   - In-bundle `manifest.json` must satisfy the parked strict checks
     (status `COMPLETE`, exact capture id, 52 symbols,
     `capture_manifest_sha256 == 634c4541…`, `files` mapping exactly equal
     to the sums) → else `HOLD:ARCHIVE_MANIFEST_INVALID`.
   - Each object's sha256 is recorded in the bundle's digest index:
     `rel → (sha256, length)`.
5. **Bundle digest:** one canonical digest over the index — sha256 of the
   concatenation, in rel-sorted order, of `f"{sha256}  {rel}\n"` for all
   158 payloads (i.e., the `SHA256SUMS` text extended with its own line and
   the `manifest.json` line, computed over in-bundle hashes). This
   `bundle_sha256` is the single value the publication journal, the
   re-fetch verifier, and any future adjudication bind to.
6. **Freeze:** the bundle is sealed. Payloads are stored as immutable
   `bytes` in a tuple-indexed mapping; no method mutates them. Construction
   of the remote prefix list, upload order, and verification expectations
   all read from the sealed bundle only.

**Invariants (must hold by construction, and be asserted in code):**

- I-1: `len(bundle) == 158`, rels exactly the frozen set ∪
  {`SHA256SUMS`, `manifest.json`}.
- I-2: for every rel, `sha256(bundle[rel]) == digest_index[rel]` — checked
  once at seal time and again **after upload completes, before
  verification** (cheap: ~30 MB), so even in-process corruption of the
  bundle is detected rather than published as truth.
- I-3: `bundle[SHA256SUMS]` parses to exactly the digest index restricted
  to the 156 objects.
- I-4: no payload byte reaches the uploader except via `bundle[rel]`.
- I-5: upload order is deterministic: rel-sorted, with `SHA256SUMS` and
  `manifest.json` uploaded **last** (a remote prefix containing both is
  therefore only ever observable after all 156 objects are present — see
  §6, partial-commit semantics).

### 2.4 Structural enforcement of I-4

- After `SnapshotBuilder` returns, the publish phase runs in a scope that
  receives only `(bundle, remote, journal)`. The implementation must not
  import or call filesystem payload reads in the upload/verify phase; a
  required static check (in the implementation's fixture suite, T-08)
  greps the publish-phase source for `open(`, `os.path`, `pathlib` payload
  access and fails if found outside the builder.
- The builder itself is the only component that receives `cap_dir`.

## 3. Upload protocol

Target: the private repo `mickaellall116-cmyk/qf-data-archive`, prefix
`captures/<capture_id>/` (retained from the accepted preflight design).

1. **Target gates (before any write):** `remote.full_name()` equals the
   compiled-in constant → else `HOLD:TARGET_NAME_DRIFT`;
   `remote.visibility() == "private"` → else `HOLD:VISIBILITY_REFUSAL`.
   These run **after** bundle construction (so the bundle digest is already
   pinned in the journal even if the run refuses here) — this ordering
   also removes the parked code's "three remote calls before upload"
   window from the byte path entirely: remote metadata calls may happen
   at any time, because no payload byte is ever re-read afterward.
2. **Prefix-conflict gate:** if the remote prefix `captures/<capture_id>/`
   exists in any form → `HOLD:CAPTURE_EXISTS`. Publication is
   **never retried into the same capture id** (see §5, retry prohibition).
   A previously partial publication (§6) therefore permanently occupies
   its capture id; a new publication requires a new capture id under a
   new adjudication.
3. **Upload:** for each rel in bundle order, `put_file(prefix/rel,
   bundle[rel])` — the exact pinned bytes. One attempt per object. Record
   per-object outcome and the remote head SHA after each put in the
   journal.
4. **Post-upload bundle re-assertion:** re-check I-2 over the in-memory
   bundle (detects any in-process mutation during upload) → mismatch is
   `HOLD:BUNDLE_MUTATED` and the remote prefix is treated as a partial
   (§6), never as published.
5. **Re-fetch verification (§4 of this design; protocol step 5):** for
   **every** one of the 158 rels, fetch the remote object and require
   `sha256(fetched) == digest_index[rel]` — the pinned hash from
   validation time. Any miss, absence, or mismatch →
   `HOLD:REFETCH_MISMATCH`, zero-trust (§6). Only 158/158 exact matches
   yield status `PUBLISHED` with the final remote head SHA recorded.
6. **No other success path exists.** In particular, upload acknowledgements,
   HTTP 2xx responses, or the remote's own reported digests are never
   substituted for step 5.

## 4. Local read discipline (closing the validate→upload TOCTOU at the root)

The bundle eliminates the TOCTOU between validation and upload. A narrower
window remains *inside* the builder's single read (a path swapped between
census and read, or during read). The design closes it as far as a local
filesystem permits, and — critically — makes any residual drift **harmless
to the published record**:

- Each payload is opened once; `os.fstat` is taken on the open handle
  before and after the read; `st_dev`, `st_ino`, `st_size`, and
  `st_mtime_ns` must be identical, and bytes read must equal `st_size` →
  else `HOLD:READ_DRIFT`, bundle discarded, nothing uploaded.
- Symlinks are refused outright: `os.lstat` on every path component of
  every payload (and of `cap_dir` itself) must show a regular file/dir,
  never a symlink → else `HOLD:PATH_TYPE_DRIFT`. `O_NOFOLLOW` is used
  where available.
- **Why residual risk is acceptable:** whatever bytes survive this single
  checked read are the bytes hashed into `SHA256SUMS` comparison, sealed,
  uploaded, and re-fetch-verified. If an attacker (or accident) swaps a
  file *before* the read, the in-bundle sums check (I-3) fails unless the
  swap also rewrites `SHA256SUMS` and `manifest.json` consistently — and
  both of those are themselves sealed in the bundle, digest-bound by
  `bundle_sha256`, and re-fetch-verified remotely. A fully consistent
  forged archive on local disk is outside this design's threat model
  (it is the capture phase's already-adjudicated problem, gated by the
  attempt journal and per-symbol hash bindings at acquisition time);
  §8 states this assumption explicitly.

## 5. Failure semantics (all fail-closed; no silent degradation)

| Condition | Code | Disposition |
|---|---|---|
| Frozen manifest hash/schema/order drift | `HOLD:MANIFEST_DRIFT` / `HOLD:ORDER_DRIFT` | Abort before census; no remote calls |
| Object set ≠ frozen 156 (+ allowed top-level) | `HOLD:OBJECT_SET` | Abort; no remote calls |
| Symlink / non-regular file / path-type drift | `HOLD:PATH_TYPE_DRIFT` | Abort; no remote calls |
| `fstat` drift during a read | `HOLD:READ_DRIFT` | Bundle discarded; no remote calls |
| Sums strict-parse or in-bundle hash mismatch | `HOLD:SUMS_INVALID` | Abort; no remote writes |
| Archive manifest strict-check failure | `HOLD:ARCHIVE_MANIFEST_INVALID` | Abort; no remote writes |
| `INCOMPLETE_HOLD.json` present | `HOLD:INCOMPLETE_MARKER` | Abort; no remote calls |
| Target name / visibility wrong | `HOLD:TARGET_NAME_DRIFT` / `HOLD:VISIBILITY_REFUSAL` | Abort; no remote writes |
| Remote prefix already exists (in whole or part) | `HOLD:CAPTURE_EXISTS` | Abort; **no top-up, no overwrite, no retry** |
| A `put_file` fails mid-upload (network, API, quota) | `HOLD:PARTIAL_UPLOAD` | Stop immediately at that object; prefix is a **partial** (§6); no retry |
| Bundle bytes change in memory during upload | `HOLD:BUNDLE_MUTATED` | Stop; prefix treated as partial |
| Re-fetch: any object missing or hash ≠ pinned | `HOLD:REFETCH_MISMATCH` | Zero-trust: the publication **did not happen** for all decision purposes; prefix treated as partial |
| Process crash / kill at any point | (no code; journal is the record) | On any later restart the prefix-exists gate fires (`HOLD:CAPTURE_EXISTS`) if anything was written, or the run is simply absent. Never resumed mid-prefix. |
| Ceiling breach (§6 of design: memory/bytes) | `HOLD:CEILING` | Abort before upload |

**Retry prohibition (absolute):** no automatic retry of any remote
operation within a run, and no re-run of publication under the same
capture id, ever. Recovery from any publication failure is a new capture
id under new adjudication — the same one-attempt discipline the capture
phase applies to vendor requests (`ATTEMPT_CONSUMED_AMBIGUOUS` analogue:
a capture id with any remote presence is consumed).

## 6. Partial-upload disposition

- A partial prefix (some objects under `captures/<capture_id>/`, no
  verified completion) is **evidence, not a dataset**: it is never read by
  any baseline, never "completed" by a later run, and never deleted by
  the publisher (deletion is Mike's explicit-approval domain, as pinned in
  the archive repo's storage procedure).
- Because `SHA256SUMS` and `manifest.json` upload **last** (I-5), a
  partial prefix never contains the two files that would make it look
  like a complete archive to a naive reader. A consumer-side rule is
  specified for any future reader: a prefix is a valid capture **iff**
  all 158 objects are present **and** every hash matches its
  `SHA256SUMS`/`manifest.json` — anything else is ignored.
- The publication journal (local, append-only, fsync'd per event as in
  the capture phase) records: `bundle_sha256`, per-object put outcomes,
  remote head SHAs, the failure code, and the final status line. The
  journal is the deterministic evidence an adjudicator uses to classify
  the partial.

## 7. Adversarial test designs (required of any future implementation)

All cases run against a fake local remote (as in the parked suites) plus a
mutation harness that can act on the local archive and on the fake remote
at defined points. Expected outcomes are exact; the suite must pass twice
with byte-identical result files (the desk's standing determinism rule).

| # | Case | Method | Required outcome |
|---|---|---|---|
| T-01 | **Injected entries** | Call the publish entry point with every plausible override (extra kwargs, monkeypatched module state, subclassed remote returning crafted data, env/CLI variation) | No API surface accepts an object set other than the frozen 52-derived 156+2; attempts raise/refuse; zero remote writes |
| T-02 | **Mutation between validation and remote calls** | Build the bundle, then modify/rename/delete files in `cap_dir` before and during upload | Uploaded and re-fetch-verified bytes are exactly the bundle bytes (`bundle_sha256` unchanged); local mutation has zero effect on the remote content |
| T-03 | **Post-bundle local mutation (aggressive)** | After bundle construction, replace the entire `cap_dir` tree with a different, internally consistent capture | Remote still receives the original bundle; verdict computed solely from the bundle |
| T-04 | **Symlink / path replacement** | Replace a payload file with a symlink (to another archive file, to outside the tree, dangling), swap a directory for a symlink, race a swap during the read window | `HOLD:PATH_TYPE_DRIFT` or `HOLD:READ_DRIFT`; zero remote writes |
| T-05 | **Remote byte substitution** | Fake remote alters stored bytes after `put_file` (bit-flip, truncation, substitution of another object's bytes, substitution of bytes from a *different valid capture*) | Re-fetch verification fails with `HOLD:REFETCH_MISMATCH`; no `PUBLISHED` status; journal shows the exact rel |
| T-06 | **Partial commit** | Fake remote fails the Nth put (for N ∈ {1, 2, 79, 157, 158}), drops a put silently (acknowledges but stores nothing), or the process is killed mid-upload | `HOLD:PARTIAL_UPLOAD` / prefix-exists on any subsequent attempt; `SHA256SUMS`+`manifest.json` absent from every partial that failed before their turn; no retry, no top-up |
| T-07 | **Existing-prefix conflict** | Pre-populate the remote prefix with (a) a full older capture, (b) a one-file stub, (c) a prefix differing only by capture-id case | All → `HOLD:CAPTURE_EXISTS` before any write; remote bytes unchanged |
| T-08 | **Publish-phase filesystem access** | Static source audit + runtime guard (filesystem-open trap armed during upload/verify that raises on any payload-path open) | Zero payload opens after bundle seal; audit grep clean outside the builder |
| T-09 | **Duplicate / extra / missing objects (local)** | Add a duplicate-named file (case variant), an extra file in a subdir, a temp file, remove one object, add a 53rd symbol's files | All → `HOLD:OBJECT_SET` (or sums/manifest HOLD) before any remote write |
| T-10 | **Wrong target / public visibility** | Fake remote reports a different `full_name`, or `visibility() != "private"` (public, internal, unknown string) | `HOLD:TARGET_NAME_DRIFT` / `HOLD:VISIBILITY_REFUSAL`; zero writes. (Carried over from the parked suite.) |
| T-11 | **In-bundle corruption during upload** | Test harness mutates one sealed payload byte between puts (via a deliberately exposed test hook that production code lacks) | Post-upload re-assertion (I-2) fires `HOLD:BUNDLE_MUTATED`, or re-fetch comparison against the *original* pinned digest fails — never `PUBLISHED` |
| T-12 | **Crash and restart** | Kill the process after k puts (k ∈ {0, 1, 50, 157}); restart publication with the same capture id; restart with a new capture id | Same id → `HOLD:CAPTURE_EXISTS` (or clean pre-write refusal if k=0 and prefix truly absent); new id publishes independently; no state confusion in journals |
| T-13 | **Ceiling enforcement** | Synthetic archive whose total bytes exceed the §8 ceiling, and one oversized single object | `HOLD:CEILING` before upload; memory ceiling (§8) never exceeded (measured peak RSS in the fixture) |
| T-14 | **Determinism** | Run the full suite twice from identical fixtures | Byte-identical result files; bundle digests identical across runs |

Retained-from-prior-suites note: the parked executor's 32/32 r2 cases and
15/15 amendment cases remain the regression floor for manifest binding,
object-set strictness, sums/manifest strictness, target/visibility gates,
and capture-phase behavior; this design changes only the publication
architecture, and a future implementation suite must include those cases
unchanged alongside T-01…T-14.

## 8. Memory / byte ceilings and bounded-bundle evidence

- Payload volume is bounded by the frozen manifest's own ceilings:
  per-symbol ≤ 20,000 rows / ≤ 32 MiB per raw file, total capture
  ≤ 512 MiB hard ceiling (manifest `call_budget.ceilings`), with an
  **expected** total of ~20–30 MB (~282k rows).
- The bundle is therefore capped by design rule, not by hope: the builder
  enforces a **bundle byte ceiling of 64 MiB** total payload (156 objects
  + sums + manifest) — comfortably above the ~30 MB expectation, far below
  the 512 MiB capture ceiling — and `HOLD:CEILING` above it. A single
  object cap of 32 MiB (the manifest's per-symbol byte ceiling) also
  applies at read time, checked against `fstat` size **before** reading.
- Peak memory is ~2× bundle size (payload bytes + fetched copies during
  verification, if verification is run naively); the design specifies
  re-fetch verification **streams per object** (fetch one, hash, discard),
  so peak is ~1× bundle + one object ≈ ≤ 96 MiB worst case — trivially
  safe on this VM, and the fixture (T-13) must record measured peak RSS
  as the deterministic evidence.
- Deterministic evidence package required from any implementation:
  fixture results (twice, byte-identical), per-case journal excerpts,
  `bundle_sha256` for the fixture capture, measured peak RSS, and the
  API-surface audit output for T-01/T-08.

## 9. Assumptions and unresolved limits (stated, not hidden)

- **A-1 (GitHub API atomicity):** the Contents API offers no multi-object
  transaction. A "publication" is 158 separate puts; atomicity is
  achieved *semantically*, not by the API: last-uploaded sums/manifest
  (I-5), the consumer-side validity rule (§6), and the prefix-exists
  prohibition together ensure a partial is never mistaken for or grown
  into a complete capture. A reader that ignores §6's rule is outside
  this design's guarantees.
- **A-2 (re-fetch trust):** re-fetch verification trusts that the remote's
  GET returns the stored bytes at verification time. It proves
  remote-content-equals-bundle at that instant; it cannot prove the
  remote will not change later. The archive repo's append-only procedure
  (checksums also referenced from the scanner repo's research notes) is
  the standing tripwire, as designated by Mike 2026-10-15.
- **A-3 (local forgery):** a fully self-consistent forged local archive
  (objects + sums + manifest + journal all rewritten together) is not
  detectable by the publisher alone (§4). Mitigation lives in the capture
  phase (per-symbol acquisition bindings, attempt journal) and in
  adjudication-time spot checks against `bundle_sha256`.
- **A-4 (transport):** the design is transport-agnostic (any `remote`
  object with `full_name/visibility/has_prefix/put_file/get_file/head_sha`
  semantics). Proving the *real* GitHub transport behaves per these
  semantics (pagination, encoding, size limits per Contents-API call —
  objects above the API's per-file limit would need Git Data API blobs)
  is implementation-task work; the largest expected object (~a few MB
  for 20k-row CSVs) is within historical Contents-API limits, but this
  design does not assert it as proven.
- **A-5 (single publisher):** one publication process per capture id is
  assumed; the prefix-exists gate is check-then-act at the remote and a
  simultaneous second publisher is out of scope (no second publisher
  exists in this program).

## 10. Stop rules

- This design, if accepted, authorizes **no** implementation, capture,
  Yahoo call, or publication. Implementation requires its own adjudicated
  task with its own budget and repair allowance.
- If any element above cannot be implemented as specified (in particular
  the structural I-4 enforcement or the T-08 runtime guard), the
  implementation task must return `HOLD` rather than weaken the design.
- The parked executor stays parked: it is not to be revived as the
  implementation base without explicit adjudication, since its publish
  path embodies B-1/B-2.

— Muse (design only; no code changed, no fixture run, no network beyond
the spec fetch)
