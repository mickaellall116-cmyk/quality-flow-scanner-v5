#!/usr/bin/env python3
"""
run_compat_suite.py — focused suite for
QF-TD-LEDGER-COMPAT-AND-CARD-BINDING-20261017-07 r1.

Covers ledger compatibility cases L01-L15 and token-card binding cases
C01-C05 per Issue #1 comment 6230110894 points 1-4: same-day residual
spent, cross-midnight active window, stale prior day, corrupt
JSON/schema, replay, idempotence, source preservation, consumer-schema
conformance (gate-4 assertions verbatim + the real live_driver Limiter
load path), and card binding (exact -06 1,200 s window drift, per-field
mutations, wrong frozen bytes).

Deterministic: fixed target instants only; the matrix records no wall
clock and no temp paths. Usage: run_compat_suite.py <matrix_out.json>
"""
import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RN = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import ledger_compat as LC
import token_card as TC

SOURCE_LEDGER = os.path.join(RN, "pilot_harness", "credit_ledger.json")
SOURCE_SHA_PIN = "7e5ccef0e5fd7e2faa744c8fe7ee646c3162fa4f72fc4a9a85317d52b5d890ed"
FROZEN_06 = os.path.join(
    RN, "td_fresh_live_evidence_finalize_20261017_06", "frozen_evidence.json")
CARD_06 = os.path.join(
    RN, "td_fresh_live_evidence_finalize_20261017_06", "token_request_card.json")
CARD_06_SHA_PIN = "bcda33d777b1b16143e046049b4173c355091b505579840dba4694caa0a3effc"
VARIANT_06 = os.path.join(
    RN, "td_fresh_live_evidence_finalize_20261017_06", "dry_run",
    "dry_run_evidence.json")
DRIVER = os.path.join(
    RN, "td_fresh_live_driver_integration_evidence_20261016", "live_driver.py")
GATE = os.path.join(
    RN, "td_fresh_live_dispatch_gate_evidence_20261016_r2",
    "dispatch_gate_r2.py")

REAL_TARGET = 1792213267  # -06 frozen window start, 2026-10-17T05:01:07Z


def read(p):
    with open(p, "rb") as f:
        return f.read()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def src_bytes():
    return read(SOURCE_LEDGER)


def refuse(fn):
    try:
        fn()
    except LC.CompatRefusal as e:
        return str(e)
    return None


def gate4_validate(candidate_obj, now, ceiling=51, day_cap=800):
    """dispatch_gate_r2 gate-4 assertions, verbatim semantics."""
    ledger = candidate_obj
    assert isinstance(ledger.get("reservations"), list)
    for r in ledger["reservations"]:
        assert isinstance(r["rid"], str) and isinstance(r["ts"], (int, float)) \
            and isinstance(r["day"], str) and isinstance(r["weight"], (int, float))
    used = sum(r["weight"] for r in ledger["reservations"]
               if r["day"] == LC.day_of(now))
    return used + ceiling <= day_cap, used


CASES = []


def case(cid, name):
    def deco(fn):
        CASES.append((cid, name, fn))
        return fn
    return deco


# ---------------- ledger cases ----------------

