# V3.7 Signal Log

Mike's "log of when the entry fired, by the time" for the tickers he watches
on TradingView with the Quality Flow System V3.7 indicator.

## How it works

1. `watcher.py` runs hourly (cron `v37-signal-log-watcher`).
2. For each symbol in `watchlist.txt`, it downloads 4H bars and evaluates the
   **canonical** `pine_buy_signal` (imported from `pine_backtest.py` — the same
   import path `pine_live/decompose.py` uses; no copied logic).
3. When the signal fires on a closed bar, one event is appended to
   `v37_signals.jsonl`. Dedup key: `(symbol, signal_bar_close)` — exactly one
   event per firing bar, ever. The seen-key set loaded from the JSONL is the
   watermark; `watermark.json` records per-symbol run times.
4. Entry/stop/TP1 reuse the canonical constants from `pine_backtest`
   (`SL_ATR = 1.5`, `TP_ATR = 2.0`): stop = signal close − ATR×1.5,
   TP1 = signal close + ATR×2.0. `entry_px` is the signal bar's close (the
   price when the signal fired — what the TradingView dashboard shows at
   signal time).
5. A newest-first snapshot `v37_signals.json` is published to GitHub
   (`signal_log/v37_signals.json` on main) via the Contents API, only when the
   events meaningfully changed (fingerprint comparison, same pattern as
   `v54_forward_harness.publish_snapshot`). The Master Scanner Streamlit app
   renders the "V3.7 Signal Log" section from that snapshot.

## Files

- `watchlist.txt` — one symbol per line; edit freely (hourly job picks it up).
- `watcher.py` — the hourly watcher + publisher. Run manually:
  `cd ~/workspace/quality-flow-scanner-v5 && python3 signal_log/watcher.py`
- `v37_signals.jsonl` — append-only source of truth (gitignored, local only).
- `v37_signals.json` — published snapshot (gitignored locally; lives on GitHub).
- `watermark.json` — last-run bookkeeping (gitignored).

## Constraints (do not break)

- Observability only: reads the frozen signal, never changes how it's computed.
- Does NOT touch `pine_backtest.py`, `pine_live/*`, V5.4 files, the `.pine`
  script, or the paper engine's 51-symbol universe and state.
