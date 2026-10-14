# Issue #9 offline enforcement-harness candidate — QF-ISSUE9-OFFLINE-HARNESS-20261014-03 r1

**Verdict: OFFLINE_HARNESS_PASS**

Spec: GitHub Issue #1 comment `6180467878` (ChatGPT adjudication of route-readiness
r1), which governs where this memo and the tasking brief differ. Build executed
2026-10-14 ~23:09–23:14 UTC, inside the ≤60-minute box, with no repair pass
needed against the harness itself (one one-line tooling fix to the fixture
runner, recorded in §5).

**What a PASS means — and does not mean.** This PASS establishes *synthetic
harness behavior only*: the enforcement code below behaves correctly against a
scripted fake transport under adversarial fixtures. It does **NOT** authorize a
first live model call or the Arm A/B swarm comparison. A separate Mike
execution GO plus same-day price/quota/model evidence remains required
(readiness blockers B1/B3 are untouched by this build). No automatic
activation; nothing here is wired into any live path.

## 1. What was built (isolated, new files only)

Package: `research_notes/issue9_offline_harness_20261014/`

- `tools/offline_harness.py` — the candidate enforcement harness (stdlib only,
  imports no HTTP client). Dependency-injected transport; an injected
  deterministic clock; per-arm-seed runner.
- `tools/run_fixtures.py` — deterministic adversarial fixture suite. It patches
  the socket layer (`socket.socket`, `create_connection`, `getaddrinfo`,
  `gethostbyname`) to raise **before** anything runs, then drives the harness
  with scripted in-memory fake transports.
- `fixtures/fixture_results.json` — full per-fixture results (29/29 matched;
  byte-identical on rerun).
- `evidence/f01_clean_control_ledger.jsonl` + `f01_clean_control_summary.json`
  — the clean-control run's actual hash-chained ledger and its frozen-schema
  summary, preserved as evidence (byte-identical on rerun).

The live `bin/or_chat.py` was **not** edited, per spec. The production scanner
and the live V5.4 harness were not touched: live `v54_forward_harness.py`
sha256 is `dc3ee392…` — the deployed feed-repair r2 candidate — unchanged
before and after this build, and the deployed feed fix's two-cycle observation
gate was not disturbed (no extra scans, no harness reads beyond a hash).

## 2. Enforcement design

- **Preflight first.** The -02 preflight guard (`preflight_guard.evaluate`,
  the D-R2-01 repair) evaluates the declared dispatch packet before any
  dispatch; a BLOCK means zero transport invocations (fixtures F08, F09,
  F10b, F24).
- **Empty content is a failed call.** A response with empty/blank content is
  recorded as `FAILED_EMPTY_CONTENT` with reason `EMPTY_CONTENT` and stops the
  run. Reasoning tokens are written into the ledger (counted) and are **never**
  substituted as candidate content — the D-R2-02 defect adjudicated against
  `bin/or_chat.py`'s `content or reasoning` is designed out here (F02, F03).
- **Immutable ledger, persisted before advancing.** Append-only JSONL with a
  sha256 hash chain (`prev_hash`/`record_hash` over canonical JSON). Every
  record is flushed and `fsync`'d before the run advances. A write-ahead
  `dispatch_intent` record precedes every transport call, so a crash between
  response and outcome append leaves a *detectable orphan* instead of an
  ambiguous gap: on restart the ledger classifies `ORPHANED` and any further
  dispatch is refused (`ORPHANED_LEDGER`) — no blind resend, no double
  counting (F20).
- **Frozen caps, enforced at runtime** (protocol v1.0.0, per arm-seed):
  A ≤ 8 / B ≤ 16 calls (`CEILING_CALLS`), ≤ 120,000 billed tokens
  (input + output + reasoning, counted in full), ≤ 45 min wall
  (`CEILING_WALL`), $0.00 incremental cost, provider free-quota headroom
  (default 50/day). Before each dispatch the runner reserves
  `est_input + max_output` against the token cap (`CEILING_TOKENS` fires
  pre-dispatch, F17); after each response, actual usage is checked — output
  over its reservation or a total over the cap is an `OVERRUN` hard stop with
  the content quarantined, never accepted (F19). A declared plan-level cap
  alone cannot stop a single oversized response; the runtime reservation can.
- **Usage integrity.** Missing usage object → `MISSING_USAGE`; missing
  reasoning metering → `UNMETERED_REASONING`; negative values →
  `NEGATIVE_USAGE`; provider-reported billed ≠ input+output+reasoning →
  `INCONSISTENT_USAGE`. Every outcome whose usage is known counts toward the
  token cap, including failed calls (F04–F07).
- **Model pin.** Requested model must equal response model
  (`MODEL_MISMATCH`, F11); a provider-reported fallback stops the run
  (`FALLBACK_DETECTED`, F12); provider model/version metadata is retained in
  every outcome record, and a response with no version metadata is treated as
  unverifiable alias drift — inconclusive, fail-closed
  (`MODEL_VERSION_UNVERIFIABLE`, F13). A model-id echo alone is not treated as
  proof of an immutable underlying version.
