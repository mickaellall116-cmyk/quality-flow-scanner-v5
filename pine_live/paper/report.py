"""The three-question paper-phase report.

Reads paper_state/ (status.json + ledger/) and writes report.md +
report.json. Answers ONLY:

  Q1. Does the system behave exactly as specified?
      (packets replayed vs mismatches, cycles run, decisions logged,
      halt state, per-cycle completeness.)
  Q2. Does execution remain within the tested cost envelope?
      (realized round-trip cost/trade vs the 25bps envelope, total
      execution leakage, detection-delay distribution, and the
      plain-English fill-assumption line.)
  Q3. Is realized behavior statistically plausible vs the validated
      backtest? (win rate with exact binomial 95% CI, expectancy at both
      cost legs, avg win/loss, max drawdown, longest losing streak,
      reason-code distribution — all vs the locked C1 expectations,
      with the explicit small-sample caveat.)

This module never touches strategy parameters and never writes trading
state; it only reads.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone

from pine_live.paper.ledger import read_jsonl
from pine_live.paper.verify import halt_path

import pine_backtest as pb  # noqa: E402  (START_EQUITY for equity curves)

# Locked C1 expectations (@4bps primary leg; 25bps retail leg).
LOCKED_4BPS = {
    "trades": 143, "win_rate": 0.462, "expectancy_r": 0.337,
    "total_return_pct": 52.25, "max_dd": 0.3163, "calmar": 1.65,
    "pf": 1.49, "avg_win_r": 2.212, "avg_loss_r": -1.27,
}
LOCKED_25BPS = {
    "trades": 142, "win_rate": 0.458, "expectancy_r": 0.280,
    "total_return_pct": 39.64, "max_dd": 0.3379, "calmar": 1.173,
}
LOCKED_REASONS = {"TAKEN": 143, "RANKED_OUT": 94, "SECTOR_CAP": 16,
                  "NO_SLOT": 0, "RISK_CAP": 10}
COST_25BPS = 0.0025

# Dual-ledger production gate (PROPOSED -- pending Mike's sign-off, see
# PAPER.md; reported only, NEVER enforced as a halt). No real-money
# deployment until: (a) achievable-fill expectancy >= +0.15R/trade,
# (b) mean detection-delay cost <= 108bps/trade (the validated execution
# headroom: the 25bps-cost backtest did +0.280R/trade vs +0.337R at 4bps),
# (c) a real-time feed exists that eliminates or directly quantifies
# detection latency (human attestation, machine can never self-certify).
GATE_MIN_TRADES = 20
GATE_MIN_ACH_EXPECTANCY_R = 0.15
GATE_MAX_MEAN_DRAG_BPS = 108.0
GATE_C_ATTESTATION_FILE = "gate_c_attestation.json"
GATE_C_REQUIRED_KEYS = ("attested_by", "attested_at", "feed", "latency")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _binom_exact_ci(wins: int, n: int, cl: float = 0.95) -> tuple:
    """Clopper-Pearson exact binomial CI via the beta quantiles."""
    if n == 0:
        return (0.0, 1.0)
    from scipy.stats import beta
    alpha = 1.0 - cl
    lo = 0.0 if wins == 0 else float(beta.ppf(alpha / 2, wins, n - wins + 1))
    hi = 1.0 if wins == n else float(beta.ppf(1 - alpha / 2, wins + 1, n - wins))
    return (lo, hi)


def _quantile(xs: list, q: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    pos = q * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _mean(xs: list) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def _median(xs: list) -> float:
    if not xs:
        return float("nan")
    return _quantile(xs, 0.5)


def _gate_c_attestation(state_dir: str) -> dict:
    """Gate (c): real-time feed attestation. A machine can never
    self-certify this leg: it is ATTESTED only when a human writes
    paper_state/gate_c_attestation.json with the required keys."""
    path = os.path.join(state_dir, GATE_C_ATTESTATION_FILE)
    if not os.path.exists(path):
        return {"status": "NOT_ATTESTED",
                "detail": f"{GATE_C_ATTESTATION_FILE} not present; "
                          "no real-time feed has been attested"}
    try:
        with open(path) as f:
            att = json.load(f)
    except (OSError, ValueError) as exc:
        return {"status": "NOT_ATTESTED",
                "detail": f"attestation file unreadable: {exc}"}
    missing = [k for k in GATE_C_REQUIRED_KEYS if not att.get(k)]
    if missing:
        return {"status": "NOT_ATTESTED",
                "detail": f"attestation missing keys {missing}"}
    return {"status": "ATTESTED",
            "detail": f"attested by {att['attested_by']} at "
                      f"{att['attested_at']}: {att['feed']} "
                      f"(latency: {att['latency']})"}


def build_execution_realism(state_dir: str) -> dict:
    """Canonical-vs-achievable dual ledger + the proposed production gate.

    Every closed paper trade carries both fills (see pine_live/paper/dual.py
    for the exact achievable-fill definition). This section reports the two
    R/trade figures, the mean/median detection-delay drag in bps, both
    realized equity curves, and the gate status. Below GATE_MIN_TRADES dual
    trades the gate reports INSUFFICIENT_DATA -- never inferred.
    """
    ledger_dir = os.path.join(state_dir, "ledger")
    trades = read_jsonl(os.path.join(ledger_dir, "trades.jsonl"))
    dual = [t for t in trades
            if t.get("ach_net_r_4bps") is not None
            and t.get("drag_bps") is not None
            and t.get("net_r_4bps") is not None
            and t.get("risk_dollars") is not None]
    dual.sort(key=lambda t: t["exit_time"])
    n_dual, n_total = len(dual), len(trades)

    canon_r4 = [t["net_r_4bps"] for t in dual]
    canon_r25 = [t["net_r_25bps"] for t in dual if t.get("net_r_25bps")
                 is not None]
    ach_r4 = [t["ach_net_r_4bps"] for t in dual]
    ach_r25 = [t["ach_net_r_25bps"] for t in dual if t.get("ach_net_r_25bps")
               is not None]
    drag_bps = [t["drag_bps"] for t in dual]
    drag_r4 = [t["drag_r_4bps"] for t in dual if t.get("drag_r_4bps")
               is not None]

    # Realized equity curves, stepped at each trade's exit (realized-only;
    # open positions are marked in equity.jsonl, not re-priced here).
    canon_curve, ach_curve = [], []
    ce = ae = float(pb.START_EQUITY)
    for t in dual:
        ce += t["net_r_4bps"] * t["risk_dollars"]
        ae += t["ach_net_r_4bps"] * t["risk_dollars"]
        canon_curve.append([t["exit_time"], round(ce, 2)])
        ach_curve.append([t["exit_time"], round(ae, 2)])

    stats = {
        "n_trades_total": n_total,
        "n_trades_dual": n_dual,
        "n_trades_missing_achievable": n_total - n_dual,
        "canonical_r_per_trade_4bps": (round(_mean(canon_r4), 4)
                                       if canon_r4 else None),
        "canonical_r_per_trade_25bps": (round(_mean(canon_r25), 4)
                                        if canon_r25 else None),
        "achievable_r_per_trade_4bps": (round(_mean(ach_r4), 4)
                                        if ach_r4 else None),
        "achievable_r_per_trade_25bps": (round(_mean(ach_r25), 4)
                                         if ach_r25 else None),
        "mean_drag_bps_per_trade": (round(_mean(drag_bps), 2)
                                    if drag_bps else None),
        "median_drag_bps_per_trade": (round(_median(drag_bps), 2)
                                      if drag_bps else None),
        "mean_drag_r_4bps_per_trade": (round(_mean(drag_r4), 4)
                                       if drag_r4 else None),
        "max_drag_bps": round(max(drag_bps), 2) if drag_bps else None,
        "min_drag_bps": round(min(drag_bps), 2) if drag_bps else None,
        "realized_equity_canonical": canon_curve,
        "realized_equity_achievable": ach_curve,
        "definition": (
            "canonical fill = next bar's OPEN (the backtest assumption); "
            "achievable fill = last visible price at detection: CLOSE of "
            "the signal bar (entries) / CLOSE of the exit-trigger bar "
            "(exits), under the current achievable-fill policy "
            "'signal-bar-close-at-detection'. This is the honest "
            "conservative proxy for what the hourly-polling architecture "
            "can do today, not necessarily the eventual production fill: "
            "when a real-time feed lands, the policy upgrades to "
            "first-actionable-quote. Gate thresholds are unchanged by the "
            "policy. Positive drag = achievable worse. See "
            "pine_live/paper/dual.py."),
    }

    # --- the proposed production gate ----------------------------------
    gate_c = _gate_c_attestation(state_dir)
    if n_dual < GATE_MIN_TRADES:
        gate = {
            "status": "INSUFFICIENT_DATA",
            "n_dual_trades": n_dual,
            "min_trades_required": GATE_MIN_TRADES,
            "detail": (f"only {n_dual} closed paper trades with dual data; "
                       f"need >= {GATE_MIN_TRADES}. Nothing is inferred."),
            "gate_a": {"status": "INSUFFICIENT_DATA"},
            "gate_b": {"status": "INSUFFICIENT_DATA"},
            "gate_c": gate_c,
        }
        return {**stats, "production_gate_proposed": gate}

    exp_ach = _mean(ach_r4)
    mean_drag = _mean(drag_bps)
    gate_a = {
        "status": "PASS" if exp_ach >= GATE_MIN_ACH_EXPECTANCY_R else "FAIL",
        "achievable_expectancy_r_4bps": round(exp_ach, 4),
        "threshold_r": GATE_MIN_ACH_EXPECTANCY_R,
    }
    gate_b = {
        "status": "PASS" if mean_drag <= GATE_MAX_MEAN_DRAG_BPS else "FAIL",
        "mean_drag_bps": round(mean_drag, 2),
        "threshold_bps": GATE_MAX_MEAN_DRAG_BPS,
    }
    if gate_a["status"] == "FAIL" or gate_b["status"] == "FAIL":
        overall, reason = "FAIL", "a measured leg failed its threshold"
    elif gate_c["status"] != "ATTESTED":
        overall, reason = "FAIL", ("blocked: no attested real-time feed "
                                   "(gate c); deployment not allowed")
    else:
        overall, reason = "PASS", "all three legs satisfied"
    gate = {
        "status": overall,
        "n_dual_trades": n_dual,
        "min_trades_required": GATE_MIN_TRADES,
        "detail": reason,
        "gate_a": gate_a,
        "gate_b": gate_b,
        "gate_c": gate_c,
        "note": ("PROPOSED gate -- pending Mike's sign-off; reported only, "
                 "never enforced as a halt."),
    }
    return {**stats, "production_gate_proposed": gate}


def build_report(state_dir: str) -> dict:
    """Compute the full report dict from paper_state/."""
    ledger_dir = os.path.join(state_dir, "ledger")
    status_path = os.path.join(state_dir, "status.json")
    status = {}
    if os.path.exists(status_path):
        with open(status_path) as f:
            status = json.load(f)
    cycles = status.get("cycles", [])
    decisions = read_jsonl(os.path.join(ledger_dir, "decisions.jsonl"))
    fills = read_jsonl(os.path.join(ledger_dir, "fills.jsonl"))
    trades = read_jsonl(os.path.join(ledger_dir, "trades.jsonl"))
    rejections = read_jsonl(os.path.join(ledger_dir, "rejections.jsonl"))
    equity = read_jsonl(os.path.join(ledger_dir, "equity.jsonl"))
    halted = os.path.exists(halt_path(state_dir))

    # ------------------------------------------------------------- Q1
    n_replayed = status.get("packets_replayed", 0)
    n_mismatch = status.get("replay_mismatches", 0)
    refused_cycles = [c for c in cycles
                      if c.get("timestamp_status") == "refused"]
    failed_closed_cycles = [c for c in cycles
                            if c.get("timestamp_status") == "failed_closed"]
    # Completeness: every cycle's evaluated symbols must reconcile to
    # signals + refusals + skips (+ pending entries, which are signals
    # whose entry bar was not yet in frame).
    incomplete = []
    for c in cycles:
        lhs = c.get("evaluated", 0)
        rhs = (c.get("signals", 0) + c.get("skipped", 0)
               + c.get("pending_entry", 0))
        if lhs != rhs:
            incomplete.append({"bar_time": c.get("bar_time"),
                               "evaluated": lhs,
                               "signals+skipped+pending": rhs})
    reason_counts: dict = {}
    for d in decisions:
        reason_counts[d["decision"]] = reason_counts.get(d["decision"], 0) + 1
    q1 = {
        "halted": halted,
        "cycles_run": len(cycles),
        "packets_replayed": n_replayed,
        "replay_mismatches": n_mismatch,
        "replay_clean": n_mismatch == 0,
        "decisions_logged": len(decisions),
        "fills_logged": len(fills),
        "trades_completed": len(trades),
        "rejections_logged": len(rejections),
        "refused_timestamps": len(refused_cycles),
        "failed_closed_timestamps": len(failed_closed_cycles),
        "incomplete_cycles": incomplete,
        "completeness_ok": not incomplete,
        "reason_counts": reason_counts,
        "verdict": ("HALTED" if halted else
                    "CLEAN" if (n_mismatch == 0 and not incomplete)
                    else "ATTENTION"),
    }

    # ------------------------------------------------------------- Q2
    delays = [f["detection_delay_minutes"] for f in fills
              if f.get("detection_delay_minutes") is not None]
    cycle_delays = [c["detection_delay_minutes"] for c in cycles
                    if c.get("detection_delay_minutes") is not None]
    exit_fills = [f for f in fills if f.get("kind") == "exit"]
    # Realized round-trip cost per completed trade at the 25bps leg:
    # (net_4bps - net_25bps) in R * risk_dollars -> dollars of extra cost.
    extra_cost_dollars = [
        (t["net_r_4bps"] - t["net_r_25bps"]) * t["risk_dollars"]
        for t in trades]
    avg_extra_cost = _mean(extra_cost_dollars)
    # Leakage: fill deviation in R (should be 0 by construction in paper).
    leak_r = [f["deviation_r"] for f in fills]
    total_leak_r = sum(abs(x) for x in leak_r)
    # Envelope check: mean per-trade round-trip cost dollars vs what the
    # 25bps leg assumes (cost * notional).
    modeled_25bps_cost = [COST_25BPS * t["size"] for t in trades]
    q2 = {
        "n_fills": len(fills),
        "total_fill_deviation_r": round(total_leak_r, 6),
        "max_abs_fill_deviation_r": round(max((abs(x) for x in leak_r),
                                             default=0.0), 6),
        "fills_match_theory": total_leak_r == 0.0,
        "avg_extra_cost_25bps_vs_4bps_dollars": (
            round(avg_extra_cost, 4) if extra_cost_dollars else None),
        "avg_modeled_25bps_roundtrip_cost_dollars": (
            round(_mean(modeled_25bps_cost), 4) if modeled_25bps_cost
            else None),
        "n_exit_fills": len(exit_fills),
        "detection_delay_minutes": {
            "n": len(cycle_delays),
            "median": round(_quantile(cycle_delays, 0.5), 1)
            if cycle_delays else None,
            "p95": round(_quantile(cycle_delays, 0.95), 1)
            if cycle_delays else None,
            "max": round(max(cycle_delays), 1) if cycle_delays else None,
        },
        "plain_english": (
            "paper fills assume execution at the bar open; "
            + (f"median detection delay was "
               f"{_quantile(cycle_delays, 0.5):.1f} min "
               f"(p95 {_quantile(cycle_delays, 0.95):.1f} min) over "
               f"{len(cycle_delays)} cycles."
               if cycle_delays else
               "no cycles have run yet, so no delay observed.")),
    }

    # ------------------------------------------------------------- Q3
    def _trade_stats(key: str) -> dict:
        rs = [t[key] for t in trades]
        wins = [r for r in rs if r > 0]
        losses = [r for r in rs if r <= 0]
        n = len(rs)
        wr = len(wins) / n if n else float("nan")
        lo, hi = _binom_exact_ci(len(wins), n)
        exp = _mean(rs)
        # Normal-approx 95% CI for the mean (diagnostic only).
        sd = math.sqrt(_mean([(r - exp) ** 2 for r in rs])) if n > 1 else 0.0
        se = sd / math.sqrt(n) if n else float("nan")
        return {
            "n": n, "win_rate": round(wr, 4) if n else None,
            "win_rate_ci95": [round(lo, 4), round(hi, 4)],
            "expectancy_r": round(exp, 4) if n else None,
            "expectancy_ci95": ([round(exp - 1.96 * se, 4),
                                 round(exp + 1.96 * se, 4)] if n > 1
                                else None),
            "avg_win_r": round(_mean(wins), 4) if wins else None,
            "avg_loss_r": round(_mean(losses), 4) if losses else None,
            "profit_factor": (round(sum(wins) / abs(sum(losses)), 3)
                              if losses and sum(losses) != 0 else None),
        }
    s4 = _trade_stats("net_r_4bps")
    s25 = _trade_stats("net_r_25bps")
    # Longest losing streak (net <= 0) in close order.
    ordered = sorted(trades, key=lambda t: t["exit_time"])
    longest = cur = 0
    for t in ordered:
        cur = cur + 1 if t["net_r_4bps"] <= 0 else 0
        longest = max(longest, cur)
    max_dd = max((e["max_dd"] for e in equity), default=0.0)
    # Reason-code distribution vs locked (proportional comparison).
    locked_total = sum(LOCKED_REASONS.values())
    reason_vs_locked = {
        code: {"paper": reason_counts.get(code, 0),
               "locked": LOCKED_REASONS[code],
               "locked_share": round(LOCKED_REASONS[code] / locked_total, 4)}
        for code in LOCKED_REASONS}
    n = s4["n"]
    caveat = (f"n={n} paper trades: plausibility means cannot-reject, not "
              f"proven. At ~1.4 trades/week the 8-week phase expects ~11 "
              f"trades; statistical power is low by design — the phase "
              f"tests engineering fidelity, not edge.")
    q3 = {
        "at_4bps": {**s4, "locked": LOCKED_4BPS,
                    "win_rate_in_locked_ci":
                        (s4["win_rate_ci95"][0] <= LOCKED_4BPS["win_rate"]
                         <= s4["win_rate_ci95"][1]) if n else None,
                    "expectancy_in_ci":
                        (s4["expectancy_ci95"][0] <=
                         LOCKED_4BPS["expectancy_r"] <=
                         s4["expectancy_ci95"][1]) if n and s4["expectancy_ci95"]
                        else None},
        "at_25bps": {**s25, "locked": LOCKED_25BPS},
        "max_drawdown": round(max_dd, 4),
        "locked_max_dd": LOCKED_4BPS["max_dd"],
        "longest_losing_streak": longest,
        "reason_codes_vs_locked": reason_vs_locked,
        "caveat": caveat,
    }

    return {
        "generated_at": _utcnow_iso(),
        "state_dir": state_dir,
        "halted": halted,
        "q1_spec_conformance": q1,
        "q2_cost_envelope": q2,
        "execution_realism": build_execution_realism(state_dir),
        "q3_statistical_plausibility": q3,
    }


def render_markdown(rep: dict) -> str:
    """Render the report dict as Markdown."""
    q1, q2, q3 = (rep["q1_spec_conformance"], rep["q2_cost_envelope"],
                  rep["q3_statistical_plausibility"])
    ex = rep.get("execution_realism", {})
    L = []
    A = L.append
    A("# Pine V3.6 Paper Phase — Three-Question Report")
    A("")
    A(f"Generated: {rep['generated_at']}  |  "
      f"Halted: {'YES' if rep['halted'] else 'no'}")
    A("")
    A("## Q1 — Does the system behave exactly as specified?")
    A("")
    A(f"- Cycles run: {q1['cycles_run']}")
    A(f"- Packets replayed: {q1['packets_replayed']}, "
      f"mismatches: {q1['replay_mismatches']} "
      f"({'CLEAN' if q1['replay_clean'] else 'HALT CONDITION'})")
    A(f"- Decisions logged: {q1['decisions_logged']} | fills: "
      f"{q1['fills_logged']} | completed trades: {q1['trades_completed']} "
      f"| rejections: {q1['rejections_logged']}")
    A(f"- Refused timestamps: {q1['refused_timestamps']} | "
      f"failed-closed timestamps: {q1['failed_closed_timestamps']}")
    A(f"- Cycle completeness: "
      f"{'OK' if q1['completeness_ok'] else 'BROKEN — see incomplete_cycles'}")
    A(f"- Reason codes: {json.dumps(q1['reason_counts'], sort_keys=True)}")
    A(f"- **Verdict: {q1['verdict']}**")
    A("")
    A("## Q2 — Does execution remain within the tested cost envelope?")
    A("")
    A(f"- Fills logged: {q2['n_fills']} "
      f"({q2['n_exit_fills']} exits); total fill deviation: "
      f"{q2['total_fill_deviation_r']} R "
      f"(max abs {q2['max_abs_fill_deviation_r']} R)")
    A(f"- Fills match theory: "
      f"{'yes (0.0 R deviation)' if q2['fills_match_theory'] else 'NO — investigate'}")
    A(f"- Avg extra cost/trade at 25bps vs 4bps: "
      f"{q2['avg_extra_cost_25bps_vs_4bps_dollars']} $ "
      f"(modeled 25bps round-trip: "
      f"{q2['avg_modeled_25bps_roundtrip_cost_dollars']} $)")
    d = q2["detection_delay_minutes"]
    A(f"- Detection delay: n={d['n']}, median={d['median']} min, "
      f"p95={d['p95']} min, max={d['max']} min")
    A(f"- {q2['plain_english']}")
    A("")
    A("## Execution realism: canonical vs achievable")
    A("")
    A(f"- {ex.get('definition', '')}")
    A(f"- Closed trades with dual data: {ex.get('n_trades_dual')} "
      f"(of {ex.get('n_trades_total')} total; "
      f"{ex.get('n_trades_missing_achievable')} missing achievable data)")
    cr4 = ex.get('canonical_r_per_trade_4bps')
    ar4 = ex.get('achievable_r_per_trade_4bps')
    cr25 = ex.get('canonical_r_per_trade_25bps')
    ar25 = ex.get('achievable_r_per_trade_25bps')
    if ex.get('n_trades_dual'):
        A(f"- Expectancy/trade, 4bps leg: canonical {cr4:+.4f} R | "
          f"achievable {ar4:+.4f} R")
        A(f"- Expectancy/trade, 25bps leg: canonical {cr25:+.4f} R | "
          f"achievable {ar25:+.4f} R")
        A(f"- Detection-delay drag: mean {ex['mean_drag_bps_per_trade']:+.1f} "
          f"bps/trade (median {ex['median_drag_bps_per_trade']:+.1f}; "
          f"range {ex['min_drag_bps']:+.1f} to {ex['max_drag_bps']:+.1f}; "
          f"mean {ex['mean_drag_r_4bps_per_trade']:+.4f} R)")
        ce = ex["realized_equity_canonical"]
        ae = ex["realized_equity_achievable"]
        A(f"- Realized equity (from $10,000): canonical "
          f"${ce[-1][1]:,.2f} | achievable ${ae[-1][1]:,.2f}")
    else:
        A("- No closed trades with dual data yet.")
    g = ex.get("production_gate_proposed", {})
    A("- **Production gate (PROPOSED -- pending Mike's sign-off; "
      "reported only, never a halt):**")
    A(f"  - Overall: **{g.get('status')}** -- {g.get('detail')}")
    ga, gb, gc = g.get("gate_a", {}), g.get("gate_b", {}), g.get("gate_c", {})
    if g.get("status") == "INSUFFICIENT_DATA":
        A(f"  - (a)/(b): INSUFFICIENT_DATA "
          f"(need >= {g.get('min_trades_required')} dual trades)")
    else:
        A(f"  - (a) achievable expectancy >= +0.15R/trade: {ga['status']} "
          f"({ga['achievable_expectancy_r_4bps']:+.4f} R)")
        A(f"  - (b) mean drag <= 108bps/trade: {gb['status']} "
          f"({gb['mean_drag_bps']:+.1f} bps)")
    A(f"  - (c) real-time feed attested: {gc.get('status')} -- "
      f"{gc.get('detail')}")
    A("")
    A("## Q3 — Is realized behavior statistically plausible vs the backtest?")
    A("")
    for leg, key in (("4bps", "at_4bps"), ("25bps", "at_25bps")):
        s = q3[key]
        lk = s["locked"]
        A(f"### {leg} leg (n={s['n']})")
        if s["n"]:
            A(f"- Win rate: {s['win_rate']:.1%} "
              f"(exact 95% CI {s['win_rate_ci95'][0]:.1%}–{s['win_rate_ci95'][1]:.1%}; "
              f"locked {lk['win_rate']:.1%})")
            ci = (f"{s['expectancy_ci95'][0]:+.3f} to "
                  f"{s['expectancy_ci95'][1]:+.3f} R"
                  if s["expectancy_ci95"] else "n/a (n<2)")
            A(f"- Expectancy: {s['expectancy_r']:+.3f} R/trade "
              f"(95% CI {ci}; locked {lk['expectancy_r']:+.3f})")
            aw = (f"{s['avg_win_r']:+.3f} R"
                  if s["avg_win_r"] is not None else "n/a")
            al = (f"{s['avg_loss_r']:+.3f} R"
                  if s["avg_loss_r"] is not None else "n/a")
            law = (f"{lk['avg_win_r']:+.3f}"
                   if lk.get("avg_win_r") is not None else "n/a")
            lal = (f"{lk['avg_loss_r']:+.3f}"
                   if lk.get("avg_loss_r") is not None else "n/a")
            A(f"- Avg win {aw} / avg loss {al} "
              f"(locked {law} / {lal})")
            A(f"- Profit factor: {s['profit_factor']} "
              f"(locked {lk.get('pf', 'n/a')})")
        else:
            A("- No completed trades yet.")
    A(f"- Max drawdown: {q3['max_drawdown']:.2%} "
      f"(locked {q3['locked_max_dd']:.2%})")
    A(f"- Longest losing streak: {q3['longest_losing_streak']} trades")
    A("- Reason codes (paper vs locked):")
    for code, v in q3["reason_codes_vs_locked"].items():
        A(f"  - {code}: paper {v['paper']} / locked {v['locked']} "
          f"(locked share {v['locked_share']:.1%})")
    A("")
    A(f"*{q3['caveat']}*")
    A("")
    return "\n".join(L) + "\n"


def write_report(state_dir: str) -> dict:
    """Build the report and write report.json + report.md. Returns the dict."""
    rep = build_report(state_dir)
    for name, body in (("report.json", json.dumps(rep, indent=1,
                                                  sort_keys=True,
                                                  default=str)),
                       ("report.md", render_markdown(rep))):
        path = os.path.join(state_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
            f.flush()
            os.fsync(f.fileno())
    return rep
