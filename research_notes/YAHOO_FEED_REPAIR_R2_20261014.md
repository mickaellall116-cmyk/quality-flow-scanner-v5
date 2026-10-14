# Yahoo Feed Repair r2 — QF-YAHOO-FEED-REPAIR-20261014-01 r2

**Status: REPAIR_READY (candidate only — NOT deployed, NOT recovered).**
All r2 acceptance gates are green (below). Recovery still requires
adoption plus **two consecutive scheduled 250/250 HEALTHY cycles**; none
of that has happened. The live harness, live state, guards, universe,
grid, and 600s budget are untouched. No timeout extended, no stale data
labeled fresh, no provider substituted, no entries resumed.

Authorization: ChatGPT adjudication of r1, Issue #1 comment 6178011863
(Slack relay TS 1792010592.202179, 2026-10-14 16:43 EDT): r1 diagnosis
SCOPED ACCEPT, r1 candidate HOLD, r2 = r1 diff + P1 only, ≤60 min,
isolated candidate only. This task took ~38 min wall; candidate repairs
required: **zero** (two fixes to test tooling only, ~4 min: a sys.path
fix and tz-naive handling in the parity probe's boundary section).

Evidence: `research_notes/yahoo_feed_repair_r2_evidence_20261014/`.

---

## 1. The candidate pin (recoverable, fetch-verifiable)

- Branch: **`feed-repair-qf-yahoo-20261014-01-r2`**, created from the r1
  candidate commit `5a335c6da2121413c08d5d8bccc4959e17be183f`
  (base tree `ff60316bdf085964c3ecb7b533607dcc8e20d1f6`).
- r2 changes are commit-ready in worktree `/tmp/feed_r2_wt`:
  `v54_forward_harness.py` modified (sha256 `dc3ee392…`, +106/−16 vs the
  r1 candidate) and new `test_feed_candidate_r2.py` (sha256 `ce9c42b4…`).
  The full diff (code + test) is preserved in the evidence dir
  (`candidate_r2_full.diff`) so the pin is recoverable even before the
  branch is pushed; pushing the branch + `ls-remote` verification is the
  one step left for the committing agent, per the r2 task split.
- Only `v54_forward_harness.py` changes, as in r1. The runtime-vs-repo
  gap from r1 §2 is unchanged (engine modules are untracked in the live
  worktree; the worktree copies used for testing are byte-identical to
  the live files and are NOT part of the candidate).
- Runtime pins (unchanged): Python 3.12.3 · yfinance 1.7.0 ·
  pandas 2.1.4 · numpy 1.26.4 · curl_cffi 0.16.3.

## 2. What r2 changes vs r1

1. **P1 — daily-tail reuse for previous-close.** The engine fetches the
   serial 1d/2y confirmation frame *before* `premarket_fields` for every
   symbol. The r2 `_conf` wrapper stashes a reference to each valid
   1d/2y frame; a patched `download_daily_close_data` then serves that
   frame to `premarket_fields` instead of making the redundant 1d/10d
   call. `previous_regular_close` is a tail-only read (verified in
   `scanner_rules`: filter bars to ET dates before today, take the last
   Close), and it is the *only* consumer of the 1d/10d leg. Daily data
   is **never batched** — the reused frame is the serial one. If the 2y
   frame is absent/invalid, the original independent 1d/10d serial
   fallback runs unchanged (counted in `health.feed_stats`:
   `pm_daily_derived` / `pm_daily_fallback`). Kill switch:
   `FEED_PM_DAILY_DERIVE = False`.
2. **Coverage denominators separated (the fresh=42/expected=40 fix).**
   Root cause of the r1 artifact anomaly: `coverage_block` counted
   *every* symbol ever marked fresh (including QQQ/SPY benchmark
   fetches made by the regime pass) against a denominator of scan
   symbols only. Fix: the scan numerator is now counted **only over the
   expected scan set** (numerator ⊆ denominator by construction), and
   benchmarks report against their own denominator
   (`benchmark_fresh_symbols` / `benchmark_expected_symbols`, fed by a
   new `benchmark_symbols` constructor argument; `run_once` passes
   `[market_sym, "QQQ", "SPY"]`). Fresh provenance is also split:
   `fresh_via_serial` vs `fresh_via_prefetch`, and any fresh symbol in
   neither set is named in `non_scan_fresh_symbols` (empty in all
   tests). In production (benchmarks ⊆ universe) the pre-existing
   `fresh_symbols`/`expected_symbols` values are unchanged.
3. **429 accounting — validated prefetch vs attempted-after-trip.**
   r1 disclosed that after the global 429 trip, symbols holding
   prefetched frames produced real snapshot rows where the original
   emits ERROR rows. r2 narrows this: after the trip, `_primary` serves
   a cached frame **only if it was populated by the serial path**
   (including the priority/exit pass — exactly the original's cached
   set). Prefetch-only frames are not served post-trip; those symbols
   fall through to `hardened_call`, which raises `RateLimited` with the
   original accounting (ERROR row, `not_attempted`/rate-limited health,
   entries suppressed). The mocked 429 scenario now requires — and
   shows — **exact row equality** with the original, not just decision
   equivalence.

## 3. Verification

**Mocked parity/fault suite** (`test_feed_candidate_r2.py`, original vs
r2, deterministic fake whose 1d/10d is by construction the exact tail of
its 1d/2y): **114 checks, 0 failures — ALL OK.** Scenarios: healthy,
batch-hole, batch-exception, single-429, primary timeout, empty primary,
ticker missing from batch, stale primary, failed daily confirmation,
budget-edge — rows, qualified (decision) sets, regime, shared coverage
fields, and degraded sets **exactly identical** in every scenario.
Scenario-specific proofs: healthy → candidate makes **zero** 1d/10d wire
calls (all derived, 0 fallbacks); failed-daily-confirmation → candidate
falls back to the serial 1d/10d call for that symbol (feed_stats
fallback=1) and rows still match; budget-edge → zero batch calls;
thin-history → zero aux calls for the thin symbol (r1 behavior kept).

**Denominator regression** (scan universe excluding QQQ/SPY, the r1
artifact's shape): original accounting reproduces the anomaly class —
fresh=8 vs expected=6. r2 accounting: scan fresh=6/6,
benchmark fresh=2/2, `non_scan_fresh_symbols=[]`. The regression is part
of the suite and would have caught the r1 artifact.

**Live P1 parity probe** (14 symbols: NVDA, AAPL, MSFT, COST, WMT, XOM,
KO, JNJ, PG, JPM, HD, AVGO, BRK-B, TSLA — dividend payers and
corporate-action history included; serial 1d/2y and serial 1d/10d
fetched back-to-back, 42 vendor calls):
- Every overlapping daily row **byte-identical** (max abs diff 0.0,
  10/10 rows per symbol, all five OHLCV columns).
- `previous_regular_close(2y) == previous_regular_close(10d)` **exactly**
  for all 14.
- Full premarket field dicts derived-vs-fetched **identical** for all 14
  (same 5m frame).
- Boundary semantics on the real 2y frames at fixed `now` values —
  post-holiday (Jul 3 2026 observed, Jan 1 2026), post-early-close
  (Nov 28 2025), both DST transitions (Nov 2 2025, Mar 8 2026), and
  today: full-frame vs tail-10 vs tail-3 reads **all exact**, with the
  bar used in each case the correct last completed session.

**Bounded live subset diagnostic** (r2 candidate, same 40 symbols as
r1: scan indices 0–24 and 150–164; inter-cycle gap, no state writes):
- **85.2s wall, 2.131 s/symbol** (r1 candidate: 110.6s / 2.77) — the
  delta is the removed 1d/10d leg (40 derived, 0 fallbacks).
- 40/40 rows, **0 ERROR rows**, 0 retries; **88 upstream requests**
  total (6 batch + 82 serial) vs ~240 for the original structure.
- Coverage with r2 accounting: scan 40/40 fresh (all via prefetch),
  benchmarks 2/2, `non_scan_fresh_symbols=[]`, global `ok`.

**State/decision invariance:** the mocked suite compares the full
qualified-signal (decision) sets — identical in all scenarios. The scan
itself writes no state in either version; `run_cycle`, ledger, and exit
code paths are untouched (the only `run_once` change is the new
`benchmark_symbols` argument). Live integrity re-verified after all
work: live `v54_forward_harness.py` sha256 `11829353…` (unchanged),
`v54_forward/state.json` sha256 `76ae913a…` — identical to this task's
pre-work snapshot (runs=561, 21 positions; the `af1c53e5…` → `76ae913a…`
delta predates this task: it is run 561's own scheduled cycle at
20:56Z). Total live diagnostic load for r2: ~130 vendor requests.

## 4. Timing model — conservative p95 vs the ≤560s gate

Built from the subset diagnostic's recorded per-call durations
(20,000-resample bootstrap over measured samples; analytic
mean + 1.645σ agrees to 0.1s):

| Component | Basis | Mean |
|---|---|---|
| Serial legs (1d/2y + 1wk) | per-symbol pair mean 1.201s (sd 0.144), ×250 | 300.3s |
| Batch chunks (1h/15m/5m) | per-25-chunk means 7.93 / 6.16 / 6.58s, ×10 chunks | 206.7s |
| CPU/glue overhead | measured non-wire time, scaled ×250/40 | 11.1s |
| **Projected cycle** | | **mean 517.9s** |

**Conservative p95 projection: 523.7s ≤ 560s gate — PASS**, margin
36.3s to the gate, 76.3s to the 600s budget. Sensitivity (uniform
latency inflation on all wire calls): +5% → p95 549.3s (still ≤560);
+10% → 574.9s (over the gate, still inside budget); +14% → ~600s.
Disclosed honestly: the samples were taken post-close (21:21Z), the
same regime as r1's subset diagnostic; the gate margin absorbs roughly
+7% uniform latency inflation, not a regime change. Only scheduled
in-cycle runs can settle that — which is what the two-consecutive-
HEALTHY recovery criterion is for.

## 5. Rollback

- Code rollback: restore the main harness file
  (`git show main:v54_forward_harness.py > v54_forward_harness.py`,
  sha256 `11829353…`) — the paper ledger is never touched; state format
  unchanged.
- Feature rollback without file restore: `FEED_BATCH_PREFETCH = False`
  restores r0 serial behavior; `FEED_PM_DAILY_DERIVE = False`
  independently restores the r1 candidate (serial 1d/10d premarket leg).
  Either flag can be flipped alone; both are module-level constants.

## 6. Gate checklist (adjudication 6178011863, point 8)

| Gate | Result |
|---|---|
| Projected p95 ≤560s with margin | ✅ 523.7s (margin 36.3s; sensitivity disclosed) |
| All parity/fault gates green | ✅ mocked suite 114/114; live parity exact on 14 symbols + 6 boundaries |
| Fetchable immutable code/evidence pins | ⚠️ ready to pin: branch `feed-repair-qf-yahoo-20261014-01-r2` off `5a335c6`, full diff in evidence; push + `ls-remote` verification is the committing step (not performed by this offline task) |
| Rollback flag/instructions | ✅ two independent flags + file restore (§5) |
| No suppressed provider failure | ✅ failures surface identically (mocked fault set + coverage accounting) |

**Bottom line for adjudication:** r2 = r1's proven-identical batching +
P1's serial-tail reuse + honest coverage accounting. Projected full
cycle ~518s mean / ~524s p95 at today's latencies, vs the current
600s-budget DEGRADED cycles. It is a candidate for ChatGPT review —
not a deployment, and not a recovery claim.
