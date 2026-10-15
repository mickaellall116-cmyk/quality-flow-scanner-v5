# QF-YAHOO-CLEAN-CAPTURE-PREFLIGHT-20261015-08 r1

## Verdict

**YAHOO_CLEAN_CAPTURE_PREFLIGHT_PASS**

This verdict covers the offline preflight only. It authorizes **no Yahoo
call**. The actual bounded capture is a separate decision because it creates
new vendor requests (spec §8). No acquisition was performed, attempted, or
simulated against the live vendor in this task: the fixture is synthetic
bytes only, sockets were denied before any code path ran, and the vendor
client (`yfinance`) was never imported.

Spec: GitHub Issue #1 comment `6190703380`. Parent state: readiness map
`30eec2d` returned `BASELINE_DATA_HOLD` (qualified reusable C1 input
0/51 symbols, 0 days); the historical-data tier remains **LIMITED**, not
PIT-clean, regardless of this preflight's outcome.

## 1. Frozen capture manifest (spec §1)

Machine-readable: `capture_manifest.json` (schema
`qf.yahoo_clean_capture.manifest/1`), verified by fixture check C1.

- **Symbols (52 requests, frozen order):** `pine_backtest.UNIVERSE_X`
  (51, exact frozen order — UNIVERSE_15 + 36) plus **QQQ** as the sole added
  benchmark dependency (`pine_signal_quality.load_benchmarks` pulls SPY/QQQ;
  SPY is already in the universe at position 39). Sector exposure uses the
  per-symbol `pine_exposure.SECTOR` map — labels, not data requests — so no
  further sector requests exist. Canonical Yahoo symbol == frozen symbol
  for all 52; any response whose returned symbol/meta does not match the
  request exactly is a SCHEMA_DRIFT HOLD.
- **Segregation:** the 7 `-USD` crypto symbols inside UNIVERSE_X are
  captured as UTC 24×7 series in their own session class and are **never**
  mixed into the equity session construction (the D1 cache mixed 45 NY +
  7 UTC files; this manifest makes the split explicit per symbol).
- **Params:** `interval=1h`, `auto_adjust=False`, `prepost=False`,
  `actions=True` (Dividends + Stock Splits fields required), one symbol per
  request, `threads=False`. Policy source: prereg rev2 §2 (frozen
  split-exclusion protocol; coverage <80% = COVERAGE-LIMITED).
- **Runtime pins (re-hashed at preflight):** Python 3.12.3, pandas 2.1.4,
  numpy 1.26.4, yfinance 1.7.0 (`__init__.py` sha256-16 `d6eda141e64f87a6`,
  `multi.py` `61aa5ec181f26c13`, `ticker.py` `6f9a72fc35cd55da`); universe
  record `v54_universe_x2.py` sha256 `44b0d8ba…`. The future executor must
  re-verify these pins and HOLD on RUNTIME_DRIFT before any request.
- **Date policy (explicit, bounded):** explicit start/end, never `period=`;
  start = execution date − 729 days, end = execution date (exclusive).
  **Unavoidable earliest-date limit, stated plainly:** Yahoo's 1h reachback
  is ~730 days, so if executed 2026-10-16 the earliest obtainable 1H is
  ≈ 2024-10-17. The prereg target start 2023-01-01 is **not reachable** at
  1h; the lost 2023–early-2024 bytes are **not** recovered by this capture
  and nothing here implies otherwise. Consequence (frozen in the manifest):
  coverage vs the 2023-01-01 target will mark symbols COVERAGE-LIMITED, and
  fold calendars must be re-frozen from actual pulled coverage at
  qualification, before any performance is computed.

## 2. Call budget (spec §2) — defined before execution

- **52 requests maximum, exactly 1 attempt per symbol.** No blind retry, no
  fallback source, no pagination. One shared limiter, ≥1.0 s between
  request starts, process-wide.
- **Hard ceilings:** 20,000 rows and 32 MiB per symbol; 512 MiB total;
  1,800 s total wall. Any breach aborts the capture.
- **Fail closed on:** HTTP 429 / throttle text; partial response; schema
  drift (missing/renamed required field); meta drift (exchange / timezone /
  currency mismatch); unknown symbol mapping; ceiling breach.
- **Estimates:** ~282,000 rows total (45 XNYS symbols × ~505 sessions × 7
  bars ≈ 159k; 7 crypto × 17,520 h ≈ 123k); ~20–30 MB canonical CSV;
  ~3–6 min wall at limiter spacing plus observed latency.

## 3. Durable write-once archive (spec §3)

Root: `~/workspace/data_archive/yahoo_1h_clean/<capture_id>/` — a plain
workspace path, deliberately **outside** the repo's git-ignored/transient
paths (the D1 loss mode: `backtest_cache/` was git-ignored and died with a
VM replacement). Layout: `raw/<SYMBOL>.csv` (canonical raw-client output),
`actions/<SYMBOL>.actions.csv` (split/dividend evidence),
`meta/<SYMBOL>.request.json` (request/config/runtime metadata + acquisition
UTC timestamp + source), top-level `manifest.json` and `SHA256SUMS`.

