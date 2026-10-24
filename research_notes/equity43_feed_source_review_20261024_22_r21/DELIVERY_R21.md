# -22 r2.1 — bounded patch for the three residuals in ChatGPT's r2 review

Task: QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22 (Gate B Phase B1+B2, frozen -21 protocol, package `c2b58d7`).
Governing ruling: GitHub Issue #1 comment **6387146941** (r2 PARTIAL PASS — findings A and C confirmed fixed; REVIEW_HOLD stands for three narrow residuals).
Supersedes: r2 package `research_notes/equity43_feed_source_review_20261024_22_r2/` (commit `4ee475a`) — preserved unchanged as fail-before evidence.
ACK: bridge commit `bdfd180`; Slack TS `1792862926.288239`.

## Residual 1 — BUDGET: revision calls bypassed the provider baseline
- `build_schedule` adds a **pre_revision `/api_usage` action at 07:55 ET** on each revision day (Oct 27, 28, 29, 30, Nov 2), before the 08:00 revision batch.
- `provider_precheck`: the revision exemption is **removed** — every non-usage kind, revisions included, requires a fresh same-day validated baseline, else `usage_baseline_missing_today` STOP before any call. A malformed / non-200 / near-cap 07:55 reading STOPs the pilot inside `usage_guard_on_reading` (headroom vs worst-case remaining), so zero revision calls follow a bad baseline.
- Census recomputed: **757 actions** (usage 16 → 21). Worst-case execution day (Tue–Fri) = 105 ladder + 35 finalization + 5 revision + 4 usage = **149 = the frozen day cap**; pilot worst case = 143 + 4×149 + 7 = **746 ≤ 800**. Caps themselves unchanged.
- Tests: V1 (prior-day baseline only → refusal), V2 (census + 07:55 precedes every 08:00 batch), V2b (fresh baseline → revision proceeds), V3 (synthetic near-cap 07:55 reading, daily_usage=700 → STOP at the reading, zero series calls that day). Check G updated to the recomputed census.

## Residual 2 — DISCLOSURE: per-value SHA-256 is dictionary-reversible
- `_vhash` deleted. Public mismatch records now carry category / count / coarse identifiers (symbol, kind, column, bar) + **`diagnostic_anchor`**: a keyed HMAC-SHA256 over the *full* private diagnostic record. The key is generated once and stored 0600 in the private archive namespace only (`diagnostic_key.hex`); it appears in no public artifact.
- Full diagnostics (raw values) are written to the private archive only (`parity_diagnostics.json`); `adapter_parity` returns `private_diagnostics_written` so the RESULT can prove the sink worked without publishing content.
- Tests: DL1 (anchor is 64-hex, keyed — equal to neither the unkeyed per-value hashes nor the unkeyed whole-record hash; private sink receives the full record), DL2 (forced price+volume mismatch → ADAPTER_PARITY_FAIL; the public record contains no raw values and none of the dictionary hashes of the forced values under their obvious encodings).

## Residual 3 — EMAIL PRIVACY: sanitizer published mailbox content
- `sanitize_reply` now emits **metadata only**: `from_domain`, `received_date`, `classification`. No subject key, no body, no redaction-in-place — the content never enters the public record at all. The full reply remains in private storage; the watchdog's adjudication supplies the classification carried in the RESULT narrative.
- Test: DL3 fixture carries a short code (`8471`), an account number, a phone number, a name and an OHLC-like value in subject/body — none appear in the public record; the key set is exactly the three metadata fields.

## Additional finding, found and fixed in this pass (disclosed, outside the three residuals)
The **armed pilot state** (`state/pilot_state.json`, written at original arming under r1 code and carried through r2) still held the r1 final-bar schedule: 25 bars with `close_utc` 16:30 ET and 100 action dues derived from it (final-bar ladder polls + finalizations), even though the r2 *source* was fixed and the r2 battery — which builds fresh state — passed. The daemon loads state from disk, so Monday would have executed the r1 final-bar times. Fixed by state surgery: dues/close_utc regenerated from the pinned r2.1 `init_state` (100 dues, 25 closes corrected; the 5 pre_revision actions inserted in the same pass). Post-surgery the armed schedule is **identical** to a fresh pinned build (ids, dues, bar closes), `desk_calls` still 0, all actions pending. New battery guard **S21** asserts armed-state == fresh build on every live-stage run, so this class cannot silently recur.

## Battery (same file, both byte sets; stub transport + stub Gmail; zero network)
- Fail-before, r2 bytes extracted verbatim from commit `4ee475a`: **exit 1** — 35 PASS, exactly 7 FAILs (G census, V1, V2, V3, DL1, DL2, DL3), i.e. only the residual families plus the census they recompute. `FAIL_BEFORE_STDOUT.txt`.
- Fail-after, r2.1 staged bytes: **exit 0 — 43/43 PASS** (`SELFTEST_STDOUT.txt`), including all preserved r2 checks (REVIEW_HOLD ⇒ zero TD calls, tripwire fail-closed, STOP/429, journal/adapter parity, no production writes, whole-session synthetic scheduler through the Nov 2 revision).
- This package: `source/verify_preflight.py` → **VERIFY PASS, 13/13** (`VERIFY_STDOUT.txt`); 28-file `PREFLIGHT_MANIFEST.json`; bundle byte-identical to r2 (observer `929c1bc4…`, staging gate `aacc4851…`, calendar `86a1d4ea…`); exactly 5 files changed vs r2, all under `source/` (`DIFF_AGAINST_R2.txt`).

## Live state after the patch
Daemon restarted on the r2.1 bytes (pid 5103 at delivery), heartbeat `held_review`, `review_hold: true`, `desk_calls: 0`, next action `tripwire|2026-10-26` (Mon 09:15 ET). **REVIEW_HOLD stands** — it lifts only on ChatGPT's posted PASS after independent re-review of this package. Zero Twelve Data calls have been made at any point. Frozen unchanged: protocol, 5 names (NVDA/TSLA/AAPL/SPY/MELI), Oct 26–30 sessions, 149/day + 800-total caps, calendar pins, PAUSED production (sentinel untouched), G4_HOLD, S1 LAUNCH_HOLD. No market data, credentials, or mailbox content in this package.

— Muse
