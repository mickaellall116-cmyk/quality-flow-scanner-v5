# QF-CRYPTO-DATA-ROUTE-DISPOSITION-20261023-05 r1 — DISPOSITION

**Type:** bounded offline disposition, existing evidence only. No vendor/API
calls, no new bytes, no credits spent. Program TD total unchanged at 24.
**Governing task:** Issue #1 comment 6370944853 (ChatGPT independent
actual-byte verdict on -04, `411ac2c`).
**Verdict of this package:** Twelve Data crypto branch is classified
**NOT_EVALUABLE_SCHEMA_AND_PHASE**. Two NOT-EXECUTED disposition paths are
returned in §4. Nothing here is adopted; adoption is a governed decision
(see §6).

---

## 1. Frozen strategy dependencies on Volume, VWAP, phase, and labels

Source pins (sha256; working-tree files identical to the pinned lineage —
`v54_engine.py`/`v54_rules.py` live in the recovery-branch stack, not on
`main`; all other files match `origin/main` byte-for-byte):

| File | sha256 |
|---|---|
| `scanner_rules.py` | `62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c` |
| `v54_engine.py` | `bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb` |
| `v54_rules.py` | `1b55dedce3b17b1670ac7ee75bfcf4375a0162a1daa780a8abb4199c9ebb817a` |
| `pine_backtest.py` | `447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5` |
| `masterscanner_api.py` | `c3e95b25b114a50c4129360f24f4fd27471b000a7749fe750abf038f1abf0a21` |
| `v54_forward_harness.py` (PAUSED pin) | `ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d` |
| checker `crypto_session_model.py` (-94) | `248442f17add6e58fa31b1e3aa847f0519dd3b21efbd564c38460d8e6da1e5e9` |

Crypto members of frozen UX51 (`pine_backtest.UNIVERSE_X`, Option A freeze):
**BTC-USD, ETH-USD, SOL-USD, DOGE-USD, AVAX-USD, LINK-USD, XRP-USD** (7).

### Volume / VWAP / relative-volume dependencies (all on the frozen path)

- `scanner_rules.py` session constructor: `SessionVWAP` = cumulative
  (typical price × `Volume`) / cumulative `Volume` per session; 4H
  aggregation takes `Volume: sum`. No Volume column ⇒ VWAP undefined.
- `scanner_rules.py` signal gate: a qualifying row requires
  `above_vwap is True` and `rel_vol >= MIN_RELATIVE_VOLUME` (0.80).
- `scanner_rules.py` confirmation block: session VWAP computed from
  `Volume`; `relative_volume` = last-bar volume / 20-bar rolling mean
  volume; both gate confirmation. Missing volume yields
  `relative_volume = 0.0`, which fails the 0.80 gate on every bar.
- `scanner_rules.py` premarket block: `pm_volume` / `pm_vwap` are computed
  from `Volume` (equity path; cited for completeness of the dependency
  inventory).
- `v54_engine.py` (frozen V5.4 engine): `min_bars` includes `VOL_BASE_LEN`
  and `VWAP_LEN`; `above_vwap = price > VWAP`; `rvol = Volume / volbase`;
  trigger paths require `above_vwap`; `rel_vol` is emitted per signal.
- `pine_backtest.py` (parity path): `vol_ma` from `Volume`; an explicit
  schema guard fires when `Volume` is absent or all-NaN.

### Bar labels and decision times

- 4H bars are labeled by bin-start; signals evaluate completed bars at bin
  closes. Cross-asset joins key on bin-start labels only (THREE-GATE
  freeze, `research_notes/THREE_GATE_FREEZE_20261021.md`).
- Crypto sessions are the adopted S-C1…S-C6 contract: session = ET
  calendar date; six 4H bins anchored **09:30/13:30/17:30/21:30/01:30/
  05:30 ET wall-clock** (:30 phase); DST absorbed in one overnight bin
  (23/25-bar sessions).

### Substitution test — FAIL CLOSED on both

- **OHLC-only substitution changes signal semantics.** With no volume,
  SessionVWAP is undefined, `above_vwap` cannot be true, and
  `relative_volume` is identically 0.0 < 0.80. Treating absent volume as
  zero silently converts the frozen strategy into a no-signal generator
  for crypto; waiving the gates instead would be a different strategy.
  Either way the frozen semantics do not survive. **Fail closed.**
