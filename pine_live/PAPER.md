# Pine V3.6 Paper Phase — Operating Manual

**Status:** commissioned by Mike 2026-09-18. Engineering path (slices 1–6)
complete; this is the eight-week paper-only production dress rehearsal.

## What this phase is

The frozen V3.6 stack runs against the live data feed, **paper only**:
every signal is evaluated through the canonical reference path
(`run_cycle` with `signal_bar="previous"`, `live_exits=True`), every
decision/fill/rejection is logged, and every packet is replayed against
the reference on its pinned bars. No orders, no broker integration, no
real money, no real alerts.

## What this phase is NOT

- Not strategy research. Entries, exits, rs_top2 ranking, the 2-per-sector
  cap, the 5% portfolio-risk gate, 5 max positions, exits-before-entries —
  all frozen. No parameters change on a short run of wins or losses.
- Not a second backtest. The backtest already established expectations
  (below); the paper phase tests **engineering fidelity**, not edge.

## The three questions

The phase answers only these:

1. **Does the system behave exactly as specified?**
   Packets replayed vs mismatches (0 required), cycles run, decisions
   logged, halt state, per-cycle completeness (every cycle's evaluated
   symbols reconcile to signals + refusals + skips + pending entries).
2. **Does execution remain within the tested cost envelope?**
   Realized round-trip cost/trade vs the 25bps envelope, total execution
   leakage (fill deviation in R), detection-delay distribution
   (median/p95). Paper fills assume execution at the bar open; the report
   states the observed median detection delay in plain English.
3. **Is realized behavior statistically plausible vs the validated
   backtest?** Win rate (exact binomial 95% CI), expectancy at both cost
   legs, avg win/loss, max drawdown, longest losing streak, reason-code
   distribution — vs the locked C1 expectations, with the explicit caveat:
   *n=X trades: plausibility means cannot-reject, not proven.*

## Locked expectations (C1, for comparison — not targets to tune to)

| leg | trades | win rate | expectancy | total | max DD | Calmar | PF |
|-----|--------|----------|------------|-------|--------|--------|----|
| 4bps | 143 | 46.2% | +0.337R | +52.25% | 31.63% | 1.65 | 1.49 |
| 25bps | 142 | 45.8% | +0.280R | +39.64% | 33.79% | 1.173 | — |

Avg winner +2.212R, avg loser −1.27R. Reason codes: TAKEN 143,
RANKED_OUT 94, SECTOR_CAP 16, NO_SLOT 0, RISK_CAP 10.

Framing: ~1.4 trades/week → the 8-week phase expects **~11 trades**.
Statistical power is low by design. Losing streaks and drawdowns inside
the backtest's distribution are *expected*, not failures.

## Execution realism: dual ledger (added 2026-09-18)

**The finding.** The paper runner detects 4H signals only after the
signal bar closes (the frozen yfinance path excludes the forming bar),
but the frozen backtest assumes fills at the next bar's OPEN — a price
that is invisible at detection time. Treated as a production blocker,
not a minor caveat: the paper phase keeps **two performance records in
parallel** and measures the gap explicitly.

**Achievable-fill definition** (frozen for the paper phase):

- *Canonical fill* (existing behavior, unchanged): the next bar's OPEN —
  the backtest assumption. Preserved for comparability with research.
- *Achievable fill* (new measurement leg): the first realistically
  tradable price when the live system actually detects the signal =
  **the CLOSE of the signal bar** for entries, **the CLOSE of the
  exit-trigger bar** for exits (the last visible price at detection).

Both prices come from **pinned packets**, never fresh downloads
(history can restate under `auto_adjust=True`): the achievable entry
from the signal packet's `signal_bar_ohlcv.close`, the achievable exit
leg from the exit walk's hash-pinned bar snapshot (`trigger_bar_time`).

**Achievable-fill policy** (swappable; currently
`signal-bar-close-at-detection`, see `ACHIEVABLE_FILL_POLICY` in
`pine_live/paper/dual.py`): the achievable ledger's fill source is a
named *policy*, not a market fact. Today's policy — signal-bar close at
detection — is the honest **conservative proxy for what this
architecture can do**: hourly yfinance polling never sees the forming
bar, so the signal-bar close is the first price the current system could
actually trade. It is NOT necessarily the eventual production fill. When
a real-time feed lands, the policy upgrades to **first-actionable-quote**
— the first actually actionable quote after the signal becomes
knowable — and the achievable ledger then measures the production fill
path. Upgrading the policy is an execution-architecture change only:
**gate thresholds do not change** with the policy.

