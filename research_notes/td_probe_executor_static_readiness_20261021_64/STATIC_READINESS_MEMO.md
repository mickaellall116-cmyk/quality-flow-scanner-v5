# TD PROBE EXECUTOR STATIC READINESS — task -64 r1

Task: QF-TD-PROBE-EXECUTOR-STATIC-READINESS-20261021-64 r1
Spec: Issue #1 comment 6308896693 (GO for one ≤35-minute zero-credit
read-only static readiness pass; single-dispatch pre-check + ACK first;
this pass does NOT authorize the probe).
Basis: -63 desk packet (commits 1b8f384 / 946618b; terminal
TD_S2_VENDOR_CONVENTION_DESK_PASS__PROBE_AUTHORIZATION_REQUIRED; memo
sha256 d37a65c1…). The probe itself remains USER-GO HOLD. Governance
correction preserved: passing the two sampled windows (NVDA/TSLA)
cannot globally retire S2 — at most it qualifies those windows'
adjustment behavior.
Method: ONE static read-only pass over pinned source at origin/main
610f138. No execution of any kind (no code run, no tests, no mock
runs), no network beyond the read-only spec fetch, no credentials read
or displayed, no credits, no files/code/manifests modified outside
this package. Sole-ownership pre-check PASS (no td64 stage dir, no
td64 worktree, no -64 commit on origin/main, no owner lease).

## TERMINAL

TD_PROBE_EXECUTOR_STATIC_HOLD__NO_PINNED_CALLABLE_ENTRYPOINT

The pinned pilot acquisition stack cannot execute the -63 packet
as-is. Five gaps, in execution order (§3); gap 1 blocks everything:
nothing in the repo can be invoked to run the packet at all.

## 1. Pinned source under inspection

| artifact | path | sha256 |
|---|---|---|
| acquisition wrapper | research_notes/pilot_harness/pilot_acquire.py | acf39bbd98f7174a4205019e754fc714ca420b4a7df43c815ea158a6fad67c59 |
| frozen manifest R3 | research_notes/pilot_harness/request_manifest.json (TD-PILOT-MANIFEST-R3-20261010, frozen=true, 91 requests) | a0a001b7458993ffb21c33a92a0fa9aec7a7126691e749a1a3dfb06afbb8b9f0 |
| credit limiter | research_notes/pilot_harness/rate_limiter.py | 06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64 |
| source verifier (wrapper preflight) | research_notes/pilot_harness/verify_sources.py | a0bd2e4cdce44be5d9fcc1d7c21046391d36c9bd366a959df03bf5d19c9a79e0 |
| pilot credit ledger (state) | research_notes/pilot_harness/credit_ledger.json (day 2026-10-14, spent 8) | 7e5ccef0e5fd7e2faa744c8fe7ee646c3162fa4f72fc4a9a85317d52b5d890ed |
| only ManifestDriver instantiation | research_notes/pilot_harness/tests/test_acquisition_wrapper_r3.py (L153) | 3b4e84be77edbd46a966a89cbb23d22b9cd51c8f1ae12cda2ac5689fb3ef17b9 |
| /api_usage gate (SEPARATE FRESH lineage) | research_notes/td_policy_a_live_readiness_packet_20261017_11/dispatch_gate_r4.py | b53996454650dafc77e647a8497eba91beb3785fb52c13d70fa81768fd370117 |
| /api_usage transaction (FRESH lineage) | research_notes/td_policy_a_live_readiness_packet_20261017_11/readiness_transaction.py | 7ced79221b0156d4111f7d93e03cc05577eb9c2272d433ae6013335b583b78f3 |
| credential helper (existence/shape ONLY; value never read) | /opt/hatch/skills/skill-creator/bin/dynamic_credentials.py | 8b1f42e80a76710edf0ff2abf8a51b0cde35b06474af865de108a7ca27d6728d (matches the sanctioned-helper pin) |

Working-tree copies of pilot_acquire.py / request_manifest.json are
byte-identical to origin/main (hashes above are of the origin/main
blobs). pilot_acquire.py imports the helper's
url_with_surrogate_query_param with CRED="custom.twelvedata" and
ALLOWED_HOSTS=["api.twelvedata.com"] (L74-87); the key is attached by
the helper at fetch time (L174-180) and never enters params, receipts,
or logs (KEY_RE scrub, L103).

