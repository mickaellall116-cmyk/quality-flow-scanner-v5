# Generation contract — XNYS_SESSION_SCHEDULE_V2 (INERT — nothing in this document has been executed)

Task: `QF-XNYS-SCHEDULE-GENERATION-CONTRACT-20261019-34 r1`
Spec: GitHub Issue #1 comment `6261572099` (accepts -33 as
`PRIMARY_SOURCE_CALENDAR_RECORD_COMPLETE__GENERATION_NOT_AUTHORIZED`; dispatches this prep).
Contract state: **`PREP_READY__AWAITING_EXPLICIT_GENERATION_GO`**

This contract binds three already-accepted records into one execution-ready
specification for a FUTURE, separately authorized generation run:

- the completed primary-source calendar record (-31/-32/-33),
- the accepted offline environment route (-29, independence-corrected by -30),
- the frozen consumer schema `XNYS_SESSION_SCHEDULE_V2` (-28, Amendment v4).

**Nothing here was installed, built, imported, executed, or generated.**
Every command in §5 and in `RECEIPT_TEMPLATE.md` is inert text. No schedule
artifact exists. No data is qualified by this contract.

---

## 1. Source set (qualification authority)

The primary record is the ONLY qualification authority. Full enumeration with
paths and SHA-256s: `SOURCE_SET_MANIFEST.json` (this package). Summary:

| Role | Artifact | SHA-256 (prefix) | Commit |
|---|---|---|---|
| Core hours (rule text) | SEC Release 34-103356 / SR-NYSE-2025-21, fn 42 quoting NYSE Rule 1.1(d): 09:30–16:00 ET | `5f0263f7…` | `fdf1c34` (-33) |
| Core hours (operative, in-block) | NYSE Regulatory Memo RM-24-12 (2024-09-13) | `305fab2e…` | `fdf1c34` (-33) |
| Dated closures + 13:00 closes 2024–2026 | ICE/NYSE Group release, Nov 10, 2023 | `564de593…` | `d307439` (-32) |
| Dated closures + 13:00 closes 2025–2027 (corroborates 2025 + 2026 columns) | ICE/NYSE Group release, Nov 8, 2024 | `3b8a67d9…` | `d307439` (-32) |
| Exceptional closure 2025-01-09 (National Day of Mourning, Carter) | NYSE/ICE announcement, Dec 30, 2024 | `e1cd4c1a…` | `d307439` (-32) |
| Dated 2026 calendar + hours (live page) | NYSE Holidays & Trading Hours page capture | `79602f7b…` | `5d2060b` (-31) |
| Session counts (2026 = 251; 2027/2028 out of interval) | Trading_Days.pdf, current vintage | `f90b6d08…` | `5d2060b` (-31) |
| Session counts (2024 = 252; 2025 = 251 pre-Carter vintage; 2026 = 251) | Trading_Days.pdf, Dec-2024 vintage | `dd349170…` | `5d2060b` (-31) |
| Session counts (2025 = 250, final vintage) | Trading_Days.pdf, Nov-2025 vintage | `414d2ed3…` | `5d2060b` (-31) |

**Source priority and conflict rule (binding):**
official event notice **>** dated calendar release **>** count cross-check.
Any contradiction between sources that the priority rule cannot resolve =
**HOLD**. Worked example already reconciled in -32 and accepted: the
Dec-2024 Trading_Days vintage states 2025 = 251, the Nov-2025 vintage
states 250; the tier-1 Carter notice is dated Dec 30, 2024 — after the
earlier vintage — and accounts for exactly one January 2025 session
(261 weekdays − 11 closures = 250). This is consistency under the priority
rule, not a conflict. A future contradiction WITHOUT such a dated,
priority-resolving explanation = HOLD.

## 2. Environment binding (referenced, never modified by this contract)

From -29 (`research_notes/qualified_calendar_env_route_preflight_20261018_29/`,
commit `99b2096`), referenced without modification:

- Wheelhouse: `~/workspace/td_nl_wheelhouse_20261016/wheels`,
  manifest SHA-256 `210b8273a15cc7317b4a8029198f8d6e1401c1e375acdbe7f8602167c13e815b` (11/11 wheels re-verified in -29).
- Proposed hash-lock file: `PROPOSED_HASH_LOCK.txt`, SHA-256 `f5e8440d4fce1704dfdb40387b0ba7c9b6e007e76f9a8564efb4f8b06405b809`.
- Accepted NL freeze the install must reproduce byte-identically:
  SHA-256 `08b38cfa1880d328ba4b13dd2a17cb0d00c925860b457ec50fb6f211d42a7068`.
