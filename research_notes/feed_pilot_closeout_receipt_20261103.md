# Feed Pilot Closeout Receipt — Twelve Data Five-Symbol Feed-Measurement Pilot

Task: QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22 (Lane C closeout, derived-only)
Symbols: NVDA, TSLA, AAPL, SPY, MELI · Sessions: 2026-10-26 → 2026-10-30
Built: 2026-11-03, from preserved local state ONLY. No vendor calls, no new captures,
no backfill of Oct 26, no code modified (stage adapter code examined read-only; nothing changed).

## Final result (as posted 2026-11-02, re-verified against preserved state)

| Item | Value | Preserved source |
|---|---|---|
| Coverage | 140 / 175 bars (35 missing, all 2026-10-26) | work/finalize_result.json `coverage` |
| Mon Oct 26 | Lost entirely — 148/148 actions missed_late under tripwire_hold; 0 bars | finalize_result `sessions.2026-10-26`; pilot_state actions |
| Thu Oct 29 | Incomplete — 15 missed_late ladder actions = the entire 12:30 ET bar ladder (5 symbols × offsets 60/180/420 s); bars themselves later received | pilot_state actions (session 2026-10-29) |
| Latency | LATENCY_UNMEASURED (label as recorded; the finalize census exists but the verdict label stands) | finalize_result `latency_label` |
| Adapter parity | ADAPTER_PARITY_FAIL — 5 mismatches, one per symbol | finalize_result `adapter_parity`; parity_diagnostics.json |
| Desk calls | 288 total (Oct 27: 64, Oct 28: 74, Oct 29: 69, Oct 30: 74, Nov 2: 7); caps 149/day, 800 total — no breach | finalize_result `credits` |
| Result posting | package 4f975b9, bridge b605064, manifest_verified_from_remote = true | state/result_posted.json |

## 1. Adapter-parity mismatch cause matrix

How the check works (finalize_pilot.py `adapter_parity`, preserved): the STREAM side replays
every ladder/finalization/revision payload row, in journal order, through the pinned −17
observer; the BATCH side feeds each bar's final `last_values` from runner state. Frames are
compared exactly, column by column (Open, High, Low, Close, Volume, SessionVWAP), and the
comparison stops at the first differing column per symbol.

Structural facts proven from the preserved replay journals (work/parity/):
- Stream journal: 1,210 INPUT records, **1,070 REJECTED records — every one class DUPLICATE,
  "stamp already processed"** — plus 40 BAR and 20 SESSION_COMPLETE records.
- Batch journal: 140 INPUT, 0 rejected, 40 BAR, 20 SESSION_COMPLETE.
- Bar index/count parity HELD for all five symbols (no `bar_index_or_count` mismatch);
  candidate sets identical (0 vs 0). The independent plain-pandas aggregation cross-check
  against the batch frame produced no mismatch.
- The pinned observer is first-wins by specification: bundle/observer/fwd_observer17.py
  rejects any row for an already-processed (date, hhmm) stamp ("stamp already processed")
  and rejects bars for already-finalized sessions as LATE_BAR (no backfill). Its frames
  therefore hold FIRST-SEEN (as-of, decision-time) values and cannot absorb later revisions.

Per-symbol matrix — earliest divergent bar is **2026-10-27 09:30 ET for all five symbols**
(the first bar present on both sides; all Oct 26 bars are absent from both). Values below are
the runner state's own preserved pair: `first_seen` (ladder +60 s snapshot) vs `last_values`
(after the next-day revision pull), pilot_state.json `bars`:

| Symbol | Open as-of → final | Other fields as-of → final (09:30 bar) | Bars revised | Revision events | Classification |
|---|---|---|---|---|---|
| AAPL | 343.165 → 343.16501 | H 345.09 → 345.10001; L 342.4 → 342.39001; V 208,825 → 5,578,507 | 28/28 | 32 | EXPECTED REVISION |
| MELI | 1706.465 → 1706.46497 | C 1706.3 → 1706.050049; H 1728.025 → 1728.47192; L 1672.1 → 1672; V 11,779 → 281,387 | 28/28 | 40 | EXPECTED REVISION |
| NVDA | 218.29 → 218.35001 | C 217.12 → 217.12000; H 218.49 → 218.49001; L 215.535 → 215.53000; V 700,855 → 81,295,861 | 28/28 | 32 | EXPECTED REVISION |
| SPY | 767.42 → 767.34003 | C 766.62 → 766.63000; H 768.3 → 768.35999; V 145,407 → 9,572,194 | 28/28 | 32 | EXPECTED REVISION |
| TSLA | 397.76 → 397.79999 | C 402.39 → 402.38000; L 395.325 → 395.25; V 267,706 → 17,375,415 | 28/28 | 32 | EXPECTED REVISION |

