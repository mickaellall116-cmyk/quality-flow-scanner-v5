"""Tests for pine_live/research/ — observation-only instrumentation.

Covers: classification determinism, spec-to-code consistency, each
pre-registered rule, counterfactual math, delay slicing + the
MIN_BUCKET_TRADES safeguard, INSUFFICIENT_DATA/INSUFFICIENT_SAMPLE
degradation, the pre-registered PASS/FAIL evaluation (incl. the
tail-winner trap), and the hard boundaries (no forbidden imports, never
writes to paper_state/).
"""

import json
import math
import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from pine_live.research import shadow, delay, evaluate  # noqa: E402
from pine_live.research import run_shadow, run_delay  # noqa: E402
import pine_backtest as pb  # noqa: E402

SPEC = os.path.join(REPO_ROOT, "pine_live", "research",
                    "SHADOW_ADVISOR_SPEC.md")
DELAY_SPEC = os.path.join(REPO_ROOT, "pine_live", "research",
                          "DELAY_STUDY_SPEC.md")


def _inputs(**kw):
    base = {"r_now": 0.5, "dist_to_stop_frac": 1.5, "mae_r": -0.1,
            "mfe_r": 0.6, "bars_held": 5, "bar_time": "2026-01-01T00:00:00+00:00"}
    base.update(kw)
    return base


# ---------------------------------------------------------------- determinism

def test_classify_deterministic():
    inp = _inputs(r_now=-0.8)
    assert shadow.classify(inp) == shadow.classify(dict(inp))
    assert shadow.classify(inp) == ("EXIT-CANDIDATE", "EC1")


def test_classify_each_rule():
    assert shadow.classify(_inputs(r_now=-0.75)) == ("EXIT-CANDIDATE", "EC1")
    assert shadow.classify(_inputs(r_now=0.1, bars_held=60)) == (
        "EXIT-CANDIDATE", "EC2")
    assert shadow.classify(_inputs(r_now=-0.2, mae_r=-0.95)) == (
        "EXIT-CANDIDATE", "EC3")
    assert shadow.classify(_inputs(r_now=1.5)) == ("PROTECT", "P1")
    assert shadow.classify(_inputs(r_now=0.8, mfe_r=2.5)) == ("PROTECT", "P2")
    assert shadow.classify(_inputs(r_now=0.1, bars_held=20)) == (
        "WEAKENING", "W1")
    assert shadow.classify(_inputs(r_now=0.2, mae_r=-0.6)) == (
        "WEAKENING", "W2")
    assert shadow.classify(_inputs()) == ("HOLD", None)


def test_classify_precedence_exit_over_protect():
    # r_now satisfies P1 but EC1 fires first (documented precedence).
    assert shadow.classify(_inputs(r_now=-0.8, mfe_r=3.0)) == (
        "EXIT-CANDIDATE", "EC1")


def test_classify_insufficient_data():
    assert shadow.classify(None) == (shadow.SENTINEL_INSUFFICIENT_DATA, None)
    assert shadow.classify({}) == (shadow.SENTINEL_INSUFFICIENT_DATA, None)
    assert shadow.compute_inputs(None, None) is None
    assert shadow.compute_inputs({"entry_px": 100, "stop_px": 90}, []) is None
    # Degenerate geometry: entry below stop.
    bars = [{"t": "2026-01-01T04:00:00+00:00", "c": 95.0}]
    assert shadow.compute_inputs({"entry_px": 90, "stop_px": 100},
                                 bars) is None


def test_compute_inputs_values():
    pos = {"entry_px": 100.0, "stop_px": 90.0}
    bars = [
        {"t": "2026-01-01T04:00:00+00:00", "c": 96.0},   # -0.4R
        {"t": "2026-01-01T08:00:00+00:00", "c": 112.0},  # +1.2R
        {"t": "2026-01-01T12:00:00+00:00", "c": 105.0},  # +0.5R
    ]
    inp = shadow.compute_inputs(pos, bars)
    assert inp["r_now"] == pytest.approx(0.5)
    assert inp["dist_to_stop_frac"] == pytest.approx(1.5)
    assert inp["mae_r"] == pytest.approx(-0.4)
    assert inp["mfe_r"] == pytest.approx(1.2)
    assert inp["bars_held"] == 3
    assert inp["bar_time"] == "2026-01-01T12:00:00+00:00"


