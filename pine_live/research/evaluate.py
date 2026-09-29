"""Shadow advisor evaluation — pre-registered PASS/FAIL standard.

OBSERVATION ONLY. Implements SHADOW_ADVISOR_SPEC.md §5. Pure functions;
no I/O, no paper-state access, no side effects. Returns
INSUFFICIENT_SAMPLE until MIN_EVAL_TRADES evaluable trades exist; above
that, PASS requires ALL of (a) mean hypothetical R improvement,
(b) top-decile capture within tolerance, (c) no populated regime
degrading. "Average hypothetical R improved" alone is NOT a pass.
"""

from __future__ import annotations

import math

# Pre-registered constants (frozen in SHADOW_ADVISOR_SPEC.md §5-6).
TOLERANCE_TOP_DECILE_DEGRADATION = 0.10
"""Max points of top-decile capture the guidance may lose vs canonical."""

MIN_EVAL_TRADES = 30
"""Sample floor: below this many evaluable trades -> INSUFFICIENT_SAMPLE."""

REGIME_MIN_TRADES = 10
"""A regime bucket is 'sufficiently populated' at >= 10 evaluable trades."""

REGIME_UNDERPERF_TOL_R = 0.10
"""Max mean hypothetical-vs-canonical underperformance per regime, in R."""

STATUS_INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _mean(xs: list) -> float | None:
    return sum(xs) / len(xs) if xs else None


def evaluate_advisor(records: list | None) -> dict:
    """Apply the pre-registered PASS/FAIL standard.

    ``records``: counterfactual.jsonl records, each with signal_id,
    actual_net_r_25bps, hypothetical_net_r_25bps (finite when evaluable),
    exit_candidate_before_exit (bool), regime (nullable).

    Returns a dict with status INSUFFICIENT_SAMPLE | PASS | FAIL plus
    per-criterion detail. Never raises on malformed input.
    """
    recs = records if isinstance(records, list) else []
    evaluable = [
        r for r in recs
        if isinstance(r, dict)
        and _finite(r.get("actual_net_r_25bps"))
        and _finite(r.get("hypothetical_net_r_25bps"))
    ]
    n = len(evaluable)
    if n < MIN_EVAL_TRADES:
        return {
            "status": STATUS_INSUFFICIENT_SAMPLE,
            "n_evaluable": n,
            "min_required": MIN_EVAL_TRADES,
            "detail": (f"only {n} evaluable closed trades; "
                       f"need >= {MIN_EVAL_TRADES} for a verdict"),
            "criteria": None,
        }

    actual = [float(r["actual_net_r_25bps"]) for r in evaluable]
    hyp = [float(r["hypothetical_net_r_25bps"]) for r in evaluable]
    mean_actual = _mean(actual)
    mean_hyp = _mean(hyp)
    crit_a = mean_hyp > mean_actual

    # (b) top-decile capture: fraction of the top 10% by actual R that
    # guidance would have kept through the canonical exit.
    k = max(1, math.ceil(n / 10))
    top_idx = sorted(range(n), key=lambda i: actual[i], reverse=True)[:k]
    kept = sum(1 for i in top_idx
               if not evaluable[i].get("exit_candidate_before_exit"))
    capture = kept / k
    required_capture = 1.0 - TOLERANCE_TOP_DECILE_DEGRADATION
    crit_b = capture >= required_capture

    # (c) per-regime: no sufficiently populated regime degrades beyond
    # tolerance. Regimes below REGIME_MIN_TRADES are reported, not judged.
    regimes: dict = {}
    for r in evaluable:
        rg = r.get("regime")
        if isinstance(rg, str) and rg:
            regimes.setdefault(rg, []).append(r)
    regime_detail = {}
    crit_c = True
    for rg, rs in sorted(regimes.items()):
        deltas = [float(x["hypothetical_net_r_25bps"])
                  - float(x["actual_net_r_25bps"]) for x in rs]
        mean_delta = _mean(deltas)
        if len(rs) >= REGIME_MIN_TRADES:
            ok = mean_delta >= -REGIME_UNDERPERF_TOL_R
            crit_c = crit_c and ok
            regime_detail[rg] = {
                "n": len(rs), "judged": True,
                "mean_delta_r": mean_delta, "pass": ok,
            }
        else:
            regime_detail[rg] = {
                "n": len(rs), "judged": False,
                "mean_delta_r": mean_delta,
                "note": STATUS_INSUFFICIENT_SAMPLE,
            }

    passed = bool(crit_a and crit_b and crit_c)
    return {
        "status": STATUS_PASS if passed else STATUS_FAIL,
        "n_evaluable": n,
        "criteria": {
            "a_mean_improvement": {
                "pass": bool(crit_a),
                "mean_actual_r": mean_actual,
                "mean_hypothetical_r": mean_hyp,
            },
            "b_top_decile_capture": {
                "pass": bool(crit_b),
                "top_decile_n": k,
                "hypothetical_capture": capture,
                "canonical_capture": 1.0,
                "required_capture": required_capture,
                "tolerance": TOLERANCE_TOP_DECILE_DEGRADATION,
            },
            "c_regime_no_degradation": {
                "pass": bool(crit_c),
                "regimes": regime_detail,
            },
        },
    }