Dimension-by-dimension:
- **As-of vs final:** the mismatch IS the as-of/final difference. The vendor revised
  **140 of 140 received bars** (finalize `revisions.revised_bars` = 140; 168 revision events;
  field diffs: close 167, volume 168, open 139, high 132, low 128). First-mismatch values in
  parity_diagnostics.json match the state pairs above exactly for all five symbols.
- **Session alignment:** HELD. Identical bar indexes and counts on both sides (40 4H bars per
  replay: 4 sessions × 5 symbols × 2 bins); no alignment mismatch recorded.
- **Split-adjustment / normalization:** NO split or adjustment signature in preserved bytes.
  Revisions are idiosyncratic per field (e.g. MELI close fell while its high rose) with no
  uniform price ratio; volume revisions range ~24×–116× irregularly. The 5-decimal float
  artifacts in final values (218.35001, 343.16501) are present in the vendor's own revision-
  endpoint payload bytes (payloads/2026-10-27/00066_revision_NVDA.json carries
  `"open":"218.35001","volume":"81295861"`), while the ladder-endpoint payload bytes carry
  clean values (`"open":"218.29","volume":"700855"`, 00003_ladder_NVDA.json). The
  representation difference is the vendor's, between its two endpoints; no adapter arithmetic
  introduces it.
- **Chronology:** first-seen values were received at the +60 s ladder poll (e.g. NVDA 09:30
  bar receipt 2026-10-27T14:31:00Z); the revising values arrived in the next-day revision
  pull (receipt 2026-10-28T12:00:00Z, action rev|2026-10-27|NVDA, from_hash → to_hash
  recorded in state). The stream replay's 1,070 DUPLICATE rejections are the preserved trace
  of every later snapshot/revision row being refused by the first-wins observer.
- **Earliest divergent bar:** 2026-10-27 09:30 ET, column Open, for every symbol
  (parity_diagnostics.json; finalize `first_mismatch` = AAPL at that bar).

**Verdict on cause: 5 of 5 mismatches are EXPECTED REVISION. 0 of 5 are a proven adapter bug.**
The parity FAIL is the mechanical consequence of comparing a first-wins as-of frame against
final revised values under universal (140/140) vendor revision. The finalize protocol itself
recorded this coexistence: verdict ADAPTER_PARITY_FAIL with revision_behavior_subcase
MEASURED and revision_cases {revised: 140, late: 0, missing: 35}.

NOT MEASURED from preserved outputs: per-symbol differences in columns after Open
(the finalize comparison stops at the first differing column per symbol), including
SessionVWAP. The OHLCV state pairs above show the revision touched nearly every field of
nearly every bar, but the observer-frame cells beyond Open were never enumerated in any
preserved output.

## 2. Bug / fix disposition

No adapter bug is proven, so no fix is warranted to the observer or the adapter. The pinned
observer behaved exactly as specified (first-wins, no backfill, duplicates rejected).

If the program wants a parity gate that can distinguish adapter error from vendor revision in
a future run, the minimal isolated change is on the MEASUREMENT side only (describe-only;
nothing changed by this receipt):
- Build the batch-side frame from each bar's `first_seen` values instead of `last_values`
  (as-of vs as-of). Any remaining mismatch then isolates adapter/observer nondeterminism,
  and revision magnitude is reported separately from the state revision census.
- Synthetic regressions that would prove it: (a) replay the same preserved journal twice →
  frame fingerprints must be identical (determinism); (b) a fixture journal containing a
  known post-first revision of one bar → observer frame must keep the first values and log
  a DUPLICATE rejection (spec conformance); (c) a fixture with float-artifact strings
  ("218.35001") fed on BOTH sides → frames must match exactly (representation is pass-through).