# ------------------------------------------------------- spec-to-code consistency

def test_every_rule_id_in_spec_and_vice_versa():
    with open(SPEC, encoding="utf-8") as f:
        text = f.read()
    for rid in shadow.RULE_IDS:
        assert rid in text, f"rule {rid} missing from spec"
    found = set(re.findall(r"\b(EC[123]|P[12]|W[12])\b", text))
    assert found, "no rule ids found in spec"
    assert found <= set(shadow.RULE_IDS), \
        f"spec mentions rules with no code path: {found - set(shadow.RULE_IDS)}"


def test_delay_spec_freezes_buckets_and_min_sample():
    with open(DELAY_SPEC, encoding="utf-8") as f:
        text = f.read()
    assert "MIN_BUCKET_TRADES = 10" in text
    assert delay.MIN_BUCKET_TRADES == 10
    for name in ("vol<1.5%", "tod 00-05", "gap<10bps"):
        assert name in text


# ---------------------------------------------------------- counterfactual math

def test_hypothetical_exit_r_math():
    # entry 100, stop 90 (risk 10), exit 104 -> gross +0.4R.
    hyp = shadow.hypothetical_exit_r(entry_px=100.0, stop_px=90.0,
                                     next_open_px=104.0)
    assert hyp is not None
    assert hyp["hypothetical_gross_r"] == pytest.approx(0.4)
    _, _, net4, _ = pb._outcome(100.0, 90.0, 104.0, pb.COSTS["4bps"])
    assert hyp["hypothetical_net_r_4bps"] == pytest.approx(net4)
    # Below stop -> negative R, still computed (no inference, just math).
    hyp2 = shadow.hypothetical_exit_r(entry_px=100.0, stop_px=90.0,
                                      next_open_px=85.0)
    assert hyp2["hypothetical_gross_r"] == pytest.approx(-1.5)
    assert shadow.hypothetical_exit_r(entry_px=100.0, stop_px=100.0,
                                      next_open_px=104.0) is None
    assert shadow.hypothetical_exit_r(entry_px=None, stop_px=90.0,
                                      next_open_px=104.0) is None


# ------------------------------------------------------------- delay slicing

def _syn_trade(symbol, drag_bps, **kw):
    t = {"signal_id": f"s-{symbol}-{drag_bps}", "symbol": symbol,
         "entry_time": "2026-09-10T14:00:00+00:00",
         "entry_px": 100.0, "stop_px": 97.0, "ach_entry_px": 100.0,
         "drag_bps": float(drag_bps), "drag_r_4bps": float(drag_bps) / 1000.0}
    t.update(kw)
    return t


def test_min_bucket_trades_safeguard():
    trades = [_syn_trade("AAA", 50 + i) for i in range(3)]     # n=3: excluded
    trades += [_syn_trade("BBB", 5 + i) for i in range(10)]    # n=10: ranked
    sliced = delay.slice_drag(trades)
    sym = sliced["dimensions"]["symbol"]
    assert [e["bucket"] for e in sym["ranked"]] == ["BBB"]
    small = {e["bucket"]: e for e in sym["insufficient_sample"]}
    assert small["AAA"]["n"] == 3
    assert small["AAA"]["note"] == delay.INSUFFICIENT_SAMPLE


def test_ranking_by_mean_drag_desc():
    trades = [_syn_trade("LOW", 1 + i) for i in range(10)]
    trades += [_syn_trade("HIGH", 100 + i) for i in range(10)]
    sliced = delay.slice_drag(trades)
    ranked = sliced["dimensions"]["symbol"]["ranked"]
    assert [e["bucket"] for e in ranked] == ["HIGH", "LOW"]
    assert ranked[0]["mean_drag_bps"] > ranked[1]["mean_drag_bps"]
    assert ranked[0]["median_drag_bps"] == pytest.approx(104.5)


def test_gap_and_vol_buckets():
    # 3% stop distance -> vol 3-5%; gap 50bps -> gap 30-75bps.
    t = _syn_trade("X", 20, entry_px=100.0, stop_px=97.0,
                   ach_entry_px=100.5)
    k = delay.trade_keys(t)
    assert k["vol"] == "vol 3-5%"
    assert k["gap"] == "gap 30-75bps"
    assert k["tod"] == "tod 12-17"
    # Missing drag -> excluded entirely.
    assert delay.trade_keys({"symbol": "X"}) is None
    assert delay.trade_keys(None) is None


