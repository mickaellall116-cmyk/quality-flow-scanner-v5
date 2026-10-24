# RESULT — QF-EQUITY43-S1-G4-VBASIS-DECISION-PACKET-20261024-20 r1

**Governed label: G4_HOLD.** (Full evidence: `PACKET.md`. This RESULT
is the packet's own report, not an independent PASS; G4/VBASIS remains
UNADOPTED and this packet changes no standing status.)

## Headline evidence (all re-derived from pinned bytes in this run)

- **Reproduction exact:** the VBASIS lane re-run on the 8 receipted
  pilot legs matches the -02 committed report on every compared field.
  SPY control fact proven from bytes: **44 (HO) / 94 (DEV)** standalone
  VBASIS flags, no declared basis event, STEP/STEP-ALL clean
  everywhere — the convention failure is volume-lane-only.
- **Negative tests 6/6:** completeness failure cannot become a
  convention failure (NT-1); the current lane flags a smooth +10%/session
  volume ramp 52 times (NT-2 fail-before) while R-B leaves it a note
  and R-C rejects it; price-lane independence (NT-3); sensitivity
  probe NT-4 (R-B structurally blind to a price-silent volume step —
  disclosed).
- **Rules compared (only the preregistered three; no returns used):**
  - R-A current fixed band — negative controls: 471 flags across 7
    legs; census: 5,751 flags, 43/43 legs blocked. Fails.
  - R-C event-free step-shape — negative controls: 167 breaks;
    census: 1,783 breaks, 43/43 legs blocked. Fails (market volume
    regime shifts are step-shaped).
  - R-B declared-action/STEP corroboration — negative controls: **0
    breaks**; positive controls NVDA ✓ / AVGO ✓ / **NFLX ✗** (prices
    CONTINUOUS_ADJUSTED but single-session volume note 0.405 →
    OTHER_VOLUME_STEP → basis mismatch under the preserved note
    lane); census: 6 corroborated breaks in 5 legs (AMD, APP, LUNR ×2,
    MRNA, SNOW), each a +35%…+85% overnight gap loosely matched to
    the 2.0 anchor — corroboration specificity not demonstrated.
    Separates the pilot controls but cannot cleanly qualify the
    captured bytes → does not meet the adoption bar.
- **Minimum missing evidence** (PACKET §6): a preregistered
  corroboration spec with demonstrated specificity; a multi-session
  declared-boundary volume note re-tested on NVDA/AVGO/NFLX; one
  verified true-positive VBASIS-class case (none exists in the
  pinned record).

## Pins and preservation

- Checker sha256 `4fdc31cbfc4b1a96baaabe775d883135cf64a4f7dc2606c7b679756da1e7d936`
  (checker-v3-candidate-2, byte-identical to -02/-94); session table
  sha256 `00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f`.
- Inputs: pilot store legs (per-leg sha256 in
  `evidence/reproduction.json`, each equal to the -02 committed
  source hash) + capture-store DEV legs (qf_td11_stage store; leg
  set = the 39 captured names + 4 pilot DEV names).
- Declared event table: NVDA/HO 2024-06-10 ×10 (as -02); AVGO/DEV
  2024-10-11 ×10; NFLX/DEV 2025-11-17 ×10. SMCI is not a control:
  its DEV leg was never captured and its HO body was not read.
- PAUSED production identical before/after: `PAUSE_NEW_ENTRIES`
  sha256 `3f4b7811a577cc989438edc568d40d739281f76bcfbb0d0f36b900b2ccaa3ea2`,
  `RESUME_NEW_ENTRIES` absent, harness
  `ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d`.
  -15..-19 packages untouched; holdout sealed and unread; SMCI/HO
  body unread.
- Offline only; 0 vendor calls; 0 credits; no performance computed;
  no production change; no S1/S2 activation; no T0; no adoption or
  waiver language beyond the governed label.
- Determinism: the full rules census was executed twice with
  identical totals (5,751 / 6 / 1,783).
