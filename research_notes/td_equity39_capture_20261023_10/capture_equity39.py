#!/usr/bin/env python3
"""QF-TD-EQUITY39-CAPTURE-20261023-10 (Issue #1 comment 6374269350; GO Slack TS 1792787921.216909).
Fail-closed live capture of the 78 frozen legs in manifest root ca49892062f1ac5d4ec...
BLOCK-BRACKET-10 (-91): sequential attempts in manifest order, blocks of <=10 attempts;
one /api_usage read opens the phase (preflight) and one closes every block (chained);
block reconciliation u_k - u_{k-1} = attempts_k + 1, mismatch = HALT; <=2 attempts/leg;
a leg exhausting its bracket or failing validation STOPS the capture (partial coverage reported).
Receipts per QF-CAPTURE-RECEIPT-CANDIDATE-20261023-01 as amended by -91: hash-chained,
block_id/block_position/bracket-read hashes, NO per-leg usage fields; emitted ONLY for legs
passing every wrapper validation, finalized at block close. Refusals logged, never chained.
Price-moving zero-volume anomaly (SMCI rule) = quarantine byte-exact + STOP.
HO bytes are raw qualification input only. The surrogate credential is never printed/written."""
import json, hashlib, time, sys, os, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import dynamic_credential_entry, DynamicCredentialError

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
BASE = "/home/hatch/workspace/qf_td10_stage"
STORE = os.path.join(BASE, "store")
WORK = os.path.join(BASE, "work")
MANIFEST_ROOT = "ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64"
HARD_CAP = 173            # worst-case call arithmetic for this run (incl. all usage reads)
BLOCK_SIZE = 10
PACE_S = 8.5
API = "https://api.twelvedata.com"
CH1_TEXT = ("CH-1 disclosed assumption (three-gate freeze a126ce5): the adopted 751-session "
            "calendar rests on the NYSE Group/ICE release of 2022-12-21 for the 2023 window; "
            "in-era 2023 core-hours documentation pursued in parallel, non-blocking.")

with open(os.path.join(STORE, "capture_manifest.json")) as f:
    MANIFEST = json.load(f)
LEGS = [(l["leg_id"], l["symbol"], l["window"], l["start_date"], l["end_date"],
         l["expected_rows_admitted"]) for l in MANIFEST["legs"]]
assert len(LEGS) == 78 and len({l[0] for l in LEGS}) == 78

state = {"calls": 0, "started_utc": None, "last_call_start": 0.0, "preflight": None,
         "legs": [], "refusals": [], "blocks": [], "stop": None,
         "program_td_total_before": 24}

def now_iso():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def pace():
    dt = time.time() - state["last_call_start"]
    if state["last_call_start"] and dt < PACE_S:
        time.sleep(PACE_S - dt)

def get_surrogate():
    entry = dynamic_credential_entry("custom.twelvedata")
    return str(entry["surrogate"]).strip()

