# MANIFEST AMENDMENT -93 (SPEC §4) — one receipt schema, read
# accounting, crypto chunk bounds + DEV/HO seam, holdout firewall,
# sequence conflict, consolidated pin

Amends the -88 capture manifest package
(`capture_manifest_provenance_20261021_88` at `6b0f5d0`) and the
-91 credit-accounting correction (`repair_91_20261021` at
`db9e0f3`) BY REFERENCE. Neither package is edited. This amendment
authorizes nothing: the capture GO (route + ceiling + manifest
pin) remains Mike's, after adjudication. All totals below are the
-91 corrected figures (program 146 expected / 289 worst); this
amendment changes no totals.

## 4.1 — One receipt schema (supersedes -88 PROVENANCE §2 by reference)

One schema for every record in a capture chain, discriminated by
`kind`. A single schema — not per-attempt records plus side
ledgers — is what makes the chain auditable end-to-end.

`kind: phase_open | attempt | block_close | phase_close`

Common fields (all kinds): `schema` (= `qf-receipt/2`),
`capture_id`, `phase`, `seq` (monotonic commit counter, -74
discipline), `prev_receipt_sha256` (hash chain; a `phase_open`
chains to the capture manifest pin, §4.6), `written_at_utc`,
`executor` (route/stack pins as in -88).

`attempt` adds: `leg_id`, `symbol`, `window`, `chunk`; `request`
(exact parameters as sent, as in -88); `attempt_no` (1 or 2);
`block_id`, `block_position`; `started_at_utc`, `finished_at_utc`;
`pace_slot` (the attempt's scheduled offset under the 8/min
pacing rule, §4.2); `http_status`; `response_bytes`,
`response_sha256`; `row_count`; **`credit_headers`** — the
vendor response's credit/rate headers and meta block **verbatim**
(`vendor_meta` in -88 terms, now explicitly including any
credit, limit, and reset headers present), never normalized,
never dropped; `bracket_open_sha256` (the usage read that opened
the attempt's block).

`block_close` adds: `block_id`, `attempts_in_block`,
`bracket_close_sha256`, `usage_open`, `usage_close`,
`reconciled` (bool). The block's closing usage read IS this
record's evidence; its sha256 is what later receipts cite —
receipts no longer claim a closing-bracket hash they cannot know
at attempt time (the -88/-91 seam this removes: -91 required each
receipt to record both bracket hashes, but a receipt written at
attempt time cannot know its block's closing read; the
`block_close` record kind is where that hash legitimately lives).

`phase_close` adds: `blocks`, `usage_reads`, `attempts_total`,
`credits_phase` (= attempts + reads, §4.2 identity),
`pilot_closing_read` (bool — see §4.2), `chain_head_sha256`.

A leg with a missing or malformed record chain is treated as not
executed, however plausible its body looks (-88, preserved).

## 4.2 — Read accounting: unit cost, pacing, reset, closing read

The BLOCK-BRACKET-10 scheme (-91) is preserved in full; this
section states the three accounting facts the -92 review asked to
see inside the scheme rather than beside it.

- **Unit cost.** Every API call — data leg or `/api_usage` read —
  costs exactly 1 credit (evidenced: -69, -75, Policy A). Block
  reconciliation is fail-closed: for every block k,
  `u_k − u_{k−1} = attempts_k + 1` (the +1 is the closing read's
  own charge), else execution halts.
- **Pacing.** The vendor's 8/min rate limit is a scheduling
  constraint, not a credit: attempts are spaced ≥ 7.5s within a
  block (`pace_slot` records the planned offset). Pacing consumes
  no credits and appears in no total; a pacing violation is an
  execution defect recorded on the attempt, not an accounting
  adjustment.
- **Reset.** The daily credit budget resets at the vendor's day
  boundary. No block may span a reset: a block that would cross
  the boundary closes early (a short block is legal; its
  reconciliation identity is unchanged), and the next block opens
  after the reset with a fresh `phase_open`-chained bracket read
  on the new day. A usage delta that crosses a reset is
  unreconcilable by construction and is therefore made
  unreachable by construction.
- **Pilot closing read.** The pilot's final `block_close` read is
  the **pilot closing read**: it is counted (reads = blocks + 1,
  already in the -91 pilot total of 19 expected / 37 worst) and it
  is the read whose reported usage the Phase-1 GO decision cites.
  No additional uncounted closing read exists anywhere in the
  program; Phase 1 closes the same way (its final block_close is
  its closing read, inside 127/252).

## 4.3 — Crypto chunk bounds and the DEV/HO seam (no leakage)

Chunk bounds (-88 §3.2, restated exactly): crypto sessions are
[D 09:30 ET, D+1 09:30 ET) under S-C1…S-C6; chunks are
date-bounded at ≤ 208 consecutive ET dates (≤ 4,993 hourly bars by
construction; a 5,000-row response is a fail-closed defect);
chunk boundaries are the -88 table (HO-C1/C2, DEV-C1…C4 per
symbol; 42 legs).

**The seam.** The holdout window's last crypto session is the ET
date 2024-09-15, i.e. the interval [2024-09-15 09:30 ET,
2024-09-16 09:30 ET). The development window's first session is
[2024-09-16 09:30 ET, 2024-09-17 09:30 ET). The intervals are
half-open and adjacent: every hourly bar belongs to exactly one
window; the bar stamped 2024-09-16 09:30 ET is DEV's first bar
and is not HO's last. **Seam verification (pre-construction,
named):** before any crypto construction, the checker (v3 crypto
mode) runs over the union of each symbol's HO and DEV bodies; the
seam is clean iff the union's COUNT over the seam dates shows
zero duplicated stamps and zero missing stamps across
2024-09-15/16/17 — any overlap is a DUPLICATE_TIMESTAMP
structural defect, any gap a missing-bar finding, and either
fails the seam closed. Leakage in the other direction (DEV bars
inside HO intervals) is the same check read from the other side;
there is one check, not two.

