# TD LIVE CLEARANCE PATH BINDING — 2026-10-17 (-15 r1)

**Task:** QF-TD-LIVE-CLEARANCE-PATH-BINDING-20261017-15 r1 (spec: Issue #1
comment 6238190142, fetched via the public API first and followed exactly).
**Verdict: `LIVE_CLEARANCE_PATH_BINDING_TARGETED_PASS_OFFLINE`** — targeted
offline PASS only, in the spec's acceptance vocabulary. The first real
`GET /api_usage` remains HOLD pending independent review of these bytes
and a distinct clearance record. **NOT AUTHORIZED.**

## What was wrong (accepted -14 review finding)

The -14 executor's one-use clearance bound transaction id and artifact
**hashes** but not the canonical live `target_path` / realpath, `workdir`,
`candidate_path`, or `dryrun_root` — those came from the unpinned live
packet, so any byte-identical legacy-ledger copy could satisfy the legacy
hash, be adopted, and yield COMPLETE while the adjudicated shared ledger
never changed. The executor also read `candidate_path` in its constructor
before clearance verification, and sent the helper's returned URL to
transport without independently asserting the final URL at the boundary.

## The repair (new candidate, -14 base preserved byte-identical)

`live_readiness_executor_r2.py` (`e93e88a5…`), derived from the -14 executor
(`689ab473…`, re-verified unchanged after all work):

1. **Clearance schema v2** (`schema: QF-TD-READINESS-CLEARANCE`,
   `schema_version: 2`) binds, in addition to the -14 hash set (txn id,
   executor sha, gate sha, Policy A digest, candidate sha, legacy sha,
   ceiling 52, scope `READINESS_ONLY_ONE_API_USAGE`): `target_path`,
   `target_realpath`, `workdir`, `candidate_path`, `dryrun_root`, and
   `packet_digest` = sha256 of the canonical live packet identity (mode,
   txn id, workdir, target path, candidate path, dry-run root, expected
   legacy/candidate hashes, GO record, sanctioned-helper identity). Every
   live packet field is thereby validated against the clearance.
2. **Admission before any touch.** The candidate read moved out of the
   constructor; live admission (`validate_live_admission`) performs the
   candidate verification read, Policy A pin, GO record, v2 clearance
   verification, and path hygiene **before** marker/workdir/lock/vendor/
   ledger touch (immutable source/policy verification reads excepted —
   the corrected boundary wording is in proposal R5).
3. **Path hygiene (live admission):** symlink or non-regular target /
   candidate, symlinked workdir ancestors, and symlink lease/lock paths
   are refused (`PATH_HYGIENE_REFUSED`) before marker creation.
4. **Target identity under lock:** the journal now captures the target's
   `st_dev`/`st_ino` under lock at BEGUN; pathname/inode/realpath (and
   bytes, pre-status) are revalidated **immediately before the status
   boundary** and **again before mutation** (`TARGET_IDENTITY_DRIFT`).
   No-stale-restore semantics preserved.
5. **Executor-side final URL boundary:** after the helper returns the
   credentialized URL, the executor parses it and requires HTTPS, exact
   host `api.twelvedata.com`, exact path `/api_usage`, no fragment, no
   userinfo, no alternate port, and only the expected credential query
   shape (no query, or exactly one `access_token` parameter) —
   `STATUS_URL_BOUNDARY` refusal **before** transport is invoked.

## Proof (offline, kernel network denial, twice)

New -15 matrix (`946baa91…`, identical both runs): **23/23 trials, 83/83
checks** —

- q01 canonical live-path fixture: admission passes, creates nothing,
  target untouched, no lease/lock files.
- q02 byte-identical **decoy target** refused at admission
  (`CLEARANCE_BINDING_MISMATCH`) before marker/status/mutation.
- q03 workdir drift, q05 packet-field (dry-run root / digest) drift, and
  the path-set-A-vs-B case refused before marker creation.
- q04 edited clearance refused twice over: stale pin →
  `CLEARANCE_PIN_MISMATCH`; re-pinned edit → `CLEARANCE_BINDING_MISMATCH`
  (a fresh hash cannot launder an edited path).
- q06–q09 symlink target / candidate / workdir ancestor / lease path →
  `PATH_HYGIENE_REFUSED` before marker.
- q10 exact canonical paths: full offline run COMPLETE once (real r4 gate
  dry-run), exactly 1 status call, recovery ADOPTED_VERIFIED with 0
  recovery status calls.
- q11 symlink swap **before status**: HOLD `TARGET_IDENTITY_DRIFT`,
  transport invocations 0, journal `status_calls` = 0, decoy never
  overwritten. q12 inode drift (identical bytes, new inode) before
  status: same HOLD, counter 0.
- q13 inode drift during status → caught before mutation: HOLD, no
  adoption, target bytes intact. q14 symlink swap during status → HOLD
  before mutation, decoy never written through.
- q15–q22 URL-boundary mutations (host confusion, alternate path,
  redirect-shaped query, userinfo, port 8443, extra query, http scheme,
  fragment): HOLD `STATUS_URL_BOUNDARY`, **transport invocations = 0**,
  boundary invocations = 0, target untouched. q23 well-formed
  `access_token` query passes the boundary → COMPLETE.

Regressions, twice under `unshare -n`, byte-identical to the pinned
matrices: -14 executor matrix `19e8dc67…` (23/23, 82/82, run against the
unmodified -14 executor); r4 gate matrix `aafd4e1b…` (46/46, 332/332);
-13 transaction matrix `56084b75…` (45/45, 193/193).

## Time / repair

≈11 minutes of the ≤20 cap (14:27→14:38 ET); **zero repairs used** — all
matrices passed on their first runs (regression commands mirrored the
-14 TMPDIR-on-overlay discipline from the start).

## Scope confirmation

Offline/network-denied throughout; zero authenticated/vendor calls beyond
the spec fetch; real-helper invocations 0 (offline path resolves only the
pinned stub/variant helpers through the same resolver; the sanctioned
helper was never imported); credits 0; real ledger writes 0 (live ledger
re-verified `7e5ccef0…` after all runs); no token/armed transport/
`time_series`/installs/backtest/production/Issue #9; the -14 package and
all prior bases byte-identical; deliverables UNCOMMITTED. Proposal R5
(`70286935…`) remains **NOT AUTHORIZED** and still explicitly excludes all
51 market-data requests and token issuance.

— Muse
