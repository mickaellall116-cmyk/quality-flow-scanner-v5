"""Synthetic qualification harness for s2_split_exclusion_v1 (REQ-S2).

Fixtures only — no real data. Emits canonical JSON (sorted keys) to
stdout; byte-identical across runs in the pinned environment.
Exit 0 iff every case passes.
"""

import copy
import datetime as dt
import hashlib
import json
import sys

from s2_split_exclusion_v1 import (S2Refusal, apply_split_exclusion,
                                   xnys_sessions)

CAL_START, CAL_END = "2026-06-22", "2026-07-20"
FIX_START, FIX_END = "2026-06-29", "2026-07-17"
SESSIONS = xnys_sessions(FIX_START, FIX_END)
RECEIPT = {"receipt_id": "synthetic-acq-1", "status": "INCOMPLETE",
           "symbols": ["AAA", "BBB"], "note": "fixture: deliberately incomplete"}


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def h(obj):
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def make_bars():
    bars = []
    for sym, off in (("AAA", 0.0), ("BBB", 500.0)):
        for i, d in enumerate(SESSIONS):
            for slot, hhmm in (("0930", "09:30"), ("1330", "13:30")):
                c = 100.0 + off + i
                bars.append({
                    "bar_id": f"{sym}-{d.isoformat()}-{slot}",
                    "symbol": sym, "session": d.isoformat(),
                    "bar_start": f"{d.isoformat()}T{hhmm}:00-04:00",
                    "open": c, "high": c + 1.0, "low": c - 1.0,
                    "close": c, "volume": 1000 + i,
                })
    return bars


def make_entries():
    return [
        {"entry_id": "E-AAA-0708", "symbol": "AAA", "session": "2026-07-08",
         "entry_time": "2026-07-08T09:30:00-04:00"},
        {"entry_id": "E-AAA-0713", "symbol": "AAA", "session": "2026-07-13",
         "entry_time": "2026-07-13T09:30:00-04:00"},
        {"entry_id": "E-BBB-0708", "symbol": "BBB", "session": "2026-07-08",
         "entry_time": "2026-07-08T09:30:00-04:00"},
    ]


def ev(symbol, d, **over):
    e = {"symbol": symbol, "effective_session": d,
         "source": "synthetic-fixture", "provenance": "fixture-ledger-v1",
         "as_of": "2026-07-01T00:00:00Z", "version": "1"}
    e.update(over)
    return e


def run(events, bars=None, entries=None, receipt=None):
    return apply_split_exclusion(
        make_bars() if bars is None else bars,
        make_entries() if entries is None else entries,
        events, copy.deepcopy(RECEIPT) if receipt is None else receipt,
        CAL_START, CAL_END)


def removed_sessions(res, symbol):
    return sorted(x["session"] for x in res["removed_sessions_ledger"]
                  if x["symbol"] == symbol)


results = {}
detail = {}


def case(name):
    def deco(fn):
        try:
            fn()
            results[name] = "PASS"
        except AssertionError as e:
            results[name] = f"FAIL: {e}"
        except Exception as e:  # unexpected
            results[name] = f"ERROR: {type(e).__name__}: {e}"
    return deco


@case("calendar_facts")
def _():
    s = [d.isoformat() for d in SESSIONS]
    assert "2026-07-03" not in s, "Jul 3 2026 must be an XNYS holiday"
    assert "2026-07-06" in s and "2026-07-02" in s
    detail["sessions_fixture"] = s


@case("midweek_split")
def _():
    res = run([ev("AAA", "2026-07-08")])
    assert removed_sessions(res, "AAA") == ["2026-07-07", "2026-07-08",
                                            "2026-07-09"]
    assert res["counts"]["bars_before"]["AAA"] - \
        res["counts"]["bars_after"]["AAA"] == 6  # 3 sessions x 2 bars
    detail["midweek_removed_AAA"] = removed_sessions(res, "AAA")


@case("monday_holiday_boundary")
def _():
    # D = Mon 2026-07-06; Fri 07-03 is a holiday, so prev session is Thu 07-02.
    res = run([ev("AAA", "2026-07-06")])
    assert removed_sessions(res, "AAA") == ["2026-07-02", "2026-07-06",
                                            "2026-07-07"]
    detail["monday_removed_AAA"] = removed_sessions(res, "AAA")


@case("civil_day_negative")
def _():
    # Civil-day arithmetic on D=2026-07-06 gives {07-05, 07-06, 07-07}:
    # it would MISS Thu 07-02 and target Sun 07-05 (no session exists).
    d = dt.date(2026, 7, 6)
    civil = {(d + dt.timedelta(days=k)).isoformat() for k in (-1, 0, 1)}
    res = run([ev("AAA", "2026-07-06")])
    sess_removed = set(removed_sessions(res, "AAA"))
    assert "2026-07-02" in sess_removed and "2026-07-02" not in civil
    assert civil != sess_removed
    assert "2026-07-05" not in {x.isoformat() for x in SESSIONS}
    detail["civil_window"] = sorted(civil)
    detail["session_window"] = sorted(sess_removed)


@case("overlapping_union")
def _():
    res = run([ev("AAA", "2026-07-07"), ev("AAA", "2026-07-09")])
    got = removed_sessions(res, "AAA")
    assert got == ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09",
                   "2026-07-10"], got
    led = {x["session"]: x["caused_by"] for x in res["removed_sessions_ledger"]
           if x["symbol"] == "AAA"}
    assert len(led["2026-07-08"]) == 2, "overlap session must cite both events"
    assert len(led) == 5, "ledger must deduplicate the union"


