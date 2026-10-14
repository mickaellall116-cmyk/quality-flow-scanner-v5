# Issue #9 Route Readiness — QF-ISSUE9-ROUTE-READINESS-20261014-02 r1

**Status: BLOCKED** (not ROUTE_READY_FOR_EXECUTION_REVIEW). Blockers B1–B3 in §7 are
evidence-based and resolvable only at/after a separate execution GO. The packet is
complete for execution review; nothing in it authorizes any provider/model call.

**Scope honored:** offline / read-only only. Zero provider/model calls, zero spend,
zero installs, zero config changes, no Arm A/B execution, no backtest, no production
files touched. The live V5.4 harness and its two-cycle observation gate were not
interrupted; no extra Yahoo scans were run. Prep was NOT repeated: the frozen prep
package was re-verified by hash only (16/16 manifest entries OK from repo root;
prep commit `8675638`).

**Spec:** GitHub Issue #1 comment `6180132721` (2026-10-14T22:42:23Z), fetched via the
unauthenticated public API as instructed by the dispatch brief. Where the brief and
the comment differed, the comment governed.

**Time spent:** inside the 45-min box — all work falls between the 22:42Z spec and
the 23:04Z manifest verification — including the single bounded repair (≈10 min,
§4). Evidence package: `research_notes/issue9_route_readiness_20261014/`.

---

## 1. What the frozen protocol requires of a route

From `comparison_protocol.json` v1.0.0 (`model_pin_requirements_at_execution` +
`budgets_per_arm_per_seed.cost_rule`), the four pin requirements, plus the two
further evidence questions the r1 spec (§1) names:

- **P1 — Model pin:** ONE model/provider/version pinned identically for both arms,
  recorded in the run manifest before any call. No mid-run substitution.
- **P2 — Metering:** the provider must expose per-call token usage **including
  reasoning tokens**; billed tokens = input + output + reasoning, summed in the
  resource ledger (`resource_ledger_schema.json` requires per-call
  `input_tokens / output_tokens / reasoning_tokens / billed_tokens / cost_usd`).
- **P3 — Zero cost:** the route must be verifiably $0.00 incremental **before the
  run**, with provider catalog/account evidence in the run manifest. If the pinned
  model is not verifiably zero-incremental, execution is unauthorized.
- **P4 — No silent fallback:** any provider-side fallback/substitution detected
  voids the affected arm-seed and stops the run for adjudication.
- **P5 — Enforceable ceilings:** per arm-seed ≤120,000 billed tokens, calls A≤8 /
  B≤16, ≤45 min wall, ≤8 cards; pair divergence >5% of cap = BUDGET_MISMATCH.
- **P6 — Retention & credentials:** prompts must not leak credentials/private data
  (immediate-stop condition); credential handling must stay inside the vault
  surrogate boundary.

## 2. Route inventory (read-only, secrets redacted)

### R1 — OpenRouter direct via vault surrogate (sole surviving candidate)
- Connector on file: `custom.legacy-openrouter` (CONNECTOR.md sha256 `92a0d29a…`).
  Auth is the stored `custom.openrouter` credential, attached by
  `dynamic_credentials.add_surrogate_to_request(...)`; only `hsurr:*` surrogate
  values are sent, only to `openrouter.ai`. No raw key was read or printed in
  this task.
- Existing clients: `bin/or_chat.py` (sha256 `512f9770…`), `bin/or_models.py`
  (sha256 `66ac451e…`) — minimal probes, not an execution harness (see D-R2-02).
  `or_chat.py` posts `{model, messages, max_tokens}`, prints the response's raw
  `usage` object; `or_models.py` lists the catalog (with a `:free` filter).
- Standing account record (MEMORY.md): free models, **50 requests/day** — a
  documented account-level cap that interacts with the run envelope (§6).

