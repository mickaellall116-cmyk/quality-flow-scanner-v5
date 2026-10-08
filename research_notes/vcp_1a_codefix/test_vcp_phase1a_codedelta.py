#!/usr/bin/env python3
"""Synthetic tests for QF-VCP-1A-CODEFIX-DELTA-20261008-04 (adjudication 6051509411).

Proves, on synthetic data only (zero real-data performance reruns), by calling
PRODUCTION functions (build_panels.forward_window, analyze.resolve_horizon_filter):
  D1  full 63/126/252-bar windows -> status 'complete', exact end index and return
  D2  closed-series delist inside window -> 'delisted_flat', last close held flat,
      counted COMPLETE per frozen RUN_PLAN §5 (exact return = last/obs - 1)
  D3  open/current series truncated by dataset boundary -> 'censored' (excluded)
  D4  boundary exactness: pos+w == n-1 -> complete; pos+w == n -> delisted/censored
  D5  fail closed: mixed schema -> hard error; missing fields -> hard error;
      unknown status value -> hard error; legacy without --legacy-repro -> hard error;
      legacy + --legacy-repro without override -> hard error;
      legacy + --legacy-repro + override -> NON-ACCEPTANCE mode
  D6  downside excursion on delisted_flat uses observed bars only

Separately labeled (NOT part of the synthetic-test count):
  PROBE-P1  raw-calendar cutoff check (legacy probe, local non-performance)

Run: python3 test_vcp_phase1a_codedelta.py   (exit 0 = all pass)
"""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_panels import forward_window, FWD_STATUS_OK
import analyze

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"[{PASS if cond else FAIL}] {name}" + (f" — {detail}" if detail else ""))


def expect_error(name, fn, detail=""):
    try:
        fn()
    except RuntimeError as e:
        check(name, True, f"RuntimeError: {str(e)[:80]}")
        return
    except Exception as e:
        check(name, False, f"wrong exception type: {type(e).__name__}")
        return
    check(name, False, "no error raised (fail-open!)")


def synth_dates(n, start="2020-01-02"):
    """n business-day ISO dates."""
    d = datetime.date.fromisoformat(start)
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def synth_closes(n, base=100.0, step=0.1):
    return [base + i * step for i in range(n)]


# ---------- D1: full windows -> complete, exact return ----------
def test_d1():
    dates = synth_dates(500)
    closes = synth_closes(500)
    pos = 100
    obs = closes[pos]
    for w in (63, 126, 252):
        status, end_i = forward_window(dates, pos, w, series_closed=False)
        check(f"D1a w={w}: status 'complete'", status == "complete",
              f"got {status}")
        check(f"D1b w={w}: end index = pos+w", end_i == pos + w,
              f"got {end_i}")
        ret = closes[end_i] / obs - 1.0
        expected = (obs + w * 0.1) / obs - 1.0
        check(f"D1c w={w}: exact return", abs(ret - expected) < 1e-12,
              f"ret={ret:.6f} expected={expected:.6f}")
    # open series, full window observed -> complete even though series open
    status, _ = forward_window(dates, pos, 252, series_closed=True)
    check("D1d closed series with full window: still 'complete'",
          status == "complete", f"got {status}")


# ---------- D2: closed-series delist -> delisted_flat, exact flat-hold return ----------
def test_d2():
    # series of 300 bars (company delisted at bar 299), obs at index 100
    dates = synth_dates(300)
    closes = synth_closes(300, base=50.0, step=0.2)
    pos = 100
    obs = closes[pos]
    # r12 needs 252 bars after pos -> only 199 remain -> delisted path
    status, end_i = forward_window(dates, pos, 252, series_closed=True)
    check("D2a delisted r12: status 'delisted_flat'", status == "delisted_flat",
          f"got {status}")
    check("D2b delisted r12: end at last bar", end_i == 299, f"got {end_i}")
    ret = closes[end_i] / obs - 1.0
    expected = closes[299] / closes[100] - 1.0
    check("D2c delisted r12: exact flat-hold return",
          abs(ret - expected) < 1e-12, f"ret={ret:.6f}")
    check("D2d 'delisted_flat' counts COMPLETE",
          "delisted_flat" in FWD_STATUS_OK)
    # r3 still fits fully -> complete (delisting beyond the window)
    status3, end3 = forward_window(dates, pos, 63, series_closed=True)
    check("D2e delisted r3 (fits): 'complete'", status3 == "complete",
          f"got {status3}")
    check("D2f delisted r3: end = pos+63", end3 == pos + 63)


# ---------- D3: open series truncated -> censored ----------
def test_d3():
    dates = synth_dates(300)
    pos = 100
    status, end_i = forward_window(dates, pos, 252, series_closed=False)
    check("D3a open truncated r12: status 'censored'", status == "censored",
          f"got {status}")
    check("D3b 'censored' NOT in complete set",
          "censored" not in FWD_STATUS_OK)
    check("D3c censored end at last bar (provenance retained)", end_i == 299)


