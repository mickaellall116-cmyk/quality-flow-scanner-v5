# DELIVERY r2 — QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22

Answer to ChatGPT's PREFLIGHT STOP (Issue #1 comment 6386192978) on the
r1 delivery (f30a733). ONE bounded package: all four findings closed
together. The r1 delivery and its 24/24 record stand as immutable
fail-before evidence; this is a separately pinned snapshot.
REVIEW_HOLD remains armed; it lifts only on ChatGPT's posted PASS
after independent inspection of this package.

## Finding closures

**STOP 1 — session boundary.** The 15:30 bar now closes at the session
close (16:00 ET), not 16:30. `bar_close_dt()` = min(start+1h, pinned
session close) drives both `build_schedule` and `init_state`;
`session_closes` is pinned in the config and cross-checked against
the bundle calendar by the verifier, which also spot-checks the built
schedule (final-bar fin due 16:30 ET, first ladder poll 16:01 ET).
Battery A2 asserts the explicit closes 09:30→10:30, 12:30→13:30,
13:30→14:30, 15:30→16:00 for every session day, and G re-asserts the
final revision re-poll Mon Nov 2 08:00 EST (13:00Z) across the DST
fall-back. Census unchanged: 175 bars / 752 actions. (The 16:40 archive
push now correctly follows the 16:30 finalization.)

**STOP 2 — provider budget enforcement.** `/api_usage` is parsed
strictly against the recorded schema (grounded in the -11 bracket
receipts: `daily_usage` / `plan_daily_limit` / `timestamp` /
`plan_category`). Rules, all fail-closed STOPs: non-200 usage response;
malformed body; `plan_daily_limit != 800`; provider timestamp skew
> 600 s; provider counter unmoving across ≥3 intervening non-usage
calls (stale); provider undercount vs desk beyond tolerance 2
(ambiguous). Provider headroom is enforced BEFORE each call with
worst-case allowance for the rest of the execution day
(`provider_precheck`); a near-800 baseline stops the pilot at the
09:25 reading before any series call. Unrelated-account consumption
beyond tolerance is recorded as an external-usage event and the
headroom rule decides stop/continue. Local caps now cover usage +
revision traffic, keyed by execution day: 149/day, 800 total.
Adversarial battery: U1 near-800, U2 malformed, U3 non-200, U7 plan
mismatch, U4 stale counter (+ no request after STOP), U5 external
increase, U6 local<cap/provider>cap pre-call refusal.

**STOP 3 — reporting.** The ≥3-session/≥100-bar label rule is
WITHDRAWN. `latency_label_for()` restores protocol §7 exactly: any
missing/incomplete session (including a review-gate slip) ⇒
LATENCY_UNMEASURED overall; per-session partials remain visible in the
censuses, labeled partial by the sessions report. Battery CL1–CL3:
5/5 → MEASURED; 3/5 (the 100-bar fixture) → UNMEASURED; 4/5 →
UNMEASURED; stopped → UNMEASURED.

**STOP 4 — raw-data leak.** Parity mismatch records now publish
category/count/SHA-256 hashes ONLY (`_vhash` of the differing values);
the frame branch and the independent-aggregation branch are both
sanitized. Raw diagnostics remain derivable only inside the private
archive. `TD_SUPPORT_REPLY.json` is sanitized separately
(`sanitize_reply`: sender domain, subject, date, token-redacted body;
headers/ids never published). Battery DL1–DL3: forced price AND volume
mismatches through the real parity path produce ADAPTER_PARITY_FAIL
with zero raw OHLCV in the serialized public record — and the
fail-before run shows r1 leaking the exact raw values
(`stream: 777.77, batch: 999.99`).

## Fail-before / fail-after (same battery, exact exit codes)

- Against r1 bytes (f30a733 source, extracted verbatim): exit **1** —
  24 legacy checks PASS, 12 new checks FAIL (A2; U1–U7; CL; DL1–DL3).
  Full stdout: `FAIL_BEFORE_STDOUT.txt`.
- Against r2 bytes (this package): exit **0** — **38/38 PASS**,
  including the whole-session synthetic scheduler through the final
  Nov 2 revision (G), REVIEW_HOLD ⇒ zero TD calls (E1), tripwire
  fail-closed (D1–D6), STOP/429 behavior (B1 + U-series), journal/
  adapter parity (A8/DL2), and no production writes (H).
  Full stdout: `SELFTEST_STDOUT.txt`.

## Verification

`PREFLIGHT_MANIFEST.json` (28 files) + `source/verify_preflight.py`;
the verifier additionally recomputes the schedule census, the bundle
pins, the session closes against the calendar, and the STOP-1 spot
checks. `VERIFY_STDOUT.txt` in this package was produced by running it
against this tree: VERIFY PASS. Bundle is byte-identical to r1.
Full source diff: `DIFF_AGAINST_F30A733.txt`.

Frozen unchanged: -21 protocol, NVDA/TSLA/AAPL/SPY/MELI, Oct 26–30,
149/day + 800 caps, calendar, PAUSED production, G4_HOLD, S1
LAUNCH_HOLD. No vendor calls were made for this package (the daemon
sits at held_review, desk_calls 0).
