# TD closed-session semantics — design/adjudication memo (QF-TD-CLOSED-SESSION-SEMANTICS-20261014-15 r1)

Date: 2026-10-14. Canonical task: GitHub Issue #1 comment 6175610471 (ChatGPT adjudication of -14, 2026-10-14T18:38:20Z); coordination correction (Slack TS 1792003165.214569) confirms THIS read-only/design-only task is canonical and the live one-credit variant (comment 6175611382) is SUPERSEDED and was NOT executed. Mode: OFFLINE only — zero vendor/auth calls, zero network calls, zero credits, zero spend, no code edits, no manifest edits, no live-state access or mutation. Budget ≤40 min.

## 1. Question

When a preregistered request window falls entirely on exchange-closed days, Twelve Data returns HTTP 400 with an error payload instead of an empty `ok` payload. How should that response be classified, what would satisfy the P2 gate for the closed-day SPOT requests (REQ-SPT-07/08), and should any semantics change exist — as a design determination only?

## 2. Pins (all independently re-verified offline in this task)

| Artifact | Pin |
|---|---|
| Candidate | `b18db3ce25f3014d11847ba1ac92f488a994022e`, tree `06b12f82977447934921d82701763251f9373af1`, ref `refs/heads/td-v2-spot-candidate-20261014` |
| Collector (executed) | `research_notes/td_lifecycle_repair_candidate/td_min_collector.py` @ candidate, sha256 `bd003c3cd5866172c04b0165d6ee60ec16be8487f28e90b4e6e1df046f8d489b` (matches -12 candidate manifest and -14 dispatch table) |
| Adapter (executed) | `research_notes/td_transport_adapter/td_http_transport_adapter.py` @ candidate, sha256 `ae8f4837b3d11a53990cfd56f207d5ec96c40b8fe4c1280f15fb08452cc43343` (matches -14 dispatch table) |
| Manifest V2 | `4a6e3a55ba6cacf80d60c26870817a272534d62cd73eb09d1dfc889d571c547d` |
| Manifest SPOT8 | `ddff040fa654303cf4289f4c39c2a5b5af998bd4065ceddd4e4f5d52fcb8c28d` |
| Manifest V1 | `66a31e10aca1ca5f8af66139c4ff30a68cfef1c1138156eae103d8cf77e44f12` |
| Live credit ledger | `research_notes/pilot_harness/credit_ledger.json` sha256 `7e5ccef0e5fd7e2faa744c8fe7ee646c3162fa4f72fc4a9a85317d52b5d890ed`, day 2026-10-14 spent = 8 |
| SPOT8 state | `acquisition_state_spot8/pilot_state.json` `80950fcb…`, `lifecycle.jsonl` `04b26958…` (terminal HOLD, attempts 7, completed SPT-01..06) |
| SPT-07 rejected evidence | 180 bytes, sha256 `3339c34154648c0ea4ddb9bd553e5274d390f953552518ad957d79704b7d5d50` |
| -09 P1H HOLD state | `pilot_state.json` `8c59a56c…`, `lifecycle.jsonl` `fbdbd1c3…`; rejected receipt `c47bf899422e4585bcd37055c0e9788c96697b6b47482133e4675bf5cb8dbc18` |
| P1–P7 protocol | Frozen 2026-10-13, `research_notes/TD_ACQUISITION_ADAPTER_PREFLIGHT_20261013.md` §5; qualification ledger `research_notes/td_v2_spot_batch_preflight_evidence_20261014/qualification_ledger_p1_p7.json` |
| -14 result | Commit `76459ef`; report `research_notes/TD_V2_SPOT8_LIVE_SCREEN_RESULT_20261014.md` + evidence dir |

## 3. Calendar cross-check — documentary vs empirical vs inferred

**Documentary (pinned mechanism).** Session truth in this codebase is `research_notes/pilot_harness/validate_input.py::xnys_schedule(day)`, which resolves each date through `pandas_market_calendars` calendar `XNYS` and returns `None` for an exchange-closed day. The -12 subset proof (generated against that calendar before dispatch) preregistered the expectations: REQ-SPT-05/06 (2025-11-28) "exactly 4 bars, last label 12:30"; REQ-SPT-07/08 (2026-07-03) "exactly 0 bars".

