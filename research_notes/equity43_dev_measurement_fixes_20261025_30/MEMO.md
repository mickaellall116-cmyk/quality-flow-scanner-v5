# -30 — P8 prospective-readiness repairs + P2/P3/P6/P9 semantic pins

QF-EQUITY43-DEV-MEASUREMENT-FIXES-20261025-30 · 2026-10-25

Governing text: ChatGPT's independent -29r verdict (Slack TS
1792941227.393299, 2026-10-25 11:13 ET): **P1 PASS** (bounded DEV
measurement repair; not edge evidence); **P8 HOLD** for prospective
use on two blockers — the calendar horizon and rejected-append
poisoning — plus a restart guard; and the still-pending **P2/P3/P6/P9
semantic pins/tests**. This package is exactly that next bounded
work. The -29 and -29r packages are unedited; the repaired modules
succeed theirs here. Bounds: measurement / telemetry / recording
only — no strategy change, no performance run, no holdout access, no
vendor calls, no pilot / S1 / G4 contact, no trading.

## A. Calendar horizon — versioned session-table extension

The adopted 751-session table ends 2026-10-16; `session_bins`
correctly failed closed after it, so the prospective journal could
not accept the Oct 26–30 pilot week or any later forward record.

**Delivered:** `artifacts/session_table_extension_2027.json` — a
separate, versioned artifact (`XNYS_SESSION_TABLE_EXTENSION_2027`,
calendar_version `XNYS-EXT-2027-20261025`), **303 sessions,
2026-10-19..2027-12-31**, sha256
`d2fa788d70f2c8677ca49b9e0201940586c051b9227f815b8d2da55b1e5d3a2f`.
The base table is byte-untouched (its sha re-verified in this
package's batteries, not trusted). Construction is explicit, by
`code/build_session_extension.py`: weekdays in the declared horizon
minus **named, dated NYSE closures** (12, incl. Good Friday
2027-03-26 and the observed Juneteenth / Independence Day /
Christmas closures), close 13:00 on the **named early closes**
(2026-11-27, 2026-12-24, 2027-11-26), 16:00 otherwise. No session is
extrapolated past 2027-12-31.

Qualification cross-checks (all recorded inside the artifact and
re-run by the verifier):
- **X1** — the same construction with the historical closure lists
  reproduces the adopted 751-session table **exactly** (dates +
  closes), including its one ad-hoc closure (2025-01-09 mourning).
- **X2** — exchange_calendars 4.13.2 XNYS agrees on all **256**
  sessions in its coverage (the vendored library's precomputed
  schedule ends 2027-10-25; the limit is recorded in the artifact,
  and the 2027-10-26..12-31 tail rests on the NYSE lists + X1/X3).
- **X3** — published counts: 251 sessions in 2027; 52 in the 2026
  tail; exactly 3 early closes.
- **X4** — continuity (first extension session is the first weekday
  after 2026-10-16) and disjointness from the base table.

Sources: NYSE Group press release 2025-12-23 ("NYSE Group Announces
2026, 2027 and 2028 Holiday and Early Closings Calendar") and the
NYSE Holiday Closures PDF (read 2026-10-25).

`code/session_bins.py` (successor) keeps `load_pinned_table()`
unchanged and adds `load_extension_table()` (sha + declared-parent
pin) and `load_union_table()` — 1054 sessions, duplicate dates
across the artifacts refused, dates in neither still fail closed.
The telemetry successor resolves bins through the union. The -29r
`test_session_bins.py` battery (base loader) passes verbatim.

## B. Transactional append + restart guard

The 29r defect, exactly as held: `append()` called `_track()` before
committing the line, and `_track()` mutated as it checked — a
backdated SIGNAL_FIRE advanced `_last_signal_idx` and inserted
`_fire_bin` *before* the stream-monotonicity check raised. Proven
fail-before against the -29r module in this lane: after the refusal,
`_last_signal_idx == {AAA: 301}` and `_fire_bin` held the ghost
`(AAA, 301)`, while the journal's lines held only the accepted fire
— a refusal that changed the journal.

**Repair (`code/qf_telemetry.py`, successor):** tracking is split
into `_validate_track()` (every link / order check, zero mutation)
and `_apply_track()` (mutations only). `append()` validates the
record, validates tracking, commits the line (file first, so an IO
failure mutates nothing), and only then applies tracking.
`_ingest_existing()` now re-runs `validate_record()` and
`_validate_track()` on load, after the chain/hash checks: hashes
prove the bytes are the bytes written, not that a record is
semantically valid.

**Battery (`tests/test_telemetry_txn.py`, 23 checks):** after each
refusal the full state snapshot (lines, chain head, all four
tracking dicts) is byte-identical; the same `signal_idx` then
accepts a valid record; ENTRY_OBSERVED / EXIT_FILL_OBSERVED cannot
attach to a rejected parent (no ghost fire, no re-parented fill —
the symmetric EXIT_DECISION overwrite is covered the same way);
file bytes are identical after refusals; and three hash-valid but
semantically invalid on-disk lines (17:30 decision, unfinalized
bar, smuggled field) are refused at restart while a valid journal
reloads cleanly. Horizon acceptance is exercised in the same
battery (pilot-week fire + entry observation, extension early
close, Thanksgiving refusal). The -29r telemetry battery (42
checks) is carried forward and passes with **one fixture moved**:
its beyond-table refusal used 2026-11-02, which is an extension
session now — the beyond-horizon refusal is exercised at
2028-01-03 instead. The horizon moved; the fail-closed property
did not.

## C. P2 / P3 / P6 / P9 semantic pins (`tests/test_semantic_pins.py`)

The -27 memo documented these semantics in prose; -28 R20 converted
P2/P6 to answers. This package pins them as executable artifacts
(25 checks):

- **P2 (rank semantics).** The frozen `pine_stack.py` copy is
  hash-verified against the -13 results.json P0 pin, then pinned
  structurally: `free0` occurs exactly once (dead code); the
  operative `free` is recomputed in-loop, `contested_now` uses the
  live value, the cap is `min(2, free)`, and the disposition order
  in source is rank → cap → sector gate → heat risk. The config's
  canonical (symbol, signal_idx) order and the ledger's census
  (taken 191 / skipped_rank 326 / skipped_risk 45 / skipped_gate
  28) reproduce.
- **P3 (SPY as-of).** `asof_benchmark.py` is hash-verified against
  its P0 pin; the 16:00 ET completion stamp is pinned at source
  and exercised functionally: at 09:30 and 13:30 on day D the
  frozen selection rule picks D−1's completed session, an
  early-close bar is stamped 16:00 and is invisible at 14:00 that
  day (delay, never leak), and the retired midnight construction
  is shown selecting the same day's bar (the -08 defect, kept as
  the fail-before artifact).
- **P6 (exposure reporting).** `code/exposure_report.py`
  implements the -27 §2.6 spec (per-position entry notional;
  per-event gross/net exposure; peak/mean gross; maximum
  single-position share), pinned by hand-computed fixtures.
  Applied to the committed DEV artifacts (`artifacts/
  exposure_dev.json`): peak gross **2.7859x** (basis A, committed
  -29r equity series, last mark ≤ entry) / 2.7792x (basis B),
  mean 1.18x, max single-position share **1.6453x** (MELI,
  risk_frac 0.61% — the unbounded-notional point made concrete),
  max concurrency 5. The flat-equity cross-check reproduces the
  recorded 2.83x proxy (2.8337x). Declared limits: full entry
  notional held to exit (post-TP1 runner halving is not in the
  ledger, so the intra-hold path is an upper bound; the exact path
  is UNVERIFIABLE from the record). Heat is never reported as
  exposure.
- **P9 (ledger parity).** `code/parity_check.py` recomputes all
  three cost views from the committed -13 ledger, each over its
  OWN taken set, and diffs against results.json's P5_run rows at
  the rows' rounding: 26/26 checks PASS (artifact
  `p9_parity.json`). The 25bps leg — the -27 gap — reproduces
  exactly: 189 taken / 185 closed / +0.107509R. total_return_pct
  and max_drawdown_pct are carried as reported, not verified
  (equity path required; the all-bar DD is the -29r P1 artifact).

## Verification

`code/verify_package.py` — manifest integrity, both table pins,
X1 re-run, artifact/recomputation agreement, and all five
batteries (20 + 32 + 42 + 23 + 25 checks) exit 0.

## What this does not do

No strategy or simulator change (the pinned sources are read, never
edited); no performance run; the -29r design note stands unchanged
(append order is causal — a late duplicate observation is refused
as backfill; a recorded-at-only track remains an adjudication item,
not a defect). P8's remaining gate is ChatGPT's independent
qualification of this package; S1 launch and any pilot use still
require their own GOs. Production PAUSED; holdout SEALED; the
original C1 FAIL stands; nothing here is edge evidence.

— Muse
