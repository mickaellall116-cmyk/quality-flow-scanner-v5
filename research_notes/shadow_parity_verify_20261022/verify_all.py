#!/usr/bin/env python3
"""Independent verification of ChatGPT's corrected shadow parity probe
(branch research/shadow-parity-probe-20261022, tip 8339d1f) and the
-80 successor candidate it gates (798de18). OFFLINE. Staged bytes only.
Emits results.json. Every check is empirical: code is executed, not
trusted from prose.
"""
import ast
import hashlib
import json
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).parent
REPO = Path("/home/hatch/workspace/quality-flow-scanner-v5")
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True

import staged_signal_parity_probe as probe  # noqa: E402

R = {}
ET = ZoneInfo("America/New_York")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------- V1: probe synthetic suite ----------
p = subprocess.run([sys.executable, "-B", "test_staged_signal_parity_probe.py"],
                   cwd=HERE, capture_output=True, text=True)
R["V1_probe_synthetic_suite"] = {
    "exit": p.returncode,
    "pass_lines": p.stdout.count("PASS"),
    "tail": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "",
    "stderr_tail": p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "",
}

# ---------- V2: probe on REAL stored bytes ----------
witness = json.loads((HERE / "witness_ba4276f.json").read_bytes())
R["V2a_witness_ba4276f"] = probe.verify(witness, sha(HERE / "witness_ba4276f.json"))

cur_obs = json.loads((REPO / "forward_test/v54_ai_observer.json").read_bytes())
R["V2b_current_observer_export"] = probe.verify(
    cur_obs, sha(REPO / "forward_test/v54_ai_observer.json"))

jsonl_rows = [json.loads(l) for l in open(REPO / "v54_forward/forward_test.jsonl")]
sig_rows = [r for r in jsonl_rows if r.get("type") == "signal"]
R["V2c_forward_jsonl_signal_rows"] = probe.verify(
    sig_rows, sha(REPO / "v54_forward/forward_test.jsonl"))
R["V2c_note"] = f"{len(sig_rows)} stored type=signal rows of {len(jsonl_rows)} jsonl lines"

latest = json.loads((REPO / "latest_v54_signals.json").read_bytes())
R["V2d_latest_cycle_output"] = probe.verify(
    {"qualified_signals": latest["results"]}, sha(REPO / "latest_v54_signals.json"))
R["V2d_rows_detail"] = [
    {"symbol": r["symbol"], "start": r["signal_bar_start_at"],
     "close": r["signal_bar_close_at"]} for r in latest["results"]]

# ---------- V3: replay the REAL adapter (pinned v54_engine) ----------
eng_sha = sha(REPO / "v54_engine.py")
sys.path.insert(0, str(REPO))
# The pinned offline venv intentionally has no network libraries.
# v54_qualified_signals is a pure filter; stub the network module
# names so the pinned engine module can be imported offline. The
# whole run is under `unshare -n`, so no stub can reach a network.
for _name in ("yfinance",):
    if _name not in sys.modules:
        _stub = types.ModuleType(_name)
        _stub.__getattr__ = lambda attr, _n=_name: (_ for _ in ()).throw(
            RuntimeError(f"{_n} stubbed offline"))
        sys.modules[_name] = _stub
import v54_engine as eng  # noqa: E402

out = eng.v54_qualified_signals(sig_rows)
mixed = sig_rows + [{"symbol": "FAKE1", "v54_eligible": False},
                    {"symbol": "FAKE2", "v54_eligible": None},
                    {"symbol": "FAKE3"}]
out_mixed = eng.v54_qualified_signals(mixed)
R["V3_adapter_replay"] = {
    "engine_sha256": eng_sha,
    "engine_pin_expected": "bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb",
    "pin_match": eng_sha == "bde3288307ac7b9bfbded29af89b056ae849f49d91b51c1151dad860224eb8fb",
    "stored_rows_in": len(sig_rows),
    "qualified_out": len(out),
    "all_stored_pass_filter": len(out) == len(sig_rows),
    "mixed_in": len(mixed), "mixed_out": len(out_mixed),
    "ineligible_excluded": len(out_mixed) == len(sig_rows),
    "probe_on_adapter_output": probe.verify(out),
}

# ---------- V4: resampler parity on synthetic 1h bars ----------
import pandas as pd  # noqa: E402
import scanner_rules as sr  # noqa: E402


