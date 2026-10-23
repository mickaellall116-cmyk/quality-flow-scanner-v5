# LAUNCH READINESS — shadow signal-only observer (closeout v3 candidate)

**This task does not launch anything.** No shadow process is
running, no namespace exists in the production tree, no
scheduler entry was created, no authorization artifact was
created, no production file was touched, and no live cycle
has run. Fixture PASSes are evidence about synthetic data
only.

## Verdict

**CANDIDATE READY FOR ADJUDICATION — LAUNCH HOLD.** The
closeout items from ChatGPT's verdict on the repair (Issue
#1 comment 6356610693, items 3-4) are implemented and
fixture-proven (39/39): the launch manifest binds the full
pin set + digest, and admission is session-table-derived
for equity and S-C-continuous for crypto. The remaining
blockers are no longer code items in this candidate:

## Remaining launch blockers (precise, in order)

1. **Immutable corrected-grid 1h cohort bytes do not exist.**
   The sole external prerequisite named by the verdict:
   raw 1h frames for the 250 cohort are NOT_AVAILABLE
   offline (D1 destroyed; the harness persists no 1h frames;
   TD probe windows cover 3 symbols only and the NVDA window
   is holdout-overlapping / qualification-only — never to be
   used). Acquisition needs a separately authorized capture
   route (the -88 capture or an authorized Yahoo 1h capture);
   neither is authorized. Actual V5.4 output remains
   legacy/off-grid (cycle-759 rows 14:30->16:00) and cannot
   seed corrected prospective evidence; no relabeling.
2. **Actual-byte parity** against corrected-grid bytes
   (verdict: after capture) — the corrected producer +
   independent attestation do not exist yet.
3. **ChatGPT adjudication** of this closeout package.
4. **Mike's explicit launch GO** naming a specific
   prospective start instant (T0) — the future-T0 GO.
5. **Launch-day re-pin**: candidate commit (the manifest
   currently binds lineage commit 4130e74), module/stack/
   calendar pins re-verified against the then-current
   stack, the session table extended past its current
   2026-10-16 coverage to the launch window (equity dates
   beyond the table refuse NON_SESSION_DATE by design), and
   the authorization artifact's digest bound into the pin
   set (the slot is frozen, digest null, NOT_AUTHORIZED).
6. **LAUNCH_AUTHORIZED.json creation** in the shadow root
   as part of the GO (the runner refuses live mode without
   it, or with a mismatched T0).
7. **Live-route decision**: the candidate's LiveAdapter
   would add one market fetch + one 250-name Yahoo scan per
   cycle. The verdict's preferred route is passive reuse of
   ordinary-cycle output, which is legacy-grid until item 1
   lands; any live-adapter cadence needs its own agreement.
   No adapter was wired, scheduled, or run by this package.
8. **Supervised first cycle** + first-cycle artifact review
   (including recording the external chain anchor outside
   the log — the anchor is now enforced at startup when
   supplied, but the operational anchor-recording procedure
   is a launch-day act).

## Explicit non-claims

- Passing fixtures do not prove live deployability against
  the real Yahoo route (the live adapter has never run; it
  is constructed only behind the authorization gate).
- Stage 1 evidence can never support a trading-edge claim:
  signals without prospective fills and end-to-end parity
  are diagnostic observation only.
- The -80 package's lifecycle design is NOT revived by this
  candidate; hypothetical mode needs its own candidate and
  its own catch-up and crash-seam tests before activation.