- Frozen-strategy separation: every code path exercised by the parity check lives inside the
  stage bundle (bundle/observer/fwd_observer17.py + a pinned bundle copy of the engine) and
  the stage's own finalize_pilot.py. No production or frozen strategy file was an input to,
  or modified by, this closeout; this receipt changed no code anywhere.

## 3. Oct 30 tripwire / archive-push / daemon-restart evidence

- **Tripwire (Oct 30): PROVEN from preserved state.** pilot_state.json `tripwire.checks`
  records the 2026-10-30 check at 2026-10-30T13:15:00.000148Z, candidates [1a174da9074a6edf],
  outcome **clean**; state/heartbeat.json repeats the same last-check record. (The only filed
  tripwire item all week was the Oct 26 TD staff reply; Oct 27–30 checks were all clean.)
- **Archive push (Oct 30 session): PROVEN from the clone's refs.** Archive clone history:
  5bab217 (Oct 27) → a941476 (Oct 28) → a1d1ae3 (Oct 29) → **3a5c9a8 (Oct 30 session capture,
  2026-10-30T20:40Z)** → 7e0035f (Nov 2). In the clone as preserved, origin/main (f7db178)
  has 3a5c9a8 as an ancestor — the Oct 30 capture is on the remote line.
- **Daemon restarts (Oct 30): PROVEN as events; cause UNVERIFIABLE.** state/daemon.lock is an
  append-only start log (65 pid lines); Oct 30 alone has 9 pid starts (03:55, 05:55, 07:55,
  12:55, 15:25, 17:25, 19:25, 21:26, 23:27 UTC). The watchdog state file records, in its own
  notes, an overnight death followed by a restart in time for the 13:15Z tripwire (08:55 ET
  backstop note) and a further explicit "Daemon restarted per step 1; fresh heartbeat
  confirmed, desk_calls unchanged at 245 (no repeated actions)" during the Oct 30 session.
  **Why the daemon kept dying is not in any preserved artifact** (logs/daemon.out contains
  only "already_running" notices and the final complete line) — cause UNVERIFIABLE, and no
  cause is asserted here. The same applies to the Oct 29 outage: its EFFECT is proven
  (15 missed 12:30-ladder actions; Oct 29 latency max ≈ 1,807 s), its cause is not.

## 4. Archive gap — status (report only; nothing pushed, rebased, or forced)

- Exactly ONE unpushed commit in the archive clone: **7e0035f** (2026-11-02T13:10:00Z,
  "capture: … append-only journal+payloads (in progress)" — the final revision/usage
  payloads, 8 files per the watchdog record). `git log origin/main..HEAD` in the clone
  returns only 7e0035f; merge-base(HEAD, origin/main) = 3a5c9a8.
- The push failed because the R7 lane's commit f7db178 (2026-11-02T01:58Z) landed on
  origin/main first, leaving 7e0035f divergent. state/last_push.json preserves the failed
  attempt: 2026-11-02T13:10:02Z, ok = false, commit_rc = 0, push_rc = 1.
- Clone working tree additionally shows one untracked file
  (captures/td_feed_measure_pilot_20261026/parity_diagnostics.json — the finalize parity
  diagnostics sink; a byte copy was used for §1).
- Disposition: UNCHANGED by this receipt. Closing it needs a runner-discipline retry/rebase
  by the owning lane; it is not hand-pushed here.

## 5. Closeout recommendation

**Do NOT qualify the feed on this pilot, and do not call it a five-day result.** The record is:
one session lost in full (Oct 26), one session's ladder incomplete (Oct 29), latency
UNMEASURED as labeled, and a parity FAIL that this receipt attributes to universal vendor
revision against a first-wins observer — i.e., the pilot measured that Twelve Data Basic
revises every 1h bar after first publication (by up to ~116× on volume at the 09:30 bar),
which the current parity construction cannot pass by design.

Recommendation: **new prospective day(s) are required** for any feed qualification, run under
a corrected measurement construction (as-of vs as-of parity per §2, with revision magnitude
reported as its own metric), and with the daemon-reliability problem (65 starts in 8 days;
repeated silent deaths) treated as a first-order input, not a footnote. The four observed
days qualify only as a measurement of revision behavior and operational fragility — that
finding stands on preserved bytes and needs no rerun. Whether to spend those prospective
days is the feed verdict owner's call, not this receipt's.

