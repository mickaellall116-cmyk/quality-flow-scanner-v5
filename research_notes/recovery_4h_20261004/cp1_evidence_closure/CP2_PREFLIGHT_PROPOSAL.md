# CP2 Preflight — Proposal Only

**Date:** 2026-10-06
**Status:** PROPOSAL. No execution performed. No aggregate performance computed.
**Authorization required:** Separately authorized by Mike before any CP2 work begins.
**Immutable evidence pin:** `84942a6929258a0c316a6e849a7480c286013d95` (main HEAD)

## Purpose

CP2 is the prospective second checkpoint: an independent replication/audit of
the corrected-grid C1 baseline construction, building on the CP1 forensic
findings. This document specifies what CP2 preflight would require — inputs,
lineage, tests, and gates — so the scope can be reviewed before authorization.

## 1. Required input identities (exact files/hashes)

All inputs pinned by `FULL_MANIFEST.json` (remote blob `6d32c0ab701b…`):

| Input | SHA-256 (expected) | Role in CP2 |
|-------|-------------------|-------------|
| `backtest_cache/v3/h4_*.pkl` (52 files) | per `cache_hashes_pinned.txt` | Original (defective-grid) cache — read-only reference |
| `research_notes/recovery_4h_20261004/cp1_bundle/02_c1_ledger/c1_240_trade_ledger.json` | `af62428d…` (manifest `inputs`) | 240-trade ledger under audit |
| `pine_backtest.py` | `447a9a13…` | Backtest engine source |
| `pine_stack/pine_stack.py` | `839e4800…` | Stack/portfolio source |
| `pine_execution/c1_corrected_baseline_20261003.py` | `4568823c…` | Corrected-baseline constructor |
| `scanner_rules.py` | `7db282dd…` (Version A, forensic line) | Resampler + signal rules |

**Lineage note:** `scanner_rules.py` Version A (`7db282dd…`) is the forensic-line
version. The hardening-line Version B (`62aa743a…`, remote main) is out of
scope unless explicitly added. See `SCANNER_RULES_IDENTITY.md`.

## 2. Lineage and reproduction limits

- **What CP2 may do:** Independently re-derive the corrected-grid trade list
  from the pinned inputs using the pinned sources; verify the 240-trade
  ledger reproduces byte-identically; verify the 51/31 split, the 14,986 /
  44 / 225 slot classification, and the T192 withdrawal.
- **What CP2 may NOT do:**
  - No fresh data retrieval or vendor backfill.
  - No holdout access (4H holdout remains sealed).
  - No corrected aggregate performance computation (no R multiples, no
    equity curves, no "what would it have made").
  - No V5.4 production or semantic changes.
  - No strategy tuning or parameter adjustment.
- **Reproduction limit:** CP2 verifies *construction integrity* (do the
  pinned inputs + pinned code reproduce the pinned ledger?), not
  *performance validity* (was the strategy good?). Performance questions
  belong to a separately authorized walk-forward research program with
  untouched validation data.

## 3. Fixed tests with pass/fail gates

| # | Test | Pass gate | Fail action |
|---|------|-----------|-------------|
| T1 | Input byte identity | All pinned SHA-256 match before any computation | STOP — do not proceed on mismatched inputs |
| T2 | Ledger reproduction | Re-derived 240-trade ledger is byte-identical to `c1_240_trade_ledger.json` | STOP — report divergence field-by-field |
| T3 | Split verification | Exactly 51 equity shifted-regime + 31 crypto calendar entries; 158 remaining | STOP — report count divergence |
| T4 | Slot classification | 14,986 shifted / 44 absent / 225 truncations reproduce exactly | STOP — report classification divergence |
| T5 | T192 withdrawal | Zero SOL trades intersect exact gaps; T192 `gap_refs` empty | STOP — report any intersection found |
| T6 | Shard canonicality | Shard reassembly reproduces `02608fd4…` and parses as 240-trade JSON | STOP — report shard corruption |
| T7 | No-performance guard | No R-multiple, equity-curve, or aggregate P&L artifact produced | STOP — delete any such artifact if created |

**Gate rule:** Any FAIL stops the preflight. Findings go to the bridge as a
forensic report; no downstream work until Mike audits.

## 4. Exclusions (explicitly out of scope)

- CP2 does not clear anything for production, live trading, or real money.
- CP2 does not validate, invalidate, or reinterpret the closed V5.4 FAIL verdict.
- CP2 does not open corrected performance in any form.
- The 1H-window evidence gap (UNAVAILABLE for all pilot trades) is a known
  limitation carried forward, not resolved by CP2.

## 5. Authorization checklist (for Mike)

- [ ] CP2 preflight scope approved as specified above
- [ ] Confirm no holdout access under any circumstances
- [ ] Confirm no performance computation under any circumstances
- [ ] Designate who adjudicates a FAIL at each gate (proposed: ChatGPT
      verifies, Claude independently replicates, Mike decides — same as CP1)
