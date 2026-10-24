"""Shared KILL-injection scenario drivers for -19 r2.

Used by test_kill_boundaries19r2.py (against the r2 bundle: every
scenario must STOP in-loop) and by failbefore19r2.py (against the
frozen r1 bundle: every scenario must FAIL to stop — the
once-per-symbol gap). Each driver returns a facts dict; the callers
assert opposite expectations on the same facts.

Injection mechanics (no manual checker call anywhere):
  * in-loop: the KILL sentinel is created from INSIDE the same-symbol
    row stream — a generator that touches <namespace>/KILL after
    yielding a deterministic number of rows, then keeps yielding.
  * before-flush: the generator touches KILL after its final row,
    i.e. in the gap between the last ingest and the flush call.
  * before-anchor: the observer's candidates() is wrapped (test-side
    subclass of the gate under test) so KILL is created during
    candidate/signal extraction, after flush, before the final anchor.
"""
import json
import math
import os

KILL_AFTER = 60  # deterministic in-loop injection point (row index)


def load_stream(bundle):
    ext = json.load(open(os.path.join(
        bundle, "calendar", "session_table_extended_candidate.json")))
    sess = {s["date"]: s for s in ext["sessions"]}

    def starts(date):
        close = int(sess[date]["close"][:2]) * 60 \
            + int(sess[date]["close"][3:5])
        out, mins = [], 570
        while mins < close:
            out.append(f"{mins // 60:02d}:{mins % 60:02d}")
            mins += 60
        return out

    def synth_rows(symbol, dates, seed=0):
        rows, n, price = [], 0, 100.0 + seed
        for d in dates:
            for s in starts(d):
                n += 1
                drift = 0.35 * math.sin(n / 6.0) \
                    + 0.12 * math.sin(n / 2.3)
                o = price
                c = price + drift
                rows.append({"datetime": f"{d} {s}:00",
                             "open": round(o, 4),
                             "high": round(max(o, c) * 1.001, 4),
                             "low": round(min(o, c) * 0.999, 4),
                             "close": round(c, 4), "volume": 10000.0})
                price = c
        return rows

    dates = [s["date"] for s in ext["sessions"]
             if s["date"] >= "2026-10-19"][:140]
    return {s: synth_rows(s, dates, seed=i * 7)
            for i, s in enumerate(["NVDA", "SPY"])}


def journal_facts(ns):
    jpath = os.path.join(ns, "journal", "observer_journal.jsonl")
    apath = os.path.join(ns, "anchors", "journal_anchor.json")
    records = []
    if os.path.exists(jpath):
        with open(jpath) as f:
            records = [json.loads(ln) for ln in f if ln.strip()]
    inputs = {}
    last_input_time = {}
    for r in records:
        if r["type"] == "INPUT":
            sym = r["payload"]["symbol"]
            inputs[sym] = inputs.get(sym, 0) + 1
            last_input_time[sym] = r["market_time"]
    anchor = None
    if os.path.exists(apath):
        with open(apath) as f:
            anchor = json.loads(f.read())
    verify = None
    if records and anchor is not None:
        import fwd_observer17 as fo
        verify = fo.Journal.verify(jpath, apath)
    return {"records": len(records),
            "types": [r["type"] for r in records],
            "inputs": inputs,
            "last_input_time": last_input_time,
            "anchor_note": anchor["note"] if anchor else None,
            "anchor_seq": anchor["seq"] if anchor else None,
            "verify": verify}


def _gate(g, bundle, prod, ns):
    return g.StagingGate(ns, prod, bundle_root=bundle,
                         namespace_class="synthetic_test")


def scenario_inloop(g, bundle, prod, ns, stream):
    rows = stream["NVDA"]
    kill_path = os.path.join(ns, "KILL")

    def gen():
        for i, row in enumerate(rows):
            if i == KILL_AFTER:
                open(kill_path, "w").close()
            yield row

    stopped = None
    try:
        g.replay_synthetic(_gate(g, bundle, prod, ns), ["NVDA", "SPY"],
                           {"NVDA": gen(), "SPY": stream["SPY"]})
    except g.GateStop as e:
        stopped = e.code
    facts = journal_facts(ns)
    facts.update({"scenario": "inloop", "stopped": stopped,
                  "stream_len_nvda": len(rows),
                  "kill_after": KILL_AFTER,
                  "expected_last_input": rows[KILL_AFTER - 1]["datetime"]})
    return facts


def scenario_before_flush(g, bundle, prod, ns, stream):
    rows = stream["NVDA"]
    kill_path = os.path.join(ns, "KILL")

    def gen():
        for row in rows:
            yield row
        open(kill_path, "w").close()

    stopped = None
    try:
        g.replay_synthetic(_gate(g, bundle, prod, ns), ["NVDA", "SPY"],
                           {"NVDA": gen(), "SPY": stream["SPY"]})
    except g.GateStop as e:
        stopped = e.code
    facts = journal_facts(ns)
    facts.update({"scenario": "before_flush", "stopped": stopped,
                  "stream_len_nvda": len(rows)})
    return facts


def scenario_before_anchor(g, bundle, prod, ns, stream):
    state = {"candidates_called": False}
    base = g.StagingGate

    class KillAtExtraction(base):
        def build_observer(self, symbols):
            fo, obs, journal = super().build_observer(symbols)
            orig = obs.candidates

            def wrapped():
                recs = orig()
                state["candidates_called"] = True
                open(os.path.join(self.ns("KILL")), "w").close()
                return recs

            obs.candidates = wrapped
            return fo, obs, journal

    gate = KillAtExtraction(ns, prod, bundle_root=bundle,
                            namespace_class="synthetic_test")
    stopped = None
    try:
        g.replay_synthetic(gate, ["NVDA"], {"NVDA": stream["NVDA"]})
    except g.GateStop as e:
        stopped = e.code
    facts = journal_facts(ns)
    facts.update({"scenario": "before_anchor", "stopped": stopped,
                  "candidates_called": state["candidates_called"]})
    return facts


def run_all(g, bundle, prod, runtime):
    stream = load_stream(bundle)
    out = {}
    for name, fn in (("inloop", scenario_inloop),
                     ("before_flush", scenario_before_flush),
                     ("before_anchor", scenario_before_anchor)):
        ns = os.path.join(runtime, name)
        os.makedirs(ns)
        out[name] = fn(g, bundle, prod, ns, stream)
    return out
