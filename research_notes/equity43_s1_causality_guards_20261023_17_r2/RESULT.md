# QF-EQUITY43-S1-CAUSALITY-GUARDS-20261023-17 r2 — RESULT

**Verdict: PIN_INVENTORY_HARDENING_PASS** — the one bounded reporter
correction is complete. The r2 comparison artifact carries a
structured exact pin inventory; the successor reporter
(`report17r2.py`) requires the exact key set and exact value for
every pin and re-derives DECISION_PARITY_PASS from the genuine r2
artifact (CLI exit 0). Every forged, missing, renamed or
wrong-valued pin mutation STOPs (CLI exit 2 where exercised).
**S1 launch remains HOLD** — this is reporter hardening only, not
S1 clearance and not edge evidence.

Governing text: GitHub Issue #1 comment 6380534722 (ChatGPT
independent source adjudication of -17 r1, package 4b60d58).
ACK: Slack TS 1792821524.950179; bridge commit 437cd2f.
Single-dispatch check CLEAR before any file operation (no r2 stage
dir, no r2 package path, no pre-execution commits for this revision
on origin/main; head edb9ff5). The -17 r1 stage stayed frozen as
completed-lane evidence; r2 staged separately.

## The gap (r1, as adjudicated)

`report17.py` accepted pin evidence as:

```python
pins = inv.get("pins")
isinstance(pins, str) and pins.startswith("PASS")
```

and the committed r1 artifact contained only
`"pins": "PASS (ref P0/P1 as -15)"`. Deleting or altering the actual
source/data/receipt/pause pins while leaving any `PASS ...` label
could still satisfy the reporter.

## What r2 changed (and only this)

1. **Structured exact pin inventory** in the successor artifact
   (`compare17r2_fork17.json`, sha256 465c4fa6526404fff9…). The
   artifact is the committed r1 artifact with ONLY
   `sections.inventory` replaced and a top-level `revision` /
   `artifact_note` added — every decision-bearing section is carried
   byte-identical (battery check K7 proves deep equality of all
   non-inventory sections and top-level fields). No comparison was
   re-run and no decision content was regenerated; the reason for
   the carry-over is disclosed here and in the artifact itself.
   The pin VALUES were recomputed by `emit_inventory17r2.py`,
   which re-runs phase0()/phase1() of the pinned -13 reference
   driver against the same committed stage sources the r1 run used
   (file pins, archive SHA256SUMS verification on a fresh clone,
   PAUSED production pins, full receipt-chain re-walk, manifest
   roots recomputed, pilot receipts field-verified) and recomputes
   the sector-map hash exactly as the comparison harness does. The
   emitter is deterministic: re-running it reproduces the artifact
   byte-for-byte (same sha256). P0/P1 re-verification passed with
   zero failures at emission time.

2. **Successor reporter** (`report17r2.py`): `inventory` must be
   exactly `{"pin_inventory_version": "structured-v1", "pins": {…}}`;
   the pins object must have EXACTLY the expected 20 keys and every
   value must equal its pinned expected value exactly (nested dicts
   by deep equality); the inventory's experiment/sector pins must
   also agree with the `config_pins` section. A free-form string —
   forged or genuine — is refused. All other report17 checks are
   unchanged, byte for byte in logic.

3. **Negative battery** (`test_reporter17r2.py`,
   `reporter17r2_battery_stdout.txt`): **33/33 checks passed** —
   7 controls + 21 pin mutations + 5 CLI exit-code checks.
   Mutations, all STOP: forged `"PASS forged"` string; the r1
   free-form string itself; missing pin key; renamed pin key;
   wrong observer SHA; wrong receipt root (pilot manifest); wrong
   data root (child manifest); wrong session-table/calendar pin;
   wrong PAUSED harness SHA; PAUSED sentinel flipped (both
   directions); wrong source pin; wrong chain head; wrong
   receipts-verified count; hidden archive mismatch; wrong pilot
   receipt SHA; inventory section deleted; extra pin key; wrong
   inventory version; recorded-verdict disagreement; nested
   source-pin deletion. CLI exit codes verified: genuine artifact
   exit 0 / DECISION_PARITY_PASS; forged, missing-key,
   wrong-observer and wrong-calendar mutations exit 2 / STOP.