Equity seam analog: XNYS sessions are discrete; HO ends at the
2024-09-15 session and DEV begins at 2024-09-16's — disjoint by
the adopted calendar itself, verified by the same union COUNT.

## 4.4 — Holdout report firewall

Capturing W-HO bytes does not open the sealed holdout (-88 §2,
preserved). This amendment makes the firewall a checkable
property of artifacts, not a promise:

1. **Phase separation in every record.** Every receipt carries
   `phase`; every body path carries its phase (`<phase>/…`). A
   record or body without a phase is malformed by schema.
2. **No HO inputs to DEV artifacts.** Any report, readout, or
   checker record produced from DEV-phase bytes must list its
   input leg_ids; a DEV artifact listing an HO leg_id — or an HO
   body hash — is a firewall breach by inspection of its own
   provenance fields, detectable by any reviewer from the
   artifacts alone.
3. **HO aggregates are not DEV evidence.** No statistic computed
   over HO bytes (counts beyond the seam check's zero/nonzero
   answers, distributions, coverage summaries) may appear in a
   DEV-phase report. The seam check (§4.3) is the single named
   exception, and it reports only duplicated/missing stamp
   identities at the seam dates — the minimum the no-leakage
   proof requires.
4. **The holdout's single governed use remains -25 §50.** This
   amendment creates no second use.

## 4.5 — Sequence conflict (stated, not resolved)

Two sequences want the same vendor days, and the manifest must
not pretend they compose silently:

- The **probe sequence** (Day-1 done at -75; R7 eligible
  2026-10-28T21:33:00Z; R30 eligible 2026-11-20T21:33:00Z — each
  its own Mike GO) re-pulls the -75 legs to test vendor revision
  behavior over time. S2 reopen triggers T1–T3 watch these legs.
- The **capture sequence** (pilot, then Phase 1) is this manifest.

Conflicts: (i) both draw on the same 800/day free budget on any
shared execution day; (ii) probe re-pulls after a capture would
create a second, later version of bytes the capture chain has
already pinned — revision evidence the capture's provenance must
be able to cite without its own chain appearing rewritten;
(iii) if capture runs first, the probe legs' "as-first-seen"
value for the revision question is spent for the captured
symbols. Proposed discipline (FOR ADJUDICATION): probe and
capture never share an execution day; each runs its own receipt
chain rooted at its own manifest pin (§4.6); probe results cite
capture body hashes by reference when they re-pull a captured
leg, never by replacement. **The ordering itself is a Mike-only
ruling (§7 of SPEC_93 / ADOPTION_NOTES)** — this amendment states
the conflict and the discipline; it does not choose the order.

## 4.6 — Consolidated pin

One pin over everything a capture execution depends on, computed
as sha256 of the canonical pin table (one `name|sha256` line per
artifact, sorted by name, LF-joined, trailing LF). Entries known
today:

| Artifact | Pin |
|---|---|
| `calendar_2023_extension` | `8d659dde9ccb51b9d86d6c45759abceb6ccd90ad7fa49e7478b13c2dc153a0a2` |
| `calendar_dev_segment` (XNYS_SESSION_SCHEDULE_V2) | `3358f2d9cc233142f0927d3a16c3a353e935ed4310c563ac046352dcf75d2b88` |
| `checker_v3_candidate` | sha256 of `checker/tsla_completeness_check.py` in this package's SHA256_MANIFEST |
| `constructor_pinned` (`construct_4h`) | `d47e8df14ec5f6f60f46b874af174e97ee60dcc796244c61293f0f2138d92cfd` |
| `guard_v3_candidate` | sha256 of `guard/constructor_guard.py` in this package's SHA256_MANIFEST |
| `package_88_capture_manifest` | commit `6b0f5d0737215af5eaeec150750ec0607ffb7996` |
| `package_91_credit_accounting` | commit `db9e0f3f946160bb533735bf2dedcb5b4837fcdd` |
| `universe_ux51_canonical` | `b5d8877ee7d6ddd105904d7f4ca35901ebb611dac7afeab2f7676529c112e6a2` |
| Session-table binding value | `calendar_sha256` of the adopted 751-session table, computed at capture preflight via guard v3 and pinned into the capture manifest at GO (not in today's pin) |

The consolidated pin VALUE is computed and recorded in
TEST_EVIDENCE.md for the entries fixed today; the session-table
line enters it at the capture GO, when the table's canonical dict
form is fixed by the executing stack. A capture whose preflight
consolidated pin differs from the GO's pin does not execute
(fail-closed) — that is what the pin is for.
