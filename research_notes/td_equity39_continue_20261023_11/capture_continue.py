#!/usr/bin/env python3
"""QF-TD-EQUITY39-CONTINUE-20261023-11 (Issue #1 comment 6374566569; GO Slack TS 1792788961.983909).
Controlled continuation of the -10 capture: the 77 never-attempted legs of the parent manifest
(root ca49892062f1ac5d4ec...) under an immutable CHILD manifest (root pinned at build time),
NEW GENESIS bound to the child digest. BLOCK-BRACKET-10 accounting identical to -10/-91.
ONE acquisition-only behavior change vs -10: a leg whose ONLY failure is the price-moving
zero-volume class is quarantined byte-exact, emits NO receipt, is recorded
NOT_EVALUABLE_PROVIDER_VOLUME, and the capture CONTINUES to the next leg. Every other fatal
class from -10 still STOPs the run. HO bytes are raw qualification input only.
The transport is injectable so the offline synthetic gate exercises this exact code path.
The surrogate credential is never printed/written."""
import json, hashlib, time, sys, os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
BASE = os.environ.get("QF_TD11_BASE", "/home/hatch/workspace/qf_td11_stage")
STORE = os.path.join(BASE, "store")
WORK = os.path.join(BASE, "work")
PARENT_ROOT = "ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64"
BLOCK_SIZE = 10
PACE_S = 8.5
CH1_TEXT = ("CH-1 disclosed assumption (three-gate freeze a126ce5): the adopted 751-session "
            "calendar rests on the NYSE Group/ICE release of 2022-12-21 for the 2023 window; "
            "in-era 2023 core-hours documentation pursued in parallel, non-blocking.")

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def now_iso():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

# ---------------------------------------------------------------- validator (==-10 + census)
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
    """Wrapper validation identical to -10, extended to also return the census of
    price-moving zero-volume stamps. Returns (ok, info_or_reason, detail)."""
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
    zero_vol_stamps = []
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
            zero_vol_stamps.append(v["datetime"])
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
            "zero_vol_range_bars": len(zero_vol_stamps),
            "zero_vol_stamps": zero_vol_stamps, "anomalous_dates": bad_dates}
    return True, info, None

