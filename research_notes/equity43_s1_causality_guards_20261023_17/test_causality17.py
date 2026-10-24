"""QF-EQUITY43-S1-CAUSALITY-GUARDS-20261023-17 — causality & provenance
suite.

Part B (FAIL-BEFORE): demonstrates, on the FROZEN -16 observer, the two
defects the -16 adjudication found — (FB1) no current-day bin-close
emission (a session's bars appear only at the next session's first bar
or at flush), and (FB2) journal-replay insufficiency (no INPUT records;
BAR payloads excluded from the journal). These checks PASS when the
defect is demonstrated.

Part C/D (PASS-AFTER): the -17 fork must emit each bin at its close
from data available at that time, fail gaps closed per-bin with no
backfill, handle early closes and both DST directions, never depend on
flush() for live decisions, and replay byte-identically from the
journal alone.

Usage: test_causality17.py <stage> <old_observer.py> <new_observer.py>
Exit 0 iff every check passes. Prints one line per check + SUMMARY.
"""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile

STAGE = os.path.abspath(sys.argv[1])
OLD_PY, NEW_PY = sys.argv[2], sys.argv[3]
for p in (STAGE, os.path.join(STAGE, "engine_successor"),
          os.path.join(STAGE, "engine_successor", "pine_stack"),
          os.path.join(STAGE, "engine_successor", "pine_ranking"),
          os.path.join(STAGE, "engine_successor", "pine_exposure"),
          os.path.join(STAGE, "engine_successor", "pine_signal_quality")):
    sys.path.insert(0, p)

import pandas as pd  # noqa: E402
import pine_backtest as pb  # noqa: E402

TABLE_JSON = json.load(open(os.path.join(STAGE, "session_table.json")))
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}", flush=True)


def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


fo_old = load_mod(OLD_PY, "fo_old16")
fo_new = load_mod(NEW_PY, "fo_new17")


def subset(mod, dates):
    return mod.SessionTable({"sessions": [s for s in TABLE_JSON["sessions"]
                                          if s["date"] in dates]})


def starts_of(date):
    sess = {s["date"]: s for s in TABLE_JSON["sessions"]}[date]
    close = int(sess["close"][:2]) * 60 + int(sess["close"][3:5])
    out, mins = [], 570
    while mins < close:
        out.append(f"{mins // 60:02d}:{mins % 60:02d}")
        mins += 60
    return out


def flat_rows(date, price=100.0, vol=1000.0, skip=()):
    return [{"datetime": f"{date} {s}:00", "open": price, "high": price,
             "low": price, "close": price, "volume": vol}
            for s in starts_of(date) if s not in skip]


def make_obs(mod, symbols, table):
    tmp = tempfile.mkdtemp(prefix="caus17_")
    j = mod.Journal(os.path.join(tmp, "journal.jsonl"),
                    os.path.join(tmp, "anchor.json"))
    return mod.ForwardObserver(table, j, pb, symbols), j, tmp


def bars_of(events):
    return [e for e in events if e["type"] == "BAR"]


# ============================================================ FAIL-BEFORE
def fb1_latency():
    tbl = subset(fo_old, {"2024-03-07", "2024-03-08"})
    obs, j, _ = make_obs(fo_old, ["AAA"], tbl)
    rows = flat_rows("2024-03-07")
    seen = []
    for r in rows:
        seen.extend(obs.ingest("AAA", r))
    after_last_member = len(bars_of(seen))
    nxt = obs.ingest("AAA", flat_rows("2024-03-08")[0])
    after_next_day = len(bars_of(seen)) + len(bars_of(nxt))
    check("FB1_old_observer_bin_close_latency",
          after_last_member == 0 and after_next_day == 2,
          f"bars after all 2024-03-07 rows={after_last_member} "
          f"(defect: bin1 unavailable at 13:30), bars after next "
          f"session's first row={after_next_day}")


def fb2_journal_insufficient():
    tbl = subset(fo_old, {"2024-03-07"})
    obs, j, _ = make_obs(fo_old, ["AAA"], tbl)
    for r in flat_rows("2024-03-07"):
        obs.ingest("AAA", r)
    obs.flush()
    j.anchor("seal")
    j.close()
    recs = [json.loads(ln)
            for ln in open(j.journal_path).read().splitlines()]
    n_input = sum(1 for r in recs if r["type"] == "INPUT")
    bar_recs = [r for r in recs if r["type"] == "BAR"]
    bars_have_payload = any("bar" in r["payload"] for r in bar_recs)
    check("FB2_old_journal_replay_insufficient",
          n_input == 0 and len(bar_recs) > 0 and not bars_have_payload,
          f"INPUT records={n_input}, BAR records={len(bar_recs)}, "
          f"BAR payloads present={bars_have_payload} "
          f"(defect: journal-only replay impossible)")