def hour_bars(day, hours):
    idx = pd.DatetimeIndex([datetime(day.year, day.month, day.day, h, 30,
                                      tzinfo=ET) for h in hours])
    n = len(idx)
    return pd.DataFrame({"Open": [100.0] * n, "High": [101.0] * n,
                         "Low": [99.0] * n, "Close": [100.5] * n,
                         "Volume": [1000] * n}, index=idx)


def bins(df):
    res = []
    for ts in df.index:
        loc = ts.tz_convert("America/New_York")
        res.append({"start_et": loc.strftime("%H:%M"),
                    "close_at": sr.bar_close_at(ts, "AAPL").strftime("%H:%M")})
    return res


from datetime import date  # noqa: E402
normal_day = hour_bars(date(2026, 10, 22), [9, 10, 11, 12, 13, 14, 15])
now_norm = pd.Timestamp("2026-10-22 20:00", tz="America/New_York")
leg = sr.resample_closed_4h(normal_day.copy(), "AAPL", now=now_norm)
anc = sr.resample_closed_4h_session_anchored(normal_day.copy(), "AAPL", now=now_norm)
early_day = hour_bars(date(2026, 11, 27), [9, 10, 11, 12])
now_early = pd.Timestamp("2026-11-27 20:00", tz="America/New_York")
anc_early = sr.resample_closed_4h_session_anchored(early_day.copy(), "AAPL", now=now_early)
R["V4_resampler_parity"] = {
    "legacy_bins_normal_day": bins(leg),
    "anchored_bins_normal_day": bins(anc),
    "anchored_bins_early_close_2026_11_27": bins(anc_early),
    "probe_on_early_close_row": probe.verify([{
        "symbol": "AAPL", "v54_rule_version": "2026-09-15-v54",
        "signal_bar_start_at": "2026-11-27T09:30:00-05:00",
        "signal_bar_close_at": "2026-11-27T13:00:00-05:00",
        "signal_id": "v54:AAPL:4h:2026-11-27T13:00:00-05:00:2026-09-15-v54"}]),
}

# ---------- V5: market-frame failure spy on successor LiveAdapter ----------
sys.path.insert(0, str(HERE / "successor"))
import shadow_signal_runner as runner  # noqa: E402

FAKE_SYMS = [f"S{i:03d}" for i in range(250)]


def spy_run(mode):
    scan = {"calls": 0, "symbols": 0}
    fake_eng = types.ModuleType("v54_engine")
    fake_m53 = types.ModuleType("m53")

    def dl(sym, interval, period):
        if mode == "raise":
            raise RuntimeError("provider down")
        return None

    fake_m53.download_data = dl
    fake_m53.MARKET_SYMBOL = "SPY"
    fake_eng.m53 = fake_m53

    def scan_symbols(universe, themes, interval, period):
        scan["calls"] += 1
        scan["symbols"] = len(universe)
        return ([{"symbol": s, "state": "OK"} for s in universe], {})

    fake_eng.v54_scan_symbols = scan_symbols
    fake_eng.v54_qualified_signals = lambda rows: []
    fake_hx = types.ModuleType("hybrid_exit_test")
    fake_hx.UNIVERSE_X = FAKE_SYMS[:51]
    fake_x2 = types.ModuleType("v54_universe_x2")
    fake_x2.UNIVERSE_X2 = FAKE_SYMS[51:]
    saved = {k: sys.modules.get(k) for k in
             ("v54_engine", "hybrid_exit_test", "v54_universe_x2")}
    sys.modules.update({"v54_engine": fake_eng, "hybrid_exit_test": fake_hx,
                        "v54_universe_x2": fake_x2})
    try:
        adapter = runner.LiveAdapter(str(REPO))
        cands, health = adapter.fetch()
        return {"scan_calls": scan["calls"], "symbols_scanned": scan["symbols"],
                "market_ok_reported": health["market_ok"],
                "candidates": len(cands)}
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


R["V5_market_frame_spy"] = {
    "market_raises": spy_run("raise"),
    "market_returns_none": spy_run("none"),
    "required": "scan_calls == 0 on market-frame failure",
}

# ---------- V6: cohort 250 unique (via the runner's own code path) ----------
_uni, _themes = runner.frozen_universe()
ux51, x2 = _uni[:51], _uni[51:]
import hybrid_exit_test as _hx  # noqa: E402
import v54_universe_x2 as _ux2m  # noqa: E402
assert list(_hx.UNIVERSE_X) == ux51 and list(_ux2m.UNIVERSE_X2) == x2
R["V6_cohort"] = {
    "ux51": len(ux51), "x2": len(x2), "union": len(ux51 + x2),
    "unique_union": len(set(ux51 + x2)),
    "overlap": len(set(ux51) & set(x2)),
    "unique_within_ux51": len(set(ux51)), "unique_within_x2": len(set(x2)),
}