# ---------------------------------------------------------------- engine
class Engine:
    """BLOCK-BRACKET-10 capture engine. transport(kind, params)->(status, headers, body)
    with kind in {'usage','series'}; clock/sleep injectable for offline tests."""

    def __init__(self, manifest, store, work, transport, hard_cap=171, pace_s=0.0,
                 child_root=None, program_td_total_before=27, log=print):
        self.manifest = manifest
        self.child_root = child_root
        self.store, self.work = store, work
        self.transport = transport
        self.hard_cap = hard_cap
        self.pace_s = pace_s
        self.log = log
        self.legs_spec = [(l["leg_id"], l["symbol"], l["window"], l["start_date"], l["end_date"],
                           l["expected_rows_admitted"]) for l in manifest["legs"]]
        self.expected = {l[0]: l[5] for l in self.legs_spec}
        self.state = {"calls": 0, "started_utc": None, "last_call_start": 0.0,
                      "preflight": None, "legs": [], "refusals": [], "quarantines": [],
                      "blocks": [], "stop": None,
                      "program_td_total_before": program_td_total_before}

    # ---- low-level helpers
    def _call(self, kind, params):
        if self.state["calls"] >= self.hard_cap:
            raise RuntimeError("HARD_CAP reached before request")
        if self.pace_s:
            dt = time.time() - self.state["last_call_start"]
            if self.state["last_call_start"] and dt < self.pace_s:
                time.sleep(self.pace_s - dt)
        self.state["last_call_start"] = time.time()
        self.state["calls"] += 1
        return self.transport(kind, params)

    def _log_attempt(self, rec):
        with open(os.path.join(self.work, "attempts.jsonl"), "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    def _log_refusal(self, leg_id, reason, detail):
        rec = {"kind": "capture_refusal", "leg_id": leg_id, "reason": reason,
               "detail": detail, "ts_utc": now_iso()}
        self.state["refusals"].append(rec)
        with open(os.path.join(self.work, "refusals.jsonl"), "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")

    def usage_read(self, tag):
        req_ts = now_iso()
        status, headers, body = self._call("usage", {})
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
        os.makedirs(os.path.join(self.store, "brackets"), exist_ok=True)
        with open(os.path.join(self.store, "brackets", tag + ".body.json"), "wb") as f:
            f.write(body)
        with open(os.path.join(self.work, "brackets.jsonl"), "a") as f:
            f.write(json.dumps({k: v for k, v in rec.items() if k != "body"} |
                               {"daily_usage": (rec["body"] or {}).get("daily_usage"),
                                "plan_daily_limit": (rec["body"] or {}).get("plan_daily_limit")},
                               sort_keys=True) + "\n")
        self._log_attempt({"kind": "api_usage", "tag": tag, "http_status": status,
                           "calls": self.state["calls"],
                           "daily_usage": (rec["body"] or {}).get("daily_usage")})
        return rec

    # ---- main run
    def run(self, required_headroom=None):
        st = self.state
        st["started_utc"] = now_iso()
        raw_dir = os.path.join(self.store, "raw")
        receipts_dir = os.path.join(self.store, "receipts")
        quar_dir = os.path.join(self.store, "quarantine")
        for d in (raw_dir, receipts_dir, quar_dir):
            os.makedirs(d, exist_ok=True)
        if required_headroom is None:
            required_headroom = self.hard_cap

        # PREFLIGHT = phase-opening bracket read R0 (once, never retried)
        r_prev = self.usage_read("R0_preflight")
        pf_body = r_prev["body"]
        pf = {"request_ts_utc": r_prev["request_ts_utc"], "receipt_ts_utc": r_prev["receipt_ts_utc"],
              "http_status": r_prev["http_status"], "sha256": r_prev["sha256"],
              "bytes": r_prev["bytes"], "body": pf_body,
              "credits_headers": r_prev["credits_headers"]}
        os.makedirs(os.path.join(self.store, "preflight"), exist_ok=True)
        with open(os.path.join(self.store, "preflight", "api_usage.body.json"), "wb") as f:
            f.write(open(os.path.join(self.store, "brackets", "R0_preflight.body.json"), "rb").read())
        with open(os.path.join(self.store, "preflight", "preflight.json"), "w") as f:
            json.dump(pf, f, indent=2, sort_keys=True)
        st["preflight"] = pf
        if r_prev["http_status"] != 200 or not pf_body:
            st["stop"] = f"PREFLIGHT_FAIL http={r_prev['http_status']}"
            return self._finish(3)
        daily_limit, daily_usage = pf_body.get("plan_daily_limit"), pf_body.get("daily_usage")
        if daily_limit != 800:
            st["stop"] = (f"ABORT plan_daily_limit={daily_limit!r} != 800 "
                          f"(daily fields only; plan_limit={pf_body.get('plan_limit')!r} is per-minute)")
            return self._finish(3)
        if daily_usage is None or (800 - daily_usage) < required_headroom:
            st["stop"] = (f"ABORT insufficient headroom: daily_usage={daily_usage!r}, "
                          f"need {required_headroom} (worst case)")
            return self._finish(3)

        prev_hash = "GENESIS:" + self.child_root
        leg_idx = 0
        block_id = 0
        while leg_idx < len(self.legs_spec) and not st["stop"]:
            block_id += 1
            block_legs = self.legs_spec[leg_idx:leg_idx + BLOCK_SIZE]
            block_attempts = 0
            pending = []
            for pos, (leg_id, symbol, window, sd, ed, expected) in enumerate(block_legs, start=1):
                if st["stop"]:
                    break
                fname = leg_id.replace("/", "__") + ".json"
                params = {"symbol": symbol, "interval": "1h",
                          "start_date": sd + "T00:00:00", "end_date": ed + "T23:59:59",
                          "timezone": "America/New_York", "outputsize": "5000",
                          "order": "ASC", "adjust": "splits"}
                attempts, outcome = 0, None
                while attempts < 2:
                    attempts += 1
                    block_attempts += 1
                    if st["calls"] >= self.hard_cap:
                        st["stop"] = "HARD_CAP before " + leg_id
                        outcome = "STOP_HARDCAP"
                        break
                    req_ts = now_iso()
                    try:
                        status, headers, body = self._call("series", params)
                        transport_err = None
                    except RuntimeError as e:
                        st["stop"] = str(e) + " before " + leg_id
                        outcome = "STOP_HARDCAP"
                        break
                    except Exception as e:
                        status, headers, body, transport_err = None, {}, b"", repr(e)
                    rec_ts = now_iso()
                    cred_h = {k.lower(): v for k, v in headers.items()
                              if k.lower().startswith("api-credits")}
                    self._log_attempt({"leg_id": leg_id, "attempt": attempts, "block_id": block_id,
                                       "http_status": status, "bytes": len(body),
                                       "sha256": hashlib.sha256(body).hexdigest(),
                                       "credits_headers": cred_h, "calls": st["calls"],
                                       "request_ts_utc": req_ts, "receipt_ts_utc": rec_ts,
                                       "transport_err": transport_err})
                    if status == 429:
                        self._log_refusal(leg_id, "SCHEMA_VIOLATION",
                                          "HTTP 429 rate-limit refusal (hard stop)")
                        st["stop"] = f"HTTP_429 on {leg_id}"
                        outcome = "STOP_429"
                        break
                    if transport_err or status is None or status >= 500 or (status == 200 and not body):
                        if attempts < 2:
                            continue
                        self._log_refusal(leg_id, "SCHEMA_VIOLATION",
                                          f"transport failure x2: http={status} err={transport_err}")
                        st["stop"] = f"BRACKET_EXHAUSTED {leg_id}"
                        outcome = "BRACKET_EXHAUSTED"
                        break
                    if status != 200:
                        self._log_refusal(leg_id, "SCHEMA_VIOLATION", f"HTTP {status}: {body[:200]!r}")
                        outcome = "REFUSED_HTTP"
                        st["stop"] = f"REFUSED_HTTP {leg_id} http={status}"
                        break
                    ok, info, detail = validate_leg({"symbol": symbol}, body)
                    if not ok:
                        # any non-volume fatal class: quarantine bytes (evidence) + STOP (==-10)
                        with open(os.path.join(quar_dir, fname), "wb") as f:
                            f.write(body)
                        self._log_refusal(leg_id, info, detail)
                        outcome = "STOPPED_" + info
                        st["stop"] = f"{info} {leg_id}"
                        break
                    if info["zero_vol_range_bars"] > 0:
                        # THE ONE AMENDED CLASS (acquisition-only): quarantine + CONTINUE
                        qsha = hashlib.sha256(body).hexdigest()
                        with open(os.path.join(quar_dir, fname), "wb") as f:
                            f.write(body)
                        qrec = {"kind": "capture_quarantine", "leg_id": leg_id,
                                "symbol": symbol, "window": window,
                                "classification": "NOT_EVALUABLE_PROVIDER_VOLUME",
                                "defect_class": "PRICE_MOVING_ZERO_VOLUME",
                                "zero_vol_range_bars": info["zero_vol_range_bars"],
                                "zero_vol_stamps": info["zero_vol_stamps"],
                                "rows": info["rows"], "sha256": qsha, "bytes": len(body),
                                "attempt": attempts, "block_id": block_id,
                                "http_status": status, "request_ts_utc": req_ts,
                                "receipt_ts_utc": rec_ts,
                                "policy": "QUARANTINE-BAD-LEG-AND-CONTINUE (GO 6374566569); "
                                          "NO receipt emitted; leg NOT retried",
                                "ts_utc": now_iso()}
                        st["quarantines"].append(qrec)
                        with open(os.path.join(self.work, "quarantines.jsonl"), "a") as f:
                            f.write(json.dumps(qrec, sort_keys=True) + "\n")
                        self._log_refusal(leg_id, "QUARANTINED_VOLUME",
                                          f"{info['zero_vol_range_bars']} price-moving zero-volume "
                                          f"bars; quarantined sha256={qsha}; no receipt; continuing")
                        outcome = "QUARANTINED_VOLUME"
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
                entry = {"leg_id": leg_id, "outcome": outcome, "attempts": attempts,
                         "block_id": block_id}
                if outcome == "OK":
                    p = pending[-1]
                    entry.update({"rows": p["info"]["rows"], "expected_rows": expected,
                                  "row_delta": p["info"]["rows"] - expected,
                                  "first_bar": p["info"]["first_bar"],
                                  "last_bar": p["info"]["last_bar"], "sha256": p["sha256"],
                                  "anomalous_dates": p["info"]["anomalous_dates"]})
                elif outcome == "QUARANTINED_VOLUME":
                    q = st["quarantines"][-1]
                    entry.update({"rows": q["rows"], "expected_rows": expected,
                                  "quarantine_sha256": q["sha256"],
                                  "zero_vol_range_bars": q["zero_vol_range_bars"],
                                  "zero_vol_stamps": q["zero_vol_stamps"]})
                st["legs"].append(entry)
                self.log(f"LEG {leg_id}: {outcome} (calls={st['calls']})")
            # ---- block close: bracket read + reconciliation + receipt finalization ----
            if st["stop"] and st["stop"].startswith("HTTP_429"):
                st["blocks"].append({"block_id": block_id, "attempts": block_attempts,
                                     "reconciled": False,
                                     "note": "no closing read after 429 hard stop",
                                     "receipts_finalized": 0})
                break
            try:
                r_close = self.usage_read(f"R{block_id}_close")
            except RuntimeError as e:
                st["blocks"].append({"block_id": block_id, "attempts": block_attempts,
                                     "reconciled": False, "note": f"closing read blocked: {e}",
                                     "receipts_finalized": 0})
                if not st["stop"]:
                    st["stop"] = f"HARD_CAP at block {block_id} close"
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
                        "manifest_root_digest_sha256": self.child_root,
                        "parent_manifest_root_digest_sha256": PARENT_ROOT,
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
                                     "expected_rows": self.expected[p["leg_id"]],
                                     "row_delta": p["info"]["rows"] - self.expected[p["leg_id"]]},
                        "block": {"block_id": p["block_id"], "block_position": p["block_position"],
                                  "bracket_open_read_sha256": r_prev["sha256"],
                                  "bracket_close_read_sha256": r_close["sha256"]},
                        "transport": {"http_status": p["http_status"],
                                      "response_bytes": p["bytes"],
                                      "credits_headers": p["credits_headers"],
                                      "request_ts_utc": p["request_ts_utc"]},
                        "anomalous_dates": p["info"]["anomalous_dates"],
                        "chain": {"prev_receipt_hash": prev_hash},
                    }
                    if p["window"] == "W_HO":
                        receipt["ch1_disclosure"] = CH1_TEXT
                    rh = hashlib.sha256(canonical(receipt)).hexdigest()
                    receipt["chain"]["receipt_hash"] = rh
                    with open(os.path.join(receipts_dir,
                                           p["leg_id"].replace("/", "__") + ".receipt.json"), "w") as f:
                        json.dump(receipt, f, indent=2, sort_keys=True)
                    prev_hash = rh
                    n_fin += 1
                    for l in st["legs"]:
                        if l["leg_id"] == p["leg_id"]:
                            l["receipt_hash"] = rh
            st["blocks"].append({"block_id": block_id, "attempts": block_attempts,
                                 "u_prev": u_prev, "u_close": u_close,
                                 "expected_delta": block_attempts + 1,
                                 "reconciled": reconciled, "receipts_finalized": n_fin,
                                 "open_read_sha256": r_prev["sha256"],
                                 "close_read_sha256": r_close["sha256"]})
            self.log(f"BLOCK {block_id}: attempts={block_attempts} u {u_prev}->{u_close} "
                     f"reconciled={reconciled} receipts={n_fin}")
            if not reconciled:
                st["stop"] = ((st["stop"] or "") +
                              f" | RECONCILIATION_MISMATCH block {block_id}").strip(" |")
                break
            r_prev = r_close
            leg_idx += len(block_legs)
            if st["stop"]:
                break
        return self._finish(0 if not st["stop"] else 4)

    def _finish(self, code):
        st = self.state
        st["finished_utc"] = now_iso()
        st["total_calls"] = st["calls"]
        with open(os.path.join(self.work, "run_summary.json"), "w") as f:
            json.dump(st, f, indent=2, sort_keys=True, default=str)
        self.log(json.dumps({"total_calls": st["calls"], "stop": st["stop"],
                             "legs_ok": sum(1 for l in st["legs"] if l["outcome"] == "OK"),
                             "legs_quarantined": sum(1 for l in st["legs"]
                                                     if l["outcome"] == "QUARANTINED_VOLUME"),
                             "legs_total_attempted": len(st["legs"])}, default=str))
        return code