- **Midnight-phase substitution changes signal semantics.** S-C bins open
  at :30 ET. Hourly bars stamped on the :00 phase cannot compose a
  09:30–13:30 bin without splitting a bar at 09:30; shifting stamps by
  −30 min would fabricate labels and move the DST-absorbing bin, changing
  bar grouping, session-VWAP accumulation boundaries, bin-start join keys,
  and decision times. **Fail closed.** (This is precisely why the equity
  legs worked: Twelve Data equity 1h bars are session-anchored at :30;
  its crypto bars are calendar-anchored at :00 — §2 evidence.)

## 2. Classification — Twelve Data crypto

**`NOT_EVALUABLE_SCHEMA_AND_PHASE`** (per task item 2; no existing
immutable evidence proves a compatible form).

Evidence (the only Twelve Data crypto body ever captured; -04,
`411ac2c`; archive `qf-data-archive` `ba4105a`, quarantine sha256
`9c5a0487569aa159ed51960bb22f94261c3ecb2be30c39ca37056f9855e20598`,
522,073 bytes; independently re-verified by ChatGPT from the archive):

- `BTC/USD` (alias of internal `BTC-USD`), exchange Binance, HTTP 200,
  exactly **4,992 rows**, 2023-10-19 00:00:00 → 2024-05-13 23:00:00.
- Row keys are exactly `datetime/open/high/low/close` — **0/4,992 rows
  carry a volume field** → `SCHEMA_COVERAGE_HOLD` (independent blocker 1).
- Stamp minutes are exactly `{00}`; fall-back 2023-11-05 has 25 wall rows
  (01:00 duplicated), spring 2024-03-10 has 23 (no 02:00) — genuine ET
  wall stamps on the **00:00 calendar phase**, not the pinned S-C :30
  phase → `CALENDAR_PHASE_HOLD` (independent blocker 2).
- The -03 form (`BTC-USD` literal) returned provider 404 — a transport
  defect, superseded by the pinned alias in -04; the alias response is
  the schema/phase evidence above. No other Twelve Data crypto response
  exists in program evidence. No parameter guessing, no timestamp
  shifting, no volume synthesis, no post-result waiver was or is applied.

## 3. Crypto route matrix (known/local evidence only)

| Route | Raw 1h OHLCV for 7 crypto | Stamp phase / provenance | Historical reach | Persistence / receipts | Status |
|---|---|---|---|---|---|
| Twelve Data | FACT: reachable, alias accepted, row count exact; **volume absent 0/4,992** | FACT: ET wall, :00 phase (wrong vs S-C :30) | FACT: 2023-10-19 reach demonstrated on HO-C1 | FACT: immutable archive + hash-chained receipts proven on equity legs | **NOT_EVALUABLE_SCHEMA_AND_PHASE** |
| Yahoo Finance | FACT: incumbent live feed; local Stage C raw 1h covers **0/7 crypto**; no crypto bytes ever captured in this program. INFERENCE: Yahoo's API returns a volume field for crypto pairs generally. UNTESTED on any captured crypto byte here | UNTESTED for crypto; equity bars are session-anchored | FACT: 1h reachback is a rolling ~730d window ending ≈Oct 2024 (-77 audit) — the 2023-10-19 HO start is **structurally out of reach today** | FACT: capture lane PARKED; rev.3 not adopted; no receipt discipline in force | **OUT for the HO window (reach)**; volume/phase UNTESTED |
| Tiingo | UNTESTED (no crypto call ever made) | UNTESTED | UNTESTED | FACT: license terms bar persistence (standing program finding) | **OUT by terms** for a persisted baseline |
| Exchange-native APIs (Binance / Coinbase / Kraken public klines) | FACT: never called in this program; zero bytes, zero receipts. INFERENCE: exchange klines natively carry volume. INFERENCE: they are :00-phase hourly, which cannot compose :30 S-C bins without sub-hourly granularity | UNTESTED | UNTESTED (public kline history is deep in general, but nothing is evidenced here) | UNTESTED (terms and receipt discipline unexamined) | **UNTESTED** — exact missing proof in §4 Path A |
| Other vendors (Intrinio / Zacks etc.) | FACT: declined by Mike for ERD ($950/mo); no crypto evidence exists | UNTESTED | UNTESTED | UNTESTED | **UNTESTED / out of scope** |

Exact missing proof for every non-TD row is the same five-part pilot
evidence defined in §4 Path A. No row besides Twelve Data has any
captured crypto byte in program evidence.

## 4. Two NOT-EXECUTED paths

### Path A — Preserve frozen UX51; qualify a separate crypto provider

Minimum separate-provider pilot evidence needed for the 7 crypto pairs,
all proven on **actual bytes** before any full-span attempt:

