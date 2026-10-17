# QF-TD-GATE3-ATTESTATION-POLICY-20261017-10 r1 — Gate-3 attestation policy

**Verdict: `GATE3_POLICY_A_ONLY_USER_DECISION_REQUIRED`** — the offline evidence contract is fully specified and the patched gate candidate passes its repeated offline matrices, but the only policy that preserves the frozen 51-request full-manifest qualification is **Policy A (52-credit ceiling)**, which raises the standing 51-credit ceiling by 1 and therefore requires **Mike's explicit GO**. No live call was made or authorized by this round. (Spec acceptance label "offline policy PASS" is met for the evidence contract itself: every required gate-3 fact is documented or mechanically derived — see clause labels; the execution-policy choice is the user decision the spec itself reserves.)

Spec: Issue #1 comment `6232499511` (fetched via the public API first, followed exactly). Bases: `0a410ab` (-09), `9474400` (-08); r3 gate pin `8564b2da…` untouched; live ledger byte-identical `7e5ccef0…` (never written).

## Field map & contract (detail: `evidence_map.json`)

Documented `/api_usage` response: `{timestamp, current_usage, plan_limit, daily_usage, plan_daily_limit, plan_category}`, cost **1 credit/request** (vendor docs; preserved snapshot -09 `endpoint_proof.json` sha256 `4c898a28…`; re-read in this pass; pricing page retrieved 2026-10-17T09:59Z documents the 8/min, 800/day tier the program record names "Basic").

| Gate-3 clause | Label | Mechanism |
|---|---|---|
| Freshness | documented | `timestamp` (UTC default) vs packet max-age 3600 s |
| Plan identity/entitlement | derived with formula | joint limit pair `plan_limit==8` AND `plan_daily_limit==800` identifies the tier; `plan_category` recorded only — its value vocabulary is documented by a single example ("enterprise"), so a literal "Basic" match would be name inference, which the spec forbids |
| Standing | derived (availability form) / unattestable (billing-state form) | per spec step 3's allowed alternative: a schema-complete success response under documented error semantics (401/403/429) attests key validity + entitlement + not-rate-limited; no documented route attests standing as a distinct state, and none is claimed |
| Daily capacity | derived with formula | `daily_remaining = plan_daily_limit − daily_usage`, cross-checked `daily_usage ≥ ledger same-day reservations` |
| Minute capacity | derived with formula | `plan_limit==8` + `current_usage < plan_limit` (headroom ≥ 1); no named minute-cap field exists |
| Failure semantics | documented | error body `{code,message,status}` → FAIL; absent/ill-typed fields → UNKNOWN |

Candidate routes enumerated: `/api_usage` (only documented route), dashboard (not machine-attestable), market-data endpoints (no counters; dual-use rejected — an `/api_usage` response contains no market data and cannot be a manifest observation, and no preserved authorized response carries capacity counters).

## Arithmetic (spec step 4)

The status request consumes 1 credit from the same daily pool; whether its response self-counts that credit is **not documented**, so the gate conservatively assumes it does **not**. Qualification of an unchanged 51-request manifest on the same day therefore necessarily requires reported `daily_remaining ≥ 52` at check time (1 + 51). The -07-conserved ledger's 8 credits sit under 2026-10-14; a fresh run day starts at 0 local reservations, and the gate fails closed if the vendor's `daily_usage` ever reads below the ledger's same-day reservations. The status request is conservatively assumed to also occupy one minute credit; run pacing stays with the limiter.

## Frozen policy candidates (canonical-JSON digests)

- **Policy A** — `policy_A.json`, canonical digest `5d9d82ca3e1c867e3f38dcb7f50cd7f372c793048d21232608f7835467d26cde`: ceiling **52** ($0) = 1 status + unchanged 51-request manifest. **User-only ceiling decision.**
- **Policy B** — `policy_B.json`, canonical digest `781f1239ac94af7e63cd16ca0d044126837d746f1076555cd21d7210acee4e91`: ceiling **51** preserved; data budget ≤ 50 → **invalidates the full-manifest qualification**. Prior-day check (freshness/day-scope), post-run check (gate is pre-dispatch), second pool (none documented), and dual-use (no market data in the response) are each rejected with reasons inside the policy object. Policy B is frozen as a documented dead end, not a fiction of viability.

## Gate patch (offline candidate only)

`gate3_policy_candidate.py` — candidate replacement body for r3 gate 3 with the same verdict interface; validates the documented schema + formulas under the packet's policy switch; the r3 original and all prior candidates are byte-identical (nothing edited in place, nothing adopted/merged).

Tests (`run_gate3_policy_tests.py`, fixed injected clock, deterministic): **27 cases** — A boundaries at remaining 50/51/52/53; B boundaries 50/51/52; stale + future timestamps; wrong-tier limits (documented enterprise example pair; daily-only mismatch); minute exhausted; inconsistent counters (over-limit daily/minute, negative, vendor-vs-ledger contradiction, and the consistent-ledger control); documented error bodies 401/429; absent fields (`plan_limit`, `plan_category`, empty response); float counter / unparseable timestamp; cost-budget mismatch both directions; category-recorded-not-proving control. Run twice under `unshare -n`: **27/27, 0 failures, matrices byte-identical**, sha256 `293e42757787f484ee80…`.

## Decision card

`USER_DECISION_CARD.md` in this package — Policy A is the only valid path, so the card goes to Mike: GO for a 52-credit ceiling (1 status + 51 data, $0) on the screen day, or the screen stays parked at this gate. The extra credit was **not** spent.

## Scope

Offline/public-documentation only: zero authenticated requests, zero helper invocations, zero credits, zero ledger writes, zero token/namespace/install/spend, zero backtest/production/Issue #9 work; all prior packages byte-identical. Elapsed ≈14 min of ≤25; repair used: none (0 min).

*— Muse*