### R2 — Claude direct
- The executing/reviewing route today; reliable, but exposes **no per-call token
  metering**, so it cannot fill the resource ledger comparably for two arms
  (prep memo §3). The r1 spec §3 forbids relying on unmetered Claude direct.

### R3 — OmniRoute (local gateway) → OpenRouter
- **Forbidden by the frozen protocol** (adjudicated FAIL/PARK 2026-10-14).
  Read-only re-inspection today (SQLite `mode=ro`, schema + row counts only, no
  credential rows read): `request_cost_ledger` = **0 rows**, `provider_quota_state`
  = **0 rows** — the pilot's central metering finding persists unchanged.
  Pilot memo (`50ae59ca…`) §1 also records: the local API key has **no daily USD
  cap and no per-day request cap**, full request/response artifacts are persisted
  in cleartext under `~/.omniroute/call_logs/`, and the daemon binds `0.0.0.0:20128`.

### R4 — MiroFish / swarm platforms
- Not installed; PARK/IDEA ONLY. Not a route; excluded per spec §3.

## 3. Requirement matrix (per route × requirement)

Evidence classes: **VERIFIED** = local artifact from an actual past run or code
read today · **DOCUMENTED** = on-file docs/catalog/account record · **INFERRED** ·
**UNKNOWN / NOT VERIFIABLE OFFLINE** · **FAILS**.

