# Yahoo Feed Repair — QF-YAHOO-FEED-REPAIR-20261014-01 r1

**Status: REPAIR-READY candidate delivered. NOT recovered.** Recovery per the
canonical criteria (full 250/250 fresh coverage, fresh completed bars, correct
frozen grid, no suppressed provider failures, **two consecutive scheduled
healthy cycles**) is **not met** — the candidate is not adopted into the live
tree, and even adopted, it is projected to improve coverage materially but
not to reach 250/250 at today's Yahoo latencies (see §7). No timeout was
extended, no universe shrunk, no guard weakened, no stale data labeled fresh,
no provider substituted, no entries resumed, no strategy file touched.

Authorization: Mike, "Fix the feed?" (2026-10-14 ~15:28 ET), via Issue #1
comment 6176597864. Diagnosis + reversible infrastructure-only candidate +
verification within the existing Yahoo/free setup.

Evidence: `research_notes/yahoo_feed_repair_evidence_20261014/`.

---

## 1. What the cycles actually show (run 559 / 560 and the recent series)

The harness keeps only the latest cycle artifact (`last_cycle.json` is
overwritten hourly), so **run 559's own summary does not survive locally** —
it is bracketed by preserved artifacts below and by the watchdog alert at
2026-10-14 15:51Z. Run 560 (the latest completed cycle) was measured
directly:

- **Run 560** — finished 2026-10-14T19:51:42Z, duration **600.3s**, status
  **DEGRADED**, error `budget exhausted before staging`, entries suppressed,
  publish skipped (by design). Coverage **154/250 fresh**; all 96 degraded
  symbols are `not_attempted` ("no vendor request completed this cycle") —
  zero timeouts, zero 429s, zero retries recorded. The scan died exactly in
  order: last fresh symbol is scan index 153 (WMT); index 154 (COST) onward
  never attempted. Mean cost **3.90 s/symbol**.
- Preserved series (all DEGRADED, all 600s budget-exhausted): 2026-09-18
  "slow run ~13 min" (pre-budget era) · 09-30: 183/250 · 10-02: 190/250 ·
  10-06: 179/250 · 10-07: 203/250 · 10-10: 193/250 · 10-12: 184/250 ·
  10-13: 183/250 · 10-14 06:41Z cycle: 172/250 · 10-14 run 560: **154/250**.
  The per-symbol cost has risen from ~3.2s (early Oct) to ~3.9s — a
  worsening trend, not a one-off.
- Ledger/state stayed safe throughout: state runs=560, 21 positions
  (all closed), last_run 2026-10-14T19:51:42Z; the fail-closed design did
  exactly its job — degraded cycles suppress entries and skip publishing.

## 2. Runtime pins and the runtime-vs-repo gap

Python 3.12.3 · yfinance **1.7.0** · pandas 2.1.4 · numpy 1.26.4 ·
curl_cffi 0.16.3. Full hashes in the evidence file.

**Gap (confirmed):** on `main`, only `v54_forward_harness.py` is tracked.
The modules it imports — `v54_engine.py`, `v54_rules.py`,
`v54_universe_x2.py`, `v54_exit_tracker.py`, `v54_forward_log.py`,
`masterscanner_api.py`, `scanner_rules.py`, `hybrid_exit_test.py` — are
**untracked files in the live worktree** (restored there 2026-10-07). The
running system therefore cannot be reproduced from the repo alone; the
candidate branch necessarily contains only the harness change, and adoption
instructions (§9) account for this. This task did not alter that situation.

## 3. Where the 600s goes — request inventory

Every cycle is one serial process (all `yf.download(..., threads=False)`).
Per symbol, the frozen engine's scan loop issues **6 vendor downloads**:

