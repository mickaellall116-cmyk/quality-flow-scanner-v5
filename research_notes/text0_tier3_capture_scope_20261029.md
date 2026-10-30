# Tier-3 holdout capture — signable scope (Muse, 2026-10-29)

Prepared at ChatGPT's request (Slack decision card, TS 1793331463.944659);
scope posted in that thread (TS 1793332628.454499). Preparation only —
no vendor call made or authorized by this document. Facts compiled from
DECISION_CARD_TIER3_BYTES.md (corr4 successor package, addendum 7443e5b).

PURPOSE: obtain the 11 missing Tier 3 holdout-window captures so the
frozen Text 0 pool-count session can run. This scope covers raw-data
capture and archival ONLY. It does not authorize the counting session
itself, any outcome or return computation, any G7 run, trading, or
production change. Raw capture is not sealed-outcome access: no
price-derived quantity is computed at capture; bars are stored raw and
hashed before any parse.

VENDOR/SOURCE: Twelve Data /time_series, interval 1h, timezone
America/New_York — identical endpoint class and parameters to the
frozen -23 manifest used for the Tier 2 holdout legs.
SYMBOLS (11): AAOI, ACN, BABA, BE, BLK, COF, CRDO, IREN, MPWR, SPOT, TWLO.
WINDOW/COVERAGE: 2023-10-19 to 2024-09-15, 227 sessions, ~1,583 bars
per symbol expected. Missingness rule: any symbol short or defective
fails the run (below).
CALLS/COST: 11 symbol requests at outputsize 5000 + 1 /api_usage
preflight = 12 calls, 12 credits, $0 on the existing free-tier plan.
No purchase, no subscription change.
USE/RETENTION: inventory construction for the Text 0 counts session
only. Private qf-data-archive only, append-only; never the public
scanner repo. Twelve Data deletion duty (within 30 days after
subscription end) applies.
HASH/RECEIPT PLAN: capture manifest (symbols, window, params, code
hash) pinned and posted BEFORE the run; every raw file SHA-256 hashed
at capture; receipt manifest and root verified before any parsing;
archive push verified byte-identical by re-fetch.
CONTROLS: two-operator — Muse executes, ChatGPT reviews the manifest
before and the receipts after. One attempt per symbol, fail-closed: a
failed, missing, or defective symbol stops the run with a named error;
the tier never shrinks; no substitute symbol; no partial result is
usable.
NO BACKFILL: this capture creates no signals, positions, or performance
records and changes no prior result.
RIGHTS LINE (the signature chooses): (a) capture proceeds scoped as
evaluation on the existing Basic plan, the same basis as the October
captures; or (b) capture waits until the ongoing-research rights basis
is settled. Unsigned = no capture.

STATUS: awaiting Mike's signature. Unsigned = no capture.

## ADDENDUM — query-parameter correction (Muse, 2026-10-30)

ChatGPT preflight flag (Slack TS 1793366866.816419; Issue #1 review):
outputsize=5000 without bounded dates returns the most recent bars and
cannot be trusted to reach October 2023. Accepted; the scope above is
corrected:

- The capture query is bound to the EXACT frozen -23 manifest
  parameters, including its explicit start_date / end_date bounding
  for the sealed window. The outputsize figure is not a standalone
  parameter and authorizes nothing by itself.
- Coverage proof joins the receipt plan: for every symbol, the receipt
  must show the first returned bar at or before the window start and
  the last at or after the window end, with bar counts reconciled
  against the 227-session calendar. Any symbol failing coverage fails
  the whole run closed, same as a missing or defective symbol.
- The pre-run manifest pin (review-gated: ChatGPT reviews the manifest
  before any call) must list the literal parameter values taken from
  the -23 manifest, so the pinning is verified, not asserted.

No change to the rights position: public Twelve Data docs do not
settle the research-use limitation, no rights are inferred, and zero
calls occur until a verified rights route exists and Mike signs.
