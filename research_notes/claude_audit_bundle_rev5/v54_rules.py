"""V5.4 rule primitives: frozen hard gates + A/B/C grading.

Frozen 2026-09-15 (see chatgpt_handoff_brief.md — the frozen source of truth).
Research phase is closed: no backtest-driven tuning from here.

This module contains ONLY:
  - the frozen hard-gate check for BUY NOW eligibility, and
  - the frozen A/B/C grading logic.

Exit logic (Mode B) lives in v54_exit_tracker.py — built as a separate step.
The scan pipeline lives in v54_engine.py — built as a separate step.

Nothing in this file modifies V5.3. It imports ONLY pure helpers from
scanner_rules (indicator math, level math, MTF/premarket/15m readers).
It never imports the V5.3 veto logic (validation_reasons /
annotate_validation / is_buy_now_result / filter_buy_now).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

import pandas as pd

import scanner_rules as sr

V54_SCANNER_VERSION = "5.4"
V54_RULE_VERSION = "2026-09-15-v54"

# Frozen grade labels (handoff section 2).
GRADE_A = "A"  # EARLY — hard gates pass + early/partial confirmation
GRADE_B = "B"  # CONFIRMED — hard gates pass + fully confirmed/mature
GRADE_C = "C"  # OBSERVATION — hard gates pass, weaker/uncertain context

MIN_ADX = 20.0  # frozen hard filter (handoff section 3: -0.019R cost, big DD cut)

KNOWN_GATES = frozenset({"BLOCK", "CAUTION", "CONFIRM"})
TREND_STATES = frozenset({"confirmed", "not_confirmed", "unknown"})


def v54_hard_gates_pass(row: Mapping[str, Any]) -> tuple[bool, list[str]]:
    """Frozen hard gates (handoff section 2).

    sr.is_structural_candidate already encodes the V5.3 structural contract:
    entry == "YES", protection == "SAFE", state in {"BUY", "PULLBACK BUY"},
    above_vwap is True, price inside the buy zone. V5.4 adds ADX >= 20.
    Completed-bar handling is owned by the engine (it must only score
    closed 4H bars); see signal_bar_is_closed for the testable predicate.
    """
    reasons: list[str] = []
    if not sr.is_structural_candidate(row):
        reasons.append("not a structural candidate "
                       "(entry/protection/state/vwap/buy-zone contract failed)")
    try:
        adx = float(row.get("adx", 0) or 0)
    except (TypeError, ValueError):
        adx = 0.0
    if adx < MIN_ADX:
        reasons.append(f"ADX {adx:.1f} below {MIN_ADX:g}")
    return (not reasons), reasons


def signal_bar_is_closed(
    bar_start: pd.Timestamp,
    symbol: str,
    now: Optional[pd.Timestamp] = None,
) -> bool:
    """Testable predicate for the completed-bar rule.

    The engine must only score closed 4H bars (handoff: 'signals scored on
    completed 4H bars only'). bar_start is the bar's open timestamp.
    """
    current = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    close_at = sr.bar_close_at(pd.Timestamp(bar_start), symbol)
    if close_at.tzinfo is None and current.tzinfo is not None:
        close_at = close_at.tz_localize("UTC")
    return current >= close_at


def _trend_state(value: Any) -> str:
    """Normalise a daily/weekly trend field to confirmed|not_confirmed|unknown."""
    if value == "confirmed":
        return "confirmed"
    if value == "not_confirmed":
        return "not_confirmed"
    return "unknown"


def v54_grade(row: Mapping[str, Any]) -> dict[str, Any]:
    """Frozen A/B/C grading (handoff section 2).

    Consumes explicit context fields produced by the engine — never raw
    dataframes, so this function stays pure and deterministic:
      - daily_trend / weekly_trend: "confirmed" | "not_confirmed" | "unknown"
      - market_gate: "BLOCK" | "CAUTION" | "CONFIRM" | "UNKNOWN"

    15m confirmation and premarket are observational only per the frozen
    spec: they are recorded on the signal record by the logger but are NOT
    grading inputs.

    Mapping (each line traces to the handoff):
      - hard gates fail            -> not eligible (grade None)
      - fully confirmed/mature     -> B. "fully confirmed" is the handoff's
        literal "Daily+Weekly both aligned and/or market CONFIRM".
      - context unknown/indeterminate -> C ("uncertain" half of the frozen
        "weaker/uncertain" wording)
      - otherwise                  -> A (assessable context, not fully
        confirmed: the pullback arrival)

    FLAGGED (not invented): the handoff's "weaker" (as distinct from
    "unknown") has no deterministic definition yet, so weak-but-known
    context currently grades A. If Mike defines specific weak-context
    combinations for C, they slot in here — nothing else changes.

    Do NOT "clean up" this function by demoting signals to C on the basis
    of accumulated soft negatives (e.g. BLOCK + low RVOL + mediocre R:R).
    No known soft-context combination is currently authorized to demote an
    otherwise qualified signal to C: the research did not establish that
    those combinations are actually bad (BLOCK and low RVOL were
    historically positive buckets). C represents grading uncertainty until
    forward-test evidence defines a deterministic weak-context rule.
    """
    eligible, gate_reasons = v54_hard_gates_pass(row)
    result: dict[str, Any] = {
        "eligible": eligible,
        "grade": None,
        "grade_label": None,
        "grade_reasons": [],
        "fully_confirmed": False,
        "context_known": False,
    }
    if not eligible:
        result["grade_reasons"] = [f"ineligible: {r}" for r in gate_reasons]
        return result

    daily = _trend_state(row.get("daily_trend"))
    weekly = _trend_state(row.get("weekly_trend"))
    gate = str(row.get("market_gate", "UNKNOWN")).upper()
    if gate not in KNOWN_GATES:
        gate = "UNKNOWN"

    fully_confirmed = (daily == "confirmed" and weekly == "confirmed") or gate == "CONFIRM"
    context_known = daily != "unknown" and weekly != "unknown" and gate != "UNKNOWN"

    result["fully_confirmed"] = fully_confirmed
    result["context_known"] = context_known

    if fully_confirmed:
        result["grade"] = GRADE_B
        result["grade_label"] = "CONFIRMED"
        result["grade_reasons"] = [
            "fully confirmed/mature profile: "
            + ("daily+weekly both aligned" if daily == "confirmed" and weekly == "confirmed" else "")
            + (" + " if (daily == "confirmed" and weekly == "confirmed") and gate == "CONFIRM" else "")
            + ("market CONFIRM" if gate == "CONFIRM" else ""),
            "treated as potential lateness, not extra quality (frozen thesis)",
        ]
    elif not context_known:
        result["grade"] = GRADE_C
        result["grade_label"] = "OBSERVATION"
        missing = [
            name for name, val in
            (("daily_trend", daily), ("weekly_trend", weekly), ("market_gate", gate))
            if val in ("unknown", "UNKNOWN")
        ]
        result["grade_reasons"] = [
            f"confirmation context indeterminate ({', '.join(missing)}): "
            "graded OBSERVATION, not assumed bad (frozen rule)",
        ]
    else:
        result["grade"] = GRADE_A
        result["grade_label"] = "EARLY"
        result["grade_reasons"] = [
            f"early/partial confirmation profile (daily={daily}, weekly={weekly}, gate={gate})",
            "highest forward-test priority (frozen thesis: confirmation is lateness)",
        ]
    return result


def v54_annotate(row: Mapping[str, Any]) -> dict[str, Any]:
    """Attach V5.4 eligibility + grade to a candidate row (dict copy).

    Rows that fail the hard gates are still returned (eligible=False) so the
    engine/logger can record what was filtered and why. Grade is None for
    ineligible rows.
    """
    enriched = dict(row)
    graded = v54_grade(row)
    enriched["v54_eligible"] = graded["eligible"]
    enriched["v54_grade"] = graded["grade"]
    enriched["v54_grade_label"] = graded["grade_label"]
    enriched["v54_grade_reasons"] = graded["grade_reasons"]
    enriched["v54_rule_version"] = V54_RULE_VERSION
    enriched["v54_scanner_version"] = V54_SCANNER_VERSION
    return enriched
