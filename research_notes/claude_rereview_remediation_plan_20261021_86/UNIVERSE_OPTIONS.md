# UNIVERSE OPTIONS — FOR MIKE'S RULING (this document decides NOTHING)
## Part of the -86 remediation plan; responds to Claude finding F1

All membership facts below were computed in this task from the
pinned sources (AST extraction of the list literals; no list was
taken from any summary, including -82's or -85's).

## 1. Membership evidence — one hashed membership, four sources compared

| Source | Pin | Membership object | n |
|---|---|---|---|
| `pine_backtest.py` (origin/main) | sha256 447a9a13bb2ec7ab… | `UNIVERSE_X` (= `UNIVERSE_15` + 36); run tags "U15"/"UX51" (line 359) | 51 |
| `hybrid_exit_test.py` (running stack) | sha256 9140504f6449cafe… | `UNIVERSE_X` | 51 |
| C1 corrected-baseline script (CP1 closure) | sha256 4568823cb8fe645a… | `import pine_backtest as pb` → `pb.UNIVERSE_X`; records `universe_window` "UX51 4H 2024-09-16 -> 2026-09-14" | 51 |
| `v54_forward_harness.py` (deployed, -37 pin) | sha256 ce7c902ce182683c… | `UX51_UNIVERSE = list(hybrid_exit_test.UNIVERSE_X)`; `FORWARD_UNIVERSE = UX51_UNIVERSE + list(ux2.UNIVERSE_X2)` | 51 + 199 = 250 |
| `v54_universe_x2.py` (running stack) | sha256 44b0d8ba5a7ea641… | `UNIVERSE_X2` (FROZEN 2026-09-15) | 199 |

**Comparison result.** `pine_backtest.UNIVERSE_X` and
`hybrid_exit_test.UNIVERSE_X` are **identical — same 51 symbols,
same order**; the C1 script's membership is that same list by
import. `UNIVERSE_X2` is **disjoint** from UX51 (intersection = ∅),
so the forward membership is exactly 51 + 199 = 250 with no
double-count. There is therefore ONE 51-name membership in the
record, not four competing ones; what differs across sources is
only the cohort it is combined with.

**THE pinned membership (UX51), in source order:**

NVDA, PLTR, TSLA, SOFI, SMCI, AMD, AAPL, MSFT, META, COIN, MSTR,
AVGO, BTC-USD, ETH-USD, SOL-USD, GOOGL, AMZN, NFLX, CRM, MU, INTC,
LRCX, AMAT, QCOM, ARM, HOOD, APP, NET, SNOW, DDOG, CRWD, SHOP,
RKLB, ASTS, LUNR, PYPL, NU, MELI, SPY, IWM, SMH, ARKK, XLF,
DOGE-USD, AVAX-USD, LINK-USD, XRP-USD, NIO, MRNA, PFE, F

**Composition (computed, not asserted):** 39 single-name equities
+ 5 ETFs (SPY, IWM, SMH, ARKK, XLF) = **44 exchange-traded names**
+ **7 crypto pairs (BTC-USD, ETH-USD, SOL-USD, DOGE-USD,
AVAX-USD, LINK-USD, XRP-USD)** = 51.

**Canonical hashes** (serialization: symbols sorted, LF-joined,
trailing LF — this package pins THESE as the membership hashes):

- UX51: `b5d8877ee7d6ddd105904d7f4ca35901ebb611dac7afeab2f7676529c112e6a2`
- X2: `eddbaf9a4b604fffbd140414583579e6ee6d7eee7a4d97b6d94c45c47efd022d`
- FORWARD (UX51 ∪ X2): `3a8d02529169b1dd22055247019231b96efc50ed05a48fec9f5a3dab19500e20`
- (UX51 in source order, same serialization:
  `533b2652d7bff274ecf186dd4e9f98c4ff32e7cf0532809395d9cf0f284c5b79`.)

