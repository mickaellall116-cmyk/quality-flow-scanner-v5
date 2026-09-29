"""Tests for v54_rules.py — frozen hard gates + A/B/C grading.

These tests pin the frozen spec (chatgpt_handoff_brief.md). They must not
be weakened to make implementation easier: if a test fails, the
implementation is wrong, not the test.
"""

import pandas as pd

import v54_rules as v54


def _base_row(**overrides):
    row = {
        "entry": "YES",
        "protection": "SAFE",
        "state": "PULLBACK BUY",
        "above_vwap": True,
        "buy_zone": "100.00-110.00",
        "price": 105.0,
        "adx": 25.0,
        "daily_trend": "not_confirmed",
        "weekly_trend": "not_confirmed",
        "market_gate": "BLOCK",
    }
    row.update(overrides)
    return row


# ---- hard gates ------------------------------------------------------

def test_hard_gates_pass_structural_adx():
    ok, reasons = v54.v54_hard_gates_pass(_base_row())
    assert ok and reasons == []


def test_hard_gate_adx_below_20_fails():
    ok, reasons = v54.v54_hard_gates_pass(_base_row(adx=19.9))
    assert not ok
    assert any("ADX" in r for r in reasons)


def test_hard_gate_adx_exactly_20_passes():
    ok, _ = v54.v54_hard_gates_pass(_base_row(adx=20.0))
    assert ok


def test_hard_gate_structural_contract_entry_no_fails():
    ok, reasons = v54.v54_hard_gates_pass(_base_row(entry="WATCH"))
    assert not ok
    assert any("structural" in r for r in reasons)


def test_hard_gate_structural_contract_not_safe_fails():
    ok, _ = v54.v54_hard_gates_pass(_base_row(protection="WARNING"))
    assert not ok


def test_hard_gate_below_vwap_fails():
    ok, _ = v54.v54_hard_gates_pass(_base_row(above_vwap=False))
    assert not ok


def test_hard_gate_outside_buy_zone_fails():
    ok, _ = v54.v54_hard_gates_pass(_base_row(price=120.0))
    assert not ok


def test_hard_gate_fresh_buy_state_counts_as_structural():
    # BUY is in BUY_NOW_STATES alongside PULLBACK BUY (V5.3 contract)
    ok, _ = v54.v54_hard_gates_pass(_base_row(state="BUY"))
    assert ok


# ---- grading ----------------------------------------------------------

def test_grade_b_both_mtf_aligned():
    g = v54.v54_grade(_base_row(daily_trend="confirmed",
                                weekly_trend="confirmed",
                                market_gate="BLOCK"))
    assert g["eligible"] and g["grade"] == "B" and g["fully_confirmed"]


def test_grade_b_market_confirm_alone():
    g = v54.v54_grade(_base_row(daily_trend="not_confirmed",
                                weekly_trend="not_confirmed",
                                market_gate="CONFIRM"))
    assert g["eligible"] and g["grade"] == "B"


def test_grade_a_partial_confirmation_block_gate():
    g = v54.v54_grade(_base_row(daily_trend="not_confirmed",
                                weekly_trend="not_confirmed",
                                market_gate="BLOCK"))
    assert g["eligible"] and g["grade"] == "A"
    assert not g["fully_confirmed"] and g["context_known"]


def test_grade_a_daily_only_caution():
    g = v54.v54_grade(_base_row(daily_trend="confirmed",
                                weekly_trend="not_confirmed",
                                market_gate="CAUTION"))
    assert g["grade"] == "A"


def test_grade_c_unknown_weekly():
    g = v54.v54_grade(_base_row(daily_trend="not_confirmed",
                                weekly_trend="unknown",
                                market_gate="BLOCK"))
    assert g["eligible"] and g["grade"] == "C"
    assert not g["context_known"]


def test_grade_c_unknown_gate():
    g = v54.v54_grade(_base_row(market_gate="UNKNOWN"))
    assert g["grade"] == "C"


def test_grade_none_when_ineligible():
    g = v54.v54_grade(_base_row(adx=10.0))
    assert not g["eligible"] and g["grade"] is None


def test_annotate_attaches_v54_fields_without_mutating():
    row = _base_row()
    out = v54.v54_annotate(row)
    assert out["v54_eligible"] is True
    assert out["v54_grade"] == "A"
    assert out["v54_rule_version"] == v54.V54_RULE_VERSION
    assert out["v54_scanner_version"] == "5.4"
    assert "v54_grade" not in row  # input untouched


def test_annotate_marks_ineligible_rows():
    out = v54.v54_annotate(_base_row(adx=5.0))
    assert out["v54_eligible"] is False
    assert out["v54_grade"] is None


# ---- completed-bar predicate ------------------------------------------

def test_signal_bar_is_closed_past_bar():
    start = pd.Timestamp("2026-09-14 09:30", tz="America/New_York")
    assert v54.signal_bar_is_closed(start, "AAPL") is True


def test_signal_bar_is_closed_forming_bar():
    # a bar that opened 1h ago in ET is still forming (4h bars, 16:00 ET cap)
    start = pd.Timestamp.now(tz="America/New_York") - pd.Timedelta(hours=1)
    assert v54.signal_bar_is_closed(start, "AAPL") is False


def test_signal_bar_is_closed_crypto():
    start = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=5)
    assert v54.signal_bar_is_closed(start, "BTC-USD") is True
