# QF-EQUITY43-S1-CALENDAR-EXTENSION-20261024-18 r1 — RESULT

**Verdict: CALENDAR_EXTENSION_PASS (candidate artifact; adoption is a
separate governance step).** Governing text: Issue #1 comment
6381871826. Single-dispatch CLEAR (no prior -18 stage content, package
path, or commits; origin/main head 8d0d653 at check time). ACK: Slack
TS 1792830526.166499, bridge cb85ca5.

## What was built

An append-only XNYS extension of the pinned 751-session table,
target through **2027-12-31 — achieved in full**; no
authoritative-source boundary was hit.

| | |
|---|---|
| Prefix (qualified) sessions | 751 (2023-10-19..2026-10-16), byte-preserved |
| Appended sessions | **303** (2026-10-19..2027-12-31) |
| Total | **1054** |
| Extended table SHA-256 | `86a1d4eaa5b838aa4138cef3c7dc5efcea99997fec40863b015075829acf6371` (56,468 bytes) |
| Superseded table SHA-256 | `00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f` |

303 appended sessions cover a prospective 100-observation S1 program
with room to spare. Appended early closes (13:00 ET): 2026-11-27,
2026-12-24, 2027-11-26 — and no others, which is itself a checked
fact (2027 has no July-3 or Dec-24 early close: Jul 4 2027 is a
Sunday, Dec 25 2027 is a Saturday).

## How it was proven (battery 30/30 PASS — test_stdout.txt)

- **Prefix equality proven, not asserted** (A1–A5): pinned table
  re-hashed to its recorded pin; all 751 rows equal in order; the
  sessions segment of the extended file carries the 751 rows as an
  exact byte prefix; first appended session is **2026-10-19** (Mon,
  regular) after the Fri 2026-10-16 boundary.
- **Generator fail-before anchor**: the pinned rule generator
  (`calendar_gen18.py`, pure stdlib, sha `898297a2…`) reproduces all
  751 qualified rows exactly — including the 2025-01-09 Carter
  national-day-of-mourning closure, encoded as a named historical
  fact — before any extension row is trusted.
- **Independent cross-check**: three-way agreement, row-for-row over
  the full 2023-10-19..2027-12-31 range — rule generator ==
  pandas_market_calendars 4.5.1 (native NYSE key) == exchange_
  calendars 4.13.2 (XNYS), 1054/1054 sessions. Libraries ran in a
  fresh offline venv from the pinned wheelhouse under `--require-
  hashes`; pip freeze is byte-identical to the -35 r2 pin
  (`08b38cfa…`). One disclosed deviation: the pinned -35 emitter
  hard-codes the exchange_calendars construction window end at
  2027-02-01, so path C used a driver identical in library and
  formatting with widened construction bounds only (PROVENANCE.json).
- **The cross-check caught a real rule error**: my draft applied the
  generic federal Saturday observance to New Year's Day and closed
  2027-12-31. Both pinned libraries keep it a regular session — NYSE
  does not observe NYD on Fri Dec 31 when Jan 1 is a Saturday (e.g.
  2021-12-31 was a full session). Rule corrected, disclosed in the
  generator docstring and PROVENANCE.json; qualified-range
  reproduction unaffected.
- **Boundary fixtures** (B): both 2026 and 2027 DST transitions in
  both directions, proven as UTC open instants (EDT 13:30 UTC vs EST
  14:30 UTC across each boundary Fri→Mon); Thanksgiving early closes
  2026+2027; July-3/4 rules incl. the 2027 Sunday case (Fri Jul 2
  regular, Mon Jul 5 closed); Christmas/New Year adjacency incl.
  2027-12-24 as the observed Christmas closure and the 2027-12-31
  exception; weekend/holiday exclusion across all 2027 holidays.
- **Structural rejection** (C): duplicate row, missing row, and
  out-of-order rows are all rejected by the consumer verifier.
- **Tamper battery** (D): altered date, open, close, timezone pin,
  source pin, table SHA pin, and generator pin each STOP the
  verifier; the clean table passes.
- **Fork re-pin** (E): the -17 causal fork file is byte-identical to
  its -17 manifest pin (`929c1bc4…`) and is untouched in content;
  under the NEW table pin it produces the correct bins on appended
  sessions — regular 2026-10-19: [09:30,13:30) + [13:30,16:00);
  early-close 2026-11-27: single [09:30,13:00) — with causal BAR
  emission end-to-end (emitted_at == bin close) and fail-closed
  UNKNOWN_SESSION rejection beyond the table (2028-01-03) and on a
  closure date (2027-12-24). The repin record is
  `observer_repin18.json`, effective only inside this candidate
  package; the -17 stage's own table still hashes to `00c5555c…`.

## Pins

- Generator: `calendar_gen18.py` sha256 `898297a2cf30015ee734fe7a5efe088849bcee727aa12e1e4cc8d024f8e6aa4d`
- Cross-check emitter: byte-identical to the pinned -35 r2 generator, sha256 `2995b124f9cd42ef3ddb0122684311e29bf2690177656e31e890ef1de2488114`
- tzdb: library conversions via pytz 2024.2 (wheel `31c7c181…`); DST
  proofs via system tzdata 2026e (`America/New_York` file sha256
  `e9ed07d7bee0c76a9d442d091ef1f01668fee7c4f26014c0a868b19fe6c18a95`)

## Bounds held

Offline only; 0 vendor calls/credits; no latency claim or
measurement; no returns/performance; no holdout or SMCI reads; no G4
adoption or waiver; no production change; no S1/S2 activation, no
T0, no trades. The adopted 751-session table of record is NOT
modified — this extension is a candidate artifact for the isolated
fork; adoption remains a separate governance step. PAUSED production
re-proved at start and at package time (harness `ce7c902c…`,
PAUSE_NEW_ENTRIES present, RESUME_NEW_ENTRIES absent). -15/-16/-17
packages untouched. Elapsed ~49 min, single lane.

## What this does not do

S1 launch remains HOLD: activation needs Mike's separate GO naming a
future T0, the live corrected-grid feed remains FEED_NOT_READY with
rights/latency UNQUALIFIED (a separate gated lane, per the tasking
comment), and G4/VBASIS remains UNADOPTED. Per the sequencing
decision, the next offline lane after independent review of this
package is staged-byte/namespace-isolation preparation.

— Muse
