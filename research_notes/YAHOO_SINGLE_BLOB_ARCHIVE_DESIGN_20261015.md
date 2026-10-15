# Yahoo Single-Blob Archive — Design

- Task: `QF-YAHOO-SINGLE-BLOB-ARCHIVE-DESIGN-20261015-12 r1` (spec: GitHub Issue #1 comment `6203735721`).
- Scope: **DESIGN ONLY.** No implementation, no edits to the parked -11 publisher (`d703a85`) or the parked executor, no fixture runs of new code, no authenticated GitHub operations, no Yahoo/vendor calls, no spend, no capture, no publication, no backtests. Sources: the adjudicated local evidence below + official public GitHub documentation (cited with access dates, §9).
- Predecessors: -10 snapshot design (`research_notes/YAHOO_PUBLISH_SNAPSHOT_DESIGN_20261015.md`, commit `28e2316`) — 158 Contents-API writes; its own §8 note concedes there is no multi-object transaction, so atomicity was "semantic only". -11 partial publisher (`research_notes/yahoo_publish_snapshot_preflight_20261015/`, commit `d703a85`) — `SNAPSHOT_IMPLEMENTATION_HOLD_PARK`: run 1 clean but twin/memo/manifest not produced inside the cap, and review found `_read_once()` re-checks only the leaf path, so an **intermediate-directory symlink swap** between census and read is not closed by leaf-level `O_NOFOLLOW`.
- This design replaces the 158 independent writes with **one deterministic, content-addressed archive blob**, made visible by **one** fast-forward-only ref update whose new commit's sole parent is the pinned expected parent. It also closes `CEILING_PARITY_REQUIRED` by construction (§4) and the component-swap race by fd-relative no-follow traversal (§3).

## Verdict: `SINGLE_BLOB_DESIGN_READY`

With two named gating probes for a future implementation preflight (U-1, U-2, §10) — they constrain implementation, not the design. No Yahoo attempt, capture, or publication is authorized by this memo.

---

## 1. Container format — QFAR1 (minimal length-prefixed)

Decision: a minimal length-prefixed container, not ZIP/TAR. ZIP freezes are possible but byte-determinism then depends on a specific writer profile (version-made-by, extra fields, external attributes, DOS timestamps, data descriptors, ZIP64 thresholds), and general-purpose tools extract rather than re-archive, so independent byte-reproduction is weak. TAR carries 512-byte block padding, pax extended headers, and checksum-field variants. QFAR1 accounts for **every byte** in the layout below; a conforming re-builder is a page of code in any language, and determinism is testable by construction (§6.5, A-01). The spec explicitly permits this branch.

Layout (all integers unsigned big-endian; no other fields exist):

| Section | Bytes | Content |
|---|---|---|
| Magic | 8 | ASCII `QFAR0001` |
| Version | 4 | u32 = 1 |
| Member count | 4 | u32 N — must equal **158** for this capture family |
| Index | N × (2 + L + 8 + 32) | per member, in index order: u16 rel byte length L (1..1024); L bytes rel (ASCII, grammar §2); u64 payload byte length; 32 bytes payload SHA-256 |
| Payloads | Σ payload lengths | the N original byte streams concatenated in index order, **exactly as captured**, no padding, no compression, no transformation |
| Trailer | 32 | SHA-256 over every preceding byte (magic through end of payload section) = `CONTAINER_SHA256` |

Determinism rules (a builder violating any one is non-conforming):

- D-1: Membership is the exact frozen set of 158 rels (§2), loaded from the frozen entry list — never from directory enumeration.
- D-2: Index order is ascending unsigned byte-wise sort of rel. (The frozen set sorted byte-wise is the canonical order; no locale, no filesystem order.)
- D-3: No timestamps, no randomness, no host/user/platform fields, no optional fields, no padding anywhere. Integers are fixed-width big-endian.
- D-4: Payloads are the captured bytes verbatim. Any re-serialization (line endings, encodings, CSV rewriting) is forbidden at this layer.
- D-5: Consequence: identical member byte sets ⇒ identical container bytes ⇒ identical `CONTAINER_SHA256` ⇒ identical Git blob id (§5). This is a theorem of the layout, and A-01 tests it empirically.

Binding: the Git blob id (§5) commits to the container bytes; `CONTAINER_SHA256` commits to header+index+payloads; each index entry commits to one member's length and SHA-256. The in-container `manifest.json` and `SHA256SUMS` members carry the same per-member hashes a second time; verification (§7) requires index, `manifest.json`, and `SHA256SUMS` to agree exactly — three encodings of the same fact, any disagreement is `HOLD:MEMBER_DRIFT`.

## 2. Membership, capture-ID grammar, path rules

- Membership (frozen, from -10 §2): 156 capture objects — `raw/<SYM>.csv`, `actions/<SYM>.actions.csv`, `meta/<SYM>.request.json` for the 52 frozen symbols — plus `manifest.json` plus `SHA256SUMS` = **158**. Local membership check is **exact set equality**: a missing member, an extra file anywhere under the capture dir, or a name outside the frozen set is `HOLD:MEMBERSHIP` before any read.
- Rel grammar (defense in depth; set equality is the gate): ASCII only; components drawn from `[a-z0-9._-]+`; no empty component, no `.` or `..` component, no leading/trailing `/`, no `\`, no NUL. Rels are used **only** as openat components (§3), never concatenated into shell or URL strings except the single repo path in §6, which is built from the validated capture ID, not from a rel.
- Capture-ID grammar (carried over from the parked publisher, unchanged): fullmatch `[A-Z0-9][A-Z0-9-]*[A-Z0-9]`, length 8..64, no `--`. The capture ID is an **instance ID assigned at separate authorization** (per the frozen capture manifest); it is consumed by a publication attempt per §6.4.

## 3. Read discipline — closing the intermediate-component swap

The -11 defect: census rejected a pre-existing directory symlink, but reads re-opened by path and `O_NOFOLLOW` guarded only the leaf, so swapping `raw/` for a symlink between census and read redirected the read. This design makes path-string re-resolution impossible:

- R-1: The capture root is opened **once**: `open(root, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)`. Its `(st_dev, st_ino)` from `fstat` is pinned. After this, no operation uses a path string for anything under the root.
- R-2 (preferred mechanism): every member is opened with Linux `openat2(root_fd, rel, {flags: O_RDONLY | O_NOFOLLOW, resolve: RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS})`. `RESOLVE_NO_SYMLINKS` applies to **every** component of the path, intermediate and leaf; `RESOLVE_BENEATH` forbids escape from the root tree. A swapped intermediate symlink therefore fails the open (`ELOOP`) — it cannot redirect.
- R-3 (portable fallback, where openat2 is unavailable): component-wise fd walk — for each component, `openat(cur_fd, comp, O_RDONLY | O_NOFOLLOW | (O_DIRECTORY if not leaf))`, starting from the pinned root fd, closing parent fds as the walk descends. Same guarantee: no-follow is set on **every** component open, so no component can be traversed through a symlink.
- R-4 (census binding, both mechanisms): census is itself taken via R-2/R-3 traversal (never a path-based walk) and records, for every directory and member: `(rel, st_dev, st_ino, st_size)`. Each read fd is `fstat`-checked against its census entry **before** reading (identity) and **after** reading (size/identity unchanged). Any mismatch — including a swap to a different *legitimate* directory, which openat2 alone permits if it is not a symlink — is `HOLD:READ_DRIFT` with zero uploads. This closes even the non-symlink directory-replacement variant.
- R-5: Reads consume the fd to EOF with the census size as the exact expected length; short/over-read is `HOLD:READ_DRIFT`. SHA-256 is computed incrementally during the read and must equal the validation-time pinned member hash before the member may enter the container.
- R-6 (seal): the container is written to a temp file opened relative to a pinned staging-directory fd (`openat` + `O_CREAT | O_EXCL | O_NOFOLLOW`), fsync'd, and the upload reads **from that same open fd** after an `lseek` to 0 — the sealed bytes are never re-opened by path. The §7 local pre-check re-reads from this fd.

## 4. One shared ceiling — `CEILING_PARITY` closed by construction

The -11 record (`ceiling_parity_record.json`, status `UNRESOLVED`, `ceilings_equal=false`): frozen capture total 536,870,912 (512 MiB), capture per-symbol 33,554,432 (32 MiB), publisher bundle 67,108,864 (64 MiB), publisher single-object 33,554,432. A capture legal under 512 MiB could be unpublishable after vendor calls were consumed.

Resolution — a single constant, one semantics, both sides:

- **`QF_SHARED_TOTAL_CEILING_BYTES = 67,108,864` (64 MiB)**, defined as: *the sum of the byte lengths of the 158 payloads*. The container's own length is then determined exactly: `Σ payloads + 12 + Σ(42 + len(rel_i)) + 32` (≤ Σ payloads + 13,068 for the frozen set).
- Capture side: a required **manifest revision (rev.3)** of the frozen capture manifest (current pin sha256 `634c4541…`, per the parity record) replaces the 512 MiB total ceiling with 67,108,864 and binds the same definition (sum of the 158 produced payload byte lengths, enforced on the running total during capture, fail-closed mid-capture before any byte beyond the ceiling is written). The 32 MiB per-symbol ceiling stays as a member-level guard; the 20,000-row ceiling is unchanged. **No Yahoo attempt may occur under the 512 MiB manifest** — rev.3 adoption is a precondition for any future capture authorization.
- Archive side: the builder refuses to seal if Σ payloads > 67,108,864 (`HOLD:CEILING`, pre-upload), and the publisher refuses to upload if the sealed container length ≠ the exact length implied by the index (format check, §1). There is no second ceiling number anywhere: the publisher's old 64 MiB bundle ceiling and the capture's new total ceiling are the same constant with the same definition, so parity cannot drift — a future change must edit one named constant mirrored in both manifests, and the implementation preflight diffs the two pins (A-10).
- Why 64 MiB is safe against documented platform limits: the Get-blob endpoint is documented to support blobs up to 100 MB, and GitHub blocks files larger than 100 MiB in regular repositories (§9). At the ceiling, the container is ≤ 67,121,932 bytes and its base64 transport form is ≤ 89,478,852 bytes — both under 100 MB even if an intermediary counts the encoded form. Expected real volume is ~20–30 MiB (the -08 estimate), so the ceiling carries 2–3× headroom, not a tight fit.
- Memory: -11 measured peak RSS 121.73 MiB for a 158-object in-memory bundle. This design forbids holding the container plus a second full copy: build streaming to the sealed temp fd (R-6), hash incrementally, base64-encode from the fd in bounded chunks. A numeric RSS gate belongs to the implementation preflight (baseline to beat: 121.73 MiB); it is a build constraint, not a byte ceiling, and is not conflated with one.

## 5. Object identity

- Git blob id = SHA-1 over `"blob " + <decimal length> + NUL + <container bytes>` (standard Git object identity; the designated repo uses SHA-1 object format — assumption A-S1, §10). The builder computes it locally before upload; §6 requires the create-blob response to return exactly this id.
- The container's own SHA-256 (§1) is the content address used by consumers and the public ledger (§7); the Git blob id is the transport cross-check. Both are pinned; either mismatch is a HOLD.

## 6. Publication protocol (Git Data API, one ref update)

Target: repo `mickaellall116-cmyk/qf-data-archive` (designated, private), branch ref `refs/heads/qf-archive`, repo path `captures/<capture_id>.qfar`. Only this publisher writes that branch.

1. **Intent + journal.** Before any remote call, append the fsync'd publication-intent record to the local publication journal: capture ID, `CONTAINER_SHA256`, blob id, member-hash pin set, capture-manifest pin (rev.3 sha256), expected parent `P` (below). From this moment the capture ID is **consumed** (§6.4).
2. **Visibility gate.** GET the repo; require `private == true` and exact owner/name match. Else `HOLD:VISIBILITY`, zero writes.
3. **Parent pin.** GET `refs/heads/qf-archive`.
   - If it exists, its commit is `P`; GET commit `P` and pin its tree `T_P`. If the branch already contains `captures/<capture_id>.qfar` in `T_P` → §6.4 restart reconciliation, never a fresh publication.
   - If it does not exist (first publication ever), `P = ∅`: the commit in step 6 is a root commit and step 7 uses ref **creation**.
   Any discrepancy between the journal's expected parent and the freshly read ref is `HOLD:PARENT_DRIFT` before any object is created.
4. **Create blob.** POST `/git/blobs` with `{content: base64(container), encoding: "base64"}`, the bytes read from the sealed fd (R-6). The returned `sha` must equal the locally computed blob id; else `HOLD:BLOB_SUBSTITUTION`.
5. **Create tree.** POST `/git/trees` with `{base_tree: T_P, tree: [{path: "captures/<capture_id>.qfar", mode: "100644", type: "blob", sha: <blob id>}]}` (omit `base_tree` when `P = ∅`). Documented semantics: entries in `tree` overwrite same-path entries of `base_tree`; all other parent entries carry over — prior captures remain untouched, append-only. Returned tree id is `T`.
6. **Create commit.** POST `/git/commits` with `{message: <frozen template: "QF archive <capture_id> <CONTAINER_SHA256>">, tree: T, parents: [P] (or []), author/committer: the frozen publisher identity; timestamp = execution time}`. Commit bytes are deliberately **not** required deterministic — determinism lives in the blob; the resulting commit id `C` is pinned in the journal and the ledger (§7).
7. **The single visibility event.** If `P` existed: PATCH `/git/refs/heads/qf-archive` with `{sha: C, force: false}`. If `P = ∅`: POST `/git/refs` with `{ref: "refs/heads/qf-archive", sha: C}`.
   **CAS-by-construction** (documented vs inference, §9): the REST update-reference body has exactly two parameters, `sha` and `force`; there is **no** expected-old-value field. With `force: false` the update must be a fast-forward — the docs' wording is that this makes sure you are "not overwriting work" — so the update succeeds only if the ref's *current* tip is an ancestor of `C`. `C`'s ancestry is exactly `{P} ∪ ancestors(P)`. Therefore a concurrent writer that advanced the ref to any commit other than `P` (or an ancestor) makes the update non-fast-forward and it is rejected (409/422) → `HOLD:REF_RACE`, and a rejected update changes nothing. Ref creation on an existing ref likewise fails rather than overwriting (422). What a consumer may trust is never the ref alone — §7 re-verifies from `C` downward and §8 requires the ref to still equal the ledger-pinned `C` at consumption time.
8. **Verify, then record.** §7 must pass in full. Only then is `PUBLISHED` written to the journal and the public ledger anchor committed (§7). A crash between step 7 and §7 leaves the capture *unanchored*, hence not valid for any consumer (§8).

### 6.4 Consumed-ID and restart discipline (carried over from -08/-11)

- A capture ID with a journal intent record is never published again. Restart reconciliation reads the ref: ref tip's tree contains our path with our blob id **and** §7 passes against the journal pins → the attempt is completed by recording (no new objects, no ref write). Ref at `P`, or path present with a different blob id, or §7 failing → `HOLD:ID_CONSUMED` / the specific §7 HOLD. No top-up, no republication, no second commit for the same ID, ever.
- Failure before step 7 leaves orphan blob/tree/commit objects. They are **unreachable and invisible**: no ref points at them, and consumers validate only through the ledger-pinned commit. They are retained-at-best evidence (GitHub may garbage-collect unreachable objects — retention is *not* guaranteed and the design never relies on it; the evidence of record is the local journal + post-§7 ledger). No cleanup is attempted.

## 6.5 Adversarial case set — required of the future implementation preflight

Each case names the attack, the required outcome. All run against a fake remote except A-10's parity diff (static) and U-1's probe (separately authorized, §10).

- **A-01 Byte determinism.** Build the container twice from two independently materialized copies of the same capture (different inode order, different mtimes, different filesystem), with directory enumeration deliberately permuted. Require: identical container bytes, identical `CONTAINER_SHA256`, identical blob id. (Order comes from the frozen index — D-2 — never from readdir.)
- **A-02 Intermediate-component swap (the -11 miss).** Symlink-swap `raw/` (a) before census, (b) after census before read, (c) in a churn loop during reads; leaf-file swap; capture-root swap; swap to a *different legitimate directory* (non-symlink — tests R-4 inode binding); magic-link (`/proc/self/fd`-style) component. Require: `HOLD:READ_DRIFT` or `HOLD:PATH_TYPE`, zero remote writes, in every variant, for whichever of R-2/R-3 ships.
- **A-03 Entry/path injection.** Rels containing `..`, an absolute path, a backslash, an empty component, a duplicate rel; member counts 157 and 159; an extra non-frozen file in the capture dir; a missing frozen file; capture IDs violating the grammar (lowercase, `--`, embedded `/`, length 7 and 65, a case-variant of an existing ID). Require: the named HOLD before any upload.
- **A-04 Member corruption.** One-bit flip in a member before build (caught against validation pins at R-5); one-byte flip in the sealed container's payload section; a flip in an index rel/length/hash field; a flip in the trailer. Require: build/verify HOLDs — never an upload of corrupted bytes under good pins, never a PASS.
- **A-05 Truncated/extended container.** Containers cut at the header, mid-index, mid-payload, and with the trailer missing; one trailing garbage byte; an index length field overstating its payload. Require: `HOLD:CONTAINER_FORMAT` at parse, in both the builder's self-check and §7 verification.
- **A-06 Ref race / parent drift.** Fake remote advances the ref to a sibling commit between steps 3 and 7; advances it to a descendant not containing our blob; deletes the ref mid-protocol; drifts the parent tree; races the first-publication ref creation. Require: non-fast-forward rejection or §7 exact-match failure → `HOLD:REF_RACE` / `HOLD:PARENT_DRIFT`; the winner's state is never overwritten.
- **A-07 Orphan-object failure / restart semantics.** Kill or fail the publisher after blob creation, after tree creation, after commit creation, and after the ref update with the response lost. On restart, require §6.4 reconciliation exactly: complete-by-recording only if ref + §7 verify against the journal pins; otherwise `HOLD:ID_CONSUMED` — never a second commit, never republication under the same ID.
- **A-08 Remote substitution.** Fake remote returns a wrong blob id at create; a tree whose entry at our path names a different blob; a commit with an extra parent or an altered message; altered blob bytes on re-fetch via both the raw and base64 routes. Require: the corresponding §6/§7 HOLD; PASS impossible in every variant.
- **A-09 Visibility / designation drift.** Repo reported public at step 2; wrong owner/repo; the ref targeted in the public scanner repo. Require: `HOLD:VISIBILITY` / designation refusal before any write.
- **A-10 Ceiling edges + parity.** Σ payloads exactly 67,108,864 → seals; Σ = ceiling + 1 → `HOLD:CEILING` pre-upload; a single member at the 32 MiB guard with total in range → seals; container overhead computed byte-exact against the §4 formula. Parity: the rev.3 capture manifest pin and the publisher's pinned constant are diffed — equal value, equal definition string — or the preflight fails before any fixture runs.
- **A-11 Encoding.** Blob GET returns base64 with embedded newlines (must verify); an `encoding` field that lies about the content; the raw media type returning a JSON error body; base64 with invalid padding. Require: strict handling or `HOLD:ENCODING` — never a PASS on ambiguous bytes.
- **A-12 Duplicate invocation.** `publish()` called twice with the same capture ID after a recorded success, and once after each A-07 crash point. Require: the verification-only/recording path or `HOLD:ID_CONSUMED`; under no interleaving do two commits for one capture ID reach the ref.

## 7. Post-publish re-fetch and member-level verification

All checks run against the **final commit**, fetched fresh; any failure is the named HOLD and `PUBLISHED` is not recorded:

1. GET ref → tip must equal `C` exactly (a descendant, a rewind, or any other value → `HOLD:REF_RACE` / `HOLD:PARENT_DRIFT`).
2. GET commit `C` → `tree == T`, `parents == [P]` (or `[]` for the root case), message matches the frozen template carrying this capture ID and `CONTAINER_SHA256` (else `HOLD:COMMIT_MISMATCH`).
3. GET tree `T` non-recursively, then the `captures` subtree → exactly one entry for our path with `mode 100644`, `type blob`, `sha == blob id`, `size == container length` (else `HOLD:TREE_MISMATCH`). (Verification walks trees level by level; it does not depend on the recursive-tree response, whose documented array limit is 100,000 entries / 7 MB.)
4. GET blob by id with the raw media type (`Accept: application/vnd.github.raw+json`, documented for this endpoint) → bytes. Strict fallbacks: if the raw form is refused, the JSON form's `content` is base64 that must decode strictly (alphabet + padding checked; embedded whitespace per the API's wrapping is stripped before a strict decode; `encoding` must say `base64`). Any other shape → `HOLD:ENCODING`.
5. Recompute SHA-256 of the fetched bytes → must equal `CONTAINER_SHA256` (else `HOLD:REFETCH_CONTAINER_HASH`).
6. Parse the container: magic, version, `N == 158`, index entries strictly increasing byte-wise, lengths consistent with the total (no overrun, no trailing bytes — else `HOLD:CONTAINER_FORMAT`). For **every** member: slice its payload by index offset/length, recompute SHA-256, require equality with (a) the index hash, (b) the validation-time pinned member hash, (c) the hash in the in-container `manifest.json`, (d) the line in the in-container `SHA256SUMS`. Any miss → `HOLD:MEMBER_DRIFT`.
7. **Ledger anchor.** Only after 1–6 pass: commit a non-data record to the public scanner repo's `research_notes/` naming {designated repo, ref, commit `C`, tree `T`, blob id, `CONTAINER_SHA256`, capture ID, capture-manifest rev.3 pin, member count 158, verification transcript hash}. The anchor contains hashes and identifiers only — never payload bytes.

## 8. Consumer validity and failure semantics

A capture is **valid for a consumer** iff all of: (i) the repo is the designated private repo (owner/name exact, `private == true` at consumption time — visibility drift after publication invalidates consumption, `HOLD:VISIBILITY`); (ii) the consumer starts from the public ledger anchor's exact commit `C` — branch-tip-only trust is explicitly invalid; (iii) the ref still resolves to `C`, or the consumer fetches commit `C` directly by id; (iv) the fetched blob's recomputed `CONTAINER_SHA256` equals the anchor's; (v) the full §7 step-6 member verification passes against the anchor's capture-manifest pin. Partial states — objects without a ref update, a ref update without a ledger anchor, an anchor whose verification transcript is absent — are **not** a dataset; a consumer must treat them as no-publication.

Failure semantics (all fail-closed, no automatic retries anywhere in the protocol):

| Condition | Verdict |
|---|---|
| Σ payloads > 67,108,864, or container length inconsistent with index | `HOLD:CEILING` / `HOLD:CONTAINER_FORMAT` (pre-upload) |
| Census/fstat drift, component swap, size change during read | `HOLD:READ_DRIFT` (zero uploads) |
| Non-regular file, symlink anywhere in traversal, membership ≠ frozen set | `HOLD:PATH_TYPE` / `HOLD:MEMBERSHIP` |
| Capture-ID grammar violation, ID already consumed, prefix conflict | `HOLD:ID_INVALID` / `HOLD:ID_CONSUMED` |
| Repo not private / wrong repo at any check | `HOLD:VISIBILITY` |
| Ref moved off the pinned parent; update rejected non-fast-forward; ref ≠ `C` at verify | `HOLD:REF_RACE` / `HOLD:PARENT_DRIFT` |
| Create-blob returns a different id; tree/commit fields differ from intent | `HOLD:BLOB_SUBSTITUTION` / `HOLD:TREE_MISMATCH` / `HOLD:COMMIT_MISMATCH` |
| Re-fetched container hash ≠ pinned; any member hash ≠ any pin | `HOLD:REFETCH_CONTAINER_HASH` / `HOLD:MEMBER_DRIFT` |
| Blob response shape/encoding not as specified | `HOLD:ENCODING` |
| Platform size rejection (4xx on object size) | `HOLD:SIZE_LIMIT` |
| Rate limit / 5xx / transport failure at any step | `HOLD:API` (attempt is over; restart only via §6.4 reconciliation) |

## 9. Platform grounding — official GitHub documentation (accessed 2026-10-15)

Documented guarantees relied on:

- **Create/Get blob** — https://docs.github.com/en/rest/git/blobs : create takes `content` + `encoding` (`"base64"` or `"utf-8"`); the Get-blob endpoint "supports blobs up to 100 megabytes in size"; its JSON response carries `content` as base64, and the raw media type `application/vnd.github.raw+json` returns the raw blob data.
- **Create/Get tree** — https://docs.github.com/en/rest/git/trees : `base_tree` semantics (new tree = base entries overlaid by `tree` entries, same-path overwritten; without `base_tree`, entries absent from `tree` are deleted by a commit using it); entry `mode`/`type` vocabulary (`100644` blob etc.); the recursive get-tree response is limited to 100,000 entries / 7 MB (`truncated` flag).
- **Create/Get commit** — https://docs.github.com/en/rest/git/commits : create takes `message`, `tree`, `parents`, `author`, `committer`; get returns `tree`, `parents`, `message` — the fields §7 pins.
- **References** — https://docs.github.com/en/rest/git/refs : update is `PATCH …/git/refs/{ref}` with body `sha` (required) and `force` (default `false`); leaving `force` false makes the update a fast-forward check so you are not "overwriting work"; create is `POST /git/refs` (201; 409/422 on conflict/validation).
- **Large files** — https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github : files larger than 50 MiB draw a warning; files larger than 100 MiB are blocked; repositories should ideally stay under 1 GB (5 GB strongly recommended maximum).

Inferences (labeled, not documented guarantees):

- **CAS-by-construction** (§6.7): the docs define no expected-old-value parameter for ref update; the expected-parent guarantee here is *derived* from documented fast-forward semantics + the new commit's pinned parentage + post-publish exact-ref verification. It is exactly as strong as that derivation and no stronger.
- **Orphan invisibility**: unreachable objects are not returned by any ref-based read; that they are never *served* as repository content follows from the Git object model, but GitHub documents no retention promise for unreachable objects — this design treats orphans as disposable, never as evidence storage.
- **Repo growth planning**: at ≤64 MiB per capture, ~15 captures approach the documented 1 GB "ideal" repo size; a retention/size review is due before then. Planning inference, not a platform limit.

## 10. Assumptions, unresolved limits, budgets

Assumptions:

- A-S1: The designated repo uses Git's SHA-1 object format (GitHub default). A SHA-256-object-format repo would change §5's blob-id computation and is out of scope.
- A-S2: The designated repo and branch are as designated in the -10/-11 line (`qf-data-archive`, publication branch) and Mike's storage designation stands; changing either is a new adjudication, not an implementation detail.
- A-S3: The 158-member frozen set and the capture layout come from the -10 design and the frozen capture manifest lineage; this design changes transport and ceilings, not membership or payload semantics.

Unresolved limits (gating probes for the future implementation preflight — they do not block this design):

- U-1: The cited docs state the 100 MB support bound on the **Get**-blob endpoint and the 100 MiB file block generally; no separate **Create**-blob request-body limit is stated in the cited pages. The preflight must probe a synthetic ~64 MiB blob create/get round-trip against the real API (under its own separate authorization) before any real capture relies on it. If create-side limits bite below the ceiling, the ceiling — not the evidence — is what gets revisited, by adjudication.
- U-2: `openat2` requires Linux ≥ 5.6. The preflight must check kernel support on the executing VM and, if absent, implement and adversarially test the R-3 fd-walk fallback to the same standard (A-02 applies to whichever mechanism ships).

Budgets / stop rules: this memo is the entire -12 deliverable (design only, ≤30 min, no repair allowance). Any future implementation is a separately tasked preflight with its own cap, must pass A-01…A-12, and must pin the rev.3 capture manifest (§4) before any Yahoo attempt is even proposable. No acquisition or real publication is authorized by `SINGLE_BLOB_DESIGN_READY`.

Local evidence relied on: Issue #1 comment `6203735721` (spec + -11 adjudication); `research_notes/YAHOO_PUBLISH_SNAPSHOT_DESIGN_20261015.md` (commit `28e2316`); `research_notes/yahoo_publish_snapshot_preflight_20261015/` (commit `d703a85`) incl. `ceiling_parity_record.json` (ceilings, frozen manifest sha256 `634c4541…`), `rss_run1.json` (peak RSS 121.73 MiB), `publish_snapshot.py` (capture-ID grammar, §2); `research_notes/yahoo_clean_capture_preflight_20261015/capture_manifest.json` (capture layout, 52-symbol membership basis).
