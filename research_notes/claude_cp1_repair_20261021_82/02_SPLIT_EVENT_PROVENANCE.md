# ITEM 2 — SPLIT-EVENT PROVENANCE: NO PRODUCER EXISTS

**Finding: there is no qualified split-event source in the record,
and no component produces a split-event list.** This is verified from
the record three independent ways, not asserted from memory:

1. **The boundary contract says so.** The -60 boundary-coverage
   contract (`td_req_s2_boundary_coverage_contract_20261020_60/
   CONTRACT_MEMO.md`, sha256 c42a6b1642bf8c98…) maps the assembly DAG
   and records edge **G-EDGE-1 (split events → anywhere): NO
   producer**, adding: "Split events: NO — there is nothing to adapt.
   A producer must be CREATED (new component, its own adjudicated
   task…)".
2. **The consumers confirm it.** The only code that touches
   `split_events` in the entire repo is the -59 exclusion transform
   (`s2_split_exclusion_v1.py`, sha256 7791ca91eb18e63f…), which
   *consumes* an events argument, and the -61 boundary shim, which
   wires the same transform. A repo-wide search for any assignment or
   construction of a split-event list from a data source returns
   nothing. In -59's own qualification, the events "were synthetic
   fixtures" (-60 §5).
3. **The -62 audit confirms the consequence.** No split-window data
   had ever been acquired at audit time and Amendment S4's split
   checks had never executed (that changed only for the -75 probe's
   sampled windows, which produced analyzer verdicts — still no
   event-list producer).

## What exists vs what S2 needs

REQ-S2 (the split-session exclusion) is a *transform*: given bars,
candidate entries, and a split-event list, it removes the
{prev(D), D, next(D)} sessions per event, deterministically, with a
removed-session ledger (-59, 16/16 synthetic PASS). The transform is
qualified on synthetic fixtures and NOT integrated (no assembly point
exists upstream of indicators). What has never existed is the INPUT:
a pinned, provenance-bound enumeration of split events (symbol,
effective date, factor, as_of) covering the acquisition window.

The one vendor route documented in the record is excluded on tier
grounds: Twelve Data `/splits` is a Grow+ paid-tier endpoint,
excluded by the -63 desk packet; and a ChatGPT-relayed or vendor
authorization for any replacement leg has never been granted for this
purpose.

## The required gate that would create a producer

The -60 contract already specifies it (GATE-E1…E5, quoted in
substance; the contract is the authority):

- **GATE-E1 (producer existence):** a pinned split-event acquisition
  leg — endpoint, request manifest, receipt schema — must exist
  before integration. STATUS: ABSENT. No file, no hash can be cited.
- **GATE-E2 (coverage completeness):** the event inventory must
  provably cover every symbol × the full bar window; a missing event
  fails SILENTLY (no exclusion happens), so completeness needs an
  independent cross-check or a vendor completeness attestation bound
  into a hash-pinned receipt whose symbol×window set equals the
  bars' set exactly. Assembly refuses on any mismatch.
- **GATE-E3 (PIT availability):** each event carries `as_of`;
  assembly must refuse if any event's as_of is after the dataset's
  as_of cutoff, if the receipt lacks an acquisition timestamp, or if
  event provenance is not bound to the receipt bytes.
- **GATE-E4 (calendar-range edge coverage):** the calendar range
  supplied to the transform must extend ≥1 XNYS session beyond the
  bars' span on both sides, derived from (event inventory ∪ bars
  span), never set independently.
- **GATE-E5 (calendar source pinning):** the assembly receipt must
  record the calendar source + version the adjacency derivation used
  (the transform derives adjacency from a live calendar library and
  carries no calendar provenance in its output).

Creating the producer is therefore a NEW COMPONENT under its own
adjudicated task: a source must be selected (a vendor corporate-actions
leg under a fresh authorization, or an exchange/SEC-filing-derived
offline enumeration with its own completeness evidence), pinned, and
qualified against E1–E5 before S2 integration can even be proposed.
Under Mike's 2026-10-20 governing frame, the producer's design must
also answer the purpose question the -62 audit left open: S2's
exclusion has no demonstrated data-quality purpose until the
mixed-basis risk it guards against is either demonstrated in the
qualified feed or the gate is re-scoped to the demonstrated risk
(e.g., the -75 NVDA/TSLA sampled windows showed uniform adjustment —
evidence about sampled windows only, not a global verdict).

**Status: DOCUMENTED (no producer).** Owner: Muse (finding).
Creating the producer: **REQUIRES_SEPARATE_GO** (new adjudicated task;
any vendor leg additionally requires Mike's vendor authorization).
No ETA is offered for the producer itself beyond an estimate for its
design task: ~2–4 h build + one review cycle, once authorized
(estimate, not a commitment).
