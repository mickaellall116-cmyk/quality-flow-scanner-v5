# TOP-vs-BROAD Clean Provenance Reproduction — Comparison Report
**Date:** 2026-10-04. **Approved by:** Mike.
**Purpose:** Reproduce the adjudicating result (df79558) from the fully committed/pinned bytes
after the `spy` fix (15b34c5) and strict-pin update (386781f).

## Provenance
- df79558 (results) predated 15b34c5 (spy dead-parameter fix) and 386781f (pin update).
- This reproduction ran from main AFTER all three commits, with strict preflight PASS.
- Preflight: 225 1H hashes ✓, 218 daily+SPY hashes ✓, all 5 module pins ✓, 16/16 fixtures ✓.
- No parameter, universe, cost, gate, membership, S4, bootstrap, or data changes.

## Result: EXACT MATCH (bit-for-bit, delta = 0.0 on all 24 metrics)

| Metric | df79558 | Reproduction | Delta |
|---|---|---|---|
| BROAD 25bps: n / expectancy | 195 / −0.090955R | 195 / −0.090955R | 0 |
| TOP 25bps: n / expectancy | 173 / +0.001911R | 173 / +0.001911R | 0 |
| BROAD 25bps: Calmar / maxDD | −0.690 / 0.2185 | −0.690 / 0.2185 | 0 |
| TOP 25bps: Calmar / maxDD | 0.260 / 0.2846 | 0.260 / 0.2846 | 0 |
| BROAD 4bps: n / expectancy | 196 / −0.040110R | 196 / −0.040110R | 0 |
| TOP 4bps: n / expectancy | 173 / +0.074302R | 173 / +0.074302R | 0 |
| Gates G0–G5 | F,F,F,F,T,F | F,F,F,F,T,F | identical |
| Bootstrap CI | [−0.20040, +0.43334] | [−0.20040, +0.43334] | 0 |
| Bootstrap point / valid / discard | 0.09287 / 10000 / 0% | 0.09287 / 10000 / 0% | 0 |
| G3 Y1/Y2 counts | (99,118) / (74,77) | (99,118) / (74,77) | identical |

## Conclusion
The `spy` fix was confirmed methodology-neutral. The adjudicating result reproduces
deterministically from the committed bytes. Per Mike's decision rule: **MATCH — formally closeable.**

The TOP-50/quarterly/composite hypothesis remains KILLED (68a7a0b).
No retuning, no holdout spend, no V5.4 changes.

## Evidence package
`research_notes/top_broad_repro_evidence_20261004.json` contains:
- 5 code hashes, 225 1H + 218 daily input hashes
- 7 quarterly TOP-50 membership lists
- Full trade ledgers (196+173+195+173 trades with timestamps, symbols, net R)
- Monthly marked-equity curves (19 points × 4 legs)
- This comparison report: `research_notes/top_broad_repro_comparison_20261004.md`
