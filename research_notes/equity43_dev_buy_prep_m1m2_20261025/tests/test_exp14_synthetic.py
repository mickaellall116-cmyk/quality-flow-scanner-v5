"""Synthetic-fixture tests for EXP-14-BUY-DEV-EXPLORATORY machinery.

Fixtures only: hand-built inventory rows with planted fires and fields.
No real data is read and no forward return is computed anywhere in
this suite. Covers: de-clustering, +/-20-bar exclusion, same-bin and
session-window rules, ATR% band edges, relaxation-ladder selection,
B-T trend filter, forward-window drops, draw determinism and seed
sensitivity, the returns-mode gate (negative), and the inventory-hash
fail-closed check (negative).
"""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
import exp14_buy as X

FAILS = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        FAILS.append(name)


def bar(sym, idx, bin_="09:30", ordinal=0, atr_pct=0.02, signal=False,
        dom=True, close=100.0, ema21=None, ema55=None, ema200=None):
    return {"symbol": sym, "idx": idx, "ts": f"2025-01-{(idx % 28) + 1:02d}T"
            f"{bin_}:00-05:00", "session_date": "2025-01-01",
            "session_ordinal": ordinal, "bin": bin_, "close": close,
            "atr": (atr_pct * close) if atr_pct is not None else None,
            "atr_pct": atr_pct, "ema21": ema21, "ema55": ema55,
            "ema200": ema200, "signal": signal, "in_generator_domain": dom}


def series(sym, n, fires=(), **kw):
    return [bar(sym, i, signal=(i in fires), **kw) for i in range(n)]


