# S2 NECESSITY SOURCE AUDIT — task -62 r1

Task: QF-TD-S2-NECESSITY-SOURCE-AUDIT-20261020-62 r1
Spec: Issue #1 comment 6307019635 (GO for one read-only source audit,
≤35 min; decide whether REQ-S2 split exclusion has a DEMONSTRATED
data-quality purpose before any -61 shim rerun).
Governing frame (Mike, 2026-10-20): the decision is demonstrated
data-quality purpose — NOT improvement of historical returns.
Binding corrections: (a) price-gap/volume patterns are anomaly screens,
not authoritative reconciliation; (b) a later /last_change timestamp
does not prove earlier bars invalid — version/consistency evidence is
required; (c) NO inference from Yahoo defects to Twelve Data's feed.
Method: ONE read-only pass over pinned files/commits. No code
modified, no tests executed, no vendor/API calls beyond the spec
fetch, no spend, no holdouts, no performance. The -61 HOLD
(8434fce / 70ee384) is preserved exactly as recorded.

## Terminal verdict (verbatim)

HOLD

S2 has NO demonstrated data-quality purpose on the current pinned
record — and the record equally fails to demonstrate it is
unnecessary. Detail in §5.

## 1. Acquisition path (what is actually pulled, and what receipts prove)

- Frozen manifest `TD-PILOT-MANIFEST-R3-20261010`
  (`research_notes/pilot_harness/request_manifest.json`, sha256
  a0a001b7458993ff…): 91 base requests, every request pinned
  `adjust="splits"`, `outputsize=5000`, interval 1h, windows
  2026-04-01 → 2026-10-06. A ~6-month 1H window is ~900 bars — a
  SINGLE pull per symbol; pagination does not trigger at this size.
- Pagination is nevertheless a designed path (`pilot_acquire.py`,
  sha256 acf39bbd98f717…, `_pag_trigger` L566–600): if a response has
  exactly 5000 rows AND its earliest bar is after the requested start,
  up to 2 extra pages are fetched BACKWARD in time (next page ends at
  the previous page's earliest bar). Longer history windows (the V2
  screen manifest spans 2022-03-07 → 2026-08-24 per
  HISTORICAL_DATA_MINIMUM_ACTION_PACKET_20261016) exceed 5000 1H bars
  and WOULD assemble one series from up to 3 separately fetched pages.
  If a vendor recomputed split adjustments between page fetches, the
  pages could in principle carry different adjustment bases at the
  seams. This is a MECHANISM, not an observed instance: no page set
  has ever been acquired (see §4), so no seam has ever been observed.
- Receipts (`pilot_acquire.py` L40, L382–390, L409–410): each response
  is stored with UTC-ms timestamps, byte count, SHA-256 of the exact
  response body, and sanitized params (including `adjust`). Receipts
  therefore prove WHAT bytes were served, WHEN, under WHICH
  parameters. They do NOT prove the vendor's adjustment arithmetic
  is correct — a receipt contains no independent reference.
- Revision machinery exists by design and has never run: the manifest
  carries REV7 / REV30 legs that re-pull identical windows at +7/+30
  days with revision-to-base linkage (`pilot_acquire.py` header L22;
  leg field L130). These are the program's own version/consistency
  instrument for detecting vendor-side rewrites.

## 2. Frozen strategy dependencies (what a split problem would actually touch)

Pinned modules (adopted inert onto main by -23; hashes as in the -60
DAG): `pine_signal_quality.py` b1b39ee8d0bd…, `pine_ranking.py`
77afae0df120…, `pine_exposure.py` 9f646161c27f….

- VOLUME is a hard dependency: `pine_signal_quality.py` L204–205 —
  a symbol with no Volume column (or all-NaN volume) is SKIPPED.
- Ranking: `pine_ranking.py` supports schemes 'rs' | 'vol' |
  'composite' | 'takeall' (L140); the 'vol' feature is relative
  volume (L108–110) and feeds pct-rank scoring in 'vol'/'composite'
  (L165–168). The recorded adopted overlay is rs_top2 (20-bar return
  minus SPY, top-2 at contested timestamps) — return-based — but the
  volume dependency above stands regardless of ranking scheme.
