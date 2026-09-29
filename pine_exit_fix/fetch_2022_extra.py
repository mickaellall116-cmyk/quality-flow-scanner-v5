"""Best-effort extension of 2022 4H validation coverage via Dukascopy.

Reuses the v6_short_v2/data_2022.py pipeline verbatim in approach:
fetch hourly 2021-09-01 -> 2023-01-15, split-verify vs yfinance adjusted
daily closes, resample with scanner_rules.resample_closed_4h (read-only),
cache to pine_exit_fix/cache_2022/. Documents successes and failures.

Symbols skipped by design: META (not on Dukascopy), ARM (IPO Sep 2023 —
no 2022 data exists), ETFs IWM/SMH/ARKK/XLF (Dukascopy ETF coverage
uncertain), micro/small caps RKLB/ASTS/LUNR, minor cryptos DOGE/AVAX/LINK/XRP.

Local-only research. Nothing frozen touched.
"""

import os
import sys
import time
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "v6_short_v2"))

from data_2022 import fetch_hourly, split_adjust, sanity  # noqa: E402
import scanner_rules as sr  # noqa: E402  (read-only: resample_closed_4h)

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache_2022")
os.makedirs(CACHE, exist_ok=True)

# yfinance symbol -> dukascopy instrument (best guesses; failures documented)
SYMBOLS = {
    "SOFI": "SOFI.US/USD", "SMCI": "SMCI.US/USD", "COIN": "COIN.US/USD",
    "MSTR": "MSTR.US/USD", "MU": "MU.US/USD", "INTC": "INTC.US/USD",
    "LRCX": "LRCX.US/USD", "AMAT": "AMAT.US/USD", "QCOM": "QCOM.US/USD",
    "PYPL": "PYPL.US/USD", "SHOP": "SHOP.US/USD", "NIO": "NIO.US/USD",
    "MRNA": "MRNA.US/USD", "PFE": "PFE.US/USD", "F": "F.US/USD",
    "NET": "NET.US/USD", "SNOW": "SNOW.US/USD", "DDOG": "DDOG.US/USD",
    "CRWD": "CRWD.US/USD", "MELI": "MELI.US/USD", "NU": "NU.US/USD",
    "HOOD": "HOOD.US/USD", "APP": "APP.US/USD",
    "BTC-USD": "BTC/USD", "ETH-USD": "ETH/USD",
}

LOG = os.path.join(HERE, "cache_2022_fetch.log")


def log(msg):
    print(msg, flush=True)
    with open(LOG, "a") as f:
        f.write(msg + "\n")


def main():
    ok, failed = [], []
    for n, (yf_sym, duka) in enumerate(SYMBOLS.items()):
        out4 = os.path.join(CACHE, f"d4h_2022_{yf_sym}.pkl")
        if os.path.exists(out4):
            log(f"[{n+1}/{len(SYMBOLS)}] {yf_sym}: cached")
            ok.append(yf_sym)
            continue
        log(f"[{n+1}/{len(SYMBOLS)}] {yf_sym} <- {duka} ...")
        try:
            h = fetch_hourly(duka)
            h = split_adjust(h, yf_sym)
            b4 = sr.resample_closed_4h(h, yf_sym)
            b4.to_pickle(out4)
            s = sanity(b4, yf_sym)
            log(f"    {s}")
            ok.append(yf_sym) if not s.startswith("EMPTY") else failed.append(yf_sym)
        except Exception as e:
            log(f"    FAILED: {type(e).__name__}: {str(e)[:200]}")
            failed.append(yf_sym)
            traceback.print_exc()
        time.sleep(1.5)
    log(f"DONE. ok={len(ok)} failed={len(failed)}")
    log(f"ok: {ok}")
    log(f"failed: {failed}")


if __name__ == "__main__":
    main()
