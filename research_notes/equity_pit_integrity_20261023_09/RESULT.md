# QF-EQUITY-PIT-INTEGRITY-20261023-09 — RESULT

**Governing text:** Issue #1 comment 6373962624 (ChatGPT adjudication of the -08
exploratory package `ca6edc6`: LEDGER ARITHMETIC PASS / EXECUTION INTEGRITY
HOLD — B1, B2, B3). **Mode:** OFFLINE only. No vendor calls, no new data, no
credits (program Twelve Data total stays 24), no sealed-HO access, no tuning,
no production/frozen-strategy change. **No historic performance was run on
patched code** — this package proves defects and fixes on synthetic fixtures
only, per the assignment. The -08 4-name report is preserved unchanged as a
labeled ledger-reconciled exploratory artifact.

**Verdict:** B1 and B2 are **proven defects** in the frozen source (fail-before
on pinned originals, synthetic fixtures), and the research-only as-of fork
**passes every assertion** (5/5). The coincident-entry ordering of the staged
ranked stack is **input-order dependent** in the original (proven) and
canonical in the fork. B3 terminal-open censoring for the -08 DEV window is
**quantified: 0 positions** (count only). All corrections are RESEARCH-ONLY
and UNADOPTED; a corrected-performance run is a later, separately framed step.

---

## B1 — SPY daily benchmark future-close leak (ranking gate)

**Mechanism (pinned source).** The -08 driver (`run_diagnostic.py` lines
310–320, stage sha256 `8362a6a7…`, mirroring `load_benchmarks` handling) built
SPY daily bars from the full day and indexed each at **ET midnight** of the
session date. `pine_ranking.compute_features` (lines 95–107, `77afae0d…`)
calls `pine_signal_quality.bench_ret` (lines 49–61, `b1b39ee8…`), which
selects the last daily bar with index ≤ the signal instant. For a signal at
09:30 or 13:30 ET on day D, the selected bar is day D's own — and its Close
is the **16:00 close, hours in the future**. The helper's "no lookahead"
docstring is wrong for midnight-stamped daily bars.

**Fixture (tests/test_pit_integrity.py, B1).** Synthetic SPY 1h bars over the
15 sessions 2025-04-28 → 2025-05-16 (2025-05-16 is one of the five real-ledger
double-entry dates; timestamps only, all prices invented); two synthetic
candidates signaled on 2025-05-16 at 09:30 and at 13:30 ET. The final bar of
2025-05-16 is then mutated ×40 (an extreme not-yet-known close) and the RS
features recomputed through the frozen `compute_features → bench_ret` path.

| impl | signal | rs normal | rs with mutated unfinished close | invariant |
|---|---|---|---|---|
| original | 09:30 | (−0.05320, −0.09091) | (−45.32906, −45.36677) | **VIOLATED** |
| original | 13:30 | (−0.05378, −0.09115) | (−45.32964, −45.36701) | **VIOLATED** |
| fork | 09:30 | (−0.05583, −0.09354) | (−0.05583, −0.09354) | HOLDS |
| fork | 13:30 | (−0.05641, −0.09378) | (−0.05641, −0.09378) | HOLDS |

**Fix (fork/asof_benchmark.py).** Frozen as-of policy, decided from time
semantics: *a daily benchmark bar becomes visible only when its session
completes.* Daily bars are stamped at **16:00 ET on the session date**
(early-close sessions complete at 13:00 but are stamped 16:00 uniformly —
conservative: later, never earlier). Aggregation is byte-identical to the
original construction; only the stamp changes. `bench_ret` itself is **not
modified** — with completion-stamped bars its existing selection rule is
causally correct. Fork rs values differ slightly from the original's even
unmutated (the window endpoints shift to the last completed session); that
shift is the correction, disclosed here, and no performance meaning is
claimed for synthetic prices.

## B2 — mark-to-market same-bar future-close leak (C0 **and** staged stack)