**Documentary (civil/exchange calendar facts, verified offline via stdlib).** 2026-07-04 is a Saturday, so NYSE observes Independence Day on Friday 2026-07-03 — a full exchange closure. 2025-11-27 is Thanksgiving (Thursday), so Friday 2025-11-28 is the published NYSE early-close day (13:00 ET close). Both agree with the pinned XNYS mechanism's treatment as preregistered in -12.

**Empirical (wire evidence from -14, the strongest class here).** On 2025-11-28 both AAPL and QQQ returned exactly 4 bars, 09:30→12:30 — the early-close session, on the wire, for both symbols. On 2026-07-03 AAPL returned HTTP 400, body `{"code":400,"status":"error","message":"No data is available on the specified dates. Try setting different start/end dates."}` (sanitized facts at -14 evidence `receipt_facts.json`, commit `76459ef`). The closed-day classification of 2026-07-03 therefore rests on: preregistered calendar expectation + civil-calendar fact + a vendor response consistent with zero sessions.

**Vendor documentation: UNKNOWN.** The repo was searched for any already-archived official Twelve Data documentation describing no-data / HTTP-400 semantics (adapter contract, Stage-0 addendum, preflight evidence, spec docs). Zero documentary hits. No archived vendor document promises that a fully-closed window yields this 400, nor that this message means "closed day" as opposed to any other no-data condition. The behavior is supported **empirically by exactly one observation** (REQ-SPT-07). One observation cannot ground a generic rule — this is the central constraint on §5's narrowness.

**Failed inspection trial (recorded, not hidden).** A fresh local re-derivation of `xnys_schedule` for the two dates was attempted in the standing environment and FAILED: `pandas_market_calendars` is not installed there (the -11/-12 runs used a disposable environment that no longer exists). It was not retried via any network install (out of scope). Calendar conclusions above therefore rest on the pinned mechanism + preregistration + empirical wire evidence, not on a new local calendar run.

## 4. Exact HTTP-400 path in the pinned code (where SPT-07 died)