- Target: CPython 3.12.3, linux x86_64, glibc ≥ 2.17. System site-packages
  are UNQUALIFIED (per -29) and must never be used or extended.

The 11 pinned wheels (name = version = wheel SHA-256):

| Wheel | SHA-256 |
|---|---|
| pandas_market_calendars 4.5.1 | `7b4f3478cc18f44d6ce7d62fbac847b9b7b53bd6fd9d2d06cd76551112cc0bfd` |
| exchange_calendars 4.13.2 | `fc5a2ad0d61b5c3a6539a3061cd4cbb55c59f4a903455cec7926e4b798919996` |
| pandas 2.2.3 | `fffb8ae78d8af97f849404f21411c95062db1496aeb3e56f146f0355c9989319` |
| numpy 1.26.4 | `675d61ffbfa78604709862923189bad94014bef562cc35cf61d3a07bba02a7ed` |
| python-dateutil 2.9.0 | `cbf2f1da5e6083ac2fbfd4da39a25f34312230110440f424a14c7558bb85d82e` |
| pytz 2024.2 | `31c7c1817eb7fae7ca4b8c7ee50c72f93aa2dd863de768e1ef4245d426aa0725` |
| tzdata 2026.5 | `b683bd1b6659ddcd810ff02ad09ba821d4bf1065072805063eb35c49617905ac` |
| pyluach 2.3.0 | `4497b731aef59508b079dbf5f00bc5bf4329ac45090a6cd37b5a83756f0e69ab` |
| toolz 1.2.0 | `890f820b1cb8152785aaf9386d8707770110809035800985ca65cb24ce1120ef` |
| korean_lunar_calendar 0.4.0 | `c042e20de0bb702add6bec8d0f6da1ea8d3b170838e63846f70420cf341fe4e7` |
| six 1.17.0 | `4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274` |

## 3. Pinned code paths and the independence classification (-30)

From -30 (`DEPENDENCY_MAP.json` SHA-256 `0752866e…`, commit `29ab49e`).
The future run must verify these installed-member hashes BEFORE any
generation; any mismatch = HOLD.

**Path A — pandas_market_calendars, key PINNED to native `NYSE` (never `XNYS`):**

| Member | SHA-256 |
|---|---|
| `pandas_market_calendars/calendar_registry.py` | `f5e70a904464ced8b055a39756c59f51c12f693e7f4b0c290f955a5002614756` |
| `pandas_market_calendars/calendars/nyse.py` (class `NYSEExchangeCalendar`) | `135ba9dc683eb6797fba014d8e5979d0dc12537fa23fcabd7f2302c94712f4e3` |
| `pandas_market_calendars/holidays/nyse.py` (rule tables) | `e85f5edb348f4b6455ac92b97e10b81a70975bab7c7e97cf7a616c82c56ac4b3` |
| `pandas_market_calendars-4.5.1.dist-info/METADATA` | `1d40c845ac4b7db1d0d9fe46cfdd8b881732977208fdd376c00b1f7ce9e71525` |

FORBIDDEN on path A: the key `XNYS`. Inside pandas_market_calendars that key
resolves to `calendars/mirror.py` (SHA-256 `3aaf6345…`), which imports
`exchange_calendars` at top level and delegates every session to it — an
emission keyed that way is exchange_calendars observed twice, not a second
observation. Any use of the mirror key invalidates the run.

**Path C — exchange_calendars used directly, key `XNYS`:**

| Member | SHA-256 |
|---|---|
| `exchange_calendars/calendar_utils.py` (registry: `XNYS` → `XNYSExchangeCalendar`) | `7d12d53482fe295bd5a9b272a635df2292528b8dc19538c93649fa4ee84b40e6` |
| `exchange_calendars/exchange_calendar_xnys.py` | `baa39f07163abafcf2800b69edc5d920c3db0a64f8bbb30dc7d522883d0b5bd7` |
| `exchange_calendars/us_holidays.py` (rule tables) | `a2444bd7aef3ff651faff3f9117c47a0d41e9e7c312f38ecf42403e4d996830e` |
| `exchange_calendars-4.13.2.dist-info/METADATA` | `b0d856a2f790e0d645d5847880ccd21de2771921a7ed78464184da4cd73289ec` |

**Classification (binding, from -30):** paths A and C are
`COMMON_ANCESTOR_BUT_SEPARATE_RULE_TABLES` — both descend from
Quantopian/Zipline's NYSE calendar; pandas_market_calendars additionally
declares `exchange-calendars>=3.3` as a runtime dependency. Therefore:

