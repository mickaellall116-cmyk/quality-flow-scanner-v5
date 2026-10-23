#!/usr/bin/env python3
"""QF-TD-BTC-SYMBOL-FIX-20261023-04 — bounded corrective BTC-only execution.

Amends ONLY the transport symbol form vs Card A (-03): the provider request
carries BTC/USD; the universe/manifest identity stays BTC-USD (explicit
one-to-one alias pinned in the amended manifest, root
23042e30ddfd3a5a233e832a011de3cdfc2b9e28f78542e6b547258fe9bccb52).
Six chunks identical to Card A: /time_series 1h, adjust=splits,
outputsize=5000, order ASC, timezone America/New_York.

BLOCK-BRACKET-10: unit cost 1 credit/call; blocks of <=10 attempts; one
/api_usage read opens a phase, one closes every block; <=2 attempts per leg.
Budget: 8 expected, 15 HARD MAX incremental request-counted credits
including preflight/retries/closing reads. $0 free tier. The surrogate
credential is never printed or written."""
import json, hashlib, time, sys, os, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import dynamic_credential_entry, DynamicCredentialError

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
BASE = "/home/hatch/workspace/qf_td_btc_fix_20261023"
STORE = os.path.join(BASE, "store")
WORK = os.path.join(BASE, "work")
MANIFEST_ROOT = "23042e30ddfd3a5a233e832a011de3cdfc2b9e28f78542e6b547258fe9bccb52"
PARENT_MANIFEST_ROOT = "79ccdd128e0b36537f56f8ae36a731b719e989b9756f65856b7dc47344327122"
HARD_CAP = 15
MAX_ATTEMPTS_PER_CHUNK = 2
BLOCK_MAX_ATTEMPTS = 10
PACE_S = 8.5
API = "https://api.twelvedata.com"

INTERNAL_SYMBOL = "BTC-USD"   # frozen UX51 universe token - never sent to the provider
REQUEST_SYMBOL = "BTC/USD"    # Twelve Data transport form - the ONLY symbol ever requested
SYMBOL_MAP = {INTERNAL_SYMBOL: REQUEST_SYMBOL}

# leg_id, internal_symbol, window, start_date, end_date, expected_rows (identical to Card A)
LEGS = [
    ("BTC-USD/HO-C1",  "BTC-USD", "W_HO",  "2023-10-19", "2024-05-13", 4992),
    ("BTC-USD/HO-C2",  "BTC-USD", "W_HO",  "2024-05-14", "2024-09-15", 3000),
    ("BTC-USD/DEV-C1", "BTC-USD", "W_DEV", "2024-09-16", "2025-04-11", 4992),
    ("BTC-USD/DEV-C2", "BTC-USD", "W_DEV", "2025-04-12", "2025-11-05", 4993),
    ("BTC-USD/DEV-C3", "BTC-USD", "W_DEV", "2025-11-06", "2026-06-01", 4991),
    ("BTC-USD/DEV-C4", "BTC-USD", "W_DEV", "2026-06-02", "2026-10-16", 3288),
]

def request_symbol_for(internal_symbol):
    """Explicit alias resolution. Raises for any unmapped symbol."""
    if internal_symbol not in SYMBOL_MAP:
        raise ValueError(f"no provider alias pinned for {internal_symbol!r}")
    return SYMBOL_MAP[internal_symbol]

def build_params(leg):
    leg_id, internal_symbol, window, sd, ed, expected = leg
    return {"symbol": request_symbol_for(internal_symbol), "interval": "1h",
            "start_date": sd + "T00:00:00", "end_date": ed + "T23:59:59",
            "timezone": "America/New_York", "outputsize": "5000",
            "order": "ASC", "adjust": "splits"}

def assert_request_form(params):
    """Fail-closed guard: the request symbol must be the pinned provider form.
    The internal universe token (BTC-USD) as a request form is rejected."""
    sym = params.get("symbol")
    if sym == INTERNAL_SYMBOL:
        raise ValueError("internal universe token must never be used as request form")
    if sym != REQUEST_SYMBOL:
        raise ValueError(f"request symbol {sym!r} != pinned provider form {REQUEST_SYMBOL!r}")

state = {
    "calls": 0, "started_utc": None, "last_call_start": 0.0,
    "reads": [], "legs": [], "refusals": [], "stop": None,
}

def now_iso():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def pace():
    dt = time.time() - state["last_call_start"]
    if state["last_call_start"] and dt < PACE_S:
        time.sleep(PACE_S - dt)