# ============================================================ PASS-AFTER
def pa1_bin_close_emission():
    tbl = subset(fo_new, {"2024-03-07", "2024-03-08"})
    obs, j, _ = make_obs(fo_new, ["AAA"], tbl)
    rows = flat_rows("2024-03-07")
    evs, at_bin1, ingested_at_bin1 = [], None, None
    for r in rows:
        evs.extend(obs.ingest("AAA", r))
        if r["datetime"].endswith("12:30:00"):
            at_bin1 = list(evs)
            ingested_at_bin1 = r["datetime"]
    b1 = bars_of(at_bin1)
    ok1 = len(b1) == 1 \
        and str(b1[0]["bar"]["decision_instant"]) == \
        "2024-03-07 13:30:00-05:00" \
        and b1[0].get("emitted_at") == "2024-03-07 13:30" \
        and b1[0].get("emission") == "BIN_CLOSE_CAUSAL"
    b_all = bars_of(evs)
    complete = [e for e in evs if e["type"] == "SESSION_COMPLETE"]
    ok2 = len(b_all) == 2 and len(complete) == 1
    check("PA1_bin_emitted_at_close_no_flush", ok1 and ok2,
          f"bin1 emitted during ingest of {ingested_at_bin1}: {ok1}; "
          f"bars={len(b_all)} session_complete={len(complete)} "
          f"before any flush/next-day row")


def pa2_no_flush_dependence():
    tbl = subset(fo_new, {"2024-03-07", "2024-03-08"})
    obs, j, _ = make_obs(fo_new, ["AAA"], tbl)
    evs = []
    for d in ("2024-03-07", "2024-03-08"):
        for r in flat_rows(d):
            evs.extend(obs.ingest("AAA", r))
    before = len(bars_of(evs))
    flushed = obs.flush()
    check("PA2_flush_adds_no_bars", before == 4
          and len(bars_of(flushed)) == 0,
          f"bars without flush={before}, bars added by flush="
          f"{len(bars_of(flushed))}")


def pa3_early_close():
    tbl = subset(fo_new, {"2024-11-29"})
    obs, j, _ = make_obs(fo_new, ["AAA"], tbl)
    evs = []
    for r in flat_rows("2024-11-29"):
        evs.extend(obs.ingest("AAA", r))
    b = bars_of(evs)
    phantom = obs.ingest("AAA", {"datetime": "2024-11-29 15:30:00",
                                 "open": 101.0, "high": 101.0,
                                 "low": 101.0, "close": 101.0,
                                 "volume": 5.0})
    excl = [e for e in phantom if e["type"] == "EXCLUDED_POSTCLOSE"]
    check("PA3_early_close_1300_bin",
          len(b) == 1 and str(b[0]["bar"]["decision_instant"]) ==
          "2024-11-29 13:00:00-05:00" and len(excl) == 1
          and len(bars_of(phantom)) == 0,
          f"bars={len(b)} decision_instant="
          f"{b[0]['bar']['decision_instant'] if b else None} "
          f"excluded={len(excl)}")


def pa4_dst():
    cases = [("2024-03-08", "-05:00"),   # Fri before spring forward
             ("2024-03-11", "-04:00"),   # Mon after spring forward
             ("2024-11-01", "-04:00"),   # Fri before fall back
             ("2024-11-04", "-05:00")]   # Mon after fall back
    tbl = subset(fo_new, {d for d, _ in cases})
    obs, j, _ = make_obs(fo_new, ["AAA"], tbl)
    ok, detail = True, []
    for d, off in cases:
        evs = []
        for r in flat_rows(d):
            evs.extend(obs.ingest("AAA", r))
        b = bars_of(evs)
        good = len(b) == 2 and str(b[0]["bar"]["decision_instant"]) \
            .endswith(off) and b[0].get("emitted_at") == f"{d} 13:30"
        ok = ok and good
        detail.append(f"{d}: bars={len(b)} off_ok="
                      f"{str(b[0]['bar']['decision_instant']).endswith(off) if b else False}")
    check("PA4_dst_both_directions", ok, "; ".join(detail))