**Mechanism (pinned source).** `pine_backtest.py` lines 233–236 (`447a9a13…`):
`mark(sym, t)` does `searchsorted(t, "right") - 1` on 4H bars stamped by
START, so at an event timestamped at the current bar's OPEN it returns that
still-unfinished bar's Close. `marked_equity(t)` feeds entry sizing
(line ~252) and the drawdown curve. **The staged `pine_stack/pine_stack.py`
lines 44–47 (`839e4800…`) carries its own identical `mark()`** — the defect is
present in the ranked stack as well, as the adjudication suspected.

**Fixture (B2a/B2b).** One synthetic symbol, six invented 4H bars; trade A
opens at bar 1, trade B opens at bar 2 while A is open. Bar 2's close — not
knowable at B's entry instant — is mutated ×30.

| impl | path | (final equity, marked eq @ B entry) normal | mutated | invariant |
|---|---|---|---|---|
| original | C0 `simulate_portfolio` | (10158.71, 10060.08) | (10627.21, **478725.60**) | **VIOLATED** |
| original | stack `simulate_stack` | final 10158.71 | final 10627.21 | **VIOLATED** |
| fork | C0 | (10158.55, 10020.00) | (10158.55, 10020.00) | HOLDS |
| fork | stack | final 10158.55 | final 10158.55 | HOLDS |

On the original, a single unfinished close inflates marked equity at B's
entry ~47× and changes B's size and the final equity — B2 threatens the -08
run's reported return/drawdown statistics (not the per-trade R ledger, which
ChatGPT verified independently).

**Fix (fork/pine_backtest.py, fork/pine_stack.py).** *Mark at the latest bar
COMPLETED at or before t* (bar end = start + 4h for this 4H engine):
`idx = (index + 4h).searchsorted(t, "right") - 1`. The original `iloc[0]`
fallback is retained for total-function compatibility; it is unreachable for
an open position in engine flow. Nothing else in either file changes (see
DIFF files).

## Ordering audit — coincident entries in the staged ranked stack

The -08 ledger has **five entry timestamps with two candidates each**:
2025-05-16 13:30 ET, 2025-09-05 13:30 ET, 2025-10-17 13:30 ET,
2026-02-11 13:30 ET, 2026-04-16 13:30 ET.

Audit of `simulate_stack` (and C0): exits at a timestamp are processed before
entries (stack: exits loop first; C0: event sort key `(t, kind)`, exits
kind 0) — deterministic. The ranked entry path is not: the original breaks
RS ties by **candidate index** (`scored = [(-rs, i)]; scored.sort()`), so at
a contested timestamp the taken candidate depends on the input order of
`all_trades`. (C0's event sort is stable and within-kind input-ordered — the
same dependence class, though C0 takes no ranking decisions.)

**Fixture (ORD).** Four fillers open (distinct earlier timestamps), one free
slot at the real ledger timestamp 2025-09-05 13:30 ET, two candidates with
equal RS and invented prices; `all_trades` permuted.

| impl | taken at T, input (AAA,BBB) | taken at T, input (BBB,AAA) | invariant |
|---|---|---|---|
| original | {AAA} | {BBB} | **VIOLATED** |
| fork | {AAA} | {AAA} | HOLDS |

**Fork fix.** Canonical identity key `(−rs, symbol, signal_idx, index)` —
the index remains only as a final, unreachable tiebreak (symbol + signal_idx
already identify a candidate); the non-ranked path gets the same canonical
key. In the -08 run this changed nothing (caps never bound; 61/61 taken), but
with binding caps across a 43/44-name universe the original behavior makes
results a function of list order — and because B1 contaminates rs itself,
the -08 ranked order at coincident timestamps was additionally a function of
same-day future closes.

## B3 — terminal open-trade censoring, quantified (count only)

**Method (coverage/coverage_tally.py).** The -08 stage pipeline
(`run_diagnostic.py` phases 0–2, imported read-only; phase 3 never called)
rebuilds the admitted DEV frames and corrected 4H bars for NVDA/TSLA/AAPL/SPY.
A counting variant of the pinned `gen_candidates` — produced by a mechanical
transformation whose only change replaces the final return with a
terminal-position capture (unified diff printed in coverage_output.txt) —
is run per symbol; its closed-trade list is asserted identical to the pinned
original's before its terminal count is believed. Zero P&L: no portfolio
simulation, no R, no performance figure of any kind.