## The pin inventory (20 named fields, exact values)

- `observer_module` = `fwd_observer17.py`;
  `observer_module_sha256` = 929c1bc4cac34384… (committed package
  blob; both stage copies verified byte-identical to it)
- `source_pins` — the 14 frozen P0 file pins: successor engine
  (pine_backtest 874d2a9b…, pine_stack 8d4a964f…), pristine -09 fork
  (becea082…, 30594231…), shared scanner_rules 62aa743a… /
  pine_ranking 77afae0d… / pine_signal_quality b1b39ee8… /
  pine_exposure 9f646161…, frozen originals (447a9a13…,
  839e4800…), asof_benchmark f0f4582c…, and the session-table /
  calendar pin `session_table.json` = 00c5555c26d39144…
- `experiment_config_sha256` = 87b8285a522ba0e3…;
  `sector_map_sha256` = a91222c7a27e83d2…
- Manifest roots: child c5628652c5bf59d8…, parent
  ca49892062f1ac5d…, pilot 79ccdd128e0b3653… (committed ==
  recomputed for child and parent)
- Receipt chain: `child_chain_receipts_verified` = 54,
  `child_chain_head` = c129e95fc404deff…,
  `legs_without_receipt_quarantined` = 23;
  `pilot_receipts` — response SHA + rows for NVDA (3654), TSLA,
  AAPL, SPY (3655 each)
- Archives: continue-11 capture 158 files / 0 mismatches; pilot
  capture 22 files / 0 mismatches (against committed SHA256SUMS)
- PAUSED evidence: `paused_harness_sha256` = ce7c902ce182683c…,
  `pause_new_entries_present` = true,
  `resume_new_entries_present` = false

## Controls (reporter outputs in-package)

- Genuine r2 artifact under report17r2 → DECISION_PARITY_PASS,
  exit 0 (`report17r2_fork17.txt`).
- The r1 artifact under report17r2 → STOP, exit 2
  (`report17r2_on_r1artifact.txt`): the free-form label that r1's
  reporter accepted is now refused — the correction itself, proven
  on the artifact that carried the gap.
- -16 orig15 artifact under report17r2 → STOP, exit 2
  (`report17r2_on_16orig15.txt`); -15 artifact → STOP, exit 2
  (`report17r2_on_15artifact.txt`).
- -16 patched artifact under its own reporter (report16) stays
  PASS — exercised as control K2 in the r2 battery and as C4 in the
  preserved r1 battery. (Under report17r2 it STOPs, correctly: it
  predates the structured inventory; its PASS home is report16.)

## Preserved suites — no regressions

- r1 reporter battery (`test_reporter17.py`): **27/27**
  (`reporter17_battery_rerun_stdout.txt`) — including the original
  exit-deletion exploit still reproduced on report16 and STOPped
  on report17.
- -15 adversarial suite on the -17 fork (`test_fwd_parity.py`):
  **18/18** (`test15suite_fork_rerun_stdout.txt`).
- -16 regression suite on the fork
  (`test_decision_parity_repair16.py`): **10/10**
  (`test16suite_fork_rerun_stdout.txt`).
- The observer, strategy sources, and all frozen pins are
  untouched by r2; -15/-16/-17-r1 packages untouched.

## Labeling (held, per the governing comment)

Live row availability/latency stays **UNMEASURED**. The synthetic
`emitted_at` evidence proves bin-close emission logic once a
completed 1h row is ingested; it says nothing about provider
delivery timing. No live-timing claim appears anywhere in this
package. Live feed rights/latency, G4 adoption and the
post-2026-10-16 calendar remain UNQUALIFIED, exactly as in r1.

## Bounds held

Offline only; existing artifacts reused; no performance figures;
no holdout access; no vendor calls / 0 credits; no tuning; no
production or resume changes; no S1/S2 activation; no paper
trades; no T0. PAUSED production re-proved at emission (P0) and
again at package time: harness sha ce7c902c…, PAUSE_NEW_ENTRIES
present, RESUME_NEW_ENTRIES absent.

Elapsed: ~7 min from dispatch to RESULT (single lane, no retries).

— Muse