## 2. Field-by-field static matrix (frozen stack, as-is)

Legend: YES = expressible as-is; NO = refuted as-is; MECH = mechanism
exists in source but the frozen artifacts do not carry the packet's
shape (would need a new pinned artifact, not a code change).

| # | -63 control | verdict | evidence |
|---|---|---|---|
| 1 | adjust=splits explicit | YES | _build_url emits adjust from the spec (pilot_acquire.py L223-236); ADJ-01/02/03 in the frozen manifest carry adjust="splits" verbatim |
| 2 | adjust=none twins REQ-ADJ-01N/02N | NO (frozen) / MECH | all 91 frozen requests are adjust="splits" (counted); no 01N/02N IDs exist. The manifest schema treats adjust as a free field (no enum check in _load_and_validate, L506-545), so a probe manifest could carry "none" with no code change — but that manifest does not exist |
| 3 | interval 1h | YES | ADJ legs are 1h; interval is a per-request field bound again by the schema gate (L246-254) |
| 4 | timezone America/New_York | YES | explicit per request and in the URL params |
| 5 | outputsize 5000 | YES | explicit per request |
| 6 | order ASC | YES | explicit per request |
| 7 | exact start/end | YES | manifest validation enforces datetime precision (DATE_RE, L503/L526-530); frozen ADJ bounds match the -63 packet exactly (NVDA 2023-12-13T00:00:00→2024-06-21T23:59:59; TSLA 2022-03-07T00:00:00→2022-09-09T23:59:59; AAPL 2026-02-19T00:00:00→2026-08-24T23:59:59) |
| 8 | zero pagination for this packet | YES | _pag_trigger fires only for leg=="PAR" AND interval=="1h" (L570) and only at exactly 5000 returned rows; ADJ/REV legs can never trigger it, and the ADJ windows (~900 rows per the -63 packet) cannot meet the row condition. PAG children are created only in run_day's post-pass over PAR rows (L601-624) |
| 9 | max 2 HTTP attempts/request | NO (frozen) / MECH | MAX_ATTEMPTS=3 (L87); EVERY frozen request pins max_attempts=3; defaults.max_attempts=3. The -63 ceiling arithmetic (≤24, expected 12) assumes ≤2 (its assumption A3). Frozen-as-is worst case breaks the ceiling: day 1 = 1 usage + 5 data×3 attempts = 16 calls; each REV day = 1 + 2×3 = 7; total worst case 30 > 24. The cap IS manifest-expressible without code change: _to_spec reads per-request max_attempts (L555) and the retry loop bounds on spec.max_attempts (L407); with 2, only BACKOFF_S[0]=60s is reachable (L87, tuple (60,300)). But no existing artifact sets it to 2 |
| 10 | one /api_usage preflight per execution day | NO in this stack | pilot_acquire's preflight is verify_sources archival pinning (_default_preflight, L218-221) — it never calls /api_usage. The /api_usage component exists ONLY in the separate FRESH/Policy-A lineage (dispatch_gate_r4.py L469-489; readiness_transaction.py L311), which is candidate-not-adopted and bound to the FRESH screen manifest, not to pilot_acquire/ManifestDriver. Not wired; cannot be invoked from this stack |
| 11 | sanitized params + UTC-ms timing + HTTP/status/error record + byte count + SHA-256 | YES | per-attempt entries: request_ts_ms, receipt_ts_ms, http_status, bytes, sha256, scrubbed allowlisted headers (L438-449); final receipt adds sanitized params (no key material by construction, L236); append-only <id>.attempts.jsonl (L297-302); completion marker re-verifies sha256+bytes+params (L304-322); snapshots O_EXCL no-overwrite (L335-355) |
| 12 | R7/R30 immutable base-request linkage | NO (for ADJ) / MECH | mechanism exists: base_request_id field (L149), manifest validation requires the base defined earlier (L533-539), run_day fails closed if the base receipt is missing (L606-612). BUT the frozen manifest's 40 REV legs all link to REQ-P1H-* PAR windows — there are NO ADJ-linked revision requests (no REQ-ADJ-01R7/02R7/01R30/02R30). The -63 waiting legs are unmanifested |
| 13 | deterministic byte/bar comparison inputs | YES (inputs only) | once acquired, base + revision legs yield byte-pinned snapshot/receipt pairs (sha256+bytes in receipts). The COMPARISON itself has no analyzer — §4 |
| 14 | packet scope isolation (run ONLY the packet's requests) | NO (frozen) | run_day(day) executes every manifest request with that day label. Frozen day D1 = 11 requests: ADJ-01/02/03 PLUS 8 SPOT legs (REQ-SPT-01..08). Running the frozen manifest "as-is" on its D1 would fire 8 requests the packet does not authorize. A probe-only manifest is required |
| 15 | callable entrypoint | NO — FIRST GAP | pilot_acquire.py has no __main__/CLI (624 lines; classes only). ManifestDriver is instantiated ONLY in tests (test_acquisition_wrapper_r3.py L153); pilot_acquire is imported ONLY by the two test files. Prior pilot executions (SPOT8, Oct 14) happened, but their invocation artifact is not pinned anywhere in the repo. There is no pinned production runner taking (manifest, day, store) |

## 3. Gaps in execution order (first-failure order for any GO day)

G1. NO_PINNED_CALLABLE_ENTRYPOINT — nothing invokable exists for the
    pilot stack. Any execution would require a new runner artifact or
    an unpinned ad-hoc session. (Blocks step 0.)
G2. NO_PROBE_MANIFEST — the packet's exact shape (ADJ-01/02/03 +
    01N/02N twins at adjust=none + ADJ-linked R7/R30 legs, and ONLY
    those) exists in no manifest. The frozen R3 manifest both omits
    the twins/ADJ-REVs and over-includes SPOT legs on the ADJ day.
    A probe manifest is authorable under the existing schema +
    budget-formula validation (expected_total == request count;
    max_total == base + pagination + retries, L537-545) with no code
    change — but it must be created, reviewed, and pinned under its
    own task before any GO.
