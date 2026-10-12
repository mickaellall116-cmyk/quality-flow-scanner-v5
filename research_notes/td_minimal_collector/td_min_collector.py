#!/usr/bin/env python3
"""
td_min_collector.py — QF-TD-MINIMAL-COLLECTOR-20261012-01 r1.

ISOLATED, reduced-scope Twelve Data collector. Spec: GitHub Issue #1
comment 6125163484; direct authorization: Mike, main chat, 2026-10-12
12:48 ET ("Proceed with Twelve Data task 6125163484 under the
60-minute budget").

Reduced scope vs the R3 pilot wrapper (pilot_harness/pilot_acquire.py):
  REMOVED from executable scope: pagination, retries (max 1 attempt per
  request), REV7/REV30 revision legs.
  NOT weakened: pinned source verification, input validation, timestamp /
  session checks, retention prerequisites, the shared persisted rolling
  credit limiter.

ZERO-CALL BUILD: this revision ships with NO vendor transport. The only
transport constructor raises TransportDisabled; dispatch logic is
exercised exclusively through injected synthetic transports in tests.
No Twelve Data API (or any vendor API) request can be made by this code.

Reuse (accepted fd03906-lineage modules, imported, not copied):
  pilot_harness/rate_limiter.py   RollingCreditLimiter (shared ledger)
  pilot_harness/verify_sources.py verify_directory + PINNED archival SHAs
  pilot_harness/validate_input.py validate() (accepted validation path)
  pilot_harness/construct_4h.py   construct_4h() (gated, see below)

Lifecycle (append-only lifecycle.jsonl + atomic pilot_state.json):
  PLANNED -> CREDIT_RESERVED -> STARTED(attempt=1) -> RECEIVED -> COMPLETED
  Any error / incomplete coverage / output-cap uncertainty -> terminal
  HOLD, persistent across invocations. A request found STARTED with no
  receipt on a later invocation is AMBIGUOUS -> terminal HOLD, never
  auto-recalled. Receipts are write-once (no overwrite); reuse only
  after exact hash/bytes/params/identity verification. Credit
  reservations are recorded separately from the vendor-attempt count.

Construction gate: session-aligned 1H->4H construction runs ONLY when
officially sourced interval-start semantics + complete validated bars +
as-of boundary all pass. Semantics are currently INSUFFICIENT (Stage-0
offline report; packet amendment A6.1), so construction is a named
HOLD in this revision; native 4H is diagnostic only.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent / "pilot_harness"
sys.path.insert(0, str(HARNESS))

from rate_limiter import RollingCreditLimiter, LedgerCorruptError  # noqa: E402
from verify_sources import verify_directory, PINNED, ARCHIVAL_DIR  # noqa: E402

ENDPOINT = "https://api.twelvedata.com/time_series"
FROZEN_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "GOOGL",
                   "QQQ", "PLTR", "HOOD", "ANET", "SMCI", "SOFI", "RKLB",
                   "NIO", "BBAI", "ONDS", "DRAM", "SPCX", "TWTR"]
IN_SCOPE_LEGS = {"PAR", "PAR4H", "ADJ", "SPOT"}
BARS_PER_DAY = {"1h": 7, "4h": 2}  # conservative calendar bound (see manifest)


class CollectorError(Exception):
    pass


class TransportDisabled(CollectorError):
    """Raised by the only built-in transport: this revision makes no
    vendor requests, by construction."""


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _bar_bound(req: dict) -> int:
    from datetime import date
    d0 = date.fromisoformat(req["start_date"][:10])
    d1 = date.fromisoformat(req["end_date"][:10])
    return ((d1 - d0).days + 1) * BARS_PER_DAY[req["interval"]]


def validate_manifest(man: dict) -> list[str]:
    """Spec point 1a: finite, no-pagination, no-retry manifest validation."""
    errs = []
    if man.get("endpoint") != ENDPOINT:
        errs.append(f"endpoint mismatch: {man.get('endpoint')!r}")
    reqs = man.get("requests")
    if not isinstance(reqs, list) or not reqs:
        return errs + ["requests missing/empty"]
    seen = set()
    for r in reqs:
        rid = r.get("request_id")
        if rid in seen:
            errs.append(f"duplicate request_id {rid}")
        seen.add(rid)
        if r.get("symbol") not in FROZEN_UNIVERSE:
            errs.append(f"{rid}: symbol {r.get('symbol')!r} not in frozen 20")
        if r.get("leg") not in IN_SCOPE_LEGS:
            errs.append(f"{rid}: leg {r.get('leg')!r} out of reduced scope")
        if r.get("interval") not in BARS_PER_DAY:
            errs.append(f"{rid}: interval {r.get('interval')!r} not allowed")
        if r.get("timezone") != "America/New_York":
            errs.append(f"{rid}: timezone not America/New_York")
        if r.get("max_attempts") != 1:
            errs.append(f"{rid}: max_attempts must be exactly 1 (no retry)")
        if r.get("pagination"):
            errs.append(f"{rid}: pagination present (removed from scope)")
        if r.get("credit_weight") != 1 or r.get("expected_credits") != 1:
            errs.append(f"{rid}: credit weight must be 1 (pinned evidence)")
        if r.get("output_name") != f"{rid}.json":
            errs.append(f"{rid}: output_name not deterministic ({rid}.json)")
        bound = _bar_bound(r)
        if r.get("one_response_bound_bars") != bound:
            errs.append(f"{rid}: one_response_bound_bars {r.get('one_response_bound_bars')} != derived {bound}")
        if bound > int(r.get("outputsize", 0)):
            errs.append(f"{rid}: window bound {bound} exceeds outputsize {r.get('outputsize')} (would need pagination)")
        expect_identity = (f"{r['symbol']}|/time_series|{r['interval']}|{r['start_date']}|"
                           f"{r['end_date']}|{r['timezone']}|adjust={r['adjust']}")
        if r.get("identity") != expect_identity:
            errs.append(f"{rid}: identity string mismatch")
    return errs


def check_prerequisites(man: dict, prereq_path: Path) -> list[str]:
    """Spec point 1b/1c: pinned source verification + Basic entitlement /
    retention prerequisites. Returns failure list (empty = pass). Any
    failure blocks dispatch; nothing here is weakened or skippable."""
    fails = []
    fails += [f"source: {f}" for f in verify_directory(ARCHIVAL_DIR, PINNED)]
    if not prereq_path.exists():
        return fails + [f"prerequisites file MISSING: {prereq_path}"]
    try:
        p = json.loads(prereq_path.read_text())
    except Exception as e:  # malformed evidence fails closed
        return fails + [f"prerequisites unparseable: {e}"]
    if p.get("plan") != "Basic":
        fails.append("entitlement: plan is not recorded as Basic")
    ep = p.get("endpoint_weight") or {}
    if ep.get("endpoint") != "/time_series" or ep.get("credits_per_request") != 1:
        fails.append("entitlement: /time_series weight != 1 credit/request")
    if not ep.get("evidence"):
        fails.append("entitlement: weight evidence not recorded")
    ret = p.get("retention") or {}
    if ret.get("status") != "BOUNDED_RESOLVED":
        fails.append("retention: status is not BOUNDED_RESOLVED")
    if "30-day" not in str(ret.get("condition", "")):
        fails.append("retention: 30-day post-termination deletion condition not recorded")
    if p.get("interval_semantics", {}).get("status") not in ("SOURCED", "INSUFFICIENT"):
        fails.append("interval semantics status missing (must be SOURCED or INSUFFICIENT)")
    return fails


class Collector:
    def __init__(self, state_dir: Path, manifest: dict, limiter: RollingCreditLimiter,
                 transport=None, semantics_status: str = "INSUFFICIENT"):
        self.state_dir = Path(state_dir)
        self.receipts = self.state_dir / "receipts"
        self.receipts.mkdir(parents=True, exist_ok=True)
        self.manifest = manifest
        self.requests = {r["request_id"]: r for r in manifest["requests"]}
        self.limiter = limiter
        # Default transport is the disabled one: zero vendor calls, always.
        self.transport = transport or self._disabled_transport
        self.semantics_status = semantics_status
        self.lifecycle_path = self.state_dir / "lifecycle.jsonl"
        self.pilot_state_path = self.state_dir / "pilot_state.json"
        self._state = self._load_pilot_state()
        self._events = self._load_events()
        self._reconcile_started_without_receipt()

    # -- persistence ---------------------------------------------------
    def _load_pilot_state(self) -> dict:
        if self.pilot_state_path.exists():
            return json.loads(self.pilot_state_path.read_text())
        return {"status": "ACTIVE", "hold_reason": None, "attempts": 0,
                "credit_reservations": 0, "completed": []}

    def _save_pilot_state(self) -> None:
        tmp = self.pilot_state_path.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(self._state, f, indent=1, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.pilot_state_path)  # atomic terminal state

    def _load_events(self) -> list[dict]:
        if not self.lifecycle_path.exists():
            return []
        return [json.loads(l) for l in self.lifecycle_path.read_text().splitlines() if l.strip()]

    def _emit(self, event: str, request_id: str | None, **kw) -> None:
        rec = {"ts_utc": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z",
               "event": event, "request_id": request_id, **kw}
        with open(self.lifecycle_path, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())  # append-only, durable
        self._events.append(rec)

    def _hold(self, reason: str, request_id: str | None) -> None:
        self._state["status"] = "HOLD"
        self._state["hold_reason"] = reason
        self._emit("HOLD", request_id, reason=reason)
        self._save_pilot_state()

    def _reconcile_started_without_receipt(self) -> None:
        """Crash rule: STARTED with no RECEIVED and no receipt file is
        AMBIGUOUS -> terminal HOLD. Never auto-recalled."""
        if self._state["status"] == "HOLD":
            return
        received = {e["request_id"] for e in self._events if e["event"] == "RECEIVED"}
        for e in self._events:
            if e["event"] == "STARTED" and e["request_id"] not in received:
                rid = e["request_id"]
                if not (self.receipts / self.requests[rid]["output_name"]).exists():
                    self._emit("AMBIGUOUS", rid,
                               reason="started-without-receipt after crash/restart")
                    self._hold(f"AMBIGUOUS: {rid} started without receipt; never auto-recalled", rid)
                    return

    # -- transports ------------------------------------------------------
    @staticmethod
    def _disabled_transport(req: dict):
        raise TransportDisabled(
            "vendor transport disabled in QF-TD-MINIMAL-COLLECTOR r1 (zero-call build)")

    # -- receipts --------------------------------------------------------
    def _receipt_path(self, req: dict) -> Path:
        return self.receipts / req["output_name"]

    def _verify_receipt(self, req: dict, path: Path) -> tuple[bool, str]:
        """Exact hash/bytes/params/identity verification before reuse."""
        recorded = [e for e in self._events
                    if e["event"] == "RECEIVED" and e["request_id"] == req["request_id"]]
        if not recorded:
            return False, "receipt file present but no RECEIVED record (foreign)"
        raw = path.read_bytes()
        if sha256_bytes(raw) != recorded[-1]["sha256"]:
            return False, "receipt hash mismatch vs lifecycle record (stale/corrupt)"
        try:
            payload = json.loads(raw)
        except Exception:
            return False, "receipt unparseable (malformed)"
        meta = payload.get("meta") or {}
        if meta.get("symbol") != req["symbol"] or meta.get("interval") != req["interval"]:
            return False, "receipt meta symbol/interval does not bind to manifest identity"
        return True, "ok"

    # -- main entry --------------------------------------------------------
    def run(self) -> dict:
        summary = {"dispatched": 0, "reused": 0, "completed": 0, "outcome": None}
        if self._state["status"] == "HOLD":
            summary["outcome"] = f"HOLD (persistent): {self._state['hold_reason']}"
            return summary
        for rid, req in self.requests.items():
            path = self._receipt_path(req)
            if path.exists():
                ok, why = self._verify_receipt(req, path)
                if not ok:
                    self._hold(f"receipt verification failed for {rid}: {why}", rid)
                    summary["outcome"] = f"HOLD: {why}"
                    return summary
                summary["reused"] += 1
                if rid not in self._state["completed"]:
                    self._state["completed"].append(rid)
                summary["completed"] += 1
                continue
            # Credit reservation: recorded separately from attempt count.
            try:
                granted = self.limiter.try_acquire(req["credit_weight"], label=rid)
            except LedgerCorruptError as e:
                self._hold(f"shared limiter ledger corrupt: {e}", rid)
                summary["outcome"] = "HOLD: limiter ledger corrupt"
                return summary
            if not granted:
                self._emit("LIMITER_REFUSED", rid, credit_weight=req["credit_weight"])
                summary["outcome"] = "REFUSED: shared rolling limiter refused credit reservation"
                self._save_pilot_state()
                return summary
            self._state["credit_reservations"] += req["credit_weight"]
            self._emit("CREDIT_RESERVED", rid, credit_weight=req["credit_weight"])
            self._state["attempts"] += 1
            self._emit("STARTED", rid, attempt=1)
            self._save_pilot_state()
            summary["dispatched"] += 1
            try:
                status, body = self.transport(req)
            except TransportDisabled as e:
                self._hold(f"transport disabled: {e}", rid)
                summary["outcome"] = "HOLD: transport disabled (zero-call build)"
                return summary
            except Exception as e:  # transport-level failure, preserved
                self._preserve_rejected(rid, repr(e).encode())
                self._hold(f"transport error for {rid}: {e}", rid)
                summary["outcome"] = f"HOLD: transport error {e}"
                return summary
            problem = self._handle_response(req, status, body)
            if problem is not None:
                self._hold(problem, rid)
                summary["outcome"] = f"HOLD: {problem}"
                return summary
            self._state["completed"].append(rid)
            summary["completed"] += 1
            self._save_pilot_state()
        summary["outcome"] = "COMPLETE"
        self._save_pilot_state()
        return summary

    def _preserve_rejected(self, rid: str, raw: bytes) -> None:
        """Error evidence preserved privately (raw bytes + hash), write-once,
        where retention permits (Basic active-account retention, C4 bounded)."""
        p = self.receipts / f"{rid}.rejected.bin"
        if not p.exists():
            with open(p, "xb") as f:
                f.write(raw)
        self._emit("ERROR_EVIDENCE", rid, sha256=sha256_bytes(raw), bytes=len(raw))

    def _handle_response(self, req: dict, status: int, body: bytes) -> str | None:
        """Returns None on success, else the HOLD reason. Every failure
        path preserves the raw payload first."""
        rid = req["request_id"]
        if status != 200:
            self._preserve_rejected(rid, body)
            return f"HTTP {status} for {rid}"
        try:
            payload = json.loads(body)
        except Exception:
            self._preserve_rejected(rid, body)
            return f"unparseable response for {rid}"
        if payload.get("status") != "ok":
            self._preserve_rejected(rid, body)
            return f"API status {payload.get('status')!r} for {rid}: {str(payload.get('message'))[:120]}"
        meta = payload.get("meta") or {}
        if meta.get("symbol") != req["symbol"] or meta.get("interval") != req["interval"]:
            self._preserve_rejected(rid, body)
            return f"meta binding mismatch for {rid} (symbol/interval)"
        values = payload.get("values")
        if not isinstance(values, list) or not values:
            self._preserve_rejected(rid, body)
            return f"missing/empty values for {rid}"
        if len(values) >= int(req["outputsize"]):
            self._preserve_rejected(rid, body)
            return (f"output-cap uncertainty for {rid}: {len(values)} rows at "
                    f"outputsize={req['outputsize']} (possible truncation; no pagination in scope)")
        if len(values) > req["one_response_bound_bars"]:
            self._preserve_rejected(rid, body)
            return f"row count {len(values)} exceeds one-response bound {req['one_response_bound_bars']} for {rid}"
        path = self._receipt_path(req)
        try:
            with open(path, "xb") as f:  # no overwrite, ever
                f.write(body)
                f.flush()
                os.fsync(f.fileno())
        except FileExistsError:
            return f"receipt already exists for {rid} at write time (no-overwrite)"
        self._emit("RECEIVED", rid, sha256=sha256_bytes(body), bytes=len(body),
                   rows=len(values))
        # Accepted validation path (validate_input.validate) runs on the
        # parsed bars with a mandatory tz-aware as-of. A validation failure
        # is a terminal HOLD; bars are never silently accepted.
        vfail = self._validate_bars(req, values)
        if vfail is not None:
            return f"validation failed for {rid}: {vfail}"
        self._emit("COMPLETED", rid)
        return None

    def _validate_bars(self, req: dict, values: list) -> str | None:
        try:
            import pandas as pd
            from validate_input import validate, ValidationError
        except Exception as e:
            return f"validation path unavailable: {e}"
        try:
            df = pd.DataFrame(values)
            # Vendor payloads carry OHLCV as strings; the accepted
            # validation path compares numerically, so convert first
            # (non-numeric values become NaN and fail V10, fail-closed).
            for c in ("open", "high", "low", "close", "volume"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
            idx = pd.to_datetime(df["datetime"])
            # Declared timezone policy (manifest: timezone=America/New_York):
            # naive vendor stamps are exchange-local; aware stamps convert.
            idx = (idx.dt.tz_localize("America/New_York") if idx.dt.tz is None
                   else idx.dt.tz_convert("America/New_York"))
            df.index = idx
            rep = validate(df, req["symbol"], req["start_date"][:10],
                           req["end_date"][:10],
                           as_of=pd.Timestamp(req["end_date"][:10]).tz_localize("America/New_York") + pd.Timedelta(days=1))
            _ = rep
        except Exception as e:  # ValidationError or structural failure
            return str(e)[:200]
        # Construction gate (spec point 4): semantics INSUFFICIENT -> the
        # 1H->4H construction leg is a named HOLD, recorded, never run.
        if req["interval"] == "1h" and self.semantics_status != "SOURCED":
            self._emit("CONSTRUCTION_HOLD", req["request_id"],
                       reason="interval-start semantics INSUFFICIENT (A6.1); native 4H diagnostic only")
        return None


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["validate-manifest", "preflight"])
    ap.add_argument("--manifest", default=str(HERE / "manifest_reduced.json"))
    ap.add_argument("--prereq", default=str(HERE / "prerequisites.json"))
    a = ap.parse_args()
    man = json.loads(Path(a.manifest).read_text())
    errs = validate_manifest(man)
    if a.cmd == "validate-manifest":
        print(json.dumps({"manifest_errors": errs, "requests": len(man["requests"])}, indent=1))
        return 1 if errs else 0
    fails = check_prerequisites(man, Path(a.prereq))
    print(json.dumps({"manifest_errors": errs, "prerequisite_failures": fails,
                      "dispatch": "BLOCKED (zero-call build: no vendor transport)"}, indent=1))
    return 1 if (errs or fails) else 0


if __name__ == "__main__":
    raise SystemExit(main())
