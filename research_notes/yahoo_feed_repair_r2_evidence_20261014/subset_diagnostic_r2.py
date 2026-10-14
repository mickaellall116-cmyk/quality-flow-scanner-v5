"""r2 bounded live subset diagnostic (no state writes).

Runs the r2 candidate scan over the same 40 symbols as the r1 diagnostic
(scan indices 0-24 and 150-164) with a recorder around yf.download that
captures every upstream request (shape, ticker count, duration). Reports
wall time, coverage with the r2 separated denominators, P1 derive/fallback
counts, and the leg-latency samples the 250-symbol projection is built
from. Run from the r2 worktree.
"""
import json
import time

import v54_forward_harness as h
import v54_engine as eng

CALLS = []
_real_download = eng.m53.yf.download


def recording_download(tickers, interval=None, period=None, **kw):
    t0 = time.monotonic()
    try:
        return _real_download(tickers, interval=interval, period=period, **kw)
    finally:
        CALLS.append({
            "tickers": tickers if isinstance(tickers, str) else list(tickers),
            "n": 1 if isinstance(tickers, str) else len(tickers),
            "interval": interval, "period": period,
            "prepost": bool(kw.get("prepost")),
            "dur_s": round(time.monotonic() - t0, 3),
        })


eng.m53.yf.download = recording_download

universe_all = list(h.FORWARD_UNIVERSE)
subset = universe_all[:25] + universe_all[150:165]
health = h.ProviderHealth(expected_symbols=list(subset),
                          benchmark_symbols=["QQQ", "SPY"])
t0 = time.monotonic()
with h.hardened_downloads(health, {}):
    rows, regime = eng.v54_scan_symbols(subset, h.THEME_MAP,
                                        h.INTERVAL, h.PERIOD)
wall = time.monotonic() - t0
health.finalize()
cov = health.coverage_block()
errors = [r for r in rows if r.get("state") == "ERROR"]
out = {
    "subset_size": len(subset),
    "wall_s": round(wall, 1),
    "per_symbol_s": round(wall / len(subset), 3),
    "rows": len(rows),
    "error_rows": len(errors),
    "coverage": {k: cov[k] for k in (
        "expected_symbols", "fresh_symbols", "benchmark_expected_symbols",
        "benchmark_fresh_symbols", "fresh_via_serial", "fresh_via_prefetch",
        "non_scan_fresh_symbols", "global_provider_status", "retries")},
    "feed_stats": getattr(health, "feed_stats", None),
    "upstream_calls": len(CALLS),
    "calls": CALLS,
}
with open("/tmp/feed_r2_evidence/subset_diagnostic_r2_result.json", "w") as fh:
    json.dump(out, fh, indent=1, default=str)
print(f"wall={wall:.1f}s per_symbol={wall/len(subset):.3f}s rows={len(rows)} "
      f"errors={len(errors)} upstream_calls={len(CALLS)}")
print("coverage:", out["coverage"])
print("feed_stats:", out["feed_stats"])
