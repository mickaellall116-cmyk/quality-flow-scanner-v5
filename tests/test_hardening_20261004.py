"""Hardening invariants (2026-10-04, branch hardening-20261004).

Item 1: V5.4 decision path must never reference filter_buy_now (V5.3 veto logic).
Item 2: Resampler call-site map — documents which constructor each production
         path uses. The frozen V5.4 affected-cohort path intentionally uses the
         legacy resample_closed_4h (pinned behavior); new research uses the
         session-anchored constructor.
Item 4: BEHAVIORAL differential test — score/rank-score fields must not alter
         V5.4 decisions. Mutates score fields across extreme/permuted values
         while holding true decision inputs constant; requires byte-identical
         decision outputs.

Evidence tier: builder-tested (Muse).
"""
import copy
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import v54_rules


# ---------------------------------------------------------------------------
# Item 1: filter_buy_now must not appear in the V5.4 decision path
# ---------------------------------------------------------------------------
V54_DECISION_FILES = [
    "v54_forward_harness.py",
    "v54_engine.py",
    "v54_rules.py",
    "v54_exit_tracker.py",
]


def test_v54_path_never_references_filter_buy_now():
    """Static invariant: the frozen V5.4 decision path must not call the
    V5.3 veto helper filter_buy_now. v54_rules.py documents this exclusion
    explicitly; this test makes it machine-checked."""
    violations = []
    for fname in V54_DECISION_FILES:
        path = os.path.join(HERE, fname)
        if not os.path.exists(path):
            continue
        in_docstring = False
        for i, line in enumerate(open(path).read().splitlines(), 1):
            stripped = line.strip()
            # Track multi-line docstrings (naive but sufficient for this repo)
            if stripped.startswith('"""') or stripped.startswith("'''"):
                # Single-line docstring: """...""" — skip, don't toggle
                q = '"""' if stripped.startswith('"""') else "'''"
                if stripped.count(q) == 2 and len(stripped) > 6:
                    continue
                in_docstring = not in_docstring
                continue
            if in_docstring or stripped.startswith("#"):
                continue
            if "filter_buy_now" in line:
                violations.append(f"{fname}:{i}: {stripped[:100]}")
    assert not violations, f"V5.4 path references filter_buy_now: {violations}"


def test_filter_buy_now_still_importable_for_api():
    """The API layer legitimately uses filter_buy_now; the quarantine is about
    the V5.4 path, not deletion."""
    import scanner_rules as sr
    assert callable(sr.filter_buy_now)
    import masterscanner_api  # noqa: F401  (import-time check only)


# ---------------------------------------------------------------------------
# Item 2: resampler call-site map
# ---------------------------------------------------------------------------
def test_resampler_call_site_map():
    """Documents (not enforces) which 4H constructor each production path
    selects, as proven 2026-10-04 by source audit:
      - v54_forward_harness.py affected-cohort path -> legacy resample_closed_4h
        (pinned; exits must evaluate on the exact legacy grid)
      - masterscanner_api.py -> legacy resample_closed_4h
      - replay_4h_corrected.py, top_broad_performance.py,
        data_inventory -> resample_closed_4h_session_anchored
    If this map changes, update it deliberately — do not let the legacy
    constructor spread silently."""
    harness_src = open(os.path.join(HERE, "v54_forward_harness.py")).read()
    # The frozen affected-cohort path pins the legacy constructor by name.
    assert "sr.resample_closed_4h(raw, symbol)" in harness_src, \
        "frozen harness affected-cohort resampler call site changed"
    # The legacy function must carry its LEGACY marker.
    import scanner_rules as sr
    assert "LEGACY" in (sr.resample_closed_4h.__doc__ or ""), \
        "legacy resampler lost its LEGACY marker"
    assert "resample_closed_4h_session_anchored" in (sr.resample_closed_4h.__doc__ or ""), \
        "legacy resampler docstring must point at the corrected constructor"