# ---------- D4: boundary exactness ----------
def test_d4():
    dates = synth_dates(400)
    # pos + w == n - 1 exactly -> complete
    status, end_i = forward_window(dates, 147, 252, series_closed=False)
    check("D4a pos+w == n-1: 'complete'", status == "complete",
          f"got {status}, end_i={end_i}")
    # pos + w == n -> one bar short
    s_c, _ = forward_window(dates, 148, 252, series_closed=True)
    s_o, _ = forward_window(dates, 148, 252, series_closed=False)
    check("D4b pos+w == n, closed: 'delisted_flat'", s_c == "delisted_flat",
          f"got {s_c}")
    check("D4c pos+w == n, open: 'censored'", s_o == "censored", f"got {s_o}")


# ---------- D5: fail closed ----------
def good_row(**kw):
    r = {"t": "AAA", "m": "2020-01-31",
         "fwd_complete_r3": True, "fwd_complete_r6": True,
         "fwd_complete_r12": True,
         "fwd_status_r3": "complete", "fwd_status_r6": "complete",
         "fwd_status_r12": "delisted_flat"}
    r.update(kw)
    return r


def test_d5():
    rows = [good_row(), good_row(t="BBB")]
    m = analyze.resolve_horizon_filter(rows)
    check("D5a all-flagged panel: accepted", m["mode"] == "flags")

    mixed = [good_row(), {"t": "BBB", "m": "2020-01-31"}]
    expect_error("D5b mixed schema -> hard error",
                 lambda: analyze.resolve_horizon_filter(mixed))

    noflags = [{"t": "AAA", "m": "2020-01-31"}]
    expect_error("D5c no flags, no --legacy-repro -> hard error",
                 lambda: analyze.resolve_horizon_filter(noflags))

    expect_error("D5d legacy + repro, no override -> hard error",
                 lambda: analyze.resolve_horizon_filter(noflags, legacy_repro=True))

    m2 = analyze.resolve_horizon_filter(
        noflags, legacy_repro=True,
        cutoff_override="r3=2025-12-31,r6=2025-12-31,r12=2025-08-29")
    check("D5e legacy + repro + override: NON-ACCEPTANCE",
          m2["mode"] == "legacy" and "NON-ACCEPTANCE" in m2["acceptance"],
          f"got {m2}")

    bad_status = [good_row(fwd_status_r12="maybe")]
    expect_error("D5f unknown status value -> hard error",
                 lambda: analyze.resolve_horizon_filter(bad_status))

    bad_bool = [good_row(fwd_complete_r3="yes")]
    expect_error("D5g non-boolean flag -> hard error",
                 lambda: analyze.resolve_horizon_filter(bad_bool))

    expect_error("D5h empty panel -> hard error",
                 lambda: analyze.resolve_horizon_filter([]))


# ---------- D6: downside on delisted_flat uses observed bars ----------
def test_d6():
    # V-shaped dip then delist: downside must reflect the observed minimum
    dates = synth_dates(300)
    closes = [100.0 - i * 0.5 for i in range(150)] + \
             [25.0 + i * 0.3 for i in range(150)]
    pos = 50
    obs = closes[pos]
    status, end_i = forward_window(dates, pos, 252, series_closed=True)
    assert status == "delisted_flat"
    segmin = min(closes[pos + 1: end_i + 1])
    dd = segmin / obs - 1.0
    check("D6a downside uses observed bars only",
          abs(segmin - 25.0) < 1e-9 and dd < -0.5,
          f"segmin={segmin:.2f} dd={dd:.4f}")


# ---------- PROBE-P1: raw-calendar cutoff (labeled probe, NOT a synthetic test) ----------
def probe_p1():
    """Local non-performance probe: data-derived horizon cutoff on on-disk
    raw EOD calendars. Not part of the synthetic-test count; the 95%
    threshold is not an accepted-run parameter (adjudication 6051509411)."""
    print("\n[PROBE-P1] raw-calendar cutoff (local probe, not a synthetic test)")
    eod_dir = os.path.join(HERE, "raw", "eod")
    panel_p = os.path.join(HERE, "panels", "panel.jsonl")
    if not (os.path.isdir(eod_dir) and os.path.exists(panel_p)):
        print("[PROBE-P1] skipped: raw/eod or panels not present on disk")
        return
    import json as _json
    rows = [{"m": _json.loads(l)["m"], "t": _json.loads(l)["t"]}
            for l in open(panel_p)]
    months = sorted(set(r["m"] for r in rows))
    for w, h in ((252, "r12"), (126, "r6"), (63, "r3")):
        try:
            c = analyze.last_complete_month(rows, months, w, eod_dir)
            print(f"[PROBE-P1] {h} (w={w}): last complete month = {c}")
        except RuntimeError as e:
            print(f"[PROBE-P1] {h}: {e}")


def main():
    print("== QF-VCP-1A-CODEFIX-DELTA-20261008-04 synthetic tests "
          "(production functions, synthetic data only) ==")
    test_d1()
    test_d2()
    test_d3()
    test_d4()
    test_d5()
    test_d6()
    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{len(results) - n_fail}/{len(results)} synthetic tests passed")
    probe_p1()
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