def gate_call(kind):
    if state["calls"] >= HARD_CAP:
        raise RuntimeError(f"HARD_CAP reached before {kind}")

def api_get(url):
    gate_call("request")
    pace()
    state["last_call_start"] = time.time()
    state["calls"] += 1
    req = urllib.request.Request(url, headers={"User-Agent": "qf-td-btc-symbolfix/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
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

def get_surrogate():
    entry = dynamic_credential_entry("custom.twelvedata")
    return str(entry["surrogate"]).strip()

def read_usage(surr, label):
    url = API + "/api_usage?" + urllib.parse.urlencode({"apikey": surr})
    req_ts = now_iso()
    try:
        status, headers, body = api_get(url)
    except Exception as e:
        log_attempt({"kind": "usage_read", "label": label, "error": repr(e)})
        return None
    rec = {"kind": "usage_read", "label": label, "http_status": status,
           "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
           "calls": state["calls"], "request_ts_utc": req_ts,
           "receipt_ts_utc": now_iso()}
    log_attempt(rec)
    state["reads"].append(rec)
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return None

def wall_to_instants(stamps):
    """Resolve ET wall stamps to UTC instants in order (fold-aware)."""
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

def validate_chunk(leg_id, body, expected):
    """Wrapper validation for a BTC chunk. Returns (ok, info_or_reason, detail, doc)."""
    try:
        doc = json.loads(body.decode("utf-8"))
    except Exception as e:
        return False, "SCHEMA_VIOLATION", f"unparseable JSON: {e}", None
    if doc.get("status") != "ok":
        return False, "SCHEMA_VIOLATION", f"status={doc.get('status')!r} code={doc.get('code')!r} msg={doc.get('message')!r}", None
    meta = doc.get("meta", {})
    # meta.symbol must equal the PROVIDER request form (BTC/USD), not the internal token
    if meta.get("symbol") != REQUEST_SYMBOL or meta.get("interval") != "1h":
        return False, "SCHEMA_VIOLATION", f"meta mismatch: {meta.get('symbol')!r}/{meta.get('interval')!r}", None
    vals = doc.get("values")
    if not isinstance(vals, list) or not vals:
        return False, "SCHEMA_VIOLATION", "values missing/empty", None
    rows = len(vals)
    if rows == 5000:
        return False, "TRUNCATION_SUSPECT", "exactly 5000 rows", doc
    if rows != expected:
        return False, "ROW_COUNT_MISMATCH", f"rows={rows} expected={expected}", doc
    stamps = []
    zero_vol_range = 0
    for v in vals:
        # volume policy: missing/null volume is a SCHEMA/COVERAGE hold, never zero
        if "volume" not in v or v["volume"] is None:
            return False, "SCHEMA_COVERAGE_HOLD", f"volume missing/null in row {v!r}", None
        try:
            o, h, lo, c = (float(v["open"]), float(v["high"]), float(v["low"]), float(v["close"]))
            vol = float(v["volume"])
        except Exception:
            return False, "SCHEMA_VIOLATION", f"non-numeric field in row {v!r}", None
        for x in (o, h, lo, c, vol):
            if x != x or x in (float("inf"), float("-inf")):
                return False, "NONFINITE_VALUE", f"non-finite in row {v!r}", None
        if vol < 0:
            return False, "SCHEMA_VIOLATION", f"negative volume in row {v!r}", None
        if vol == 0 and h > lo:
            zero_vol_range += 1
        stamps.append(v["datetime"])
    try:
        instants = wall_to_instants(stamps)
    except ValueError as e:
        msg = str(e)
        reason = "DUPLICATE_INSTANT" if msg.startswith("DUPLICATE") else "SCHEMA_VIOLATION"
        return False, reason, msg, None
    minutes = {s[14:16] for s in stamps}
    if minutes != {"30"}:
        return False, "OFF_GRID_STAMPS", f"stamp minutes {sorted(minutes)} != ['30'] (S-C grid phase)", doc
    for a, b in zip(instants, instants[1:]):
        if b - a != 3600:
            return False, "GAP_VIOLATION", f"crypto gap {int(b-a)}s within chunk", None
    info = {"rows": rows, "first_bar": stamps[0], "last_bar": stamps[-1],
            "zero_vol_range_bars": zero_vol_range,
            "instants": instants, "stamps": stamps, "stamp_minutes": sorted(minutes)}
    return True, info, None, doc

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

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
    os.makedirs(os.path.join(STORE, "preflight"), exist_ok=True)
    os.makedirs(os.path.join(WORK, "quarantine"), exist_ok=True)

    # ---- OPENING /api_usage READ (preflight; counts) ----
    usage_open = read_usage(surr, "open_preflight")
    if usage_open is None:
        state["stop"] = "PREFLIGHT_FAIL (no usable usage read)"
        print(json.dumps(state, indent=1, default=str))
        return 3
    daily_limit, daily_usage = usage_open.get("plan_daily_limit"), usage_open.get("daily_usage")
    with open(os.path.join(STORE, "preflight", "preflight.json"), "w") as f:
        json.dump({"request_ts_utc": state["reads"][-1]["request_ts_utc"],
                   "daily_usage": daily_usage, "plan_daily_limit": daily_limit,
                   "plan_limit_per_minute": usage_open.get("plan_limit")}, f, indent=2, sort_keys=True)
    log_attempt({"kind": "preflight_decision", "daily_limit": daily_limit,
                 "daily_usage": daily_usage, "calls": state["calls"]})
    if daily_limit != 800:
        state["stop"] = f"ABORT plan_daily_limit={daily_limit!r} != 800 (daily fields only)"
        print(json.dumps(state, indent=1, default=str))
        return 3
    if daily_usage is None or (800 - daily_usage) < HARD_CAP:
        state["stop"] = f"ABORT insufficient remaining quota: daily_usage={daily_usage!r}"
        print(json.dumps(state, indent=1, default=str))
        return 3

    usage_snapshot = {"daily_usage": daily_usage, "plan_daily_limit": daily_limit}
    prev_hash = "GENESIS:" + MANIFEST_ROOT
    receipts_dir = os.path.join(STORE, "receipts")
    raw_dir = os.path.join(STORE, "raw")
    os.makedirs(receipts_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)
    block_attempts = 0
    block_index = 1

    for leg in LEGS:
        if state["stop"]:
            break
        leg_id, internal_symbol, window, sd, ed, expected = leg
        fname = leg_id.replace("/", "__") + ".json"
        params = build_params(leg)
        assert_request_form(params)  # fail-closed: pinned provider form only
        attempts, outcome = 0, None
        while attempts < MAX_ATTEMPTS_PER_CHUNK:
            if state["stop"]:
                break
            if block_attempts >= BLOCK_MAX_ATTEMPTS:
                snap = read_usage(surr, f"close_block_{block_index}")
                usage_snapshot = {"daily_usage": snap.get("daily_usage") if snap else None,
                                  "plan_daily_limit": snap.get("plan_daily_limit") if snap else None}
                block_attempts = 0
                block_index += 1
            try:
                attempts += 1
                block_attempts += 1
                url = API + "/time_series?" + urllib.parse.urlencode({**params, "apikey": surr})
                req_ts = now_iso()
                status, headers, body = api_get(url)
                transport_err = None
            except RuntimeError as e:
                attempts -= 1
                block_attempts -= 1
                state["stop"] = str(e)
                outcome = "HARD_CAP_REFUSED"
                break
            except Exception as e:
                status, headers, body, transport_err = None, {}, b"", repr(e)
            rec_ts = now_iso()
            cred_h = {k.lower(): v for k, v in headers.items() if k.lower().startswith("api-credits")}
            log_attempt({"leg_id": leg_id, "attempt": attempts, "http_status": status,
                         "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                         "credits_headers": cred_h, "calls": state["calls"],
                         "request_ts_utc": req_ts, "receipt_ts_utc": rec_ts,
                         "transport_err": transport_err})
            if status == 429:
                log_refusal(leg_id, "RATE_LIMIT_429", "HTTP 429: hard stop for this task")
                state["stop"] = f"HTTP_429 on {leg_id}"
                outcome = "STOP_429"
                break
            if transport_err or status is None or status >= 500 or (status == 200 and not body):
                if attempts < MAX_ATTEMPTS_PER_CHUNK:
                    continue
                log_refusal(leg_id, "SCHEMA_VIOLATION", f"transport failure x2: http={status} err={transport_err}")
                state["stop"] = f"BRACKET_EXHAUSTED {leg_id}"
                outcome = "BRACKET_EXHAUSTED"
                break
            if status != 200:
                log_refusal(leg_id, "SCHEMA_VIOLATION", f"HTTP {status}: {body[:200]!r}")
                state["stop"] = f"REFUSED_HTTP {leg_id} http={status}"
                outcome = "REFUSED_HTTP"
                break
            ok, info, detail, doc = validate_chunk(leg_id, body, expected)
            if not ok:
                reason = info
                with open(os.path.join(WORK, "quarantine", fname), "wb") as f:
                    f.write(body)
                log_refusal(leg_id, reason, detail)
                outcome = "QUARANTINED_" + reason
                state["stop"] = f"{reason} {leg_id}"
                break
            if info["zero_vol_range_bars"] > 0:
                with open(os.path.join(WORK, "quarantine", fname), "wb") as f:
                    f.write(body)
                log_refusal(leg_id, "SCHEMA_VIOLATION",
                            f"SMCI-class volume-completeness: {info['zero_vol_range_bars']} zero-volume bars with nonzero range")
                outcome = "QUARANTINED_VOLUME_COMPLETENESS"
                state["stop"] = f"VOLUME_COMPLETENESS {leg_id}"
                break
            with open(os.path.join(raw_dir, fname), "wb") as f:
                f.write(body)
            body_sha = hashlib.sha256(body).hexdigest()
            receipt = {
                "kind": "capture_receipt",
                "leg_id": leg_id,
                "internal_symbol": internal_symbol,
                "request_symbol": params["symbol"],
                "symbol_map": {"internal_symbol": internal_symbol, "provider": "Twelve Data",
                               "request_symbol": params["symbol"]},
                "window": window,
                "manifest_root_digest_sha256": MANIFEST_ROOT,
                "parent_manifest_root_digest_sha256": PARENT_MANIFEST_ROOT,
                "provider": {"name": "Twelve Data", "request_id": None,
                             "response_timestamp_utc": rec_ts},
                "request": {"endpoint_class": "/time_series", "interval": "1h",
                            "start_date": params["start_date"], "end_date": params["end_date"],
                            "adjust": "splits", "outputsize": 5000, "attempt": attempts},
                "response": {"rows": info["rows"], "sha256": body_sha,
                             "first_bar": info["first_bar"], "last_bar": info["last_bar"],
                             "expected_rows": expected,
                             "row_delta": info["rows"] - expected},
                "credits": {"api_usage_before": usage_snapshot, "leg_credits": attempts,
                            "calls_cumulative": state["calls"], "hard_cap": HARD_CAP},
                "transport": {"http_status": status, "response_bytes": len(body),
                              "credits_headers": cred_h, "request_ts_utc": req_ts},
                "chain": {"prev_receipt_hash": prev_hash},
                "crypto_stamp_minutes": info.get("stamp_minutes"),
            }
            rh = hashlib.sha256(canonical(receipt)).hexdigest()
            receipt["chain"]["receipt_hash"] = rh
            with open(os.path.join(receipts_dir, leg_id.replace("/", "__") + ".receipt.json"), "w") as f:
                json.dump(receipt, f, indent=2, sort_keys=True)
            prev_hash = rh
            outcome = "OK"
            state["legs"].append({"leg_id": leg_id, "outcome": outcome, "attempts": attempts,
                                  "rows": info["rows"], "expected_rows": expected,
                                  "first_bar": info["first_bar"], "last_bar": info["last_bar"],
                                  "sha256": body_sha, "receipt_hash": rh,
                                  "stamp_minutes": info.get("stamp_minutes")})
            break
        if outcome and not outcome.startswith("OK"):
            state["legs"].append({"leg_id": leg_id, "outcome": outcome, "attempts": attempts})
        print(f"LEG {leg_id}: {outcome} (calls={state['calls']})", flush=True)

    # ---- CLOSING /api_usage READ (closes the open block; counts) ----
    if state["calls"] < HARD_CAP:
        snap = read_usage(surr, "close_final")
        state["post_daily_usage"] = snap.get("daily_usage") if snap else None
        state["post_plan_daily_limit"] = snap.get("plan_daily_limit") if snap else None
    else:
        state["post_daily_usage"] = None
        log_attempt({"kind": "usage_read", "label": "close_final_skipped_hard_cap"})

    state["finished_utc"] = now_iso()
    state["total_calls"] = state["calls"]
    state["counters"] = {
        "request_counted_credits_this_task": state["calls"],
        "provider_daily_usage_before": daily_usage,
        "provider_daily_usage_after": state.get("post_daily_usage"),
        "note": "the two counters are preserved distinctly; they are not asserted identical",
    }
    with open(os.path.join(WORK, "run_summary.json"), "w") as f:
        json.dump(state, f, indent=2, sort_keys=True, default=str)
    print(json.dumps({"total_calls": state["calls"], "stop": state["stop"],
                      "legs": [(l["leg_id"], l["outcome"]) for l in state["legs"]]}, indent=1))
    return 0 if not state["stop"] else 4

if __name__ == "__main__":
    sys.exit(main())