**Achievable trade construction** (measurement only — no re-simulation):

- Stop: the pinned `stop_px`, unchanged (the strategy defines the stop
  as signal-close − 1.5×ATR, and the achievable entry IS the signal
  close, so it is already consistent).
- TP1: re-anchored to the achievable entry —
  `ach_tp1 = ach_entry + (pinned_tp1 − pinned_entry)` — preserving the
  reference "TP1 = entry + 2.0×ATR" relationship.
- Exit: the canonical blended-exit formula with the exit fill leg
  replaced by the trigger-bar close. `tp_hit` and the trigger bar come
  from the canonical walk: this measures fill-price difference, it does
  not re-simulate the trade path (no alternate triggers, no slot/gate
  replay).
- R recomputed via the canonical `pb._outcome` at both cost legs.

**Per-trade drag** (positive = achievable worse, a cost):

- `drag_r` = canonical net R − achievable net R (per cost leg).
- `drag_bps` = `drag_r_4bps × risk_dollars / size × 10000`, where `size`
  is the canonical notional dollars — the dollar drag as bps of trade
  notional, a same-risk-dollar comparison. (The 108bps headroom is the
  25bps-leg expectancy, +0.280R/trade, expressed as bps of average
  notional: the per-trade edge that execution costs must not eat.)

Every paper trade records both fills (`fills.jsonl` gains
`achievable_fill_px`; `trades.jsonl` gains the `ach_*` leg and the drag
fields). The report's "Execution realism: canonical vs achievable"
section shows both R/trade figures, mean/median bps drag, trade counts,
and both realized equity curves. Pure instrumentation: strategy, entries,
exits, ranking, and parameters are untouched, and achievable-computation
failures record nulls + loud logs — they never break the canonical
wake-up and never halt.

## Proposed production gate (NOT approved — pending Mike's sign-off)

**Status: PROPOSED.** Reported in `report.md`/`report.json` only; it is
**not** enforced as a halt and no code path acts on it.

No real-money deployment until ALL THREE hold:

- **(a)** achievable-fill expectancy ≥ **+0.15R/trade** (4bps leg);
- **(b)** mean detection-delay cost ≤ **108bps/trade** — the validated
  execution headroom (25bps-cost backtest did +0.280R/trade vs +0.337R
  at 4bps);
- **(c)** a real-time feed exists that **eliminates or directly
  quantifies** detection latency.

Gate status is `PASS` / `FAIL` / `INSUFFICIENT_DATA`. It reports
`INSUFFICIENT_DATA` (never inferred) until ≥20 closed paper trades with
dual data exist. Legs (a)/(b) are machine-measured; leg (c) is a **human
attestation** — the machine can never self-certify it. Attest by writing
`paper_state/gate_c_attestation.json`:

```json
{
  "attested_by": "Mike",
  "attested_at": "2026-..-..",
  "feed": "<what real-time feed, and how it was validated>",
  "latency": "<eliminated | quantified: measured detection latency>"
}
```

Overall `PASS` requires all three legs; a failed measured leg or a
missing attestation is `FAIL` (the per-leg detail says which blocks
deployment).

**If the achievable ledger ever fails the gate while the canonical leg
holds, the investigation goes to data timing / execution architecture —
V3.6 stays frozen, no strategy changes.** A failing achievable leg means
the live architecture cannot reproduce the tested entry assumption; it is
not evidence the strategy is wrong and it never authorizes touching
entries, exits, ranking, or parameters. The fix path is a better feed /
faster detection (the achievable-fill policy upgrade), not research.

## Operating rules (Mike's standing rules)

- No manual cherry-picking or overrides. Take every finalized paper
  signal the stack allows.
- Log every entry, exit, rejection, sector-cap skip, ranking decision,
  and risk-gate veto.
- Record theoretical vs paper fill and total execution leakage.
- Reconciliation runs continuously (every wake-up replays every new
  packet). Any category 2–7 mismatch is a halt condition.
- Category 1 (data/vendor differences) is classified separately and never
  silently.
- Compare against established expectations: losing streaks, drawdown
  distribution, cost sensitivity.

## How to run

One wake-up (cron or manual):

