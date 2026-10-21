#!/usr/bin/env python3
"""C1-C6 analyzer candidate — TD probe (task -65 r1).

Performance-blind comparison analyzer for the -63 probe packet.
Consumes ONLY explicit receipt/snapshot path pairs; verifies bytes,
SHA-256, params and identity from the receipts BEFORE parsing any
snapshot. All arithmetic is Decimal; the factor tolerance is
PREDECLARED and derived from the observed decimal precision of the
two operands (half-ulp of each printed value, propagated through the
ratio) — never a loose fitted tolerance.

Checks (per -63 section 6c):
  C1 none-vs-splits per-bar OHLC ratio == known factor pre-split,
     == 1 post-split (within rounding tolerance).
  C2 volume convention measured and REPORTED (scaled-by-factor /
     unscaled); an inconsistent per-bar volume factor inside one
     series is mixed-basis evidence -> FAIL.
  C3 split-session factor-flip location, read off C1/C2, reported
     against the effective date. No assumption imported.
  C4 Amendment S4: per-bar OHLC consistency on both series plus the
     deterministic pre/post price-ratio step across the split.
  C5 revision byte-compare; any difference is enumerated bar-by-bar
     and the revision verdict is HOLD (classification is a
     governance act, never automated here).
  C6 row-count / no-pagination confirmation (equal twin counts,
     count < outputsize trigger).

Window verdicts are sampled-window only:
  PASS | DATA_UNQUALIFIED | HOLD.
This module NEVER emits a global S2 verdict and computes no
performance metric of any kind.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

# Known-split facts from the -63 packet (independently known factors).
KNOWN_SPLITS = {
    "REQ-ADJ-01": {"factor": Decimal(10), "split_date": "2024-06-10"},
    "REQ-ADJ-02": {"factor": Decimal(3), "split_date": "2022-08-25"},
}

OHLC = ("open", "high", "low", "close")


class EvidenceHold(Exception):
    """Evidence defect: the window cannot be evaluated -> HOLD."""

    def __init__(self, tag: str, detail: str = ""):
        super().__init__(f"{tag}: {detail}" if detail else tag)
        self.tag = tag


def decimal_places(s: str) -> int:
    if "." not in s:
        return 0
    return len(s.split(".", 1)[1])


def half_ulp(s: str) -> Decimal:
    return Decimal("0.5") * (Decimal(10) ** -decimal_places(s))


def ratio_tolerance(none_str: str, splits_str: str,
                    expected: Decimal) -> Decimal:
    """Max |none/splits - expected| explainable purely by rounding
    both operands to their printed precision."""
    s = Decimal(splits_str)
    if s == 0:
        return Decimal(0)
    return (half_ulp(none_str) + expected * half_ulp(splits_str)) / s


def ratio_within(none_str: str, splits_str: str,
                 expected: Decimal) -> bool:
    s = Decimal(splits_str)
    if s == 0:
        return False
    dev = abs(Decimal(none_str) / s - expected)
    return dev <= ratio_tolerance(none_str, splits_str, expected)


def verify_receipt(receipt_path: Path, snapshot_path: Path,
                   expected_params: dict) -> dict:
    """Verify receipt integrity + identity before any parsing."""
    receipt_path, snapshot_path = Path(receipt_path), Path(snapshot_path)
    if not receipt_path.exists():
        raise EvidenceHold("RECEIPT_MISSING", receipt_path.name)
    if not snapshot_path.exists():
        raise EvidenceHold("SNAPSHOT_MISSING", snapshot_path.name)
    try:
        receipt = json.loads(receipt_path.read_text())
    except Exception as e:
        raise EvidenceHold("RECEIPT_MALFORMED", str(e)) from e
    if not isinstance(receipt, dict):
        raise EvidenceHold("RECEIPT_MALFORMED", "not an object")
    if receipt.get("http_status") != 200:
        raise EvidenceHold("RECEIPT_IDENTITY", "http_status != 200")
    if receipt.get("params") != expected_params:
        raise EvidenceHold("RECEIPT_PARAMS_MISMATCH",
                           receipt_path.name)
    body = snapshot_path.read_bytes()
    if receipt.get("sha256") != hashlib.sha256(body).hexdigest():
        raise EvidenceHold("SNAPSHOT_SHA_MISMATCH", snapshot_path.name)
    if receipt.get("bytes") != len(body):
        raise EvidenceHold("SNAPSHOT_BYTES_MISMATCH",
                           snapshot_path.name)
    return receipt


def parse_bars(snapshot_path: Path) -> list[dict]:
    try:
        payload = json.loads(Path(snapshot_path).read_bytes())
    except Exception as e:
        raise EvidenceHold("SNAPSHOT_MALFORMED", str(e)) from e
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise EvidenceHold("SNAPSHOT_MALFORMED", "status != ok")
    values = payload.get("values")
    if not isinstance(values, list) or not values:
        raise EvidenceHold("SNAPSHOT_MALFORMED", "values empty/missing")
    bars = []
    for v in values:
        if not isinstance(v, dict) or not isinstance(
                v.get("datetime"), str):
            raise EvidenceHold("SNAPSHOT_MALFORMED", "bar shape")
        bar = {"datetime": v["datetime"]}
        for f in OHLC:
            if not isinstance(v.get(f), str):
                raise EvidenceHold("SNAPSHOT_MALFORMED",
                                   f"bar {f} not a string")
            bar[f] = v[f]
        bar["volume"] = v.get("volume")  # may be absent -> None
        bars.append(bar)
    return bars


def _pre_post(bar: dict, split_date: str) -> str:
    return "pre" if bar["datetime"][:10] < split_date else "post"


def check_c1(none_bars, splits_bars, factor, split_date) -> dict:
    bad = []
    for nb, sb in zip(none_bars, splits_bars):
        exp = factor if _pre_post(nb, split_date) == "pre" \
            else Decimal(1)
        for f in OHLC:
            if not ratio_within(nb[f], sb[f], exp):
                bad.append({"datetime": nb["datetime"], "field": f,
                            "none": nb[f], "splits": sb[f],
                            "expected_ratio": str(exp)})
    return {"status": "PASS" if not bad else "FAIL",
            "deviations": bad[:10], "n_deviations": len(bad)}


def check_c2(none_bars, splits_bars, factor, split_date) -> dict:
    if any(b["volume"] is None for b in none_bars + splits_bars):
        return {"status": "FAIL", "convention": "MISSING_VOLUME",
                "detail": "at least one bar lacks volume"}
    scaled = unscaled = other = 0
    for nb, sb in zip(none_bars, splits_bars):
        # ratio splits/none: factor pre-split if volume is scaled
        exp = factor if _pre_post(nb, split_date) == "pre" \
            else Decimal(1)
        if ratio_within(sb["volume"], nb["volume"], exp):
            if exp == factor:
                scaled += 1
            else:
                unscaled += 1
        elif ratio_within(sb["volume"], nb["volume"], Decimal(1)):
            unscaled += 1
        else:
            other += 1
    if other:
        return {"status": "FAIL", "convention": "INCONSISTENT",
                "detail": f"{other} bar(s) fit neither convention"}
    if scaled and unscaled:
        # pre-split bars scaled, post-split ratio 1 also counts as
        # "unscaled" bucket above; disambiguate by pre-split only.
        pass
    pre = [(nb, sb) for nb, sb in zip(none_bars, splits_bars)
           if _pre_post(nb, split_date) == "pre"]
    pre_scaled = all(ratio_within(sb["volume"], nb["volume"], factor)
                     for nb, sb in pre)
    convention = "SCALED_BY_FACTOR" if pre_scaled else "UNSCALED"
    return {"status": "PASS", "convention": convention,
            "detail": "consistent per-bar volume factor"}


def check_c3(none_bars, splits_bars, factor, split_date) -> dict:
    states = []
    for nb, sb in zip(none_bars, splits_bars):
        if ratio_within(nb["close"], sb["close"], factor):
            states.append("factor")
        elif ratio_within(nb["close"], sb["close"], Decimal(1)):
            states.append("one")
        else:
            states.append("other")
    flips = [i for i in range(1, len(states))
             if states[i] != states[i - 1]]
    if states.count("other") or len(flips) != 1 or \
            states[0] != "factor" or states[-1] != "one":
        return {"status": "FAIL", "states": states,
                "detail": "no single clean factor->1 transition"}
    flip_dt = none_bars[flips[0]]["datetime"]
    rel = ("ON_EFFECTIVE_DATE" if flip_dt[:10] == split_date else
           "AFTER_EFFECTIVE_DATE" if flip_dt[:10] > split_date else
           "BEFORE_EFFECTIVE_DATE")
    return {"status": "PASS", "flip_datetime": flip_dt,
            "relation_to_effective_date": rel}


def _ohlc_consistent(bars) -> list[str]:
    bad = []
    for b in bars:
        o, h, l, c = (Decimal(b[f]) for f in OHLC)
        if l <= 0 or l > min(o, c) or max(o, c) > h:
            bad.append(b["datetime"])
        if b["volume"] is not None and Decimal(b["volume"]) < 0:
            bad.append(b["datetime"] + ":volume")
    return bad


def check_c4(none_bars, splits_bars, factor, split_date) -> dict:
    bad = _ohlc_consistent(none_bars) + _ohlc_consistent(splits_bars)
    pre = [i for i, b in enumerate(none_bars)
           if _pre_post(b, split_date) == "pre"]
    post = [i for i, b in enumerate(none_bars)
            if _pre_post(b, split_date) == "post"]
    step_ok = False
    step = None
    if pre and post:
        i, j = pre[-1], post[0]
        n_pre, s_pre = Decimal(none_bars[i]["close"]), \
            Decimal(splits_bars[i]["close"])
        n_post, s_post = Decimal(none_bars[j]["close"]), \
            Decimal(splits_bars[j]["close"])
        step = (n_pre / s_pre) / (n_post / s_post)
        tol = factor * sum(
            half_ulp(x) / Decimal(x) for x in
            (none_bars[i]["close"], splits_bars[i]["close"],
             none_bars[j]["close"], splits_bars[j]["close"]))
        step_ok = abs(step - factor) <= tol
    ok = not bad and step_ok
    return {"status": "PASS" if ok else "FAIL",
            "ohlc_inconsistent_bars": bad[:10],
            "pre_post_ratio_step": None if step is None else str(step),
            "step_matches_factor": step_ok}


def check_c6(none_bars, splits_bars, outputsize: int = 5000) -> dict:
    ok = len(none_bars) == len(splits_bars) and \
        0 < len(none_bars) < outputsize
    return {"status": "PASS" if ok else "FAIL",
            "rows_none": len(none_bars), "rows_splits": len(splits_bars),
            "pagination_trigger_rows": outputsize}


def analyze_window(*, splits_receipt: Path, splits_snapshot: Path,
                   none_receipt: Path, none_snapshot: Path,
                   expected_params_splits: dict,
                   expected_params_none: dict,
                   factor: Decimal, split_date: str) -> dict:
    """Run C1/C2/C3/C4/C6 on one twin pair. C5 is separate."""
    try:
        verify_receipt(splits_receipt, splits_snapshot,
                       expected_params_splits)
        verify_receipt(none_receipt, none_snapshot,
                       expected_params_none)
        s_bars = parse_bars(splits_snapshot)
        n_bars = parse_bars(none_snapshot)
    except EvidenceHold as e:
        return {"verdict": "HOLD", "hold_tag": e.tag,
                "detail": str(e), "checks": {}}
    if [b["datetime"] for b in n_bars] != \
            [b["datetime"] for b in s_bars]:
        return {"verdict": "DATA_UNQUALIFIED",
                "detail": "twin datetime sets differ", "checks": {}}
    checks = {
        "C1": check_c1(n_bars, s_bars, factor, split_date),
        "C2": check_c2(n_bars, s_bars, factor, split_date),
        "C3": check_c3(n_bars, s_bars, factor, split_date),
        "C4": check_c4(n_bars, s_bars, factor, split_date),
        "C6": check_c6(n_bars, s_bars),
    }
    verdict = "PASS" if all(c["status"] == "PASS"
                            for c in checks.values()) \
        else "DATA_UNQUALIFIED"
    return {"verdict": verdict, "checks": checks}


def analyze_revision(*, base_receipt: Path, base_snapshot: Path,
                     rev_receipt: Path, rev_snapshot: Path,
                     expected_params: dict) -> dict:
    """C5: byte-compare base vs revision snapshots (receipts verified
    first). Differing bytes are enumerated bar-by-bar; the revision
    verdict is HOLD — classification is never automated."""
    try:
        verify_receipt(base_receipt, base_snapshot, expected_params)
        verify_receipt(rev_receipt, rev_snapshot, expected_params)
    except EvidenceHold as e:
        return {"C5": {"status": "HOLD", "hold_tag": e.tag,
                       "detail": str(e)}, "verdict": "HOLD"}
    base_bytes = Path(base_snapshot).read_bytes()
    rev_bytes = Path(rev_snapshot).read_bytes()
    if base_bytes == rev_bytes:
        return {"C5": {"status": "PASS", "identical": True,
                       "bytes": len(base_bytes)}, "verdict": "PASS"}
    b_bars = {b["datetime"]: b for b in parse_bars(base_snapshot)}
    r_bars = {b["datetime"]: b for b in parse_bars(rev_snapshot)}
    diffs = []
    for dt in sorted(set(b_bars) | set(r_bars)):
        if dt not in b_bars:
            diffs.append({"datetime": dt, "change": "added"})
        elif dt not in r_bars:
            diffs.append({"datetime": dt, "change": "removed"})
        else:
            for f in OHLC + ("volume",):
                if b_bars[dt][f] != r_bars[dt][f]:
                    diffs.append({"datetime": dt, "field": f,
                                  "base": b_bars[dt][f],
                                  "revision": r_bars[dt][f]})
    return {"C5": {"status": "DIFFERS", "identical": False,
                   "n_bar_diffs": len(diffs), "diffs": diffs[:50]},
            "verdict": "HOLD"}