| symbol | 4H bars | closed candidates | terminal open at window end |
|---|---|---|---|
| NVDA | 1,043 | 22 | 0 |
| TSLA | 1,043 | 11 | 0 |
| AAPL | 1,043 | 12 | 0 |
| SPY | 1,043 | 16 | 0 |
| **total** | | **61** (= -08 ledger) | **0** |

Reproduced identically in two executions. **For this window and symbol set,
censoring removed nothing**: no candidate position was open at the cutoff, so
there is no censored-end exposure or marking impact to quantify for -08. The
construction property itself (gen_candidates emits only closed trades)
remains true in general and must be re-tallied for any future window.

## Hashes — originals and fork

| file | sha256 |
|---|---|
| `pine_backtest.py` (original, repo = td08 stage) | `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5` |
| `pine_ranking/pine_ranking.py` (original) | `77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6` |
| `pine_signal_quality/pine_signal_quality.py` (original) | `b1b39ee8d0bd4bbb1387b3ce54c7345c1f8dd622f94a5ed390c989fed1d39e69` |
| `pine_stack/pine_stack.py` (original, td08 stage = in-repo archival copy) | `839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb29a5956dfcefa` |
| `run_diagnostic.py` (-08 stage driver) | `8362a6a765edc0cf6f21950ea84ef317dd3c9afa5b6e544810b624eb0489b0ee` |
| `fork/pine_backtest.py` (patched) | `becea0824486003daef386b49e137a83ffdf22c1e2d145136498919102fc42f2` |
| `fork/pine_stack.py` (patched) | `30594231ffc3bac27303f96310e8f274229415c890c371f4dbdfcdb54156cda4` |
| `fork/asof_benchmark.py` (new) | see SHA256_MANIFEST.txt |

## Minimal independent rerun requirements

1. **Original engine tree** (any directory layout matching the -08 stage
   `engine/`): `pine_backtest.py`, `pine_ranking/`, `pine_signal_quality/`,
   `pine_exposure/` from the repo working tree at the hashes above;
   `pine_stack/` from
   `research_notes/recovery_4h_20261004/cp1_evidence_closure/archival_sources_v1/pine_stack/`
   (same hash). The -08 stage tree `~/workspace/qf_td08_stage/engine` is
   hash-identical to this reconstruction.
2. **Fork tree** = original tree with `fork/pine_backtest.py` overlaid at the
   root and `fork/pine_stack.py` overlaid at `pine_stack/pine_stack.py`.
3. **Fixtures** (Python with pandas 2.2.3; the -08 stage venv qualifies):
   `python tests/test_pit_integrity.py --impl original --engine <orig-tree>`
   → expect exit 1, 0/5 assertions hold;
   `python tests/test_pit_integrity.py --impl fork --engine <fork-tree>`
   → expect exit 0, 5/5 hold. Full captured output: tests/test_output.txt.
4. **Coverage tally**: requires the -08 stage (`run_diagnostic.py`,
   `session_table.json`, engine tree) and the qf-data-archive pilot bytes
   (`captures/td_pilot_20261023/`, archive commit `45496f8`, SHA256SUMS
   re-verified inside phase 0); DEV legs only — HO files are hash-checked by
   the archive manifest but their market content is never parsed.
   `python coverage/coverage_tally.py` → coverage_tally.json (closed 61,
   terminal open 0).

## Bounds and state

PAUSED production untouched and re-proved: harness `ce7c902c…` identical
before/after, `PAUSE_NEW_ENTRIES` present, `RESUME_NEW_ENTRIES` absent; all
work was done on copies in an isolated stage. The next 39 equity assets
remain **UNACQUIRED** and SMCI/HO remains `NOT_EVALUABLE_PROVIDER_VOLUME`;
the broad 43-name capture/test remains **HOLD** pending complete qualified
history and separate authorization. These fork corrections are candidates
for adjudication/adoption — nothing here adopts them, and no corrected
performance figure exists or is claimed.