# ---------------------------------------------------------------- live transport
def live_main():
    import urllib.request, urllib.parse, urllib.error
    sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
    from dynamic_credentials import dynamic_credential_entry, DynamicCredentialError
    API = "https://api.twelvedata.com"
    try:
        surr = str(dynamic_credential_entry("custom.twelvedata")["surrogate"]).strip()
    except DynamicCredentialError as e:
        print(json.dumps({"fatal": f"credential unavailable: {e}"}))
        return 2
    if not surr.startswith("hsurr:"):
        print(json.dumps({"fatal": "credential is not a surrogate; refusing"}))
        return 2

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

    with open(os.path.join(STORE, "child_manifest.json")) as f:
        manifest = json.load(f)
    m = dict(manifest)
    stated_root = m.pop("root_digest_sha256"); m.pop("root_digest_construction")
    child_root = hashlib.sha256(canonical(m)).hexdigest()
    assert child_root == stated_root, "child manifest root mismatch - refusing to run"
    assert manifest["parent"]["root_digest_sha256"] == PARENT_ROOT
    assert len(manifest["legs"]) == 77
    eng = Engine(manifest, STORE, WORK, transport, hard_cap=171, pace_s=PACE_S,
                 child_root=child_root, program_td_total_before=27)
    return eng.run()

if __name__ == "__main__":
    sys.exit(live_main())
