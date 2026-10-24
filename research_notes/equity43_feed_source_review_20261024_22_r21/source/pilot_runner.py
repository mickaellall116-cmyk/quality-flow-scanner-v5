#!/usr/bin/env python3
"""QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22 — Twelve Data prospective
1h feed measurement pilot (Gate B Phase B1 capture daemon).

Governing design: QF-EQUITY43-FEED-QUALIFICATION-FRAME-20261024-21
MEASUREMENT_PROTOCOL.md (package c2b58d7). Authority: Mike GO, main chat
2026-10-24 10:36 ET. This daemon ONLY measures: poll ladder +60/+180/+420s
(stop at first sighting), finalization +1800s, next-session 08:00 ET
revision re-poll, /api_usage snapshots at session start/midday/end.
Append-only capture journal + byte-exact payloads go to the PRIVATE
qf-data-archive clone inside this staging namespace. No production import
path, no orders, no performance computation. The surrogate credential is
never printed or written.

Modes:
  run        live daemon (schedule from run_manifest.json)
  --selftest offline stub-transport exercise of the full state machine
  --status   print state summary
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
BASE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(BASE, "state")
STATE_PATH = os.path.join(STATE_DIR, "pilot_state.json")
HEARTBEAT_PATH = os.path.join(STATE_DIR, "heartbeat.json")
STOP_PATH = os.path.join(STATE_DIR, "STOP")
CLEAR_PATH = os.path.join(STATE_DIR, "tripwire_clear.json")
REVIEW_HOLD_PATH = os.path.join(STATE_DIR, "REVIEW_HOLD")
TRIPWIRE_DIR = os.path.join(BASE, "work", "tripwire")
GMAIL_CLI = "/opt/hatch/bin/hatch_gws_cli"
# TD rights inquiry sent 2026-10-24T14:32Z; only TD mail after this counts.
TRIPWIRE_CUTOFF = datetime(2026, 10, 24, 14, 32, tzinfo=timezone.utc)
ARCHIVE_NS = os.path.join(BASE, "archive_clone", "captures",
                          "td_feed_measure_pilot_20261026")
JOURNAL_PATH = os.path.join(ARCHIVE_NS, "journal.jsonl")
API = "https://api.twelvedata.com"
BAR_STARTS = ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]
LADDER = [60, 180, 420]
FINALIZATION = 1800
PACE_S = 1.2          # between calls inside one burst (Basic tier 8/min)
LATE_WINDOW_S = 900   # ladder/finalization actions older than this are MISSED
DAY_CALL_CAP = 149
TOTAL_CALL_CAP = 800
TD_KINDS = ("usage", "ladder", "finalization", "revision")


def parse_usage_body(body):
    """Strict parse of the recorded Twelve Data /api_usage schema
    (grounded in the -11 bracket receipts, 2026-10-23):
    {"timestamp": "YYYY-MM-DD HH:MM:SS" (UTC), "current_usage": int,
     "plan_limit": int, "daily_usage": int, "plan_daily_limit": int,
     "plan_category": str}. Raises ValueError on any deviation —
    callers fail closed (STOP 2, comment 6386192978)."""
    data = json.loads(body.decode())
    if not isinstance(data, dict):
        raise ValueError("usage_not_object")
    for k in ("daily_usage", "plan_daily_limit"):
        if not isinstance(data.get(k), int) \
                or isinstance(data.get(k), bool):
            raise ValueError(f"usage_field_invalid:{k}")
    ts_raw = data.get("timestamp")
    if not isinstance(ts_raw, str):
        raise ValueError("usage_timestamp_missing")
    try:
        ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc)
    except ValueError:
        raise ValueError("usage_timestamp_unparseable")
    return {"daily_usage": data["daily_usage"],
            "plan_daily_limit": data["plan_daily_limit"],
            "plan_category": data.get("plan_category"),
            "provider_ts": ts}


def iso(dt):
    return dt.astimezone(UTC).isoformat()


def now_utc():
    return datetime.now(UTC)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


# ---------------------------------------------------------------- transport
def live_transport(kind, params):
    sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
    from dynamic_credentials import dynamic_credential_entry
    surr = str(dynamic_credential_entry("custom.twelvedata")["surrogate"]).strip()
    if not surr.startswith("hsurr:"):
        raise RuntimeError("credential is not a surrogate; refusing")
    if kind == "usage":
        url = API + "/api_usage?" + urllib.parse.urlencode({"apikey": surr})
    else:
        url = API + "/time_series?" + urllib.parse.urlencode(
            {**params, "apikey": surr})
    req = urllib.request.Request(
        url, headers={"User-Agent": "qf-feed-measure-pilot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# ---------------------------------------------------------------- state
def load_state():
    with open(STATE_PATH) as f:
        return json.load(f)


def save_state(st):
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)
    os.replace(tmp, STATE_PATH)


def journal_append(rec):
    prev = ""
    if os.path.exists(JOURNAL_PATH):
        with open(JOURNAL_PATH, "rb") as f:
            data = f.read()
        if data:
            prev = sha256_bytes(data.rstrip(b"\n").split(b"\n")[-1])
    rec["prev_line_sha256"] = prev
    line = json.dumps(rec, sort_keys=True)
    with open(JOURNAL_PATH, "a") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())
    return sha256_bytes(line.encode())


def _gmail_json(args, timeout=120):
    import subprocess
    out = subprocess.run([GMAIL_CLI, "gmail", *args],
                         capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise RuntimeError(f"gmail cli rc={out.returncode}: "
                           f"{out.stderr[-300:]} {out.stdout[-300:]}")
    return json.loads(out.stdout)


def _msg_datetime(item):
    """Best-effort message instant from a +triage item; None if unknown."""
    for key in ("internalDate", "internal_date", "timestamp"):
        v = item.get(key)
        if v is not None:
            try:
                return datetime.fromtimestamp(int(v) / 1000.0,
                                              tz=timezone.utc)
            except (TypeError, ValueError):
                pass
    for key in ("date", "message_sent_at", "received"):
        v = item.get(key)
        if isinstance(v, dict):
            v = v.get("utc") or v.get("iso") or v.get("user_local")
        if isinstance(v, str) and v:
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    from email.utils import parsedate_to_datetime
                    return parsedate_to_datetime(v)
                except (TypeError, ValueError):
                    pass
    return None


def session_close_dt(manifest, date_str):
    """Session close from the pinned manifest session_closes (fail-closed
    if absent — the closes are cross-checked against the bundle calendar
    by the preflight verifier)."""
    closes = manifest.get("session_closes") or {}
    if date_str not in closes:
        raise KeyError(f"session_closes missing {date_str}")
    hh, mm = map(int, closes[date_str].split(":"))
    return datetime.fromisoformat(date_str).replace(
        tzinfo=ET, hour=hh, minute=mm)


def bar_close_dt(manifest, date_str, start_dt):
    """A 1h bar closes at start+1h, except the final bar of the session,
    which closes AT the session close (15:30 bar -> 16:00 ET on a regular
    day, NOT 16:30 — STOP 1, comment 6386192978)."""
    return min(start_dt + timedelta(hours=1),
               session_close_dt(manifest, date_str))


def gmail_tripwire_search():
    """TD-sender mail after the inquiry cutoff. Injectable for tests.
    Returns a list of {id, from, subject, date_utc} for NEW candidate
    messages. Unknown-date messages are included (fail-closed)."""
    import subprocess
    out = subprocess.run([GMAIL_CLI, "gmail", "+triage", "--query",
                          "from:twelvedata.com after:2026/10/24",
                          "--max", "20", "--format", "json"],
                         capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"gmail triage rc={out.returncode}: "
                           f"{out.stderr[-300:]} {out.stdout[-300:]}")
    # the CLI prints "No messages found..." to stderr and nothing to stdout
    if "No messages found" in (out.stdout + out.stderr) \
            or not out.stdout.strip():
        return []
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"gmail triage unparseable output: {e}")
    items = data
    if isinstance(data, dict):
        for key in ("messages", "results", "items", "mail"):
            if isinstance(data.get(key), list):
                items = data[key]
                break
        else:
            items = [data] if data else []
    found = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        sender = str(it.get("from") or it.get("sender") or "")
        if "twelvedata.com" not in sender.lower():
            continue
        mid = it.get("id") or it.get("message_id") or it.get("messageId")
        if not mid:
            continue
        dt = _msg_datetime(it)
        if dt is not None and dt <= TRIPWIRE_CUTOFF:
            continue  # predates the inquiry — not a reply candidate
        found.append({"id": str(mid), "from": sender,
                      "subject": str(it.get("subject") or ""),
                      "date_utc": iso(dt) if dt else None})
    return found


def gmail_read_message(mid):
    """Full message via +read; returns the raw CLI JSON dict."""
    return _gmail_json(["+read", "--id", mid, "--format", "json"],
                       timeout=180)


def build_schedule(manifest):
    """Deterministic action list from the manifest pins."""
    sessions = manifest["sessions"]
    symbols = manifest["symbols"]
    actions = []
    table_sessions = sessions + ["2026-11-02"]  # revision day for last session
    for i, d in enumerate(sessions):
        day = datetime.fromisoformat(d).replace(tzinfo=ET)
        actions.append({
            "id": f"tripwire|{d}", "kind": "tripwire", "session": d,
            "due": iso(day.replace(hour=9, minute=15)), "status": "pending"})
        for tag, hhmm in (("start", "09:25"), ("midday", "13:00"),
                          ("end", "16:35")):
            hh, mm = map(int, hhmm.split(":"))
            actions.append({
                "id": f"usage|{d}|{tag}", "kind": "usage", "session": d,
                "due": iso(day.replace(hour=hh, minute=mm)),
                "tag": tag, "status": "pending"})
        for sym in symbols:
            for bs in BAR_STARTS:
                hh, mm = map(int, bs.split(":"))
                start = day.replace(hour=hh, minute=mm)
                close = bar_close_dt(manifest, d, start)
                key = f"{d}|{sym}|{bs}"
                for off in LADDER:
                    actions.append({
                        "id": f"ladder|{key}|{off}", "kind": "ladder",
                        "session": d, "symbol": sym, "bar_key": key,
                        "due": iso(close + timedelta(seconds=off)),
                        "offset_s": off, "status": "pending"})
                actions.append({
                    "id": f"fin|{key}", "kind": "finalization",
                    "session": d, "symbol": sym, "bar_key": key,
                    "due": iso(close + timedelta(seconds=FINALIZATION)),
                    "offset_s": FINALIZATION, "status": "pending"})
        nxt = table_sessions[i + 1]
        nday = datetime.fromisoformat(nxt).replace(tzinfo=ET)
        # r2.1 (ruling 6387146941, residual 1): a same-day /api_usage
        # baseline must exist BEFORE the 08:00 revision batch — the
        # pre_revision usage action at 07:55 ET supplies it, and
        # provider_precheck no longer exempts revision traffic.
        actions.append({
            "id": f"usage|{nxt}|pre_revision", "kind": "usage",
            "session": nxt,
            "due": iso(nday.replace(hour=7, minute=55)),
            "tag": "pre_revision", "status": "pending"})
        for sym in symbols:
            actions.append({
                "id": f"rev|{d}|{sym}", "kind": "revision", "session": d,
                "symbol": sym, "due": iso(nday.replace(hour=8, minute=0)),
                "status": "pending"})
    actions.append({
        "id": "usage|2026-11-02|pilot_close", "kind": "usage",
        "session": "2026-11-02",
        "due": iso(datetime(2026, 11, 2, 8, 5, tzinfo=ET)),
        "tag": "pilot_close", "status": "pending"})
    for d in sessions:
        day = datetime.fromisoformat(d).replace(tzinfo=ET)
        actions.append({
            "id": f"push|{d}", "kind": "archive_push", "session": d,
            "due": iso(day.replace(hour=16, minute=40)), "status": "pending"})
    actions.append({
        "id": "push|final", "kind": "archive_push", "session": "2026-11-02",
        "due": iso(datetime(2026, 11, 2, 8, 10, tzinfo=ET)),
        "status": "pending"})
    actions.sort(key=lambda a: a["due"])
    return actions


def init_state(manifest):
    bars = {}
    for d in manifest["sessions"]:
        for sym in manifest["symbols"]:
            for bs in BAR_STARTS:
                key = f"{d}|{sym}|{bs}"
                hh, mm = map(int, bs.split(":"))
                start = datetime.fromisoformat(d).replace(
                    tzinfo=ET, hour=hh, minute=mm)
                bars[key] = {
                    "session": d, "symbol": sym, "bar_start_et": bs,
                    "close_utc": iso(bar_close_dt(manifest, d, start)),
                    "first_seen": None, "sightings": 0,
                    "partial_sightings": 0, "last_values": None,
                    "last_hash": None, "revisions": [],
                    "finalized": False, "missing_at_finalization": False}
    return {
        "task": manifest["task"], "manifest_task": manifest["task"],
        "actions": build_schedule(manifest), "bars": bars,
        "desk_calls": 0, "desk_calls_by_day": {}, "usage_snapshots": [],
        "desk_nonusage_calls": 0,
        "usage_guard": {"baseline": None, "last": None,
                        "desk_calls_at_last": 0, "nonusage_at_last": 0,
                        "external_events": []},
        "consecutive_429": 0, "stopped": None, "journal_seq": 0,
        "tripwire": {"checks": [], "hold": False, "hold_info": None,
                     "filed": [], "pending_review": []},
        "sessions_status": {d: "pending" for d in manifest["sessions"]}}


# ---------------------------------------------------------------- engine
class Pilot:
    def __init__(self, manifest, transport, state=None):
        self.manifest = manifest
        self.transport = transport
        self.st = state if state is not None else init_state(manifest)
        self.st.setdefault("desk_nonusage_calls", 0)
        self.st.setdefault("usage_guard", {
            "baseline": None, "last": None, "desk_calls_at_last": 0,
            "nonusage_at_last": 0, "external_events": []})

    # -- accounting ------------------------------------------------------
    def _count_call(self, when, kind=None):
        day = when.astimezone(ET).date().isoformat()
        self.st["desk_calls"] += 1
        if kind != "usage":
            self.st["desk_nonusage_calls"] = \
                self.st.get("desk_nonusage_calls", 0) + 1
        self.st["desk_calls_by_day"][day] = \
            self.st["desk_calls_by_day"].get(day, 0) + 1

    def cap_check(self, action, now=None):
        """Local caps (STOP 2): 800 pilot total + 149 per EXECUTION day,
        covering usage and revision traffic too."""
        if self.st["desk_calls"] >= TOTAL_CALL_CAP:
            return "total_call_cap_800_reached"
        if action["kind"] in TD_KINDS:
            now = now or now_utc()
            day = now.astimezone(ET).date().isoformat()
            if self.st["desk_calls_by_day"].get(day, 0) >= DAY_CALL_CAP:
                return f"day_call_cap_149_reached:{day}"
        return None

    # -- provider usage guard (STOP 2) ------------------------------------
    def _remaining_td_today(self, now):
        today = now.astimezone(ET).date().isoformat()
        n = 0
        for a in self.st["actions"]:
            if a["status"] == "pending" and a["kind"] in TD_KINDS:
                due_day = datetime.fromisoformat(a["due"]).astimezone(
                    ET).date().isoformat()
                if due_day == today:
                    n += 1
        return n

    def usage_guard_on_reading(self, action, status, body, receipt_dt):
        """Evaluate one /api_usage response. Returns a STOP reason or
        None. Fail-closed on non-200, malformed, stale, plan-mismatched
        or ambiguous provider data, and on exhausted headroom."""
        g = self.st["usage_guard"]
        if status != 200:
            return f"usage_http_{status}"
        try:
            u = parse_usage_body(body)
        except Exception as e:  # noqa: BLE001
            return f"usage_data_malformed:{e}"
        if u["plan_daily_limit"] != 800:
            return f"usage_plan_daily_limit_mismatch:{u['plan_daily_limit']}"
        skew = abs((receipt_dt - u["provider_ts"]).total_seconds())
        if skew > 600:
            return f"usage_data_stale_timestamp:skew_{int(skew)}s"
        reading = {"daily_usage": u["daily_usage"],
                   "plan_daily_limit": u["plan_daily_limit"],
                   "plan_category": u["plan_category"],
                   "provider_ts": iso(u["provider_ts"]),
                   "receipt_utc": iso(receipt_dt),
                   "et_date": receipt_dt.astimezone(ET).date().isoformat(),
                   "tag": action.get("tag")}
        prev = g["last"]
        if prev is not None:
            desk_delta = self.st["desk_calls"] - g["desk_calls_at_last"]
            nonusage_delta = self.st["desk_nonusage_calls"] \
                - g["nonusage_at_last"]
            prov_delta = u["daily_usage"] - prev["daily_usage"]
            if prev["et_date"] == reading["et_date"]:
                if prov_delta == 0 and nonusage_delta >= 3:
                    return "usage_data_stale_counter"
                excess = prov_delta - desk_delta
                if excess < -2:
                    return f"usage_reconciliation_ambiguous:undercount_" \
                           f"{excess}"
                if excess > 2:
                    g["external_events"].append({
                        "at_utc": iso(receipt_dt),
                        "provider_delta": prov_delta,
                        "desk_delta": desk_delta, "excess": excess})
        remaining = self._remaining_td_today(receipt_dt)
        headroom = u["plan_daily_limit"] - u["daily_usage"]
        if headroom < remaining:
            return f"provider_headroom_exhausted:headroom_{headroom}" \
                   f"_remaining_{remaining}"
        if g["baseline"] is None:
            g["baseline"] = reading
        g["last"] = reading
        g["desk_calls_at_last"] = self.st["desk_calls"]
        g["nonusage_at_last"] = self.st["desk_nonusage_calls"]
        return None

    def provider_precheck(self, action, now):
        """Provider-observed headroom BEFORE each non-usage call, with
        worst-case allowance for the rest of the execution day. EVERY
        non-usage kind — revision traffic included — requires a fresh
        same-day baseline: on revision days the 07:55 pre_revision
        usage action supplies it before the 08:00 batch (r2.1, ruling
        6387146941 residual 1; the r2 revision exemption is removed)."""
        if action["kind"] == "usage":
            return None
        g = self.st.get("usage_guard") or {}
        last = g.get("last")
        today = now.astimezone(ET).date().isoformat()
        if last is None or last.get("et_date") != today:
            return "usage_baseline_missing_today"
        effective = last["daily_usage"] + (
            self.st["desk_calls"] - g["desk_calls_at_last"])
        headroom = last["plan_daily_limit"] - effective
        remaining = self._remaining_td_today(now)
        if headroom < remaining:
            return f"provider_headroom_exhausted_precheck:headroom_" \
                   f"{headroom}_remaining_{remaining}"
        return None

    # -- payload processing ----------------------------------------------
    def _process_payload(self, action, parsed, receipt_dt):
        """Update bar states from one /time_series response."""
        sym = action["symbol"]
        session = action["session"]
        new_first = []
        values = (parsed or {}).get("values") or []
        for row in values:
            stamp = row.get("datetime", "")
            if not stamp.startswith(session):
                continue
            bs = stamp[11:16]
            key = f"{session}|{sym}|{bs}"
            bar = self.st["bars"].get(key)
            if bar is None:
                continue
            vals = {k: row.get(k) for k in
                    ("open", "high", "low", "close", "volume")}
            rhash = sha256_bytes(canonical(row))
            close_dt = datetime.fromisoformat(bar["close_utc"])
            if receipt_dt < close_dt:
                bar["partial_sightings"] += 1
                continue
            bar["sightings"] += 1
            if bar["first_seen"] is None:
                bar["first_seen"] = {
                    "receipt_utc": iso(receipt_dt),
                    "lag_s": (receipt_dt - close_dt).total_seconds(),
                    "via": action["kind"], "action_id": action["id"],
                    "values": vals, "hash": rhash}
                new_first.append(key)
            elif bar["last_hash"] is not None and rhash != bar["last_hash"]:
                diffs = {k: [bar["last_values"][k], vals[k]]
                         for k in vals if bar["last_values"][k] != vals[k]}
                if diffs:
                    bar["revisions"].append({
                        "receipt_utc": iso(receipt_dt), "phase": action["kind"],
                        "action_id": action["id"], "field_diffs": diffs,
                        "from_hash": bar["last_hash"], "to_hash": rhash})
            bar["last_values"] = vals
            bar["last_hash"] = rhash
        return new_first

    # -- one call ----------------------------------------------------------
    def _call(self, action):
        kind = action["kind"]
        req_dt = now_utc()
        req_mono = time.monotonic()
        if kind == "usage":
            status, body = self.transport("usage", {})
            params = {}
        else:
            d = action["session"]
            params = {"symbol": action["symbol"], "interval": "1h",
                      "start_date": d + "T00:00:00",
                      "end_date": d + "T23:59:59",
                      "timezone": "America/New_York", "outputsize": "5000",
                      "order": "ASC", "adjust": "splits"}
            status, body = self.transport("series", params)
        rec_dt = now_utc()
        rec_mono = time.monotonic()
        self._count_call(rec_dt, kind)
        self.st["journal_seq"] += 1
        seq = self.st["journal_seq"]
        payload_rel = None
        if body:
            pdir = os.path.join(ARCHIVE_NS, "payloads",
                                action.get("session", "misc"))
            os.makedirs(pdir, exist_ok=True)
            sym = action.get("symbol", "usage")
            payload_rel = f"payloads/{action.get('session','misc')}/" \
                          f"{seq:05d}_{kind}_{sym}.json"
            with open(os.path.join(ARCHIVE_NS, payload_rel), "wb") as f:
                f.write(body)
        parsed = None
        provider_error = None
        try:
            parsed = json.loads(body.decode()) if body else None
        except Exception:
            provider_error = "undecodable_body"
        if isinstance(parsed, dict) and parsed.get("status") == "error":
            provider_error = {"code": parsed.get("code"),
                              "message": parsed.get("message")}
        is_429 = status == 429 or (isinstance(provider_error, dict)
                                   and provider_error.get("code") == 429)
        if is_429:
            self.st["consecutive_429"] += 1
        elif status == 200 and provider_error is None:
            self.st["consecutive_429"] = 0
        new_first = []
        if kind != "usage" and status == 200 and isinstance(parsed, dict) \
                and parsed.get("values") is not None:
            new_first = self._process_payload(action, parsed, rec_dt)
        if kind == "finalization":
            bar = self.st["bars"][action["bar_key"]]
            bar["finalized"] = True
            if bar["first_seen"] is None:
                bar["missing_at_finalization"] = True
        if kind == "usage" and isinstance(parsed, dict):
            self.st["usage_snapshots"].append({
                "tag": action.get("tag"), "receipt_utc": iso(rec_dt),
                "provider": parsed})
        if kind == "usage":
            reason = self.usage_guard_on_reading(action, status, body,
                                                  rec_dt)
            if reason:
                self.st["stopped"] = {"reason": reason,
                                      "at": iso(rec_dt)}
        rec = {
            "seq": seq, "action_id": action["id"], "kind": kind,
            "session": action.get("session"), "symbol": action.get("symbol"),
            "bar_key": action.get("bar_key"),
            "scheduled_due_utc": action["due"],
            "execution_lateness_s":
                (req_dt - datetime.fromisoformat(action["due"])
                 ).total_seconds(),
            "request_ts_utc": iso(req_dt), "receipt_ts_utc": iso(rec_dt),
            "request_mono": req_mono, "receipt_mono": rec_mono,
            "http_status": status, "provider_error": provider_error,
            "payload_sha256": sha256_bytes(body) if body else None,
            "payload_file": payload_rel,
            "bars_in_payload": len((parsed or {}).get("values") or [])
            if kind != "usage" else None,
            "new_first_seen": new_first,
            "desk_calls_total_after": self.st["desk_calls"]}
        journal_append(rec)
        return rec

    # -- action driver -----------------------------------------------------
    # ------------------------------------------------------------ tripwire
    def mark_stale(self, now, cause):
        """Mark overdue ladder/finalization actions missed_late (used when
        a tripwire hold lifts after their lateness window has passed)."""
        for action in self.st["actions"]:
            if action["status"] != "pending":
                continue
            if action["kind"] not in ("ladder", "finalization"):
                continue
            due = datetime.fromisoformat(action["due"])
            late = (now - due).total_seconds()
            if late > LATE_WINDOW_S:
                action["status"] = "missed_late"
                action["lateness_s"] = late
                action["missed_cause"] = cause
                if action["kind"] == "finalization":
                    bar = self.st["bars"][action["bar_key"]]
                    bar["finalized"] = True
                    if bar["first_seen"] is None:
                        bar["missing_at_finalization"] = True

    def process_tripwire_clear(self, now):
        """Consume state/tripwire_clear.json written by the watchdog after
        adjudication: {verdicts: {message_id: 'confirmed'|'contradiction'}}.
        Returns 'stopped' if a contradiction verdict fired the tripwire."""
        if not os.path.exists(CLEAR_PATH):
            return None
        try:
            with open(CLEAR_PATH) as f:
                clear = json.load(f)
        except Exception:
            return None
        tw = self.st["tripwire"]
        fired = None
        for mid, verdict in (clear.get("verdicts") or {}).items():
            rec = next((r for r in tw["pending_review"]
                        if r["id"] == mid), None)
            if verdict == "contradiction":
                fired = {"id": mid,
                         "reply_file": rec and rec.get("reply_file")}
            elif verdict == "confirmed":
                tw["filed"].append({
                    "id": mid, "filed_utc": iso(now),
                    "reply_file": rec and rec.get("reply_file"),
                    "from": rec and rec.get("from"),
                    "subject": rec and rec.get("subject")})
                tw["pending_review"] = [r for r in tw["pending_review"]
                                         if r["id"] != mid]
        os.remove(CLEAR_PATH)
        if fired:
            self.st["stopped"] = {
                "reason": "TRIPWIRE FIRED — TD email reply contradicts the "
                          "AI-assistant answers on Q1-Q3 (message "
                          f"{fired['id']}); restart only after ChatGPT "
                          "adjudication",
                "at": iso(now), "tripwire_message_id": fired["id"],
                "tripwire_reply_file": fired["reply_file"]}
            tw["hold"] = False
            save_state(self.st)
            return "stopped"
        if tw["hold"] and not tw["pending_review"]:
            tw["hold"] = False
            tw["hold_info"] = None
            self.mark_stale(now, "tripwire_hold")
            save_state(self.st)
        return None

    def execute_tripwire(self, action, now):
        """Pre-open Gmail check for the session day. Clean = no TD-sender
        message after the inquiry cutoff that is not already filed.
        Any new candidate or any search failure sets the hold (fail-closed:
        the day's captures proceed only on a clean check)."""
        tw = self.st["tripwire"]
        check = {"session": action["session"], "at_utc": iso(now)}
        try:
            found = gmail_tripwire_search()
        except Exception as e:  # noqa: BLE001 — fail closed, record cause
            check["outcome"] = "search_failed"
            check["error"] = str(e)[:400]
            tw["checks"].append(check)
            tw["hold"] = True
            tw["hold_info"] = {"since_utc": iso(now),
                               "session": action["session"],
                               "reason": "tripwire search failed",
                               "error": str(e)[:400]}
            save_state(self.st)
            return
        filed_ids = {r["id"] for r in tw["filed"]}
        pending_ids = {r["id"] for r in tw["pending_review"]}
        new = [m for m in found
               if m["id"] not in filed_ids and m["id"] not in pending_ids]
        check["candidates"] = [m["id"] for m in found]
        if not new:
            check["outcome"] = "clean"
            tw["checks"].append(check)
            save_state(self.st)
            return
        os.makedirs(TRIPWIRE_DIR, exist_ok=True)
        for m in new:
            rec = {**m, "detected_utc": iso(now),
                   "session": action["session"], "reply_file": None}
            try:
                body = gmail_read_message(m["id"])
                path = os.path.join(TRIPWIRE_DIR, f"reply_{m['id']}.json")
                with open(path, "w") as f:
                    json.dump(body, f, indent=1)
                rec["reply_file"] = path
            except Exception as e:  # noqa: BLE001
                rec["read_error"] = str(e)[:400]
            tw["pending_review"].append(rec)
        check["outcome"] = "reply_pending_review"
        check["new"] = [m["id"] for m in new]
        tw["checks"].append(check)
        tw["hold"] = True
        tw["hold_info"] = {"since_utc": iso(now),
                           "session": action["session"],
                           "reason": "TD reply awaiting adjudication",
                           "message_ids": [m["id"] for m in new]}
        save_state(self.st)

    # ------------------------------------------------------- review gate
    def review_gate_sync(self, now):
        """ChatGPT source-review HOLD (Issue #1 comment 6385813954):
        while state/REVIEW_HOLD exists, no Twelve Data call executes
        (tripwire Gmail checks and archive pushes still run). When the
        file is removed after the review, sessions whose capture window
        fully passed while held are slipped as documented review-wait:
        their remaining capture actions are marked skipped_review_wait
        (never executed, never backfilled)."""
        gate = self.st.setdefault(
            "review_gate", {"held": False, "slipped_sessions": []})
        held = os.path.exists(REVIEW_HOLD_PATH)
        if held and not gate["held"]:
            gate["held"] = True
            gate["since_utc"] = iso(now)
            save_state(self.st)
        elif not held and gate["held"]:
            gate["held"] = False
            gate["lifted_utc"] = iso(now)
            for d in self.manifest["sessions"]:
                fins = [a for a in self.st["actions"]
                        if a["session"] == d
                        and a["kind"] == "finalization"]
                if fins and all(
                        datetime.fromisoformat(a["due"]) < now
                        for a in fins):
                    for a in self.st["actions"]:
                        if a["session"] == d and a["status"] == "pending" \
                                and a["kind"] in ("usage", "ladder",
                                                  "finalization",
                                                  "revision"):
                            a["status"] = "skipped_review_wait"
                    self.st["sessions_status"][d] = \
                        "slipped_review_wait"
                    gate["slipped_sessions"].append(d)
            save_state(self.st)
        return gate["held"]

    def run_due(self, now=None):
        now = now or now_utc()
        if os.path.exists(STOP_PATH):
            with open(STOP_PATH) as f:
                reason = f.read().strip()
            self.st["stopped"] = {"reason": "STOP file: " + reason,
                                  "at": iso(now)}
            save_state(self.st)
            return "stopped"
        if self.process_tripwire_clear(now) == "stopped":
            return "stopped"
        if self.st["tripwire"]["hold"]:
            return "held"
        review_held = self.review_gate_sync(now)
        for action in self.st["actions"]:
            if action["status"] != "pending":
                continue
            due = datetime.fromisoformat(action["due"])
            if due > now:
                break
            if self.st["stopped"]:
                break
            if review_held and action["kind"] not in ("tripwire",
                                                       "archive_push"):
                continue  # source-review HOLD: no TD calls; the schedule
                # itself is untouched — slipped sessions are marked at lift
            if action["kind"] == "tripwire":
                self.execute_tripwire(action, now)
                action["status"] = "done"
                action["executed_utc"] = iso(now)
                save_state(self.st)
                if self.st["tripwire"]["hold"]:
                    return "held"
                continue
            if action["kind"] == "archive_push":
                action["status"] = "done"
                action["executed_utc"] = iso(now)
                save_state(self.st)
                self.archive_push()
                continue
            if action["kind"] == "ladder":
                bar = self.st["bars"][action["bar_key"]]
                if bar["first_seen"] is not None:
                    action["status"] = "skipped_seen"
                    continue
            late = (now - due).total_seconds()
            if action["kind"] in ("ladder", "finalization") \
                    and late > LATE_WINDOW_S:
                action["status"] = "missed_late"
                action["lateness_s"] = late
                if action["kind"] == "finalization":
                    bar = self.st["bars"][action["bar_key"]]
                    bar["finalized"] = True
                    if bar["first_seen"] is None:
                        bar["missing_at_finalization"] = True
                continue
            cap = self.cap_check(action, now)
            if cap:
                self.st["stopped"] = {"reason": cap, "at": iso(now)}
                action["status"] = "refused_cap"
                save_state(self.st)
                return "stopped"
            pre = self.provider_precheck(action, now)
            if pre:
                self.st["stopped"] = {"reason": pre, "at": iso(now)}
                action["status"] = "refused_provider_precheck"
                save_state(self.st)
                return "stopped"
            self._call(action)
            action["status"] = "done"
            action["executed_utc"] = iso(now)
            save_state(self.st)
            if self.st["stopped"]:
                return "stopped"
            if self.st["consecutive_429"] >= 2:
                self.st["stopped"] = {
                    "reason": "two_consecutive_429 (protocol S10)",
                    "at": iso(now)}
                save_state(self.st)
                return "stopped"
            time.sleep(PACE_S)
        save_state(self.st)
        if review_held:
            return "held_review"
        pending = [a for a in self.st["actions"] if a["status"] == "pending"]
        if not pending:
            return "complete"
        return "running"

    def archive_push(self):
        import subprocess
        clone = os.path.join(BASE, "archive_clone")
        rel = "captures/td_feed_measure_pilot_20261026"
        def git(*args):
            return subprocess.run(["git", "-C", clone, *args],
                                  capture_output=True, text=True, timeout=300)
        git("add", rel)
        committed = git("commit", "-m",
                        "capture: QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22"
                        " append-only journal+payloads (in progress)")
        pushed = git("push", "origin", "main")
        ok = pushed.returncode == 0
        hb = {"archive_push_utc": iso(now_utc()), "ok": ok,
              "commit_rc": committed.returncode, "push_rc": pushed.returncode}
        with open(os.path.join(STATE_DIR, "last_push.json"), "w") as f:
            json.dump(hb, f, indent=1)
        return ok


def heartbeat(st, status):
    nxt = None
    for a in st["actions"]:
        if a["status"] == "pending":
            nxt = {"id": a["id"], "due": a["due"]}
            break
    seen = sum(1 for b in st["bars"].values() if b["first_seen"])
    with open(HEARTBEAT_PATH, "w") as f:
        json.dump({"ts_utc": iso(now_utc()), "pid": os.getpid(),
                   "status": status, "next_action": nxt,
                   "desk_calls": st["desk_calls"],
                   "bars_first_seen": seen, "bars_total": len(st["bars"]),
                   "tripwire_hold": st.get("tripwire", {}).get("hold", False),
                   "review_hold": st.get("review_gate", {}).get(
                       "held", False),
                   "tripwire_last_check": (st.get("tripwire", {})
                                           .get("checks") or [None])[-1],
                   "stopped": st["stopped"]}, f, indent=1)


def main():
    manifest = json.load(open(os.path.join(BASE, "run_manifest.json")))
    os.makedirs(STATE_DIR, exist_ok=True)
    os.makedirs(os.path.join(ARCHIVE_NS, "payloads"), exist_ok=True)
    if os.path.exists(STATE_PATH):
        st = load_state()
    else:
        st = init_state(manifest)
        save_state(st)
    pilot = Pilot(manifest, live_transport, st)
    while True:
        status = pilot.run_due()
        heartbeat(pilot.st, status)
        if status in ("complete", "stopped"):
            print(json.dumps({"pilot": status,
                              "stopped": pilot.st["stopped"],
                              "desk_calls": pilot.st["desk_calls"]}))
            return 0 if status == "complete" else 3
        nxt = None
        for a in pilot.st["actions"]:
            if a["status"] == "pending":
                nxt = datetime.fromisoformat(a["due"])
                break
        wait = 15.0
        if nxt:
            wait = max(2.0, min(20.0, (nxt - now_utc()).total_seconds()))
        time.sleep(wait)


if __name__ == "__main__":
    sys.exit(main())
