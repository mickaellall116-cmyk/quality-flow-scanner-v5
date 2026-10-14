# TD V2 SPOT8 Live Screen — Result: EXECUTED, 6/8 COMPLETE, fail-closed HOLD at REQ-SPT-07 (HTTP 400), REQ-SPT-08 NOT ATTEMPTED

**Task:** QF-TD-V2-SPOT8-LIVE-SCREEN-20261014-14 r1 — the authorized
bounded live SPOT batch (canonical text: GitHub Issue #1 comment
`6174336884`).
**Authorization:** Mike's direct reply **"Yea authorize"** (2026-10-14,
recorded in the canonical task text) for exactly eight free Twelve
Data requests, confirmed again by Mike directly in the main chat
("Run the 8-credit spot screen now"); scoped vendor calls are
automatic under Mike's standing rule of the same day.
**Executed by:** Muse (subagent), 2026-10-14. Pre-dispatch checks
~14:09–14:11 EDT; the single batch run executed **14:11:22–14:11:59
EDT** (18:11:22–18:11:59Z), elapsed 36.46 s.

## Verdict: EXECUTED — 7 dispatched of 8 authorized, 7 credits, batch HOLD (fail-closed stop honored)

| Request | Case | Dispatched | HTTP | Classification | Bars |
|---|---|---|---|---|---|
| REQ-SPT-01 AAPL | DST-spring week | yes, 18:11:22Z | 200 | **COMPLETE** | 35/35 |
| REQ-SPT-02 QQQ | DST-spring week | yes, 18:11:31Z | 200 | **COMPLETE** | 35/35 |
| REQ-SPT-03 AAPL | DST-fall week | yes, 18:11:39Z | 200 | **COMPLETE** | 35/35 |
| REQ-SPT-04 QQQ | DST-fall week | yes, 18:11:48Z | 200 | **COMPLETE** | 35/35 |
| REQ-SPT-05 AAPL | early close 2025-11-28 | yes, 18:11:55Z | 200 | **COMPLETE** | 4 (bound 7) |
| REQ-SPT-06 QQQ | early close 2025-11-28 | yes, 18:11:57Z | 200 | **COMPLETE** | 4 (bound 7) |
| REQ-SPT-07 AAPL | closed day 2026-07-03 | yes, 18:11:58Z | **400** | **HOLD** — rejected evidence preserved | 0 |
| REQ-SPT-08 QQQ | closed day 2026-07-03 | **NO** | — | NOT ATTEMPTED (fail-closed stop) | — |

Collector run summary: `dispatched 7, reused 0, completed 6, outcome
"HOLD: HTTP 400 for REQ-SPT-07"`. Exactly one attempt per dispatched
request; no retry, no pagination, no 9th call under any
circumstance; **7 of the 8-credit ceiling consumed** (the unspent
credit is REQ-SPT-08's, never reserved).

## What the results establish

- **Venue identity under V2 binds on the wire.** Every accepted
  receipt's meta matched its V2 pin exactly — AAPL:
  NASDAQ/**XNGS**/USD; QQQ: NASDAQ/**XNMS**/USD (the segment MICs
  that V1 got wrong and V2 corrected). No venue HOLD occurred.
- **DST weeks are clean.** Both the spring-forward week
  (2026-03-09→13) and the fall-back week (2025-11-03→07, EST resumed
  2025-11-02) returned full 35-bar weeks — first bar 09:30, last bar
  15:30 on each of the five sessions — and passed the collector's
  full session_1h validation (which emits the standing
  CONSTRUCTION_HOLD marker per request: the 1H→4H construction leg
  remains held on interval-start semantics INSUFFICIENT, by design —
  it is a marker, not a failure).
- **Early close is exactly as calendared.** 2025-11-28 returned 4
  bars per symbol, 09:30→12:30 (the 13:00 ET early close), inside
  the conservative bound of 7, and passed session_1h validation.
- **A fully-closed single-day window is a vendor HTTP 400, not an
  empty ok.** For 2026-07-03 (Independence Day observed) the vendor
  answered `{"code": 400, "status": "error", "message": "No data is
  available on the specified dates. Try setting different start/end
  dates."}`. The collector preserved the 180-byte body write-once as
  rejected evidence and HOLDed the run. This is now pinned
  empirically as the vendor's closed-day behavior for a zero-bar
  window.
- **REQ-SPT-08's behavior is not evidenced.** It was never
  dispatched; the near-certain inference that QQQ would draw the
  same 400 is recorded as inference only, not evidence. No claim is
  made for it.
- The SPOT8 run state is terminally **HOLD** (`hold_reason: HTTP 400
  for REQ-SPT-07`). Under the collector's frozen rules, REQ-SPT-07
  cannot be re-dispatched from this state (STARTED without durable
  completion reconciles as AMBIGUOUS on any future entry), and any
  further acquisition — REQ-SPT-08, a re-scoped closed-day probe, or
  the full 51-request manifest — requires its own fresh task and
  adjudication. Nothing here promotes any qualification gate; the
  P1–P7 ledger update is the parent's step (facts in the evidence:
  SPOT receipts now exist for 6 of 8 requests, so the -12 "all eight"
  condition for P2 remains unmet).