- Agreement between emission A and emission C is a **correlated consistency
  check ONLY**. It is logged in the receipt; it **never qualifies** anything.
- **Qualification = date-by-date parity of the generated artifact against
  the §1 primary record + the pinned session counts** (`PARITY_MATRIX.md`).
- Any A≠C disagreement, or any artifact≠primary-record disagreement =
  **HOLD**, with no partial credit and no pinned artifact.

(Note: -29's plan text described the two libraries as "independent"; that
characterization is superseded by -30's audit and must not be relied on.)

## 4. Generator contract (specification only — the generator is NOT written here)

A future authorized task writes the generator; this section fixes what it
must do so the GO needs no further specification work.

**Deterministic inputs (complete list — nothing else may influence output):**

1. The §2 wheel closure, installed per §5.
2. Path A key string: exactly `NYSE`. Path C key string: exactly `XNYS`.
3. Interval: closed `[2024-09-16, 2026-10-16]` (generation window), plus two
   auxiliary full-calendar-year windows for the count parities only:
   `[2024-01-01, 2024-12-31]` and `[2026-01-01, 2026-12-31]` (2025 is fully
   inside the main window).
4. The §1 source set, hash-verified against `SOURCE_SET_MANIFEST.json`
   before generation (verification only — the generator never parses the
   primary PDFs/HTML; parity is a review step, §6).

**Emission rules:**

- For each path, enumerate sessions in the window: date, open, close in
  `America/New_York` local time. Ordinary sessions: open `09:30`, close
  `16:00`. Scheduled early closes: close `13:00`. No other open/close pair
  is admissible; any other value from either library = HOLD.
- The artifact's session set = the set on which A and C agree exactly
  (date, open, close). If the sets differ in any element: HOLD, no artifact.
- `sessions` sorted ascending by date; exactly one entry per date; no date
  outside `[2024-09-16, 2026-10-16]`; no weekend sessions (a weekend session
  from either library = HOLD).

**Output artifact — exact `XNYS_SESSION_SCHEDULE_V2` schema instance**
(as required by `fold_materializer_v3.py`, SHA-256 `e1b0dfed…`, -28):

```json
{
  "artifact": "XNYS_SESSION_SCHEDULE_V2",
  "source": "<future generation task id> + primary record packages -31/-32/-33",
  "version": "1",
  "exchange": "XNYS",
  "timezone": "America/New_York",
  "coverage_start": "2024-09-16",
  "coverage_end": "2026-10-16",
  "sessions": [
    {"date": "YYYY-MM-DD", "open": "09:30", "close": "16:00"},
    {"date": "YYYY-MM-DD", "open": "09:30", "close": "13:00"}
  ]
}
```

Field rules (consumer-enforced, restated so generation cannot drift):
`artifact` exactly `XNYS_SESSION_SCHEDULE_V2`; `source`/`version` non-empty
strings; `exchange` exactly `XNYS`; `timezone` exactly `America/New_York`;
`coverage_start` exactly `2024-09-16` (frozen by the consumer);
`coverage_end` exactly `2026-10-16` for this generation (the frozen
interval end; any other value = a different task); every session
`close > open` and `close` after `09:30` (Amendment v3 anchor rule).

**Canonical serialization (contract-fixed):** UTF-8 JSON, object keys
sorted, separators `(",", ":")`, `sessions` in ascending date order, one
trailing newline. The emitted bytes are hashed (SHA-256) and pinned in the
receipt BEFORE any market timestamps are supplied to any consumer.

**Determinism check (mandatory in the future run):** the generator runs
twice from the same pinned environment; the two artifact byte strings must
be identical. Any difference = HOLD.

## 5. Inert execution sequence (future run — EXECUTE NONE OF THIS NOW)

Placeholders: `<GO_TASK_ID>`, `<WORKDIR>` (isolated scratch outside the
repo), `<WHEELHOUSE>` = `~/workspace/td_nl_wheelhouse_20261016`,
`<REPO>` = the scanner repo. All steps run with networking disabled
(`--no-index` everywhere; the run must additionally execute inside a
no-network context, and any attempted network access = HOLD).

```text
# 0. Pre-flight verification (read-only)
sha256sum -c SOURCE_SET_MANIFEST.json-derived checks   # every §1 artifact
sha256sum <WHEELHOUSE>/SHA256SUMS (manifest 210b8273…) # wheel-by-wheel
sha256sum PROPOSED_HASH_LOCK.txt == f5e8440d…

# 1. Isolated environment build (offline, hash-pinned)
python3.12 -m venv <WORKDIR>/venv
<WORKDIR>/venv/bin/pip install --no-index --no-cache-dir --require-hashes \
    -r <REPO>/research_notes/qualified_calendar_env_route_preflight_20261018_29/PROPOSED_HASH_LOCK.txt \
    --find-links <WHEELHOUSE>/wheels

# 2. Freeze acceptance — must equal the accepted NL lock byte-for-byte
<WORKDIR>/venv/bin/pip freeze | sha256sum   # expect 08b38cfa…

# 3. Installed-member pins (§3 tables) — verify each sha256; mismatch = HOLD

# 4. Dual emission (generator written under the GO task; source hashed first)
<WORKDIR>/venv/bin/python <WORKDIR>/generator.py --path A --key NYSE \
    --start 2024-09-16 --end 2026-10-16 --out <WORKDIR>/emission_A.json
<WORKDIR>/venv/bin/python <WORKDIR>/generator.py --path C --key XNYS \
    --start 2024-09-16 --end 2026-10-16 --out <WORKDIR>/emission_C.json
#    + auxiliary full-year emissions for 2024 and 2026 (count parities)
#    + a second full repetition of both emissions (determinism check)

# 5. Agreement + assembly: A == C session-for-session, else HOLD.
#    Assemble the §4 artifact; canonical-serialize; sha256 it.

# 6. Parity review per PARITY_MATRIX.md (independent of the generator):
#    every row PASS, else HOLD with the failing row ids in the receipt.

# 7. Consumer checks (no market data):
#    - re-run the frozen -28 synthetic fixture suite expectations against
#      fold_materializer_v3.py unchanged (sha e1b0dfed…);
#    - parse the real artifact via the consumer's schedule parser using
#      SYNTHETIC timestamps spanning the interval (expect no SCHEDULE_*
#      error; expect coverage_first/last sessions = first/last artifact
#      sessions on/after 2024-09-16 / on/before 2026-10-16).

# 8. Receipt: complete RECEIPT_TEMPLATE.md, attach stdout/stderr files,
#    commit artifact + receipt, pin the artifact SHA-256 on the bridge.
```

## 6. Fail-closed conditions (any one = HOLD; no partial artifact, no pin)

1. Any §1 source artifact hash ≠ `SOURCE_SET_MANIFEST.json`.
2. Wheelhouse manifest mismatch, any wheel hash mismatch, or the lock file
   hash ≠ `f5e8440d…`.
3. `pip freeze` ≠ NL lock `08b38cfa…` (byte comparison).
4. Any §3 installed-member hash mismatch.
5. Path A invoked with any key other than `NYSE`, or any use of the PMC
   mirror module/key `XNYS` — run invalid, restart not permitted under the
   same GO without disclosure.
6. Any network access attempted or detected during install or generation.
7. Emission A ≠ emission C on any date/open/close (logged as a consistency
   failure — never resolved by picking a side).
8. Any `PARITY_MATRIX.md` row FAIL — including the master date sweep, any
   dated closure or early close, the Carter closure, core hours, or any
   count check (2024 = 252 auxiliary, 2025 = 250, 2026 = 251 auxiliary).
9. Non-determinism: repeated emissions or repeated artifact bytes differ.
10. Artifact violates §4 schema/serialization, or the consumer parser
    rejects it, or consumer synthetic checks regress.
11. `coverage_end` ≠ `2026-10-16`, any session outside the closed interval,
    any weekend session, any open/close pair other than 09:30–16:00 /
    09:30–13:00.
12. Any contradiction in the primary record not resolved by the §1
    priority rule.

## 7. Authority marker (exact statement required by the spec)

> **Contract state: `PREP_READY__AWAITING_EXPLICIT_GENERATION_GO`.**
> Generation requires a separate explicit GO: a distinct future task ID
> authorizing (a) isolated environment creation from the pinned wheelhouse
> under this contract, and (b) `XNYS_SESSION_SCHEDULE_V2` generation,
> parity review, and pinning. This contract does NOT claim the environment
> was built, a schedule was generated, or any data became qualified. Source
> completion (-33 acceptance) did not authorize generation; this prep does
> not either.

## 8. What this contract preserves and never touches

-29 through -33 packages are referenced by hash and preserved unedited.
No schedule bytes exist. The sealed holdout remains sealed — the artifact
interval starts 2024-09-16, the day after the holdout ends (2024-09-15),
by construction of the V2 contract. No market/OHLC data, no performance,
no strategy code, no TD/vendor calls, no production/live/ledger writes,
no Issue #9.
