#!/usr/bin/env python3
"""
test_coinbase_15m_adapter.py — task -06 offline fixtures.

Deterministic synthetic Coinbase-shaped 15m series (stdlib only).
Every fixture asserts explicit expected values; refusal fixtures assert
the AdapterRefusal code. Prints per-fixture PASS lines, the canonical
output hashes, and a final count. Exit 0 iff all pass.

Run: unshare -n <pinned venv python> test_coinbase_15m_adapter.py
"""
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, ".")
from coinbase_15m_adapter import (AdapterRefusal, aggregate,
                                  expected_15m_count, session_span_utc)

RESULTS = []


def check(name, fn):
    try:
        fn()
        RESULTS.append((name, "PASS"))
        print(f"PASS {name}")
    except Exception as e:  # noqa: BLE001
        RESULTS.append((name, f"FAIL {type(e).__name__}: {e}"))
        print(f"FAIL {name}: {type(e).__name__}: {e}")


def synth_rows(session_dates, drop=(), mutate=None):
    """Deterministic Coinbase rows [time, low, high, open, close, vol]
    for the union of the given session spans, in provider (descending)
    order. Price/volume are pure functions of the global bar index."""
    instants = []
    for d in session_dates:
        s, e = session_span_utc(d)
        t = s
        while t < e:
            instants.append(int(t.timestamp()))
            t += timedelta(seconds=900)
    instants.sort()
    rows = []
    for i, t in enumerate(instants):
        if t in drop:
            continue
        base = 100.0 + (i % 97) * 0.25
        row = [t, base - 0.5, base + 0.75, base, base + 0.25,
               10.0 + (i % 13)]
        if mutate:
            row = mutate(row, i, t)
        rows.append(row)
    rows.reverse()  # provider returns descending; adapter must sort
    return rows


def span_of(session_dates):
    s, _ = session_span_utc(session_dates[0])
    _, e = session_span_utc(session_dates[-1])
    return s, e


def canon_hash(bins):
    return hashlib.sha256(json.dumps(
        bins, sort_keys=True).encode()).hexdigest()


def expect_refusal(code, fn):
    try:
        fn()
    except AdapterRefusal as r:
        assert r.code == code, f"refusal {r.code} != {code} ({r.detail})"
        return
    raise AssertionError(f"no refusal raised; expected {code}")


NORMAL = [date(2024, 1, 10)]
SPRING = [date(2024, 3, 9)]     # session containing 2024-03-10 02:00 jump
FALL = [date(2023, 11, 4)]      # session containing 2023-11-05 fallback


def t_normal_day():
    s, e = span_of(NORMAL)
    assert expected_15m_count(NORMAL[0]) == 96
    bins, anom = aggregate(synth_rows(NORMAL), s, e)
    assert len(bins) == 6 and all(b["n_bars"] == 16 for b in bins), bins
    assert [b["bin_open_et"][11:16] for b in bins] == \
        ["09:30", "13:30", "17:30", "21:30", "01:30", "05:30"]
    assert anom == []
    # honest composition: bin 0 from its 16 bars, by UTC order
    rows = sorted(synth_rows(NORMAL), key=lambda r: r[0])[:16]
    b0 = bins[0]
    assert b0["open"] == rows[0][3] and b0["close"] == rows[-1][4]
    assert b0["high"] == max(r[2] for r in rows)
    assert b0["low"] == min(r[1] for r in rows)
    assert b0["volume"] == sum(r[5] for r in rows)
    print("  normal canonical sha256:", canon_hash(bins))


def t_spring_dst():
    s, e = span_of(SPRING)
    assert expected_15m_count(SPRING[0]) == 92  # 23h session
    bins, _ = aggregate(synth_rows(SPRING), s, e)
    counts = [b["n_bars"] for b in bins]
    assert counts == [16, 16, 16, 16, 12, 16], counts
    assert bins[4]["bin_open_et"][11:16] == "01:30"  # absorbing bin
    assert bins[4]["expected_bars"] == 12
    print("  spring canonical sha256:", canon_hash(bins))


def t_fall_dst():
    s, e = span_of(FALL)
    assert expected_15m_count(FALL[0]) == 100  # 25h session
    bins, _ = aggregate(synth_rows(FALL), s, e)
    counts = [b["n_bars"] for b in bins]
    assert counts == [16, 16, 16, 16, 20, 16], counts
    assert bins[4]["bin_open_et"][11:16] == "01:30"  # absorbing bin
    # both repeated 01:xx wall bars are inside bin 4 (UTC-instant math)
    assert bins[4]["expected_bars"] == 20
    print("  fall canonical sha256:", canon_hash(bins))


def t_missing_row():
    s, e = span_of(NORMAL)
    s0, _ = session_span_utc(NORMAL[0])
    drop = {int(s0.timestamp()) + 40 * 900}
    expect_refusal("GAP", lambda: aggregate(
        synth_rows(NORMAL, drop=drop), s, e))


