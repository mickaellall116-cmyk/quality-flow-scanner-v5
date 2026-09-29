#!/usr/bin/env python3
"""Portfolio end-of-day snapshot for Mike's real book.

Read-only observability: reads ~/workspace/user/holdings.json, fetches
current daily prices via yfinance (stocks by ticker, crypto as XXX-USD),
and prints a JSON summary to stdout. Never places orders, never modifies
strategy files, never writes state. One yfinance batch download; crypto
tickers Yahoo fails to serve fall back to CoinGecko simple/price (day %
then = 24h change, flagged day_src="coingecko_24h"). Per-symbol failures
are recorded and skipped, never fatal.
"""

import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
HOLDINGS = os.path.expanduser("~/workspace/user/holdings.json")


def fmt_px(p):
    if p is None:
        return None
    if p >= 1:
        return round(p, 2)
    if p >= 0.01:
        return round(p, 4)
    return round(p, 8)


def load_holdings(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def yahoo_ticker(symbol, kind, underlying=None):
    if kind == "option":
        return underlying
    if kind == "crypto":
        return f"{symbol}-USD"
    return symbol


# CoinGecko ids for crypto Yahoo occasionally fails to serve (RBLX-style gaps).
COINGECKO_IDS = {"UNI": "uniswap", "SUI": "sui", "PEPE": "pepe"}


def coingecko_fallback(symbols):
    """{SYM: (price, day_pct_24h)} via CoinGecko simple/price. Read-only."""
    import urllib.request

    out = {}
    ids = {s: COINGECKO_IDS[s] for s in symbols if s in COINGECKO_IDS}
    if not ids:
        return out
    url = ("https://api.coingecko.com/api/v3/simple/price?ids="
           + ",".join(ids.values())
           + "&vs_currencies=usd&include_24hr_change=true")
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.load(resp)
    except Exception as exc:  # noqa: BLE001 — fallback is best-effort
        for s in ids:
            out[s] = (None, None, f"coingecko failed: {type(exc).__name__}")
        return out
    for sym, cgid in ids.items():
        d = data.get(cgid) or {}
        px, chg = d.get("usd"), d.get("usd_24h_change")
        if px is None:
            out[sym] = (None, None, "coingecko: no price")
        else:
            out[sym] = (float(px), round(float(chg), 2) if chg is not None else None, None)
    return out


def fetch_quotes(plan):
    """Return {yahoo_ticker: (price, day_pct, day_src, note)}.

    Primary: one yfinance batch (daily bars; day % = last vs prior close).
    Fallback: CoinGecko simple/price for crypto tickers Yahoo misses
    (day % = 24h change, noted in day_src).
    """
    import yfinance as yf

    tickers = sorted({yahoo_ticker(p["symbol"], p["kind"], p["underlying"]) for p in plan})
    crypto_of = {yahoo_ticker(p["symbol"], p["kind"], p["underlying"]): p["symbol"]
                 for p in plan if p["kind"] == "crypto"}
    out = {}
    try:
        df = yf.download(
            tickers, period="1mo", interval="1d",
            auto_adjust=False, progress=False, threads=True,
        )
        closes = df["Close"]
        for t in tickers:
            try:
                series = closes.dropna() if len(tickers) == 1 else closes[t].dropna()
                if len(series) == 0:
                    out[t] = (None, None, None, "yahoo: no price data")
                    continue
                price = float(series.iloc[-1])
                prev = float(series.iloc[-2]) if len(series) >= 2 else None
                day_pct = round((price - prev) / prev * 100, 2) if prev else None
                out[t] = (price, day_pct, "yahoo", None)
            except Exception as exc:  # noqa: BLE001 — fail closed per symbol
                out[t] = (None, None, None, f"yahoo: {type(exc).__name__}")
    except Exception as exc:  # noqa: BLE001 — whole-batch failure
        for t in tickers:
            out[t] = (None, None, None, f"yahoo batch failed: {type(exc).__name__}")

    missing = [crypto_of[t] for t in tickers
               if out[t][0] is None and t in crypto_of]
    if missing:
        for sym, (px, chg, note) in coingecko_fallback(missing).items():
            t = f"{sym}-USD"
            if px is not None:
                out[t] = (px, chg, "coingecko_24h", None)
            else:
                out[t] = (None, None, None, note or out[t][3])
    return out


def next_level_text(symbol, wallet, price, levels):
    """First rung above current price, plus stop info when set."""
    key = symbol if wallet != "second" or f"{symbol}2" not in levels else f"{symbol}2"
    lvl = levels.get(key)
    if not lvl:
        return None, None
    rungs = [r for r in lvl.get("rungs", []) if r.get("px") and price and r["px"] > price]
    txt = None
    dist = None
    if rungs:
        r = rungs[0]
        qty_txt = f"sell {r['qty']}" if r.get("qty") else "next"
        note_txt = f" ({r['note']})" if r.get("note") else ""
        txt = f"{qty_txt} @ ${r['px']}{note_txt}"
        dist = round((r["px"] - price) / price * 100, 1)
    stop = lvl.get("stop")
    if stop:
        stop_txt = f"stop ${stop}{' (' + lvl['stop_note'] + ')' if lvl.get('stop_note') else ''}"
        txt = f"{txt}; {stop_txt}" if txt else stop_txt
    return txt, dist


def main():
    try:
        h = load_holdings(sys.argv[1] if len(sys.argv) > 1 else HOLDINGS)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "errors": [f"holdings unreadable: {exc}"], "positions": []}))
        return

    levels = h.get("levels", {})
    plan = []  # (row_key, kind, symbol, wallet, qty, cost, underlying)

    def add(kind, symbol, qty, cost, wallet=None, underlying=None, extra=None):
        plan.append({"kind": kind, "symbol": symbol, "wallet": wallet,
                     "qty": qty, "cost": cost, "underlying": underlying,
                     "extra": extra or {}})

    for s in h.get("stocks", []):
        if s.get("kind") == "call":
            add("option", s["symbol"], s["qty"], s["cost"],
                underlying="BBAI", extra={"expiry": s.get("expiry"), "strike": s.get("strike")})
        else:
            add("stock", s["symbol"], s["qty"], s["cost"])
    for c in h.get("crypto_main", []):
        add("crypto", c["symbol"], c["qty"], c["cost"], wallet="main")
    for c in h.get("crypto_second", []):
        add("crypto", c["symbol"], c["qty"], None, wallet="second")

    quotes = fetch_quotes(plan)

    positions, errors = [], []
    for p in plan:
        t = yahoo_ticker(p["symbol"], p["kind"], p["underlying"])
        price, day_pct, day_src, err = quotes.get(t, (None, None, None, "ticker missing"))
        row = {"symbol": p["symbol"], "kind": p["kind"], "wallet": p["wallet"],
               "qty": p["qty"], "ticker": t}
        if err or price is None:
            row.update({"status": "DATA_UNAVAILABLE", "note": err or "no price"})
            errors.append(f"{p['symbol']}: {err or 'no price'}")
            positions.append(row)
            continue

        row.update({"status": "OK", "price": fmt_px(price), "day_pct": day_pct})
        if day_src and day_src != "yahoo":
            row["day_src"] = day_src

        if p["kind"] == "option":
            premium_total = round(p["qty"] * p["cost"], 2)
            row.update({"cost_note": f"{p['qty']}x ${p['cost']} premium",
                        "premium_total": premium_total,
                        "contract": f"{p['extra'].get('expiry')} ${p['extra'].get('strike')} call",
                        "underlying": p["underlying"]})
        else:
            cost, qty = p["cost"], p["qty"]
            value = price * qty
            row["value"] = round(value, 2)
            if cost is not None:
                pnl = (price - cost) * qty
                row.update({"cost": cost,
                            "pnl_usd": round(pnl, 2),
                            "pnl_pct": round((price - cost) / cost * 100, 1)})
            nxt, dist = next_level_text(p["symbol"], p["wallet"], price, levels)
            if nxt:
                row["next_level"] = nxt
                row["next_level_dist_pct"] = dist
        positions.append(row)

    summary = {
        "ok": True,
        "date": datetime.now(ET).strftime("%Y-%m-%d"),
        "generated_et": datetime.now(ET).strftime("%Y-%m-%d %H:%M"),
        "holdings_confirmed": h.get("confirmed"),
        "positions": positions,
        "errors": errors,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
