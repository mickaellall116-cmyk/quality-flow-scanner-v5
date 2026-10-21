#!/usr/bin/env python3
"""Pinned CLI runner candidate — TD probe (task -67 r1, successor
of -66/-65; the usage session is integrity- AND execution-date-
bound — see account_preflight.py defect-3 repair + -67 closure).

Closes -64 gap G1 for the probe candidate: a pinned, invokable runner
around the FROZEN acquisition module. It:

- verifies the frozen pilot source by SHA-256 before importing it
  (pilot_acquire.py acf39bbd98f7174a4205019e754fc714ca420b4a7df43
  c815ea158a6fad67c59; sibling rate_limiter.py 06ad383d856e62d126d
  1aae9edc7804e1b09471d87d9b280ec55a25aea0b8d64);
- requires explicit --manifest/--manifest-sha256/--day/--store;
- checks the SCOPE ALLOWLIST (exact request-ID set, exact per-request
  fields, max_attempts=2 everywhere) BEFORE any preflight or
  transport construction;
- enforces the temporal eligibility gate for REV days
  (temporal_gate.py) before any transport construction;
- refuses manifest/file hash mismatch, unexpected request ID,
  nonempty unapproved leg, absolute/traversal store path, existing
  conflicting store, or unrecognized day — exit code 3, fail closed;
- wires the /api_usage account preflight (account_preflight.py) as
  the ManifestDriver preflight, once per execution day;
- takes NO credential in arguments or logs: transports receive URLs
  without key material; the production transport attaches the key at
  fetch time via the sanctioned helper, as in the frozen module.

Transport/clock/sleeper/limiter are injectable; the qualification
harness injects synthetic fakes. The live transport path (pilot
UrllibTransport) is constructed only when --transport-module is
absent, and is NEVER exercised by this task.

Offline candidate only — not adopted, not integrated.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import temporal_gate  # noqa: E402
from account_preflight import (  # noqa: E402
    AccountPreflight,
    DailyUsageSession,
)

PILOT_REL = "research_notes/pilot_harness/pilot_acquire.py"
PILOT_SHA256 = ("acf39bbd98f7174a4205019e754fc714ca420b4a7df43"
                "c815ea158a6fad67c59")
RATE_LIMITER_REL = "research_notes/pilot_harness/rate_limiter.py"
RATE_LIMITER_SHA256 = ("06ad383d856e62d126d1aae9edc7804e1b09471d87"
                       "d9b280ec55a25aea0b8d64")

RECOGNIZED_DAYS = ("D1", "D7", "D30")

# Scope allowlist: request_id -> exact expected manifest fields.
EXPECTED_REQUESTS = {
    "REQ-ADJ-01": {"symbol": "NVDA", "adjust": "splits", "leg": "ADJ",
                   "day": "D1", "base_request_id": ""},
    "REQ-ADJ-02": {"symbol": "TSLA", "adjust": "splits", "leg": "ADJ",
                   "day": "D1", "base_request_id": ""},
    "REQ-ADJ-03": {"symbol": "AAPL", "adjust": "splits", "leg": "ADJ",
                   "day": "D1", "base_request_id": ""},
    "REQ-ADJ-01N": {"symbol": "NVDA", "adjust": "none", "leg": "ADJ",
                    "day": "D1", "base_request_id": ""},
    "REQ-ADJ-02N": {"symbol": "TSLA", "adjust": "none", "leg": "ADJ",
                    "day": "D1", "base_request_id": ""},
    "REQ-ADJ-01R7": {"symbol": "NVDA", "adjust": "splits", "leg": "REV7",
                     "day": "D7", "base_request_id": "REQ-ADJ-01"},
    "REQ-ADJ-02R7": {"symbol": "TSLA", "adjust": "splits", "leg": "REV7",
                     "day": "D7", "base_request_id": "REQ-ADJ-02"},
    "REQ-ADJ-01R30": {"symbol": "NVDA", "adjust": "splits",
                      "leg": "REV30", "day": "D30",
                      "base_request_id": "REQ-ADJ-01"},
    "REQ-ADJ-02R30": {"symbol": "TSLA", "adjust": "splits",
                      "leg": "REV30", "day": "D30",
                      "base_request_id": "REQ-ADJ-02"},
}
EXPECTED_FIXED = {"interval": "1h", "timezone": "America/New_York",
                  "outputsize": 5000, "order": "ASC", "max_attempts": 2}
EXPECTED_WINDOWS = {
    "NVDA": ("2023-12-13T00:00:00", "2024-06-21T23:59:59"),
    "TSLA": ("2022-03-07T00:00:00", "2022-09-09T23:59:59"),
    "AAPL": ("2026-02-19T00:00:00", "2026-08-24T23:59:59"),
}


class RunnerRefusal(Exception):
    def __init__(self, tag: str, detail: str = ""):
        super().__init__(f"{tag}: {detail}" if detail else tag)
        self.tag = tag


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_pilot(repo_root: Path):
    """Import the frozen acquisition module by pinned path/hash."""
    pilot_path = Path(repo_root) / PILOT_REL
    limiter_path = Path(repo_root) / RATE_LIMITER_REL
    if not pilot_path.exists():
        raise RunnerRefusal("PILOT_SOURCE_MISSING", str(PILOT_REL))
    if _sha256_file(pilot_path) != PILOT_SHA256:
        raise RunnerRefusal("PILOT_SOURCE_HASH_MISMATCH", PILOT_REL)
    if _sha256_file(limiter_path) != RATE_LIMITER_SHA256:
        raise RunnerRefusal("PILOT_SOURCE_HASH_MISMATCH",
                            RATE_LIMITER_REL)
    spec = importlib.util.spec_from_file_location("pilot_acquire",
                                                  pilot_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pilot_acquire"] = mod
    spec.loader.exec_module(mod)
    return mod


def validate_scope(manifest: dict) -> None:
    """Scope allowlist. Runs BEFORE any preflight/transport work."""
    reqs = manifest.get("requests")
    if not isinstance(reqs, list) or not reqs:
        raise RunnerRefusal("MANIFEST_EMPTY_OR_MALFORMED")
    seen = set()
    for r in reqs:
        rid = r.get("request_id")
        if rid not in EXPECTED_REQUESTS:
            raise RunnerRefusal("UNEXPECTED_REQUEST_ID", str(rid))
        if rid in seen:
            raise RunnerRefusal("DUPLICATE_REQUEST_ID", rid)
        seen.add(rid)
        exp = EXPECTED_REQUESTS[rid]
        for k, v in exp.items():
            if r.get(k, "") != v:
                raise RunnerRefusal(
                    "SCOPE_FIELD_MISMATCH", f"{rid}.{k} != {v!r}")
        for k, v in EXPECTED_FIXED.items():
            if r.get(k) != v:
                raise RunnerRefusal(
                    "SCOPE_FIELD_MISMATCH", f"{rid}.{k} != {v!r}")
        win = EXPECTED_WINDOWS[exp["symbol"]]
        if (r.get("start_date"), r.get("end_date")) != win:
            raise RunnerRefusal("SCOPE_FIELD_MISMATCH",
                                f"{rid} window != {win}")
        if r.get("output_name") != f"{rid}.json":
            raise RunnerRefusal("SCOPE_FIELD_MISMATCH",
                                f"{rid} output_name")
    missing = set(EXPECTED_REQUESTS) - seen
    if missing:
        raise RunnerRefusal("SCOPE_INCOMPLETE",
                            ",".join(sorted(missing)))


def day_request_ids(manifest: dict, day: str) -> list[str]:
    return [r["request_id"] for r in manifest["requests"]
            if r["day"] == day]


def program_ceiling(manifest: dict) -> tuple[int, int]:
    """(expected, hard_max) program calls including one /api_usage
    preflight per execution day (max 2 attempts each). For the -63
    packet shape this must be exactly (12, 24)."""
    reqs = manifest["requests"]
    days = {r["day"] for r in reqs}
    data_expected = len(reqs)
    data_max = sum(r["max_attempts"] for r in reqs)
    usage_expected = len(days)
    usage_max = 2 * len(days)
    return (data_expected + usage_expected, data_max + usage_max)


def validate_store_path(store: Path) -> Path:
    """Refuse traversal: any '..' component, or a path that resolves
    outside the working directory via relative components. Explicit
    absolute paths without traversal are accepted (they are the
    operator's unambiguous choice); manifest output names are
    separately forced relative by the frozen validator."""
    if ".." in store.parts:
        raise RunnerRefusal("STORE_PATH_TRAVERSAL", str(store))
    if not store.is_absolute():
        resolved = (Path.cwd() / store).resolve()
        if Path.cwd().resolve() not in resolved.parents and \
                resolved != Path.cwd().resolve():
            raise RunnerRefusal("STORE_PATH_TRAVERSAL", str(store))
    return store


def check_store(store: Path, manifest_sha256: str) -> None:
    """Refuse a conflicting store; stamp a fresh one."""
    marker = store / "probe_store.json"
    if marker.exists():
        try:
            m = json.loads(marker.read_text())
        except Exception as e:
            raise RunnerRefusal("STORE_MARKER_MALFORMED", str(e)) from e
        if m.get("manifest_sha256") != manifest_sha256:
            raise RunnerRefusal("STORE_CONFLICT",
                                "store bound to another manifest")
        return
    if store.exists() and any(store.iterdir()):
        raise RunnerRefusal("STORE_FOREIGN_CONTENT",
                            "nonempty store without probe marker")
    store.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(
        {"manifest_sha256": manifest_sha256,
         "runner": "td_probe_runner_candidate_67"}, indent=2))


def store_marker_string(store: Path) -> str:
    """Canonical string form of the store marker written by
    check_store; the usage session binds its cached receipt to the
    digest of this string (defect-3 repair)."""
    marker = json.loads((Path(store) / "probe_store.json").read_text())
    return json.dumps(marker, sort_keys=True)


def run_probe_day(*, repo_root: Path, manifest_path: Path,
                  manifest_sha256: str, day: str, store_dir: Path,
                  data_transport, usage_transport, clock=None,
                  sleeper=None, limiter=None) -> dict:
    """Execute one probe day against injected transports. All
    fail-closed checks run before any transport is used."""
    clock = clock or time.time
    sleeper = sleeper or time.sleep
    if day not in RECOGNIZED_DAYS:
        raise RunnerRefusal("UNRECOGNIZED_DAY", day)
    store_dir = validate_store_path(Path(store_dir))
    raw = Path(manifest_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest_sha256:
        raise RunnerRefusal("MANIFEST_HASH_MISMATCH")
    try:
        manifest = json.loads(raw)
    except Exception as e:
        raise RunnerRefusal("MANIFEST_MALFORMED", str(e)) from e
    validate_scope(manifest)
    ids = day_request_ids(manifest, day)
    if not ids:
        raise RunnerRefusal("EMPTY_DAY_LEG", day)
    check_store(store_dir, manifest_sha256)
    # Temporal gate BEFORE transport construction/use.
    now_ms = int(clock() * 1000)
    try:
        gate_proofs = temporal_gate.check_day_eligibility(
            store_dir, manifest, day, now_ms)
    except temporal_gate.GateRefusal as e:
        raise RunnerRefusal(e.tag, str(e)) from e
    pilot = load_pilot(repo_root)
    if limiter is None:
        limiter = pilot.RollingCreditLimiter(
            8, 800, state_path=store_dir / "probe_credit_ledger.json",
            clock=clock)
    headroom = sum(r["max_attempts"] for r in manifest["requests"]
                   if r["day"] == day)
    session = DailyUsageSession(
        store_dir, day,
        AccountPreflight(usage_transport, clock=clock, sleeper=sleeper,
                         required_headroom=headroom),
        manifest_sha256=manifest_sha256,
        store_marker=store_marker_string(store_dir),
        required_headroom=headroom, clock=clock)
    driver = pilot.ManifestDriver(
        Path(manifest_path), store_dir, limiter, data_transport,
        clock=clock, sleeper=sleeper, preflight=session)
    outcomes = driver.run_day(day)
    rows = [{"request_id": o.request_id, "outcome": o.outcome,
             "attempts": o.attempts} for o in outcomes]
    ok = all(o["outcome"] in ("OK", "SKIPPED_RESUMED") for o in rows)
    return {"day": day, "ok": ok, "outcomes": rows,
            "gate_proofs": gate_proofs,
            "usage_attempts": session.preflight.attempts_made,
            "program_ceiling": program_ceiling(manifest)}


def _load_transport_module(path: Path):
    spec = importlib.util.spec_from_file_location(
        "probe_transport_module", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="probe_runner")
    ap.add_argument("--repo-root", default=str(HERE.parents[1]))
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--manifest-sha256", required=True)
    ap.add_argument("--day", required=True)
    ap.add_argument("--store", required=True)
    ap.add_argument("--transport-module", default=None,
                    help="python file defining make_data_transport() / "
                         "make_usage_transport() [/ make_clock() / "
                         "make_sleeper()]; absent = live pilot "
                         "UrllibTransport (never used by this task)")
    args = ap.parse_args(argv)
    try:
        # Scope allowlist + hash + day checks BEFORE any transport
        # construction (spec ordering requirement). run_probe_day
        # re-validates everything independently.
        if args.day not in RECOGNIZED_DAYS:
            raise RunnerRefusal("UNRECOGNIZED_DAY", args.day)
        validate_store_path(Path(args.store))
        raw = Path(args.manifest).read_bytes()
        if hashlib.sha256(raw).hexdigest() != args.manifest_sha256:
            raise RunnerRefusal("MANIFEST_HASH_MISMATCH")
        try:
            pre_manifest = json.loads(raw)
        except Exception as e:
            raise RunnerRefusal("MANIFEST_MALFORMED", str(e)) from e
        validate_scope(pre_manifest)
        if args.transport_module:
            tm = _load_transport_module(Path(args.transport_module))
            data_transport = tm.make_data_transport()
            usage_transport = tm.make_usage_transport()
            clock = tm.make_clock() if hasattr(tm, "make_clock") \
                else time.time
            sleeper = tm.make_sleeper() if hasattr(tm, "make_sleeper") \
                else time.sleep
            summary = run_probe_day(
                repo_root=Path(args.repo_root),
                manifest_path=Path(args.manifest),
                manifest_sha256=args.manifest_sha256,
                day=args.day, store_dir=Path(args.store),
                data_transport=data_transport,
                usage_transport=usage_transport,
                clock=clock, sleeper=sleeper)
        else:
            pilot = load_pilot(Path(args.repo_root))
            transport = pilot.UrllibTransport()
            summary = run_probe_day(
                repo_root=Path(args.repo_root),
                manifest_path=Path(args.manifest),
                manifest_sha256=args.manifest_sha256,
                day=args.day, store_dir=Path(args.store),
                data_transport=transport, usage_transport=transport)
    except RunnerRefusal as e:
        print(json.dumps({"refused": e.tag, "detail": str(e)}),
              file=sys.stderr)
        return 3
    except Exception as e:  # wrapper preflight abort etc. — fail closed
        print(json.dumps({"run_failed": type(e).__name__,
                          "detail": str(e)[:300]}), file=sys.stderr)
        return 4
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 4


if __name__ == "__main__":
    sys.exit(main())