def pa5_gap_bin1():
    tbl = subset(fo_new, {"2024-03-07", "2024-03-08"})
    obs, j, _ = make_obs(fo_new, ["AAA"], tbl)
    evs, inc_at_1330 = [], None
    for r in flat_rows("2024-03-07", skip=("11:30",)):
        evs.extend(obs.ingest("AAA", r))
        if r["datetime"].endswith("13:30:00"):
            inc_at_1330 = [e for e in evs
                           if e["type"] == "SESSION_INCOMPLETE"]
    for r in flat_rows("2024-03-08"):
        evs.extend(obs.ingest("AAA", r))
    evs.extend(obs.flush())
    inc = [e for e in evs if e["type"] == "SESSION_INCOMPLETE"]
    bars = bars_of(evs)
    late = obs.ingest("AAA", {"datetime": "2024-03-07 11:30:00",
                              "open": 100.0, "high": 100.0, "low": 100.0,
                              "close": 100.0, "volume": 1000.0})
    late_rej = [e for e in late if e["type"] == "REJECTED"
                and e["class"] == fo_new.REJ_LATE_BAR]
    check("PA5_gap_bin1_fails_closed",
          inc_at_1330 is not None and len(inc_at_1330) == 1
          and inc_at_1330[0]["missing"] == ["11:30"]
          and len(inc) == 1 and len(bars) == 2
          and all(str(b["bar"]["ts"])[:10] == "2024-03-08" for b in bars)
          and len(late_rej) == 1,
          f"incomplete known by 13:30 admission="
          f"{inc_at_1330 is not None and len(inc_at_1330) == 1}, "
          f"total incomplete={len(inc)}, bars={len(bars)} "
          f"(03-08 only), late bar rejected={len(late_rej)}")


def pa6_gap_bin2_only():
    tbl = subset(fo_new, {"2024-03-07"})
    obs, j, _ = make_obs(fo_new, ["AAA"], tbl)
    evs = []
    for r in flat_rows("2024-03-07", skip=("14:30",)):
        evs.extend(obs.ingest("AAA", r))
    evs.extend(obs.flush())
    bars = bars_of(evs)
    inc = [e for e in evs if e["type"] == "SESSION_INCOMPLETE"]
    check("PA6_gap_bin2_completed_bin1_stands",
          len(bars) == 1
          and str(bars[0]["bar"]["decision_instant"]) ==
          "2024-03-07 13:30:00-05:00"
          and len(inc) == 1 and inc[0]["missing"] == ["14:30"],
          f"bars={len(bars)} (bin1 only, emitted at its close), "
          f"incomplete={len(inc)} missing="
          f"{inc[0]['missing'] if inc else None}")


def pa7_outage_truncation():
    tbl = subset(fo_new, {"2024-03-07", "2024-03-08"})
    obs, j, _ = make_obs(fo_new, ["AAA"], tbl)
    partial = [r for r in flat_rows("2024-03-07")
               if r["datetime"][11:16] in ("09:30", "10:30")]
    evs = []
    for r in partial:
        evs.extend(obs.ingest("AAA", r))
    first_next = obs.ingest("AAA", flat_rows("2024-03-08")[0])
    inc = [e for e in first_next if e["type"] == "SESSION_INCOMPLETE"]
    backfill = obs.ingest("AAA", {"datetime": "2024-03-07 11:30:00",
                                  "open": 100.0, "high": 100.0,
                                  "low": 100.0, "close": 100.0,
                                  "volume": 1000.0})
    rej = [e for e in backfill if e["type"] == "REJECTED"
           and e["class"] == fo_new.REJ_LATE_BAR]
    check("PA7_outage_sealed_no_backfill",
          len(inc) == 1 and inc[0]["missing"] ==
          ["11:30", "12:30", "13:30", "14:30", "15:30"]
          and len(bars_of(evs)) == 0 and len(rej) == 1,
          f"sealed at next session's first bar, missing="
          f"{inc[0]['missing'] if inc else None}, backfill "
          f"rejected={len(rej)}")


