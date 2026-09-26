"""Pre-performance linter for as-seen fundamental vendor sample rows.

This deliberately does NOT score factors, choose a decision clock, validate
dual anchors, or certify a vendor as point-in-time. It catches data-shape
failures before the frozen availability framework is applied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


FIELDS = (
    "security_id", "fiscal_period", "metric", "value", "available_at",
    "availability_provenance", "vendor_record_id", "source_version",
)
ACCEPTED_PROVENANCE = {"vendor_recorded", "feed_log"}
PRECISE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def parse_delivery_timestamp(value: object) -> datetime | None:
    """Reject dates, coarse/naive clocks, and invented publication times."""
    if not isinstance(value, str) or PRECISE_ISO.fullmatch(value) is None:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None or result.utcoffset() is None:
        return None
    return result.astimezone(timezone.utc)


def audit_rows(rows: list[dict]) -> dict:
    counts: Counter[str] = Counter()
    issues: list[dict] = []
    versions: dict[tuple[str, str, str, str], list[tuple[int, object]]] = defaultdict(list)
    seen_ids: dict[str, tuple[str, str, str]] = {}

    for index, row in enumerate(rows, start=1):
        errors: list[str] = []
        if not isinstance(row, dict):
            issues.append({"row": index, "errors": ["not_an_object"]})
            counts["malformed_rows"] += 1
            continue
        for field in FIELDS:
            if field not in row or row[field] is None or row[field] == "":
                errors.append(f"missing:{field}")
        for field in ("security_id", "fiscal_period", "metric", "vendor_record_id", "source_version"):
            if field in row and row[field] is not None and not isinstance(row[field], str):
                errors.append(f"not_string:{field}")
        timestamp = parse_delivery_timestamp(row.get("available_at"))
        if timestamp is None:
            errors.append("invalid_delivery_timestamp")
        if row.get("availability_provenance") not in ACCEPTED_PROVENANCE:
            errors.append("not_vendor_delivery_evidence")
        value = row.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            errors.append("invalid_numeric_value")

        # A repeated vendor record ID attached to different facts is unsafe.
        rid = row.get("vendor_record_id")
        identity = tuple(str(row.get(key)) for key in ("security_id", "fiscal_period", "metric"))
        if isinstance(rid, str) and rid:
            if rid in seen_ids and seen_ids[rid] != identity:
                errors.append("record_id_reused_across_facts")
            else:
                seen_ids[rid] = identity

        if not errors and timestamp is not None:
            key = (*identity, timestamp.isoformat())
            versions[key].append((index, value))
            counts["structurally_eligible_rows"] += 1
        else:
            issues.append({"row": index, "errors": sorted(set(errors))})
            counts["rejected_rows"] += 1

    for key, entries in versions.items():
        if len({value for _, value in entries}) > 1:
            issues.append({"rows": [i for i, _ in entries], "errors": ["same_time_conflicting_values"],
                           "fact_key": list(key)})
            counts["ambiguous_conflict_groups"] += 1
        elif len(entries) > 1:
            counts["identical_duplicate_groups"] += 1

    return {
        "status": "STRUCTURAL_ISSUES" if issues else "SHAPE_ONLY_OK",
        "note": "SHAPE_ONLY_OK is not availability, provenance, vendor-coverage, or trading approval",
        "rows": len(rows), "counts": dict(sorted(counts.items())), "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path, help="Vendor sample as JSON Lines; no P&L fields needed")
    args = parser.parse_args()
    raw = args.sample.read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    result = audit_rows(rows)
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["status"] == "STRUCTURAL_ISSUES" else 0


if __name__ == "__main__":
    raise SystemExit(main())
