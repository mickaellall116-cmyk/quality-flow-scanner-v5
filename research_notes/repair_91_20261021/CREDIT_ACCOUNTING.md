# CREDIT ACCOUNTING — corrected scheme (REPAIR -91, FIX 3)

**Supersedes, by reference, the credit-accounting clauses of the
-88 package** (`capture_manifest_provenance_20261021_88/PROVENANCE.md`
§2 receipt fields `usage_before` / `usage_after` / `credit_delta`
and §3 day-close reconciliation; CAPTURE_MANIFEST.md totals table).
The -88 package bytes are untouched; where this document and -88
disagree on credit accounting, THIS document governs. Nothing here
authorizes a capture (the capture GO, route + ceiling + manifest
pin, remains Mike's).

## The defect (ChatGPT review, blocker 3)

-88's receipts claimed a per-leg `credit_delta` computed from
`usage_after − usage_before`, but the only usage snapshots the
scheme actually took were a day-open preflight and a day-close
snapshot. A per-leg delta is **not derivable** from two day-level
brackets: every leg in the day shares the same pair of numbers.
The totals were also at risk of omitting closing usage reads:
132 expected / 262 worst counted exactly 2 usage calls, while the
scheme's own text implied more.

## The corrected scheme: BLOCK-BRACKET-10

One coherent rule set; every credit is either attributed or
explicitly accounted — never silently absorbed.

1. **Unit cost.** Every API call — data leg or `/api_usage` read —
   costs exactly 1 credit. This is evidenced, not assumed: -69
   (one usage read = 1 credit), -75 (preflight usage read + 5 data
   legs = 6 credits), Policy A accounting (1 usage + 51 requests =
   52). A scheme that denied unit cost could not reconcile at all.
2. **Sequential execution, blocks of ≤ 10 attempts.** Attempts
   execute strictly sequentially in manifest order, grouped into
   blocks of at most **10 attempts**. No program call of any kind
   interleaves inside a block except the block's own data attempts.
3. **Bracketing reads.** One `/api_usage` read opens each phase
   (r₀) and one closes **every** block (r_k); the close of block k
   is the open of block k+1 (chained, never duplicated). Reads per
   phase = blocks + 1. Each receipt records `block_id`,
   `block_position`, and the sha256 of its block's two bracket
   reads — receipts no longer carry per-leg `usage_before` /
   `usage_after` / `credit_delta` fields, because per-leg deltas
   are not claimed.
4. **Block reconciliation (fail-closed).** For every block k:
   `u_k − u_{k−1} = attempts_k + 1`, where the +1 is the closing
   read r_k's own charge, attributed by convention to the interval
   it closes. If any block's delta differs — in either direction —
   execution halts and the block's receipts are the evidence. There
   is **no unattributed-remainder rule** because there is no
   remainder: a mismatch is a stop, not a rounding bucket. The
   pilot's first block empirically confirms the charge-timing
   convention before any Phase-1 credit is spent; a convention
   mismatch at the pilot is a pilot FAIL.
5. **Phase-close identity.** Credits consumed by a phase =
   attempts + (blocks + 1) reads. The final read r_last reports
   usage before its own charge lands; the books close
   arithmetically with that known +1 (the -72/-74 tail-closure
   precedent), not with an extra read. Program totals are the sum
   of the two phase totals (pilot, Phase 1), each phase opening
   its own chain on its own execution day.

Why block bracketing and not per-leg bracketing: per-leg brackets
would add 2 usage reads per attempt (expected program cost
130 + 2×130 = 390 > the 300 ceiling) to attribute what unit cost
already attributes exactly — inside a sequential block with no
interleaved calls, the block delta can only be the attempts plus
the closing read, so attribution is exact at block granularity
with 10× fewer reads. Per-leg `credit_delta` was false precision;
block reconciliation is the strongest claim the snapshots support.

## Recounted totals under BLOCK-BRACKET-10 (delta to -88)

Legs are unchanged (130 data legs: pilot 16 = 10 session-bound +
BTC-USD 6 chunks; Phase 1 = 114). Attempts: expected = legs;
worst = 2 × legs (≤2-attempts cap, unchanged).

| Phase | Case | Attempts | Blocks | Usage reads | **Total** | -88 figure |
|---|---|---|---|---|---|---|
| Pilot | expected | 16 | 2 | 3 | **19** | 17 |
| Pilot | worst | 32 | 4 | 5 | **37** | 33 |
| Phase 1 | expected | 114 | 12 | 13 | **127** | — |
| Phase 1 | worst | 228 | 23 | 24 | **252** | — |
| **Program** | **expected** | 130 | 14 | 16 | **146** | 132 |
| **Program** | **worst** | 260 | 27 | 29 | **289** | 262 |

**Ceiling implication, plainly: the proposed 300-credit ceiling
STANDS** — the corrected worst case (289) remains under it, with
the margin narrowed from 38 to 11 credits. No ceiling amendment is
requested. If adjudication prefers a wider margin, that is a
ceiling decision for Mike at the capture GO, not a scheme change.
