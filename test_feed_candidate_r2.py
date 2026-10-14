"""Offline equivalence + fault tests for the QF-YAHOO-FEED-REPAIR-20261014-01
r2 candidate (r1 batched prefetch + P1 daily-tail reuse + separated
scan/benchmark coverage denominators + post-trip prefetch accounting).

A deterministic fake replaces yfinance's download. For the three batched
shapes the batch and single paths serve the SAME underlying arrays (the
property measured live in r1). The fake's 1d/10d series is BY CONSTRUCTION
the exact tail of its 1d/2y series — the property the r2 live parity probe
verifies against the real vendor — so the P1 derivation must reproduce
the original rows exactly.

Scenarios (original vs r2, full-scan): healthy, batch_empty_one,
batch_raises, single_429 (EXACT rows now required, incl. post-trip),
timeout_primary, empty_primary, missing_in_batch, stale_primary,
failed_daily_conf (P1 must fall back to the serial 1d/10d call),
budget_edge (prefetch disabled), plus a denominator regression run that
reproduces the r1 artifact anomaly (fresh=42 > expected=40 class) against
the original accounting and proves the r2 accounting cannot produce it.

Usage:
  python3 test_feed_candidate_r2.py run <scenario> <out.json>
  python3 test_feed_candidate_r2.py denom <out.json>
  python3 test_feed_candidate_r2.py all
"""
import json
import os
import subprocess
import sys
import zlib

import numpy as np
import pandas as pd

CALLS = []
SCENARIO = "healthy"
FAIL_SYM = None            # batch-hole target
RATELIMIT_SYM = None       # 429 target
TIMEOUT_SYM = None         # primary-timeout target
EMPTY_SYM = None           # empty-primary target
DAILY_FAIL_SYM = None      # 1d/2y failure target (P1 fallback proof)
MISSING_SYM = None         # omitted-from-batch target
STALE_SYM = None           # stale-primary target

ET = "America/New_York"


def _seed(*parts):
    return zlib.crc32("|".join(str(p) for p in parts).encode()) & 0xFFFFFFFF


def _walk(rng, n, start=100.0):
    steps = rng.normal(0, 0.004, n).cumsum()
    close = start * np.exp(steps)
    open_ = np.concatenate([[start], close[:-1]])
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.002, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.002, n))
    vol = rng.randint(1_000, 900_000, n).astype(float)
    return open_, high, low, close, vol


def _frame(idx, sym, shape):
    rng = np.random.RandomState(_seed(sym, shape))
    o, h, l, c, v = _walk(rng, len(idx), start=50 + _seed(sym) % 200)
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c,
                         "Volume": v}, index=idx)


def _idx_1h(days=182, end="2026-10-13"):
    days_idx = pd.bdate_range(end=pd.Timestamp(end), periods=days)
    stamps = []
    for d in days_idx:
        base = pd.Timestamp(d.date()).tz_localize(ET) + pd.Timedelta(hours=9, minutes=30)
        stamps += [base + pd.Timedelta(hours=i) for i in range(7)]
    return pd.DatetimeIndex(stamps)


def _idx_15m(days=5):
    days_idx = pd.bdate_range(end=pd.Timestamp("2026-10-13"), periods=days)
    stamps = []
    for d in days_idx:
        base = pd.Timestamp(d.date()).tz_localize(ET) + pd.Timedelta(hours=9, minutes=30)
        stamps += [base + pd.Timedelta(minutes=15 * i) for i in range(26)]
    return pd.DatetimeIndex(stamps)


def _idx_5m(days=2):
    days_idx = pd.bdate_range(end=pd.Timestamp("2026-10-13"), periods=days)
    stamps = []
    for d in days_idx:
        base = pd.Timestamp(d.date()).tz_localize(ET) + pd.Timedelta(hours=4)
        stamps += [base + pd.Timedelta(minutes=5 * i) for i in range(192)]
    return pd.DatetimeIndex(stamps)


def _daily_2y(sym):
    idx = pd.bdate_range(end="2026-10-13", periods=501).tz_localize(ET)
    return _frame(idx, sym, "1d2y")


def raw_frame(sym, interval, period):
    """The deterministic underlying data for one (symbol, interval, period)."""
    if interval == "1h":
        if sym == STALE_SYM:
            idx = _idx_1h(182, end="2026-09-29")
            return _frame(idx, sym, "1h180d")
        idx = _idx_1h(40) if sym == "THIN" else _idx_1h()
        return _frame(idx, sym, "1h180d")
    if interval == "1d" and period == "2y":
        return _daily_2y(sym)
    if interval == "1wk":
        idx = pd.bdate_range(end="2026-10-09", periods=262, freq="W-FRI").tz_localize(ET)
        return _frame(idx, sym, "1wk5y")
    if interval == "15m":
        return _frame(_idx_15m(), sym, "15m5d")
    if interval == "5m":
        return _frame(_idx_5m(), sym, "5m2d")
    if interval == "1d" and period == "10d":
        # By construction the exact tail of the 2y series — the property
        # the live r2 parity probe verifies against the real vendor.
        return _daily_2y(sym).tail(10).copy()
    raise ValueError(f"unexpected shape {interval}/{period}")


