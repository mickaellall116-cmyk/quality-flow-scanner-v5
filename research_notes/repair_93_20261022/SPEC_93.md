# REPAIR SPEC -93 — Claude -92 HOLD items: guard v3, checker v3,
# R1–R5 amendment draft, manifest amendment, CH-1 verification

Source of the assignment: ChatGPT, GitHub Issue #1 comment
6343957169 (2026-10-22 15:02Z), relaying Claude's -92 targeted
review verdict: CH-1 PASS for retirement (conditional — archive PDF
byte verification + supersession note); R1–R5 HOLD; guard v2/-91
HOLD despite repair correctness; checker v2/-91 HOLD despite
repair correctness; -82 divergence PASS unchanged; credit scheme
HOLD minor (arithmetic / 300 ceiling PASS: 146 expected / 289
worst); pilot HOLD.

Scope honored: OFFLINE / synthetic only. No vendor calls, no
credits spent, no capture, no holdout access, no performance runs,
no production or frozen-strategy changes, no shadow launch, no
trading. The -88 / -89 / -91 packages are NOT edited; this package
supersedes by reference where it corrects them. Option A UX51 is
not touched. Everything here is a CANDIDATE: all adoptions remain
HOLD pending ChatGPT + Claude adjudication and Mike's GOs.

Implemented as code (isolated synthetic fixes, where unambiguous):
§1 guard v3, §2 checker v3. Drafted as text for adjudication
(spec-only, no code): §3 R1–R5 amendment, §4 manifest amendment
(in MANIFEST_AMENDMENT.md). Verified: §5 CH-1 archive bytes.

---

## §1 — Guard v3 (`guard/constructor_guard.py`, GUARD_VERSION `guard-v3-candidate-1`)

Base: the -91 repaired v2 candidate, byte-copied, then extended.
The v2/-91 refusal classes, their order, and clean-path
byte-identity are preserved (floor re-proven: §6). V3 adds, all
pre-construction, constructor never invoked on refusal:

1. **NONFINITE** (`CONSTRUCTOR_GUARD_NONFINITE`) — any NaN or ±inf
   in Open/High/Low/Close/Volume refuses; a missing OHLCV column is
   a cannot-verify refusal under the same code. Closes the v2 hole
   Claude named: the constructor's dropna silently discarded
   NaN-OHLC rows and the volume-conservation shadow mirrored the
   exclusion, so a vendor **placeholder NaN row** crossed the
   guarded boundary and vanished, while the checker classified the
   same row a completeness defect. The shadow's dropna mirror is
   now unreachable on guarded input — the boundary and the checker
   agree. Fixture V3_G6 proves both halves: the shadow, invoked
   directly, still excludes the NaN row silently (the divergence,
   on the record); the guarded path refuses the same frame.
2. **INTERVAL_END exactness** (`CONSTRUCTOR_GUARD_INTERVAL_END`) —
   when the frame carries an `interval_end` column, every stated
   end must be a grid end for its bar: the next session-grid start
   for a non-final bar; for the session's final bar, the session
   close OR the nominal next hour (start+60m) — the two conventions
   in evidence in this chain (the constructor's own derivation caps
   at the close; every prior fixture and the vendor's nominal-hour
   stamps use start+60m). v2 consumed stated ends for the shadow
   without validating them. A truncated end, an end stretched past
   the nominal hour, or an off-grid end refuses. Named case proven:
   the **truncated 3-of-4 bin** — the 12:30 bar absent, the 11:30
   bar's end stretched to the 13:30 bin end claiming completeness —
   is refused by the exactness assert directly and by the wrapper.
   DISCLOSED CONVENTION POINT for adjudication: tightening the
   final-bar set to the close only is a one-line change; v3 admits
   both conventions rather than silently invalidating every frame
   the chain has ever fixtured.
3. **CALENDAR_BINDING** (`CONSTRUCTOR_GUARD_CALENDAR_BINDING`) —
   `calendar_sha256(session_closes)` canonical hash of the session
   table (sorted `YYYY-MM-DD|<close, UTC ISO>` lines, LF-joined,
   sha256). When the caller supplies `expected_calendar_sha256`,
   the guard recomputes and refuses on mismatch before
   construction. The session table is the guard's ground truth for
   exact-index and interval-end derivation; v2 accepted it
   unbound. The argument is optional in the candidate so the
   v2/-91 call contract is not silently broken; the G3-v3 adoption
   pin is expected to make it mandatory at the route level
   (Mike-only ruling, §7).