| # | Request | Path | Per-call mean (probe, n=9) | Payload |
|---|---------|------|------------------|---------|
| 1 | 1h / 180d → resampled closed 4H | primary (gating) | 0.845s (steady ≈0.68) | 1251 bars |
| 2 | 1d / 2y | confirmation → feeds daily_trend → **feeds grades** | 0.644s | 501 bars |
| 3 | 1wk / 5y | confirmation → weekly_trend → **feeds grades** | 0.629s | 262 bars |
| 4 | 15m / 5d | confirmation (observational only) | 0.662s | 130 bars |
| 5 | 1d / 10d | inside `premarket_fields` (observational only) | 0.588s | 10 bars |
| 6 | 5m / 2d prepost | inside `premarket_fields` (observational only) | 0.651s | ~290 bars |

Plus QQQ/SPY regime primaries (already cache-deduped — measured: exact
duplicates on the wire are ≈0; the cycle-local `primary_cache`, regime and
position passes already share frames). Total ≈ **1500 downloads/cycle**.
CPU is irrelevant: resample 19ms + classify 16ms per symbol (~9s/cycle max).

**Scheduler overlap (context, not proven cause):** the same egress IP also
runs the hourly V5.4 MTF 1h paper harness (~750 downloads of the same
universe), the lonewolf overlay (own 1d downloads), the V3.7 watcher and the
Tiingo observer — roughly 2600+ Yahoo requests/hour aggregate. In run 560
the 1h MTF cycle finished 19:41:17Z, 25s before the 4H cycle started, so
run 560 was **not** a direct-overlap casualty; rate-shaping at hourly scale
cannot be ruled in or out from local evidence.

## 4. Diagnosis — measured bottleneck

Per-call latency is **flat ~0.5–0.85s regardless of payload** (a 10-row
request costs what a 1251-row request costs): the time is fixed per-call
overhead — proxy CONNECT + TLS + Yahoo cookie/crumb handling per fresh
`yf.download` — not data transfer. Confirmed by three negative controls:

- **No amortization:** three identical sequential NVDA primaries took
  0.60 / 0.72 / 0.82s — nothing is cached between calls.
- **No parallel gain:** a 9-ticker batch with yfinance's own `threads=True`
  took 3.26s vs 3.19s serial-internal — the path (proxy/Yahoo) does not
  parallelize; client-side concurrency is not a lever (and threaded
  monkeypatching is prohibited anyway).
- **Shared session:** a shared curl_cffi session gave no reliable gain
  ([1.18, 1.37, 0.50, 0.57, 0.51] vs baseline steady ~0.62–0.79) and one
  flaky empty frame — **rejected**.

Arithmetic verdict: even the *fastest* measured per-symbol serial total
(3.34s) × 250 = **835s > 600s**. The current design is structurally over
budget at present Yahoo latencies; no in-guardrail tuning of the serial
path closes a 40% gap. The only lever is reducing per-call overhead per
symbol — i.e., multi-ticker batching where it is provably identical.

## 5. Batching — what is identical, what is not (measured, not assumed)

Equivalence was tested batch-vs-single through the **exact** frozen
post-processing (flatten → dropna → `resample_closed_4h` / closed-bar
trimming), 12 symbols across scan order incl. the run-560 cutoff names:

- **Byte-identical (max abs diff 0.0, same index):** 1h/180d primary,
  15m/5d, 5m/2d-prepost. Adopted for batching.
- **NOT identical — REJECTED:** 1d/2y and 1wk/5y. For dividend payers the
  multi-ticker path rounds adjusted prices at float32 ulp (max diff
  3e-05…6.6e-05 across most historical rows; Volume diff exactly 0.0;
  non-dividend MARA exact 0.0). A reconstruction attempt (batch raw ×
  AdjClose/Close in float64) also failed — the batch *raw* values are
  themselves quantized (6.1e-05) — so no post-hoc fix exists. Because
  daily/weekly frames feed V5.4 **grades**, a 1-ulp input change can flip
  a knife-edge trend state; these two shapes stay on the serial path.
  (1d/10d tested identical, but a 10-day window can contain an ex-dividend
  date — same mechanism risk — so it was conservatively **not** batched.)

