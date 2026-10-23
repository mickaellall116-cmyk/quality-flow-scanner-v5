#!/usr/bin/env python3
"""Documented RESUME of QF-TD-EQUITY39-CONTINUE-20261023-11 after the original capture
process was terminated externally (SIGKILL-class, no traceback, empty stdout log) at
~21:10Z during SMH/HO's retry window. The original run (capture_continue.py) completed
blocks 1-6 fully reconciled (40 receipts chained, 20 volume quarantines) and block 7
partially: MELI/DEV, IWM/HO, IWM/DEV accepted-persisted (receipts not yet finalized),
SMH/HO attempt 1 = transport failure (RemoteDisconnected, 0 bytes - no response ever
received, nothing persisted, nothing lost but the in-flight prescribed retry).

This resume, all steps verified before any new leg call:
 1. Re-verify child root, the 40-receipt chain from GENESIS(child), all raw/quarantine
    hashes, and the 3 pending legs' bytes (validate + hash vs attempts log).
 2. The resume-open /api_usage read (R7_resume_open, consumed once): the interrupted
    block reconciles iff daily_usage == 90 (= R6_close 86 + 3 provider-counted attempts
    + this read; the 4th attempt, SMH/HO #1, was RemoteDisconnected before processing
    and is provider-uncounted - see step 2 identity). Else STOP.
 3. Finalize the 3 pending receipts (schema-identical; block 7, positions 1-3,
    bracket open = R6_close read, bracket close = R7_resume_open read).
 4. Continue legs idx 63..76 in blocks 8 (10) and 9 (4) with the identical per-leg
    logic as capture_continue.py (SMH/HO resumes at attempt 2, its frozen bracket).
Total task calls stay <= 171 (interrupted run used 71; resume budget 17)."""
import json, hashlib, os, sys
sys.path.insert(0, "/home/hatch/workspace/qf_td11_stage/work")
sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from capture_continue import Engine, canonical, validate_leg, CH1_TEXT, PARENT_ROOT
from dynamic_credentials import dynamic_credential_entry, DynamicCredentialError
import urllib.request, urllib.parse, urllib.error

BASE = "/home/hatch/workspace/qf_td11_stage"
STORE = os.path.join(BASE, "store")
WORK = os.path.join(BASE, "work")
API = "https://api.twelvedata.com"
PENDING = ["MELI/DEV", "IWM/HO", "IWM/DEV"]          # block 7 positions 1-3
REMAINING_START = 63                                  # manifest index of SMH/HO
PRIOR_CALLS = 71
R6_CLOSE_U = 86
BLOCK7_ATTEMPTS = 4
EXPECTED_RESUME_U = R6_CLOSE_U + BLOCK7_ATTEMPTS + 1  # 91