def _empty_batch_frame(sym):
    cols = pd.MultiIndex.from_product(
        [[sym], ["Open", "High", "Low", "Close", "Volume"]])
    return pd.DataFrame(columns=cols,
                        index=pd.DatetimeIndex([], tz=ET))


def _batch_hole(sym, interval):
    """True when the batch slot for this symbol must come back empty so
    the candidate falls through to the serial path (where the scenario's
    real fault lives)."""
    if interval != "1h":
        return False
    return ((sym == FAIL_SYM and SCENARIO == "batch_empty_one")
            or (sym == RATELIMIT_SYM and SCENARIO == "single_429")
            or (sym == TIMEOUT_SYM and SCENARIO == "timeout_primary")
            or (sym == EMPTY_SYM and SCENARIO == "empty_primary"))


def fake_download(tickers, interval=None, period=None, prepost=False,
                  progress=False, auto_adjust=True, threads=False,
                  group_by=None, **kw):
    single = isinstance(tickers, str)
    syms = [tickers] if single else list(tickers)
    CALLS.append({"tickers": syms, "interval": interval, "period": period,
                  "prepost": bool(prepost), "batch": not single})
    if not single and SCENARIO == "batch_raises":
        raise RuntimeError("simulated batch transport failure")
    if single:
        sym = tickers
        if SCENARIO == "single_429" and sym == RATELIMIT_SYM and interval == "1h":
            raise RuntimeError("429 Too Many Requests")
        if SCENARIO == "timeout_primary" and sym == TIMEOUT_SYM and interval == "1h":
            raise RuntimeError("HTTPSConnectionPool: Read timed out")
        if SCENARIO == "failed_daily_conf" and sym == DAILY_FAIL_SYM \
                and interval == "1d" and period == "2y":
            raise RuntimeError("HTTPSConnectionPool: connection reset by peer")
        df = raw_frame(sym, interval, period)
        if SCENARIO == "empty_primary" and sym == EMPTY_SYM and interval == "1h":
            df = df.iloc[0:0]
        df = df.copy()
        df.columns = pd.MultiIndex.from_product(
            [["Open", "High", "Low", "Close", "Volume"], [sym]])
        return df
    frames = {}
    for sym in syms:
        if SCENARIO == "missing_in_batch" and sym == MISSING_SYM:
            continue  # ticker omitted from the batch response entirely
        if _batch_hole(sym, interval):
            frames[sym] = _empty_batch_frame(sym)
            continue
        frames[sym] = raw_frame(sym, interval, period)
    parts = []
    for sym in syms:
        if sym not in frames:
            continue
        f = frames[sym].copy()
        if not isinstance(f.columns, pd.MultiIndex):
            f.columns = pd.MultiIndex.from_product(
                [[sym], ["Open", "High", "Low", "Close", "Volume"]])
        parts.append(f)
    return pd.concat(parts, axis=1)


def _setup_scenario(scenario, universe):
    global FAIL_SYM, RATELIMIT_SYM, TIMEOUT_SYM, EMPTY_SYM
    global DAILY_FAIL_SYM, MISSING_SYM, STALE_SYM
    FAIL_SYM = universe[3]
    RATELIMIT_SYM = universe[10]
    TIMEOUT_SYM = universe[5]
    EMPTY_SYM = universe[7]
    DAILY_FAIL_SYM = universe[9]
    MISSING_SYM = universe[11]
    STALE_SYM = universe[13]