## UNVERIFIABLE list (facts not provable from preserved state — labeled, never reconstructed)

1. The cause of the daemon's repeated deaths (Oct 26 – Nov 2). No crash trace exists in
   preserved artifacts.
2. Per-symbol observer-frame differences in columns after Open, including SessionVWAP —
   the finalize comparison stops at the first differing column; no preserved output
   enumerates the rest.
3. Which of the vendor's two value sets (ladder-time as-of vs next-day revised) matches the
   official exchange record. Preserved state proves the vendor revised its own output;
   no independent source exists in preserved state to grade either set.
4. The exact wall-clock instant of the Oct 29 daemon death. Preserved state bounds its
   effect (12:30 ladder missed at all three offsets; session latency max ≈ 1,807 s) but
   does not timestamp the death itself.
5. Any Oct 26 intraday values whatsoever — no capture exists; the session is absent, not
   reconstructed.

## Manifest of preserved-state files used (SHA-256)

| File | SHA-256 |
|---|---|
| state/pilot_state.json | f634d5a743236f69858d149f3be7753cec558533ddeccd9abc326ec32524b16d |
| state/result_posted.json | ee097ba3f4fb042c6d48f37151a8f2397a0eb765dc42d44763d403fa57ad4bdf |
| state/last_push.json | c906dc6b5d5ea49b5b796fe4975dd848b7ce17ce1e20d7f90105c678311a79ce |
| state/heartbeat.json | 66a8cf9814aa737782155846849718a404a141cf734b4ef5bf2eeceeac348e9b |
| state/daemon.lock | 8f489ae580327d0696eab7181f7f4c06fc42d66abe946ab9cfeffb2d2661cfe3 |
| logs/daemon.out | ffdebf8df3b113b68d7cb3ed43224bb67662740a73f1b54b79662c3213e52860 |
| work/finalize_result.json | 59d67b2f542f72d515db31d7948b177e6605cf5d00a649cf2b75f8ec844e2687 |
| work/parity/journal_stream.jsonl | 6d1e56a4750676afab48e4c01488069ab9708124d2bd58989d04efa151764b18 |
| work/parity/journal_batch.jsonl | de751662ed93181b6b1480e4ba57f74979461bac8e101d020611868ab5ec1a47 |
| work/parity/anchors_stream.json | 08bccff6d2a66e47a0be890dce51897dce68c8edb226f921dc6d7d2c9276e602 |
| work/parity/anchors_batch.json | 53e0c04b23388bbecd664d59e96008bf9286960d4977a2d87bdc7a10a1e6a31c |
| archive_clone/captures/td_feed_measure_pilot_20261026/journal.jsonl | 8ccc6729ccb0e0946f2299d6388b4a5d93142b4bc56cbdb52f370476fddad868 |
| archive_clone/captures/td_feed_measure_pilot_20261026/parity_diagnostics.json | 78e61e01dc0a2b365ea88cb5068adcef95f34b4f9ee92b3f212f46059ebd4735 |
| archive_clone/…/payloads/2026-10-27/00003_ladder_NVDA.json | f078c152db5c3a2e848bf1128f5cd521bf0d0393624976032c60f999da954ae1 |
| archive_clone/…/payloads/2026-10-27/00066_revision_NVDA.json | cae2cc5f4382a5b4cfbf6e2bd9eb7132d3457fdb4436fe4cf07980dfbce24851 |
| bundle/observer/fwd_observer17.py | 929c1bc4cac34384ad0a8807a1006aaafc555f5b6cf548f5f030ef26110052c3 |
| finalize_pilot.py | f533bf56a7c13ebe3755adeaccf4918e9048e2d4a2fe593a53c56aa8331fa016 |
| run_manifest.json | 596e9e81c7b62a2370c4caa6df8ac9149657189a4684f419784ca4914f6922db |
| goals/quality-flow-research-bridge/hidden_files/td_pilot_watchdog_state.json | d3641df9f3498964d9c68b5f59e5b6009fac1623a6d3dd6feaad1d187754c8a6 |
