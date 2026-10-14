# OmniRoute Utility Pilot — QF-OMNIROUTE-UTILITY-PILOT-20261014-16 r1

**Scope:** Research-only evaluation of the existing local OmniRoute test instance for low-cost preliminary research, coding assistance, and adversarial review. No integration, no production dependence, no scanner changes. Secondary lane; Twelve Data work unaffected.
**Executed:** 2026-10-14, inspection from 18:59Z, routed calls 19:03:12–19:03:45Z. Total pilot wall time ~6 min of the 45-min cap; active request time 32.9s of the 15-min cap.
**Evidence:** `research_notes/omniroute_utility_pilot_evidence_20261014/` (fixtures + ground truth hashed pre-call, outputs, attempts.json, results.json, evidence_hashes.txt, run_pilot.py).

## 1. Installed configuration (read-only inspection; nothing altered)

- **Version:** OmniRoute **3.8.51** (`node_modules/omniroute/package.json`; wrapper pins `^3.8.51`). Running as a daemon on port 20128 (PID 6242, started 18:05Z by the earlier setup session — this pilot did not start it). Start path: `~/workspace/tools/omniroute/start.sh`.
- **Bind — FINDING:** the daemon listens on **0.0.0.0:20128**, i.e. NOT local-only at the socket level. Mitigations observed: `/v1/*` returns **401** without a valid local API key (verified by unauthenticated probe), and this VM's external reachability is constrained by its NAT/egress setup (not externally probed). Recommendation stands regardless: treat the dashboard/API as LAN-exposed wherever this VM is reachable, or rebind to 127.0.0.1 in any future approved change (none made here).
- **Provider connections: exactly one.** OpenRouter, `auth_type=apikey`, active, `test_status=active`, connection id redacted (`bc7bfb52…`). Per the setup record the stored credential is the vault surrogate (`hsurr:*`), never the raw key; this pilot never read the provider credential. No other providers, accounts, or connections exist.
- **Local API key:** one key, name `claude-test`, prefix `sk-5cd286147…`, active, scopes `["self:usage"]`, `allowed_models=[]` (unrestricted), **no daily USD cap and no per-day request cap set**, `no_log=0` (logging on). The runner read its value in-process from the local DB solely to authenticate to the local gateway; the value appears nowhere in these artifacts.
- **Routing/fallback:** the `combos` table is empty and `activeComboId` is null — no stored routing config. The only fallback behavior on record is the built-in `auto/best-free` combo exercised in the setup session (see §4): it attempted OpenCode first and failed. This pilot pinned an exact model, and the gateway log confirms **no fallback and no model substitution** occurred (resilience_actions empty on all 3 calls).
- **Logging/retention:** `detailedLogsEnabled=true`, `callLogPipelineEnabled=true`; full request/response artifacts are written to `~/.omniroute/call_logs/<date>/` (8 files from setup + 3 from this pilot = 11). Stored settings: `callLogs=90` (retention value as stored), `rawDataRetentionDays=7`, `autoCleanupEnabled=true`. **Cost metering: `request_cost_ledger` contains 0 rows** — OmniRoute records no cost for any call made through it here, so the gateway itself proves nothing about charges (the canonical task's warning is confirmed empirically). `provider_quota_state` is also empty: no quota tracking for the OpenRouter connection.

## 2. Zero-charge proof (gate before any call)

The only route with any working evidence is OpenRouter. The pinned model is **`dots-studio/dots-3-note-preview:free`**. OpenRouter's public catalog entry for this exact model id (fetched 2026-10-14 from `/api/v1/models`) lists pricing **prompt = "0", completion = "0"** (context 512k). Zero incremental charge is therefore established by construction for this pin, and only for this pin. No other route is demonstrably no-charge, and none was called.

## 3. Head-to-head (identical prompts, synthetic/public-style fixtures only)

Design note: no abstract was supplied with the task, so the "supplied public abstract" and the other two fixtures were authored as synthetic fixtures (labeled as such in the files) with pre-written ground truth, hashed before any call (19:02Z). The baseline route is the executing agent (Muse) answering the identical prompts directly — the current single-model route — consuming 0 API requests; baseline outputs were written and hashed **before** the routed calls. Routed params pinned: model above, temperature 0, max_tokens 700 (hard cap per task). **3 of 6 budgeted requests used; 0 retries; 0 fallbacks.**

| Item | Route | HTTP | Latency | Tokens in/out (reasoning) | Result |
|---|---|---|---|---|---|
| (a) Extract 2 falsifiable questions + nulls + data needs | OmniRoute→OpenRouter free | 200 | 11.1s | 244 / 700 (817) | **FAIL — empty output** |
| (b) Review toy DST-bug function | OmniRoute→OpenRouter free | 200 | 10.2s | 115 / 700 (721) | **FAIL — empty output** |
| (c) Adversarial critique of fabricated backtest claim | OmniRoute→OpenRouter free | 200 | 11.4s | 226 / 700 (758) | **FAIL — empty output** |
| (a) | Claude direct | — | — | — | **PASS** (2 falsifiable questions, explicit nulls, series/frequency/sample specified, 0 invented facts) |
| (b) | Claude direct | — | — | — | **PASS** (fixed-offset DST bug; example mechanically verified: toy returns 09:00 for 2026-07-01T14:00Z vs correct 10:00 EDT; zoneinfo fix) |
| (c) | Claude direct | — | — | — | **PASS** (leakage, multiple-testing over 240 trials, survivorship, gross-of-cost, in-sample-as-live all caught; actionable evidence requirements; 0 invented facts) |

**Failure mode (the pilot's central finding):** the pinned free model is a *reasoning* model. On all three jobs it consumed the entire 700-token completion budget as internal reasoning (721–817 reasoning tokens), hit `finish_reason="length"`, and returned `choices[0].message.content` **null** — the omni_*.md output files hash to the SHA-256 of the empty string. The saved reasoning traces show the model was on track (item b's trace names the fixed-offset bug and drafts the `ZoneInfo` fix; item c's trace reaches survivorship bias) but no final answer was ever emitted in the channel an OpenAI-compatible consumer reads. HTTP 200 at the gateway therefore does **not** mean a usable answer — any future route acceptance test must assert non-empty content, not status.

**Scoring method:** executing agent against the pre-written fixture ground truth (fixture check, in results.json) — not model self-grading. Invented facts: 0 in Claude outputs; 0 in routed delivered content (vacuously — nothing was delivered). Secret hygiene: PASS for both routes (fixtures contained no secrets; no credential-like content in any output or trace). Reproducibility: pins and parameters recorded; the routed failure is cap-dependent and would likely reproduce deterministically at this cap. Limitation: the scorer was not blinded to route identity; the routed verdicts are nonetheless unambiguous (empty outputs).

**Budget discipline:** the remaining 3 requests were deliberately **not** spent. There is no second working OmniRoute route to test, and re-running the same items with a larger token cap would be a retry of the measurement, which the task forbids. Actual charge: **$0** (zero-priced catalog model; 2,685 total tokens). Rate/quota effects: none observed; free-model account-level rate limits are not visible from the gateway and were not measured.

## 4. Prior setup evidence (reused per task step 5 — not repeated)

Setup session 2026-10-14 18:06–18:10Z, from OmniRoute call_logs (8 attempts): `opencode/big-pickle` via `auto/best-free` → **403** (OpenCode free tier is client-locked — catalog caveat CONFIRMED); `cloudflare-playground` Llama-3.3-70B → **502 ×2** (browser binary missing — caveat CONFIRMED); `uncloseai` Qwen3.6 → **499** (aborted at 90s); `zcode/glm-4.7-flash` → **502 ×2** (binary not installed); `openrouter/dots-studio/dots-3-note-preview:free` → **200** (22 in / 46 out, 2.8s) — the sole working route and the basis for this pilot's pin. Provider availability in OmniRoute's catalog is not a guarantee of a working route: 4 of 5 zero-config routes failed outright.

## 5. Conclusions — cheapest reliable route per job

- **(a) Research-question extraction, (b) code review, (c) adversarial critique: Claude direct remains the only reliable route** for all three jobs and the cheapest *working* one (no per-request charge; complete, ground-truth-passing outputs).
- **OmniRoute → OpenRouter free pin is NOT recommended as configured.** It is genuinely zero-charge but delivered zero usable output on 3/3 jobs under a hard token cap, because the pinned model spends its budget reasoning. "Free" routes that return empty content are not a cost saving; they are a latency cost (~11s per call here).
- **Preconditions for any future retest (new task, not executed here):** pin a non-reasoning free model OR raise the completion cap well above the model's typical reasoning length (traces suggest ≥2,500 tokens) with an explicit non-empty-content acceptance check; re-verify the exact pin's catalog price is 0 on the day; keep inputs synthetic/public only; count gateway-internal fallbacks from call_logs, not from client responses.
- **Do not rely on OmniRoute for cost or quota evidence:** its cost ledger and quota state are empty for this connection. Cost claims must come from provider-side catalog/account data.
- **Security note for any continued use:** the 0.0.0.0 bind (§1) plus full request/response artifact logging means prompts sent through this gateway are persisted on disk in cleartext under `~/.omniroute/call_logs/`. Keep the synthetic/public-only input rule until both are addressed by an approved change.

## 6. Rollback

Nothing to roll back: no OmniRoute configuration was created, altered, or deleted by this pilot; no scanner code, production config, or frozen artifact was touched; the only writes are this memo and its evidence directory under `research_notes/`, plus the gateway's own call logs for the 3 calls. OmniRoute remains a standalone local test daemon that nothing depends on; leaving it running or stopping it has no effect on the Quality Flow system.

*No claim is made that OmniRoute gives ChatGPT direct access to Muse's runtime; it does not. This memo evaluates a local gateway only.*
