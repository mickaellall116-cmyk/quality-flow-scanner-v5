# TD Venue Identity — Adjudication Support for the -09 r2 HOLD

**Task:** QF-TD-VENUE-IDENTITY-ADJUDICATION-20261014-10 r1 — READ-ONLY.
No vendor calls (zero network calls of any kind). No code or manifest
changes; recommendation only.
**Subject:** QF-TD-FIRST-LIVE-SCREEN-20261014-09 r2 outcome —
**HOLD: venue binding mismatch for REQ-P1H-01** (result commit
`4333f06`; screen dispatched 2026-10-14 09:38:19 EDT, HTTP 200,
status ok, 1 credit).

## Verdict

The HOLD was caused by exactly **one field**: `mic_code`.
The manifest pins **XNAS**; the vendor returned **XNGS**.

- **Classification: (ii) vendor naming/semantics variant of the same
  venue**, with (i) as its flip side — the manifest pin is wrong
  about what the vendor returns. XNAS is the ISO 10383 *operating*
  (parent) MIC for the NASDAQ Stock Market; XNGS is the ISO 10383
  *segment* MIC for the Nasdaq Global Select Market, which is
  AAPL's listing segment. Twelve Data returns the **segment MIC** in
  `meta.mic_code`. The data is from the venue the manifest declares —
  exchange, currency, timezone, symbol, and interval all bind.
- **Not (iv):** no evidence of a genuine venue mismatch.
- **Not primarily (iii):** the collector's exact-equality binding is
  its designed, adjudicated contract; its frozen doctrine routes
  identity corrections through a revised manifest.
- **Recommendation: manifest V2 venue pin amendment** (details
  below). No collector change. Accept-and-document alone cannot
  work — the gate is mechanical and will HOLD every NASDAQ receipt
  regardless of documentation.

## 1. Payload verification (before any read)

| Item | Value |
|---|---|
| Path | `research_notes/twelve_data_stage0/snapshots/acquisition_state/receipts/REQ-P1H-01.rejected.bin` (git-ignored private store; read-only access) |
| Expected sha256 | `c47bf899422e4585bcd37055c0e9788c96697b6b47482133e4675bf5cb8dbc18` |
| Actual sha256 | `c47bf899422e4585bcd37055c0e9788c96697b6b47482133e4675bf5cb8dbc18` |
| Bytes | 117,985 |
| Match | **YES** — proceeded only after this verified |

Pins re-verified for this adjudication: collector
`td_min_collector.py` sha256 `bd003c3c…` (candidate `7ec0f0e`,
path `research_notes/td_lifecycle_repair_candidate/td_min_collector.py`);
manifest `acquisition_manifest_v1.json` sha256 `66a31e10…`.

## 2. Venue fields: expected vs actual

Response `meta` (the only payload content extracted; no bar data was
copied, quoted, or stored anywhere by this task):

| Field | Manifest pin (REQ-P1H-01) | Vendor meta | Bind |
|---|---|---|---|
| `exchange` | `NASDAQ` | `NASDAQ` | ✓ |
| `mic_code` | `XNAS` | **`XNGS`** | **✗** |
| `currency` | `USD` | `USD` | ✓ |
| `symbol` | `AAPL` | `AAPL` | ✓ (earlier gate) |
| `interval` | `1h` | `1h` | ✓ (earlier gate) |
| `exchange_timezone` | (request tz `America/New_York`) | `America/New_York` | consistent (not part of `venue_identity`) |
| `type` | (not pinned) | `Common Stock` | n/a |

## 3. The exact failed comparison

Collector `td_min_collector.py` (pin `bd003c3c…`), live receive path,
lines 417–419:

```python
if any(meta.get(k) != v for k, v in req["venue_identity"].items()):
    self._preserve_rejected(rid, body)
    return f"venue binding mismatch for {rid}"
```

The identical check exists on the receipt-revalidation path, lines
308–310:

```python
venue = req["venue_identity"]
if any(meta.get(k) != v for k, v in venue.items()):
    return False, "receipt venue binding mismatch"
```

Semantics: exact string equality over **every** key in the request's
`venue_identity` dict (`exchange`, `mic_code`, `currency`). One
differing field fails the binding. Here: `meta["mic_code"] == "XNGS"
!= "XNAS"` — the sole failure; `exchange` and `currency` are equal.

## 4. Classification, with evidence

- The manifest's `venue_identity` was constructed, per
  `TD_ACQUISITION_ADAPTER_PREFLIGHT_20261013.md` §1, from "the
  frozen plan §1 + ISO 10383" — i.e., the operating MIC was pinned
  from reference data, never from an observed vendor response (no
  live receipt existed before -09 r2).
- The vendor's response meta carries `mic_code: XNGS`. Under ISO
  10383, XNAS is the operating MIC of the NASDAQ Stock Market and
  XNGS is a segment MIC of that same market (Nasdaq Global Select
  Market). AAPL is a Global Select listing, so the vendor's value is
  the *more specific, correct* identity of the same venue — a
  granularity/semantics variant, not a different venue.
- All other identity evidence agrees: `exchange: NASDAQ`,
  `exchange_timezone: America/New_York`, `currency: USD`, symbol and
  interval bound at the prior gate, status ok. A genuine venue
  mismatch (iv) would be expected to diverge on more than the MIC
  granularity.