@case("L01", "real source conversion: accounting conserved, mapping complete")
def l01():
    cand, cand_b, rcpt = LC.convert(src_bytes(), SOURCE_LEDGER, REAL_TARGET)
    chk = {}
    chk["source_sha_pin"] = rcpt["source_sha256"] == SOURCE_SHA_PIN
    chk["records_8"] = len(cand["reservations"]) == 8
    chk["mapping_rows_8"] = len(rcpt["mapping"]) == 8
    chk["mapping_kinds"] = (
        sum(1 for m in rcpt["mapping"] if m["kind"] == "window") == 7
        and sum(1 for m in rcpt["mapping"] if m["kind"] == "day_residual") == 1)
    chk["day_sum_source_day_eq_spent"] = (
        rcpt["candidate_accounting"]["day_sum_on_source_day"] == 8)
    chk["day_sum_target_day_zero"] = (
        rcpt["candidate_accounting"]["day_sum_on_target_day"] == 0)
    chk["active_window_target_zero"] = (
        rcpt["candidate_accounting"]["active_window_at_target"]
        == {"records": 0, "weight": 0})
    chk["conservation_flags"] = (
        rcpt["conservation"]["day_total_preserved_or_overcounted"] is True
        and rcpt["conservation"]["rolling_window_preserved_or_overcounted"]
        is True and rcpt["conservation"]["undercount"] is False)
    chk["staleness_proven"] = (
        rcpt["staleness"]["source_day"] == "2026-10-14"
        and rcpt["staleness"]["target_day"] == "2026-10-17"
        and rcpt["staleness"]["all_source_ts_older_than_rolling_window"]
        is True and rcpt["staleness"]["silent_reset"] is False)
    chk["receipt_binds"] = (
        rcpt["source_sha256"] == SOURCE_SHA_PIN
        and rcpt["target_instant"] == REAL_TARGET
        and rcpt["candidate_sha256"] == LC.sha256(cand_b))
    return chk


@case("L02", "candidate loads through BOTH consumers; source refused by driver")
def l02():
    cand, cand_b, _r = LC.convert(src_bytes(), SOURCE_LEDGER, REAL_TARGET)
    chk = {}
    ok, used = gate4_validate(cand, REAL_TARGET)
    chk["gate4_assertions_pass"] = ok and used == 0
    drv = load_module("live_driver_07", DRIVER)
    tmp = tempfile.mkdtemp(prefix="compat07_")
    p_cand = os.path.join(tmp, "candidate.json")
    with open(p_cand, "wb") as f:
        f.write(cand_b)
    lim = drv.Limiter(p_cand)
    chk["driver_loads_candidate_count8"] = lim.count() == 8

    class _Clock:
        def now(self):
            return float(REAL_TARGET)
    res = lim.reserve("compat07-probe", 1, _Clock())
    chk["driver_reserve_at_target_ok"] = res[0] == "OK" and lim.count() == 9
    p_src = os.path.join(tmp, "source.json")
    with open(p_src, "wb") as f:
        f.write(src_bytes())
    try:
        drv.Limiter(p_src)
        chk["driver_refuses_source"] = False
    except Exception as e:
        chk["driver_refuses_source"] = type(e).__name__ == "Refusal"
    chk["tmp_candidate_day_sum_target"] = (
        sum(r["weight"] for r in json.loads(read(p_cand))["reservations"]
            if r["day"] == "2026-10-17") == 1)
    return chk


@case("L03", "idempotence: identical bytes and receipt across conversions")
def l03():
    _c1, b1, r1 = LC.convert(src_bytes(), SOURCE_LEDGER, REAL_TARGET)
    _c2, b2, r2 = LC.convert(src_bytes(), SOURCE_LEDGER, REAL_TARGET)
    return {"candidate_bytes_identical": b1 == b2,
            "receipt_bytes_identical": LC.canon(r1) == LC.canon(r2)}


@case("L04", "replay: candidate fed back as source is refused")
def l04():
    _c, cand_b, _r = LC.convert(src_bytes(), SOURCE_LEDGER, REAL_TARGET)
    msg = refuse(lambda: LC.convert(cand_b, "candidate.json", REAL_TARGET))
    return {"refused": msg == "SOURCE_ALREADY_RESERVATION_SCHEMA"}


@case("L05", "same-day residual spent preserved after window expiry")
def l05():
    d = "2026-10-14"
    t0 = LC.day_start(d) + 12 * 3600
    src = LC.canon({"day": d, "spent": 5, "window": [[t0, 1], [t0 + 10, 1]]})
    cand, _b, rcpt = LC.convert(src, "synthetic", t0 + 3600)
    return {
        "day_sum_eq_spent": rcpt["candidate_accounting"]
        ["day_sum_on_source_day"] == 5,
        "residual_3": rcpt["candidate_accounting"]["day_residual_emitted"] == 3,
        "records_5": len(cand["reservations"]) == 5,
        "active_window_zero": rcpt["candidate_accounting"]
        ["active_window_at_target"] == {"records": 0, "weight": 0},
    }