- PRICE/ATR: stops and targets are ATR constructions on Close —
  stop = Close − ATR·SL_ATR (L112), TP1 = entry + ATR·TP_ATR (L119),
  trailing runner stop (L132); quality gates use atr_ratio (L88–89)
  and a tight-base range test (L92–95). R accounting is ratio-based
  (L149, L170).
- Consequence, stated precisely: every one of these constructions is
  INVARIANT under a UNIFORM split adjustment (prices and, per vendor
  convention, volumes scaled consistently). What corrupts them is a
  MIXED-basis series — e.g., pre-split bars on one basis and
  post-split bars on another inside one series — which manufactures
  false ATR spikes, false relative-volume spikes, and false range
  breaks at the seam. The strategy therefore needs protection from
  an INCONSISTENTLY adjusted series, not from splits as such. S2's
  blanket D−1/D/D+1 exclusion is a blunt mitigation aimed at exactly
  that seam risk; it also removes perfectly valid sessions whenever
  the vendor's adjustment is in fact consistent.

## 3. Gate-7 July-3 truth (both authoritative sources, cited)

- Gate source: `dispatch_gate_r4.py` (sha256 b53996454650…,
  research_notes/td_policy_a_live_readiness_packet_20261017_11/)
  Gate 7, L584–607: the gate RE-DERIVES the calendar in the pinned
  environment and requires `closed_2026_07_03 is True` and
  `closed_2026_07_02 is False`, where the derivation is
  `xnys_schedule(pd.Timestamp('2026-07-03')) is None` (L212). The
  pinned proof record must carry `closed: True`, `date: "2026-07-03"`,
  PMC 4.5.1. The word "early" appears ZERO times in this file; the
  gate has NO early-close predicate for 2026-07-03. It asserts
  CLOSED (non-session).
- Pinned artifact: `XNYS_SESSION_SCHEDULE_V2.json` (sha256
  3358f2d9cc233142…, -35 r2 qualified) contains NO 2026-07-03 session
  at all (sessions run 2026-07-02 close 16:00 → 2026-07-06). It also
  asserts NON-SESSION.
- Plain statement: the two authoritative sources AGREE — 2026-07-03
  is a closed/non-session day (Independence Day observed). No pinned
  source asserts an early close for 2026-07-03. The "early-close"
  phrasing exists only as a downstream reporting label (Gate-7 spot
  summaries in the -56/-61 lineage), not as a source fact. One real
  divergence remains, of a different kind: Gate 7 derives from LIVE
  PMC at runtime while the qualification artifact is pinned — two
  calendar authorities whose agreement here is incidental, not
  pinned (the E5 point from -60).

## 4. Existing evidence of Twelve Data split contamination

NONE EXISTS in the pinned record. Specifically:

- No Twelve Data bar data spanning a split window has ever been
  acquired in this program. The only live TD call in the record is
  the -18 `/api_usage` check (1 credit); the -16 live attempt
  transmitted zero requests. The designed adjustment probes — ADJ
  legs over the NVDA 10:1 window (split-adjusted trading from
  2024-06-10) and the TSLA 3:1 window (from 2022-08-25) in
  `TD_ACQUISITION_ADAPTER_PREFLIGHT_20261013.md` (sha256
  a5beb9ab9807…), L43, L253–256 — were never executed.
- S2's own lineage is precautionary, not evidentiary. At contract
  consolidation (-21, `VALIDATION_CONTRACT_CONSOLIDATION_20261018_21.md`
  sha256 92ea4a999479…, L92–94) split handling was marked PROSE_ONLY,
  inherited from the Yahoo-era preregistration (Yahoo 1H
  `auto_adjust=False` — UNADJUSTED prices, where a split is a real
  price discontinuity; cf. CORRECTED_BASELINE_DATA_READINESS_MAP_
  20261015.md sha256 980c372dc79f…). Amendment v1 (-24,
  VALIDATION_GOVERNANCE_CLOSURE_20261018_24.md §2) then froze S2 as —
  in its own words — "a governance constant fixed here, before any
  data pull or performance computation… not derived from, or tuned
  on, any result or dataset," replacing a LOST original protocol.
