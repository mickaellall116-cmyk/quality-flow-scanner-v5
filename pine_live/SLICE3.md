# SLICE 3 — Duplicate suppression + paper alert delivery

**Status:** built 2026-09-18. All 29 tests pass (13 slice-1 + 5 slice-2 +
11 slice-3). No regressions. Paper-only.
**Scope (Mike's commission):** duplicate suppression FIRST, then alert
delivery. Strict contract: delivery plumbing must be causally separated
from trading logic — structurally incapable of influencing it, not merely
observed not to.

## What was built (`pine_live/` — new files only, nothing existing modified)

| File | Purpose |
|---|---|
| `dedup.py` | `DedupStore`: persistent exactly-once gate on finalized-decision identity. `dedup_key` = sha256(signal_id \| decision_time \| state_seq_after), pinning the exact portfolio-state version the decision was finalized against. `check_and_claim` returns True exactly once per key; later calls return False and log `duplicate_suppressed`. **Stdlib only — zero imports from pine_live or any reference module.** Consulted strictly AFTER the decision is finalized and packet-logged. |
| `alerts.py` | Paper alert delivery. `build_alert_payload` copies fields from the finalized decision packet ONLY (missing field = loud KeyError, never invented). `PaperOutbox`: local append-only JSONL outbox, idempotent enqueue on deterministic `alert_id`. `deliver_pending`: injectable sender; ANY sender exception is caught and logged as a parity-spec **category-7** event; the function **never raises**. Retries reuse the same alert_id (idempotent). **Stdlib only.** |
| `cycle.py` | The ONLY meeting point of delivery and decisions, and it is one-directional: portfolio decides -> packet logged -> dedup consulted -> alerts enqueued -> delivery attempted. `run_timestamp` rolls the state back to its exact pre-t snapshot on ANY decision-engine exception (unknown sector label etc.), logs a `portfolio_refused` packet, takes no entries, fires no alerts. `safe_evaluate_live` fails closed on download failure (logged, returns None, no signal). |
| `tests/test_slice3.py` | 11 tests (below). |

## Acceptance proof (Mike's contract, incl. the three causal-separation proofs)

**(f) Dependency direction — structural.** AST-level import-graph test:
`dedup.py` and `alerts.py` import **stdlib only** (`hashlib, json, os,
datetime, traceback`). No import path back to the decision engine or
portfolio state exists — the one-way data flow is proven from the source,
not from observed behavior.

**(g) Fault injection.** A sender that raises mid-cycle: no exception
escapes `run_timestamp`; portfolio-state sha256 identical to the
control run; decision packet intact (exactly one finalized packet);
`decide_entries` called exactly once (no recalculation); the failure
logged as a category-7 `alert_delivery_failed` event.

**(h) Causal inertness — full window twice.** The research window driven
through `run_timestamp` with delivery layers **enabled** vs **physically
disabled** (never invoked, not merely idle): per-timestamp decisions
**byte-identical** across all timestamps. The delivery layers cannot
influence selection — proven, not assumed.

**(b) Dedup.** Crafted contested bar run twice (rerun + simulated retry
from identical prior state): decisions byte-identical; exactly one
`acted` action per finalized-decision key (4 acted / 4 suppressed);
exactly one paper alert (the single TAKEN). Dedup-on vs
decide_entries-called-directly: byte-identical decisions.

**(d) Full-window parity with delivery enabled.** Locked C1 reproduced
**exactly**: 143 trades, +0.337R, 52.25%, DD 31.63%, Calmar 1.65;
reason breakdowns TAKEN=143, RANKED_OUT=94, SECTOR_CAP=16, NO_SLOT=0,
**RISK_CAP=10**; 143 paper alerts delivered, 263 dedup claims.

**(c) Failure drills (parity spec C9).** Download killed -> `None`,
`evaluation_failed` logged, zero packets. Unknown sector label ->
whole timestamp refused, state rolled back exactly (no positions, no
new events, counters zero), `portfolio_refused` packet logged, zero
alerts, zero dedup claims. Alert delivery failure -> (g) above.

**(e) No trading surface.** Banned-pattern static scan covers all new
modules; alerts terminate at the caller-supplied local outbox path —
no URLs, no keys, no remote-notification wiring anywhere.

## Critical correction honored: the 5% portfolio-risk gate is preserved

Per Mike's correction, the canonical locked stack is FOUR components:
V3.6 entries/exits, rs_top2 ranking, E1 sector cap, **and the 5%
portfolio-risk gate**. The gate lives in `pine_live/portfolio.py`
(branch order RANKED_OUT -> NO_SLOT -> SECTOR_CAP -> RISK_CAP -> TAKEN,
mirroring `pine_stack.simulate_stack` exactly) and was **not touched,
reordered, weakened, or reinterpreted** in this slice. Evidence: the
full-window run reproduces **RISK_CAP=10** — the gate fired 10 times,
exactly as in the validated C1 path. `cycle.py` never re-runs, skips,
or reorders decision branches.

## Explicitly NOT built

- **Real alert wiring (phone/chat/email/SMS): NOT done.** The outbox is a
  local JSONL file. Wiring real notifications is a separate, explicit
  Mike decision — no notification code, credentials, or endpoints exist
  in this slice.
- Per-bar V3.6 exit evaluation for live open positions (state machine
  consumes exit events; nothing generates them live yet).
- The multi-symbol live evaluation cycle (per-bar fan-out across UX51).
- The Part-B reconciliation job (daily live-vs-reference diff).
- Any trading, order, or execution integration.

## Test summary (29/29 green)

- Slice-1 (13) and slice-2 (5): unchanged, all pass — no regressions.
  (One fix during build: the word "broker" in the updated package
  docstring tripped the slice-1 banned-pattern scan; reworded. The scan
  doing its job.)
- Slice-3 (11): dependency-direction static; dedup-key determinism;
  rerun/retry single-action; dedup on/off byte-identical; fault
  injection; alert-payload derivation; full-window C1-exact with
  delivery; full-window enabled-vs-disabled byte-identical; download
  drill; unknown-sector drill; no-trading-surface.
