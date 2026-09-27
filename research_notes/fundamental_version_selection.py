"""Decision-clock version selection for as-seen fundamental facts (lab only).

Feasibility-only helper. Pure function: given candidate fact versions for one
(security_id, fiscal_period, metric) fact and a decision time, select the
latest as-seen version that was deliverable before the decision.

This deliberately does NOT score factors, open returns, or certify anything.
It implements the frozen decision-clock rule from the F7 proposal:

- A fact version is eligible only if available_at + frozen_latency_buffer
  < decision_at, with STRICT inequality (an eligible 16:01 release cannot be
  scored for a 16:00 decision; equality fails).
- Among eligible versions, select the latest by available_at instant.
- Same-instant conflicting values fail closed (no selection).
- Selection is keyed on permanent security_id, never on ticker alone.
- decision_at must come from the frozen manifest; this function performs no
  decision-time override and accepts no caller-supplied "as of" substitution.

Statuses: SELECTED, NO_ELIGIBLE_VERSION, SAME_TIME_CONFLICT, NO_USABLE_VERSION.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


PRECISE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def parse_instant(value: object) -> datetime | None:
    """Strict ISO-8601 with timezone; anything else is unusable (None)."""
    if not isinstance(value, str) or PRECISE_ISO.fullmatch(value) is None:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None or result.utcoffset() is None:
        return None
    return result.astimezone(timezone.utc)


def select_version(versions: list[dict], decision_at: datetime,
                   latency_buffer: timedelta) -> dict:
    """Select the latest eligible as-seen version for one fact.

    versions: dicts with at least "available_at" (ISO str) and "value".
    decision_at: timezone-aware decision instant from the frozen manifest.
    latency_buffer: frozen non-negative latency buffer.

    Returns {"status": ..., "version": <dict|None>, "available_at": <iso|None>}.
    """
    if decision_at.tzinfo is None or latency_buffer < timedelta(0):
        return {"status": "NO_USABLE_VERSION", "version": None, "available_at": None}

    eligible: list[tuple[datetime, dict]] = []
    for v in versions:
        instant = parse_instant(v.get("available_at") if isinstance(v, dict) else None)
        if instant is None:
            continue
        # STRICT inequality: available_at + buffer < decision_at. Equality fails.
        if instant + latency_buffer < decision_at:
            eligible.append((instant, v))

    if not eligible:
        return {"status": "NO_ELIGIBLE_VERSION", "version": None, "available_at": None}

    latest_instant = max(i for i, _ in eligible)
    tied = [v for i, v in eligible if i == latest_instant]
    if len({repr(v.get("value")) for v in tied}) > 1:
        # Same-instant disagreeing values: fail closed, never guess.
        return {"status": "SAME_TIME_CONFLICT", "version": None,
                "available_at": latest_instant.isoformat()}
    chosen = tied[0]
    return {"status": "SELECTED", "version": chosen,
            "available_at": latest_instant.isoformat()}


def group_by_fact(versions: list[dict]) -> dict[tuple[str, str, str], list[dict]]:
    """Group raw intake rows by (security_id, fiscal_period, metric).

    Selection is keyed on permanent security_id, never on ticker alone: two
    securities that reused the same ticker at different times land in
    different groups. Raises on rows missing a grouping key (fail closed).
    """
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for v in versions:
        if not isinstance(v, dict):
            raise ValueError("non-object version row")
        key = (v.get("security_id"), v.get("fiscal_period"), v.get("metric"))
        if not all(isinstance(k, str) and k for k in key):
            raise ValueError("missing fact grouping key")
        groups.setdefault(key, []).append(v)
    return groups


def completeness(components: dict[str, object]) -> str:
    """Frozen completeness rule: no weight renormalization, ever.

    components: mapping component_name -> value or None/NaN/"UNKNOWN".
    Returns "COMPUTABLE" only if every required component has a real value;
    a stored 0.0 is a real value (not missing). Anything else -> "UNKNOWN".
    """
    import math
    if not components:
        return "UNKNOWN"  # zero components supplied: nothing computable
    for value in components.values():
        if value is None:
            return "UNKNOWN"
        if isinstance(value, str):
            return "UNKNOWN"
        if isinstance(value, float) and not math.isfinite(value):
            return "UNKNOWN"
    return "COMPUTABLE"


def split_adjust(versions: list[dict], effective_at: str, factor: float) -> list[dict]:
    """Apply a corporate-action split factor to as-seen versions (lab only).

    Invariance rule: only versions with available_at STRICTLY AFTER the
    action's effective instant are adjusted. Versions with
    available_at <= effective_at are returned unchanged — a corporate action
    can never rewrite history. Raises on unparseable inputs (fail closed).
    """
    eff = parse_instant(effective_at)
    if eff is None:
        raise ValueError("unparseable corporate-action effective_at")
    out = []
    for v in versions:
        instant = parse_instant(v.get("available_at") if isinstance(v, dict) else None)
        if instant is None:
            raise ValueError("unparseable version available_at")
        nv = dict(v)
        if instant > eff:
            nv["value"] = v["value"] * factor
            nv["corporate_action_applied"] = effective_at
        out.append(nv)
    return out