- **Cost.** Price evidence is validated before the run and before every
  dispatch: missing → guard `COST_NOT_VERIFIED` / runtime
  `PRICE_EVIDENCE_MISSING`; unknown price → `PRICE_UNKNOWN`; nonzero →
  `PRICE_NONZERO`; expired → `PRICE_EVIDENCE_EXPIRED` (F08–F10b). A response
  reporting nonzero cost despite a $0 catalog stops the run (`NONZERO_COST`,
  F26).
- **No retries, no silent fallback.** A transport timeout is recorded once
  (`FAILED_TIMEOUT`) and stops the run; the fixture proves the transport is
  invoked exactly once and no second dispatch occurs (F14).
- **Quota and multi-day continuation.** Dispatch intents are counted per
  quota day from the ledger itself. A continuation on a new day is refused
  (`QUOTA_RESET_UNVERIFIED`, F21) unless an evidence-backed `quota_reset`
  ledger record exists for that day (F22) — the reset is itself an immutable
  record naming its evidence reference.
- **Order and blinding preconditions.** Frozen seed order S1 → S2 → S3 is
  enforced by a seed-order guard (`SEED_ORDER_VIOLATION`, F25); each call's
  prompt hash must be in the registered frozen set at dispatch time, so plan
  drift to an unregistered/cross-arm prompt is blocked pre-dispatch
  (`PROMPT_CONTAMINATION`, F23). Per-arm role sets are enforced
  (`ROLE_INVALID`).

## 3. Fixture results — 29/29 matched, deterministic

All fixtures were attempted; none skipped. Summary by class (full records in
`fixtures/fixture_results.json`):

| Class | Fixtures | Result |
|---|---|---|
| Network denial | F00 | PASS — socket layer raises before any dispatch |
| Clean control | F01 | PASS — 3/3 recorded, chain verifies, billed 3,750, frozen-schema summary emitted |
| Empty content | F02, F03 | PASS — `EMPTY_CONTENT` stop; reasoning counted, never substituted |
| Usage integrity | F04, F05, F06, F07 | PASS — unmetered/missing/inconsistent/negative all fail closed |
| Price & cost evidence | F08, F09, F10, F10b, F26 | PASS — guard or runtime blocks; zero dispatches on plan-level failures |
| Model pin / fallback | F11, F12, F13 | PASS — alias swap, fallback, unverifiable version all stop the run |
| Timeout / retry | F14 | PASS — exactly 1 invocation, recorded once, no re-dispatch |
| Quota | F15 | PASS — stops at the daily cap (cap 3 injected; same code path as the default 50) |
| Call / token / wall ceilings | F16a, F16b, F17, F18 | PASS — caps fire pre-dispatch at the boundary |
| Overrun | F19 | PASS — hard stop, usage counted, content quarantined |
| Crash / restart | F20 | PASS — orphan detected, resume refused, billed counted once |
| Multi-day continuation | F21, F22 | PASS — no reset without evidence; reset with evidence resumes cleanly |
| Contamination / order | F23, F25 | PASS — unregistered prompt and out-of-order seed both blocked |
| Preflight guard | F24 (+ F08/F09/F10b) | PASS — forbidden route BLOCKed, zero dispatch |

## 4. Scope confirmations

- Fake transport only; **zero** provider/model/API calls, **zero** spend,
  **zero** installs, **zero** live/production changes. New files only, under
  `research_notes/issue9_offline_harness_20261014/` plus this memo.
- The frozen protocol was not altered; the prep package was re-verified by
  hash only (its manifest state is unchanged).
- The Yahoo post-deploy observation/rollback obligations are the parent
  desk's; this build ran no scans and touched no live state.

## 5. Defects and repair effort

- No defect was found in the harness enforcement logic; no repair pass against
  it was needed (the ≤15-minute repair allowance is unused).
- One tooling fix during verification: the fixture runner did not create a
  caller-supplied evidence directory before writing into it
  (`FileNotFoundError` on a rerun into a fresh path). Fixed with a one-line
  `os.makedirs(..., exist_ok=True)`; the suite was then rerun end-to-end —
  29/29 matched and outputs were byte-identical across runs.
- Known synthetic-only limits, stated plainly: quota fixtures inject small
  caps (3 and 2) to exercise the same enforcement path as the production
  default of 50/day; wall time and timestamps come from the injected clock;
  transport behaviors are scripted, so transport-level realities of a real
  provider (partial JSON, connection resets mid-body) are represented only
  insofar as they surface as the exception/response shapes fixtures script.

## 6. What remains before any execution (unchanged from readiness)

1. Mike's separate execution GO.
2. Same-day evidence on execution day: catalog $0 price for the selected pin,
   account/quota headroom against the 50/day free cap, first-call assertions
   (usage present, response model/version match, non-empty content), post-run
   $0 delta — checklist E1–E8 in the -02 memo.
3. Pin selection itself (blocker B1): the only model with local $0 evidence
   returned empty content in the pilot configuration; this harness now
   guarantees such a run stops fail-closed and counts its reasoning tokens —
   it does not make the model good.

— Muse