## Candidate (executed from a self-contained `git archive` export of `b18db3c`)

| Component | Pin (sha256) | Verified |
|---|---|---|
| Candidate commit / tree | `b18db3ce25f3014d11847ba1ac92f488a994022e` / `06b12f82977447934921d82701763251f9373af1` (branch `td-v2-spot-candidate-20261014`) | ✓ |
| Adapter `td_http_transport_adapter.py` | `ae8f4837b3d11a53990cfd56f207d5ec96c40b8fe4c1280f15fb08452cc43343` | ✓ |
| Driver `driver.py` | `671f4d0ce25a76bc4967f1ca8cbb16fcda037f0e0ce71529c2aa385dce33fed1` | ✓ (pin taken from the -12 proof record) |
| Collector `td_min_collector.py` | `bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b` | ✓ |
| Limiter `rate_limiter.py` | `06ad383d856e62d126d1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64` | ✓ |
| `validate_input.py` / `verify_sources.py` | `1b83cdcd…` / `a0bd2e4c…` | ✓ |
| Manifest V2 | `4a6e3a55ba6cacf80d60c26870817a272534d62cd73eb09d1dfc889d571c547d` | ✓ |
| SPOT8 subset (file / canonical digest) | `ddff040f…` / `748ca95789c6f16bab81fbc903fd0c60a890dd2f2e21a63d97ffdb962d70e4fb` | ✓ |
| Adapter contract | `ec877a04d12e6b0c69378dba245be07ab60279a15c9eb78cc50e8b0c705e166b` | ✓ |

Environment: venv built from the candidate's own lock (pandas 2.2.3,
pandas_market_calendars 4.5.1, Python 3.12.3 — identical to -12).
**No candidate, collector, adapter, driver, or manifest byte was
changed.**

## Dispatch context (identical to the -09 r2 proven pattern)

The single dispatch process — and only it — ran with `http_proxy`,
`https_proxy`, `HTTP_PROXY`, `HTTPS_PROXY`, `all_proxy`, `ALL_PROXY`
all set to exactly `http://hatch-egress-proxy:3128`
(credential-free). In-process `getproxies()` check before dispatch:
scheme `http`, host `hatch-egress-proxy`, port `3128`, userinfo
absent — PASS. The vault fetch (authd over a Unix socket) is
unaffected by proxy configuration; the driver retrieved the
`custom.twelvedata` `hsurr:*` surrogate via the production path and
the value was never printed, logged, or written anywhere.

## Pre-dispatch gates (all PASS before the first vendor call)

| Check | Result |
|---|---|
| Component pins (9/9) + candidate tree | **PASS** |
| Subset canonical digest `748ca957…`; subset requests byte-identical copies of V2; budget exactly 8 credits; `max_attempts=1` ×8 | **PASS** |
| Collector `validate_manifest` on the subset | **PASS** — 0 errors |
| Collector `check_prerequisites` | **PASS** — 0 failures against the candidate-pinned package `prerequisites.json` (`038ccaf3…`; the `td_minimal_collector` copy also passes) |
| Vault surrogate via production driver path | **PASS** — `hsurr:*` form verified, value never recorded |
| Live credit ledger | **PASS** — sha256 `4ba4cf6f…` (pin match), day 2026-10-14 spent = 1 (the -09 credit); read-only check non-mutating |
| State isolation | **PASS** — SPOT8 state rooted at a **fresh** dir `…/snapshots/acquisition_state_spot8/` inside the git-ignored private store (`git check-ignore` verified); the -09 P1H HOLD state was never opened by the run |
| No duplicate spend | **PASS** — no REQ-SPT-* id in the live lifecycle; no prior SPOT8 state |
| Benign CONNECT probe (non-vendor, non-credit) | **PASS** — `CONNECT example.com:443` via the credential-free proxy returned `HTTP/1.1 200 Connection Established`, no Proxy-Authorization sent |

