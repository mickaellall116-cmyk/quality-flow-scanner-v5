# §7.7 Coverage Gate — Operational Specification (correction C1)

Freezes exactly what the protocol already requires. No new numeric thresholds;
no performance-gate changes. This spec turns §7.7's qualitative rule into code.

## Protocol source (v3 §7.7 / §8)

- Gate 7: "the §8 coverage audit shows delisted/acquired/bankrupt names included
  per the point-in-time criterion. Material unquantifiable gaps → INCONCLUSIVE
  (not fail)."
- Mandatory pre-run coverage audit (blocks the run if skipped): publish (a)
  tickers in criterion vs tickers with usable data, (b) missing tickers with
  reason, (c) count of delisted/acquired/bankrupt names included.

## Operationalization

The coverage audit classifies every criterion ticker into exactly one bucket:

| Bucket | Meaning |
|--------|---------|
| `usable_ge100` | ≥100 adjusted bars, in sample |
| `short_lt100` | file exists, <100 bars (reason: insufficient history) |
| `inactive_truncated` | delisted/acquired, truncated series (reason documented) |
| `inactive_bankrupt_q` | bankrupt, −100% applied (reason documented) |
| `missing_no_file` | **no file and no reason — unquantified by definition** |

**Gate rule (`coverage_ok`):** PASS iff the audit artifact exists AND
`missing_no_file` is empty — i.e., every criterion ticker is accounted for
with data or a documented reason. Any ticker in `missing_no_file` is an
unquantified gap; per §7.7 the verdict becomes INCONCLUSIVE (not FAIL).

**Run-blocking:** if the coverage audit step is skipped or its artifact is
absent, the script refuses to emit a verdict (protocol: "blocks the run if
skipped").

**Verdict precedence:** if `coverage_ok` is False → verdict INCONCLUSIVE,
regardless of performance gates. Performance-gate outcomes on the partial
sample are still reported (preserved as facts, e.g. today's Calmar FAIL),
but they do not constitute the verdict.

## Dedup rule (portfolio admission)

`universe_mapping.json` assigns every ticker a permanent security ID; rename
pairs (CPRI/KORS, BHGE/BKR, FI/FISV, CPAY/FLT, J/JEC) share one ID. Portfolio
caps (20 max positions, 5 per sector, 10% heat) count **security IDs, not
tickers**. If two aliases of one security both pass signal filters, only the
canonical ticker's trade is admitted (deterministic). Dedup happens before
portfolio admission — ledger-level cleanup alone is insufficient.