Version discipline (Claude's pin-minting condition): GUARD_VERSION
is bumped to the unique `guard-v3-candidate-1` — the -91 repair
deliberately did not bump, and Claude's HOLD named that. The -89
v2 suite's single version-anchor assertion belongs to the v2 pin;
against the v3 module that suite reads 14/15 with exactly that one
divergence, and every behavioral check passes (§6).

Also on the record from the v3 build: the pinned constructor's own
derivation path (no `interval_end` column) imports `validate_input`,
which the fixture copy does not carry — a column-less frame cannot
be constructed by the fixture copy at all. That is why every chain
fixture supplies explicit interval_end, and why the v3 exactness
step is a no-op (not a refusal) when the column is absent.

## §2 — Checker v3 (`checker/tsla_completeness_check.py`, CHECKER_VERSION `checker-v3-candidate-1`)

Base: the -91 repaired v2 candidate, byte-copied, then extended.
All v1/v2 lane semantics are preserved on inputs the new lanes do
not touch (proven: the -89 v2 suite passes 38/38 against the v3
module, the -91 repair suite 11/11, and the -82 v1 floor reads the
identical 10/14 — same four checks, the -82 fixture's own embedded
step documented in -89 — against both the pristine v2 module and
v3; §6). V3 adds:

1. **STRUCTURAL lane** (runs first; defects fail completeness):
   - `DUPLICATE_TIMESTAMP` — v2's set-based COUNT collapsed
     duplicate stamps silently; a doubled bar was invisible.
   - `TZ_NAIVE` / `TZ_NOT_SESSION_ZONE` (equity mode) — v2
     reconciled a UTC-stamped frame against NY expected starts and
     reported COUNT chaos instead of the named basis defect.
   - `ORDER_VIOLATION` — v2's set logic hid order entirely, while
     STEP's first/last-bar reads silently used file order.
2. **Invalid-OHLC defect classes** (ANOMALY lane):
   `ZERO_OR_NEGATIVE_PRICE` (any of O/H/L/C ≤ 0), `HIGH_LT_LOW`,
   `PRICE_OUT_OF_RANGE` (Open or Close outside [Low, High]).
   DISCLOSED TIGHTENING: an all-zero flat bar was NO_TRADE_FLAT in
   v2; in v3 it is a ZERO_OR_NEGATIVE_PRICE defect — a 0.00 print
   is not a trade price.
3. **NaN at a split boundary → UNTESTABLE** — a NaN first-open or
   last-close at a declared boundary classifies the boundary
   `UNTESTABLE_NAN_BOUNDARY` (v2 silently fell through to
   PRICE_ACTION); a NaN feeding a STEP-ALL boundary step is
   likewise recorded, not skipped. All untestable boundaries are
   enumerated in the top-level `untestable` list; a declared
   boundary outside the span joins it (`BOUNDARY_OUTSIDE_SPAN`).
   If nothing else fails, the overall verdict is **UNTESTABLE**
   (new v3 overall value, disclosed). The NaN bar itself remains a
   NAN_VALUE completeness defect — both facts are reported;
   neither hides the other.
4. **Crypto instrument mode** — `run_check(..., instrument="crypto")`
   implements the adopted S-C1…S-C6 calendar as a checker
   instrument: a session is one ET calendar date, every table date
   a session, expected bars the 24 hourly starts 00:00…23:00 ET;
   bars are attributed to ET dates whatever their stamp zone (any
   tz-aware stamp accepted; naive refuses structurally). A missing
   hour is a COUNT finding naming the ET stamp; a missing date is a
   -91 missing-session finding with 24 expected starts. Declared
   splits in crypto mode are a fail-closed caller error
   (`CRYPTO_DECLARED_SPLITS_NOT_APPLICABLE`). STEP-ALL / VBASIS
   still scan date boundaries — a factor-shaped step in a 24/7
   series is the same defect signature as in equities.
   DISCLOSED CONVENTION POINTS for adjudication: (i) on the
   fall-back date the repeated wall hour surfaces as a
   DUPLICATE_TIMESTAMP structural defect rather than being absorbed
   — the candidate takes the fail-closed side; (ii) on the
   spring-forward date the absent wall hour is a COUNT missing-bar
   finding. Both follow from the 24-wall-starts convention and are
   stated here so adjudication can rule on them explicitly (the
   crypto pilot implementation ruling, §7).

## §3 — R1–R5 amendment draft (text only; adoption is Mike's G2-ext GO on the amended text)

Amends the -88 freeze text (`R1R5_FREEZE_TEXT.md` at `6b0f5d0`)
by reference. The -88 text is not edited. Each clause is DRAFT.

- **AM-1 — Missing-session admission reachability** (amends §0(b),
  §7). A data-absent session can enter a frame by exactly one
  path: R5 re-materialization from corrected qualified bytes,
  producing a new frame pin and a new readout that supersedes.
  There is no admission path into an existing frame pin, however
  the absence is later explained; a session absent at frame freeze
  is absent for that pin permanently. (Reachability is enforced in
  code by the guard's exact-index step: the frame's session set is
  a function of its pinned session table, and by checker -91's
  missing-session findings, which name absences rather than
  absorbing them.)
- **AM-2 — Orphan window-spans-gap accounting** (amends §4, §5(d)).
  §4 records window-spans-gap for windows feeding a position's
  entry signal. Windows that span an absent session but feed no
  position (orphan windows) are counted in the readout's
  data-quality annex — count only, dates enumerated — and never
  enter the GAP_DOMINATED tripwire's numerator or denominator.
  The tripwire stays position-based exactly as frozen; orphan
  counts can neither dilute nor inflate it.
- **AM-3 — Missing-bin granularity; crypto granularity** (amends
  §0(b)). Equity: a session is admitted to a frame all-or-nothing —
  a single missing 4H bin's worth of 1H constituents (a partial
  session) makes the session absent for the frame, enforced by
  the guard's exact-index step; there is no partial-session frame
  state. Crypto: the capture/checking unit is the 1H bar under
  S-C1; a missing hour is a missing bar, a missing ET date is an
  absent session; 4H bins are derived at construction, never
  capture or qualification units.
