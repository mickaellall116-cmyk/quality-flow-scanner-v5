# SEQUENCING NOTE — what fires when -09 clears

## QF equity-capture prep, 2026-10-23 · PREPARED ONLY

Mike's standing sequence (chat, 2026-10-23): **fix the two
look-ahead defects → qualify the remaining equities → run the
unchanged strategy across the full eligible equity universe →
independently validate → only then evaluate the protected
out-of-sample period.** This note pins the trigger chain so the
39-name capture can fire immediately when step 1 clears, with no
step silently absorbing another step's gate.

---

### STEP 1 — -09 PIT-integrity fix clears adjudication *(running now; this prep waits on it)*

QF-EQUITY-PIT-INTEGRITY-20261023-09 delivers research-only as-of
corrections for the two defects ChatGPT's -08 review found
(midnight-stamped SPY daily bars visible to same-day RS ranking;
frozen mark-to-market using the unfinished bar's close), proven
fail-before/pass-after on synthetic bars, plus the
simultaneous-entry ordering audit and the terminal-open count —
**no performance re-run**. "Clears" means: package committed,
ChatGPT adjudication returned, and the corrections stand as
reviewed research-lane artifacts. The corrections are **not**
adopted into any run by this prep or by the capture; adoption into
the full-universe run is Step 4's own gate.

### STEP 2 — Capture GO *(the trigger this prep exists to serve)*

A capture GO (Mike directly, or a ChatGPT-relayed GO inside an
adjudicated task under the 2026-10-23 rule) that **names the
manifest root digest
`ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64`**
(`capture_manifest_equity39.json`). Credits are not part of the GO
decision (Mike, 2026-10-23 16:04 ET: free; sized to the work).
On the GO, the capture fires **immediately** — no further prep
package, no re-derivation of the manifest.

### STEP 3 — Capture execution (one phase, fail-closed)

78 legs in manifest order under BLOCK-BRACKET-10 (**87 expected /
173 worst** credits, $0, one execution day at either figure);
receipts hash-chained to the manifest root; archive
`qf-data-archive/captures/td_capture_equity39_<EXEC_DATE>/`,
SHA256SUMS re-fetch verified. Abort conditions exactly as frozen
in `CAPTURE_MANIFEST.md` §3 (preflight field check, 5000-row
truncation, bracket exhaustion, chain break, block-reconciliation
mismatch, SMCI-class volume anomaly → quarantine + adjudication).
Partial completion is reported as partial — never silently
completed, never retried outside the bracket rules.

### STEP 4 — Per-name qualification preflight (-08-style, per name)

Each captured name runs gates **G-1..G-7**
(`CAPTURE_MANIFEST.md` §4): receipt integrity → calendar-bound
admission vs the pinned 751-session table → completeness
exactness → phantom-row accounting → volume completeness
(TSLA-C2 / SMCI classes named) → schema/instant hygiene → VBASIS
disclosure carried. Outcomes are per-name and public in the
report: **QUALIFIED** or the failing gate named
(`NOT_EVALUABLE_PROVIDER_VOLUME`, `COMPLETENESS_FAIL`, …).
The eligible universe for Step 5 is exactly the names that
qualify, plus the 4 pilot-qualified names (NVDA/TSLA/AAPL/SPY),
plus SMCI only if its separate disposition (§6) resolves it in.

### STEP 5 — Corrected full-universe run

The unchanged frozen strategy (pinned code hashes as in -08)
across the full **eligible** equity universe, DEV window, with:

- the **-09 research-only as-of corrections applied only once
  adopted** for this run by adjudication (Step 1's gate) — the
  corrections are never silently folded in;
- the **actual ranking and portfolio limits live** (rs_top2
  ranking, sector caps, risk gate, max positions — the layer the
  4-name -08 run never exercised: 61/61 candidates taken, 0
  skips);
- **realistic costs** on the frozen legs (4 bps and 25 bps
  reporting, as in -08);
- simultaneous-entry ordering and terminal-open treatment exactly
  as audited/counted in -09 — no new conventions invented at run
  time.

### STEP 6 — SMCI disposition (parallel track, Mike's decision)

Independent of Steps 3–5 timing: the gated Alpaca sample card
(`SMCI_RESOLUTION.md` §2) can fire only after **G0** (Alpaca
re-screen passes — currently HOLD on license) **and G1** (its own
GO). Its outcome feeds the disposition decision (**B1** disclosed
43/44, **B3** defer, or an evidenced Alpaca SMCI/HO route via a
separate manifest amendment). If no disposition exists when Step
5 is ready, Step 5's universe is the qualified names with the
SMCI exclusion disclosed in the run's own record — Step 5 does
not wait indefinitely on SMCI, and SMCI is never silently
included or silently dropped.

### STEP 7 — Independent validation

Claude replicates Steps 3–5 from the **archive bytes** (not the
local store) and issues an independent verdict; ChatGPT
adjudicates; Mike decides adoption. A PASS here is what makes the
dataset + run QUALIFIED. **No edge claim before this step, under
any intermediate result.**

### STEP 8 — Protected out-of-sample evaluation *(LAST, separately gated)*

Only after Step 7: the sealed holdout's single governed use
(-25 §50) is drafted as its own authorization. Capturing W-HO
bytes in Step 3 does **not** open the holdout, does not count as
its evaluation, and does not weaken this gate. Nothing in this
prep touches it.

---

**What this prep changed:** nothing is authorized, captured, or
adopted. What exists now that did not exist before: a frozen,
root-digested 39-name manifest with the gates copied and the
receipt schema pinned; a completed second-source screen with a
named blocker and cure path; a frozen SMCI sample card behind its
two gates; and this trigger chain. When Step 1 clears and Step
2's GO lands, execution starts the same day.

— Muse
