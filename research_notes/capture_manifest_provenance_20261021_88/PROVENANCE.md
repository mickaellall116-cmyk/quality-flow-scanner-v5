# DATA PROVENANCE — UX51 CAPTURE (task -88)
## The chain that lets a reviewer re-verify a capture without trusting Muse

**Purpose.** Every captured byte must carry enough evidence that
ChatGPT, Claude, or Mike can independently establish: what was
requested, what the vendor returned, when, at what credit cost, and
that the bytes on disk are the bytes received — without taking the
executor's word for any of it. This document specifies that chain
for the capture defined in CAPTURE_MANIFEST.md. It authorizes
nothing.

## 1. Objects

- **Leg:** one manifest request (CAPTURE_MANIFEST.md §3), identified
  `ux51v1/<PHASE>/<SYM>/<LEG>` (e.g. `ux51v1/pilot/NVDA/HO`,
  `ux51v1/phase1/BTC-USD/DEV-C3`).
- **Attempt:** one HTTP execution of a leg (≤ 2 per leg).
- **Receipt:** the per-attempt record (§2), written transactionally
  by the -71 receipt writer as closed in -74 (70/70).
- **Body:** the vendor response bytes, stored byte-exact, never
  transformed in place. Any later transformation (construction,
  checking) reads the body and writes elsewhere.

## 2. Receipt fields (per attempt, all required)

| Field | Content |
|---|---|
| `leg_id`, `capture_id`, `phase` | Manifest identity (§1) |
| `symbol`, `window`, `chunk` | Manifest leg coordinates |
| `request` | Exact parameters: endpoint `/time_series`, `interval=1h`, `adjust=splits`, `outputsize=5000`, start/end bounds as sent, `order` |
| `attempt` | 1 or 2 |
| `started_at_utc`, `finished_at_utc` | Executor clock, ISO-8601 Z |
| `http_status` | As received |
| `response_bytes`, `response_sha256` | Byte count + sha256 of the stored body (of the error body on failure) |
| `row_count` | Rows parsed from the body (0 on failure) |
| `vendor_meta` | The response's meta block **verbatim**, including any `last_change` / version fields present — never normalized, never dropped |
| `usage_before`, `usage_after` | The day's /api_usage snapshot bracketing the leg (`daily_usage`, `plan_daily_limit`, minute bucket), from the preflight + closing snapshot |
| `credit_delta` | `usage_after.daily_usage − usage_before.daily_usage` for the day, reconciled at day close (§3) |
| `prev_receipt_sha256` | Hash chain link (§3) |
| `commit_state` | Monotonic commit counter (§3) |
| `executor` | Entrypoint/CLI/constructor pins of the executing stack (route manifest `9573118c…` lineage), code commit of the capture driver |
| `ch1_flag` | `true` for W-HO legs (CH-1 disclosed assumption, CAPTURE_MANIFEST.md header) |

A leg with a missing or malformed receipt is treated as not
executed, however plausible its body looks.

## 3. Hash chaining + monotonic commit (-71/-74 discipline)

- Receipts form a **hash chain** in execution order: each receipt
  embeds `prev_receipt_sha256` = sha256 of the previous receipt's
  canonical bytes; the first receipt of a capture phase chains to
  the phase's `capture_manifest.json` hash. A gap, reorder, or
  rewrite anywhere breaks every later link — tampering is
  detectable from the receipts alone.
- **Monotonic commit:** the writer assigns `commit_state` as a
  strictly increasing integer per capture directory, persisted
  transactionally with the receipt (the -74 closure: a receipt
  exists on disk complete, or not at all; `commit_state="1"`
  semantics proven live in -75). No receipt is ever edited after
  commit; a correction is a new receipt that cites the one it
  supersedes.
- **Day-close reconciliation:** at each execution day's end, the
  ledger asserts: sum of per-leg `credit_delta` reconciles with
  the day's /api_usage movement, receipt count = attempts made,
  chain head = last receipt. A failed reconciliation fails the
  day closed and is reported with the receipts as evidence.

## 4. Checker pass — recorded per symbol before construction

No captured symbol's bytes may be consumed by construction until
its **checker record** exists. The checker is the independent
completeness/convention instrument (-82 item 4, fixture-proven
14/14 in its v1 form; v2 per -86 F4 — NaN/negative/1-share lanes,
VBASIS, STEP-ALL, declared-boundary table — adoption is the
separate G4 gate in the -89 lane; until G4 lands, the v1 checker
record is what the pilot produces and the gap is disclosed in the
pilot report). Per symbol, the record states:

- checker identity (code pin + version), run instant, input body
  hashes (must equal the receipt `response_sha256` values);
- per-window verdict: row count vs the manifest's calendar
  expectation (§3 of the manifest), every anomaly enumerated
  (zero-volume bars, missing hours/sessions, duplicates,
  non-monotonic stamps) with counts and coordinates — zero
  *unexplained* anomalies is the qualification bar;
- convention lanes: split-step detection with factor estimates
  (under the S2-REJECT freeze this is a **reporting** instrument:
  it feeds the SPLIT_SPANNING subset of the session rules, it
  excludes nothing);
- verdict: `QUALIFIED_CLEAN` / `COMPLETENESS_FAIL` /
  `CONVENTION_BREAK_SUSPECT`, signed into the capture directory
  and covered by SHA256SUMS.

## 5. Revision evidence (R7/R30-style; S2 reopen trigger T1)

The freeze's S2 reopen trigger **T1** — an R7/R30 leg showing a
basis revision — is only decidable if first-pull bytes survive
unchanged with their receipts. Accordingly: bodies and receipts
are **write-once** (archive rule); a later re-pull of the same leg
is a *new* leg instance in a new capture directory, chained to its
own receipts, and the comparison (byte equality, row-level diff,
`vendor_meta.last_change` movement) is computed from the two
preserved artifacts — never from executor memory. The -75 Day-1
store (`captures/td_probe_day1_20261021/`, archive commit
`2f223cf`, 20/20 re-fetch verified) is the working precedent and
the comparison base for the probe legs' R7/R30.

## 6. Reviewer re-verification (no trust in Muse required)

A reviewer with only this package, the archive, and git can:

1. Recompute SHA256SUMS over the capture directory from a fresh
   fetch of `qf-data-archive` and compare (the -75/-81 procedure).
2. Walk the receipt hash chain from `capture_manifest.json` to
   the head; confirm monotonic `commit_state` with no gaps.
3. For any leg: recompute `response_sha256` over the stored body;
   confirm it matches the receipt, the checker record's input
   hashes, and SHA256SUMS — three independent mentions of one
   hash.
4. Recompute the calendar expectations (751 sessions; per-symbol
   row counts; crypto date-span hours) from the adopted calendar
   artifacts (`8d659dde…` + `3358f2d9…`) and this manifest, and
   compare against receipts + checker records.
5. Reconcile credits: sum receipts against the /api_usage
   snapshots and the program ledger (8 credits spent pre-capture,
   -75; ceiling per Mike's capture GO).
6. Confirm membership: hash the sorted-LF symbol list and compare
   to `b5d8877e…` (-86 §1).

Any step failing is a named, evidenced blocker — reported, never
smoothed over.