- The same Amendment v1 already contains the sharper instrument:
  S4 requires the documented adjustment convention to be VERIFIED
  with deterministic pre/post price-ratio checks and OHLC-consistency
  checks across each split, with DATA_UNQUALIFIED on failure (S5).
  S4 has never been executed against Twelve Data bytes. The standing
  feed-eval spec said the same earlier (DATA_FEED_SAMPLE_EVAL_SPEC_
  20261006.md sha256 1650d964cd2d…, [A4] L208–212): document the
  vendor's corporate-action handling; "Do not assume the Yahoo
  contract."
- Per Mike's binding corrections, nothing in the Yahoo record
  (defective grids, contamination) is evidence about Twelve Data,
  and no anomaly screen (gaps, volume patterns) could substitute for
  the S4-style verification in either direction.

## 5. Verdict reasoning

- KEEP S2 would assert a demonstrated purpose. There is none: zero
  contamination instances, zero acquired split-window bytes, and a
  rule whose own freeze record describes it as an untuned governance
  constant inherited from an unadjusted-data context that does not
  describe Twelve Data's adjust='splits' feed.
- REPLACE (retire or narrow S2 now) would assert demonstrated
  non-purpose. That is equally unproven: the feed's split behavior
  has never been observed, the strategy is mechanically sensitive
  to adjustment inconsistency (§2), and a theoretical basis-mixing
  seam exists in chunked acquisition (§1) that receipts make
  detectable but nobody has ever checked.
- Therefore HOLD — with the qualification path below. S2 remains
  frozen in the contract meanwhile (this audit changes nothing),
  and no -61 shim rerun should be spent until the purpose question
  is answered: if S2 falls, the shim is moot; if S2 stands, it stands
  on evidence.

## 6. Shortest qualification path (in order)

1. $0 desk step (no vendor call): document Twelve Data's
  corporate-action convention from vendor documentation — ex-date
  vs pay-date basis, whether splits scale volume under
  adjust='splits', and revision/rewrite behavior. This satisfies
  S1's "documented convention" leg and the eval spec's [A4].
2. Gated vendor step (requires Mike's authorization — NOT given;
  no calls made here): execute the already-designed ADJ probe legs
  (NVDA Jun-2024 and TSLA Aug-2022 split windows) plus the manifest's
  REV7/REV30 revision legs, then run Amendment v1's S4 checks on the
  returned bytes — deterministic pre/post price-ratio and
  OHLC-consistency checks across each split, adjust='splits' vs
  adjust='none' over identical windows, all byte-pinned by the
  existing receipt machinery. This is version/consistency evidence,
  the only kind Mike's corrections accept.
3. Decide on that evidence: demonstrated inconsistency → KEEP S2
  (and finish the -60 E1–E5 gates). Demonstrated consistency →
  REPLACE S2 for Twelve-Data-adjusted datasets via contract
  amendment (retire it, or narrow it to a seam-only guard at
  pagination boundaries).

## 7. Explicit unknowns

- U1: Twelve Data's actual adjustment behavior across a split
  effective date — never observed on acquired bytes.
- U2: Whether adjust='splits' scales volume, and by what convention
  — undocumented in the pinned record.
- U3: Whether Twelve Data retroactively rewrites previously served
  bars after a split becomes effective (revision behavior) — the
  REV legs designed to detect this have never run.
- U4: Whether pagination pages fetched minutes apart can carry
  different adjustment bases (depends on U3) — mechanism identified,
  no instance observed.
- U5: Which ranking scheme the eventual corrected run freezes
  (module supports rs/vol/composite; recorded adopted overlay is
  rs_top2) — determines how much the volume dependency weighs.
- U6: Whether any symbol in a future frozen acquisition window has
  an in-window split at all — unknowable until a real-data manifest
  and window are frozen.

## Timing / disclosures

Elapsed: spec fetch 2026-10-21T03:16:46Z → result commit verified
03:19:04Z ≈ 2 min on the host clock (≤35 budget); repair minutes 0;
one read-only pass; no deviations. This audit is
independent of Claude's CP1 review lane; the -61 HOLD and all other
standing HOLDs are untouched.