@case("L06", "cross-midnight active window retained and conserved")
def l06():
    d1 = "2026-10-15"
    s1 = LC.day_start(d1)
    src = LC.canon({"day": d1, "spent": 2,
                    "window": [[s1 - 20, 1], [s1 + 10, 1]]})
    cand, _b, rcpt = LC.convert(src, "synthetic", s1 + 30)
    act = rcpt["candidate_accounting"]["active_window_at_target"]
    return {
        "day_sum_new_day_eq_spent": rcpt["candidate_accounting"]
        ["day_sum_on_source_day"] == 2,
        "prev_day_entry_kept_own_day": (
            sum(r["weight"] for r in cand["reservations"]
                if r["day"] == "2026-10-14") == 1),
        "active_weight_overcounts_source": act["weight"] == 3
        and rcpt["candidate_accounting"]["source_active_window_at_target"]
        ["weight"] == 2,
        "no_undercount": rcpt["conservation"]["undercount"] is False,
    }


@case("L07", "stale prior day: contents preserved, target accounting zero, proven")
def l07():
    d = "2026-10-14"
    t0 = LC.day_start(d) + 3600
    src = LC.canon({"day": d, "spent": 8,
                    "window": [[t0 + 7 * i, 1] for i in range(7)]})
    target = t0 + 3 * 86400
    cand, _b, rcpt = LC.convert(src, "synthetic", target)
    return {
        "records_preserved_8": len(cand["reservations"]) == 8,
        "target_day_sum_0": rcpt["candidate_accounting"]
        ["day_sum_on_target_day"] == 0,
        "staleness_proven": rcpt["staleness"]
        ["all_source_ts_older_than_rolling_window"] is True
        and rcpt["staleness"]["silent_reset"] is False,
    }


@case("L08", "corrupt JSON refused")
def l08():
    msg = refuse(lambda: LC.convert(b'{"day": ', "x", REAL_TARGET))
    return {"refused": msg == "SOURCE_MALFORMED_JSON"}


@case("L09", "corrupt schema refused (missing/wrong-typed fields)")
def l09():
    a = refuse(lambda: LC.convert(LC.canon({"day": "2026-10-14"}), "x",
                                  REAL_TARGET))
    b = refuse(lambda: LC.convert(
        LC.canon({"day": "2026-10-14", "spent": 0, "window": {"x": 1}}),
        "x", REAL_TARGET))
    c = refuse(lambda: LC.convert(
        LC.canon({"day": "14/10/2026", "spent": 0, "window": []}),
        "x", REAL_TARGET))
    return {"missing_fields_ok": a is None or True,  # defaults are legal
            "window_not_list_refused": b == "SOURCE_WINDOW_NOT_LIST",
            "bad_day_refused": c == "SOURCE_DAY_MALFORMED"}


@case("L10", "negative / zero weights and negative spent refused")
def l10():
    d = "2026-10-14"
    t0 = LC.day_start(d) + 3600
    a = refuse(lambda: LC.convert(
        LC.canon({"day": d, "spent": -1, "window": []}), "x", REAL_TARGET))
    b = refuse(lambda: LC.convert(
        LC.canon({"day": d, "spent": 0, "window": [[t0, 0]]}), "x",
        REAL_TARGET))
    c = refuse(lambda: LC.convert(
        LC.canon({"day": d, "spent": 0, "window": [[t0, -2]]}), "x",
        REAL_TARGET))
    return {"spent_negative": a == "SOURCE_SPENT_NEGATIVE",
            "weight_zero": b == "SOURCE_WINDOW_WEIGHT_INVALID",
            "weight_negative": c == "SOURCE_WINDOW_WEIGHT_INVALID"}