G3. ATTEMPTS_CAP_NOT_IN_ANY_ARTIFACT — max_attempts=3 everywhere;
    the packet's ≤2 (and therefore its ≤24 ceiling) is unenforceable
    from existing artifacts. Fix is data-only (per-request
    max_attempts=2 in the G2 probe manifest), zero code change.
G4. API_USAGE_PREFLIGHT_EXTERNAL — the once-per-day /api_usage
    preflight lives in a different, unadopted candidate lineage
    (FRESH gate) bound to a different manifest. The pilot stack has
    no account-standing check at all; its ledger (RollingCreditLimiter,
    pilot-shaped day/window caps, rate_limiter.py L64-76) is a local
    spend guard, not an account probe.
G5. NO_C1_C6_ANALYZER — §4. Post-acquisition, nothing pinned exists
    to run the precommitted comparisons.

None of G1-G5 is self-fixed here (hard control). G2+G3 are closable
with data-only artifacts; G1 needs a small runner artifact; G4 needs
an explicit lineage decision; G5 needs an analyzer task. All are
pre-GO work, none requires vendor contact.

## 4. Analyzer inventory (spec §5): NONE EXISTS

Searched the repo (code + notes, excluding archived evidence copies)
for any ready, performance-blind analyzer for the -63 comparisons
C1 (none-vs-splits factor ratios), C2 (volume scaling), C3 (split-day
flip location), C4 (Amendment S4 OHLC consistency), C5 (revision
byte/bar diff), C6 (row-count/no-pagination confirmation). Result:
no such module exists. Nearest non-matches, for the record:
- research_notes/td_req_s2_offline_implementation_20261020_59/
  s2_split_exclusion_v1.py — the S2 EXCLUSION transform, not a
  comparison analyzer.
- research_notes/pilot_harness/construct_4h.py — 4H bar construction
  from acquired bars; computes no C1-C6 comparison.
- xnys parity_check.py (-35 lineage) — calendar parity, unrelated.
A missing analyzer is a readiness gap, not permission to implement.

## 5. Execution-day-only dependencies — UNTESTED UNTIL USER GO

Do not probe any of these in this task; each can only be observed on
an authorized execution day:
D1. Credential presence/validity via the sanctioned helper
    (path exists, sha256 matches the standing pin 8b1f42e8…;
    whether the vault surrogate resolves on the day: UNTESTED).
D2. Account/plan status and remaining credit headroom (observable
    only via the /api_usage call itself; Basic/Free evidence on file
    is from the -18 preflight record, not re-probed).