Note: -85 cites a different UX51 definition hash
(`d139d7bf…`, -77 §0) under a different serialization. Both name
the same 51 symbols as extracted here; going forward the hash
above is the one membership pin, and -85's figure is superseded
by reference for membership purposes (see DATA_ROUTE_DELTA_85.md).

## 2. The -82 X2 rationale was ERRONEOUS — stated plainly, corrected by reference

The -82 designation memo (item 1) is NOT edited; the following
errors in it are corrected by this reference:

1. **False composition contrast.** The memo argued against X2
   partly on composition — X2 as the cohort "containing crypto
   pairs and macro ETFs", against UX51 as the baseline universe.
   That contrast is false: **UX51 itself contains 7 crypto pairs
   and 5 ETFs** (§1). Composition does not distinguish X2 from
   UX51 in kind, only in degree (X2: 18 crypto of 199).
2. **The designated universe's composition was never disclosed.**
   The memo designated UX51 for a qualification program whose
   calendar is the XNYS session schedule, without stating that 7
   of the 51 are continuous-market crypto pairs **no XNYS
   calendar can govern**. The 44 + 7 split first appears as an
   ad-hoc costing device in -85, not as a disclosed property of
   the designation. A designation that does not state what the
   universe contains is defective as a designation.
3. **The survivorship framing understated the selection.** See §3.

What survives of -82 item 1: the provenance facts (C1 ran on
this list; D1's pins cover it; the -25 preregistration registers
H_cohort_UX51) are true and remain the record. What is corrected
is the rationale built on them.

## 3. Survivorship / hindsight framing — exact statement

`UNIVERSE_X` is a hand-assembled list in a script of the
September-2026 program. There is **no point-in-time selection
rule** for it (no ranking, no as-of date, no eligibility
criterion) and **no freeze of the membership predating the
windows it is applied to**: the earliest pinned reference to the
list as a cohort is the forward test's day-1 freeze of X2
(2026-09-15), which references UX51 as already existing. The
membership was therefore **selected with 2026 hindsight** —
assembled with full knowledge of which names mattered in
2024–2026 — and is applied retrospectively to the holdout window
(2023-10-19 → 2024-09-15) and the dev window (from 2024-09-16),
both of which precede or overlap its assembly. It contains no
delisted names by construction (names that died before Sep 2026
could not be picked), and its survivorship bias is of unknown
size and **cannot be bounded from inside the record**. Any
result on this membership is a result about a survivor-curated,
hindsight-selected 51 — under EVERY option below that retains
it, that sentence must travel with the result. (This is the
UPIT axis of F6 — distinct from E3, which is split-event timing
and has no bearing here.)

## 4. Options for Mike's ruling

### Option A — UX51 intact (44 XNYS-calendar names + 7 crypto on a separately specified continuous calendar)

- **C1 comparability:** preserved exactly. Same membership
  (hash b5d8877e…), same list C1 ran on; the corrected baseline
  remains the same research family and C1's readouts remain
  directly interpretable against its rerun.
- **Calendar:** TWO calendars must be qualified. The 44 use the
  XNYS track (candidate 8d659dde… + -35 r2). The 7 crypto pairs
  need their own bar-construction specification: in the C1
  construction they were built on the same UTC-anchored 4H grid
  as everything else (the C1 script's grid is UTC-anchored
  13:30/17:30 UTC) — a corrected qualification must state the
  crypto construction explicitly as its own spec; it cannot
  borrow the XNYS session schedule, and its session/bar counting
  for hold and indicator windows must be declared.
- **-85 request math:** unchanged — 88 firm (44 × 2) + ≈42
  estimated (7 crypto × ≈6) + 2 usage ≈ **132 expected /
  ≈264 worst case**, ceiling 300 stands.
- **Family ledger:** unchanged family; the -25 Holm family
  (H_pooled, H_cohort_UX51, H_cohort_X2, grades) stands as
  registered. Pooled UX51 readouts mix two bar physics
  (session-bound and continuous) — a disclosure obligation on
  every pooled readout, not a bar to the option.

