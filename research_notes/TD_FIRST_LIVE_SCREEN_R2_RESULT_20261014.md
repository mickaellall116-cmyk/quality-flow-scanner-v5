# TD First Live Screen — Result R2: DISPATCHED, NON-COMPLETE (venue binding HOLD)

**Task:** QF-TD-FIRST-LIVE-SCREEN-20261014-09 r2 — re-execution of the
first live Twelve Data screen via unblock option (a).
**Authorization / basis chain:**
- Mike authorized r1 in the main chat, 2026-10-14 ~09:25 EDT ("I
  authorize QF-TD-FIRST-LIVE-SCREEN-20261014-09 r1 exactly as
  specified" / "Run the one-credit AAPL screen now").
- r1 ABORTED PRE-DISPATCH with zero network attempts and zero credits
  (result commit `df11c4a`): the ambient `*_proxy` URL for
  `hatch-egress-proxy:3128` carries embedded userinfo, and the
  candidate adapter rejects credential-bearing proxy URLs by design
  (`proxy_credentials_rejected`).
- Mike was presented unblock options (a)/(b), told re-issue needed his
  fresh word, and delegated the choice in the main chat, 2026-10-14
  ~09:35 EDT: **"Do whats best"**. The parent agent chose **option
  (a)** — dispatch-context proxy configuration only.
- Parent-verified diagnostic (pre-r2, non-vendor): a CONNECT
  handshake to `example.com:443` through
  `http://hatch-egress-proxy:3128` with NO Proxy-Authorization
  returned `HTTP/1.1 200 Connection Established` — the sanctioned
  proxy accepts tunnels in the credential-free form documented in
  -06/-07.
**Executed by:** Muse (subagent), 2026-10-14. Pre-dispatch checks
~09:37 EDT; the single dispatch ran **09:38:19 EDT** (13:38:19Z).

## Verdict: DISPATCHED — exactly one request, one credit — outcome NON-COMPLETE

The screen's one request was dispatched through the candidate's
production path (vault surrogate → CONNECT proxy → collector) and the
vendor answered. The collector then **fail-closed on venue identity
binding** and placed the run on HOLD:

> **HOLD: venue binding mismatch for REQ-P1H-01**

Per the task's absolute rules, that outcome is terminal for this
task: **no retry, no second dispatch, no repair-and-rerun** was made
or attempted. Exactly **1 credit** was spent (ledger reservation
granted and recorded by the harness limiter itself).

## What the outcome proves — and what it does not

The collector's response handler checks, in order: HTTP status →
JSON parse → payload `status == "ok"` → meta symbol/interval binding
→ **venue binding** → bar validation. The HOLD fired at the venue
step, so every earlier gate passed:

- The request traversed the credential-free CONNECT proxy and
  reached the vendor; the vendor returned **HTTP 200** with a
  parseable, `status: "ok"` payload whose meta **symbol (AAPL) and
  interval (1h) bound correctly** to the manifest identity.
- A status-ok authenticated response is the first on-the-wire
  evidence that **Sentinel surrogate substitution works on this
  path**: the adapter sent only the `hsurr:*` surrogate as `apikey`;
  a verbatim surrogate would not have produced an authenticated
  status-ok response. (Statement of consistency with the evidence,
  recorded for adjudication — not a broader feed qualification.)
- The response's venue meta (the manifest declares exchange
  `NASDAQ`, mic_code `XNAS`, currency `USD` for REQ-P1H-01) did
  **not** bind to the manifest's `venue_identity` on at least one
  field. Which field differs is recorded only inside the preserved
  private evidence; the collector deliberately reports the category,
  not the values, and no payload values are reproduced here.
- Bar validation never ran (the venue gate precedes it), so **no bar
  count is claimed**. The payload is preserved write-once as
  rejected evidence in the private store (see Dispatch record).

## Candidate (executed from a self-contained `git archive` export of `7ec0f0e`)

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

**No adapter, driver, collector, or candidate byte was changed.**
The only difference from r1 is process environment for the dispatch
process (below).

## Dispatch-context proxy configuration (option (a), the r2 delta)

The single dispatch process — and only it — ran with `http_proxy`,
`https_proxy`, `HTTP_PROXY`, `HTTPS_PROXY`, `all_proxy`, `ALL_PROXY`
all set to exactly `http://hatch-egress-proxy:3128` (credential-free).
All other steps ran under the ambient environment. This is
environment configuration only; the candidate adapter's proxy
resolution (`urllib.request.getproxies()`) consumed it unchanged.
The vault fetch inside the dispatch process is unaffected by proxy
configuration (the sanctioned helper speaks to authd over a Unix
socket).

## Pre-dispatch check results

