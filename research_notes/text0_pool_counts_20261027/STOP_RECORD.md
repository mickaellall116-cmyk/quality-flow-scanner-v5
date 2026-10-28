# Text 0 — §5 pool-count staging session: SESSION LOG (STOP)

Session date: 2026-10-27 ET / opened 2026-10-28T00:59Z, stopped 2026-10-28T01:02Z.
Operator: Muse, under Mike's direct GO in chat (2026-10-27) adopting
Text 0 of the G7 decision package (commit `acbb526`).
Outcome: **STOP before any holdout access. No counts were produced.
No holdout data was opened, read, or computed on in this session.**

## What Text 0 required

A single outcome-blind staging session: the §5 matching code, at the
freeze record's pins, run in pool-sizes-only mode over the sealed
holdout window (2023-10-19 → 2024-09-15) for Tier 2 and Tier 3 at the
frozen ladder step (c); permitted outputs limited to per-event
eligible-pool counts, the dropped-event count, and the event-mix
composition summary (by symbol and session bin).

## Pin verification (all verified before any run)

| Artifact | Pin of record | Verified |
|---|---|---|
| G7_DECISION_PACKAGE.md (commit `acbb526`) | manifest sha256 `99fdb9b770bca242fc3dcce840254030fc31d5cc1a9f09066e829787a2c6ee22` | MATCH |
| PREREG_V10.md (§5) | sha256 `29a0477a13e52ff4467193f69df7ef107048a8801f64c61f43de28d40d2850c6` | MATCH |
| §5 matching code — EXP-14 execution code, corr2 pin: `research_notes/equity43_dev_buy_decisionb_corr2_20261025/code/exp14_buy.py` (package commit `7a0e487`) | P11_PINS_V10.json `exp14_study_pins[0]` sha256 `77bd53e82963d65ab743a57f1eff0d23b54467a0e17aaf1831b42e6e96b6f3d8` | MATCH |

## The blocker (precise)

The pinned matching code is DEV-bound by compiled-in constants and
cannot execute over the holdout window:

1. `exp14_buy.py` line 137: `EXPECTED_FIRES = 2892` — the DEV P7
   all-fire census. `run_pool_counts()` (line ~409) raises
   fail-closed unless the loaded inventory's total signal fires
   equal 2892 exactly. A Tier 2 + Tier 3 holdout inventory
   (30 symbols, 227 sessions) is a different domain and cannot
   satisfy the DEV census; the check fires before any pool is
   counted.
2. Lines 138–139: `DEV_START = "2024-09-16"`, `DEV_END =
   "2026-10-16"`, with `_check_dev_ts` rejecting non-DEV session
   dates on the analysis path — the code's domain is the DEV
   window by construction.
3. The returns path is separately gated (`RETURNS_ENABLED = False`,
   line 143) and was never invoked; that gate is not the blocker.
   The pool-count path itself (`eligible_pool`) is a pure function
   of inventory fields and computes no outcome quantity — the
   outcome-blind design is sound; only the domain binding blocks
   execution.

### Empirical demonstration (synthetic data only)

The pinned code was run in `--mode pool-counts` against a fabricated
60-row synthetic inventory (1 symbol, 2 signal fires; sha256
`84a2aa3bb49d27b89e73540800ac26aea32e8885d0d49eb6c8bcc37e75a0b70f`), built solely to
exercise the entry path:

```
FAIL-CLOSED: inventory domain fires 2 != P7 census 2892
exit code 1 — no report file written
```

The refusal is the code's own fail-closed census reconciliation,
exactly as designed for DEV. No real data of any window was used in
the demonstration.

## Why the session stopped instead of adapting

Text 0 authorizes the session "under … frozen code hash — the
pinned matching code at the freeze record's pins." Producing the
counts would require changing the pinned code (generalizing the
census/domain binding) or writing new counting code. The pinned
code's own governance states the rule for such changes: a new
version plus a new pin plus authorization. A successor pin is a
freeze-procedure step requiring its own adjudication; it is not
inside Text 0 as drafted, and improvising it inside a sealed-window
access would break the frozen-code condition that makes the counts
admissible. Per the session's hard bounds, the failure is reported,
not retried with changes.

## Attestation

- Holdout bars for every symbol were NOT accessed in this session;
  the stop occurred at code verification, before any data step.
- No performance quantity of any kind was computed, viewed, or
  recorded. The only executions were hash verifications and the
  synthetic-fixture demonstration above.
- Tier 2 / Tier 3 per-event §5 pool counts remain OPEN
  (FREEZE_CHECKLIST row O6 unclosed by this session).

## What would unblock (for adjudication — NOT executed)

1. A corr3-style successor of the pinned matching code:
   byte-identical logic, with the DEV census/domain binding
   replaced by a binding to a pinned holdout inventory (its
   SHA-256 and its own census recorded at staging), independently
   reviewed and re-pinned in the freeze record — the same
   successor discipline used for corr1/corr2.
2. A pinned holdout inventory builder producing the code's row
   schema for the Tier 2 (19) and Tier 3 (11) symbols over the
   sealed window, its output hash recorded as the successor's
   bound input.
3. On those pins entering the freeze record, the Text 0 session
   runs as drafted under the successor pin.

## Files in this staging directory

- `SESSION_LOG.md` — this record.
- `work/` — pin-verification scratch (extracted pinned texts and
  code, the synthetic inventory, command outputs). No holdout data,
  no counts, no outcome fields anywhere in these files.