def run(scenario, out_path):
    global SCENARIO
    SCENARIO = scenario
    target = os.environ.get("FEED_REPO")
    if target:
        sys.path.insert(0, target)
    import v54_forward_harness as h
    import v54_engine as eng

    universe = list(h.FORWARD_UNIVERSE[:30]) + ["BRK-B", "THIN"]
    _setup_scenario(scenario, universe)
    eng.m53.yf.download = fake_download
    deadline = 80.0 if scenario == "budget_edge" else h.HARD_CYCLE_DEADLINE_S
    kwargs = {}
    if "benchmark_symbols" in h.ProviderHealth.__init__.__code__.co_varnames:
        kwargs["benchmark_symbols"] = ["QQQ", "SPY"]
    health = h.ProviderHealth(expected_symbols=list(universe) + ["QQQ", "SPY"],
                              cycle_deadline_s=deadline, **kwargs)
    with h.hardened_downloads(health, {}):
        rows, regime = eng.v54_scan_symbols(universe, h.THEME_MAP,
                                            h.INTERVAL, h.PERIOD)
    health.finalize()
    cov = health.coverage_block()
    payload = {
        "scenario": scenario,
        "rows": sorted(json.dumps(r, default=str, sort_keys=True) for r in rows),
        "qualified": sorted(json.dumps(r, default=str, sort_keys=True)
                            for r in eng.v54_qualified_signals(rows)),
        "regime": json.dumps(regime, default=str, sort_keys=True),
        "calls": CALLS,
        "n_calls": len(CALLS),
        "coverage": cov,
        "feed_stats": getattr(health, "feed_stats", None),
    }
    with open(out_path, "w") as fh:
        json.dump(payload, fh)
    print(f"{scenario}: rows={len(rows)} calls={len(CALLS)} "
          f"fresh={cov['fresh_symbols']}/{cov['expected_symbols']} "
          f"global={cov['global_provider_status']}")


def run_denom(out_path):
    """Denominator regression: scan universe EXCLUDES the benchmarks, so
    regime fetches (QQQ/SPY) mark fresh outside the scan denominator —
    the exact shape of the r1 artifact anomaly (fresh=42, expected=40)."""
    target = os.environ.get("FEED_REPO")
    if target:
        sys.path.insert(0, target)
    import v54_forward_harness as h
    import v54_engine as eng

    universe = [s for s in h.FORWARD_UNIVERSE[:12]
                if s not in ("QQQ", "SPY")][:6]
    _setup_scenario("healthy", list(h.FORWARD_UNIVERSE[:30]))
    eng.m53.yf.download = fake_download
    kwargs = {}
    if "benchmark_symbols" in h.ProviderHealth.__init__.__code__.co_varnames:
        kwargs["benchmark_symbols"] = ["QQQ", "SPY"]
    health = h.ProviderHealth(expected_symbols=list(universe), **kwargs)
    with h.hardened_downloads(health, {}):
        rows, regime = eng.v54_scan_symbols(universe, h.THEME_MAP,
                                            h.INTERVAL, h.PERIOD)
    health.finalize()
    cov = health.coverage_block()
    payload = {"universe": universe, "coverage": cov,
               "n_rows": len(rows)}
    with open(out_path, "w") as fh:
        json.dump(payload, fh)
    print(f"denom: expected={cov['expected_symbols']} "
          f"fresh={cov['fresh_symbols']} cov={ {k: cov[k] for k in cov if 'benchmark' in k or 'non_scan' in k} }")


def _run_in(dirname, mode, scenario=None):
    out = f"/tmp/feed_r2_{mode}_{scenario or ''}_{dirname}.json"
    repo = ("/home/hatch/workspace/quality-flow-scanner-v5" if dirname == "orig"
            else "/tmp/feed_r2_wt")
    env = dict(os.environ, FEED_REPO=repo, PYTHONDONTWRITEBYTECODE="1")
    args = [sys.executable, __file__, mode]
    if scenario:
        args.append(scenario)
    args.append(out)
    r = subprocess.run(args, cwd=repo, capture_output=True, text=True, env=env)
    print(("ORIG " if dirname == "orig" else "CAND ") + (r.stdout.strip()
          or r.stderr[-2000:]))
    if r.returncode != 0:
        print(r.stderr[-3000:])
        raise SystemExit(f"run failed: {dirname}/{mode}/{scenario}")
    return json.load(open(out))


def _calls_for(payload, sym, interval=None, period=None, batch=None):
    out = []
    for c in payload["calls"]:
        if sym not in c["tickers"]:
            continue
        if interval is not None and c["interval"] != interval:
            continue
        if period is not None and c["period"] != period:
            continue
        if batch is not None and c["batch"] != batch:
            continue
        out.append(c)
    return out


SHARED_COV_KEYS = ("expected_symbols", "fresh_symbols", "retries",
                   "global_provider_status")