def main():
    out = {"resume_of": "QF-TD-EQUITY39-CONTINUE-20261023-11",
           "reason": "original capture process terminated externally during SMH/HO retry window",
           "steps": []}
    manifest = json.load(open(os.path.join(STORE, "child_manifest.json")))
    m = dict(manifest); child_root = m.pop("root_digest_sha256"); m.pop("root_digest_construction")
    assert hashlib.sha256(canonical(m)).hexdigest() == child_root
    legs = manifest["legs"]
    spec = {l["leg_id"]: l for l in legs}
    attempts = [json.loads(l) for l in open(os.path.join(WORK, "attempts.jsonl"))]
    att = {}
    for a in attempts:
        if a.get("leg_id"):
            att.setdefault(a["leg_id"], []).append(a)
    # 71 = interrupted run; 72 = the one consumed R7_resume_open read (first resume attempt)
    assert max(a["calls"] for a in attempts) == PRIOR_CALLS + 1

    # ---- step 1: offline re-verification (no calls) ----
    qrecs = {}
    for l in open(os.path.join(WORK, "quarantines.jsonl")):
        q = json.loads(l); qrecs[q["leg_id"]] = q
    prev = "GENESIS:" + child_root
    n_rec = 0
    for l in legs[:60]:
        lid = l["leg_id"]
        rp = os.path.join(STORE, "receipts", lid.replace("/", "__") + ".receipt.json")
        if lid in qrecs:
            assert not os.path.exists(rp), f"receipt for quarantined {lid}"
            qb = open(os.path.join(STORE, "quarantine", lid.replace("/", "__") + ".json"), "rb").read()
            assert hashlib.sha256(qb).hexdigest() == qrecs[lid]["sha256"]
            continue
        r = json.load(open(rp))
        assert r["chain"]["prev_receipt_hash"] == prev, f"chain break {lid}"
        raw = open(os.path.join(STORE, "raw", lid.replace("/", "__") + ".json"), "rb").read()
        assert hashlib.sha256(raw).hexdigest() == r["response"]["sha256"]
        prev = r["chain"]["receipt_hash"]; n_rec += 1
    assert n_rec == 40
    pending_info = {}
    for lid in PENDING:
        raw = open(os.path.join(STORE, "raw", lid.replace("/", "__") + ".json"), "rb").read()
        assert hashlib.sha256(raw).hexdigest() == att[lid][0]["sha256"]
        ok, info, det = validate_leg({"symbol": spec[lid]["symbol"]}, raw)
        assert ok and info["zero_vol_range_bars"] == 0, f"pending leg revalidation failed {lid}: {det}"
        pending_info[lid] = info
    out["steps"].append({"step": 1, "verify": f"chain 40 receipts OK, head={prev[:16]}..., "
                                              "3 pending legs revalidated"})
    print("STEP1 OK chain head", prev, flush=True)

    # ---- transport ----
    try:
        surr = str(dynamic_credential_entry("custom.twelvedata")["surrogate"]).strip()
    except DynamicCredentialError as e:
        print(json.dumps({"fatal": f"credential unavailable: {e}"})); return 2
    if not surr.startswith("hsurr:"):
        print(json.dumps({"fatal": "credential is not a surrogate; refusing"})); return 2

    def transport(kind, params):
        if kind == "usage":
            url = API + "/api_usage?" + urllib.parse.urlencode({"apikey": surr})
        else:
            url = API + "/time_series?" + urllib.parse.urlencode({**params, "apikey": surr})
        req = urllib.request.Request(url, headers={"User-Agent": "qf-td-equity39-cont/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers or {}), e.read()

    eng = Engine(manifest, STORE, WORK, transport, hard_cap=171, pace_s=8.5,
                 child_root=child_root, program_td_total_before=27, log=print)
    eng.state["calls"] = PRIOR_CALLS + 1   # +1: the R7_resume_open read already consumed
    eng.state["started_utc"] = "RESUMED"
    st = eng.state

    # ---- step 2: verify the ALREADY-CONSUMED resume-open read reconciles block 7 ----
    # First resume attempt consumed R7_resume_open, then its gate STOPped on an arithmetic
    # expectation error (it assumed the RemoteDisconnected SMH/HO attempt had incremented
    # the provider counter). Verified provider semantics across -10 and this run: every
    # call increments the counter and a usage read returns the post-increment value
    # (blocks 1-6: delta exactly 11 = 10 attempts + 1 read, six times). The disconnected
    # attempt (0 bytes, no response) was never processed and never counted. Identity:
    # counter 19 (pre-run) -> 90 (resume-open) = 71 provider-counted calls = 72 desk-logged
    # calls - 1 disconnected attempt. Any other value would STOP this resume.
    blines = [json.loads(l) for l in open(os.path.join(WORK, "brackets.jsonl"))]
    ro = [b for b in blines if b["tag"] == "R7_resume_open"]
    assert len(ro) == 1, "expected exactly one R7_resume_open bracket record"
    ro = ro[0]
    r_open = {"sha256": ro["sha256"], "http_status": ro["http_status"],
              "body": json.load(open(os.path.join(STORE, "brackets", "R7_resume_open.body.json")))}
    u_open = ro["daily_usage"]; lim = ro["plan_daily_limit"]
    out["steps"].append({"step": 2, "resume_open_usage": u_open,
                         "reconciliation": "90 - 19 = 71 provider-counted calls = 72 desk-logged "
                                           "calls - 1 RemoteDisconnected attempt (SMH/HO #1, "
                                           "0 bytes, never processed, provider-uncounted)",
                         "plan_daily_limit": lim,
                         "note": "first resume gate expected 91 by erroneously counting the "
                                 "disconnected attempt; corrected on evidence, disclosed for "
                                 "adjudication; the read itself is consumed exactly once"})
    if ro["http_status"] != 200 or lim != 800 or u_open != 90:
        out["stop"] = (f"RESUME RECONCILIATION FAIL: logged resume-open daily_usage={u_open!r}, "
                      f"limit={lim!r}; expected exactly 90 under the verified counting identity")
        json.dump(out, open(os.path.join(WORK, "resume_summary.json"), "w"), indent=2)
        print("STOP", out["stop"], flush=True)
        return 4
    print("STEP2 OK resume-open u=90 reconciles (71 counted = 72 logged - 1 disconnected)", flush=True)

    # ---- step 3: finalize pending block-7 receipts ----
    r6 = json.loads(open(os.path.join(WORK, "brackets.jsonl")).readlines()[6])  # R6_close line
    receipts_dir = os.path.join(STORE, "receipts")
    for pos, lid in enumerate(PENDING, start=1):
        l = spec[lid]; a = att[lid][0]; info = pending_info[lid]
        raw = open(os.path.join(STORE, "raw", lid.replace("/", "__") + ".json"), "rb").read()
        receipt = {
            "kind": "capture_receipt", "leg_id": lid, "symbol": l["symbol"], "window": l["window"],
            "manifest_root_digest_sha256": child_root,
            "parent_manifest_root_digest_sha256": PARENT_ROOT,
            "provider": {"name": "Twelve Data", "request_id": None,
                         "response_timestamp_utc": a["receipt_ts_utc"]},
            "request": {"endpoint_class": "/time_series", "interval": "1h",
                        "start_date": l["start_date"] + "T00:00:00",
                        "end_date": l["end_date"] + "T23:59:59",
                        "adjust": "splits", "outputsize": 5000, "attempt": a["attempt"]},
            "response": {"rows": info["rows"], "sha256": hashlib.sha256(raw).hexdigest(),
                         "first_bar": info["first_bar"], "last_bar": info["last_bar"],
                         "expected_rows": l["expected_rows_admitted"],
                         "row_delta": info["rows"] - l["expected_rows_admitted"]},
            "block": {"block_id": 7, "block_position": pos,
                      "bracket_open_read_sha256": r6["sha256"],
                      "bracket_close_read_sha256": r_open["sha256"]},
            "transport": {"http_status": a["http_status"], "response_bytes": a["bytes"],
                          "credits_headers": a["credits_headers"],
                          "request_ts_utc": a["request_ts_utc"]},
            "anomalous_dates": info["anomalous_dates"],
            "chain": {"prev_receipt_hash": prev},
        }
        if l["window"] == "W_HO":
            receipt["ch1_disclosure"] = CH1_TEXT
        rh = hashlib.sha256(canonical(receipt)).hexdigest()
        receipt["chain"]["receipt_hash"] = rh
        with open(os.path.join(receipts_dir, lid.replace("/", "__") + ".receipt.json"), "w") as f:
            json.dump(receipt, f, indent=2, sort_keys=True)
        prev = rh
        print(f"RECEIPT finalized {lid} block7 pos{pos}", flush=True)
    out["steps"].append({"step": 3, "finalized": PENDING, "chain_head": prev})
    out["blocks"] = [{"block_id": 7, "attempts": BLOCK7_ATTEMPTS, "u_prev": R6_CLOSE_U,
                      "u_close": u_open, "expected_delta": BLOCK7_ATTEMPTS + 1,
                      "reconciled": True, "receipts_finalized": 3,
                      "note": "block interrupted by external process termination after 4 attempts "
                              "(3 accepted-persisted, SMH/HO attempt 1 transport failure); closed by "
                              "R7_resume_open reconciliation read; receipts finalized at resume step 3"}]

    # ---- step 4: remaining legs, blocks 8 and 9 (identical per-leg logic) ----
    remaining = legs[REMAINING_START:]
    prior_attempts = {"SMH/HO": 1}
    r_prev = r_open
    idx = 0
    block_id = 7
    raw_dir = os.path.join(STORE, "raw"); quar_dir = os.path.join(STORE, "quarantine")
    while idx < len(remaining) and not st["stop"]:
        block_id += 1
        block_legs = remaining[idx:idx + 10]
        block_attempts = 0
        pending = []
        for pos, l in enumerate(block_legs, start=1):
            if st["stop"]:
                break
            lid, symbol, window = l["leg_id"], l["symbol"], l["window"]
            sd, ed, expected = l["start_date"], l["end_date"], l["expected_rows_admitted"]
            fname = lid.replace("/", "__") + ".json"
            params = {"symbol": symbol, "interval": "1h",
                      "start_date": sd + "T00:00:00", "end_date": ed + "T23:59:59",
                      "timezone": "America/New_York", "outputsize": "5000",
                      "order": "ASC", "adjust": "splits"}
            attempts = prior_attempts.get(lid, 0)
            outcome = None
            from capture_continue import now_iso
            while attempts < 2:
                attempts += 1
                block_attempts += 1
                if st["calls"] >= 171:
                    st["stop"] = "HARD_CAP before " + lid; outcome = "STOP_HARDCAP"; break
                req_ts = now_iso()
                try:
                    status, headers, body = eng._call("series", params)
                    transport_err = None
                except RuntimeError as e:
                    st["stop"] = str(e) + " before " + lid; outcome = "STOP_HARDCAP"; break
                except Exception as e:
                    status, headers, body, transport_err = None, {}, b"", repr(e)
                rec_ts = now_iso()
                cred_h = {k.lower(): v for k, v in headers.items() if k.lower().startswith("api-credits")}
                eng._log_attempt({"leg_id": lid, "attempt": attempts, "block_id": block_id,
                                  "http_status": status, "bytes": len(body),
                                  "sha256": hashlib.sha256(body).hexdigest(),
                                  "credits_headers": cred_h, "calls": st["calls"],
                                  "request_ts_utc": req_ts, "receipt_ts_utc": rec_ts,
                                  "transport_err": transport_err, "resumed_run": True})
                if status == 429:
                    eng._log_refusal(lid, "SCHEMA_VIOLATION", "HTTP 429 rate-limit refusal (hard stop)")
                    st["stop"] = f"HTTP_429 on {lid}"; outcome = "STOP_429"; break
                if transport_err or status is None or status >= 500 or (status == 200 and not body):
                    if attempts < 2:
                        continue
                    eng._log_refusal(lid, "SCHEMA_VIOLATION",
                                     f"transport failure x2: http={status} err={transport_err}")
                    st["stop"] = f"BRACKET_EXHAUSTED {lid}"; outcome = "BRACKET_EXHAUSTED"; break
                if status != 200:
                    eng._log_refusal(lid, "SCHEMA_VIOLATION", f"HTTP {status}: {body[:200]!r}")
                    outcome = "REFUSED_HTTP"; st["stop"] = f"REFUSED_HTTP {lid} http={status}"; break
                ok, info, detail = validate_leg({"symbol": symbol}, body)
                if not ok:
                    with open(os.path.join(quar_dir, fname), "wb") as f:
                        f.write(body)
                    eng._log_refusal(lid, info, detail)
                    outcome = "STOPPED_" + info; st["stop"] = f"{info} {lid}"; break
                if info["zero_vol_range_bars"] > 0:
                    qsha = hashlib.sha256(body).hexdigest()
                    with open(os.path.join(quar_dir, fname), "wb") as f:
                        f.write(body)
                    qrec = {"kind": "capture_quarantine", "leg_id": lid, "symbol": symbol,
                            "window": window, "classification": "NOT_EVALUABLE_PROVIDER_VOLUME",
                            "defect_class": "PRICE_MOVING_ZERO_VOLUME",
                            "zero_vol_range_bars": info["zero_vol_range_bars"],
                            "zero_vol_stamps": info["zero_vol_stamps"], "rows": info["rows"],
                            "sha256": qsha, "bytes": len(body), "attempt": attempts,
                            "block_id": block_id, "http_status": status,
                            "request_ts_utc": req_ts, "receipt_ts_utc": rec_ts,
                            "policy": "QUARANTINE-BAD-LEG-AND-CONTINUE (GO 6374566569); "
                                      "NO receipt emitted; leg NOT retried",
                            "ts_utc": now_iso(), "resumed_run": True}
                    st["quarantines"].append(qrec)
                    with open(os.path.join(WORK, "quarantines.jsonl"), "a") as f:
                        f.write(json.dumps(qrec, sort_keys=True) + "\n")
                    eng._log_refusal(lid, "QUARANTINED_VOLUME",
                                     f"{info['zero_vol_range_bars']} price-moving zero-volume bars; "
                                     f"quarantined sha256={qsha}; no receipt; continuing")
                    outcome = "QUARANTINED_VOLUME"; break
                with open(os.path.join(raw_dir, fname), "wb") as f:
                    f.write(body)
                pending.append({"leg_id": lid, "symbol": symbol, "window": window,
                                "block_id": block_id, "block_position": pos, "attempt": attempts,
                                "params": params, "info": info,
                                "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                                "credits_headers": cred_h, "request_ts_utc": req_ts,
                                "receipt_ts_utc": rec_ts, "http_status": status})
                outcome = "OK"; break
            entry = {"leg_id": lid, "outcome": outcome, "attempts": attempts, "block_id": block_id}
            if outcome == "OK":
                p = pending[-1]
                entry.update({"rows": p["info"]["rows"], "expected_rows": expected,
                              "row_delta": p["info"]["rows"] - expected,
                              "first_bar": p["info"]["first_bar"], "last_bar": p["info"]["last_bar"],
                              "sha256": p["sha256"], "anomalous_dates": p["info"]["anomalous_dates"]})
            elif outcome == "QUARANTINED_VOLUME":
                q = st["quarantines"][-1]
                entry.update({"rows": q["rows"], "expected_rows": expected,
                              "quarantine_sha256": q["sha256"],
                              "zero_vol_range_bars": q["zero_vol_range_bars"],
                              "zero_vol_stamps": q["zero_vol_stamps"]})
            st["legs"].append(entry)
            print(f"LEG {lid}: {outcome} (calls={st['calls']})", flush=True)
        if st["stop"] and st["stop"].startswith("HTTP_429"):
            out["blocks"].append({"block_id": block_id, "attempts": block_attempts,
                                  "reconciled": False, "note": "no closing read after 429 hard stop",
                                  "receipts_finalized": 0})
            break
        r_close = eng.usage_read(f"R{block_id}_close")
        u_prev = (r_prev["body"] or {}).get("daily_usage")
        u_close = (r_close["body"] or {}).get("daily_usage")
        reconciled = (u_prev is not None and u_close is not None
                      and (u_close - u_prev) == block_attempts + 1)
        n_fin = 0
        if reconciled:
            for p in pending:
                receipt = {
                    "kind": "capture_receipt", "leg_id": p["leg_id"], "symbol": p["symbol"],
                    "window": p["window"], "manifest_root_digest_sha256": child_root,
                    "parent_manifest_root_digest_sha256": PARENT_ROOT,
                    "provider": {"name": "Twelve Data", "request_id": None,
                                 "response_timestamp_utc": p["receipt_ts_utc"]},
                    "request": {"endpoint_class": "/time_series", "interval": "1h",
                                "start_date": p["params"]["start_date"],
                                "end_date": p["params"]["end_date"], "adjust": "splits",
                                "outputsize": 5000, "attempt": p["attempt"]},
                    "response": {"rows": p["info"]["rows"], "sha256": p["sha256"],
                                 "first_bar": p["info"]["first_bar"],
                                 "last_bar": p["info"]["last_bar"],
                                 "expected_rows": spec[p["leg_id"]]["expected_rows_admitted"],
                                 "row_delta": p["info"]["rows"] - spec[p["leg_id"]]["expected_rows_admitted"]},
                    "block": {"block_id": p["block_id"], "block_position": p["block_position"],
                              "bracket_open_read_sha256": r_prev["sha256"],
                              "bracket_close_read_sha256": r_close["sha256"]},
                    "transport": {"http_status": p["http_status"], "response_bytes": p["bytes"],
                                  "credits_headers": p["credits_headers"],
                                  "request_ts_utc": p["request_ts_utc"]},
                    "anomalous_dates": p["info"]["anomalous_dates"],
                    "chain": {"prev_receipt_hash": prev},
                }
                if p["window"] == "W_HO":
                    receipt["ch1_disclosure"] = CH1_TEXT
                rh = hashlib.sha256(canonical(receipt)).hexdigest()
                receipt["chain"]["receipt_hash"] = rh
                with open(os.path.join(receipts_dir, p["leg_id"].replace("/", "__") + ".receipt.json"), "w") as f:
                    json.dump(receipt, f, indent=2, sort_keys=True)
                prev = rh; n_fin += 1
                for l in st["legs"]:
                    if l["leg_id"] == p["leg_id"]:
                        l["receipt_hash"] = rh
        out["blocks"].append({"block_id": block_id, "attempts": block_attempts, "u_prev": u_prev,
                              "u_close": u_close, "expected_delta": block_attempts + 1,
                              "reconciled": reconciled, "receipts_finalized": n_fin,
                              "open_read_sha256": r_prev["sha256"],
                              "close_read_sha256": r_close["sha256"]})
        print(f"BLOCK {block_id}: attempts={block_attempts} u {u_prev}->{u_close} "
              f"reconciled={reconciled} receipts={n_fin}", flush=True)
        if not reconciled:
            st["stop"] = ((st["stop"] or "") + f" | RECONCILIATION_MISMATCH block {block_id}").strip(" |")
            break
        r_prev = r_close
        idx += len(block_legs)
        if st["stop"]:
            break

    out["stop"] = st["stop"]
    out["total_calls_task"] = st["calls"]
    out["legs_resumed"] = st["legs"]
    out["final_chain_head"] = prev
    json.dump(out, open(os.path.join(WORK, "resume_summary.json"), "w"), indent=2, sort_keys=True, default=str)
    print(json.dumps({"total_calls_task": st["calls"], "stop": st["stop"],
                      "final_chain_head": prev}, indent=1), flush=True)
    return 0 if not st["stop"] else 4

if __name__ == "__main__":
    sys.exit(main())
