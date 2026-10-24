# RESULT — QF-EQUITY43-S1-G4-VBASIS-DECISION-PACKET-20261024-20 r2

**Governed label: G4_HOLD (retained).** Event-table correction only
(governing: Issue #1 comment 6384407724; full evidence: `PACKET.md`).
This RESULT is the packet's own report, not an independent PASS;
G4/VBASIS remains UNADOPTED and this packet changes no standing
status. The r1 package (`b1d3661`) is preserved untouched; its
positive-control conclusion is labeled **CONTROL_TABLE_INVALID**.

## The defect, owned

The false AVGO date was mine: r1's `DECLARED_SPLITS_DEV` carried
AVGO "2024-10-11 ×10", hand-entered with no issuer source. Broadcom's
own release puts split-adjusted trading at **2024-07-15** — outside
the DEV window — so r1's "NVDA + AVGO splits clean" was unsupported.

## What r2 did (all figures re-derived from the artifacts this run)

- **Source-attested event table** (first split-adjusted trading
  dates, primary issuer records quoted in PACKET §2 /
  `code/common.py::ATTESTED_EVENTS`): NVDA **2024-06-10** ×10
  (NVIDIA release, 2024-05-22); AVGO **2024-07-15** ×10 (Broadcom
  release, 2024-06-12, + company split FAQ); NFLX **2025-11-17** ×10
  (Netflix release, 2025-10-30; distribution after the 2025-11-14
  close — verified against the primary announcement).
- **AVGO excluded from the DEV controls entirely**; AVGO/HO bytes
  not read. **Corrected positive-control denominator: 2**
  (NVDA/HO, NFLX/DEV).
- **False-row impact, proven on identical bytes** (`evidence/impact.json`;
  the false-table run first reproduces r1's committed AVGO record on
  all 9 compared fields and r1's census totals exactly): AVGO/DEV's
  manufactured STEP record (CONTINUOUS_ADJUSTED 0.975287, PASS, no
  mismatch) and UNSCALED volume note (0.667136) disappear; R-A flags
  138 → 138, R-B breaks/notes 0/138 → 0/138, R-C breaks 35 → 35,
  R-C untestable 43 → 44; the 2024-10-11 boundary, unjudged under
  the false row, is judged under the corrected table and produces
  no flag and no break. **Census totals are identical to the unit**
  (R-A 5,751; R-B 6 breaks / 5 legs; R-C 1,783) — AVGO/DEV is the
  only changed leg, and only in its STEP/note records. The damage
  was to the control evidence: cleanly handled positive controls go
  from a claimed 2 of 3 to an actual **1 of 2**.
- **Fail-before/after + rejection tests 7/7**
  (`code/event_table_tests.py`): the false row manufactures the
  control (ET-1) and is itself rejected by the corrected machinery
  (ET-4); the attested-but-out-of-window AVGO event is rejected
  rather than silently used (ET-5); unattested events are rejected
  (ET-6); corrected controls validate (ET-7).
- **Recomputed R-A/R-B/R-C only** (no new rule, no threshold
  change), deterministic across two executions (both
  `evidence/rules_eval*.json` hash to `0d77c4b9…`): negative
  controls unchanged (R-A 471 flags, R-B 0 breaks, R-C 167 breaks
  across 7 legs); positive controls — NVDA/HO clean (CONTINUOUS_
  ADJUSTED 0.993671, note UNSCALED 1.307109, no mismatch), NFLX/DEV
  still fails the preserved note lane (note OTHER_VOLUME_STEP
  0.405241 → basis mismatch; prices CONTINUOUS_ADJUSTED 0.995681);
  census dispositions unchanged (R-A blocks 43/43; R-B 6
  corroborated breaks in 5 legs, the same six ordinary-gap
  boundaries; R-C blocks 43/43).
- **Label basis:** with the fabricated control removed, verified
  true-positive evidence is one clean control and zero verified
  VBASIS-class true positives; R-B's corroboration specificity
  failure stands; R-A/R-C fail the negative controls outright.
  Insufficient true-positive/specificity evidence → **G4_HOLD**
  retained, per the r1 governance. Label options were exactly
  ADOPTABLE_CANDIDATE or G4_HOLD; this packet adopts nothing.

## Pins and preservation

- Checker sha256 `4fdc31cbfc4b1a96baaabe775d883135cf64a4f7dc2606c7b679756da1e7d936`
  (byte-identical to r1/-02/-94, pin-verified); session table
  sha256 `00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f`.
- PAUSED production identical before/after: `PAUSE_NEW_ENTRIES`
  sha256 `3f4b7811a577cc989438edc568d40d739281f76bcfbb0d0f36b900b2ccaa3ea2`,
  `RESUME_NEW_ENTRIES` absent, harness
  `ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d`.
- r1 package, -15..-19 packages untouched; -19 r2 unchanged;
  holdout sealed and unread (AVGO/HO included); SMCI bodies unread.
- Offline only (sole network use: reading the three primary issuer
  records the governing comment requires the dates be pinned to);
  0 vendor calls; 0 credits; no performance computed; no production
  change; no S1/S2 activation; no T0; no trades; no adoption/waiver.