# ---------- V7: T0 strictness + successor acceptance suite ----------
import shadow_signal_core as core  # noqa: E402

T0 = datetime(2026, 10, 22, 13, 30, tzinfo=ET)
NOW = datetime(2026, 10, 22, 17, 0, tzinfo=ET)
HEALTHY = {"market_ok": True, "scan_complete": True, "degraded_symbols": []}


def srow(start, close, sym="TEST", sid=None):
    sid = sid or f"v54:{sym}:4h:{close}:2026-09-15-v54"
    return {"signal_id": sid, "symbol": sym, "v54_grade": "B",
            "signal_bar_start_at": start, "signal_bar_close_at": close}


tmp = tempfile.mkdtemp(prefix="t0_")
root = str(Path(tmp) / "shadow")
obs = core.SignalObserver(root, T0, clock=lambda: NOW)
s_close_eq_t0 = obs.run_cycle(
    [srow("2026-10-22T09:30:00-04:00", "2026-10-22T13:30:00-04:00")],
    HEALTHY, now=NOW)
s_valid = obs.run_cycle(
    [srow("2026-10-22T13:30:00-04:00", "2026-10-22T16:00:00-04:00")],
    HEALTHY, now=NOW)
s_partial = obs.run_cycle(
    [srow("2026-10-22T13:30:00-04:00", "2026-10-22T16:00:00-04:00",
          sym="LATE")],
    HEALTHY, now=datetime(2026, 10, 22, 15, 0, tzinfo=ET))
s_degraded = obs.run_cycle(
    [srow("2026-10-22T13:30:00-04:00", "2026-10-22T16:00:00-04:00",
          sym="DEG")],
    {"market_ok": False, "scan_complete": True, "degraded_symbols": []},
    now=NOW)
t0_move = "no_error"
try:
    core.SignalObserver(root, datetime(2026, 10, 23, 13, 30, tzinfo=ET),
                        clock=lambda: NOW)
except core.ShadowError:
    t0_move = "ShadowError"
t0_same = "ok"
try:
    core.SignalObserver(root, T0, clock=lambda: NOW)
except Exception as e:  # noqa: BLE001
    t0_same = f"{type(e).__name__}: {e}"
R["V7_t0_strictness"] = {
    "close_eq_T0_refused": s_close_eq_t0["signals_refused"],
    "close_eq_T0_recorded": s_close_eq_t0["new_signals_recorded"],
    "valid_post_T0_recorded": s_valid["new_signals_recorded"],
    "partial_bar_refused": s_partial["signals_refused"],
    "degraded_cycle_status": s_degraded["status"],
    "degraded_cycle_recorded": s_degraded["new_signals_recorded"],
    "t0_move_on_reopen": t0_move,
    "t0_same_on_reopen": t0_same,
}

# ---------- V8: hash-chained provenance, end to end ----------
log_lines = [json.loads(l) for l in open(Path(root) / core.LOG_FILENAME)]
chain_keys = ("hash", "prev_hash", "record_hash", "chain_hash", "sha256")
records_with_chain = sum(
    1 for r in log_lines if any(k in r for k in chain_keys))
pins = runner.verify_pins(str(REPO))
R["V8_provenance"] = {
    "log_records_written": len(log_lines),
    "records_with_any_hash_chain_field": records_with_chain,
    "record_kinds": sorted({r.get("record_kind") for r in log_lines}),
    "verify_pins_matches": pins == runner.PINNED_STACK,
    "verify_pins_count": len(pins),
}

# successor acceptance suite (its own sandbox)
p2 = subprocess.run([sys.executable, "-B", "tests/test_shadow_signal_observer.py"],
                    cwd=HERE / "successor", capture_output=True, text=True)
R["V7b_successor_suite"] = {
    "exit": p2.returncode,
    "pass_lines": p2.stdout.count("PASS"),
    "fail_lines": p2.stdout.count("FAIL"),
    "tail": (p2.stdout.strip().splitlines() or [""])[-1],
    "stderr_tail": (p2.stderr.strip().splitlines() or [""])[-1],
}

print(json.dumps(R, indent=1, default=str))
(HERE / "results.json").write_text(json.dumps(R, indent=1, default=str))
