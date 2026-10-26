#!/usr/bin/env python3
"""Tier 3 mechanical symbol selection — implements TIER3_RULE_FROZEN.md v1.0 exactly.

Outcome-blind by construction: reads listing metadata (NASDAQ Trader symbol
directories + NASDAQ screener IPO years) and CURRENT liquidity metadata
(Yahoo daily bars, completed sessions 2026-09-01..2026-10-25) for candidate
symbols only. Never touches the sealed holdout window, never computes a
return, never fetches anything for an excluded (UX51/X2) symbol.

Output (tier3_list.json) is a pure function of the archived inputs: no
wall-clock fields, sorted keys, fixed rounding — two runs on the same
inputs must be byte-identical.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "sources"
OUT = HERE / "tier3_list.json"

RULE_VERSION = "TIER3_RULE_FROZEN v1.0 (2026-10-26)"
SOURCE_DATE = "2026-10-26"
ADV_CUTOFF = 25_000_000.0
MIN_LAST_CLOSE = 5.00
LIST_SIZE = 12
ADV_WINDOW_BARS = 20
FETCH_START = "2026-09-01"
FETCH_END = "2026-10-26"  # yfinance end is exclusive -> last bar 2026-10-23 (completed session)

NAME_EXCLUSIONS = [
    re.compile(p, re.IGNORECASE)
    for p in (r"%", r"\bPreferred\b", r"\bPreference\b", r"\bUnits?\b",
              r"\bRights?\b", r"\bWarrants?\b", r"\bNotes?\b")
]
SYMBOL_OK = re.compile(r"^[A-Z]{1,6}$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_pipe_file(path: Path):
    rows = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header = lines[0].split("|")
    for line in lines[1:]:
        if not line.strip() or line.startswith("File Creation Time"):
            continue
        parts = line.split("|")
        if len(parts) != len(header):
            continue
        rows.append(dict(zip(header, parts)))
    return rows


def main() -> int:
    stage = {}

    # ---- Steps 1-3: listed, exchange, real security -------------------------
    nas_rows = parse_pipe_file(SRC / "nasdaqlisted.txt")
    oth_rows = parse_pipe_file(SRC / "otherlisted.txt")

    universe = {}  # symbol -> security name
    for r in nas_rows:
        sym = r["Symbol"].strip()
        if r.get("Test Issue") == "N" and r.get("ETF") == "N" and r.get("NextShares") == "N":
            universe[sym] = r["Security Name"]
    stage["s1_nasdaq_real_securities"] = len(universe)
    n_oth = 0
    for r in oth_rows:
        sym = r["NASDAQ Symbol"].strip()
        if r.get("Exchange") in ("N", "A") and r.get("Test Issue") == "N" and r.get("ETF") == "N":
            if sym not in universe:
                universe[sym] = r["Security Name"]
                n_oth += 1
    stage["s2_otherlisted_added"] = n_oth
    stage["after_steps_1_3"] = len(universe)

    # ---- Step 4: common stock only ------------------------------------------
    universe = {s: n for s, n in universe.items()
                if not any(p.search(n) for p in NAME_EXCLUSIONS)}
    stage["after_step_4_common_stock"] = len(universe)

    # ---- Step 5: plain ticker ------------------------------------------------
    universe = {s: n for s, n in universe.items() if SYMBOL_OK.match(s)}
    stage["after_step_5_plain_ticker"] = len(universe)

    # ---- Step 6: never in any prior study ------------------------------------
    excl = json.loads((HERE / "exclusion_universes.json").read_text())
    excluded = set(excl["UX51"]) | set(excl["X2"])
    universe = {s: n for s, n in universe.items() if s not in excluded}
    stage["after_step_6_prior_study_exclusion"] = len(universe)

    # ---- Step 7: listed before the holdout window (IPO year <= 2023) ---------
    screener = json.loads((SRC / "nasdaq_screener_raw.json").read_text())
    ipo_year = {}
    for row in screener["data"]["rows"]:
        y = str(row.get("ipoyear") or "").strip()
        if y.isdigit():
            ipo_year[row["symbol"].strip()] = int(y)
    universe = {s: n for s, n in universe.items()
                if s in ipo_year and ipo_year[s] <= 2023}
    stage["after_step_7_ipo_year"] = len(universe)

    candidates = sorted(universe)
    print("stage counts:", json.dumps(stage, indent=1), flush=True)
    print(f"candidates for liquidity fetch: {len(candidates)}", flush=True)

    # ---- Step 8: liquidity (current metadata only, candidates only) ----------
    import yfinance as yf

    liquidity = {}  # symbol -> (adv20, last_close, n_bars)

    def fetch_into(symbols):
        """One transport pass. Eligibility logic is unchanged: a symbol lands
        in `liquidity` only with >= ADV_WINDOW_BARS valid bars. Transport
        robustness fix (v1.1, disclosed in REPRODUCIBILITY_RECORD.md): the
        caller retries symbols that produced no result, because the free
        feed drops requests transiently; a symbol that still yields no
        result after the retry is ineligible (fail-closed), per the rule."""
        CHUNK = 200
        for i in range(0, len(symbols), CHUNK):
            chunk = symbols[i:i + CHUNK]
            try:
                data = yf.download(chunk, start=FETCH_START, end=FETCH_END,
                                   auto_adjust=False, group_by="ticker",
                                   threads=True, progress=False)
            except Exception:
                continue
            for sym in chunk:
                try:
                    df = data[sym] if len(chunk) > 1 else data
                    df = df.dropna(subset=["Close", "Volume"])
                    df = df[df["Volume"] > 0]
                    if len(df) < ADV_WINDOW_BARS:
                        continue
                    tail = df.tail(ADV_WINDOW_BARS)
                    adv = float((tail["Close"] * tail["Volume"]).mean())
                    last_close = float(tail["Close"].iloc[-1])
                    liquidity[sym] = (round(adv, 2), round(last_close, 4), int(len(tail)))
                except Exception:
                    continue
            print(f"  fetched pass {min(i + CHUNK, len(symbols))}/{len(symbols)}", flush=True)

    fetch_into(candidates)
    missing = [s for s in candidates if s not in liquidity]
    print(f"retry pass for {len(missing)} symbols with no result", flush=True)
    fetch_into(missing)

    stage["fetch_failed_or_short"] = len(candidates) - len(liquidity)
    eligible = {s: v for s, v in liquidity.items()
                if v[0] >= ADV_CUTOFF and v[1] >= MIN_LAST_CLOSE}
    stage["after_step_8_liquidity"] = len(eligible)

    # ---- Ranking: ADV20 desc, symbol asc; take top LIST_SIZE ------------------
    ranked = sorted(eligible.items(), key=lambda kv: (-kv[1][0], kv[0]))
    selected = ranked[:LIST_SIZE]

    result = {
        "rule_version": RULE_VERSION,
        "source_date": SOURCE_DATE,
        "source_hashes": {
            "nasdaqlisted.txt": sha256(SRC / "nasdaqlisted.txt"),
            "otherlisted.txt": sha256(SRC / "otherlisted.txt"),
            "nasdaq_screener_raw.json": sha256(SRC / "nasdaq_screener_raw.json"),
            "exclusion_universes.json": sha256(HERE / "exclusion_universes.json"),
        },
        "parameters": {
            "adv20_cutoff_usd": ADV_CUTOFF,
            "min_last_close_usd": MIN_LAST_CLOSE,
            "list_size": LIST_SIZE,
            "adv_window_bars": ADV_WINDOW_BARS,
            "liquidity_window": "completed sessions 2026-09-01..2026-10-25 (last 20 valid bars)",
            "ipo_year_max": 2023,
        },
        "stage_counts": stage,
        "tier3_list": [
            {"rank": i + 1, "symbol": sym, "adv20_usd": adv,
             "last_close_usd": lc, "bars_used": nb}
            for i, (sym, (adv, lc, nb)) in enumerate(selected)
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=False) + "\n")
    print(f"wrote {OUT} sha256={sha256(OUT)}")
    print("selected:", [e["symbol"] for e in result["tier3_list"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