Publication protocol (proven by fixture C5): write temp in the same
directory → fsync file → rename to final → fsync directory; per-file SHA256
on final bytes. **Restart/collision:** a final file is hash-verified and
skipped — never re-requested, never overwritten; an existing final path is
a WRITE_ONCE_COLLISION stop. An fsync'd **attempt journal** is appended
before each request: a symbol with an attempt record but no final raw file
is `ATTEMPT_CONSUMED_AMBIGUOUS` and HOLDs for adjudication — it is never
blindly re-requested on restart.

## 4. Session construction (spec §4) — frozen

Source of truth: `recovery_4h_20261004/spec/canonical_4h_constructor.md`
(`scanner_rules.resample_closed_4h_session_anchored`). Raw 1H bytes are
retained untouched; construction is a derived, reproducible view: convert to
America/New_York, restrict to the regular session [09:30, session_close),
bins [09:30, 13:30) → label 09:30 and [13:30, session_close) → label 13:30,
left-labeled/left-closed, OHLCV = first/max/min/last/sum. `session_close`
comes from the XNYS calendar (16:00 regular, 13:00 early close); early-close
days emit only the morning bar; no forward-fill; forming bar excluded by
causal cutoff. Crypto stays in its segregated UTC class (00/04/08/12/16/20
UTC bins) and never enters the equity baseline.

## 5. Qualification gates (spec §5) — frozen before acquisition

G1 completeness (52/52 accounted; zero silent exclusions) · G2 coverage
(≥80% of window sessions else COVERAGE-LIMITED — counted and retained,
never dropped; listing-age exceptions only with evidenced first-trade
dates) · G3 integrity (duplicates/nonmonotonic = 0 tolerance) · G4 missing
expected sessions enumerated vs the XNYS calendar · G5 impossible OHLCV = 0
· G6 timezone/DST label exactness (any UTC-anchored label = HOLD — the D1
defect class) · G7 early-close disposition · G8 split/action reconciliation
under the frozen split-exclusion protocol · G9 raw→4H conservation · G10
two-window parity across a DST boundary · G11 archive hash stability.
No favorable-window selection anywhere: the window is the manifest's, for
every symbol.

## 6. Synthetic fixture (spec §6) — trials

Driver: `run_preflight_fixture.py`. Sockets are replaced with raising stubs
**before** any other import runs; `yfinance` is never imported. Two full
runs, byte-identical results (`fixture_results.json`, sha256 `21a294cf…` — see SHA256
manifest); **8/8 checks matched in both runs; failures: none; repair
minutes used: 0.**

| Check | Proof |
|---|---|
| C0 network denial | socket layer raises; attempt counter records the probe |
| C1 manifest/order | 52 requests in exact frozen order (UNIVERSE_X + QQQ), policy pins and budget caps verified from `capture_manifest.json` |
| C2 DST labels | synthetic bars Fri 2025-03-07 (EST, −5) + Mon 2025-03-10 (EDT, −4) → 4 bars labeled 09:30/13:30 ET with correct offsets |
| C3 early close | 2025-11-28 (13:00 close) emits exactly one 09:30 bar; volume conserved vs its 4 morning 1H rows |
| C4 parity/conservation | short-window bars byte-equal full-window bars on the 4-bar overlap across the DST boundary; per-bar volume conservation exact |
| C5 write-once archive | temp→fsync→rename publication; hash matches; restart re-read byte-identical; second write refused with WRITE_ONCE_COLLISION |
| C6 gates fail closed | good frame QUALIFIED; missing / partial / throttled / schema-drift / missing-sessions / duplicate / impossible-OHLCV synthetic cases all return their named HOLD |
| C7 no engine | `pine_backtest`, `pine_signal_quality`, `v54_forward_harness`, `scanner_rules`, `yfinance` all absent from `sys.modules` |

## 7. Later execution packet (spec §7)

- **Command:**
  `python3 research_notes/yahoo_clean_capture_preflight_20261015/execute_capture.py --manifest research_notes/yahoo_clean_capture_preflight_20261015/capture_manifest.json --archive-root ~/workspace/data_archive/yahoo_1h_clean --execute`
  The executor is written at the separately authorized execution task from
  this frozen packet, reusing this package's fixture-proven archive /
  construction / gate code paths; it does not exist yet, and this preflight
  builds no machinery that talks to the vendor.
- **Estimated volume:** 52 requests, ~282k rows, ~20–30 MB, ~3–6 min.
- **Abort rules:** any fail-closed trigger → stop immediately, keep the
  partial archive as evidence, mark the capture `INCOMPLETE_HOLD`; no
  resume except per the attempt-journal rules; qualification runs only on a
  complete, 52/52-accounted archive.
- **Rollback:** the archive is additive and write-once and nothing in live
  state is ever touched, so rollback = abandon the capture directory
  (retained as evidence, marked INCOMPLETE). Prior captures are never
  deleted.

## 8. Scope confirmation

Zero vendor/API/model calls; zero downloads; zero installs; zero spend;
zero backtests; zero strategy execution or tuning; zero holdout access;
zero production changes; zero live-state writes. Deliverables are
uncommitted worktree files. After any separately authorized capture,
qualification must pass and bytes/hashes must be pinned **before** any
unchanged-strategy baseline preflight — and a qualified baseline still
would not by itself prove a deployable edge.

**Minutes used:** ~3 of the ≤45 budget (spec fetch 11:26:50Z → final
verification 11:30:00Z, VM clock reads). Repair minutes: **0**.
