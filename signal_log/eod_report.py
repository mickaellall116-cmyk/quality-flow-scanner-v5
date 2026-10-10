#!/usr/bin/env python3
"""End-of-day "still in play?" check on V3.7 signal-log alerts.

Observability only: reads signal_log/v37_signals.jsonl, replays 4H bars after
each entry_yes=true signal from the last 10 calendar days, and prints a JSON
summary to stdout. Fill = next bar's open after the signal bar (system
convention). TP1 hit when a bar's high >= tp1; stop hit when a bar's close <
stop (V3.7's stop model); stop wins same-bar ties. Otherwise OPEN.
Does not modify strategy code, the watcher, or frozen files.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
JSONL_PATH = os.path.join(HERE, "v37_signals.jsonl")
ET = ZoneInfo("America/New_York")
LOOKBACK_DAYS = 10

# Same data convention as watcher.download_frame
sys.path.insert(0, os.path.dirname(HERE))
from signal_log.watcher import download_frame  # noqa: E402


def load_events():
    events = []
    if not os.path.exists(JSONL_PATH):
        return events
    with open(JSONL_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def bars_since_signal(df, signal_close):
    """4H bars after the signal bar, in chronological order, tz-aware ET."""
    idx = df.index.tz_convert(ET)
    return df[idx > signal_close]


def evaluate(event, df):
    """Return outcome dict for one signal; download failures handled by caller."""
    entry, stop, tp1 = event["entry_px"], event["stop_px"], event["tp1_px"]
    sig_close = datetime.fromisoformat(event["signal_bar_close"])
    later = bars_since_signal(df, sig_close)

    # Fill at next bar's open after the signal bar (system convention).
    fill_px = None
    walk = later.iloc[1:]  # empty DataFrame when no bars exist yet (avoids list crash)
    if len(later) >= 1:
        fill_px = float(later["Open"].iloc[0])

    outcome = {"status": "OPEN", "fill_px": fill_px}
    hit_bar = None
    for ts, bar in walk.iterrows():
        high, low, close = float(bar["High"]), float(bar["Low"]), float(bar["Close"])
        hit_tp1 = high >= tp1
        hit_stop = close < stop
        if hit_tp1 and hit_stop:
            # stop wins same-bar ties (system convention)
            outcome = {"status": "STOPPED", "status_note": "stop reached"}
            hit_bar = ts
            break
        if hit_stop:
            outcome = {"status": "STOPPED", "status_note": "stop reached"}
            hit_bar = ts
            break
        if hit_tp1:
            outcome = {"status": "TP1_HIT", "status_note": "target reached"}
            hit_bar = ts
            break

    outcome["hit_bar_et"] = hit_bar.strftime("%Y-%m-%d %H:%M") if hit_bar is not None else None
    n_walk = len(walk)
    if n_walk:
        last_close = float(walk["Close"].iloc[-1])
    else:
        last_close = None

    if outcome["status"] == "OPEN":
        if last_close is None:
            outcome["status_note"] = "no bars after fill yet"
        else:
            outcome["current_price"] = round(last_close, 2)
            ref = fill_px if fill_px is not None else entry
            outcome["pct_from_entry"] = round((last_close - entry) / entry * 100, 2)
            outcome["pct_from_fill"] = round((last_close - ref) / ref * 100, 2)
            outcome["pct_to_stop"] = round((stop - last_close) / last_close * 100, 2)
            outcome["pct_to_tp1"] = round((tp1 - last_close) / last_close * 100, 2)
            outcome["bars_since"] = n_walk
            # Simple chart facts: direction of last 3 bars, above/below entry,
            # nearest of stop/TP1.
            closes = walk["Close"].iloc[-4:].tolist()
            up = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i - 1])
            dn = sum(1 for i in range(1, len(closes)) if closes[i] < closes[i - 1])
            note_parts = [f"{up} of last {len(closes) - 1} bars up" if up >= dn
                          else f"{dn} of last {len(closes) - 1} bars down"]
            if last_close >= entry:
                note_parts.append(f"holding {abs(outcome['pct_from_entry'])}% above entry")
            else:
                note_parts.append(f"{abs(outcome['pct_from_entry'])}% below entry")
            dist_stop = abs(last_close - stop) / last_close
            dist_tp1 = abs(tp1 - last_close) / last_close
            if dist_stop <= dist_tp1:
                note_parts.append("closer to stop than target")
            else:
                note_parts.append("closer to target than stop")
            outcome["trend_note"] = "; ".join(note_parts)
            outcome["status_note"] = "still in play"
    else:
        outcome["bars_since"] = n_walk
    return outcome


def main():
    cutoff = datetime.now(ET) - timedelta(days=LOOKBACK_DAYS)
    events = [e for e in load_events()
              if e.get("entry_yes") and
              datetime.fromisoformat(e["signal_bar_close"]) >= cutoff]
    # newest first
    events.sort(key=lambda e: e["signal_bar_close"], reverse=True)

    # One download per symbol
    symbols = sorted({e["symbol"] for e in events})
    frames = {}
    for sym in symbols:
        try:
            df = download_frame(sym)
            frames[sym] = df if df is not None and not df.empty else None
        except Exception as exc:  # noqa: BLE001 — fail closed per symbol
            frames[sym] = exc

    signals = []
    for e in events:
        row = {
            "symbol": e["symbol"],
            "signal_time_et": datetime.fromisoformat(
                e["signal_bar_close"]).strftime("%Y-%m-%d %H:%M"),
            "entry": e["entry_px"],
            "stop": e["stop_px"],
            "tp1": e["tp1_px"],
        }
        df = frames[e["symbol"]]
        if isinstance(df, Exception) or df is None:
            err = str(df) if isinstance(df, Exception) else "download empty"
            row.update({"status": "UNKNOWN", "status_note": f"data unavailable: {err}",
                        "trend_note": "no data"})
        else:
            row.update(evaluate(e, df))
        signals.append(row)

    summary = {"date": date.today().isoformat(), "signals": signals}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
