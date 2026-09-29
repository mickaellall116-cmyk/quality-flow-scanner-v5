# SLICE 1 — Live V3.6 path skeleton + decision packets

**Status:** built 2026-09-18. All 13 tests pass. Paper-only.
**Scope (Mike's commission):** live path skeleton + decision packets. Zero
trading/alerting side effects.

## What was built (`pine_live/`)

| File | Purpose |
|---|---|
| `live_path.py` | `evaluate_live(symbol)` (download → assert → decide → packet) and `evaluate_frame(...)` (same, on a supplied 4H frame). Calls `download_data`, `add_pine_indicators`, `pine_buy_signal`, `bar_close_at` **by import** — nothing reimplemented. |
| `assertions.py` | Input gates: tz-aware index (naive rejected), monotonic/unique, OHLCV present, no NaN fill, reference session-grid conformance, intraday chain-consistency via `bar_close_at`, ≥215-bar warmup (refuse + log refusal otherwise), forming-bar exclusion when `now` is given. |
| `decompose.py` | Read-only explanation of the Hybrid formula exposing sub-condition booleans for the packet. Constants imported from `pine_backtest`; pinned to the reference by an exhaustive test (below). The **decision** always comes from `pine_buy_signal`. |
| `packets.py` | Append-only JSONL `PacketLog` (fsync per write, never rewritten) + content-hashed bar snapshots (`sha256`; existing snapshot with different content raises instead of overwriting). |
| `replay.py` | `replay_packet(packet)`: load snapshot (hash-verified) → re-run `add_pine_indicators` + `pine_buy_signal` → diff decision and indicator values (1e-10) against the packet. CLI included. |
| `tests/test_slice1.py` | 13 tests (see below). |

No existing file was modified. No ranking, sector cap, slot state,
duplicate suppression, alert delivery, or trading exists anywhere in this
slice.

## Milestone proof (Mike's acceptance criterion)

> One live ticker/bar replayed from its packet reproduces the exact same
> V3.6 decision.

- **Live:** `evaluate_live('NVDA')` downloaded fresh 4H bars (254 bars,
  warmup OK), evaluated the latest closed bar **2026-09-17 13:30 ET**
  (Friday's 09:30 bar correctly excluded as still forming), decided
  **no_signal**. Packet written to `pine_live/packets/decisions.jsonl`,
  snapshot `pine_live/snapshots/NVDA_2026m09m17T133000m0400.json`.
- **Replay:** `replay_packet` on that packet → `exact: True`,
  `decision_match: True`. Indicator values match to 1e-10.
- **Signal case:** cached NVDA bar 2026-09-04 09:30 (a bar where V3.6 fired)
  evaluated via `evaluate_frame` → `signal`; replay → `exact: True`.
- **Tamper case:** appending one byte to a snapshot makes replay raise
  (hash mismatch) instead of silently replaying.

## Test summary (13/13 green)

- `test_decompose_matches_reference_all_symbols` — the explain-mirror agrees
  with `pine_buy_signal` on **every bar ≥ WARMUP across all 52 cached
  symbols** (~40k bars). If the reference formula ever changes, this fails
  loudly instead of drifting.
- `test_evaluate_frame_latest_bar_matches_reference` — packet decision ==
  reference on the latest bar (NVDA, BTC-USD, SPY).
- Replay tests (no-signal bar, known signal bar, tampered snapshot).
- Assertion tests (naive timestamps refused, <215 bars refused with logged
  refusal, off-grid bars raise, forming bar refused).
- Packet schema test (all Part-B slice-1 fields, tz-aware ISOs, engine
  version = git SHA + sha256 of the three reference files).
- No-side-effect tests: static scan (no alert/trade/network imports in
  `pine_live`; only `download_data` via the reference module) + runtime
  test (evaluation writes only into the caller-supplied dirs).
- `test_live_smoke_optional` — real download → packet → replay, skipped
  gracefully if offline.

## Import blockers

**None.** All canonical functions import cleanly with no import-time side
effects: `pine_backtest` (guarded `main()`), `scanner_rules` (pure),
`masterscanner_api.download_data` (module also builds an inert FastAPI app;
no I/O on import). No code was copied.

## Notable discovery during build

The reference `resample_closed_4h` (origin=`start_day`, offset=`9h30min` on a
tz-aware index) shifts bar labels by one hour across the fall DST transition
(08:30/12:30 ET bars the week after). An idealized "bars must start at
09:30/13:30" assertion **falsely rejected 332 genuine NVDA reference bars**.
The assertion now pins to the reference's actual grid
{(8,30),(9,30),(12,30),(13,30)} plus intraday chain-consistency via the
reference's own `bar_close_at`. Lesson recorded: assertions must test
conformance with the reference implementation, not with an idealized model
of it.

## Explicitly NOT built yet (next slices)

- rs_top2 ranking (needs live SPY daily feed; research cache is static)
- E1 sector cap (frozen `SECTOR` map; nothing consumes it live)
- Position-slot accounting / 5-position cap / 5% risk gate
- Duplicate-signal suppression
- Alert delivery (no alerting code exists; the module cannot send anything)
- Any trading, order, or broker integration
- The Part-B reconciliation job (daily live-vs-reference diff)

Each of those layers on top of this slice's packet format without changing it.