| Req | R1 OpenRouter direct | R2 Claude direct | R3 OmniRoute |
|---|---|---|---|
| P1 pin | **DOCUMENTED capability, NOT VERIFIED**: exact model-id strings exist (catalog CLI; pilot pinned an exact id). No execution pin has been selected, so no pin exists to verify. Selection is an execution act. | n/a (route excluded) | **FAILS (policy)**: protocol forbids the route outright. |
| P2 metering incl. reasoning | **VERIFIED (mechanism)**: pilot `results.json` (`707db1f9…`) records per-call tokens_in/out/**reasoning** (244/700/817, 115/700/721, 226/700/758) from this provider's responses; `or_chat.py` surfaces the raw `usage` object (code-read today). Caveat: no direct-path ledger capture exists yet (B2). | **FAILS**: no per-call metering exposed (prep memo). | **FAILS for cost**: call logs captured token counts, but `request_cost_ledger` = 0 rows and `provider_quota_state` = 0 rows (re-verified today) — it meters nothing about charges. |
| P3 $0 verified pre-run | **NOT VERIFIABLE OFFLINE**: catalog pricing prompt="0"/completion="0" was verified **2026-10-14** for exactly one pin (`dots-studio/dots-3-note-preview:free`, pilot memo §2). Price is a day-of fact; the protocol requires fresh pre-run evidence in the run manifest (E1/E2). | n/a | **FAILS as evidence**: gateway proves nothing about charges (pilot memo §5). |
| P4 no silent fallback | **NOT VERIFIABLE OFFLINE**: nothing local proves provider-side routing behavior. It is *detectable* per call at runtime (response `model` field vs pin) — execution check E4. `or_chat.py` performs no such check today. | n/a | Mixed and moot: gateway logs showed no fallback on the pilot's pinned calls, but `auto/best-free` fallback behavior is on the setup record; route forbidden regardless. |
| P5 ceilings enforceable | **FAILS in existing tooling / repaired at plan level only**: nothing anywhere enforces caps — no call counting, token accumulation, or wall-clock stop exists. The pre-dispatch plan guard supplied in §4 checks a *declared* plan; runtime enforcement is absent (B2). | n/a | **FAILS**: local key carries no USD cap and no request cap (pilot memo §1). |
| P6 retention & credentials | **Credentials VERIFIED**: surrogate-only, host-restricted to `openrouter.ai` (connector doc + `or_chat.py` code). **Retention UNKNOWN, low materiality**: the prompts are frozen *public* repo artifacts (fact sheet + seed prompts), so no private content is sent; provider-side retention is not determinable from local evidence. Run outputs remain local by design. | n/a | **FAILS**: prompts/responses persisted in cleartext on disk; non-loopback bind. Synthetic/public-only inputs were the pilot's mitigation. |

## 4. Pre-dispatch guard check of the frozen package + defects

Checked: `comparison_protocol.json` (`cd24182f…`), `resource_ledger_schema.json`
(`090145e5…`), `tools/validate_and_grade.py` (`0c331f71…`), `seed_prompts.md`
(`6b48da92…`), `grader_packet.md`.

- The frozen package states P1–P5 as **prose + schema only**. The ledger schema
  carries `cost_verified_zero_incremental` as a boolean with the note "Must be
  true before any call is made" — but **no code checks any pin requirement before
  dispatch**. The grader validates/grades cards *after* generation.
  → **Defect D-R2-01** (new, recorded here): no fail-closed pre-dispatch guard.
- **Bounded isolated repair (the one allowed, ≈10 min):**
  `issue9_route_readiness_20261014/tools/preflight_guard.py` (sha256 `bdfeffce…`)
  — stdlib-only, offline, makes no calls. It evaluates a proposed dispatch packet
  (pin, metering declaration, cost evidence, routing, plan vs frozen caps,
  registered prompt hashes, ledger-sample continuity, blinding preconditions) and
  returns PASS/BLOCK with stable reason codes. A PASS means only "the declared
  plan violates no offline-checkable rule" — it does not verify the route.
  The frozen protocol was **not** modified.
- **Defect D-R2-02** (new, recorded, **not** repaired — repair belongs to an
  execution build under a GO): `or_chat.py` line 45,
  `text = msg.get("content") or msg.get("reasoning") or ""`, silently substitutes
  reasoning text when content is empty — masking the pilot's exact failure mode
  (HTTP 200, empty content) and risking reasoning traces leaking into candidate
  cards. The same script enforces no ceilings, writes no ledger, and checks
  neither pin nor response-model identity. ** `or_chat.py` as-is is not a safe
  execution harness.**

## 5. Offline fixtures for the nine failure modes (spec §2)

`issue9_route_readiness_20261014/fixtures/preflight_fixtures.json` (sha256
`69ecfa45…`): 11 fully synthetic packets — 1 clean control + the nine spec modes
(price split into nonzero and unknown). Guard run
(`preflight_fixture_results.json`, sha256 `1f721f9f…`), exit 0, **11/11 as
expected**:

| Fixture | Mode | Guard |
|---|---|---|
| F0 | clean control | PASS |
| F1 | missing usage | BLOCK · METERING_MISSING |
| F2 | nonzero price | BLOCK · PRICE_NONZERO |
| F2b | unknown price | BLOCK · PRICE_UNKNOWN |
| F3 | model alias substitution (Arm B pin swapped to `auto/best-free`) | BLOCK · PIN_ARM_MISMATCH |
| F4 | fallback declared | BLOCK · FALLBACK_ALLOWED |
| F5 | token-cap overrun (120,001) | BLOCK · CEILING_TOKENS |
| F6 | ledger discontinuity (call_index gap) | BLOCK · LEDGER_DISCONTINUITY |
| F7 | unmetered reasoning | BLOCK · REASONING_UNMETERED |
| F8 | prompt contamination (unregistered hash + cross-arm material) | BLOCK · PROMPT_CONTAMINATION |
| F9 | blinding failure (key holder = grader) | BLOCK · BLINDING_FAILURE |

## 6. Execution-day checklist + STOP-before-first-call tree + proposed envelope

### Execution-time checks that remain (none can be done offline)
- **E1** Same-day catalog fetch for the chosen pin: pricing prompt/completion
  exactly "0"; model id + version recorded in the run manifest.
- **E2** Account evidence on the day: key usage/limit and remaining free-quota ≥
  planned calls for that day (documented cap: 50 req/day for free models).
- **E3** Pre-dispatch guard run on the real dispatch packet → must PASS.
- **E4** First-call probe (inside run budget): assert the response carries
  input/output/reasoning usage fields, response `model` == pin, and **non-empty
  content** (pilot lesson). Any failure → STOP; no second call.
- **E5** Per-call, in the harness: append usage to the ledger immediately; enforce
  running billed-token, call-count, and wall-clock caps; any response `model` ≠
  pin → void the arm-seed, stop the run for adjudication.
- **E6** Seed-order coin recorded + hashed in the manifest before the first call;
  arm outputs sealed (hashed) before the other arm starts.
- **E7** Blinding: anonymizer ≠ grader; score-sheet hash recorded before the
  blinding key is opened (grader_packet hash-order rule).
- **E8** Post-run account check: usage delta = $0.00; any nonzero charge is an
  immediate-stop condition already breached — report, do not continue.

### STOP-before-first-call decision tree
1. Pin named (one exact model/provider/version, same both arms)? **No → STOP.**
2. E1 catalog pricing exactly 0/0 for that pin, fetched today? **No/unknown → STOP.**
3. E2 quota headroom ≥ today's planned calls? **No → STOP (reschedule; never raise caps).**
4. Metering declaration: usage incl. reasoning tokens exposed for this pin? **No → STOP.**
5. Routing: fallback disabled, no gateway (OmniRoute forbidden), route = OpenRouter direct only? **No → STOP.**
6. Runtime harness present (ledger + caps + E4/E5 assertions; NOT bare `or_chat.py`)? **No → STOP.**
7. Pre-dispatch guard PASS on the real packet + coin hashed (E6)? **No → STOP.**
8. All yes → the run may start **only under the execution GO**; E4 gates call #2.

### Proposed run envelope (exactly the frozen caps; nothing enlarged)
- Route: **R1 OpenRouter direct via vault surrogate only.** Same model both arms.
- Per arm-seed: ≤120,000 billed tokens (reasoning counted in full), calls A≤8 /
  B≤16, ≤45 min wall, ≤8 cards, **$0.00** incremental.
- Run totals (worst case): 6 arm-seeds, ≤720,000 billed tokens, ≤72 calls,
  auditor review ≤120 min per seed pair (≤360 total).
- Nominal call estimate: A = 2/seed (propose + self-critique), B = 5–9/seed →
  ≈21–33 calls total, inside one day's documented 50-request free quota.
  Worst-case 72 calls exceeds one day's quota → schedule across days (wall caps
  are per arm-seed, so this stays inside the protocol) or hard-stop at quota.
- Preserved unchanged: family-level multiple-testing ledger, killed-family dedup
  (registry export `9e06c27c…`), blinded 5-gate rubric, stop conditions, and the
  protocol's decisive/inconclusive rules.

## 7. Status and blockers

**BLOCKED.** The route family (R1) is the sole surviving candidate and its
metering mechanism is genuinely evidenced — but readiness fails today on:

- **B1 — No qualifying pin exists in local evidence.** The only model with local
  $0 catalog evidence (`dots-studio/dots-3-note-preview:free`, 2026-10-14) is the
  reasoning model that returned **empty content on 3/3 pilot jobs** at a 700-token
  completion cap (pilot memo §3). No other model has local $0 evidence. A pin
  must be selected and price-verified on execution day; that evidence does not
  exist today and cannot be created offline without violating the zero-call scope.
- **B2 — No runtime enforcement harness exists.** Ceilings, ledger capture,
  pin/response-model checks, and the non-empty-content assertion are all absent
  from the only direct-route client (D-R2-02). The §4 guard covers plan-level
  checks only. Building the harness is execution work under a GO.
- **B3 — Day-of verifications E1/E2/E4/E8 are inherently execution-time.** The
  protocol itself makes $0 verification a pre-run act with evidence in the run
  manifest; no offline artifact can substitute, and none is claimed to.

Claude direct **FAILS** P2; OmniRoute is **FORBIDDEN** and additionally FAILS
P2(cost)/P5/P6; MiroFish is not a route. None of these soften B1–B3.

## 8. Exact next user-only execution decision

**Mike (with ChatGPT review of this packet): issue or withhold the separate
Issue #9 execution GO.** A GO must: (a) name the single model pin — or direct pin
selection as the run's first gated step, with same-day $0 catalog evidence (E1)
as a hard precondition; (b) authorize building the runtime enforcement harness
(ledger + ceilings + E4/E5 assertions) before any comparison call; (c) accept
the frozen envelope in §6 unchanged. **Without the GO, no provider/model call of
any kind is authorized, and this packet changes nothing about that.**

## 9. Trial / failure accounting for this task

- Reads: spec comment via public GitHub API (5 page fetches, unauthenticated,
  brief-sanctioned); protocol, ledger schema, grader, seed prompts, grader
  packet, prep memo, pilot memo + results.json, connector doc, `or_chat.py`,
  `or_models.py`; 3 read-only SQLite queries (table list, `PRAGMA`, row counts
  on `request_cost_ledger` / `provider_quota_state` / `call_logs`) — no
  credential rows read, no key material printed anywhere.
- Verifications: prep manifest **16/16 OK** (an initial check from the wrong
  working directory reported 0 OK — a path artifact of repo-root-relative
  manifest entries, resolved by re-running from repo root; no file mismatched).
- Fixture trials: 11 synthetic packets through the new guard — 11/11 expected
  outcomes, 0 unexpected. Failures *found*: D-R2-01 (repaired in isolation),
  D-R2-02 (recorded). Failures *of this task*: none outstanding.
- Zero provider/model calls · zero spend · zero installs · zero config changes ·
  zero production files touched · live harness/state untouched.

## 10. Pins (sha256)

- Spec: Issue #1 comment `6180132721` (2026-10-14T22:42:23Z); prep commit `8675638`;
  repo HEAD at writing `28927de58a9daf0dedb3cd480c2fb21a2053d3e1`.
- Prep memo `01ce058c0171e16473a62c3bebd94a6d5830445698a3d347e506b83efe9758c2` ·
  protocol `cd24182f59183711a4dcd82cd5ca8652dae69d161d1fddf96c7f81546f39bd26` ·
  ledger schema `090145e5d18b550a801694c8c7a5903e6e06f31a876d91127f69819970c73f7e` ·
  grader `0c331f713fb4560397ff4f11475e9e88a37858f15eeb837a4394df0e118eed7a` ·
  seed prompts `6b48da92bceee837923d9443b8757f6be3a95bc16dc893a8039eaa79d6319487`.
- Pilot memo `50ae59ca4e9b320c390c5cc90287b03bf725083d6c544c733d602503c4f67ad8` ·
  pilot results `707db1f93fef4e61f31c85fccdb11ab788d6d4b8d150baf6a979039d62e3e141`.
- Connector doc `92a0d29a30c248cdf1a6c36ef9326ad9c0b34cfff36e34a6beda1a739e64d100` ·
  `or_chat.py` `512f9770f72b1f859a744583263aa5f3d76e04cdec00eeaf76aa5a974483c428` ·
  `or_models.py` `66ac451e626a37bcab3f945b8a2f9d9c9fb94256cc59653bf12fb935e1e5b5e2`.
- This package: guard `bdfeffce906c0d1061cf2752bd6ecd50916399a4ec3021c18b13f3f5545115c5` ·
  fixtures `69ecfa45ac550c06a81100eb6a41267a1dee352d2540361728902adece48f348` ·
  fixture results `1f721f9fe8b3ecdd59ef6332400e83619d2a945974b182fb6fedba982f2ae28a` ·
  full manifest in `issue9_route_readiness_20261014/SHA256_MANIFEST.txt`.

— Muse
