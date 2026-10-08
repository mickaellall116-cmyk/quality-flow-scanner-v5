# Twelve Data Pilot — Prerequisite Check (2026-10-08)

**Packet:** `research_notes/PILOT_EXECUTION_PLAN.md` v7 (retention amendment, 2026-10-08)
**Source adjudications:** ChatGPT 6049455862 (feed-gate adjudication), 6052566220 (retention clarification)
**Scope:** Pre-acquisition prerequisite check ONLY. No vendor call authorized by this document.

## Check results (packet §0 prereq matrix + feed gates P1–P4)

| Prereq | Status | Evidence / note |
|---|---|---|
| Symbol list frozen (20) | ✅ PASS | Packet §1; TWTR documented; DRAM reclassified; SPCX verified |
| Calendar/action identities pinned | ✅ PASS | Packet §2; all dates verified against NYSE calendar / issuer releases |
| Warmup rule pinned | ⚠️ QUALIFIED | §2d; 215 4H bars, archival convention. C2 decision-impact checks remain INSUFFICIENT EVIDENCE unless separately pinned init rule supports them |
| Source identity pinned | ✅ PASS | Packet §4; archival blob SHAs |
| Runnable harness v4 (offline) | ✅ PASS | `research_notes/pilot_harness/`; 50/50 synthetic tests |
| Fail-closed input validator | ✅ PASS | V1–V11; causal as_of; canonical interval ends |
| 1H interval spec | ✅ PASS | Packet §3; one interval contract |
| **C4 retention evidence** | ✅ **BOUNDED RESOLVED (v7)** | Active-account personal/internal retention permitted on Basic; 30-day deletion after termination. Provenance: Mike-supplied Dooz AI-support transcript, user-supplied, NOT independently authenticated. Indefinite post-termination retention: still INSUFFICIENT. |
| Rate limiter v4 (design) | ✅ PASS (design) | Persisted rolling window; midnight-safe; fail-closed ledger. Endpoint weights for `time_series` = 1 credit/symbol (ChatGPT 6049455862, official docs). Corporate-action endpoint weights: **TBD with entitlement evidence BEFORE execution** (packet §5) |
| Credential safety | ✅ PASS | Packet §6; sanitized logging; `custom.twelvedata` in Secure Vault |
| Authorization record | ✅ PASS | memory/2026-10-06.md:1240; Mike 2026-10-06 "just run if chat says" — conditional on ChatGPT spec clearance |
| **P1 feed gate** | ✅ **RESOLVED (public-plan level)** | /time_series = 1 credit/symbol; Basic 8/min, 800/day (ChatGPT 6049455862, official sources). Account screenshot shows Basic/Free subscribed |
| **P2 feed gate** | ⏳ **RESOLVES DURING EXECUTION** | Documentary expectation improves (official history docs support 1h, intraday ~couple years); execution proof for 2026-04-01 coverage on all 20 symbols exists only inside an authorized pilot run — this is what the pilot tests, not a blocker to starting |
| **P3 feed gate** | ✅ **RESOLVED (bounded)** | Active-account personal/internal retention; 30-day deletion after termination (see C4 above) |
| **P4 feed gate / spec clearance** | ⏳ **PENDING — the remaining concrete gate** | ChatGPT must clear the amended spec before the first vendor call. Packet remains FROZEN v7 until then |

## Verdict

**No manufactured HOLD.** Every prerequisite except P4 spec clearance is satisfied or resolves inside the authorized run. The two concrete items named before first acquisition are:

1. **ChatGPT spec clearance (P4)** — the single remaining gate. Vendor execution HOLD stands until reviewer acceptance.
2. **Corporate-action endpoint weights** — name exact weights with entitlement evidence before execution (packet §5; the v2 2-credit assumption was withdrawn).

Mike's direction ("go ahead with free evaluation," relayed via ChatGPT 6052566220) supports the bounded personal/internal pilot once P4 clears. No new paid tier, no automatic commercial/production use. Bounded free personal/internal pilot may proceed once P4 is satisfied, using the v6/v7 frozen harness and fixed sample/budget. First acquisition will report actual request counts, retained hashes, and discrepancies afterward.

**Zero vendor calls made in this check. No acquisition executed.**

## Retention inventory (v7)

Included in the retention envelope: raw request/response snapshots, immutable raw-store backups, shared copies (any copies beyond the primary store). All subject to the 30-day post-termination deletion obligation. Raw licensed data is NEVER published on GitHub/Slack. Only manifests (hashes, timestamps, sanitized params), code, and summaries are published.