def test_delay_report_insufficient_data():
    report = run_delay.build_report([])
    assert "INSUFFICIENT_DATA" in report
    report2 = run_delay.build_report([{"symbol": "X"}])  # no drag_bps
    assert "INSUFFICIENT_DATA" in report2


def test_top_drag_buckets_respects_minimum():
    trades = [_syn_trade("AAA", 999.0) for _ in range(9)]  # huge but n=9
    sliced = delay.slice_drag(trades)
    assert delay.top_drag_buckets(sliced) == []


# --------------------------------------------------------------- evaluation

def test_tolerance_constant():
    assert evaluate.TOLERANCE_TOP_DECILE_DEGRADATION == 0.10
    assert evaluate.MIN_EVAL_TRADES == 30
    assert evaluate.REGIME_MIN_TRADES == 10


def _cf(signal_id, actual, hyp, flagged=False, regime=None):
    return {"signal_id": signal_id,
            "actual_net_r_25bps": float(actual),
            "hypothetical_net_r_25bps": float(hyp),
            "exit_candidate_before_exit": bool(flagged),
            "regime": regime}


def test_evaluate_insufficient_sample():
    recs = [_cf(f"s{i}", 0.3, 0.35) for i in range(29)]
    out = evaluate.evaluate_advisor(recs)
    assert out["status"] == evaluate.STATUS_INSUFFICIENT_SAMPLE
    assert out["criteria"] is None
    assert evaluate.evaluate_advisor([])["status"] == \
        evaluate.STATUS_INSUFFICIENT_SAMPLE
    assert evaluate.evaluate_advisor(None)["status"] == \
        evaluate.STATUS_INSUFFICIENT_SAMPLE


def test_evaluate_fail_mean_up_but_tail_clipped():
    # 30 trades; top decile (k=3) actual R = 5.0, 4.0, 3.0.
    # Guidance flags the 5R monster early -> capture 2/3 < 0.90.
    # Overall mean still improves -> (a) passes, (b) fails -> FAIL.
    recs = []
    recs.append(_cf("monster", 5.0, 0.5, flagged=True))   # clipped
    recs.append(_cf("w2", 4.0, 4.1))
    recs.append(_cf("w3", 3.0, 3.1))
    for i in range(27):
        recs.append(_cf(f"s{i}", 0.2, 0.5))  # +0.3 delta each
    out = evaluate.evaluate_advisor(recs)
    assert out["status"] == evaluate.STATUS_FAIL
    crit = out["criteria"]
    assert crit["a_mean_improvement"]["pass"] is True
    b = crit["b_top_decile_capture"]
    assert b["top_decile_n"] == 3
    assert b["hypothetical_capture"] == pytest.approx(2 / 3)
    assert b["pass"] is False
    assert b["required_capture"] == pytest.approx(0.90)


def test_evaluate_pass_all_three():
    recs = [_cf(f"s{i}", 0.2 + 0.01 * i, 0.25 + 0.01 * i,
                regime="bull" if i < 12 else None)
            for i in range(30)]
    out = evaluate.evaluate_advisor(recs)
    assert out["status"] == evaluate.STATUS_PASS
    crit = out["criteria"]
    assert crit["a_mean_improvement"]["pass"] is True
    assert crit["b_top_decile_capture"]["pass"] is True
    assert crit["b_top_decile_capture"]["hypothetical_capture"] == 1.0
    reg = crit["c_regime_no_degradation"]
    assert reg["pass"] is True
    assert reg["regimes"]["bull"]["judged"] is True


def test_evaluate_fail_regime_degradation():
    recs = [_cf(f"s{i}", 0.2, 0.25,
                regime="bear" if i < 10 else "bull")
            for i in range(30)]
    # Bear regime: guidance destroys 0.2R/trade on average -> (c) fails.
    for r in recs[:10]:
        r["hypothetical_net_r_25bps"] = r["actual_net_r_25bps"] - 0.2
    out = evaluate.evaluate_advisor(recs)
    assert out["status"] == evaluate.STATUS_FAIL
    reg = out["criteria"]["c_regime_no_degradation"]
    assert reg["pass"] is False
    assert reg["regimes"]["bear"]["judged"] is True
    assert reg["regimes"]["bear"]["pass"] is False
    assert reg["regimes"]["bull"]["judged"] is True