# ---------------------------------------------------------------------------
# Item 4: behavioral differential test — scores must not gate decisions
# ---------------------------------------------------------------------------
SCORE_FIELDS = ["score", "v53_score", "v53_rank_score"]

SCORE_MUTATIONS = [
    0, 1, 150, -1, -999, 999999, -999999,
    3.14159, None, "", "BUY", "not_a_number",
    float("inf"), -float("inf"),
]

DECISION_KEYS = ["v54_eligible", "v54_grade", "v54_grade_label",
                 "v54_grade_reasons", "fully_confirmed", "context_known"]


def _base_row():
    """A fully eligible V5.4 candidate row with fixed decision inputs."""
    return {
        "symbol": "TEST",
        "entry": "YES",
        "protection": "SAFE",
        "state": "BUY",
        "above_vwap": True,
        "price": 100.0,
        "buy_zone": "95.0-105.0",
        "zone_low": 95.0,
        "zone_high": 105.0,
        "adx": 25.0,
        "daily_trend": "confirmed",
        "weekly_trend": "not_confirmed",
        "market_gate": "CAUTION",
        # score fields under test (baseline values)
        "score": 80,
        "v53_score": 80,
        "v53_rank_score": 95,
    }


def _decision_snapshot(row):
    out = v54_rules.v54_annotate(row)
    return {k: out.get(k) for k in DECISION_KEYS}


def test_scores_do_not_gate_eligible_row():
    """Mutate every score field across extremes on an eligible row;
    all V5.4 decision outputs must be byte-identical."""
    baseline = _decision_snapshot(_base_row())
    assert baseline["v54_eligible"] is True  # sanity: fixture is eligible
    for field in SCORE_FIELDS:
        for val in SCORE_MUTATIONS:
            row = _base_row()
            row[field] = val
            got = _decision_snapshot(row)
            assert got == baseline, (
                f"score field {field}={val!r} altered V5.4 decision: "
                f"{json.dumps(got, default=str)} != {json.dumps(baseline, default=str)}"
            )


def test_scores_do_not_gate_ineligible_row():
    """Same mutations on an ineligible row (ADX below gate)."""
    baseline_row = _base_row()
    baseline_row["adx"] = 10.0
    baseline = _decision_snapshot(baseline_row)
    assert baseline["v54_eligible"] is False
    for field in SCORE_FIELDS:
        for val in SCORE_MUTATIONS:
            row = copy.deepcopy(baseline_row)
            row[field] = val
            got = _decision_snapshot(row)
            assert got == baseline, (
                f"score field {field}={val!r} altered ineligible-row decision"
            )


def test_scores_do_not_gate_grade_variants():
    """Cover grade B (fully confirmed) and grade C (unknown context) paths."""
    variants = [
        {"daily_trend": "confirmed", "weekly_trend": "confirmed",
         "market_gate": "CONFIRM"},   # -> B
        {"daily_trend": "unknown", "weekly_trend": "unknown",
         "market_gate": "UNKNOWN"},   # -> C
    ]
    for v in variants:
        base = _base_row()
        base.update(v)
        baseline = _decision_snapshot(base)
        for field in SCORE_FIELDS:
            for val in SCORE_MUTATIONS:
                row = copy.deepcopy(base)
                row[field] = val
                got = _decision_snapshot(row)
                assert got == baseline, (
                    f"variant {v}: field {field}={val!r} altered decision"
                )


def test_score_fields_absent_from_grade_source():
    """Defense in depth: v54_grade must not read score fields at all.
    (Static supplement to the behavioral test above.)"""
    import inspect
    src = inspect.getsource(v54_rules.v54_grade)
    src += inspect.getsource(v54_rules.v54_hard_gates_pass)
    for field in SCORE_FIELDS:
        assert f'"{field}"' not in src and f"'{field}'" not in src, \
            f"v54_grade reads score field {field}"