```
cd ~/workspace/quality-flow-scanner-v5
python -m pine_live.paper.runner [--state-dir pine_live/paper_state]
```

Exit codes: `0` = ok (or already halted); `1` = usage/internal error;
`2` = halted this wake-up (HALT written — see below).

First run ever initializes watermarks to the latest bar opens and runs
**zero cycles** — paper starts now; history is never backfilled as paper.

## Where artifacts live (under `pine_live/paper_state/`)

- `portfolio.json`, `watermarks.json`, `download_health.json` — persisted
  state (atomic writes, fsync).
- `packets.jsonl` — signal + portfolio-decision packets (the audit trail).
- `exit_packets.jsonl` — exit packets with hash-pinned bar snapshots.
- `snapshots/` — bar snapshots referenced by packets.
- `dedup.jsonl`, `outbox.jsonl`, `delivery.jsonl`, `actions.jsonl` —
  delivery layers. **The outbox is observational only**: `paper_sender`
  returns True and records nothing external (verified by reading
  `pine_live/alerts.py`). Nothing leaves the machine.
- `cycle_log.jsonl` — per-cycle operational events.
- `ledger/{decisions,fills,trades,rejections,equity}.jsonl` — the paper
  ledger (derived convenience view; packets are the audit trail of
  record). `fills`/`trades` carry the dual-ledger achievable leg
  (see "Execution realism" above).
- `gate_c_attestation.json` — human-written real-time-feed attestation
  for production-gate leg (c); absent until Mike attests.
- `status.json` — per-cycle records, cumulative replay counts, flags.
- `report.md` / `report.json` — the three-question report, regenerated
  every wake-up.
- `HALT` — present only when halted.

## Halt conditions (any → HALT file + non-zero exit)

- Any replay mismatch (packet vs canonical on pinned bars).
- Any exit-eval skip for a symbol that HAS a bar at the cycle's bar_time.
- Any exception escaping `run_cycle`, or state persistence failure.

The runner stays halted until a human clears it. **Clearing a halt is a
human decision, never code:**

1. Read the HALT file (reason + classification attempt + context).
2. Root-cause it: logic bug (fix code, add a regression test), vendor
   data difference (confirm category 1 with evidence), or operational
   issue.
3. Document the root cause. Get explicit sign-off.
4. Delete `paper_state/HALT`. The next wake-up resumes from persisted
   watermarks.

Log-but-continue (flagged in `status.json`, never halting): per-symbol
download failures (fail closed; flagged at 5 consecutive wake-ups), SPY
fallback (`rs_score` → −inf with logged reason), expected misaligned exit
skips, timestamp fail-closed events (shouldn't happen in normal
operation — investigate if flagged).

## Suggested schedule

One wake-up per hour, a few minutes after the hour (bars are detected
when the download sees them closed; the forming bar is always excluded
by the frozen download path, so detection delay is measured, not
assumed):

```
35 * * * * cd ~/workspace/quality-flow-scanner-v5 && python3 -m pine_live.paper.runner >> pine_live/paper_state/cron.log 2>&1
```

Do NOT create this cron without Mike's explicit go-ahead. Watermarks make
wake-ups idempotent: no new bars → no cycles → no state changes.

## Code layout (new code only — no existing module modified)

- `pine_live/paper/runner.py` — the wake-up (`python -m pine_live.paper.runner`)
- `pine_live/paper/ledger.py` — append-only JSONL ledger (dual-leg fields)
- `pine_live/paper/dual.py` — achievable-vs-canonical fill math (pure,
  read-only instrumentation; imports the canonical blend formula but
  changes no strategy code)
- `pine_live/paper/verify.py` — replay verification + halt logic
- `pine_live/paper/report.py` — the three-question report + the
  "Execution realism: canonical vs achievable" section and the proposed
  production gate (reported only, never a halt)
- `pine_live/paper/state.py` — atomic persistence helpers
- `pine_live/tests/test_paper.py` — 13 tests + dual-ledger cases, fake
  provider, no network

## Sign-off gate

After ~8 weeks (or ≥10 paper signals if the pace is slow): Mike reviews
(a) the three-question report series, (b) the halt/incident log (must be
empty of unresolved category 2–7), and (c) the reconciliation record.
Production readiness is binary — no discrepancy is "close enough."
Real money remains a separate Mike decision after the paper phase.
