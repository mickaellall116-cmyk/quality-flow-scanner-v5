#!/usr/bin/env python3
"""
Offline collector lifecycle repair candidate — 2026-10-12.
Based on failed commit 411457df87595f908906c899043d21a76ae2cea1.
NO vendor transport, no execution clearance, no automatic migration.

Changes: all run paths enforce preflight; whole-run exclusive process lock;
immutable canonical manifest binding; RECEIVED is not COMPLETED; durable
completion binds request/manifest/receipt and reused bytes are revalidated.
Interrupted attempts remain HOLD without redispatch. Native 4H responses
receive structural diagnostic validation only, never 1H completeness claims.
Exact venue identity must be declared and checked. Legacy state is refused.

Known limits: lifecycle regression probes stub accepted dependencies;
actual source/calendar/limiter integration and the revised explicit venue
manifest still require independent review. No full feed or strategy verdict.
"""
from __future__ import annotations

import hashlib
import copy
import fcntl
from contextlib import contextmanager
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


def canonical_digest(value) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                  allow_nan=False).encode())


def _bar_bound(req: dict) -> int:
    from datetime import date
    d0 = date.fromisoformat(req["start_date"][:10])
    d1 = date.fromisoformat(req["end_date"][:10])
    return ((d1 - d0).days + 1) * BARS_PER_DAY[req["interval"]]


def validate_manifest(man: dict) -> list[str]:
    """Spec point 1a: finite, no-pagination, no-retry manifest validation."""
    errs = []
    if not isinstance(man, dict):
        return ["manifest must be an object"]
    if man.get("endpoint") != ENDPOINT:
        errs.append(f"endpoint mismatch: {man.get('endpoint')!r}")
    reqs = man.get("requests")
    if not isinstance(reqs, list) or not reqs:
        return errs + ["requests missing/empty"]
    seen = set()
    for r in reqs:
        if not isinstance(r, dict):
            errs.append("request must be an object")
            continue
        rid = r.get("request_id")
        if not isinstance(rid, str) or not rid or not all(c.isalnum() or c in "_-" for c in rid):
            errs.append("unsafe/missing request_id")
            continue
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
        if r.get("adjust") not in ("none", "splits", "dividends", "all"):
            errs.append(f"{rid}: invalid adjustment domain")
        if r.get("order") not in ("asc", "desc"):
            errs.append(f"{rid}: invalid order")
        venue = r.get("venue_identity")
        if not isinstance(venue, dict) or not venue.get("exchange") or not venue.get("currency"):
            errs.append(f"{rid}: explicit exchange/currency identity required")
        try:
            from datetime import datetime
            start = datetime.fromisoformat(r["start_date"])
            end = datetime.fromisoformat(r["end_date"])
            if start >= end:
                errs.append(f"{rid}: invalid request window")
            if type(r.get("outputsize")) is not int or not 1 <= r["outputsize"] <= 5000:
                errs.append(f"{rid}: invalid outputsize")
            bound = _bar_bound(r)
        except (KeyError, TypeError, ValueError):
            errs.append(f"{rid}: malformed request window/interval")
            continue
        if r.get("one_response_bound_bars") != bound:
            errs.append(f"{rid}: one_response_bound_bars {r.get('one_response_bound_bars')} != derived {bound}")
        if bound > int(r.get("outputsize", 0)):
            errs.append(f"{rid}: window bound {bound} exceeds outputsize {r.get('outputsize')} (would need pagination)")
        if any(k not in r for k in ("symbol", "interval", "start_date", "end_date", "timezone", "adjust")):
            errs.append(f"{rid}: missing identity fields")
            continue
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
    if not isinstance(p, dict):
        return fails + ["prerequisites must be an object"]
    if p.get("plan") != "Basic":
        fails.append("entitlement: plan is not recorded as Basic")
    ep = p.get("endpoint_weight") or {}
    if not isinstance(ep, dict):
        return fails + ["endpoint evidence must be an object"]
    if ep.get("endpoint") != "/time_series" or ep.get("credits_per_request") != 1:
        fails.append("entitlement: /time_series weight != 1 credit/request")
    if not ep.get("evidence"):
        fails.append("entitlement: weight evidence not recorded")
    ret = p.get("retention") or {}
    if not isinstance(ret, dict):
        return fails + ["retention evidence must be an object"]
    if ret.get("status") != "BOUNDED_RESOLVED":
        fails.append("retention: status is not BOUNDED_RESOLVED")
    if "30-day" not in str(ret.get("condition", "")):
        fails.append("retention: 30-day post-termination deletion condition not recorded")
    if p.get("interval_semantics", {}).get("status") not in ("SOURCED", "INSUFFICIENT"):
        fails.append("interval semantics status missing (must be SOURCED or INSUFFICIENT)")
    return fails