def http_get(url):
    if state["calls"] >= HARD_CAP:
        raise RuntimeError("HARD_CAP reached before request")
    pace()
    state["last_call_start"] = time.time()
    state["calls"] += 1
    req = urllib.request.Request(url, headers={"User-Agent": "qf-td-equity39/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()

def log_attempt(rec):
    with open(os.path.join(WORK, "attempts.jsonl"), "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")

def log_refusal(leg_id, reason, detail):
    rec = {"kind": "capture_refusal", "leg_id": leg_id, "reason": reason,
           "detail": detail, "ts_utc": now_iso()}
    state["refusals"].append(rec)
    with open(os.path.join(WORK, "refusals.jsonl"), "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")

def wall_to_instants(stamps):
    out, last = [], None
    for s in stamps:
        naive = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        cands = sorted({naive.replace(tzinfo=ET, fold=f).astimezone(UTC).timestamp()
                        for f in (0, 1)})
        pick = None
        for c in cands:
            if last is None or c > last:
                pick = c
                break
        if pick is None:
            if last is not None and cands and cands[-1] == last:
                raise ValueError("DUPLICATE_INSTANT at " + s)
            raise ValueError("OUT_OF_ORDER at " + s)
        out.append(pick)
        last = pick
    return out

def validate_leg(leg, body):
    """Wrapper validation identical to the pilot's. Returns (ok, info_or_reason, detail)."""
    try:
        doc = json.loads(body.decode("utf-8"))
    except Exception as e:
        return False, "SCHEMA_VIOLATION", f"unparseable JSON: {e}"
    if doc.get("status") != "ok":
        return False, "SCHEMA_VIOLATION", f"status={doc.get('status')!r} code={doc.get('code')!r} msg={doc.get('message')!r}"
    meta = doc.get("meta", {})
    if meta.get("symbol") != leg["symbol"] or meta.get("interval") != "1h":
        return False, "SCHEMA_VIOLATION", f"meta mismatch: {meta.get('symbol')!r}/{meta.get('interval')!r}"
    vals = doc.get("values")
    if not isinstance(vals, list) or not vals:
        return False, "SCHEMA_VIOLATION", "values missing/empty"
    rows = len(vals)
    if rows == 5000:
        return False, "TRUNCATION_SUSPECT", "exactly 5000 rows"
    stamps = []
    zero_vol_range = 0
    for v in vals:
        try:
            o, h, lo, c = (float(v["open"]), float(v["high"]), float(v["low"]), float(v["close"]))
            vol = float(v["volume"])
        except Exception:
            return False, "SCHEMA_VIOLATION", f"non-numeric field in row {v!r}"
        for x in (o, h, lo, c, vol):
            if x != x or x in (float("inf"), float("-inf")):
                return False, "NONFINITE_VALUE", f"non-finite in row {v!r}"
        if vol < 0:
            return False, "SCHEMA_VIOLATION", f"negative volume in row {v!r}"
        if vol == 0 and h > lo:
            zero_vol_range += 1
        stamps.append(v["datetime"])
    try:
        instants = wall_to_instants(stamps)
    except ValueError as e:
        msg = str(e)
        reason = "DUPLICATE_INSTANT" if msg.startswith("DUPLICATE") else "SCHEMA_VIOLATION"
        return False, reason, msg
    from collections import defaultdict
    by_date = defaultdict(list)
    for s, inst in zip(stamps, instants):
        by_date[s[:10]].append((s, inst))
    bad_dates = []
    for d, items in sorted(by_date.items()):
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        mins = [s[14:16] for s, _ in items]
        if dt.weekday() >= 5 or len(items) not in (4, 7) or set(mins) != {"30"}:
            bad_dates.append([d, len(items)])
            continue
        for (_, a), (_, b) in zip(items, items[1:]):
            if b - a != 3600:
                return False, "GAP_VIOLATION", f"equity intra-session gap on {d}"
    info = {"rows": rows, "first_bar": stamps[0], "last_bar": stamps[-1],
            "zero_vol_range_bars": zero_vol_range, "anomalous_dates": bad_dates}
    return True, info, None

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def usage_read(surr, tag):
    """One /api_usage read (never retried). Returns read record dict."""
    url = API + "/api_usage?" + urllib.parse.urlencode({"apikey": surr})
    req_ts = now_iso()
    status, headers, body = http_get(url)
    rec_ts = now_iso()
    rec = {"tag": tag, "request_ts_utc": req_ts, "receipt_ts_utc": rec_ts,
           "http_status": status, "sha256": hashlib.sha256(body).hexdigest(),
           "bytes": len(body), "body": None,
           "credits_headers": {k.lower(): v for k, v in headers.items()
                               if k.lower().startswith("api-credits")}}
    try:
        rec["body"] = json.loads(body.decode("utf-8"))
    except Exception:
        rec["body"] = None
    os.makedirs(os.path.join(STORE, "brackets"), exist_ok=True)
    with open(os.path.join(STORE, "brackets", tag + ".body.json"), "wb") as f:
        f.write(body)
    with open(os.path.join(WORK, "brackets.jsonl"), "a") as f:
        f.write(json.dumps({k: v for k, v in rec.items() if k != "body"} |
                           {"daily_usage": (rec["body"] or {}).get("daily_usage"),
                            "plan_daily_limit": (rec["body"] or {}).get("plan_daily_limit")},
                           sort_keys=True) + "\n")
    log_attempt({"kind": "api_usage", "tag": tag, "http_status": status,
                 "calls": state["calls"], "daily_usage": (rec["body"] or {}).get("daily_usage")})
    return rec

def main():
    state["started_utc"] = now_iso()
    try:
        surr = get_surrogate()
    except DynamicCredentialError as e:
        print(json.dumps({"fatal": f"credential unavailable: {e}"}))
        return 2
    if not surr.startswith("hsurr:"):
        print(json.dumps({"fatal": "credential is not a surrogate; refusing"}))
        return 2

    raw_dir = os.path.join(STORE, "raw")
    receipts_dir = os.path.join(STORE, "receipts")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(receipts_dir, exist_ok=True)

    # ---- PREFLIGHT = phase-opening bracket read R0 (once, never retried) ----
    r_prev = usage_read(surr, "R0_preflight")
    pf_body = r_prev["body"]
    pf = {"request_ts_utc": r_prev["request_ts_utc"], "receipt_ts_utc": r_prev["receipt_ts_utc"],
          "http_status": r_prev["http_status"], "sha256": r_prev["sha256"],
          "bytes": r_prev["bytes"], "body": pf_body,
          "credits_headers": r_prev["credits_headers"]}
    os.makedirs(os.path.join(STORE, "preflight"), exist_ok=True)
    with open(os.path.join(STORE, "preflight", "api_usage.body.json"), "wb") as f:
        f.write(open(os.path.join(STORE, "brackets", "R0_preflight.body.json"), "rb").read())
    with open(os.path.join(STORE, "preflight", "preflight.json"), "w") as f:
        json.dump(pf, f, indent=2, sort_keys=True)
    state["preflight"] = pf
    if r_prev["http_status"] != 200 or not pf_body:
        state["stop"] = f"PREFLIGHT_FAIL http={r_prev['http_status']}"
        return finish(3)
    daily_limit, daily_usage = pf_body.get("plan_daily_limit"), pf_body.get("daily_usage")
    if daily_limit != 800:
        state["stop"] = (f"ABORT plan_daily_limit={daily_limit!r} != 800 "
                         f"(daily fields only; plan_limit={pf_body.get('plan_limit')!r} is per-minute)")
        return finish(3)
    if daily_usage is None or (800 - daily_usage) < HARD_CAP:
        state["stop"] = f"ABORT insufficient headroom for worst case: daily_usage={daily_usage!r}, need {HARD_CAP}"
        return finish(3)

    prev_hash = "GENESIS:" + MANIFEST_ROOT
    leg_idx = 0
    block_id = 0
    while leg_idx < len(LEGS) and not state["stop"]:
        block_id += 1
        block_legs = LEGS[leg_idx:leg_idx + BLOCK_SIZE]
        block_attempts = 0
        pending = []   # accepted legs in this block awaiting receipt finalization
        block_stop = None
        for pos, (leg_id, symbol, window, sd, ed, expected) in enumerate(block_legs, start=1):
            if state["stop"]:
                block_stop = state["stop"]
                break
            leg = {"symbol": symbol}
            fname = leg_id.replace("/", "__") + ".json"
            params = {"symbol": symbol, "interval": "1h",
                      "start_date": sd + "T00:00:00", "end_date": ed + "T23:59:59",
                      "timezone": "America/New_York", "outputsize": "5000",
                      "order": "ASC", "adjust": "splits"}
            attempts, outcome = 0, None
            while attempts < 2:
                attempts += 1
                block_attempts += 1
                if state["calls"] >= HARD_CAP:
                    state["stop"] = "HARD_CAP before " + leg_id
                    outcome = "STOP_HARDCAP"
                    break
                url = API + "/time_series?" + urllib.parse.urlencode({**params, "apikey": surr})
                req_ts = now_iso()
                try:
                    status, headers, body = http_get(url)
                    transport_err = None
                except Exception as e:
                    status, headers, body, transport_err = None, {}, b"", repr(e)
                rec_ts = now_iso()
                cred_h = {k.lower(): v for k, v in headers.items() if k.lower().startswith("api-credits")}
                log_attempt({"leg_id": leg_id, "attempt": attempts, "block_id": block_id,
                             "http_status": status, "bytes": len(body),
                             "sha256": hashlib.sha256(body).hexdigest(),
                             "credits_headers": cred_h, "calls": state["calls"],
                             "request_ts_utc": req_ts, "receipt_ts_utc": rec_ts,
                             "transport_err": transport_err})
                if status == 429:
                    log_refusal(leg_id, "SCHEMA_VIOLATION", "HTTP 429 rate-limit refusal (hard stop)")
                    state["stop"] = f"HTTP_429 on {leg_id}"
                    outcome = "STOP_429"
                    break
                if transport_err or status is None or status >= 500 or (status == 200 and not body):
                    if attempts < 2:
                        continue
                    log_refusal(leg_id, "SCHEMA_VIOLATION", f"transport failure x2: http={status} err={transport_err}")
                    state["stop"] = f"BRACKET_EXHAUSTED {leg_id}"
                    outcome = "BRACKET_EXHAUSTED"
                    break
                if status != 200:
                    log_refusal(leg_id, "SCHEMA_VIOLATION", f"HTTP {status}: {body[:200]!r}")
                    outcome = "REFUSED_HTTP"
                    state["stop"] = f"REFUSED_HTTP {leg_id} http={status}"
                    break
                ok, info, detail = validate_leg(leg, body)
                if not ok:
                    reason = info
                    qpath = os.path.join(WORK, "quarantine")
                    os.makedirs(qpath, exist_ok=True)
                    with open(os.path.join(qpath, fname), "wb") as f:
                        f.write(body)
                    log_refusal(leg_id, reason, detail)
                    outcome = "QUARANTINED_" + reason
                    state["stop"] = f"{reason} {leg_id}"
                    break
                if info["zero_vol_range_bars"] > 0:
                    qpath = os.path.join(WORK, "quarantine")
                    os.makedirs(qpath, exist_ok=True)
                    with open(os.path.join(qpath, fname), "wb") as f:
                        f.write(body)
                    log_refusal(leg_id, "SCHEMA_VIOLATION",
                                f"TSLA-class/SMCI-rule volume-completeness failure: "
                                f"{info['zero_vol_range_bars']} price-moving zero-volume bars")
                    outcome = "QUARANTINED_VOLUME_COMPLETENESS"
                    state["stop"] = f"VOLUME_COMPLETENESS {leg_id}"
                    break
                # PASS: persist raw bytes now; receipt finalized at block close
                with open(os.path.join(raw_dir, fname), "wb") as f:
                    f.write(body)
                pending.append({"leg_id": leg_id, "symbol": symbol, "window": window,
                                "block_id": block_id, "block_position": pos,
                                "attempt": attempts, "params": params, "info": info,
                                "sha256": hashlib.sha256(body).hexdigest(),
                                "bytes": len(body), "credits_headers": cred_h,
                                "request_ts_utc": req_ts, "receipt_ts_utc": rec_ts,
                                "http_status": status})
                outcome = "OK"
                break
            state["legs"].append({"leg_id": leg_id, "outcome": outcome, "attempts": attempts,
                                  "block_id": block_id,
                                  **({"rows": pending[-1]["info"]["rows"],
                                      "expected_rows": expected,
                                      "row_delta": pending[-1]["info"]["rows"] - expected,
                                      "first_bar": pending[-1]["info"]["first_bar"],
                                      "last_bar": pending[-1]["info"]["last_bar"],
                                      "sha256": pending[-1]["sha256"],
                                      "anomalous_dates": pending[-1]["info"]["anomalous_dates"]}
                                     if outcome == "OK" else {})})
            print(f"LEG {leg_id}: {outcome} (calls={state['calls']})", flush=True)
            if outcome != "OK":
                block_stop = state["stop"] or outcome
                break
        # ---- block close: bracket read + reconciliation + receipt finalization ----
        if state["stop"] and state["stop"].startswith("HTTP_429"):
            state["blocks"].append({"block_id": block_id, "attempts": block_attempts,
                                    "reconciled": False, "note": "no closing read after 429 hard stop",
                                    "receipts_finalized": 0})
            break
        try:
            r_close = usage_read(surr, f"R{block_id}_close")
        except RuntimeError as e:
            state["blocks"].append({"block_id": block_id, "attempts": block_attempts,
                                    "reconciled": False,
                                    "note": f"closing read blocked: {e}",
                                    "receipts_finalized": 0})
            if not state["stop"]:
                state["stop"] = f"HARD_CAP at block {block_id} close"
            break
        u_prev = (r_prev["body"] or {}).get("daily_usage")
        u_close = (r_close["body"] or {}).get("daily_usage")
        reconciled = (u_prev is not None and u_close is not None
                      and (u_close - u_prev) == block_attempts + 1)
        n_fin = 0
        if reconciled:
            for p in pending:
                receipt = {
                    "kind": "capture_receipt",
                    "leg_id": p["leg_id"],
                    "symbol": p["symbol"],
                    "window": p["window"],
                    "manifest_root_digest_sha256": MANIFEST_ROOT,
                    "provider": {"name": "Twelve Data", "request_id": None,
                                 "response_timestamp_utc": p["receipt_ts_utc"]},
                    "request": {"endpoint_class": "/time_series", "interval": "1h",
                                "start_date": p["params"]["start_date"],
                                "end_date": p["params"]["end_date"],
                                "adjust": "splits", "outputsize": 5000,
                                "attempt": p["attempt"]},
                    "response": {"rows": p["info"]["rows"], "sha256": p["sha256"],
                                 "first_bar": p["info"]["first_bar"],
                                 "last_bar": p["info"]["last_bar"],
                                 "expected_rows": dict((l[0], l[5]) for l in LEGS)[p["leg_id"]],
                                 "row_delta": p["info"]["rows"] - dict((l[0], l[5]) for l in LEGS)[p["leg_id"]]},
                    "block": {"block_id": p["block_id"], "block_position": p["block_position"],
                              "bracket_open_read_sha256": r_prev["sha256"],
                              "bracket_close_read_sha256": r_close["sha256"]},
                    "transport": {"http_status": p["http_status"], "response_bytes": p["bytes"],
                                  "credits_headers": p["credits_headers"],
                                  "request_ts_utc": p["request_ts_utc"]},
                    "anomalous_dates": p["info"]["anomalous_dates"],
                    "chain": {"prev_receipt_hash": prev_hash},
                }
                if p["window"] == "W_HO":
                    receipt["ch1_disclosure"] = CH1_TEXT
                rh = hashlib.sha256(canonical(receipt)).hexdigest()
                receipt["chain"]["receipt_hash"] = rh
                with open(os.path.join(receipts_dir, p["leg_id"].replace("/", "__") + ".receipt.json"), "w") as f:
                    json.dump(receipt, f, indent=2, sort_keys=True)
                prev_hash = rh
                n_fin += 1
                for l in state["legs"]:
                    if l["leg_id"] == p["leg_id"]:
                        l["receipt_hash"] = rh
        state["blocks"].append({"block_id": block_id, "attempts": block_attempts,
                                "u_prev": u_prev, "u_close": u_close,
                                "expected_delta": block_attempts + 1,
                                "reconciled": reconciled, "receipts_finalized": n_fin,
                                "open_read_sha256": r_prev["sha256"],
                                "close_read_sha256": r_close["sha256"]})
        print(f"BLOCK {block_id}: attempts={block_attempts} u {u_prev}->{u_close} "
              f"reconciled={reconciled} receipts={n_fin}", flush=True)
        if not reconciled:
            state["stop"] = (state["stop"] or "") + f" | RECONCILIATION_MISMATCH block {block_id}: "
            state["stop"] = state["stop"].strip(" |")
            break
        r_prev = r_close
        leg_idx += len(block_legs)
        if block_stop:
            break
    return finish(0 if not state["stop"] else 4)

def finish(code):
    state["finished_utc"] = now_iso()
    state["total_calls"] = state["calls"]
    with open(os.path.join(WORK, "run_summary.json"), "w") as f:
        json.dump(state, f, indent=2, sort_keys=True, default=str)
    print(json.dumps({"total_calls": state["calls"], "stop": state["stop"],
                      "blocks": state["blocks"],
                      "legs_ok": sum(1 for l in state["legs"] if l["outcome"] == "OK"),
                      "legs_total_attempted": len(state["legs"])}, indent=1, default=str))
    return code

if __name__ == "__main__":
    sys.exit(main())