def _trend_observer_run():
    """A 150-session deterministic trend run on the fork via the -15
    suite's own synthetic generator (bound to the fork module)."""
    import shutil
    scratch = tempfile.mkdtemp(prefix="caus17_trend_")
    pkg = os.path.join(scratch, "pkg")
    os.makedirs(os.path.join(pkg, "observer"))
    os.makedirs(os.path.join(pkg, "tests"))
    shutil.copy(NEW_PY, os.path.join(pkg, "observer", "fwd_observer.py"))
    suite_src = os.path.join(STAGE, "pkg16", "tests",
                             "test_fwd_parity.py")
    shutil.copy(suite_src, os.path.join(pkg, "tests",
                                        "test_fwd_parity.py"))
    argv = sys.argv
    sys.argv = ["test_fwd_parity.py", STAGE]
    try:
        suite = load_mod(os.path.join(pkg, "tests",
                                      "test_fwd_parity.py"), "suite17")
    finally:
        sys.argv = argv
    sessions = suite.first_sessions(150)
    rows = suite.expand_targets(suite.trend_targets(sessions, 0.990,
                                                    250, 262))
    obs, j, tmp = suite.make_observer(["TEST"])
    suite.feed_all(obs, {"TEST": rows})
    j.anchor("causality17 seal")
    j.close()
    return suite, obs, j, rows


def pa8_journal_replay():
    suite, obs, j, rows = _trend_observer_run()
    recs = [json.loads(ln)
            for ln in open(j.journal_path).read().splitlines()]
    n_input = sum(1 for r in recs if r["type"] == "INPUT")
    bar_recs = [r for r in recs if r["type"] == "BAR"]
    payloads_ok = all("bar" in r["payload"] for r in bar_recs)
    out_j = os.path.join(tempfile.mkdtemp(prefix="caus17_replay_"),
                         "replay.jsonl")
    out_a = out_j + ".anchor"
    ok, info = fo_new.replay_journal(
        j.journal_path, j.anchor_path, suite.FULL_TABLE, pb, ["TEST"],
        out_j, out_a)
    check("PA8_journal_only_replay_byte_identical",
          n_input == len(rows) and payloads_ok and ok
          and len(obs.decision_events) > 0,
          f"INPUT={n_input}/{len(rows)} rows, BAR payloads complete="
          f"{payloads_ok}, decision_events={len(obs.decision_events)}, "
          f"replay={info}")


def pa9_replay_tamper_refused():
    suite, obs, j, rows = _trend_observer_run()
    raw = open(j.journal_path).read().splitlines()
    tampered = list(raw)
    rec = json.loads(tampered[3])
    rec["payload"] = {"forged": True}
    tampered[3] = json.dumps(rec, sort_keys=True, separators=(",", ":"))
    tmp = tempfile.mkdtemp(prefix="caus17_tamper_")
    p2 = os.path.join(tmp, "tampered.jsonl")
    open(p2, "w").write("\n".join(tampered) + "\n")
    ok, info = fo_new.replay_journal(p2, j.anchor_path, suite.FULL_TABLE,
                                     pb, ["TEST"],
                                     os.path.join(tmp, "r.jsonl"),
                                     os.path.join(tmp, "r.anchor"))
    check("PA9_replay_refuses_tampered_journal", not ok,
          f"replay ok={ok} (must be False), info={info}")


def pa10_bar_payload_fidelity():
    suite, obs, j, rows = _trend_observer_run()
    recs = [json.loads(ln)
            for ln in open(j.journal_path).read().splitlines()]
    from_journal = [r["payload"]["bar"] for r in recs
                    if r["type"] == "BAR"]
    from_obs = [{"symbol": b["symbol"], "ts": str(b["ts"]),
                 "decision_instant": str(b["decision_instant"]),
                 "Open": b["Open"], "High": b["High"], "Low": b["Low"],
                 "Close": b["Close"], "Volume": b["Volume"],
                 "SessionVWAP": b["SessionVWAP"]}
                for b in obs.bars["TEST"]]
    check("PA10_journal_bar_payloads_are_the_bars",
          from_journal == from_obs and len(from_journal) > 0,
          f"journal BAR payloads={len(from_journal)}, observer bars="
          f"{len(from_obs)}, identical={from_journal == from_obs}")


def main():
    for fn in (fb1_latency, fb2_journal_insufficient,
               pa1_bin_close_emission, pa2_no_flush_dependence,
               pa3_early_close, pa4_dst, pa5_gap_bin1, pa6_gap_bin2_only,
               pa7_outage_truncation, pa8_journal_replay,
               pa9_replay_tamper_refused, pa10_bar_payload_fidelity):
        try:
            fn()
        except Exception as e:
            import traceback
            traceback.print_exc()
            check(fn.__name__, False,
                  f"raised {type(e).__name__}: {e}")
    n_ok = sum(1 for _, ok in RESULTS if ok)
    print(f"SUMMARY {n_ok}/{len(RESULTS)} checks passed")
    return 0 if n_ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
