# O4 Basis Pin — paired-SD cost basis (PROPOSED)

**Status: PROPOSED — effective on ChatGPT's concurrence in review.
The O4 computation itself remains blocked on Mike's direct GO,
unchanged.**

## Why this pin exists

ChatGPT's independent G5 review (Issue #1 comment `6434458722`),
hold 2: `O4_PROCEDURE.md` leaves the leg cost basis unresolved — its
§3 states the estimator on the §8 per-fill convention, while the DEV
record's Stage-1 views carry the flat per-trade convention — and the
exact basis/config hash must be pinned **before** an O4 GO is
requested, so the GO covers a fully specified computation.

## The pin

- **Cost basis for the O4 paired-SD estimation:** the **Stage-1 flat
  cost views of the frozen C1 experiment configuration**, canonical
  pin
  `87b8285a522ba0e3e5a80f0097b9668afc1ddf11da4fc5559c0ca31f55218706`
  (driver `run_study13.py`, -13 package; reproduced in the G5
  package's `MECHANICAL_CHECKS.md`). The gating view is the **25 bps
  round-trip flat view** of that config, matching the frozen
  constants already on record in `O4_PROCEDURE.md` §1 (δ = 0.10R,
  Holm allocation over {1, 3, 4}, 100-closed-trade validity floor).
- Where `O4_PROCEDURE.md` says "§8 per-fill cost convention", this
  pin substitutes the Stage-1 flat convention above. Every other
  element of `O4_PROCEDURE.md` stands unaltered: DEV-only inputs,
  arms E0/E1/E3, the §7 pre-entry gap exclusion, the common retained
  set, and variance-only reporting (only {n, SD, DE, n_eff} leaves
  the run).

## Why Stage-1 flat, not §8 per-fill

1. **It is the only cost config in the record.** No config recording
   the §8 per-fill conversion exists anywhere in the record (the G5
   package's P5 finding). Authoring one is the P5 Stage-2 staging
   step; inventing a config inside the O4 lane would put an
   unreviewed artifact under a gated computation.
2. **The DEV legs of record were computed under it.** The -13 DEV
   ledger (SHA-256
   `267e794c284a409d7d9b6d8e1056c452976b59746062e9e18c5664b74c003b`) —
   the Tier 1 evidence base O4 pools — carries the Stage-1 flat
   views (gross / 4 bps / 25 bps). SDs estimated on the same basis
   describe the quantity the DEV evidence actually carries;
   switching basis for the SD alone would mix conventions inside one
   power calculation.

## Effect and limits

- On ChatGPT's concurrence, `O4_PROCEDURE.md` is read with this pin
  and its §3 "Open review point" stands resolved as above.
- This pin authorizes nothing. The computation runs only on Mike's
  direct GO, as recorded in the 2026-10-26 closure addendum and in
  `O4_PROCEDURE.md`. O4/EXIT remains separately gated from the
  BUY-only G5 freeze.

— Muse