def test_evaluate_unpopulated_regime_not_judged():
    recs = [_cf(f"s{i}", 0.2, 0.25, regime="bull") for i in range(9)]
    recs += [_cf(f"b{i}", 0.2, 0.25) for i in range(21)]
    out = evaluate.evaluate_advisor(recs)
    assert out["status"] == evaluate.STATUS_PASS
    reg = out["criteria"]["c_regime_no_degradation"]
    assert reg["regimes"]["bull"]["judged"] is False
    assert reg["regimes"]["bull"]["note"] == evaluate.STATUS_INSUFFICIENT_SAMPLE


# ------------------------------------------------- hard boundaries: isolation

def test_no_forbidden_imports():
    code = (
        "from pine_live.research import shadow, delay, evaluate, "
        "run_shadow, run_delay\n"
        "import sys\n"
        "bad = [m for m in sys.modules if 'pine_live.paper.runner' in m "
        "or 'pine_live.alerts' in m]\n"
        "assert not bad, bad\n"
        "print('clean')\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert "clean" in proc.stdout


def test_research_never_writes_paper_state(tmp_path):
    state_dir = tmp_path / "paper_state"
    (state_dir / "ledger").mkdir(parents=True)
    pf = state_dir / "portfolio.json"
    pf.write_text(json.dumps({"portfolio": {"positions": {}}, "schema": "x"}))
    before_files = set()
    for root, _ds, fs in os.walk(state_dir):
        before_files |= {os.path.join(root, f) for f in fs}
    before_bytes = pf.read_bytes()

    out_dir = tmp_path / "research"
    out_dir.mkdir()
    assert run_shadow.main(["--state-dir", str(state_dir),
                            "--out-dir", str(out_dir)]) == 0
    assert run_delay.main(["--state-dir", str(state_dir),
                           "--out-dir", str(out_dir)]) == 0

    after_files = set()
    for root, _ds, fs in os.walk(state_dir):
        after_files |= {os.path.join(root, f) for f in fs}
    assert after_files == before_files, "research wrote into paper_state!"
    assert pf.read_bytes() == before_bytes, "portfolio.json mutated!"
    # Research outputs land in the research dir only.
    assert (out_dir / "detection_delay_report.md").exists()
    assert "INSUFFICIENT_DATA" in (out_dir /
                                   "detection_delay_report.md").read_text()


def test_run_shadow_classify_and_dedup(tmp_path):
    state_dir = tmp_path / "paper_state"
    (state_dir / "ledger").mkdir(parents=True)
    (state_dir / "ledger" / "trades.jsonl").write_text("")
    (state_dir / "portfolio.json").write_text(json.dumps({
        "portfolio": {"positions": {"AAA": {
            "symbol": "AAA", "signal_id": "sig-1", "entry_px": 100.0,
            "stop_px": 90.0, "tp1_px": 120.0,
            "entry_time": "2026-01-01T00:00:00+00:00",
            "risk_dollars": 100.0, "risk_frac": 0.1, "size": 1000.0}}},
        "schema": "x"}))
    out_dir = tmp_path / "research"
    out_dir.mkdir()

    def fake_bars(symbol):
        assert symbol == "AAA"
        return [
            {"t": "2026-01-01T04:00:00+00:00", "o": 100, "h": 101,
             "l": 99, "c": 105.0},
            {"t": "2026-01-01T08:00:00+00:00", "o": 105, "h": 106,
             "l": 104, "c": 104.0},
        ]

    c1 = run_shadow.classify_positions(
        state_dir=str(state_dir), out_dir=str(out_dir),
        bars_provider=fake_bars)
    assert c1["classified"] == 1
    log = [json.loads(l) for l in
           (out_dir / "shadow_log.jsonl").read_text().splitlines()]
    assert len(log) == 1
    assert log[0]["signal_id"] == "sig-1"
    assert log[0]["label"] in shadow.LABELS
    assert log[0]["inputs"]["r_now"] == pytest.approx(0.4)
    # Re-run: no duplicate appended.
    c2 = run_shadow.classify_positions(
        state_dir=str(state_dir), out_dir=str(out_dir),
        bars_provider=fake_bars)
    assert c2["classified"] == 0
    log2 = (out_dir / "shadow_log.jsonl").read_text().splitlines()
    assert len(log2) == 1
