# RESULT — QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22
## Twelve Data prospective 1h feed measurement pilot (Gate B B1+B2)

Authority: Mike GO, main chat 2026-10-24 10:36 ET, under the frozen -21
protocol (package c2b58d7). Symbols NVDA/TSLA/AAPL/SPY/MELI (MELI = lowest
median DEV daily volume, 328,352 over 524 sessions). Sessions
2026-10-26..2026-10-30. Measurement only: no S1 activation, no T0, no
trading. S1 PREP_READY / LAUNCH_HOLD and G4_HOLD unchanged.

## Verdicts
- Latency: **LATENCY_UNMEASURED** — pooled n=140, p50=63.782255s,
  p95=67.533074s, p99=1806.123753s, max=1807.787787s;
  first-seen-at-finalization=25.
- Coverage: 140/175 bars
  received; missing=35;
  late (first seen after finalization)=
  0.
- Revision census: 140 bars revised,
  168 events, fields {'high': 132, 'low': 128, 'open': 139, 'volume': 168, 'close': 167}.
- Adapter parity: **ADAPTER_PARITY_FAIL** (stream rows fed
  1210, batch rows 140,
  mismatches 5, first mismatch:
  {"symbol": "AAPL", "kind": "value", "column": "Open", "bar": "2026-10-27 09:30:00-04:00", "diagnostic_anchor": "4dbd2043aeefbf4f6348e0a1a87d5f35fde4cb20c0ed9acfc108580bcad81066"}; revision-behavior sub-case
  MEASURED).
- Credits: desk 288 calls total
  (by day {"2026-10-27": 64, "2026-10-28": 74, "2026-10-29": 69, "2026-10-30": 74, "2026-11-02": 7}); provider snapshots
  in credit_ledger.json. Caps 149/day, 800 total — held.
- Sessions: {"2026-10-26": false, "2026-10-27": false, "2026-10-28": true, "2026-10-29": false, "2026-10-30": true}
  (detail in sessions.json). Complete sessions:
  ["2026-10-28", "2026-10-30"]; slipped as documented review-wait:
  [].
- Stopped: null.
- Email tripwire: 5 pre-open checks; TD staff reply RECEIVED and filed as the governing source superseding the AI-assistant answers (message 1a174da9074a6edf, TD_SUPPORT_REPLY.json in this package).
- PAUSED re-proof at finalize: {"pause_new_entries_present": true, "resume_new_entries_present": false, "pause_sha256": "3f4b7811a577cc989438edc568d40d739281f76bcfbb0d0f36b900b2ccaa3ea2"}.

## Rights record
- Q1–Q3 (Twelve Data AI assistant, 2026-10-24; adjudication memo on the
  bridge): Basic permits internal non-display use for evaluation/
  development incl. internal processing/storage; private research/paper
  observation is non-commercial; storage during subscription, delete
  within 30 days after it ends (audit trail excepted).
- Q6 SETTLED (Dooz AI assistant follow-up, Mike screenshot 2026-10-24
  ~11:03 ET): private automated research on 1h data via /time_series
  permitted; raw storage internal while subscribed; AI processing —
  raw market data must remain in the private environment, sharing with
  third parties including external AI services (ChatGPT, Muse named)
  counts as REDISTRIBUTION on Basic. Confirmed model: raw data →
  private infrastructure; AI agents → only derived results that cannot
  be reverse-engineered to the original data. Standing consequence:
  on Basic, no workflow may feed raw Twelve Data bars to any hosted AI
  agent — derived aggregates/hashes only. This pilot complied as
  built (local deterministic capture/processing; this package is
  bar-free derived evidence).
- The staff email reply, if received and filed (see tripwire log),
  supersedes the AI-assistant answers where it differs.

Raw payloads + capture journal are in the PRIVATE qf-data-archive
(captures/td_feed_measure_pilot_20261026/), never public GitHub. This
package carries bar-free derived evidence only.