def all_scenarios():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(f"  [{'OK' if cond else 'FAIL'}] {name} {detail}")
        if not cond:
            ok = False

    scenarios = ("healthy", "batch_empty_one", "batch_raises", "single_429",
                 "timeout_primary", "empty_primary", "missing_in_batch",
                 "stale_primary", "failed_daily_conf", "budget_edge")
    for scenario in scenarios:
        print(f"== {scenario} ==")
        a = _run_in("orig", "run", scenario)
        b = _run_in("cand", "run", scenario)
        check("rows identical", a["rows"] == b["rows"],
              f"(orig {len(a['rows'])} vs cand {len(b['rows'])})")
        if a["rows"] != b["rows"]:
            for x, y in zip(a["rows"], b["rows"]):
                if x != y:
                    print("  FIRST DIFF orig:", x[:260])
                    print("  FIRST DIFF cand:", y[:260])
                    break
        check("qualified identical", a["qualified"] == b["qualified"])
        check("regime identical", a["regime"] == b["regime"])
        for k in SHARED_COV_KEYS:
            check(f"coverage[{k}] identical",
                  a["coverage"][k] == b["coverage"][k],
                  f"(orig {a['coverage'][k]} vs cand {b['coverage'][k]})")
        da = sorted((d["symbol"], d["reason"])
                    for d in a["coverage"]["degraded_symbols"])
        db = sorted((d["symbol"], d["reason"])
                    for d in b["coverage"]["degraded_symbols"])
        check("degraded sets identical", da == db)
        cov = b["coverage"]
        check("cand numerator <= denominator",
              cov["fresh_symbols"] <= cov["expected_symbols"])
        check("cand via split sums to fresh",
              cov["fresh_via_serial"] + cov["fresh_via_prefetch"]
              == cov["fresh_symbols"],
              f"({cov['fresh_via_serial']}+{cov['fresh_via_prefetch']}"
              f" vs {cov['fresh_symbols']})")
        if scenario == "healthy":
            d10 = [c for c in b["calls"] if c["interval"] == "1d"
                   and c["period"] == "10d"]
            check("cand zero 1d/10d wire calls (all derived)", len(d10) == 0,
                  f"(cand {len(d10)}, orig "
                  f"{len([c for c in a['calls'] if c['interval']=='1d' and c['period']=='10d'])})")
            st = b["feed_stats"] or {}
            check("cand pm_daily_derived > 0", st.get("pm_daily_derived", 0) > 0,
                  f"({st})")
            check("cand pm_daily_fallback == 0", st.get("pm_daily_fallback", 0) == 0)
            thin_aux = [c for c in b["calls"] if c["tickers"] == ["THIN"]
                        and c["interval"] != "1h"]
            check("THIN zero aux single calls (cand)", len(thin_aux) == 0)
        if scenario == "single_429":
            check("global guard trips in both",
                  a["coverage"]["global_provider_status"]
                  == b["coverage"]["global_provider_status"]
                  == "rate_limited")
        if scenario == "failed_daily_conf":
            d10 = [c for c in b["calls"] if c["interval"] == "1d"
                   and c["period"] == "10d" and not c["batch"]]
            check("cand fell back to serial 1d/10d on failed 2y",
                  len(d10) >= 1, f"({len(d10)} calls)")
            st = b["feed_stats"] or {}
            check("cand feed_stats records fallback",
                  st.get("pm_daily_fallback", 0) >= 1, f"({st})")
        if scenario == "missing_in_batch":
            singles = [c for c in b["calls"] if c["batch"] is False
                       and c["interval"] == "1h"]
            check("cand serial fallback used for batch-missing symbol",
                  len(singles) >= 1, f"({len(singles)} single 1h calls)")
        if scenario == "budget_edge":
            batches = [c for c in b["calls"] if c["batch"]]
            check("cand zero batch calls under budget edge",
                  len(batches) == 0, f"({len(batches)})")

    print("== denominator regression ==")
    da = _run_in("orig", "denom")
    db = _run_in("cand", "denom")
    oc, nc = da["coverage"], db["coverage"]
    check("orig accounting reproduces the anomaly (fresh > expected)",
          oc["fresh_symbols"] > oc["expected_symbols"],
          f"(orig fresh={oc['fresh_symbols']} expected={oc['expected_symbols']})")
    check("cand scan fresh <= expected",
          nc["fresh_symbols"] <= nc["expected_symbols"],
          f"(cand fresh={nc['fresh_symbols']} expected={nc['expected_symbols']})")
    check("cand scan fresh == scanned universe",
          nc["fresh_symbols"] == nc["expected_symbols"] == len(db["universe"]))
    check("cand benchmark block separated",
          nc.get("benchmark_fresh_symbols") == 2
          and nc.get("benchmark_expected_symbols") == 2,
          f"({nc.get('benchmark_fresh_symbols')}/{nc.get('benchmark_expected_symbols')})")
    check("cand non_scan_fresh empty", nc.get("non_scan_fresh_symbols") == [])
    print("ALL OK" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "denom":
        run_denom(sys.argv[2])
    else:
        sys.exit(all_scenarios())
