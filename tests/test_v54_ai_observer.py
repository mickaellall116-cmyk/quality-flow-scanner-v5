"""Tests for the AI Observer (AI-OBS-v1) layer.

Verifies: grade/judgment fields never reach the observer snapshot, the
assessment schema validates, the log is append-only and idempotent, and
the machine-readable export is well-formed.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import v54_forward_harness as hz


def _sample_row():
    return {
        "symbol": "INTC", "theme": "Forward-UX51", "timeframe": "4h",
        "signal_bar_start_at": "2026-09-15T06:30:00-04:00",
        "signal_bar_close_at": "2026-09-15T10:30:00-04:00",
        "state": "PULLBACK BUY", "entry": "YES", "protection": "SAFE",
        "price": 99.25, "stop": 95.80, "tp1": 107.80, "risk_reward": 2.474,
        "buy_zone": "97.72-100.39", "above_vwap": True,
        "ema9": 99.87, "ema21": 99.06, "ema55": 96.76, "ema200": 98.13,
        "adx": 21.01, "rel_vol": 0.9007,
        "market_gate": "CAUTION", "market_regime": "RISK-OFF",
        "daily_trend": "not_confirmed", "weekly_trend": "confirmed",
        "confirmation_15m": False, "confirmation_15m_rel_vol": 0.514,
        "pm_gap_pct": 1.76, "pm_range_pct": 3.14, "pm_read": "NEUTRAL",
        "v53_state": "PULLBACK BUY", "v53_entry": "WATCH",
        "v53_would_veto": True,
        # Judgment fields that must NEVER reach the observer:
        "v54_grade": "A", "v54_grade_label": "EARLY",
        "v54_grade_reasons": ["early/partial confirmation"],
        "v54_eligible": True,
        "score": 90, "v53_score": 90, "v53_rank_score": 112,
        "v54_rule_version": "2026-09-15-v54", "v54_scanner_version": "5.4",
    }


def _good_assessment(sid="v54:TEST:4h:2026-09-15T10:30:00-04:00:2026-09-15-v54"):
    return {
        "signal_id": sid,
        "observer": "AI-OBS-v1",
        "prompt_version": "v1",
        "assessed_at": "2026-09-15T17:50:00+00:00",
        "classification": "NEUTRAL",
        "confidence": 55,
        "reasons": ["ADX barely above threshold at 21.0",
                    "RVOL 0.90 shows no accumulation"],
        "primary_risk": "Thin momentum with gate CAUTION.",
        "invalidation": "A high-volume 4H close above TP1.",
        "timing": "EARLY",
        "features": hz.observer_snapshot_from_row(sid, _sample_row()),
    }


def test_snapshot_excludes_grade_and_scores():
    snap = hz.observer_snapshot_from_row("sid-1", _sample_row())
    for k in ("v54_grade", "v54_grade_label", "v54_grade_reasons",
              "v54_eligible", "score", "v53_score", "v53_rank_score"):
        assert k not in snap, f"judgment field leaked: {k}"


def test_snapshot_keeps_raw_fields_and_derived_levels():
    snap = hz.observer_snapshot_from_row("sid-1", _sample_row())
    for k in ("symbol", "signal_bar_start_at", "stop", "tp1", "adx",
              "rel_vol", "market_gate", "daily_trend", "weekly_trend",
              "risk_reward", "v53_would_veto", "pm_gap_pct",
              "confirmation_15m"):
        assert k in snap, f"raw field missing: {k}"
    assert snap["entry_plan"].startswith("next 4H bar open")
    assert snap["ref_price"] == pytest.approx(99.25)
    # plus1r_ref = ref + (ref - stop)
    assert snap["plus1r_ref_price"] == pytest.approx(99.25 + (99.25 - 95.80))


def test_snapshot_tripwire_fires_on_judgment_allowlist():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(hz, "_OBS_RAW_FIELDS",
                   hz._OBS_RAW_FIELDS + ["v54_grade"])
        with pytest.raises(AssertionError):
            hz.observer_snapshot_from_row("sid-1", _sample_row())


def test_validate_accepts_good_assessment():
    assert hz.validate_assessment(_good_assessment()) == []


def test_validate_rejects_each_bad_field():
    base = _good_assessment()
    cases = [
        ("classification", "BULLISH"),
        ("confidence", 101),
        ("confidence", "high"),
        ("reasons", ["only one"]),
        ("reasons", ["a", "b", "c", "d", "e"]),
        ("primary_risk", ""),
        ("invalidation", "   "),
        ("timing", "LATE"),
        ("observer", "AI-OBS-v2"),
        ("features", "not-a-dict"),
    ]
    for key, bad in cases:
        obj = dict(base)
        obj[key] = bad
        errs = hz.validate_assessment(obj)
        assert errs, f"no error for bad {key}={bad!r}"


def test_validate_rejects_grade_leak_in_features():
    obj = _good_assessment()
    obj["features"] = dict(obj["features"])
    obj["features"]["v54_grade"] = "A"
    errs = hz.validate_assessment(obj)
    assert any("leak" in e for e in errs)


def test_export_empty_when_no_log(tmp_path):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(hz, "OBSERVER_LOG_PATH", str(tmp_path / "missing.jsonl"))
        mp.setattr(hz, "OBSERVER_EXPORT_PATH", str(tmp_path / "obs.json"))
        out = hz.write_observer_export()
        payload = json.load(open(out, encoding="utf-8"))
    assert payload["observer"] == "AI-OBS-v1"
    assert payload["prompt_version"] == "v1"
    assert payload["assessment_count"] == 0
    assert payload["assessments"] == []
    assert payload["prompt_sha256_12"]  # prompt file exists


def test_export_roundtrip_and_idempotent_skip(tmp_path):
    logp = tmp_path / "ai_observer.jsonl"
    expp = tmp_path / "obs.json"
    line = json.dumps(_good_assessment())
    logp.write_text(line + "\n", encoding="utf-8")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(hz, "OBSERVER_LOG_PATH", str(logp))
        mp.setattr(hz, "OBSERVER_EXPORT_PATH", str(expp))
        assert hz.observer_already_assessed(
            "v54:TEST:4h:2026-09-15T10:30:00-04:00:2026-09-15-v54") is True
        assert hz.observer_already_assessed("v54:OTHER") is False
        out = hz.write_observer_export()
        payload = json.load(open(out, encoding="utf-8"))
    assert payload["assessment_count"] == 1
    assert payload["assessments"][0]["classification"] == "NEUTRAL"


def test_prompt_file_frozen():
    assert os.path.exists(hz.AI_OBS_PROMPT_PATH)
    text = open(hz.AI_OBS_PROMPT_PATH, encoding="utf-8").read()
    assert "FROZEN" in text
    assert "AI-OBS-v1" in text
    assert "V5.4 grade" in text  # documents the withholding


def _assess_now(sid="v54:NEW:4h:2026-09-15T14:30:00-04:00:2026-09-15-v54"):
    from datetime import datetime, timezone
    a = _good_assessment(sid)
    a["assessed_at"] = datetime.now(timezone.utc).isoformat()
    return a


def test_append_assessment_happy_path(tmp_path):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(hz, "OBSERVER_LOG_PATH", str(tmp_path / "obs.jsonl"))
        r = hz.observer_append_assessment(_assess_now())
        assert r["ok"] is True
        assert hz.observer_already_assessed(r["signal_id"]) is True


def test_append_refuses_duplicate_and_bad_schema(tmp_path):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(hz, "OBSERVER_LOG_PATH", str(tmp_path / "obs.jsonl"))
        assert hz.observer_append_assessment(_assess_now())["ok"] is True
        dup = hz.observer_append_assessment(_assess_now())
        assert dup["ok"] is False
        assert any("already assessed" in e for e in dup["errors"])
        bad = _assess_now("v54:OTHER")
        bad["classification"] = "MOON"
        r = hz.observer_append_assessment(bad)
        assert r["ok"] is False


def test_append_refuses_stale_backfill(tmp_path):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(hz, "OBSERVER_LOG_PATH", str(tmp_path / "obs.jsonl"))
        a = _assess_now()
        a["assessed_at"] = "2020-01-01T00:00:00+00:00"
        r = hz.observer_append_assessment(a)
        assert r["ok"] is False
        assert any("backfill" in e for e in r["errors"])