1. **Adapter** (`td_http_transport_adapter.py`): by design returns `(status, body)` for ANY HTTP status — including 400 — and raises only on transport-level failure. The vendor error payload reaches the collector byte-intact; the adapter makes no classification.
2. **Collector run loop** (`td_min_collector.py`, `_run_locked`): per request, in order — existing-receipt verification → limiter reservation (**the credit is reserved and spent BEFORE dispatch**, per the pinned budget rule; SPT-07's credit was consumed even though it failed) → `transport(req)` → `_handle_response(...)` → any non-`None` problem → `_hold()` → **terminal HOLD; the loop returns immediately**. This is exactly why REQ-SPT-08 was never attempted.
3. **`_handle_response` first gate**: `if status != 200: _preserve_rejected(rid, body); return f"HTTP {status} for {rid}"`. REQ-SPT-07 terminated HERE. The error JSON was preserved as evidence but never parsed for classification.
4. Later gates (reachable only on HTTP 200): payload `status != "ok"` → HOLD; `values` missing/empty → `"missing/empty values"` HOLD; then meta/venue binding, row-count bounds, receipt write, then bar validation.

**Consequence:** under the frozen contract there is NO path by which a zero-bar response can be accepted — non-200 → HOLD, and 200-with-empty-values → HOLD. Yet the validation layer could bless exactly this case: `validate_input` v2 rule V8a is "exchange-CLOSED day + 0 bars → PASS (verified closed)", V4 is "no bars on exchange-closed days", V5 resolves closes from the XNYS calendar. The validator is only ever invoked on a written receipt, which a zero-bar response can never become under the current front gates. **The semantic gap is precisely and only in `_handle_response`'s front gates.**

**How closed sessions are "known" today:** not by the collector. The collector is deliberately calendar-blind (its only calendar-adjacent constant, `BARS_PER_DAY = {"1h": 7, "4h": 2}`, is a truncation bound). Closed-ness knowledge lives in (a) preregistration — manifest windows and subset-proof expectations derived from the XNYS calendar at design time — and (b) `validate_input`'s `xnys_schedule` at validation time, for bars that exist.

## 5. The narrow future classification — `EXPECTED_EMPTY_CLOSED_SESSION` (DESIGN ONLY; nothing implemented)

A future, separately versioned contract MAY add this classification in `_handle_response`, ahead of the `status != 200` gate, only when ALL of the following hold conjunctively:

1. **Preregistered closed window.** Every date in the request's entire `[start_date, end_date]` window (exchange-local) is exchange-closed under the pinned XNYS mechanism (`xnys_schedule` → `None` for every date), AND the pinned manifest (or a versioned supplement pinned before dispatch) declares `expected_bars == 0` for this request. Mixed open/closed windows are excluded by construction.
2. **Exact wire match.** HTTP status == 400 AND the body parses as a JSON object with exactly `code == 400` (integer), `status == "error"`, and `message` byte-equal to `"No data is available on the specified dates. Try setting different start/end dates."` No prefix, fuzzy, or case-insensitive matching. Any `values` field present → not this class.
3. **Provenance limits.** Symbol/venue for this class come from the manifest only — the error payload carries no `meta`, so this class is **never wire-verified identity evidence** and must never be recorded as such. The credit reservation stands (spent, accounted, never refunded). The raw body is preserved write-once as `<rid>.closed_day.bin` (bytes + sha256, same retention class as rejected evidence), with a lifecycle event carrying the calendar-proof digest (calendar library + version + per-date closed results).
4. **Disposition.** The request is marked `CLOSED_DAY_EVIDENCED` — explicitly NOT `COMPLETED`, NOT construction-admissible, NOT usable as bars or as a receipt. This is the single behavioral change: this class does not trigger the fail-closed stop, so the run proceeds to the next request. That is justified only because every condition was preregistered and the outcome contains no data that could be acted on; any deviation falls back to the existing HOLD path unchanged.

**Explicit exclusions** (each routes to the existing HOLD path, no exceptions): any other 400 message/code or unparseable body; HTTP 200 with empty `values` on any window (remains HOLD — see below); HTTP 200 with `status:"error"`; any 401/403/429/5xx; a window containing any open session or any date the calendar cannot resolve; calendar source unavailable or version-mismatched (classification disabled, fail-closed); a request not preregistered with `expected_bars == 0`; a message differing by even one character.

**Why HTTP-200-empty stays excluded:** an empty 200 on an open day is precisely the missing-data failure mode `validate_input` v2's R1/V8a redesign was written to catch. The 400 class keys on a *positive vendor assertion* plus a *preregistered* closed window — never on absence of data alone. Broadening to empty-200 would accept silence as evidence; that is out of scope for this design and would need its own adjudication.

## 6. P2 disposition — recommendation

**P2 v1 remains UNMET.** The frozen P2 criterion (protocol of 2026-10-13) is "all eight SPOT receipts". REQ-SPT-07 produced a HOLD under the contract frozen before dispatch; reclassifying it after seeing the result would be moving the goalposts. REQ-SPT-08 was NOT ATTEMPTED — no evidence exists and nothing can be classified. The SPOT8 state stays terminally HOLD; no replay into it; no reuse of spent attempts. This memo changes none of that.

**Future option (not adopted here):** a separately versioned qualification supplement (e.g., "P2-SPOT v2") could preregister §5 acceptance for closed-day spot requests, provided (a) the §7 fixture matrix passes 100% offline in the network-disabled harness before any dispatch — a single negative-fixture misclassification makes the protocol ineligible; (b) closed-day requests are recorded in the qualification ledger at their own evidence class ("closed-day no-data evidenced — zero bars by design"), never as receipts and never as identity evidence; (c) any live deviation from the exact schema → existing HOLD + batch stop, credit accounted as spent. Even under such a supplement, REQ-SPT-08 would require a FRESH dispatch under the new version with fresh authorization (Mike's direct word for the live call; the -14 authority's unused eighth credit does not carry into a new protocol version by itself — carry-over is Mike's/ChatGPT's call, not this memo's).

## 7. Proposed no-network fixtures (for the future supplement; NOT built in this task)

Positive (must classify `EXPECTED_EMPTY_CLOSED_SESSION`):
- **F1** — the preserved SPT-07 payload shape (180-byte body; fixture derived from private evidence sha `3339c341…`, fixture file carrying that provenance + its own sha) + preregistered single closed-day window + XNYS closed proof → class assigned, run continues to next request.
- **F2** — same payload + preregistered multi-day window in which every date is closed → class assigned.

Negative (must HOLD via the existing path):
- **N1** same payload, window containing one open session (mixed window) → HOLD.
- **N2** message mutated by one character → HOLD.
- **N3** `code`/`status` fields missing, retyped, or altered → HOLD.
- **N4** HTTP 200 + `status:"ok"` + `values: []` on a closed window → HOLD (silent-acceptance exclusion).
- **N5** HTTP 200 + `status:"error"` + the exact message → HOLD.
- **N6** HTTP 400 with an entitlement/auth-style message → HOLD.
- **N7** HTTP 401/403/429/500 with any body → HOLD.
- **N8** HTTP 400 with unparseable body → HOLD.
- **N9** closed window but request NOT preregistered `expected_bars == 0` → HOLD.
- **N10** calendar source unavailable or version-mismatched at classification time → HOLD (classification disabled).
- **N11** error payload that also contains a `values` field → HOLD.
- **N12** payload exact but request digest does not match the pinned manifest entry → HOLD.

Failure budget: 100% pass required on F1–F2 and N1–N12 in the network-disabled harness (transport stubbed, socket-guarded, in the pattern of the -12 preflight). Any failure = supplement not eligible, no partial credit, no live dispatch.

## 8. What does not change

P2 v1 unmet; REQ-SPT-08 NOT ATTEMPTED; SPOT8 terminal HOLD state untouched; the -09 P1H HOLD state untouched; 1H→4H `CONSTRUCTION_HOLD` unchanged (the classification, if ever built, is never construction-admissible); no baseline/performance work opened; no candidate merge; PR #8 untouched.

## 9. Inspections performed in this task

Canonical text fetched (Slack read + Issue #1 comment 6175610471 via public API) and followed; -14 report + `receipt_facts.json` read; pinned collector read end-to-end around the response path (`_run_locked`, `_handle_response`, `_preserve_rejected`, `_validate_bars`); adapter return-contract read; `validate_input.py` session/calendar logic read (V4/V5/V8a, `xnys_schedule`); SPOT8 manifest REQ-SPT-07/08 entries read; -12 subset proof and P1–P7 qualification ledger read; repo-wide search for archived vendor no-data/400 documentation (0 hits — §3 UNKNOWN); stdlib weekday verification for 2026-07-03/04 and 2025-11-27/28; one FAILED trial (local `xnys_schedule` re-derivation — `pandas_market_calendars` absent from the standing environment; recorded in §3, not retried online). Zero network calls of any kind were made by this task beyond the one unauthenticated GitHub API read of the canonical comment at intake (parent-directed source fetch); zero vendor/auth calls; zero credits.

## 10. Verdict and next eligible task

**Verdict:** the closed-day 400 is classifiable safely ONLY in the narrow preregistered form of §5 — exact schema + provably fully-closed window + `expected_bars == 0` declared before dispatch — and even then only as a distinct evidence class, never as a receipt. Vendor documentary support is UNKNOWN; empirical support is a single observation; that is enough to design the class, not enough to widen it. P2 v1 stays unmet; SPT-08 stays NOT ATTEMPTED.

**Next eligible task** (requires fresh tasking; the live leg additionally requires Mike's direct authorization): an OFFLINE implementation + fixture task for a versioned P2-SPOT supplement on an isolated candidate (collector front-gate branch + F/N fixtures in the network-disabled harness), followed by separate adjudication. No implementation is authorized by this memo.

Effort: within the 40-minute budget (single pass; inspections + this memo). Deliverable: this memo only, left uncommitted in the main worktree.
