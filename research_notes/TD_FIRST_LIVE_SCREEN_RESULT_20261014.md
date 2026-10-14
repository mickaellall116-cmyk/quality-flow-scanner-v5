# TD First Live Screen — Result: ABORTED PRE-DISPATCH (proxy gate)

**Task:** QF-TD-FIRST-LIVE-SCREEN-20261014-09 r1 (ChatGPT assignment,
Issue #1 comment 6164534553; candidate SCOPED PASS).
**Authorization anchor:** Mike, main chat, 2026-10-14 ~09:25 EDT —
"I authorize QF-TD-FIRST-LIVE-SCREEN-20261014-09 r1 exactly as
specified" / "Run the one-credit AAPL screen now".
**Executed by:** Muse (subagent), 2026-10-14. Pre-dispatch checks ran
~09:27–09:28 EDT; abort declared 09:28:49 EDT (13:28:49Z).

## Verdict: ABORTED PRE-DISPATCH — the one request was NEVER dispatched

The task's pre-dispatch stop rule fired on the proxy gate. **Zero
vendor contact of any kind occurred** — no TCP connection to the
vendor, no HTTP request, no credit consumed. The "exactly one attempt"
budget is untouched (no attempt exists). No retry, no repair, no
fallback was attempted, per spec.

**Exact failure:** in this execution environment, the proxy URL that
the platform mechanism (`urllib.request.getproxies()`, key `https`)
resolves carries **embedded userinfo** (a username and a password are
present in the URL; the values are deliberately not recorded anywhere).
The candidate adapter rejects credential-bearing proxy URLs **by
design** (adapter v1.1.0, `_resolve_proxy`): they are never used,
propagated, or recorded, and there is no direct fallback for
surrogate requests. Proven through the candidate's own code, locally,
before any connection object existed: `_resolve_proxy()` raises the
sanitized TransportError category **`proxy_credentials_rejected`**.

Had the run proceeded anyway, the collector would have reserved the
credit in the ledger and emitted STARTED, then HOLDed on the transport
error — spending the ledger reservation with zero vendor contact and
leaving an ambiguous started-without-receipt state. The pre-dispatch
abort exists precisely to prevent that.

## Candidate (executed from a self-contained `git archive` export)

| Component | Pin (sha256) | Verified |
|---|---|---|
| Candidate commit | `7ec0f0efce7d9ce668233bf8ee55d7503ec47c0a` (branch `td-combined-candidate-20261014`) | ✓ export |
| Adapter `td_http_transport_adapter.py` | `ae8f4837b3d11a53990cfd56f207d5ec96c40b8fe4c1280f15fb08452cc43343` | ✓ |
| Driver `driver.py` | `671f4d0ce25a76bc4967f1ca8cbb16fcda037f0e0ce71529c2aa385dce33fed1` | ✓ |
| Collector `td_min_collector.py` | `bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b` | ✓ |
| Limiter `rate_limiter.py` | `06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64` | ✓ |
| `validate_input.py` / `verify_sources.py` | `1b83cdcd…` / `a0bd2e4c…` | ✓ |
| Manifest TD-ACQUISITION-MANIFEST-V1-20261013 | `66a31e10aca1ca5f8af66139c4ff30a68cfef1c1138156eae103d8cf77e44f12` | ✓ |
| Adapter contract | `db6c44a2c95254fcc46d3c2717b682e00b33aa70fc563f8e86557dbca852a1f5` | ✓ |

## Pre-dispatch check results

| Check | Result |
|---|---|
| Component pins vs r2 evidence | **PASS** — all 8 hashes match |
| Single-request manifest (REQ-P1H-01 only) | **PASS** — collector `validate_manifest`: 0 errors (AAPL, 1h, 2026-04-01T00:00:00 → 2026-10-06T23:59:59, America/New_York, outputsize 5000, order asc, adjust=splits, max_attempts=1, credit_weight=1) |
| Collector prerequisites (`check_prerequisites`) | **PASS** — 0 failures: pinned archival sources verify; plan Basic; /time_series = 1 credit/request; retention BOUNDED_RESOLVED with the 30-day condition; interval semantics INSUFFICIENT recorded |
| Vault surrogate | **PASS** — production driver path (`driver.get_api_key()`) retrieved the `custom.twelvedata` entry via the sanctioned dynamic-credentials/authd facility; value is an `hsurr:*` surrogate and placement `query_param=apikey` is enforced inside the driver. The surrogate value was never printed, logged, or written anywhere; the raw key never entered the process |
| Proxy route | **FAIL → ABORT** — resolved via `getproxies()`; scheme http, host present, port present, but **credentials present** in the URL → adapter category `proxy_credentials_rejected` (confirmed by direct call into the candidate adapter's `_resolve_proxy`, dummy in-memory probe string, no connection created) |
| Live credit ledger | **PASS** — sha256 `ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59` (pin match); harness limiter reports daily spent = **0** for 2026-10-14; a read-only check left the file byte-identical |
| Retention destination | **PASS** — collector state dir designated inside the git-ignored private store (`research_notes/twelve_data_stage0/snapshots/acquisition_state/`, `git check-ignore` verified); dir did not pre-exist (fresh state) and was **not** created, since dispatch never occurred |

## Dispatch record

| Field | Value |
|---|---|
| Request | REQ-P1H-01 — NOT DISPATCHED |
| Dispatch timestamp (ET) | none — aborted 2026-10-14 09:28:49 EDT, pre-dispatch |
| HTTP status | none (no request) |
| Outcome classification | **ABORTED PRE-DISPATCH** (proxy gate) — not a COMPLETE/non-COMPLETE response outcome; no response exists |
| Bar count / range | n/a |
| Raw payload | none received; nothing stored |
| Credit spent | **0** |
| Ledger before | sha256 `ce515aa6…`, daily spent 0 |
| Ledger after | sha256 `ce515aa6…` — **byte-identical**, daily spent 0 (no reservation was granted; per the limiter's own conventions an ungranted reservation writes nothing — the abort is recorded here and in the evidence, not by hand-editing limiter state) |
| Collector state dir | never created; private store untouched (only the two pre-existing Stage-0 snapshot files remain) |

## What this means / what unblocks

- This is an **environment/configuration mismatch**, not a vendor,
  credential, or data failure: the -06/-07 work documented the
  sanctioned proxy in credential-free form, but the proxy URL this
  execution environment actually hands to `getproxies()` carries
  embedded userinfo, and the accepted adapter — deliberately, as a
  reviewed security property — refuses that form.
- Resolution paths (for ChatGPT adjudication / Mike's call; **none**
  taken under this task): (a) run the dispatch from an environment
  whose `*_proxy` configuration is credential-free, matching the
  form the adapter was reviewed against; or (b) a separately
  reviewed adapter correction defining how a credential-bearing
  sanctioned-proxy URL is handled. Re-issuing the screen after
  either resolution requires its own authorization.
- Sentinel substitution on the wire remains unproven; nothing about
  this abort is evidence for or against it.

**Scope honored:** zero vendor calls, zero credits, zero spend, no
merge, PR #8 untouched, no production/frozen-strategy changes. The
raw payload does not exist; no credential or surrogate value appears
in any artifact (secret-isolation scan over the deliverables: clean).

Evidence: `research_notes/td_first_live_screen_evidence_20261014/`.

**Status: screen NOT executed — ABORTED PRE-DISPATCH (proxy
credentials gate). Live dispatch remains HOLD pending adjudication
of the resolution path.**
