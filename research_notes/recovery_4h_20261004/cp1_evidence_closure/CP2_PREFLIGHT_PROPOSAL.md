# CP2 Preflight — Proposal Only (AMENDED 2026-10-07)

**Date:** 2026-10-06 (amended 2026-10-07 per ChatGPT amendment 6028744990)
**Status:** PROPOSAL. No execution performed. No aggregate performance computed.
**Authorization required:** Separately authorized by Mike before any CP2 work begins.
**Immutable evidence pin:** `84942a6929258a0c316a6e849a7480c286013d95` (main HEAD)

## Purpose

CP2 is the prospective second checkpoint: an independent replication/audit of
the C1 baseline construction, building on the CP1 forensic findings. This
document specifies what CP2 preflight would require — inputs, lineage, tests,
and gates — so the scope can be reviewed before authorization.

## 0. Amendment (2026-10-07): two separate reproduction tasks

The 2026-10-06 version conflated two different reproduction tasks under a
single "ledger reproduction" test. They are separated here because **they
cannot both require byte identity to the same 240-trade ledger**.

- **Task R1 — Defective-grid ledger reproduction (REPRODUCIBLE).**
  Re-run the pinned engine sources (`pine_backtest.py`, `pine_stack/
  pine_stack.py`, `pine_execution/c1_corrected_baseline_20261003.py`) against
  the 52 retained defective-grid 4H caches (`backtest_cache/v3/h4_*.pkl`,
  13:30/17:30 UTC grid). The expected output is byte-identical reproduction
  of `c1_240_trade_ledger.json` (whose provenance states it was built on
  those exact caches: "UTC-anchored bins at 13:30/17:30 UTC"). All inputs are
  retained; byte identity is a legitimate gate.

- **Task R2 — Corrected-grid reconstruction (UNREPRODUCIBLE from retained
  evidence).** Rebuild 4H bars on the session-anchored grid
  (`resample_closed_4h_session_anchored`) from the **constituent 1H inputs**,
  then run the stack. This necessarily produces a *different* trade list —
  it cannot be byte-identical to the 240-trade ledger, and byte identity
  must NOT be required of it. **Critical:** the constituent 1H inputs used
  to build the 52 caches (2026-09-15, via an uncommitted process) were **not
  retained** — the trade-chart pilot confirms "no retained constituent 1H
  files exist" for the examined trades. The 4H caches **cannot** be
  "corrected" into the right grid: they are already aggregated on the wrong
  grid, and aggregation is not reversible. **Task R2 is therefore marked
  UNREPRODUCIBLE** from retained evidence. It may only proceed if 1H inputs
  with documented provenance are supplied; otherwise it stays closed and
  the limitation is carried forward explicitly.

## 1. Required input identities (exact files/hashes)

All inputs pinned by `FULL_MANIFEST.json` (remote blob `6d32c0ab701b…`).
Remote-readable archival copies: `cp1_evidence_closure/archival_sources_v1/`.

| Input | SHA-256 (expected) | Role in CP2 |
|-------|-------------------|-------------|
| `backtest_cache/v3/h4_*.pkl` (52 files) | per `cache_hashes_pinned.txt` | Original (defective-grid) cache — read-only reference for R1 |
| `research_notes/recovery_4h_20261004/cp1_bundle/02_c1_ledger/c1_240_trade_ledger.json` | `af62428d…` (manifest `inputs`) | 240-trade ledger under audit (R1 target) |
| `pine_backtest.py` | `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5` | Backtest engine source |
| `pine_stack/pine_stack.py` | `839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb29a5956dfcefa` | Stack/portfolio source |
| `pine_execution/c1_corrected_baseline_20261003.py` | `4568823cb8fe645a820c64bb4fac112fa7c90ac860bf626611467f7d94ea8f2b` | Corrected-baseline constructor |
| `scanner_rules.py` | `7db282ddfc150c9e9aec7d8f1f10f439ce7e296da2d69da38f97ed8cbec70cac` (Version A, forensic line) | Resampler + signal rules |

**Lineage note:** `scanner_rules.py` Version A (`7db282dd…`) is the forensic-line
version. The hardening-line Version B (`62aa743a…`, remote main) is out of
scope unless explicitly added. See `SCANNER_RULES_IDENTITY.md`.

## 2. Lineage and reproduction limits

