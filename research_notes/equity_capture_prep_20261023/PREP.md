# QF EQUITY-CAPTURE PREP — 2026-10-23 (PREPARED ONLY, EXECUTES NOTHING)

**Status: PREP.** This package prepares the equity data acquisition so
the 39-name Twelve Data capture can fire immediately when
QF-EQUITY-PIT-INTEGRITY-20261023-09 clears adjudication. It executes
nothing: **no vendor data calls, no captures, no credits spent
(program TD total stays 24), no account creation, no holdout access,
no performance runs, no production/frozen changes.** Prepared under
Mike's direct instruction (chat, 2026-10-23 ~16:26 ET) to prepare the
data-acquisition work in parallel with the -09 timing corrections,
following his standing sequence: fix the two look-ahead defects
(-09, running) → qualify the remaining equities → run the unchanged
strategy across the full eligible equity universe → independent
validation → only then evaluate the protected out-of-sample period.

**Single-dispatch check: CLEAR.** No existing equity-capture prep
package, stage, or commits, and no Alpaca screen, on origin/main at
ACK time (HEAD = -09 ACK bridge `f451339`, a separate lane, untouched
by this prep). ACK: Slack TS `1792787378.790559`; bridge `5bcfb38`.

## Contents

| File | What it is |
|---|---|
| `CAPTURE_MANIFEST.md` + `capture_manifest_equity39.json` | Equity-only capture manifest: 39 names × HO+DEV = **78 legs**, BLOCK-BRACKET-10 totals **87 expected / 173 worst** credits ($0 free tier, one execution day at either figure), pilot hash-chained receipt schema, -08 qualification gates G-1..G-7. Manifest root digest `ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64`. Every name: **NOT ACQUIRED / NOT QUALIFIED**. SMCI is a separately-flagged line, not a leg. |
| `ALPACA_SCREEN.md` | Second-source screen, documentation only. Verdict: **HOLD — LICENSE_NOT_AFFIRMATIVE (test a)**, same failure class as Kraken. Technical offering is strong (historical SIP without subscription when end ≥15 min old; 1h bars with volume; adjustment=split documented; history since 2016; 200 calls/min Basic). No Coinbase-type validation bar found (absent, not waived); no deletion-on-termination clause found. Cure path: Alpaca's written consent (the mechanism its own terms name), then re-screen. |
| `SMCI_RESOLUTION.md` | TD HO defect facts (19 price-moving zero-volume bars, 6 April-2024 dates, quarantined body sha256 `737cb24a…`, classified NOT_EVALUABLE_PROVIDER_VOLUME in -02) + a **NOT-EXECUTED** bounded Alpaca sample card (SMCI, April 2024 only) gated on (i) the Alpaca screen passing — **currently NOT passed** — and (ii) a separate GO. On-record fallbacks B1/B3 (and B2 for completeness) restated **without recommendation**. |
| `SEQUENCING.md` | Exactly what fires when -09 clears: capture GO naming the manifest root → capture (one phase, fail-closed) → per-name -08-style preflight → corrected full-universe run under the -09 research-only as-of corrections **once adopted** → independent validation → protected OOS evaluation last, separately gated. |
| `SHA256_MANIFEST.txt` | Package file hashes (verified from the pushed remote tree at RESULT). |

## Pins (BEFORE, verified at ACK; re-proved at RESULT)

- PAUSED production harness sha256
  `ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d`
  (`v54_forward_harness.py`); `forward_test/PAUSE_NEW_ENTRIES`
  present; `forward_test/RESUME_NEW_ENTRIES` absent.
- Pinned session table sha256
  `00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f`
  (`research_notes/shadow_closeout_20261022/session_table.json`,
  XNYS-751-UNION-20261021).
- Program Twelve Data credit total: **24** (unchanged by this prep).

— Muse
