"""Download 4H bars for the X2 cohort (199 symbols) using the same builder as the h4 cache.
Long pole: run in background. Incremental: skips symbols already cached.
"""
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import masterscanner_api as m
from v54_universe_x2 import UNIVERSE_X2

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(BASE, "cache_x2")
os.makedirs(CACHE, exist_ok=True)
LOG = os.path.join(BASE, "fetch_x2_log.json")

def main():
    log = {}
    if os.path.exists(LOG):
        log = json.load(open(LOG))
    ok, fail, skip = 0, 0, 0
    for n, sym in enumerate(UNIVERSE_X2):
        path = os.path.join(CACHE, f"h4_{sym}.pkl")
        if os.path.exists(path):
            skip += 1
            continue
        try:
            df = m.download_data(sym, "4h", "2y")
            time.sleep(0.4)
            if df is None or df.empty or len(df) < 100:
                log[sym] = {"ok": False, "reason": "empty/short", "bars": 0 if df is None else len(df)}
                fail += 1
            elif "Volume" not in df.columns or df["Volume"].isna().all():
                log[sym] = {"ok": False, "reason": "no_volume", "bars": len(df)}
                fail += 1
            else:
                df.to_pickle(path)
                log[sym] = {"ok": True, "bars": len(df),
                            "start": str(df.index[0]), "end": str(df.index[-1])}
                ok += 1
        except Exception as e:
            log[sym] = {"ok": False, "reason": f"exception: {type(e).__name__}"}
            fail += 1
            traceback.print_exc()
        if (n + 1) % 25 == 0:
            print(f"[{n+1}/{len(UNIVERSE_X2)}] ok={ok} fail={fail} skip={skip}", flush=True)
            with open(LOG, "w") as f:
                json.dump(log, f, indent=1, default=str)
    with open(LOG, "w") as f:
        json.dump(log, f, indent=1, default=str)
    print(f"DONE ok={ok} fail={fail} skip={skip} total={len(UNIVERSE_X2)}", flush=True)

if __name__ == "__main__":
    main()