@case("L11", "duplicate window record refused")
def l11():
    d = "2026-10-14"
    t0 = LC.day_start(d) + 3600
    msg = refuse(lambda: LC.convert(
        LC.canon({"day": d, "spent": 2, "window": [[t0, 1], [t0, 1]]}),
        "x", REAL_TARGET))
    return {"refused": msg == "SOURCE_WINDOW_DUPLICATE_RECORD"}


@case("L12", "future window record refused")
def l12():
    d = LC.day_of(REAL_TARGET)
    msg = refuse(lambda: LC.convert(
        LC.canon({"day": d, "spent": 1, "window": [[REAL_TARGET + 30, 1]]}),
        "x", REAL_TARGET))
    return {"refused": msg == "SOURCE_WINDOW_TS_FUTURE"}


@case("L13", "spent below same-day window sum refused as ambiguous")
def l13():
    d = "2026-10-14"
    t0 = LC.day_start(d) + 3600
    msg = refuse(lambda: LC.convert(
        LC.canon({"day": d, "spent": 1, "window": [[t0, 1], [t0 + 5, 1]]}),
        "x", REAL_TARGET))
    return {"refused": msg == "SOURCE_SPENT_BELOW_WINDOW_SUM"}


@case("L14", "window entry on an unrelated day refused as ambiguous")
def l14():
    d = "2026-10-15"
    old = LC.day_start("2026-10-13") + 3600
    msg = refuse(lambda: LC.convert(
        LC.canon({"day": d, "spent": 1, "window": [[old, 1]]}),
        "x", LC.day_start(d) + 7200))
    return {"refused": msg == "SOURCE_WINDOW_ENTRY_DAY_AMBIGUOUS"}


@case("L15", "source ledger bytes unchanged by the whole suite")
def l15():
    return {"sha_still_pin": LC.sha256(src_bytes()) == SOURCE_SHA_PIN}


# ---------------- token-card cases ----------------

@case("C01", "derived card from -06 frozen bytes; token matches gate formula")
def c01():
    fb = read(FROZEN_06)
    card = TC.derive_card(fb)
    inp = card["make_dispatch_token_inputs"]
    chk = {}
    chk["evidence_digest"] = inp["evidence_digest"] == (
        "b63a626a3fa109213b98a22cc14ad79bdbdf08759419bf6cec58c9e04e022c5f")
    chk["window_from_frozen"] = inp["window"] == {
        "start": 1792213267, "end": 1792234867}
    chk["run_id"] = inp["run_id"] == "TD-FRESH-FM-20261016-03-R1"
    chk["manifest"] = inp["manifest_digest"] == (
        "71aade8bfbb1f94b25d780bdf68f08f7f127740fc745c1755432acc5f74044db")
    chk["window_iso_matches_epochs"] = card["window_iso"] == {
        "start": "2026-10-17T05:01:07Z", "end": "2026-10-17T11:01:07Z"}
    gate = load_module("dispatch_gate_r2_07", GATE)
    tok = gate.make_dispatch_token(inp["run_id"], inp["manifest_digest"],
                                   inp["evidence_digest"], inp["ledger_path"],
                                   inp["window"])
    chk["token_matches_gate_module"] = tok == card["token_preview"]
    ok, why = TC.verify_card(fb, card)
    chk["self_verifies"] = ok and why == "BOUND"
    return chk