- **What CP2 may do (R1):** Independently re-derive the 240-trade ledger
  from the pinned defective-grid caches + pinned sources; verify byte
  identity; verify the 51/31 split, the 14,986 / 44 / 225 slot
  classification, and the T192 withdrawal.
- **What CP2 may do (R2):** ONLY if documented 1H inputs are supplied —
  rebuild session-anchored 4H bars and run the stack to produce the
  corrected-grid trade list (a *new* artifact, not a reproduction).
  Without 1H inputs, R2 is closed as UNREPRODUCIBLE.
- **What CP2 may NOT do:**
  - No fresh data retrieval or vendor backfill.
  - No holdout access (4H holdout remains sealed).
  - No corrected aggregate performance computation (no R multiples, no
    equity curves, no "what would it have made").
  - No V5.4 production or semantic changes.
  - No strategy tuning or parameter adjustment.
  - No "correction" of the 4H caches in place — they are evidence.
- **Reproduction limit:** CP2 verifies *construction integrity* (do the
  pinned inputs + pinned code reproduce the pinned ledger?), not
  *performance validity* (was the strategy good?). Performance questions
  belong to a separately authorized walk-forward research program with
  untouched validation data.

## 3. Fixed tests with pass/fail gates

| # | Test | Pass gate | Fail action |
|---|------|-----------|-------------|
| T1 | Input byte identity | All pinned SHA-256 match before any computation | STOP — do not proceed on mismatched inputs |
| T2a | R1: defective-grid ledger reproduction | Re-derived ledger byte-identical to `c1_240_trade_ledger.json` | STOP — report divergence field-by-field |
| T2b | R2: 1H input availability | Documented constituent 1H inputs present with provenance, or R2 formally closed as UNREPRODUCIBLE | STOP — do not imply 4H caches can substitute; mark UNREPRODUCIBLE and carry forward |
| T3 | Split verification (R1) | Exactly 51 equity shifted-regime + 31 crypto calendar entries; 158 remaining | STOP — report count divergence |
| T4 | Slot classification (R1) | 14,986 shifted / 44 absent / 225 truncations reproduce exactly | STOP — report classification divergence |
| T5 | T192 withdrawal (R1) | Zero SOL trades intersect exact gaps; T192 `gap_refs` empty | STOP — report any intersection found |
| T6 | Shard canonicality | Shard reassembly reproduces `02608fd4…` and parses as 240-trade JSON | STOP — report shard corruption |
| T7 | Forbidden-output quarantine | If any forbidden output (R multiples, equity curves, aggregate P&L, holdout access, fresh-data pull) is accidentally produced: **STOP immediately, quarantine the artifact WITHOUT inspecting it, preserve it as evidence of the boundary violation, and report**. Do NOT delete it — deletion destroys evidence. Do NOT open, read, or summarize its contents. | STOP — quarantine + report; await Mike's direction on disposition |

**Gate rule:** Any FAIL stops the preflight. Findings go to the bridge as a
forensic report; no downstream work until Mike audits.

**T7 rationale (amended 2026-10-07):** the 2026-10-06 version directed
deletion of accidental forbidden artifacts. Deletion is wrong: it destroys
evidence of *how* the boundary was crossed and invites silent re-violation.
Quarantine-without-inspection preserves the evidence while preventing its
use. "Without inspecting" matters because even reading a forbidden
performance number contaminates the blind.

## 4. Exclusions (explicitly out of scope)

- CP2 does not clear anything for production, live trading, or real money.
- CP2 does not validate, invalidate, or reinterpret the closed V5.4 FAIL verdict.
- CP2 does not open corrected performance in any form.
- The 1H-window evidence gap (UNAVAILABLE for all pilot trades) is a known
  limitation carried forward, not resolved by CP2.
- R2 (corrected-grid reconstruction) is not a backdoor to performance
  computation: even with 1H inputs, producing the corrected trade *list* is
  construction verification only. Aggregate performance stays closed.

## 5. Authorization checklist (for Mike)

- [ ] CP2 preflight scope approved as specified above (R1 reproducible, R2
      UNREPRODUCIBLE unless 1H inputs supplied)
- [ ] Confirm no holdout access under any circumstances
- [ ] Confirm no performance computation under any circumstances
- [ ] Confirm T7 quarantine rule (preserve-without-inspecting, never delete)
- [ ] Designate who adjudicates a FAIL at each gate (proposed: ChatGPT
      verifies, Claude independently replicates, Mike decides — same as CP1)