1. **Schema:** the provider's crypto 1h response carries a real volume
   field on 100% of rows for a first full-span symbol (BTC first, per
   the Card A structure) — zero-volume/nonflat and missing-volume classes
   trip the checker as on equities.
2. **Phase composability:** stamps are honest instants from which the
   exact S-C :30-phase bins compose **without splitting bars or shifting
   stamps** — i.e. native :30-phase/session-anchored hourly bars, or a
   finer native granularity (e.g. 30m) that aggregates exactly.
3. **Reach:** the HO window 2023-10-19 → 2024-09-13 and the DEV span are
   both served, with exact expected-row counts stated before the call.
4. **Persistence:** terms permit immutable archival + hash-chained
   receipts in `qf-data-archive` (the Tiingo failure mode excluded up
   front).
5. **Pilot discipline:** one-symbol-first, preflight quota read, hard
   credit/cost cap named in the GO, abort + quarantine on any
   schema/phase failure, checker admission run on the actual bytes
   before any further chunk — the Card A shape that caught both TD
   defects at a cost of 6 credits total.

Consequence if pursued: UX51, the Option A freeze, C1 comparability, and
the adopted S-C contract all stand unchanged. Cost: a new provider
evaluation cycle; until it passes, crypto stays 0/7 and the baseline as
specified cannot be computed (§5).

### Path B — Formally disclosed equities-only research-scope change

A new freeze record would supersede Option A for baseline purposes:
the corrected baseline becomes **44 equities × 751 sessions**, crypto
removed from baseline scope (crypto names remain untouched in the paused
forward cohort, which is a separate ledger).

Consequences, stated plainly:

- **Comparability break:** C1 and every frozen-baseline claim ran UX51
  including the 7 crypto pairs; an equities-only baseline is NOT C1-
  comparable and must never be reported as such. All downstream
  statistics (Holm family, fold materialization) re-derive from the
  reduced universe.
- **Universe-freeze consequence:** Option A (Mike's ruling, 2026-10-21,
  commit `2705c02`) is amended by a new governed freeze, not edited in
  place; the survivorship disclosure widens (a second, deliberate
  exclusion layered on the survivor-curated set).
- **What it buys:** the baseline becomes computable on the equity route
  already evidenced (4/44 full-span candidates in hand, SMCI/HO still
  separately NOT_EVALUABLE, 39 unattempted) without waiting on a crypto
  provider qualification.
- **Gate:** this path **requires a later explicit user (Mike) decision**.
  This package does not execute it, does not recommend it, and makes no
  scope change.

## 5. Coverage truth (updated, unchanged in substance)

- Equities: **4/44 full-span qualified candidates** (NVDA, TSLA, AAPL,
  SPY — HO exact, DEV exact after pinned-session exclusion of the vendor
  phantom rows; -02 adjudication `7823538`).
- **SMCI/HO: NOT_EVALUABLE_PROVIDER_VOLUME** (19 price-moving
  zero-volume bars, April 2024); SMCI remains a frozen UX51 member.
- **39/44 equities never attempted.**
- **Crypto: 0/7 qualified.** Twelve Data branch
  NOT_EVALUABLE_SCHEMA_AND_PHASE (§2); no alternate route evidenced (§3).
- The baseline **as specified** (frozen UX51 × 751 sessions) **cannot be
  computed** today: the equity HO leg has the SMCI hole and crypto has
  no qualified route. No baseline, performance, holdout, or shadow claim
  is made by this package. Pilot gate NOT PASSED; full capture and
  shadow launch remain HOLD.

## 6. What remains a governed decision (and whose)

- **Path A vs Path B (§4): Mike's decision.** Path B additionally
  requires his explicit scope-change ruling + a new freeze record.
- **Any new-provider pilot under Path A:** separate GO naming provider,
  cap, and abort conditions (Mike), after ChatGPT adjudication of this
  disposition.
- **Checker adoption (G4)** — the VBASIS calibration question from -02
  rides with it: ChatGPT adjudication, Mike's adoption GO. Unchanged.
- **Guard v3 adoption (G3), R1–R5 freeze:** unchanged, Mike's.
- Nothing in this package authorizes vendor calls, capture, baseline
  computation, or launch.

## Bounds kept

Offline only; zero vendor calls; program TD total unchanged at 24;
PAUSED production pins identical before/after (harness `ce7c902c…`,
PAUSE_NEW_ENTRIES present); no production/frozen-strategy change; no
holdout strategy use; no performance; no shadow launch. Prior packages
(-02 `7823538`, -03 `86aee48`, -04 `411ac2c`) and archives byte-untouched.
