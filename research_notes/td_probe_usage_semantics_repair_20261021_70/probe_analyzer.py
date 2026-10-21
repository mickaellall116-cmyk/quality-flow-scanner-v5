#!/usr/bin/env python3
"""C1-C6 analyzer candidate — TD probe (task -67 r1, successor of
-66/-65).

Performance-blind comparison analyzer for the -63 probe packet.
Consumes ONLY explicit receipt/snapshot path pairs. REPAIRS over -65
(independent adjudication, Issue #1 comment 6310607516):

  R-A (defect 2) Receipt identity is verified BEFORE any parsing:
     exact expected request_id, http status, params, SHA-256, byte
     count, and sane request/receipt timestamps. Base and revision
     request IDs must be distinct and exact — same-params receipts
     can no longer be cross-bound.
  R-B (defect 2, cont.) Snapshot structure is verified before C1-C6:
     meta symbol+interval must match expectation; bar datetimes must
     be unique and strictly ascending; every bar must lie inside the
     requested window.
  R-C (defect 1) C2 volume convention: pre-split volume must be
     UNIFORMLY factor-scaled or UNIFORMLY unscaled. A mixture of the
     two otherwise-valid conventions is INCONSISTENT (the -65 code
     returned a false PASS/UNSCALED for exactly that mixture).
     Nonempty pre-split AND post-split coverage is required.

CLOSURES over -66 (independent adjudication, Issue #1 comment
6311907793) — task -67:
  C-A Mandatory expectations: expected request IDs, symbol,
     interval, requested window, and now_ms are REQUIRED keyword
     arguments of analyze_window / analyze_revision — no None
     defaults anywhere on those paths. Missing/blank/ambiguous
     expectations raise EvidenceHold (EXPECTATION_*) before any
     C1-C6 work; omitting an argument is a TypeError at the call
     site (the legacy -66 call shape no longer runs at all).
  C-B C5 structure-first: analyze_revision parses and validates
     BOTH snapshots (status/meta, numeric bar shape, strictly
     ascending unique datetimes, window containment) BEFORE the
     byte-identical PASS branch — identical-but-invalid snapshots
     HOLD instead of passing.
  C-C Numeric shape: every OHLC/volume field must be a
     Decimal-parseable string, verified at parse time; malformed
     numerics HOLD (SNAPSHOT_MALFORMED) and never escape the
     analyzer as uncaught exceptions.

All arithmetic is Decimal; the factor tolerance is PREDECLARED and
derived from the observed decimal precision of the two operands
(half-ulp of each printed value, propagated through the ratio) —
never a loose fitted tolerance.

Checks (per -63 section 6c):
  C1 none-vs-splits per-bar OHLC ratio == known factor pre-split,
     == 1 post-split (within rounding tolerance).
  C2 volume convention measured and REPORTED (scaled-by-factor /
     unscaled); a mixed or otherwise inconsistent per-bar volume
     factor inside one series is mixed-basis evidence -> FAIL.
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
import re
from decimal import Decimal
from pathlib import Path

# Known-split facts from the -63 packet (independently known factors).
KNOWN_SPLITS = {
    "REQ-ADJ-01": {"factor": Decimal(10), "split_date": "2024-06-10"},
    "REQ-ADJ-02": {"factor": Decimal(3), "split_date": "2022-08-25"},
}

OHLC = ("open", "high", "low", "close")
FUTURE_SKEW_MS = 300_000


class EvidenceHold(Exception):
    """Evidence defect: the window cannot be evaluated -> HOLD."""

    def __init__(self, tag: str, detail: str = ""):
        super().__init__(f"{tag}: {detail}" if detail else tag)
        self.tag = tag


_WINDOW_END = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$"


def _validate_expectations(ids, symbol, interval, window, now_ms):
    """C-A: every expectation is mandatory and must be well-formed.
    Returns the normalized tuple (ids, symbol, interval, window,
    now_ms); raises EvidenceHold BEFORE any receipt is read or any
    C1-C6 check runs when anything is missing, blank, or ambiguous
    (including duplicate expected request IDs)."""
    out_ids = []
    for rid in ids:
        if not isinstance(rid, str) or not rid.strip():
            raise EvidenceHold(
                "EXPECTATION_INVALID",
                f"expected request_id missing/blank: {rid!r}")
        out_ids.append(rid)
    if len(set(out_ids)) != len(out_ids):
        raise EvidenceHold(
            "EXPECTATION_AMBIGUOUS",
            f"expected request IDs not distinct: {out_ids!r}")
    if not isinstance(symbol, str) or not symbol.strip():
        raise EvidenceHold("EXPECTATION_INVALID",
                           f"expected symbol missing/blank: "
                           f"{symbol!r}")
    if not isinstance(interval, str) or not interval.strip():
        raise EvidenceHold("EXPECTATION_INVALID",
                           f"expected interval missing/blank: "
                           f"{interval!r}")
    if not isinstance(window, (tuple, list)) or len(window) != 2 or \
            not all(isinstance(w, str) and re.match(_WINDOW_END, w)
                    for w in window) or not window[0] < window[1]:
        raise EvidenceHold("EXPECTATION_INVALID",
                           f"expected window malformed: {window!r}")
    if not _is_int_ts(now_ms) or now_ms <= 0:
        raise EvidenceHold("EXPECTATION_INVALID",
                           f"now_ms missing/insane: {now_ms!r}")
    return (tuple(out_ids), symbol, interval,
            (window[0], window[1]), now_ms)


def _decimal_field(raw, field: str, dt: str) -> str:
    """C-C: a bar field must be a Decimal-parseable string. Returns
    the string unchanged (printed precision is evidence); raises
    EvidenceHold on any malformed numeric."""
    try:
        Decimal(raw)
    except Exception as e:
        raise EvidenceHold(
            "SNAPSHOT_MALFORMED",
            f"bar {field} at {dt} not a decimal string: "
            f"{raw!r}") from e
    return raw


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


def _is_int_ts(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def verify_receipt(receipt_path: Path, snapshot_path: Path,
                   expected_params: dict, *,
                   expected_request_id: str,
                   now_ms: int) -> dict:
    """Verify receipt integrity + identity before any parsing.

    R-A + C-A: expected_request_id is MANDATORY and must match
    exactly; request/receipt timestamps must be present, integral,
    positive and ordered (request <= receipt), and the receipt must
    not be future-dated beyond FUTURE_SKEW_MS relative to the
    mandatory now_ms."""
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
    if receipt.get("request_id") != expected_request_id:
        raise EvidenceHold(
            "RECEIPT_ID_MISMATCH",
            f"{receipt_path.name}: {receipt.get('request_id')!r} "
            f"!= {expected_request_id!r}")
    if receipt.get("http_status") != 200:
        raise EvidenceHold("RECEIPT_IDENTITY", "http_status != 200")
    if receipt.get("params") != expected_params:
        raise EvidenceHold("RECEIPT_PARAMS_MISMATCH",
                           receipt_path.name)
    req_ts = receipt.get("request_ts_ms")
    rcpt_ts = receipt.get("receipt_ts_ms")
    if not _is_int_ts(req_ts) or not _is_int_ts(rcpt_ts) \
            or req_ts <= 0 or rcpt_ts < req_ts:
        raise EvidenceHold("RECEIPT_TS_INSANE",
                           f"request={req_ts!r} receipt={rcpt_ts!r}")
    if rcpt_ts > now_ms + FUTURE_SKEW_MS:
        raise EvidenceHold("RECEIPT_TS_FUTURE",
                           f"receipt {rcpt_ts} > now {now_ms}")
    body = snapshot_path.read_bytes()
    if receipt.get("sha256") != hashlib.sha256(body).hexdigest():
        raise EvidenceHold("SNAPSHOT_SHA_MISMATCH", snapshot_path.name)
    if receipt.get("bytes") != len(body):
        raise EvidenceHold("SNAPSHOT_BYTES_MISMATCH",
                           snapshot_path.name)
    return receipt


def parse_bars(snapshot_path: Path, *,
               expected_symbol: str,
               expected_interval: str,
               window: tuple[str, str]) -> list[dict]:
    """Parse a snapshot after structural verification (R-B + C-A):
    meta symbol/interval (mandatory expectations), unique strictly
    ascending datetimes, requested-window containment, and (C-C)
    Decimal-parseable numeric bar fields."""
    try:
        payload = json.loads(Path(snapshot_path).read_bytes())
    except Exception as e:
        raise EvidenceHold("SNAPSHOT_MALFORMED", str(e)) from e
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise EvidenceHold("SNAPSHOT_MALFORMED", "status != ok")
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        raise EvidenceHold("SNAPSHOT_META_MISMATCH", "meta missing")
    if meta.get("symbol") != expected_symbol:
        raise EvidenceHold(
            "SNAPSHOT_META_MISMATCH",
            f"symbol {meta.get('symbol')!r} != {expected_symbol!r}")
    if meta.get("interval") != expected_interval:
        raise EvidenceHold(
            "SNAPSHOT_META_MISMATCH",
            f"interval {meta.get('interval')!r} "
            f"!= {expected_interval!r}")
    values = payload.get("values")
    if not isinstance(values, list) or not values:
        raise EvidenceHold("SNAPSHOT_MALFORMED", "values empty/missing")
    bars = []
    prev_dt = None
    for v in values:
        if not isinstance(v, dict) or not isinstance(
                v.get("datetime"), str):
            raise EvidenceHold("SNAPSHOT_MALFORMED", "bar shape")
        dt = v["datetime"]
        if prev_dt is not None and dt <= prev_dt:
            raise EvidenceHold(
                "BARS_NOT_STRICTLY_ASCENDING",
                f"{dt!r} after {prev_dt!r} (duplicate or out of order)")
        prev_dt = dt
        norm = dt.replace(" ", "T")
        if norm < window[0] or norm > window[1]:
            raise EvidenceHold(
                "BAR_OUT_OF_WINDOW",
                f"{dt!r} outside {window[0]}..{window[1]}")
        bar = {"datetime": dt}
        for f in OHLC:
            if not isinstance(v.get(f), str):
                raise EvidenceHold("SNAPSHOT_MALFORMED",
                                   f"bar {f} not a string")
            bar[f] = _decimal_field(v[f], f, dt)
        vol = v.get("volume")
        if vol is not None:
            if not isinstance(vol, str):
                raise EvidenceHold("SNAPSHOT_MALFORMED",
                                   f"bar volume not a string at {dt}")
            _decimal_field(vol, "volume", dt)
        bar["volume"] = vol  # may be absent -> None
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
    """R-C: pre-split volume must be UNIFORMLY factor-scaled or
    UNIFORMLY unscaled; any mixture of the two valid conventions —
    or any bar fitting neither — is INCONSISTENT. Nonempty pre and
    post coverage is required (else EvidenceHold -> HOLD)."""
    if any(b["volume"] is None for b in none_bars + splits_bars):
        return {"status": "FAIL", "convention": "MISSING_VOLUME",
                "detail": "at least one bar lacks volume"}
    pairs = list(zip(none_bars, splits_bars))
    pre = [(nb, sb) for nb, sb in pairs
           if _pre_post(nb, split_date) == "pre"]
    post = [(nb, sb) for nb, sb in pairs
            if _pre_post(nb, split_date) == "post"]
    if not pre:
        raise EvidenceHold("C2_PRE_COVERAGE_EMPTY",
                           "no pre-split bars in window")
    if not post:
        raise EvidenceHold("C2_POST_COVERAGE_EMPTY",
                           "no post-split bars in window")
    classes = set()
    n_other = 0
    for nb, sb in pre:
        if ratio_within(sb["volume"], nb["volume"], factor):
            classes.add("scaled")
        elif ratio_within(sb["volume"], nb["volume"], Decimal(1)):
            classes.add("unscaled")
        else:
            classes.add("other")
            n_other += 1
    post_bad = sum(
        1 for nb, sb in post
        if not ratio_within(sb["volume"], nb["volume"], Decimal(1)))
    if "other" in classes or post_bad:
        return {"status": "FAIL", "convention": "INCONSISTENT",
                "detail": f"{n_other} pre-split bar(s) fit neither "
                          f"convention; {post_bad} post-split bar(s) "
                          f"off ratio 1"}
    if classes == {"scaled", "unscaled"}:
        return {"status": "FAIL", "convention": "INCONSISTENT",
                "detail": "mixed pre-split volume conventions: "
                          "factor-scaled and unscaled bars in one "
                          "series"}
    convention = "SCALED_BY_FACTOR" if classes == {"scaled"} \
        else "UNSCALED"
    return {"status": "PASS", "convention": convention,
            "detail": "uniform per-bar volume convention"}


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
                   factor: Decimal, split_date: str,
                   expected_request_id_splits: str,
                   expected_request_id_none: str,
                   expected_symbol: str,
                   expected_interval: str,
                   expected_window: tuple[str, str],
                   now_ms: int) -> dict:
    """Run C1/C2/C3/C4/C6 on one twin pair. C5 is separate.

    C-A: ALL expectations (request IDs, symbol, interval, window,
    now_ms) are mandatory keyword arguments — there are no defaults
    to omit. They are validated (_validate_expectations) before any
    receipt is read; receipt identity + snapshot structure
    verification (R-A/R-B) then completes before any check runs."""
    try:
        (er_s, er_n), sym, ivl, win, now = _validate_expectations(
            (expected_request_id_splits, expected_request_id_none),
            expected_symbol, expected_interval, expected_window,
            now_ms)
        verify_receipt(splits_receipt, splits_snapshot,
                       expected_params_splits,
                       expected_request_id=er_s, now_ms=now)
        verify_receipt(none_receipt, none_snapshot,
                       expected_params_none,
                       expected_request_id=er_n, now_ms=now)
        s_bars = parse_bars(splits_snapshot, expected_symbol=sym,
                            expected_interval=ivl, window=win)
        n_bars = parse_bars(none_snapshot, expected_symbol=sym,
                            expected_interval=ivl, window=win)
    except EvidenceHold as e:
        return {"verdict": "HOLD", "hold_tag": e.tag,
                "detail": str(e), "checks": {}}
    if [b["datetime"] for b in n_bars] != \
            [b["datetime"] for b in s_bars]:
        return {"verdict": "DATA_UNQUALIFIED",
                "detail": "twin datetime sets differ", "checks": {}}
    try:
        checks = {
            "C1": check_c1(n_bars, s_bars, factor, split_date),
            "C2": check_c2(n_bars, s_bars, factor, split_date),
            "C3": check_c3(n_bars, s_bars, factor, split_date),
            "C4": check_c4(n_bars, s_bars, factor, split_date),
            "C6": check_c6(n_bars, s_bars),
        }
    except EvidenceHold as e:
        return {"verdict": "HOLD", "hold_tag": e.tag,
                "detail": str(e), "checks": {}}
    except (ArithmeticError, ValueError, TypeError) as e:
        return {"verdict": "HOLD",
                "hold_tag": "NUMERIC_EVALUATION_ERROR",
                "detail": f"{type(e).__name__}: {e}", "checks": {}}
    verdict = "PASS" if all(c["status"] == "PASS"
                            for c in checks.values()) \
        else "DATA_UNQUALIFIED"
    return {"verdict": verdict, "checks": checks}


def analyze_revision(*, base_receipt: Path, base_snapshot: Path,
                     rev_receipt: Path, rev_snapshot: Path,
                     expected_params: dict,
                     expected_base_request_id: str,
                     expected_rev_request_id: str,
                     expected_symbol: str,
                     expected_interval: str,
                     expected_window: tuple[str, str],
                     now_ms: int) -> dict:
    """C5: byte-compare base vs revision snapshots.

    C-A: all expectations are mandatory and validated first (base
    and revision request IDs distinct and exact, R-A). C-B: BOTH
    snapshots are parsed and structurally validated (status/meta,
    numeric shape, strictly ascending unique datetimes, window
    containment) BEFORE the byte-identical PASS branch — identical
    bytes no longer bypass structure. Differing bytes are enumerated
    bar-by-bar; the revision verdict is HOLD — classification is
    never automated."""
    try:
        (er_b, er_r), sym, ivl, win, now = _validate_expectations(
            (expected_base_request_id, expected_rev_request_id),
            expected_symbol, expected_interval, expected_window,
            now_ms)
        verify_receipt(base_receipt, base_snapshot, expected_params,
                       expected_request_id=er_b, now_ms=now)
        verify_receipt(rev_receipt, rev_snapshot, expected_params,
                       expected_request_id=er_r, now_ms=now)
        b_list = parse_bars(base_snapshot, expected_symbol=sym,
                            expected_interval=ivl, window=win)
        r_list = parse_bars(rev_snapshot, expected_symbol=sym,
                            expected_interval=ivl, window=win)
    except EvidenceHold as e:
        return {"C5": {"status": "HOLD", "hold_tag": e.tag,
                       "detail": str(e)}, "verdict": "HOLD"}
    base_bytes = Path(base_snapshot).read_bytes()
    rev_bytes = Path(rev_snapshot).read_bytes()
    if base_bytes == rev_bytes:
        return {"C5": {"status": "PASS", "identical": True,
                       "bytes": len(base_bytes)}, "verdict": "PASS"}
    b_bars = {b["datetime"]: b for b in b_list}
    r_bars = {b["datetime"]: b for b in r_list}
    try:
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
    except (ArithmeticError, ValueError, TypeError) as e:
        return {"C5": {"status": "HOLD",
                       "hold_tag": "NUMERIC_EVALUATION_ERROR",
                       "detail": f"{type(e).__name__}: {e}"},
                "verdict": "HOLD"}
    return {"C5": {"status": "DIFFERS", "identical": False,
                   "n_bar_diffs": len(diffs), "diffs": diffs[:50]},
            "verdict": "HOLD"}