- **AM-4 — Stale next-present-open fills** (amends §2). A fill
  deferred under §2 carries a `STALE_FILL` flag with the deferral
  length in sessions on the trade record, and every readout
  reports its stale-fill count and maximum deferral alongside the
  §5 subsets. No staleness cap is imposed by this amendment: a cap
  would change fill semantics (a strategy change, new family),
  and is explicitly not smuggled in as a clarification.
- **AM-5 — Cross-calendar portfolio scope** (amends §5(c)). No
  pooled portfolio metric may mix the XNYS calendar and the crypto
  continuous calendar without per-calendar subset accounting in
  the §5(c) form. Session counts are never compared or summed
  across calendars: 751 XNYS sessions and continuous ET dates are
  unlike units, and any readout that places them in one
  denominator is mislabeled by construction.
- **AM-6 — C1 source evidence** (annex to the freeze text). Each
  rule's evidence class is stated in an annex table: A1 (no
  max-hold) VERIFIED from C1 source in -86; R1/R2 fill and
  hold-counting semantics code-fact, to be pinned to the C1 source
  hash at freeze; any rule whose basis is testimonial rather than
  source-pinned is labeled TESTIMONIAL in the annex — the freeze
  may still adopt it, but never under a source-verified label it
  has not earned.

## §5 — CH-1: archive byte verification + supersession note

Claude's CH-1 PASS was conditional on (i) archive PDF bytes
verification and (ii) a supersession note. Both are discharged
here, by verification, not assertion:

(i) Fresh clone of `qf-data-archive` (HEAD `6de1517`, descendant
of the -90 commits `f47823b` + `4f6d470`), 2026-10-22: the three
PDFs under `captures/ch1_core_hours_evidence_20261021_90/` hash to
exactly the -90 EVIDENCE.md pins —
`NYSE_2023_Annual_Guidance_Letter.pdf` 81a16c40…,
`NYSE_RB-23-043.pdf` 7d94f9c7…, `NYSE_RB-23-116.pdf` e1dec911… —
and `sha256sum -c` passes on both SHA256SUMS (7/7) and
SHA256SUMS_ADDENDUM (4/4). CH-1's evidentiary basis is byte-exact
in the archive of record.

(ii) SUPERSESSION NOTE (proposed for the record): the -87
three-gate packet's Gate-1 text and the freeze record `a126ce5`
carry 2023 core hours as "disclosed assumption CH-1". That
assumption is superseded by the -90 evidence package (`b30ea93`)
as byte-verified above: for the 2023 segment, core hours
09:30–16:00 ET are evidenced fact (NYSE Rule 7.34 language in
RB-23-043 and RB-23-116, the latter dated inside the segment),
not assumption. No calendar bytes move; the 751-session union is
unchanged. The freeze record itself is not edited — this note,
on adjudication, is the supersession instrument, cited by
reference wherever CH-1 is mentioned.

## §6 — Test evidence (summary; full record in TEST_EVIDENCE.md)

Environment: pinned venv CPython 3.12.3 / pandas 2.2.3, offline
under `unshare -n`, synthetic fixtures only.

- Regressions vs pristine prior modules (extracted from their
  commits): -84 floor 12/12; -89 guard 15/15; -89 checker 38/38
  (its embedded -82 v1 floor: 10/14, the documented -82 fixture
  divergence); -91 checker repair 11/11; -91 guard sabotage 8/8.
- New v3 suites: guard 16/16; checker 20/20.
- Compatibility (prior suites vs the v3 modules): guard floor
  12/12, sabotage 8/8, v2 suite 14/15 (sole divergence: the
  version-anchor assertion, by design); checker v2 suite 38/38,
  -91 repair 11/11, v1 floor identical 10/14 with the identical
  four checks — zero new divergence.

## §7 — What remains HOLD / Mike-only rulings

See ADOPTION_NOTES.md. Nothing in this package is adopted,
authorized, or executed beyond offline synthetic tests.
