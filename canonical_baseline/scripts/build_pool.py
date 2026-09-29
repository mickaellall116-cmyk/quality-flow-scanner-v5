"""Step 1: build the PIT-safe candidate pool (union of symbols referenced in repo)."""
import re, os, glob, json, importlib.util, sys

REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
OUT = os.path.join(REPO, "canonical_baseline")

pool = {}  # sym -> list of sources
def add(syms, src):
    for s in syms:
        s = s.strip().upper()
        if not s: continue
        pool.setdefault(s, []).append(src)

spec = importlib.util.spec_from_file_location("x2", os.path.join(REPO, "v54_universe_x2.py"))
x2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(x2)
add(x2.UNIVERSE_X2, "v54_universe_x2:UNIVERSE_X2")
sys.path.insert(0, REPO)
import pine_backtest as pb
add(pb.UNIVERSE_15, "pine_backtest:UNIVERSE_15"); add(pb.UNIVERSE_X, "pine_backtest:UNIVERSE_X")
for line in open(os.path.join(REPO, "signal_log/watchlist.txt")):
    line = line.strip()
    if line and not line.startswith("#"): add([line], "signal_log/watchlist.txt")
for pat in ["backtest_cache/*_*.pkl", "backtest_cache/v3/*.pkl", "pine_1h/cache/*.pkl",
            "pine_2h3h_backtest/cache/*.pkl", "pine_entry_timing_backtest/cache/*.pkl"]:
    for f in glob.glob(os.path.join(REPO, pat)):
        m = re.search(r"(?:h1_|h4_|d1_5y_|d1_|w1_|signals_)(.+)\.pkl$", f)
        if m:
            s = m.group(1)
            s = re.sub(r"^(U15|UX)_", "", s)   # U15_AAPL / UX_AAPL tags -> AAPL
            add([s], "data-cache-filename")
add(["IREN","BE","BTDR","TLN","PWR","ETN","POWL","EME","LEU","BWXT","SNDK","NNE","OKLO","NBIS",
     "INTC","MU","ONDS","UMAC","MP","USAR","TSSI"], "rotation_watch.py:TICKERS")
# names referenced in code/docstrings but not in a list (delisted / renamed)
add(["CYBR"], "v54_universe_x2.py docstring (acquired 2025, dropped from forward test)")
add(["SQ"], "v54_universe_x2.py docstring (renamed XYZ)")

# drop obvious non-tickers scraped from prose
DROP = {"BASE","FAIL","PASS","MAYBE","LOOSE","FVG","REL","SIGN","PB"}
for d in DROP: pool.pop(d, None)

recs = [{"symbol": s, "sources": sorted(set(v))} for s, v in sorted(pool.items())]
with open(os.path.join(OUT, "candidate_pool.json"), "w") as f:
    json.dump(recs, f, indent=1)
print(f"pool size: {len(recs)}")
crypto = [r for r in recs if r["symbol"].endswith("-USD")]
print(f"crypto pairs in pool: {len(crypto)}")
