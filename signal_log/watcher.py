#!/usr/bin/env python3
"""V3.7 watchlist signal watcher — observability only.

Hourly job: for each symbol in watchlist.txt, download recent 4H bars and
evaluate the CANONICAL buySignal. When it fires on a closed bar, append one
event to the append-only log ``v37_signals.jsonl`` and publish a newest-first
snapshot (``signal_log/v37_signals.json``) to GitHub when the meaningful
content changed.

Hard rules (do not weaken):
  * The decision ALWAYS comes from ``pine_backtest.pine_buy_signal`` via the
    same import path ``pine_live/decompose.py`` uses. No copied logic.
  * Entry/stop/TP1 reuse the canonical constants (SL_ATR / TP_ATR) from
    ``pine_backtest`` — no invented formulas.
  * Nothing here modifies pine_backtest.py, pine_live/*, V5.4 files, the
    Quality-Flow-System-V3.7.pine script, or the paper engine's universe /
    state. This module only READS the frozen signal.
  * Fail-closed per symbol: a download or evaluation failure skips that
    symbol this wake-up and is reported; it never kills the run.

Event schema (JSONL, one object per line):
  detected_at      UTC ISO timestamp of this wake-up
  signal_bar_close ISO timestamp (with offset) of the 4H bar that fired
  symbol           e.g. "QQQ"
  timeframe        "4H"
  entry_px         signal bar close (price when the signal fired — what the
                   TradingView dashboard shows at signal time)
  stop_px          entry_px - ATR * SL_ATR  (canonical, from pine_backtest)
  tp1_px           entry_px + ATR * TP_ATR  (canonical, from pine_backtest)
  score            0-5 integer trend score (via pine_live.decompose)
  adx              ADX value on the signal bar
  source           "watchlist"
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Canonical imports — the SAME import path pine_live/decompose.py uses.
from pine_backtest import (  # noqa: E402
    SL_ATR,
    TP_ATR,
    WARMUP,
    add_pine_indicators,
    pine_buy_signal,
)
from pine_live.decompose import decompose_signal  # noqa: E402
from scanner_rules import bar_close_at  # noqa: E402

SIGNAL_DIR = os.path.join(REPO_ROOT, "signal_log")
WATCHLIST_PATH = os.path.join(SIGNAL_DIR, "watchlist.txt")
JSONL_PATH = os.path.join(SIGNAL_DIR, "v37_signals.jsonl")
SNAPSHOT_PATH = os.path.join(SIGNAL_DIR, "v37_signals.json")
WATERMARK_PATH = os.path.join(SIGNAL_DIR, "watermark.json")

GH_OWNER = "mickaellall116-cmyk"
GH_REPO = "quality-flow-scanner-v5"
GH_BRANCH = "main"
GH_CLI = os.path.expanduser("~/workspace/skills/github/bin/gh_contents.py")
REMOTE_PATH = "signal_log/v37_signals.json"

LOOKBACK_BARS = 3    # steady-state: re-check the last 3 closed bars (catch-up)
BACKFILL_BARS = 60   # first run only (empty log): backfill recent history
SNAPSHOT_CAP = 200   # newest-first cap for the published snapshot
DOWNLOAD_PERIOD = "2y"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_watchlist() -> list[str]:
    syms: list[str] = []
    with open(WATCHLIST_PATH, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip().upper()
            if s and not s.startswith("#"):
                syms.append(s)
    return syms


def load_seen_keys() -> set[tuple[str, str]]:
    """Dedup watermark: the set of (symbol, signal_bar_close) already logged,
    loaded from the append-only JSONL (the source of truth)."""
    seen: set[tuple[str, str]] = set()
    if not os.path.exists(JSONL_PATH):
        return seen
    with open(JSONL_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                seen.add((str(e.get("symbol")), str(e.get("signal_bar_close"))))
            except Exception:
                continue
    return seen


def download_frame(symbol: str):
    """Same download path the paper engine uses (masterscanner_api, 4H)."""
    from masterscanner_api import download_data

    return download_data(symbol, "4h", DOWNLOAD_PERIOD)


def evaluate_symbol(symbol: str, lookback: int, seen: set[tuple[str, str]]):
    """Return (events, warnings) for one symbol. Fail-closed: raises nothing."""
    warnings: list[str] = []
    df = download_frame(symbol)
    if df is None or df.empty or len(df) < WARMUP + 2:
        return [], [f"{symbol}: insufficient data ({0 if df is None else len(df)} bars)"]
    df = add_pine_indicators(df)
    n = len(df)
    lo = max(WARMUP, n - lookback)
    events: list[dict] = []
    for i in range(lo, n):
        try:
            fired = bool(pine_buy_signal(df, i))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{symbol}: eval failed at bar {i}: {type(exc).__name__}")
            continue
        if not fired:
            continue
        # Cross-check the mirror against the canonical decision.
        try:
            d = decompose_signal(df, i)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{symbol}: decompose failed at bar {i}: {type(exc).__name__}")
            continue
        if bool(d["decision"]) != bool(d["reference_decision"]):
            warnings.append(
                f"{symbol}: decompose/canonical mismatch at bar {i} — skipped")
            continue
        r = df.iloc[i]
        bar_close = bar_close_at(df.index[i], symbol)
        key = (symbol, bar_close.isoformat())
        if key in seen:
            continue
        close = float(r["Close"])
        atr = float(r["atr"])
        adx = float(r["adx"])
        events.append({
            "detected_at": _utcnow_iso(),
            "signal_bar_close": bar_close.isoformat(),
            "symbol": symbol,
            "timeframe": "4H",
            "entry_px": round(close, 2),
            "stop_px": round(close - atr * SL_ATR, 2),
            "tp1_px": round(close + atr * TP_ATR, 2),
            "score": int(d["trend_score"]),
            "adx": round(adx, 1),
            "source": "watchlist",
        })
        seen.add(key)
    return events, warnings


def append_events(events: list[dict]) -> None:
    if not events:
        return
    with open(JSONL_PATH, "a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")


def load_all_events() -> list[dict]:
    out: list[dict] = []
    if not os.path.exists(JSONL_PATH):
        return out
    with open(JSONL_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    return out


def build_snapshot(events: list[dict], watchlist: list[str]) -> dict:
    newest = sorted(events, key=lambda e: str(e.get("signal_bar_close", "")),
                    reverse=True)[:SNAPSHOT_CAP]
    return {
        "updated_at": _utcnow_iso(),
        "timeframe": "4H",
        "source": "v37-watchlist-watcher",
        "watchlist": watchlist,
        "event_count": len(newest),
        "events": newest,
    }


def _fingerprint(events: list[dict]) -> str:
    return hashlib.sha256(
        json.dumps(events, sort_keys=True).encode("utf-8")).hexdigest()


def _gh_cli(*args: str) -> dict:
    r = subprocess.run([sys.executable, GH_CLI, *args],
                       capture_output=True, text=True, timeout=120)
    try:
        return json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:
        return {"ok": False, "error": f"cli failed: {(r.stderr or r.stdout)[-300:]}"}


def publish_snapshot(snapshot: dict) -> dict:
    """Publish signal_log/v37_signals.json via the GitHub Contents API.

    Pushes only when the meaningful content (events) changed — volatile
    timestamps alone don't trigger a commit. Mirrors the fingerprint approach
    of v54_forward_harness.publish_snapshot.
    """
    with open(SNAPSHOT_PATH, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2)
    cur = _fingerprint(snapshot["events"])
    got = _gh_cli("get", "--owner", GH_OWNER, "--repo", GH_REPO,
                  "--branch", GH_BRANCH, "--remote", REMOTE_PATH)
    if got.get("ok"):
        try:
            old = _fingerprint(json.loads(got["content"])["events"])
        except Exception:
            old = None
        if old == cur:
            return {"ok": True, "pushed": False, "note": "up to date"}
    elif got.get("error") != "not found":
        return {"ok": False, "step": "get-remote",
                "error": str(got.get("error"))}
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    put = _gh_cli("put", "--owner", GH_OWNER, "--repo", GH_REPO,
                  "--branch", GH_BRANCH, "--local", SNAPSHOT_PATH,
                  "--remote", REMOTE_PATH,
                  "--message", f"V3.7 signal log snapshot {stamp}")
    if not put.get("ok"):
        return {"ok": False, "step": "put", "error": str(put.get("error"))}
    return {"ok": True, "pushed": True, "commit": put.get("commit")}


def save_watermark(symbols: dict[str, str]) -> None:
    with open(WATERMARK_PATH, "w", encoding="utf-8") as fh:
        json.dump({"last_run": _utcnow_iso(), "symbols": symbols}, fh, indent=2)


def main() -> dict:
    watchlist = load_watchlist()
    if not watchlist:
        return {"ok": False, "error": "watchlist is empty"}
    seen = load_seen_keys()
    first_run = not os.path.exists(JSONL_PATH) or not seen
    lookback = BACKFILL_BARS if first_run else LOOKBACK_BARS

    new_events: list[dict] = []
    failures: list[str] = []
    warnings: list[str] = []
    watermark: dict[str, str] = {}
    for sym in watchlist:
        try:
            events, warns = evaluate_symbol(sym, lookback, seen)
        except Exception as exc:  # noqa: BLE001 — fail closed per symbol
            failures.append(f"{sym}: {type(exc).__name__}: {exc}")
            continue
        new_events.extend(events)
        warnings.extend(warns)
        watermark[sym] = _utcnow_iso()

    append_events(new_events)
    save_watermark(watermark)
    snapshot = build_snapshot(load_all_events(), watchlist)
    pub = publish_snapshot(snapshot)

    return {
        "ok": True,
        "symbols": watchlist,
        "lookback_bars": lookback,
        "new_events": len(new_events),
        "events": new_events,
        "failures": failures,
        "warnings": warnings,
        "published": pub,
    }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result.get("ok") else 1)