| Check | Result |
|---|---|
| Component pins vs r2 evidence | **PASS** — all 8 hashes match |
| Single-request manifest (REQ-P1H-01 only) | **PASS** — collector `validate_manifest`: 0 errors (AAPL, 1h, 2026-04-01T00:00:00 → 2026-10-06T23:59:59, America/New_York, outputsize 5000, order asc, adjust=splits, max_attempts=1, credit_weight=1) |
| Collector prerequisites (`check_prerequisites`) | **PASS** — 0 failures: pinned archival sources verify; plan Basic; /time_series = 1 credit/request; retention BOUNDED_RESOLVED with the 30-day condition; interval semantics INSUFFICIENT recorded |
| Vault surrogate | **PASS** — production driver path (`driver.get_api_key()`) retrieved the `custom.twelvedata` entry via the sanctioned dynamic-credentials/authd facility; value is an `hsurr:*` surrogate and placement `query_param=apikey` is enforced inside the driver. The surrogate value was never printed, logged, or written anywhere; the raw key never entered the process |
| Live credit ledger | **PASS** — sha256 `ce515aa6fd53b297b693762e4236b2ea203874641ce745e482ba76daf1a67c59` (pin match); harness limiter daily spent = **0** for 2026-10-14; read-only check left the file byte-identical |
| Retention destination | **PASS** — collector state dir designated inside the git-ignored private store (`research_notes/twelve_data_stage0/snapshots/acquisition_state/`, `git check-ignore` verified); dir did not pre-exist (fresh state) |
| **Dispatch-context proxy (NEW, r2)** | **PASS** — inside the dispatch process, `urllib.request.getproxies()` resolved the https proxy to scheme `http`, host `hatch-egress-proxy`, port `3128`, **userinfo absent** (presence/absence only checked; no values exist in this configuration) |

## Dispatch record

| Field | Value |
|---|---|
| Request | REQ-P1H-01 — **DISPATCHED** (single attempt; lifecycle STARTED attempt=1, 2026-10-14T13:38:19Z) |
| Dispatch timestamp | **2026-10-14 09:38:19 EDT** (13:38:19Z) |
| Network attempts at the vendor | **1** (no retry, no second dispatch process) |
| HTTP status | **200** (established by the collector's validation order: the venue-binding gate is reached only after the non-200, unparseable, API-status, and symbol/interval gates all pass) |
| Outcome classification | **NON-COMPLETE** — collector HOLD: `venue binding mismatch for REQ-P1H-01` |
| Bar count / range | **not claimed** — validation halted at the venue gate, before bar validation |
| Raw payload | Response preserved write-once by the collector as rejected evidence at `…/acquisition_state/receipts/REQ-P1H-01.rejected.bin` inside the git-ignored private store — **117,985 bytes, sha256 `c47bf899422e4585bcd37055c0e9788c96697b6b47482133e4675bf5cb8dbc18`** (hash/bytes only here; payload never printed, logged, or committed) |
| Credit spent | **1** (harness limiter reservation, recorded by the limiter itself) |
| Ledger before | sha256 `ce515aa6…`, day 2026-10-10 record, daily spent for 2026-10-14 = 0 |
| Ledger after | sha256 `4ba4cf6ff91caabab09e60604e8682a3869f7805b83d9a6d4b40c98aebebf494`, day 2026-10-14, **spent = 1**, one window entry at the dispatch epoch |
| Collector state | `pilot_state.json`: status **HOLD**, hold_reason `venue binding mismatch for REQ-P1H-01`, attempts 1, credit_reservations 1, completed [] — the state dir (lifecycle, binding, state, rejected evidence) remains in the private store for adjudication; the collector's started-state reconciliation rules apply to any future run against it |

## What this means / what unblocks

- The r1 blocker is resolved by configuration, not code: the
  sanctioned proxy accepts the credential-free form, and the
  adapter's reviewed rejection of credential-bearing proxy URLs
  stands untouched.
- The screen's decisive question — does Sentinel substitution work
  on the wire — is answered affirmatively by the status-ok
  authenticated response (see above, stated as evidence-consistency
  for adjudication).
- The new blocker is a **manifest-vs-vendor venue-identity
  discrepancy**: the vendor's response meta venue fields do not all
  equal the manifest's declared `{NASDAQ, XNAS, USD}`. Resolution
  paths (for ChatGPT adjudication / Mike's call; **none** taken
  under this task): inspect the preserved private evidence to
  identify the differing field, then either correct the manifest's
  venue declaration via a revised manifest (the collector's frozen
  rule: identity corrections are effected by a revised manifest,
  never by in-run continuation) or record a semantics ruling.
- Any further vendor request — including a re-run of REQ-P1H-01
  under a revised manifest — requires its own fresh authorization.
  This task's one-attempt budget is consumed.

**Scope honored:** exactly one vendor request; one credit; no
retry; no merge; PR #8 untouched; no production/frozen-strategy
changes; no adapter/candidate byte changes; no other vendor calls.
No credential, surrogate, or payload value appears in any artifact
(secret-isolation scan over the deliverables: clean — see evidence).

Evidence: `research_notes/td_first_live_screen_r2_evidence_20261014/`.

**Status: screen EXECUTED — DISPATCHED, NON-COMPLETE (venue binding
HOLD). Live acquisition remains HOLD pending adjudication of the
venue-identity discrepancy and fresh authorization for any further
request.**