def main():
    # ---- de-clustering --------------------------------------------------
    check("decluster: lone fire kept", X.decluster([100]) == [100])
    check("decluster: fire 20 bars after prior dropped",
          X.decluster([100, 120]) == [100])
    check("decluster: fire 21 bars after prior kept",
          X.decluster([100, 121]) == [100, 121])
    check("decluster: chain uses any prior signal bar, not kept events",
          X.decluster([100, 115, 130]) == [100])

    # ---- exclusion set ---------------------------------------------------
    ex = X.excluded_set({50}, 200)
    check("exclusion: fire itself excluded", 50 in ex)
    check("exclusion: +/-20 inclusive", 30 in ex and 70 in ex)
    check("exclusion: +/-21 not excluded", 29 not in ex and 71 not in ex)

    # ---- B-A pool rules ---------------------------------------------------
    rows = series("AAA", 300, fires={150})
    for r in rows:
        r["session_ordinal"] = r["idx"] // 2
    ev = rows[150]
    ev["session_ordinal"] = 75
    step0 = X.LADDER[0]
    pool = X.eligible_pool(rows, X.excluded_set({150}, 300), ev, step0,
                           10, "B-A")
    check("pool: event bar itself excluded (fire)", 150 not in pool)
    check("pool: +/-20 around fire excluded",
          all(abs(j - 150) > 20 for j in pool))
    check("pool: same-bin only",
          all(rows[j]["bin"] == "09:30" for j in pool))
    rows2 = [dict(r) for r in rows]
    rows2[100]["bin"] = "13:30"
    pool2 = X.eligible_pool(rows2, X.excluded_set({150}, 300), ev, step0,
                            10, "B-A")
    check("pool: opposite-bin bar excluded", 100 not in pool2)
    rows3 = [dict(r) for r in rows]
    rows3[100]["session_ordinal"] = 75 + 31
    pool3 = X.eligible_pool(rows3, X.excluded_set({150}, 300), ev, step0,
                            10, "B-A")
    check("pool: session window 30 enforced", 100 not in pool3)
    rows4 = [dict(r) for r in rows]
    rows4[100]["atr_pct"] = 0.02 * 1.26
    pool4 = X.eligible_pool(rows4, X.excluded_set({150}, 300), ev, step0,
                            10, "B-A")
    check("pool: ATR% band +25% edge excluded at 1.26x", 100 not in pool4)
    # boundary with binary-exact values: event 1/32, pool exactly 1.25x
    rows5 = series("AAA", 300, fires={150}, atr_pct=0.03125)
    for r in rows5:
        r["session_ordinal"] = r["idx"] // 2
    ev5 = rows5[150]
    rows5[100]["atr_pct"] = 0.0390625
    pool5 = X.eligible_pool(rows5, X.excluded_set({150}, 300), ev5, step0,
                            10, "B-A")
    check("pool: ATR% band +25% edge included at exactly 1.25x",
          100 in pool5)
    rows6 = [dict(r) for r in rows]
    rows6[100]["atr_pct"] = None
    pool6 = X.eligible_pool(rows6, X.excluded_set({150}, 300), ev, step0,
                            10, "B-A")
    check("pool: missing ATR% excluded, never imputed", 100 not in pool6)
    rows7 = [dict(r) for r in rows]
    rows7[100]["in_generator_domain"] = False
    pool7 = X.eligible_pool(rows7, X.excluded_set({150}, 300), ev, step0,
                            10, "B-A")
    check("pool: non-domain bar excluded (P-1)", 100 not in pool7)
    pool_h = X.eligible_pool(rows, X.excluded_set({150}, 300), ev, step0,
                             10, "B-A")
    check("pool: forward window h=10 inside data",
          all(j + 10 <= 299 for j in pool_h))
    pool_h20 = X.eligible_pool(rows, X.excluded_set({150}, 300), ev, step0,
                               20, "B-A")
    check("pool: forward window h=20 stricter",
          all(j + 20 <= 299 for j in pool_h20)
          and len(pool_h20) <= len(pool_h))

    # ---- B-T trend filter --------------------------------------------------
    rowsT = series("BBB", 300, fires={150})
    for r in rowsT:
        r["session_ordinal"] = r["idx"] // 2
        r["ema200"], r["ema55"], r["ema21"] = 90.0, 95.0, 96.0
    evT = rowsT[150]
    poolT = X.eligible_pool(rowsT, X.excluded_set({150}, 300), evT, step0,
                            10, "B-T")
    check("B-T: uptrend bars eligible", len(poolT) > 0)
    rowsT2 = [dict(r) for r in rowsT]
    rowsT2[100]["close"] = 80.0  # below EMA200
    poolT2 = X.eligible_pool(rowsT2, X.excluded_set({150}, 300), evT,
                             step0, 10, "B-T")
    check("B-T: close <= EMA200 excluded", 100 not in poolT2)
    poolA2 = X.eligible_pool(rowsT2, X.excluded_set({150}, 300), evT,
                             step0, 10, "B-A")
    check("B-A: same bar allowed (no trend filter)", 100 in poolA2)
    rowsT3 = [dict(r) for r in rowsT]
    rowsT3[100]["ema21"] = 94.0  # EMA21 <= EMA55
    poolT3 = X.eligible_pool(rowsT3, X.excluded_set({150}, 300), evT,
                             step0, 10, "B-T")
    check("B-T: EMA21 <= EMA55 excluded", 100 not in poolT3)

    # ---- ladder selection ---------------------------------------------------
    # Crafted universe: sparse bars so base pools are tiny -> ladder must
    # walk. One symbol, fires every 100 bars, domain bars only near fires.
    rowsL = []
    for i in range(400):
        rowsL.append(bar("CCC", i, ordinal=i // 2, dom=(i % 100 < 40),
                         signal=(i in (10, 210))))
    inv = {"CCC": rowsL}
    # monkeypatch census expectation for the fixture
    orig = X.EXPECTED_FIRES
    X.EXPECTED_FIRES = 2
    try:
        rep, cohort, draws = X.run_pool_counts(inv)
    finally:
        X.EXPECTED_FIRES = orig
    check("ladder: report has 4 steps", len(rep["ladder"]) == 4)
    check("ladder: frozen step is first with drop<=15% or last",
          rep["frozen_step"] == next(
              (r["step"] for r in rep["ladder"] if r["drop_rate"] <= 0.15),
              "c"))
    check("ladder: cohort counted", rep["declustered_events_total"] == 2)

    # ---- draws: determinism + seed sensitivity ------------------------------
    pool = list(range(0, 200, 3))
    d1 = X.event_draws("B-A", "AAA", 150, pool)
    d2 = X.event_draws("B-A", "AAA", 150, pool)
    check("draws: deterministic", d1 == d2)
    check("draws: size 20 without replacement",
          len(d1) == 20 and len(set(d1)) == 20)
    check("draws: drawn from pool", all(x in pool for x in d1))
    d3 = X.event_draws("B-A", "AAA", 151, pool)
    check("draws: per-event sub-seed differs", d3 != d1)
    d4 = X.event_draws("B-T", "AAA", 150, pool)
    check("draws: per-arm sub-seed differs", d4 != d1)
    small = X.event_draws("B-A", "AAA", 150, [5, 9])
    check("draws: pool smaller than 20 drawn whole", small == [5, 9])

    # ---- returns gate (negative) ---------------------------------------------
    try:
        X.compute_forward_returns()
        check("returns gate: raises", False)
    except X.ExecutionGoRequired:
        check("returns gate: raises ExecutionGoRequired", True)

    # ---- inventory hash fail-closed (negative) --------------------------------
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl",
                                     delete=False) as f:
        f.write(json.dumps(bar("ZZZ", 0)) + "\n")
        path = f.name
    try:
        X.load_inventory(path, "0" * 64)
        check("hash gate: mismatch refused", False)
    except SystemExit:
        check("hash gate: mismatch refused", True)
    good = hashlib.sha256(open(path, "rb").read()).hexdigest()
    loaded = X.load_inventory(path, good)
    check("hash gate: matching hash loads", list(loaded) == ["ZZZ"])
    os.unlink(path)

    # ---- census fail-closed (negative) -----------------------------------------
    try:
        X.run_pool_counts({"AAA": series("AAA", 300, fires={150})})
        check("census gate: wrong fire count refused", False)
    except SystemExit:
        check("census gate: wrong fire count refused", True)

    print(f"\n{len(FAILS)} failures")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
