# QF-EQUITY43-FWD-DECISION-PARITY-REPAIR-20261023-16 r1 — RESULT

**Verdict (re-derived from the comparison artifact by report16.py, not
from any wrapper signal): DECISION_PARITY_PASS.**

Governing adjudication: Issue #1 comment 6377575196. Scope held exactly:
field census → deterministic reproduction → chronological
first-divergence attribution → ONE minimal observer-layer correction →
exactly ONE full re-comparison. No performance figures, no vendor
calls/credits, no holdout access, no tuning, no G4 waiver, no
production/resume changes, no activation/T0/entries. The -15 package
(5f77509) is untouched; its failed artifacts remain frozen evidence.
PAUSED production pins verified identical before and after (P0 phase of
both comparison runs: PAUSE present, RESUME absent, harness sha and
committed artifacts pinned).

**Answer to the governing question:** yes — the corrected observer now
earns the narrowed -15 label "isolated corrected 43-equity forward
observer": bars, benchmark, candidates (every simulator-consumed
field), and portfolio decisions all reproduce the -13 reference
exactly on the receipted DEV bytes. Activation remains a separate,
unnamed-T0 decision (ChatGPT adjudication, then Mike's GO) — nothing
in this task requests or implies it.

## 1. Fail-before (pristine -15 observer, this task's harness)

Deterministic, byte-level reproduction of the committed -15 failure:

- Decision mismatches: **201** — the identical set head as the -15
  artifact: AAPL 715 taken_25bps; AMD 533 taken_25bps; AMD 833
  disposition_4bps skipped_rank (observer) vs skipped_risk
  (reference); AMD 1001 taken_25bps; AMZN 455 disposition_4bps
  skipped_rank vs skipped_risk. rs_mismatches 0.
- C0 observer taken/skipped_cap/skipped_risk = 192/328/70 vs reference
  193/323/74. Terminal inventory observer {CRM, PFE} in all views vs
  reference {CRM, MRNA, PFE} (gross) and {CRM, MRNA, PFE, SHOP}
  (4bps/25bps).
- Layers that held in -15 hold identically: bars 44,849 compared,
  session-VWAP max abs diff 4.547473508864641e-13; SPY as-of benchmark
  equal over 524 sessions; journal 68,903 records, chain verified;
  close series identical (43/43 symbols, max abs diff 0.0); pinned
  experiment config sha matched
  (87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706).
- Reference self-check (reference candidates through the identical
  simulation path): 0 mismatches, C0 exact — the harness and reference
  path are faithful; the divergence is observer-side only.

## 2. Field census (every simulator-consumed field, 590 candidates)

| field | mismatches (fail-before) |
|---|---|
| entry, stop, tp1, entry_time, exit_time, signal_time, reason, hold_bars, tp1_hit, risk_frac | **0 each** |
| **exit** | **276** (max abs diff $109.15) |
| censored (strict) | 586 — key-presence artifact only, see §4 |

The 276 exit mismatches are exactly the closed candidates with
tp1_hit=True. Independent formula audit (analyze_exit_stdout.txt):
recomputing the reference exit from (entry, stop, tp1, tp1_hit, raw
exit-bar open) with the reference's own arithmetic reproduces the
reference `exit` **bit-exactly for 586/586** closed candidates, and
|reference exit − raw open| splits cleanly: 276 tp1-hit candidates
material (>1e-9), 310 non-tp1 candidates epsilon-only (≤1e-9 — the
reference recomputes the exit through the blend algebra even without a
TP1 hit). No other category exists.

## 3. Root cause (proven, four independent ways)

The -15 observer's CandidateMachine stored the **raw next-bar open**
as the candidate `exit`. The reference generator
(`gen_candidates_censored`, field-verified against the frozen
`gen_candidates` in -13) records the **TP1-blended synthetic exit** —
50% realized at TP1 when hit, the runner at the raw exit price —
because that is the V5.4 execution model the simulators price. The
-15 comparison loop and the -15 suite's `decision_fields()` both
omitted `exit` from comparison, although `pine_backtest._outcome`
consumes it for every cash flow: the divergence flowed through exactly
the untested field ChatGPT named.

Divergence chain (chronological walk, diagnostics in
compare16_orig15.json):

- First field divergence = first cash-flow divergence: **XLF 224**,
  exit 2025-03-04 13:30 ET, tp1_hit=True, reason stop — reference exit
  51.234642196082504 vs observer 50.12; 4bps exit cash flow −$14.99
  (reference) vs −$156.13 (observer).
- First disposition divergence downstream: ARM 411 (entry 2025-07-16
  13:30 ET), observer skipped_risk vs reference skipped_rank — the
  same species as AMD 833 / AMZN 455.
- Classification of the 201 ledger mismatches against the first
  field-divergence instant: **201 cascade-consistent, 0 independent.**
- Substitution proof: observer candidates with ONLY the `exit` field
  replaced by the reference values restore **full** decision parity
  (0 mismatches, C0 exact 193/323/74, terminal identical in all
  views). The exit field is the sole root cause.

## 4. The one semantic note (disclosed, not hidden)

Strict key-equality on `censored` counts 586 in BOTH runs: the
reference/frozen generator omits the key on closed candidates (None)
while the observer writes False explicitly. The simulator consumes
the field solely via `tr.get("censored")` truthiness
(engine_successor/pine_stack/pine_stack.py line 70), so the consumed
values are identical for all 590 candidates (the 4 genuinely censored
candidates carry True on both sides and match strictly). Strict dict
equality is unachievable by construction without touching frozen
code; the PASS bar counts simulator-consumed fields, and report16.py
fails closed on any strict residual other than this artifact.

## 5. The repair (minimal, observer layer only)

One hunk in the observer's CandidateMachine._advance
(observer_fix.diff, 32 diff lines): the exit assignment now computes
the reference's blended synthetic exit with the identical float
arithmetic (same expressions, same order). Nothing else changed.
Strategy sources byte-identical; frozen pins untouched.

- observer sha256: -15 committed 48466a16fdeda56b7d7781f7af895fc3e58004388ad52ccdad888ff68100aef3 → repaired 0f5a6638c5dc7f2f19240a27bf3bc4ec9abab566cd7726972fa13cd98f0a6fd9

## 6. The single full re-comparison (PASS bar, item by item)

From compare16_patched.json, re-derived by report16.py (exit 0):

- Field census: **0 mismatches** in every simulator-consumed field
  (exit 0 of 590; only residual = the §4 artifact).
- Decision mismatches: **0**; rs_mismatches **0**.
- Terminal inventory identical in all views: gross {CRM, MRNA, PFE};
  4bps/25bps {CRM, MRNA, PFE, SHOP} — observer and reference.
- C0 counts identical: taken 193, skipped_cap 323, skipped_risk 74.
- Bars 44,849 (VWAP max abs diff 4.547473508864641e-13); benchmark
  equal (524 sessions); closes identical 43/43; journal 68,903
  records verified; reference self-check clean; config pin matched.

## 7. Fail-closed reporting (the -15 error mode, closed)

report16.py reads the comparison artifact itself and re-derives the
verdict from section values; any inconsistency → STOP, exit 2.
Negative battery (tests16, R2a–R2g, all passing): the -15 committed
artifact derives STOP; the same artifact with its verdict string
flipped to PASS derives STOP; counts zeroed with problems retained →
STOP; problems cleared with counts nonzero → STOP; census section
removed → STOP; the -16 fail-before document derives STOP;
report16.py run directly on the -15 artifact and on the fail-before
document exits 2 with STOP, and on the re-comparison document exits 0
with PASS.

## 8. Tests

- -15 adversarial suite (18 tests, unmodified): 18/18 against the
  pristine observer (its blind spot reproduced) and **18/18 against
  the repaired observer**.
- -16 regression suite (test_decision_parity_repair16.py): against the
  pristine observer 9/10 — the ONLY failure is R1 exit-field parity
  (exactly 1 exit mismatch on the synthetic series' single tp1-hit
  closed candidate; fail-before). Against the repaired observer
  **10/10**.

## 9. Package

decision_compare16.py (census + comparison harness), report16.py
(fail-closed reporter), fwd_observer.py (repaired observer),
observer_fix.diff, test_decision_parity_repair16.py,
compare16_orig15.json + compare16_patched.json (the two governed
runs), their stdouts, analyze_exit_stdout.txt, both test stdouts
(orig/patched), both -15-suite stdouts, report16 outputs for the
three real documents, SHA256_MANIFEST.txt.

Remaining gates unchanged: ChatGPT adjudication of this package;
Mike's GO naming a future T0 before any activation. G4 adoption and
the SMCI disposition remain open items outside this task.

— Muse