class Collector:
    def __init__(self, state_dir: Path, manifest: dict, limiter: RollingCreditLimiter,
                 transport=None, semantics_status: str = "INSUFFICIENT",
                 prereq_path: Path | None = None):
        self.state_dir = Path(state_dir)
        self.receipts = self.state_dir / "receipts"
        self.receipts.mkdir(parents=True, exist_ok=True)
        errors = validate_manifest(manifest)
        if errors:
            raise CollectorError("invalid manifest: " + "; ".join(errors))
        self.manifest = copy.deepcopy(manifest)
        self.manifest_digest = canonical_digest(self.manifest)
        self.prereq_path = Path(prereq_path) if prereq_path is not None else HERE / "prerequisites.json"
        self.requests = {r["request_id"]: r for r in self.manifest["requests"]}
        self.limiter = limiter
        # Default transport is the disabled one: zero vendor calls, always.
        self.transport = transport or self._disabled_transport
        self.semantics_status = semantics_status
        self.lifecycle_path = self.state_dir / "lifecycle.jsonl"
        self.pilot_state_path = self.state_dir / "pilot_state.json"
        self._state = self._load_pilot_state()
        self._events = self._load_events()
        # Reconciliation happens under the exclusive run lock, never in constructor.

    @contextmanager
    def _exclusive_run(self):
        with open(self.state_dir / "collector.lock", "a+") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise CollectorError("another collector owns the state directory")
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _bind_manifest(self):
        p = self.state_dir / "manifest_binding.json"
        if p.exists():
            saved = json.loads(p.read_text())
            if saved != {"sha256": self.manifest_digest}:
                raise CollectorError("manifest binding changed; refusing receipt/state reuse")
        else:
            if self._events or any(self.receipts.iterdir()) or self.pilot_state_path.exists():
                raise CollectorError("legacy/unbound evidence requires review; no migration")
            with open(p, "x") as f:
                json.dump({"sha256": self.manifest_digest}, f)
                f.flush()
                os.fsync(f.fileno())

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
        completed = {e["request_id"] for e in self._events if e["event"] == "COMPLETED"}
        started = {e["request_id"] for e in self._events if e["event"] == "STARTED"}
        for rid in started - completed:
            self._hold(f"AMBIGUOUS: {rid} dispatched without durable validation completion; no redispatch", rid)
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
        event = recorded[-1]
        if event.get("request_digest") != canonical_digest(req) or event.get("manifest_digest") != self.manifest_digest:
            return False, "receipt request/manifest binding mismatch"
        complete = [e for e in self._events if e["event"] == "COMPLETED" and e["request_id"] == req["request_id"]]
        if not complete or complete[-1].get("sha256") != event.get("sha256") or complete[-1].get("request_digest") != canonical_digest(req) or complete[-1].get("manifest_digest") != self.manifest_digest:
            return False, "no matching durable validated completion"
        raw = path.read_bytes()
        if len(raw) != event.get("bytes"):
            return False, "receipt byte-length mismatch"
        if sha256_bytes(raw) != recorded[-1]["sha256"]:
            return False, "receipt hash mismatch vs lifecycle record (stale/corrupt)"
        try:
            payload = json.loads(raw)
        except Exception:
            return False, "receipt unparseable (malformed)"
        if not isinstance(payload, dict) or not isinstance(payload.get("meta"), dict):
            return False, "malformed receipt object/meta"
        meta = payload["meta"]
        if meta.get("symbol") != req["symbol"] or meta.get("interval") != req["interval"]:
            return False, "receipt meta symbol/interval does not bind to manifest identity"
        venue = req["venue_identity"]
        if any(meta.get(k) != v for k, v in venue.items()):
            return False, "receipt venue binding mismatch"
        failure = self._validate_bars(req, payload.get("values"))
        return (False, "receipt revalidation failed: " + failure) if failure else (True, "ok")

    # -- main entry --------------------------------------------------------
    def run(self) -> dict:
        with self._exclusive_run():
            # Every entry path enforces the same prerequisite/source gates.
            errors = validate_manifest(self.manifest)
            failures = check_prerequisites(self.manifest, self.prereq_path)
            if errors or failures:
                raise CollectorError("dispatch preflight failed: " + "; ".join(errors + failures))
            self._state = self._load_pilot_state()
            self._events = self._load_events()
            self._bind_manifest()
            self._reconcile_started_without_receipt()
            return self._run_locked()

    def _run_locked(self) -> dict:
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
                self._hold(f"transport error for {rid}: {type(e).__name__}", rid)
                summary["outcome"] = "HOLD: transport error (details omitted to protect credentials)"
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
        if not isinstance(payload, dict) or not isinstance(payload.get("meta"), dict):
            self._preserve_rejected(rid, body)
            return f"malformed response object/meta for {rid}"
        if payload.get("status") != "ok":
            self._preserve_rejected(rid, body)
            return f"API status {payload.get('status')!r} for {rid}: {str(payload.get('message'))[:120]}"
        meta = payload.get("meta") or {}
        if meta.get("symbol") != req["symbol"] or meta.get("interval") != req["interval"]:
            self._preserve_rejected(rid, body)
            return f"meta binding mismatch for {rid} (symbol/interval)"
        if any(meta.get(k) != v for k, v in req["venue_identity"].items()):
            self._preserve_rejected(rid, body)
            return f"venue binding mismatch for {rid}"
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
                   rows=len(values), request_digest=canonical_digest(req),
                   manifest_digest=self.manifest_digest)
        # Accepted validation path (validate_input.validate) runs on the
        # parsed bars with a mandatory tz-aware as-of. A validation failure
        # is a terminal HOLD; bars are never silently accepted.
        vfail = self._validate_bars(req, values)
        if vfail is not None:
            return f"validation failed for {rid}: {vfail}"
        self._emit("COMPLETED", rid, sha256=sha256_bytes(body),
                   request_digest=canonical_digest(req), manifest_digest=self.manifest_digest,
                   validation_scope="session_1h" if req["interval"] == "1h" else "native_4h_structural_diagnostic")
        return None

    def _validate_bars(self, req: dict, values: list) -> str | None:
        if not isinstance(values, list) or not values or any(not isinstance(v, dict) for v in values):
            return "values missing/malformed"
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
            if df.index.has_duplicates:
                return "duplicate labels"
            if not (df.index.is_monotonic_increasing or df.index.is_monotonic_decreasing):
                return "unordered labels"
            if req["interval"] == "4h":
                # Native bars are diagnostic, never fed into 1H constituent validation.
                import numpy as np
                fields = df[["open", "high", "low", "close", "volume"]]
                if not np.isfinite(fields.to_numpy()).all():
                    return "non-finite OHLCV"
                if ((df.high < df[["open", "close"]].max(axis=1)) |
                    (df.low > df[["open", "close"]].min(axis=1)) |
                    (df.high < df.low) | (df.volume < 0)).any():
                    return "invalid OHLCV geometry"
                start = pd.Timestamp(req["start_date"]).tz_localize("America/New_York")
                end = pd.Timestamp(req["end_date"]).tz_localize("America/New_York")
                if (df.index < start).any() or (df.index > end).any():
                    return "native diagnostic label outside request window"
                return None
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