## Dispatch record

| Field | Value |
|---|---|
| Run window | 2026-10-14 **14:11:22.74 → 14:11:59.20 EDT** (18:11:22.74Z → 18:11:59.20Z), 36.46 s |
| Network attempts at the vendor | **7** (one per dispatched request; no retries) |
| Credits consumed by this task | **7** of the 8-credit ceiling |
| Ledger before | sha256 `4ba4cf6ff91caabab09e60604e8682a3869f7805b83d9a6d4b40c98aebebf494`, day 2026-10-14, spent = 1 |
| Ledger after | sha256 `7e5ccef0e5fd7e2faa744c8fe7ee646c3162fa4f72fc4a9a85317d52b5d890ed`, day 2026-10-14, **spent = 8** (1 from -09 r2 + 7 from this task; reservations recorded by the harness limiter itself, including the HTTP-400 request, per the pinned budget rule that every dispatch consumes exactly 1 credit reserved in advance) |
| Accepted receipts (private, write-once, git-ignored store) | REQ-SPT-01 `56b8531f…` 4,715 B · REQ-SPT-02 `58c92a5f…` 4,721 B · REQ-SPT-03 `b0adc3ec…` 4,708 B · REQ-SPT-04 `860e55ed…` 4,745 B · REQ-SPT-05 `3746d373…` 697 B · REQ-SPT-06 `7c845cb7…` 688 B — full hashes in the evidence |
| Rejected evidence (private, write-once) | `receipts/REQ-SPT-07.rejected.bin` — 180 bytes, sha256 `3339c34154648c0ea4ddb9bd553e5274d390f953552518ad957d79704b7d5d50`; verified to contain no credential material |
| SPOT8 state | `pilot_state.json` sha256 `80950fcb…`: status **HOLD**, hold_reason `HTTP 400 for REQ-SPT-07`, attempts 7, credit_reservations 7, completed [SPT-01..06]; `lifecycle.jsonl` `04b26958…`; `manifest_binding.json` `10f0c43e…` (digest `748ca957…`) |
| -09 P1H HOLD state | **Byte-identical before/after** (pilot_state `8c59a56c…`, lifecycle `fbdbd1c3…`, binding `324a69ba…`, rejected receipt `c47bf899…`) — undisturbed |

HTTP 200 for REQ-SPT-01..06 is established by the collector's
validation order (the receipt is written and RECEIVED emitted only
after the non-200, unparseable, API-status, meta-binding, and
venue-binding gates all pass); HTTP 400 for REQ-SPT-07 is recorded
directly in the collector's HOLD reason and the preserved error
body.

## Trials, failures, effort (this task)

- Canonical fetch + r2-pattern review (1 pass). Phase A pre-dispatch
  script: first run flagged one pin mismatch — a hand-transcription
  error in the check script's own driver-pin constant (61 vs 64
  chars); the export bytes matched the independently recorded -12
  proof pin exactly, the constant was replaced by the proof-sourced
  value, and the re-run passed 9/9. No candidate byte was ever in
  question and no dispatch depended on the mistyped constant.
- Phase B: proxy check PASS → CONNECT probe PASS → one
  `build_collector` (live ledger, fresh SPOT8 state) → one
  `collector.run()`. No retries, no second run process, no repair
  pass used against the vendor path.
- The single substantive failure is the task's own finding:
  REQ-SPT-07's vendor HTTP 400 on the closed-day window, handled
  exactly as preregistered (evidence preserved, batch stopped,
  REQ-SPT-08 not attempted).

**Scope honored:** only REQ-SPT-01..08 addressed; 7 dispatched; no
additional acquisition; no full-51 run; no 1H→4H construction; no
merge; PR #8 untouched; no production/frozen-strategy changes; no
Tiingo. No credential, surrogate, or raw payload value appears in
any deliverable (secret-isolation scan over the deliverables:
clean — see evidence). Raw receipts remain private in the
git-ignored store.

Evidence: `research_notes/td_v2_spot8_live_screen_evidence_20261014/`
(`pre_dispatch_checks.json`, `dispatch_output.json`,
`receipt_facts.json`, `screen_evidence.json`).

**Status: SPOT screen EXECUTED — 6 COMPLETE / 1 HOLD (vendor HTTP
400, closed-day window) / 1 NOT ATTEMPTED. Qualification remains
HOLD pending independent review of these results.**