D3. Endpoint response/schema conformance for the ADJ windows
    (meta.symbol/interval binding and value shapes are enforced at
    L239-259; whether TD's actual responses pass is UNTESTED).
D4. Host clock correctness (all receipt timestamps derive from the
    local clock; the -18 stale-clock adoption rollback is the
    standing precedent for this failure family).
D5. Writable store path + ledger state on the day (pilot ledger is
    pinned at day 2026-10-14 / spent 8; day-rollover and the
    untracked .lock/.dispatch_lease residue in pilot_harness/ are
    UNTESTED for a probe run; the limiter's caps are pilot-shaped,
    not packet-shaped — the ≤24 packet ceiling is enforced by the
    manifest budget formula + the G2/G3 artifacts, not by the
    limiter).
D6. Network egress to api.twelvedata.com (ALLOWED_HOSTS pin exists
    in source; reachability on the day UNTESTED).

## 6. No-secret command/argument blueprint (placeholders only)

Step 0 (MISSING — separate pre-GO task): author + pin <PROBE_MANIFEST>
(ADJ-01/02/03 adjust=splits; ADJ-01N/02N adjust=none; every request
max_attempts=2; ADJ-01R7/02R7 on the +7 day and ADJ-01R30/02R30 on
the +30 day with base_request_id -> REQ-ADJ-01 / REQ-ADJ-02) and a
pinned <RUNNER> that instantiates
ManifestDriver(<PROBE_MANIFEST>, <STORE_DIR>, RollingCreditLimiter,
UrllibTransport) and calls run_day(<DAY>).

  # execution day (only after Mike's GO + ChatGPT's execution spec):
  <API_USAGE_PREFLIGHT>            # once; lineage per G4 decision
  python3 <RUNNER> --manifest <PROBE_MANIFEST> --day <D-EXEC>  --store <STORE_DIR>
  # no earlier than +7 days:
  python3 <RUNNER> --manifest <PROBE_MANIFEST> --day <D-REV7>  --store <STORE_DIR>
  # no earlier than +30 days:
  python3 <RUNNER> --manifest <PROBE_MANIFEST> --day <D-REV30> --store <STORE_DIR>

No credentials appear in any argument: the transport attaches the
surrogate server-side via the sanctioned helper at fetch time.

## 7. Failure order at runtime + rollback/cleanup

Runtime failure order inside the stack (for the future GO record):
(1) wrapper preflight source-verification failure -> RuntimeError
before any call, zero credits; (2) LEDGER_REFUSED -> driver exits,
resume is a fresh invocation (completed requests skip via verified
markers); (3) AUTH_STOP on 401/403 -> run stops; (4)
SCHEMA_QUARANTINE on 200-with-schema-break or unexpected terminal
status -> stop; (5) RATE_STOP (2 consecutive 429s on one request, or
3 distinct-request 429s in a rolling 10 min) -> stop; (6)
RETRIES_EXHAUSTED -> stop. Rollback for acquisition is structural:
snapshots are O_EXCL immutable, receipts/attempt logs are append-only
evidence, orphans are quarantined (never silently accepted, L324-333);
an aborted day leaves store + ledger consistent for resume, and no
production/trading state is touched by this stack. For -64 itself:
read-only; the package is additive; rollback = ignore the package.

## 8. Accounting

Elapsed: spec fetch 2026-10-21T06:00:36Z -> package commit (see
SHA256_MANIFEST.txt companion commit) — under 10 minutes of the
≤35-minute box. Repair minutes: 0. Credits spent: 0. Vendor/API
calls: 0 (the read-only GitHub spec fetch is the only network use).
Disclosures: (a) prior pilot executions exist in the record (SPOT8)
but their invocation artifact is not pinned in-repo — stated as
found, not reconstructed; (b) untracked runtime residue
(credit_ledger.json.lock / .dispatch_lease) sits in pilot_harness/ —
observed, untouched; (c) the FRESH-lineage executor (r5) was NOT
inspected as this packet's executor because it binds the FRESH
screen manifest and Policy A, a different acquisition program; its
/api_usage lineage is cited only for G4.

Failure-family tags: #no-pinned-entrypoint #manifest-scope-mismatch
#attempts-cap-not-in-artifact #api-usage-preflight-external-stack
#analyzer-absent #executor-static-readiness #td-s2-probe
#user-go-required