### Option B — Equity-only 44 (the 7 crypto pairs leave the corrected-baseline universe)

- **C1 comparability:** BROKEN, and stated as such. C1's
  readouts include crypto-symbol trades; a 44-name rerun is a
  different universe, so "corrected C1" cannot be claimed — C1
  remains prior-family forensic evidence. Under -25 §2 a
  universe change creates a **new research family**.
- **Calendar:** ONE calendar — the XNYS track only (candidate
  8d659dde… + -35 r2). The simplest qualification surface of
  the three options; no crypto construction spec is needed.
- **-85 request math:** 44 × 2 = 88 firm + 2 usage ≈ **90
  expected / ≈180 worst case**; the ≈42-request crypto estimate
  is deleted; the capture ceiling should be re-derived
  (≈200 covers the worst case with margin). Earliest-dataset
  dates are unchanged (the waits are decision-shaped, -85 §5).
- **Family ledger:** new family entry required; the -25 Holm
  family does not transfer (a new preregistration or a governed
  amendment creating the family is required). The FORWARD test
  is untouched — its frozen 250 (51 + X2) keeps its own UX51
  cohort of 51 — so the baseline family's "UX51" (44) and the
  forward family's "UX51" cohort (51) would thereafter be
  DIFFERENT sets under one name; all future reporting must
  disambiguate them (e.g. baseline-44 vs Forward-UX51) or the
  same conflation class recurs.

### Option C — The canonical PIT 131 as the corrected-baseline universe (new family)

The 131-symbol construction of `canonical_baseline/UNIVERSE.md`
(sha 1df084af…; top-120 by trailing-63-day ADDV as of
2023-09-30 + 11 rule-admitted new listings; built 2026-09-24/25,
never adopted).

- **C1 comparability:** NONE. A different membership (131 vs
  51, partially overlapping); a baseline on it is a new
  baseline, not a correction of C1. C1 stays forensic evidence
  for the data-defect question only.
- **Calendar:** ONE calendar (XNYS) — the construction excludes
  *-USD pairs from ranking by rule, so no crypto track exists.
- **-85 request math:** 131 session-bound × 2 = **262 firm** +
  usage ≈ **264 expected / ≈528 worst case**; the ceiling must
  be re-derived (≈550) and still fits the documented 800/day
  free allowance at expected volume. NEW RISK the other options
  don't carry: per-name vendor coverage of 2023-era names is
  unproven (the construction's own record shows CYBR
  unrecoverable from Yahoo; Twelve Data coverage of every 131
  name is UNCONFIRMED) — names the route cannot serve become
  DATA_UNQUALIFIED reductions, i.e. the executed universe could
  silently shrink below 131 unless the capture gate refuses on
  any missing name.
- **Family ledger:** NEW family, requiring its own
  preregistration. Its UPIT story is the strongest of the three
  (selection rule knowable on 2023-09-30; delisted handling
  documented) with one residual the construction itself
  discloses: the candidate POOL was the union of the program's
  2026 lists (hindsight-influenced pool, PIT selection rule) —
  the residual is named, not hidden.

## 5. Muse assessment — labeled, NOT a ruling

> The choice turns on what the corrected baseline is FOR. If it
> exists to answer CP1's forensic question — was the C1 result
> an artifact of defective data — only Option A keeps that
> question well-posed, because changing the universe changes
> the question. If it exists to start the most defensible new
> validation family, Option C has the cleanest selection story
> and Option B the smallest qualification surface, and both pay
> for it with a new family and the loss of C1 comparability.
> What is NOT available under any option: keeping the -82
> designation's language ("provenance-designated, survivorship
> noted") without the §3 hindsight sentence attached. — Muse

**Status: OPTIONS DOCUMENTED for Mike's ruling (GO G6 in
REMEDIATION_PLAN.md). Nothing in this document designates a
universe.**