Batch economics: a 9-ticker primary batch took 3.19s vs ~7.6s of singles
(~0.35s/symbol vs ~0.68s steady) — one session/crumb setup per chunk
instead of per symbol. That is the entire mechanism of the candidate.

## 6. The candidate (isolated branch, reversible)

Branch **`feed-repair-qf-yahoo-20261014-01`**, commit **5a335c6**; only
`v54_forward_harness.py` changed (sha256 `aa0d5e7d…`; diff in evidence).
One-flag kill switch: `FEED_BATCH_PREFETCH = False` restores today's
behavior exactly. Design:

- `hardened_downloads` gains a **chunk prefetch** (25 symbols, scan order,
  45s deadline, skipped when rate-limited or when <90s budget remains) for
  the three proven-identical shapes: primary (1h/180d) into the existing
  `primary_cache`, 15m/5d into a new cycle-local conf cache, and the 5m
  premarket leg via patching `m53.download_premarket_data` (restored in
  `finally`, same pattern as the existing patches). Prefetched frames pass
  the **same** post-processing and, for primaries, the **same**
  `validate_primary_frame` before entering a cache.
- **Pure accelerator semantics:** batch timeout/exception, a missing
  ticker, an empty frame, or a validation failure caches nothing for that
  symbol — its request falls through to the existing hardened serial call
  with identical classification, retry, 429-global-trip and budget
  accounting. All guards (1–8) untouched; the 600s/45s/5s constants
  untouched; the frozen files untouched.
- **Thin-history skip:** when a symbol's validated primary frame has
  <205 bars, `v54_classify` returns None *before* reading any auxiliary
  input — so the candidate skips that symbol's aux fetches (they are
  computed-then-discarded today). Outputs provably identical.
