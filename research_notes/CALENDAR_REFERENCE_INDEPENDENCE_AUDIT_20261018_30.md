# Calendar Reference Independence Audit — 2026-10-18 (task -30 r1)

Spec: GitHub Issue #1 comment `6258069766` (verdict on -29:
`ROUTE_A_ENV_CLOSURE_ACCEPTED__QUALIFICATION_INDEPENDENCE_HOLD`). Cap ≤20 min,
one static pass. Method: wheel bytes read as zip archive members only — no
install, no import, no execution, no schedule generation. This is an additive
correction; -29's commit `99b2096` is preserved unchanged. Machine-readable map:
`calendar_reference_independence_audit_20261018_30/DEPENDENCY_MAP.json`.

## Gate return: `NO_INDEPENDENT_OFFLINE_REFERENCE`

The existing bytes cannot support independence. Details by path:

**Classification (spec vocabulary):**
- PMC key `NYSE` (native) vs EC key `XNYS` (direct):
  `COMMON_ANCESTOR_BUT_SEPARATE_RULE_TABLES`
- PMC key `XNYS` (mirror) vs EC key `XNYS` (direct):
  `SHARED_RULES_OR_CALL_THROUGH`
- `INDEPENDENT`: not supportable (package-name difference is zero evidence).

## The three code paths, pinned to bytes

Wheels (wheelhouse manifest `210b8273…`): `pandas_market_calendars-4.5.1`
sha256 `7b4f3478…`; `exchange_calendars-4.13.2` sha256 `fc5a2ad0…`.

**Path A — PMC `NYSE`, native.** `calendar_registry.py` (`f5e70a90…`) imports
`NYSEExchangeCalendar` from `.calendars.nyse` (`135ba9dc…`), aliases
`["NYSE","stock","NASDAQ","BATS","DJIA","DOW"]` (line 807). The module imports
only pandas/pytz and PMC's own modules — **zero** `exchange_calendars`
references in `calendars/nyse.py`, `holidays/nyse.py` (`e85f5edb…`), and
`calendar_utils.py` (`eb206a4f…`). Its rule tables are its own: `Holiday(...)`
objects defined in `holidays/nyse.py` (e.g. `USNewYearsDayNYSEpost1952`,
`FridayAfterIndependenceDayNYSEpre2013`, `USJuneteenthAfter2022`); special
closes/opens and adhoc lists are defined in the class module itself.

**Path B — PMC `XNYS`, mirror = call-through.** `calendars/mirror.py`
(`3aaf6345…`) does `import exchange_calendars` at top level, reads EC's
`_default_calendar_factories`, and dynamically builds a `TradingCalendar`
subclass for **every** EC key — including `XNYS` — whose `_ec_class` is the EC
class and whose sessions/holidays/weekmask delegate to the wrapped EC instance.
A PMC emission keyed `XNYS` is therefore the EC calendar observed twice, not a
second implementation. Any future dual-emission run must pin the PMC key to
`NYSE` explicitly; the -29 plan did not pin the key.

**Path C — EC `XNYS`, direct.** `exchange_calendar_xnys.py` (`baa39f07…`):
`XNYSExchangeCalendar(ExchangeCalendar)`, registered as `"XNYS"` in
`calendar_utils.py` (`7d12d534…`, line 126; EC-internal aliases map
`"NYSE" -> "XNYS"`). Rule tables are EC's own `us_holidays.py` (`a2444bd7…`,
43 named `Holiday` objects imported by the calendar); special closes/adhoc in
the class module. The source itself cites `nyse.com/pdfs/closings.pdf` as a
resource for its rules.

## Why not INDEPENDENT (byte-level)

- **Common ancestor:** both NYSE modules carry Quantopian, Inc. copyright
  headers (PMC 2016; EC 2018) — both descend from Quantopian/Zipline's original
  NYSE calendar. Identically named rules appear in both tables
  (`USMartinLutherKingJrAfter1998`, `USWashingtonsBirthDay1964to1970`,
  `MonTuesThursBeforeIndependenceDay`, `WednesdayBeforeIndependenceDayPost2013`,
  `USElectionDay1848to1967`, …). The tables are separately maintained copies
  (divergent entries on both sides) — hence separate tables, but a shared
  ancestral rule set: an ancestral error would be present in both.
- **Package-level coupling:** PMC's METADATA (`1d40c845…`) declares
  `Requires-Dist: exchange-calendars>=3.3`, and PMC's registry imports the
  mirror module, which imports EC at module level. The two packages are not
  separable in the Route A closure — EC's presence in the 11-wheel set exists
  precisely because PMC requires it.

Agreement between the Path A and Path C emissions is therefore a **correlated
consistency check** (it catches implementation drift between two maintained
copies, nothing more). It is not proof of official NYSE holiday/closure/
early-close semantics.

## Revised qualification gate (supersedes -29's gate by reference)

1. Dual library agreement (Path A `NYSE` native vs Path C `XNYS` direct) may
   be **logged** as a consistency check. It **cannot qualify** the artifact,
   alone or in part.
2. Qualification requires an **immutable primary NYSE authoritative source**
   plus the pinned implementation as a cross-check: the artifact's every
   session, holiday, and early close in `[2024-09-16, coverage_end]` must match
   the primary source date-by-date; any disagreement = HOLD.
3. **Missing artifact (exact):** a hash-pinned capture of the New York Stock
   Exchange's own published Holidays & Hours calendar (NYSE Group, Inc.;
   `nyse.com/markets/hours-calendars`, whose published form includes the
   exchange's closings document cited by the EC source,
   `nyse.com/pdfs/closings.pdf`), covering every year of the coverage
   interval. Future authorized step: fetch once, pin SHA-256 in a committed
   capture receipt (source URL, retrieval timestamp, artifact hash), then run
   the date-by-date cross-check. No fetch was performed in this audit.

## Prohibitions — explicit confirmation

Static pass only: zero installs; zero imports or executions of candidate
distributions (wheel members read as bytes via zipfile); zero schedule
generation; zero market/OHLC data; zero holdout access in any form; zero
vendor/helper/model/API calls (network solely for the read-only public spec
fetch and the git delivery push); zero credentials, credits, or spend; zero
tuning; zero live/production/ledger writes; zero trading; zero Issue #9 work;
no prior frozen record edited — this package is additive and supersedes -29's
qualification-gate language by reference only. TD transaction
`QF-TD-READINESS-LIVE-20261017-20` remains UNUSED and untouched.
