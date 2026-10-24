#!/usr/bin/env python3
"""Preflight verifier — QF-EQUITY43-FEED-MEASUREMENT-PILOT-20261024-22.

Recomputes, from the bytes in front of it (this package), everything the
preflight manifest claims:
  1. SHA-256 of every delivered file vs PREFLIGHT_MANIFEST.json.
  2. Bundle pins (observer / staging gate / calendar) vs the frozen -21
     protocol values recorded in the manifest.
  3. Schedule census: imports the delivered runner, rebuilds the frozen
     schedule from the delivered run_manifest.json, counts actions by
     kind, compares to the manifest census.
  4. Cap constants in the delivered runner (149/day, 800 total).
Usage: python3 verify_preflight.py [package_root]   (default: .)
Exit 0 = all checks PASS. No network, no credentials, no market data."""
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name
          + (f" — {detail}" if detail else ""))
    if not cond:
        fails.append(name)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


man_path = os.path.join(ROOT, "PREFLIGHT_MANIFEST.json")
manifest = json.load(open(man_path))

bad = []
for rel, expected in sorted(manifest["files"].items()):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p) or sha(p) != expected:
        bad.append(rel)
check(f"file hashes ({len(manifest['files'])} files)", not bad,
      f"mismatched: {bad}" if bad else "all match")

for name, rel in (("observer", "bundle/observer/fwd_observer17.py"),
                  ("staging_gate", "bundle/staging_gate19.py"),
                  ("calendar", "bundle/calendar/"
                               "session_table_extended_candidate.json")):
    got = sha(os.path.join(ROOT, rel))
    check(f"bundle pin {name}", got == manifest["bundle_pins"][name],
          got)

spec = importlib.util.spec_from_file_location(
    "pilot_runner_verify", os.path.join(ROOT, "source", "pilot_runner.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
cfg = json.load(open(os.path.join(ROOT, "source", "run_manifest.json")))
census = Counter(a["kind"] for a in runner.build_schedule(cfg))
expected_census = {k: v for k, v in manifest["schedule_census"].items()
                   if k != "total_actions"}
check("schedule census by kind", dict(census) == expected_census,
      f"{dict(census)}")
check("schedule census total",
      sum(census.values()) == manifest["schedule_census"]["total_actions"],
      f"total={sum(census.values())}")
state = runner.init_state(cfg)
check("expected bars", len(state["bars"]) == manifest["expected_bars"],
      f"bars={len(state['bars'])}")
check("cap constants", runner.DAY_CALL_CAP == 149
      and runner.TOTAL_CALL_CAP == 800,
      f"day={runner.DAY_CALL_CAP} total={runner.TOTAL_CALL_CAP}")
check("symbols pinned", cfg["symbols"] == manifest["symbols"],
      f"{cfg['symbols']}")
check("sessions pinned", cfg["sessions"] == manifest["sessions"],
      f"{cfg['sessions']}")

# STOP 1 cross-checks: manifest session_closes must equal the delivered
# bundle calendar, and the built schedule must derive the final bar's
# polls from the 16:00 close (fin 16:30 ET, first ladder 16:01 ET).
cal = json.load(open(os.path.join(
    ROOT, "bundle", "calendar",
    "session_table_extended_candidate.json")))
cal_closes = {s["date"]: s["close"] for s in cal["sessions"]}
check("session_closes match bundle calendar",
      all(cal_closes.get(d) == c
          for d, c in manifest["session_closes"].items()),
      f"{manifest['session_closes']}")
_by_id = {a["id"]: a for a in runner.build_schedule(cfg)}
spot = _by_id.get("fin|2026-10-28|SPY|15:30", {}).get("due") == \
    "2026-10-28T20:30:00+00:00" and \
    _by_id.get("ladder|2026-10-28|SPY|15:30|60", {}).get("due") == \
    "2026-10-28T20:01:00+00:00" and \
    _by_id.get("fin|2026-10-28|SPY|09:30", {}).get("due") == \
    "2026-10-28T15:00:00+00:00"
check("schedule derives 15:30 bar from 16:00 close (STOP 1)", spot)

# r2.1 residual 1 cross-check: every revision batch is preceded, the
# same UTC date, by a 07:55 ET pre_revision usage action (the same-day
# baseline source for the provider gate).
_sched21 = runner.build_schedule(cfg)
_pre21 = [a for a in _sched21 if a.get("tag") == "pre_revision"]
spot21 = len(_pre21) == 5 and \
    _by_id.get("usage|2026-10-27|pre_revision", {}).get("due") == \
    "2026-10-27T11:55:00+00:00" and \
    _by_id.get("usage|2026-11-02|pre_revision", {}).get("due") == \
    "2026-11-02T12:55:00+00:00" and \
    all(p["due"] < r["due"] for p in _pre21 for r in _sched21
        if r["kind"] == "revision" and r["due"][:10] == p["due"][:10])
check("pre_revision baseline precedes every revision batch (r2.1)",
      spot21)

# r2.2 (ruling 6387473294): the startup invariant exists in the
# delivered runner, a fresh build validates clean against itself, and
# a single mutated due is caught by the validator.
_inv_ok = hasattr(runner, "startup_state") and \
    hasattr(runner, "validate_state_against_build")
_fresh_v = runner.init_state(cfg)
_mut_v = runner.init_state(cfg)
_mut_v["actions"][3]["due"] = "2026-10-26T00:00:00+00:00"
check("startup invariant validates state vs fresh build (r2.2)",
      _inv_ok and runner.validate_state_against_build(_fresh_v, cfg)
      == [] and runner.validate_state_against_build(_mut_v, cfg) != [])

print("VERIFY", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