- One real bug was caught by the offline tests during development and
  fixed before delivery: prefetched primaries initially bypassed
  `health.mark_fresh`, which would have collapsed coverage accounting to
  0-fresh. `_primary` now marks fresh on a validated cache hit (idempotent
  with the serial path's marking). Disclosed here and in the commit.

## 7. Verification

**Offline (mocked wire, deterministic fake, original-vs-candidate full
scan over 32 symbols; `test_feed_candidate.py` in evidence):**

| Scenario | Rows identical | Regime identical | Wire calls orig → cand |
|----------|:-:|:-:|:-:|
| healthy | ✔ | ✔ | 194 → 100 |
| batch hole (one ticker empty in batch) | ✔ | ✔ | 194 → 103 |
| batch transport raises | ✔ | ✔ | 194 → 196 (full fallback) |
| single-symbol 429 | guard trips in both; entries suppressed in both | ✔ | 63 → 36 |

429-scenario disclosure: after the global trip, the candidate holds
validated prefetched frames for later symbols, so its *snapshot rows* for
those symbols are real rows and its coverage marks them fresh (they **are**
this-cycle validated fetches), where the current code emits ERROR rows and
not-attempted. Entries are suppressed identically, coverage still shows
the cycle DEGRADED/rate-limited, exits unaffected (priority pass precedes
the scan in both). This is the pre-existing "cached frames remain usable"
principle, extended — flagged for adjudication.

**Live bounded diagnostic (canonical step 6 — no state writes, no extra
full scan):** candidate-path scan of 40 real symbols (scan indices 0–24
and 150–164, incl. BRK-B and the run-560 cutoff names COST/HD): **110.6s,
2.77 s/symbol, 40/40 rows, 0 ERROR rows, coverage full, 0 retries.**
Baselines: 3.90 s/symbol (run 560, in-cycle), 4.02 s/symbol (serial probe).
Total diagnostic load for this task ≈ 570 vendor requests across ~1.5h —
about a third of one cycle, deliberately kept far below an extra full scan.

**Projection:** 2.77 s/symbol → ~691s scan for 250 symbols; expected
coverage at the 600s deadline ≈ **205–215/250 (from 154)**. **The
candidate alone does not reach full coverage** at today's latencies,
because the two grade-feeding serial legs (1d/2y + 1wk/5y ≈ 1.27s/symbol)
and the serial premarket daily leg (0.59s/symbol) remain. Claiming
otherwise would be dishonest; the remaining gap is ~15%.

**State integrity:** pre-work backups of all three state dirs + logs taken
before any work (hashes in evidence); post-work `v54_forward/state.json`
sha256 **unchanged**, runs=560, positions intact; live harness file
unchanged and imports cleanly; no harness process was disturbed (no cycle
was running during diagnostics; the live subset ran in the inter-cycle
gap and performed no state writes).

**Observed anomaly (disclosed, unresolved):** in the subset diagnostic's
comparison step (~20:22Z), plain serial fetches for NVDA/COST/BRK-B
transiently returned 503–504 resampled bars vs the candidate-served 511;
a re-check one minute later showed single and batch again identical at
511/511 with identical indices. The transient hit the *serial* path, not
the batch path, minutes after the 16:00 ET close; batch-vs-single
byte-equality rests on the two probe rounds (12 symbols, exact 0.0 diffs
through the full m53 path), not on that one comparison.

## 8. Proposals beyond this task's guardrails (NOT implemented)

- **P1 — subset-dedup of the premarket daily leg (−0.59 s/symbol →
  projected ~545s cycle, inside budget).** `premarket_fields`' 1d/10d
  request is a strict tail-subset of the already-fetched 1d/2y frame, and
  its only consumer (`previous_regular_close`) reads the tail. Serving it
  from the confirmation frame is *not* an exact-request dedup (different
  period, and a degraded-case behavior change: if 1d/2y fails, premarket
  loses its independent second chance) — observational fields only, but
  it needs adjudication, so it is documented, not shipped.
- **P2 — defer observational fetches (15m + premarket) for
  non-qualified rows.** Would cut the scan to ~1.63 s/symbol (~407s), but
  changes snapshot content for non-qualified rows (fields become N/A) —
  a record-semantics decision for Mike/ChatGPT, not an infrastructure fix.
- **P3 — schedule de-overlap.** Offset the MTF 1h / lonewolf windows away
  from the 4H cycle window (ops change, zero code). Unproven effect;
  run 560 had no direct overlap. Supporting measure only.
- **P4 — retest 1d/1wk batching on any yfinance upgrade.** The blocker is
  yfinance's multi-ticker float32 adjustment rounding (§5); if a future
  version fixes it, batching those two legs is worth ~0.57 s/symbol and
  would make the candidate sufficient alone (~560s projected).

## 9. Adoption & rollback

Adopt (after adjudication): verify state backup exists, then
`git show feed-repair-qf-yahoo-20261014-01:v54_forward_harness.py >
v54_forward_harness.py` in the live worktree (file-level; the untracked
modules stay as-is), confirm `python3 -c "import v54_forward_harness"`,
and let the **next scheduled cycles** judge it — recovery still requires
two consecutive scheduled HEALTHY cycles at 250/250. Rollback: restore
the main version (`git show main:v54_forward_harness.py >
v54_forward_harness.py`, sha256 `11829353…`) or set
`FEED_BATCH_PREFETCH = False`. The paper ledger is never touched by
either operation; state format is unchanged.

**Bottom line for adjudication:** the feed's problem is 1500 serial
requests × ~0.6s of fixed overhead against a 600s budget — measured, not
speculated. The candidate removes the overhead where removal is provably
value-identical and is worth ~+55 symbols of coverage, but full recovery
additionally needs one adjudicated step (P1 or P2) or a yfinance fix
(P4). The fail-closed guards earned their keep throughout: two weeks of
degraded cycles cost zero bad entries and zero ledger damage.