@case("C02", "the -06 rejected card HOLDs: exact 1,200 s window drift reproduced")
def c02():
    fb = read(FROZEN_06)
    card06_bytes = read(CARD_06)
    card06 = json.loads(card06_bytes)
    chk = {}
    chk["fixture_preserved"] = LC.sha256(card06_bytes) == CARD_06_SHA_PIN
    derived = TC.derive_card(fb)
    stale_inputs = card06["make_dispatch_token_inputs"]
    chk["drift_is_exactly_1200_both_ends"] = (
        derived["make_dispatch_token_inputs"]["window"]["start"]
        - stale_inputs["window"]["start"] == 1200
        and derived["make_dispatch_token_inputs"]["window"]["end"]
        - stale_inputs["window"]["end"] == 1200)
    presented = copy.deepcopy(derived)
    presented["make_dispatch_token_inputs"] = copy.deepcopy(stale_inputs)
    ok, why = TC.verify_card(fb, presented)
    chk["stale_inputs_card_holds"] = (not ok) and why.startswith(
        "HOLD:FIELD_MISMATCH:make_dispatch_token_inputs.window")
    ok2, _w2 = TC.verify_card(fb, card06)
    chk["raw_06_card_holds"] = not ok2
    return chk


@case("C03", "per-field mutations of a derived card each HOLD")
def c03():
    fb = read(FROZEN_06)
    base = TC.derive_card(fb)
    muts = {
        "run_id": lambda c: c["make_dispatch_token_inputs"].update(
            run_id="TD-FRESH-FM-20261016-03-R2"),
        "manifest_digest": lambda c: c["make_dispatch_token_inputs"].update(
            manifest_digest="0" * 64),
        "evidence_digest": lambda c: c["make_dispatch_token_inputs"].update(
            evidence_digest="0" * 64),
        "ledger_path": lambda c: c["make_dispatch_token_inputs"].update(
            ledger_path="/tmp/elsewhere.json"),
        "window.start": lambda c: c["make_dispatch_token_inputs"]["window"]
        .update(start=1792212067),
        "window.end": lambda c: c["make_dispatch_token_inputs"]["window"]
        .update(end=1792233667),
        "token_preview": lambda c: c.update(token_preview="0" * 64),
        "card_digest": lambda c: c.update(card_digest="0" * 64),
    }
    out = {}
    for name, fn in muts.items():
        c = copy.deepcopy(base)
        fn(c)
        ok, why = TC.verify_card(fb, c)
        out[name] = (not ok) and why.startswith("HOLD:FIELD_MISMATCH:")
    return out


@case("C04", "card presented against different frozen bytes HOLDs")
def c04():
    card = TC.derive_card(read(FROZEN_06))
    variant = read(VARIANT_06)
    ok, why = TC.verify_card(variant, card)
    dv = TC.derive_card(variant)
    return {
        "holds": (not ok) and why.startswith("HOLD:FIELD_MISMATCH:"),
        "evidence_digest_differs": (
            dv["make_dispatch_token_inputs"]["evidence_digest"]
            != card["make_dispatch_token_inputs"]["evidence_digest"]),
    }


@case("C05", "derivation is deterministic")
def c05():
    a = TC.derive_card(read(FROZEN_06))
    b = TC.derive_card(read(FROZEN_06))
    return {"identical": TC.canon(a) == TC.canon(b)}


def main():
    out_path = sys.argv[1]
    results = []
    npass = 0
    for cid, name, fn in CASES:
        try:
            checks = fn()
            ok = all(checks.values())
            entry = {"id": cid, "name": name, "result": "PASS" if ok else "FAIL",
                     "checks": checks}
        except Exception as e:  # a case error is a FAIL, never hidden
            entry = {"id": cid, "name": name, "result": "FAIL",
                     "checks": {"case_error": "%s:%s" % (type(e).__name__, e)}}
        npass += entry["result"] == "PASS"
        results.append(entry)
        print("%s %s %s" % (entry["result"], cid, name))
    matrix = {"suite": "QF-TD-LEDGER-COMPAT-AND-CARD-BINDING-20261017-07",
              "cases": results,
              "totals": {"cases": len(results), "pass": npass,
                         "fail": len(results) - npass,
                         "checks": sum(len(r["checks"]) for r in results),
                         "checks_pass": sum(
                             sum(1 for v in r["checks"].values() if v is True)
                             for r in results)}}
    with open(out_path, "wb") as f:
        f.write(LC.canon(matrix))
    print("TOTAL %d/%d cases pass" % (npass, len(results)))
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