- The preflight anticipated this exact failure class: protocol **P4**
  (check receipt meta against the pin; mismatch HOLDs) and residual
  **§6.3** (for DRAM: vendor venue strings not exemplified in docs;
  "The pin uses the frozen plan's exchange + ISO 10383 MIC; a
  mismatch fails closed at that receipt … manifest revision
  required"). The NASDAQ operating-vs-segment MIC case is the same
  construction and the same pre-declared remedy.

## 5. Blast radius (manifest V1, 51 requests)

| Pinned triple | Requests | Symbols |
|---|---|---|
| NASDAQ / XNAS / USD | **39** | AAPL, AMD, GOOGL, HOOD, META, MSFT, NVDA, ONDS, PLTR, QQQ, SMCI, SOFI, SPCX, TSLA (14) |
| NYSE / XNYS / USD | 10 | ANET, BBAI, NIO, RKLB, TWTR (5) |
| Cboe BZX / BATS / USD | 2 | DRAM (1) |

- **All 39 NASDAQ-pinned requests would fail this gate in kind.**
  The vendor returns each symbol's listing-segment MIC
  (XNGS / XNMS / XNCM by tier), never the operating MIC XNAS. The
  exact returned value differs per symbol and is empirically
  established **only for AAPL (XNGS)**; no in-repo evidence pins the
  segment MIC of the other 13 NASDAQ symbols.
- **NYSE (10):** XNYS is both the operating MIC and the principal
  segment MIC for NYSE, so these pins may bind as-is — unproven; no
  NYSE receipt exists.
- **Cboe BZX / DRAM (2):** unresolved by this evidence; the
  preflight (§6.3) already flagged the DRAM vendor strings as
  unverifiable from public docs, with the same fail-closed /
  manifest-revision consequence pre-declared.

## 6. What the response would have contained (counts/timestamps only)

Had the venue gate passed, the receipt held: status `ok`, **910
values**, first bar datetime **2026-04-01 09:30:00**, last bar
datetime **2026-10-06 15:30:00**, bar fields
`datetime/open/high/low/close/volume`. 910 is under `outputsize`
5000 and under the manifest's `one_response_bound_bars` 1323; both
timestamps sit inside the requested window. **Bar validation and
completeness never ran and are not adjudicated here** — this records
structure only, not acceptance of the bars.

## 7. Recommendation (no implementation under this task)

**Manifest V2 venue pin amendment** — the minimal correction path,
and the collector's own frozen correction channel ("identity
corrections are effected by a revised manifest, never by in-run
continuation"):

1. V2 corrects `mic_code` per symbol to the vendor-returned segment
   MIC. Evidence directly supports **AAPL → XNGS** only.
2. The other 13 NASDAQ symbols' segment MICs must **not be guessed
   into V2**. They need an evidenced source under separately
   authorized scope, or per-symbol first-receipt adjudication under
   the same fail-closed rule (each such receipt costs its credit
   and HOLDs if the pin is wrong — a cost/benefit call for Mike and
   ChatGPT, not assumed here).
3. **Not recommended as primary:** a collector binding-rule
   correction (e.g., accept a MIC family). It edits the pinned,
   adjudicated collector (`f64d12f` content; candidate `7ec0f0e`
   SCOPED PASS) and weakens a deliberately exact identity gate to
   fix what is, on the evidence, a declaration error.
4. **Insufficient alone:** accept-and-document. The gate is
   mechanical; documentation does not stop the HOLD.

**Frozen/adjudicated touch flags:**
- V2 would **supersede, not edit**, manifest V1 (pin `66a31e10…`) —
  the same documented path by which V1 superseded R3. V1 was
  adjudicated within the accepted preflight; supersession requires
  re-adjudication of V2.
- The recommendation touches **nothing** in the collector, adapter,
  or driver (all pinned and adjudicated).
- Venue identity is an acquisition-manifest declaration, not a
  frozen strategy artifact; preflight P4/§6.3 pre-declared this
  failure mode and its remedy.

**A corrected re-screen would need:** manifest V2 (new pin,
re-adjudicated) → a candidate bound to V2 → reconciliation of the
existing HOLD state dir in the private store under the collector's
started-state rules (REQ-P1H-01 sits at attempts 1, status HOLD) →
**fresh authorization from Mike** for the new credit. None of that
is authorized by this task.

## Scope honored

Zero network calls; payload accessed read-only after hash
verification; meta block only — no bar values extracted, quoted, or
stored; no changes to collector, manifest, adapter, driver, ledger,
or any production/frozen file. Deliverables: this report +
`research_notes/td_venue_identity_adjudication_evidence_20261014/adjudication_evidence.json`.
Secret-isolation scan over both deliverables: **CLEAN** (no
credential, surrogate, `apikey` value, or bar data present; payload
hash/bytes and meta values only).

**Status: adjudication support COMPLETE. Live acquisition remains
HOLD. The venue discrepancy is a manifest pin granularity error
(XNAS operating MIC pinned; XNGS segment MIC returned) — correction
path is a manifest V2 amendment, pending ChatGPT adjudication and
Mike's decisions.**
