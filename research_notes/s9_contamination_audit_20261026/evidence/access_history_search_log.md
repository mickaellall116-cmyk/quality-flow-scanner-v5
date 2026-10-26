# A2 access-history search log — §9 audit, 2026-10-26

Method: metadata/history only. No holdout payload was opened, parsed, or computed on.
Searches run against: scanner repo git history (all refs), scanner repo working tree,
qf-data-archive clone git history, bridge thread, research notes, memory daily logs,
CP1 bundle documents, stage directories.

## Searches and results

1. `git log --all --oneline -S "2023-10-19"` (scanner repo) — hits are the v0.3 package
   (b65696a), measurement packages (-29r/-30), feed-measure pilot, G4 packet, S1 staging:
   all governance/calendar/measurement records. No performance-run package.
2. `git log --all --oneline | grep -i holdout` — governance closure -24 (dates recovered
   by record), task -81 (2023 NYSE calendar evidence), source adoption -23, universe
   proposal v3 (f054ff7). No run package, no results file.
3. Scanner commits 2026-10-03..2026-10-26 mentioning holdout/HO: 7 — all governance,
   calendar, or capture-qualification records.
4. qf-data-archive `git log` on HO capture paths — exactly two commits ever touch them:
   db1b43d (-10 capture STOP, PLTR/HO quarantined) and bb644db (-11 continue capture).
   The only archive commit after 2026-10-23 is 282531d (P7b DEV inventory). No
   post-capture access commits.
5. Capture acquisition log: attempts.jsonl / brackets.jsonl in each capture dir record
   every Twelve Data call (timestamps, leg ids, credits). All HO-leg calls are the
   Oct 23, 2026 qualification captures themselves.
6. -13 RESULT.md (QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13): states verbatim that the
   run "does not touch the frozen C1 FAIL, the sealed W_HO" and "W_HO sealed (HO files
   touched only as SHA256SUMS hashes and receipt-chain metadata)".
7. EXP-14B RUN_RECORD.md (2026-10-26): four pinned inputs — P7b inventory (DEV),
   exec-prices input (DEV, 44,849 bars), frozen cohort, frozen draws. No HO input.
8. CP1 follow-up FINDINGS.md scope line: "FORENSIC EVIDENCE COLLECTION ONLY. No
   corrected performance computed or opened." CP1's trade-intersection work covered the
   C1 240-trade ledger, whose cache (D1) spans 2024-09-16..2026-09-15 only.
9. CORRECTED_BASELINE_DATA_READINESS_MAP_20261015.md row D7: "Sealed 11-month holdout —
   Identity-only per spec; no holdout files exist on this VM; nothing opened."
10. Bridge thread grep "holdout" (11 mentions): a surrogate study's own 2026 holdout
    (different object), standing-evidence summaries ("holdouts sealed"), data-readiness
    memo, validation-contract consolidations. No holdout outcome anywhere.
11. pine_claims_* code inspection (method only): run_crt.py / run_ib.py / run_ob.py all
    read pine_entry_timing_backtest/cache (the D2 14-symbol cache) and compute by-year
    and pre-2025 ("dev_2023_2024") splits — post-designation outcome computations on a
    DIFFERENT rule family whose trades include entries inside the holdout window.
    Recorded as finding F-A2-3.
12. Sep-24 re-baseline handover (workspace/your_files/trading-handover-2026-09-24-
    rebaseline.md): full-portfolio replay on "4H data from Oct 2023", 374 trades,
    aggregate + decomposition read by the team; decisions taken from it recorded in the
    document itself (old baseline discarded, lone-wolf removed, checkpoint re-anchored
    to ~0R). Recorded as finding F-A2-1.
13. CANONICAL_RECONSTRUCTION_FROZEN_RULES_20260928_REV6.md §9/§10: reconstruction
    governance — Gate D signal-identity evaluation across the reconstruction window
    (2023-10-26..2026-09-24), comparator discipline, "No historical outcome was used to
    choose among the §7 resolutions", no result-driven semantic changes. Recorded as
    finding F-A2-2.

## Limitation

No OS-level file-access (atime) log exists or is reliable on this VM. Access history
rests on: both repos' git histories, the capture receipt/attempt chains, the bridge
record, and study documents. An unlogged interactive look at D2/D3/reconstruction bytes
before 2026-10-03 cannot be excluded by this method; A5 attestations are the protocol's
instrument for that residue, and §9 discloses public market knowledge as unauditable.