def t_duplicate_conflict():
    s, e = span_of(NORMAL)
    rows = synth_rows(NORMAL)
    dup = list(rows[10])
    dup[4] = dup[4] + 1.0  # same instant, different close
    rows.append(dup)
    expect_refusal("DUPLICATE", lambda: aggregate(rows, s, e))


def t_overlap_dedupe():
    s, e = span_of(NORMAL)
    full = synth_rows(NORMAL)
    bins_full, _ = aggregate(full, s, e)
    overlapped = full + full[20:35]  # exact-identical overlap rows
    bins_ov, _ = aggregate(overlapped, s, e)
    assert canon_hash(bins_ov) == canon_hash(bins_full)


def t_reversed_order():
    s, e = span_of(NORMAL)
    rows_desc = synth_rows(NORMAL)                 # descending
    rows_asc = list(reversed(rows_desc))           # ascending
    h1 = canon_hash(aggregate(rows_desc, s, e)[0])
    h2 = canon_hash(aggregate(rows_asc, s, e)[0])
    assert h1 == h2


def t_partial_terminal():
    s, e0 = span_of(NORMAL)
    end = s + timedelta(hours=10)  # 2 full bins + half of bin 2
    rows = [r for r in synth_rows(NORMAL) if r[0] < int(end.timestamp())]
    bins, _ = aggregate(rows, s, end, allow_partial_terminal=True)
    assert [b["n_bars"] for b in bins] == [16, 16, 8]
    assert bins[-1]["partial"] is True
    assert bins[0]["partial"] is False
    expect_refusal("GAP", lambda: aggregate(rows, s, end))


def t_zero_volume_nonflat():
    s, e = span_of(NORMAL)

    def mut(row, i, t):
        if i == 5:
            row[5] = 0.0  # high > low, volume 0
        return row
    bins, anom = aggregate(synth_rows(NORMAL, mutate=mut), s, e)
    assert len(bins) == 6
    assert [a["class"] for a in anom] == ["ZERO_VOLUME_NONFLAT"], anom


def t_page_boundary_300():
    dates = [date(2024, 1, 8) + timedelta(days=k) for k in range(4)]
    s, _ = span_of(dates)
    end = s + timedelta(seconds=300 * 900)  # exactly one max page
    rows = [r for r in synth_rows(dates) if r[0] < int(end.timestamp())]
    assert len(rows) == 300
    bins, _ = aggregate(rows, s, end, allow_partial_terminal=True)
    assert sum(b["n_bars"] for b in bins) == 300
    assert bins[-1]["partial"] is True and bins[-1]["n_bars"] == 12


def t_volume_missing():
    s, e = span_of(NORMAL)

    def mut(row, i, t):
        if i == 3:
            row[5] = None  # the TD crypto defect class
        return row
    expect_refusal("SCHEMA", lambda: aggregate(
        synth_rows(NORMAL, mutate=mut), s, e))
    rows = synth_rows(NORMAL)
    rows[0] = rows[0][:5]  # 5-field row
    expect_refusal("SCHEMA", lambda: aggregate(rows, s, e))


def t_misaligned():
    s, e = span_of(NORMAL)

    def mut(row, i, t):
        if i == 7:
            row[0] = t + 60  # off the 900s grid
        return row
    expect_refusal("MISALIGNED", lambda: aggregate(
        synth_rows(NORMAL, mutate=mut), s, e))


def t_out_of_span():
    s, e = span_of(NORMAL)
    rows = synth_rows([NORMAL[0] - timedelta(days=1), NORMAL[0]])
    expect_refusal("OUT_OF_SPAN", lambda: aggregate(rows, s, e))


FIXTURES = [
    ("normal_day", t_normal_day),
    ("spring_dst_23h", t_spring_dst),
    ("fall_dst_25h", t_fall_dst),
    ("missing_row_gap", t_missing_row),
    ("duplicate_conflict", t_duplicate_conflict),
    ("overlap_dedupe", t_overlap_dedupe),
    ("reversed_descending_order", t_reversed_order),
    ("partial_terminal_bin", t_partial_terminal),
    ("zero_volume_nonflat", t_zero_volume_nonflat),
    ("page_boundary_300", t_page_boundary_300),
    ("volume_missing_schema", t_volume_missing),
    ("misaligned_stamp", t_misaligned),
    ("out_of_span", t_out_of_span),
]

if __name__ == "__main__":
    for name, fn in FIXTURES:
        check(name, fn)
    passed = sum(1 for _, r in RESULTS if r == "PASS")
    print(f"TOTAL: {passed}/{len(FIXTURES)} PASS")
    sys.exit(0 if passed == len(FIXTURES) else 1)