@case("two_symbol_isolation")
def _():
    res = run([ev("AAA", "2026-07-08")])
    assert removed_sessions(res, "BBB") == []
    assert res["counts"]["bars_after"]["BBB"] == \
        res["counts"]["bars_before"]["BBB"]
    assert "E-BBB-0708" not in res["removed_entry_ids"]


@case("entry_removal_matches_bars")
def _():
    res = run([ev("AAA", "2026-07-08")])
    assert res["removed_entry_ids"] == ["E-AAA-0708"]
    bar_sessions = {b["session"] for b in res["bars_out"]
                    if b["symbol"] == "AAA"}
    assert "2026-07-08" not in bar_sessions  # matching bar removal
    kept = {e["entry_id"] for e in res["entries_out"]}
    assert kept == {"E-AAA-0713", "E-BBB-0708"}


def expect_refusal(name, code, fn):
    try:
        fn()
    except S2Refusal as e:
        results[name] = "PASS" if e.code == code else \
            f"FAIL: code {e.code} != {code}"
        detail[name] = e.code
        return
    results[name] = f"FAIL: no refusal raised (wanted {code})"


expect_refusal("non_session_refusal", "NON_SESSION_EFFECTIVE",
               lambda: run([ev("AAA", "2026-07-03")]))  # XNYS holiday
expect_refusal("non_session_refusal_sat", "NON_SESSION_EFFECTIVE",
               lambda: run([ev("AAA", "2026-07-04")]))  # Saturday


def _missing_prov():
    e = ev("AAA", "2026-07-08")
    del e["provenance"]
    run([e])
expect_refusal("provenance_missing_refusal", "MISSING_FIELD", _missing_prov)


def _conflict_dup():
    run([ev("AAA", "2026-07-08"),
         ev("AAA", "2026-07-08", as_of="2026-07-02T00:00:00Z")])
expect_refusal("provenance_conflict_refusal", "DUPLICATE_CONFLICTING_EVENT",
               _conflict_dup)


def _naive_bar():
    bars = make_bars()
    bars[0] = dict(bars[0], bar_start="2026-06-29T09:30:00")  # no offset
    run([ev("AAA", "2026-07-08")], bars=bars)
expect_refusal("tz_naive_refusal", "TZ_NAIVE", _naive_bar)


def _label_mismatch():
    bars = make_bars()
    bars[0] = dict(bars[0], session="2026-06-30")  # ts is 2026-06-29 ET
    run([ev("AAA", "2026-07-08")], bars=bars)
expect_refusal("session_label_refusal", "SESSION_LABEL_MISMATCH",
               _label_mismatch)


@case("receipt_unchanged")
def _():
    res = run([ev("AAA", "2026-07-08")])
    assert res["acquisition_receipt"] == RECEIPT
    assert res["acquisition_receipt"]["status"] == "INCOMPLETE", \
        "exclusion must never upgrade an incomplete acquisition"
    detail["receipt_sha"] = h(RECEIPT)


@case("zero_imputation_ordering")
def _():
    bars, entries = make_bars(), make_entries()
    res = run([ev("AAA", "2026-07-08")], bars=bars, entries=entries)
    in_ids = {b["bar_id"] for b in bars}
    out_ids = {b["bar_id"] for b in res["bars_out"]}
    assert out_ids < in_ids, "output must be a strict subset of input bars"
    assert len(res["bars_out"]) == len(bars) - len(res["removed_bar_ids"])
    assert not (out_ids - in_ids), "no synthetic/imputed bars"
    # post-exclusion session ordering (fold input): strictly increasing,
    # excluded sessions absent, no placeholders.
    aaa_sessions = [b["session"] for b in res["bars_out"]
                    if b["symbol"] == "AAA"]
    uniq = list(dict.fromkeys(aaa_sessions))
    assert uniq == sorted(uniq)
    assert len(uniq) == len(SESSIONS) - 3
    # downstream recompute proof: rolling mean computed from bars_out
    # equals an independent from-scratch recomputation that filters the
    # raw input by the removed-session ledger.
    removed = {(x["symbol"], x["session"])
               for x in res["removed_sessions_ledger"]}

    def roll3(seq):
        return [round(sum(seq[i - 2:i + 1]) / 3.0, 10)
                for i in range(2, len(seq))]

    seq_out = [b["close"] for b in res["bars_out"] if b["symbol"] == "AAA"]
    seq_ref = [b["close"] for b in bars
               if b["symbol"] == "AAA"
               and (b["symbol"], b["session"]) not in removed]
    assert roll3(seq_out) == roll3(seq_ref) and len(seq_out) == len(seq_ref)
    detail["aaa_bars_out"] = len(seq_out)


@case("no_input_mutation")
def _():
    bars, entries = make_bars(), make_entries()
    events = [ev("AAA", "2026-07-08")]
    before = h({"bars": bars, "entries": entries, "events": events,
                "receipt": RECEIPT})
    run(events, bars=bars, entries=entries)
    after = h({"bars": bars, "entries": entries, "events": events,
               "receipt": RECEIPT})
    assert before == after
    detail["input_sha"] = before


def main():
    out = {"results": results, "detail": detail,
           "n_cases": len(results),
           "n_pass": sum(1 for v in results.values() if v == "PASS")}
    print(canon(out))
    return 0 if out["n_pass"] == out["n_cases"] else 1


if __name__ == "__main__":
    sys.exit(main())
