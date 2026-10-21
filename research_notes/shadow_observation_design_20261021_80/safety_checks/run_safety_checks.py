"""Offline safety suite for the TASK -80 shadow-observation design.

Runs S1-S6 against synthetic fixtures only. No live feed, no network,
no production writes: fixture runs execute inside a temp sandbox whose
"production" subtree is a byte copy of the real production files.

    S1  isolation: a fixture run writes ONLY inside the shadow namespace
    S2  production state hashes identical before/after the fixture run
    S3  static: no import of, or call into, the production harness's
        position-opening / ledger functions from the shadow runtime
    S4  every emitted record carries the cohort label + both timestamps
    S5  the hypothetical exit simulation reproduces the frozen Mode B
        stack on 3 hand-computed fixture trades
    S6  fail-closed: degraded data -> zero signals + a DEGRADED marker

Exit code 0 iff every check passes. Writes results.json and
SAFETY_CHECK_RESULTS.md next to this file.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # the suite itself must not scatter .pyc files

import ast
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PKG = Path(__file__).resolve().parents[1]
SAFETY_DIR = PKG / "safety_checks"
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(SAFETY_DIR))

import fixtures  # noqa: E402
import shadow_core  # noqa: E402

MAIN_REPO = Path.home() / "workspace" / "quality-flow-scanner-v5"
PROD_FILES = [
    "v54_forward/state.json",
    "v54_forward/forward_test.jsonl",
    "forward_test/PAUSE_NEW_ENTRIES",
    "forward_test/v54_status.json",
]

T1 = datetime(2026, 10, 5, 20, 5, tzinfo=timezone.utc)
T2 = datetime(2026, 10, 6, 0, 5, tzinfo=timezone.utc)
T3 = datetime(2026, 10, 6, 14, 5, tzinfo=timezone.utc)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_path(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def find_tracker_dir() -> Path:
    env = os.environ.get("QF_REPO_ROOT")
    candidates = ([Path(env)] if env else []) + [PKG.parents[1], MAIN_REPO]
    for cand in candidates:
        if (cand / shadow_core.PINNED_TRACKER_FILENAME).exists():
            return cand
    raise SystemExit("pinned tracker module not found in any candidate repo root")


def snapshot_tree(root: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = sha256_path(p)
    return out


def read_log(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def health(expected: List[str], degraded: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"market_ok": True, "scan_complete": True,
            "expected_symbols": list(expected),
            "degraded_symbols": list(degraded or [])}


def build_sandbox() -> Path:
    sandbox = Path(tempfile.mkdtemp(prefix="qf80_sandbox_"))
    prod = sandbox / "production"
    for rel in PROD_FILES:
        dst = prod / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(MAIN_REPO / rel, dst)
    (sandbox / "shadow_ns").mkdir()
    return sandbox


# ---------------------------------------------------------------------------
# S1 / S2 / S4 — one shared scenario: two signals, entries, exits, a
# restart in the middle, and a duplicate-signal cycle after the restart.
# ---------------------------------------------------------------------------

def scenario_s1_s2_s4(tracker_module) -> Dict[str, Any]:
    sandbox = build_sandbox()
    shadow_root = sandbox / "shadow_ns"
    before = snapshot_tree(sandbox)

    obs = shadow_core.ShadowObserver(str(shadow_root), tracker_module,
                                     clock=lambda: T1)
    a, b = fixtures.TRADE_A, fixtures.TRADE_B
    sig_a, sig_b = fixtures.signal_bar("FIXA"), fixtures.signal_bar("FIXB")
    s1 = obs.run_shadow_cycle(
        [a["row"], b["row"]],
        {"FIXA": [sig_a], "FIXB": [sig_b]},
        health(["FIXA", "FIXB"]), now=T1)
    s2 = obs.run_shadow_cycle(
        [],
        {"FIXA": [sig_a] + a["bars"], "FIXB": [sig_b] + b["bars"][:3]},
        health(["FIXA", "FIXB"]), now=T2)
    # Simulated crash: FIXA closed in cycle 2 (its close is in the log),
    # but the state file is rolled back to mid-cycle-2, when FIXA's
    # lifecycle still read "open" — as if the state save never landed.
    # On restart the observer must reconcile from the log (log is the
    # source of truth) and never emit a second FIXA close.
    state_path = shadow_root / shadow_core.STATE_FILENAME
    crashed = json.loads(state_path.read_text(encoding="utf-8"))
    fixa_sid = shadow_core.shadow_id_for(a["row"]["signal_id"])
    crashed["lifecycles"][fixa_sid]["status"] = "open"
    state_path.write_text(json.dumps(crashed), encoding="utf-8")
    # Restart: a new process object on the same namespace must resume
    # cleanly (rehydrated state) and dedup the repeated signals.
    obs2 = shadow_core.ShadowObserver(str(shadow_root), tracker_module,
                                      clock=lambda: T3)
    s3 = obs2.run_shadow_cycle(
        [a["row"], b["row"]],
        {"FIXB": [sig_b] + b["bars"]},
        health(["FIXB"]), now=T3)

    after = snapshot_tree(sandbox)
    records = read_log(shadow_root / shadow_core.LOG_FILENAME)
    shutil.rmtree(sandbox, ignore_errors=True)
    return {"before": before, "after": after, "records": records,
            "summaries": [s1, s2, s3]}


def check_s1(ctx: Dict[str, Any]) -> Dict[str, Any]:
    changed = sorted(p for p in set(ctx["before"]) | set(ctx["after"])
                     if ctx["before"].get(p) != ctx["after"].get(p))
    outside = [p for p in changed if not p.startswith("shadow_ns/")]
    return {"pass": bool(changed) and not outside,
            "details": {"changed_paths": changed,
                        "writes_outside_shadow_namespace": outside}}


def check_s2(ctx: Dict[str, Any]) -> Dict[str, Any]:
    prod_before = {p: h for p, h in ctx["before"].items()
                   if p.startswith("production/")}
    prod_after = {p: h for p, h in ctx["after"].items()
                  if p.startswith("production/")}
    return {"pass": prod_before == prod_after and bool(prod_before),
            "details": {"production_replica_files": prod_before,
                        "identical_after_run": prod_before == prod_after}}


def check_s4(ctx: Dict[str, Any]) -> Dict[str, Any]:
    records = ctx["records"]
    problems: List[str] = []
    for i, rec in enumerate(records):
        if rec.get("cohort") != shadow_core.COHORT_LABEL:
            problems.append(f"record {i}: cohort label missing/wrong")
        if rec.get("counts_as_trade") is not False:
            problems.append(f"record {i}: counts_as_trade is not False")
        if not rec.get("record_kind") or not rec.get("logged_at"):
            problems.append(f"record {i}: record_kind/logged_at missing")
    signals = [r for r in records if r["record_kind"] == "shadow_signal"]
    for rec in signals:
        for field in ("signal_bar_start_at", "signal_bar_close_at",
                      "detected_at_utc"):
            if not rec.get(field):
                problems.append(f"signal {rec.get('shadow_id')}: {field} missing")
            else:
                datetime.fromisoformat(rec[field])  # must parse
        if not str(rec.get("shadow_id", "")).startswith("shadow:"):
            problems.append(f"signal id outside shadow namespace: {rec.get('shadow_id')}")
    closes_by_id: Dict[str, int] = {}
    for r in records:
        if r["record_kind"] == "shadow_close":
            closes_by_id[r["shadow_id"]] = closes_by_id.get(r["shadow_id"], 0) + 1
    if any(n != 1 for n in closes_by_id.values()):
        problems.append(f"duplicate close records after crash+restart: {closes_by_id}")
    counts = {
        "records_total": len(records),
        "shadow_signal": len(signals),
        "shadow_close": sum(1 for r in records if r["record_kind"] == "shadow_close"),
        "closes_by_shadow_id": closes_by_id,
        "crash_reconcile": "state rolled back mid-close before restart; "
                           "log-wins reconcile must yield exactly one close per id",
        "shadow_cycle": sum(1 for r in records if r["record_kind"] == "shadow_cycle"),
        "dedup_after_restart_new_signals": ctx["summaries"][2]["new_signals"],
    }
    ok = (not problems and counts["shadow_signal"] == 2
          and counts["shadow_close"] == 2 and counts["shadow_cycle"] == 3
          and counts["dedup_after_restart_new_signals"] == 0)
    return {"pass": ok, "details": {"counts": counts, "problems": problems}}


# ---------------------------------------------------------------------------
# S3 — static isolation of the shadow runtime modules.
# ---------------------------------------------------------------------------

FORBIDDEN_MODULES = {
    "v54_forward_harness",   # the production harness (opening/ledger/state)
    "v54_forward_log",       # the production log writer
    "v54_mtf_paper", "v54_fvg_sidecar", "v54_lonewolf_overlay",
    "subprocess", "socket", "requests", "urllib",
}
# Function names owned by the production harness / production log that
# stage signals, open positions into the production ledger, persist
# production state, or publish. (tracker.open_position is deliberately
# NOT in this set: it is the pinned tracker's own API, reachable only
# on the shadow's in-memory instance — the harness module that also
# calls it is never imported, which is what this check proves.)
FORBIDDEN_CALLS = {
    "run_cycle", "run_once", "_process_symbol", "save_state", "load_state",
    "blank_state", "pause_control_state", "publish_snapshot",
    "write_github_snapshot", "observer_append_assessment", "log_signal",
    "log_event", "log_close", "ForwardLog",
}
FORBIDDEN_LITERALS = [
    "v54_forward", "forward_test", "PAUSE_NEW_ENTRIES",
    "RESUME_NEW_ENTRIES", "ENTRIES_RESUME",
]
ALLOWED_NON_STDLIB = {
    "shadow_core": set(),
    "shadow_runner": {"shadow_core", "v54_engine", "v54_rules",
                      "v54_exit_tracker", "v54_universe_x2",
                      "hybrid_exit_test", "masterscanner_api",
                      "scanner_rules"},
}


def _imports_and_calls(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports, calls = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                calls.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                calls.add(fn.attr)
    return imports, calls


def check_s3(tracker_dir: Path) -> Dict[str, Any]:
    stdlib = set(sys.stdlib_module_names)
    problems: List[str] = []
    per_file: Dict[str, Any] = {}
    for name in ("shadow_core", "shadow_runner"):
        path = PKG / f"{name}.py"
        imports, calls = _imports_and_calls(path)
        non_stdlib = imports - stdlib
        bad_imports = sorted(imports & FORBIDDEN_MODULES)
        unlisted = sorted(non_stdlib - ALLOWED_NON_STDLIB[name])
        bad_calls = sorted(calls & FORBIDDEN_CALLS)
        text = path.read_text(encoding="utf-8")
        bad_literals = [lit for lit in FORBIDDEN_LITERALS if lit in text]
        per_file[name] = {"imports": sorted(imports),
                          "non_stdlib_imports": sorted(non_stdlib),
                          "forbidden_imports": bad_imports,
                          "unlisted_imports": unlisted,
                          "forbidden_calls": bad_calls,
                          "forbidden_literals": bad_literals}
        if bad_imports or unlisted or bad_calls or bad_literals:
            problems.append(f"{name}: imports={bad_imports} unlisted={unlisted} "
                            f"calls={bad_calls} literals={bad_literals}")
    # The one production module the core executes must itself be
    # I/O-free: verify its imports are stdlib-only.
    tracker_imports, _ = _imports_and_calls(
        tracker_dir / shadow_core.PINNED_TRACKER_FILENAME)
    tracker_non_stdlib = sorted(tracker_imports - stdlib)
    if tracker_non_stdlib:
        problems.append(f"pinned tracker imports non-stdlib: {tracker_non_stdlib}")
    per_file["v54_exit_tracker (pinned, executed by core)"] = {
        "imports": sorted(tracker_imports), "non_stdlib_imports": tracker_non_stdlib}
    return {"pass": not problems,
            "details": {"per_file": per_file, "problems": problems,
                        "note": "open_position is reachable only as the pinned "
                                "tracker's method on the shadow's own in-memory "
                                "instance; the production harness module is never "
                                "imported, so none of its functions are callable."}}


# ---------------------------------------------------------------------------
# S5 — frozen-stack fidelity on hand-computed fixtures.
# ---------------------------------------------------------------------------

def _close_matches(close: Dict[str, Any], expected: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    mapping = {"reason": "exit_reason"}
    for key, want in expected.items():
        got = close.get(mapping.get(key, key))
        if isinstance(want, float):
            if got is None or round(float(got), 4) != round(want, 4):
                errs.append(f"{key}: got {got}, want {want}")
        elif got != want:
            errs.append(f"{key}: got {got!r}, want {want!r}")
    return errs


def _run_trade(tracker_module, trade: Dict[str, Any],
               split_at: Optional[int] = None) -> Dict[str, Any]:
    sandbox = Path(tempfile.mkdtemp(prefix="qf80_trade_"))
    root = sandbox / "shadow_ns"
    obs = shadow_core.ShadowObserver(str(root), tracker_module, clock=lambda: T1)
    sym = trade["symbol"]
    sig = fixtures.signal_bar(sym)
    obs.run_shadow_cycle([trade["row"]], {sym: [sig]},
                         health([sym]), now=T1)
    bars = trade["bars"]
    mid_close_count: Optional[int] = None
    if split_at is not None:
        obs.run_shadow_cycle([], {sym: [sig] + bars[:split_at]},
                             health([sym]), now=T2)
        mid = read_log(root / shadow_core.LOG_FILENAME)
        mid_close_count = sum(1 for r in mid
                              if r["record_kind"] == "shadow_close")
        obs.run_shadow_cycle([], {sym: [sig] + bars}, health([sym]), now=T3)
    else:
        obs.run_shadow_cycle([], {sym: [sig] + bars}, health([sym]), now=T2)
    records = read_log(root / shadow_core.LOG_FILENAME)
    shutil.rmtree(sandbox, ignore_errors=True)
    closes = [r for r in records if r["record_kind"] == "shadow_close"]
    events = [r for r in records if r["record_kind"] == "shadow_event"]
    return {"close": closes[-1] if closes else None, "events": events,
            "mid_close_count": mid_close_count}


def check_s5(tracker_module) -> Dict[str, Any]:
    details: Dict[str, Any] = {}
    all_ok = True
    for trade, split in ((fixtures.TRADE_A, None), (fixtures.TRADE_B, 3),
                         (fixtures.TRADE_C, None)):
        out = _run_trade(tracker_module, trade, split_at=split)
        errs: List[str] = []
        if out["close"] is None:
            errs.append("no shadow_close record produced")
        else:
            errs += _close_matches(out["close"], trade["expected_close"])
        ev = [(e.get("event"), e.get("bar")) for e in out["events"]]
        if trade is fixtures.TRADE_A:
            kinds = [k for k, _ in ev]
            if kinds != ["opened", "closed"]:
                errs.append(f"event sequence {kinds}, want [opened, closed]")
        if trade is fixtures.TRADE_B:
            if ("profit_protect_armed", trade["expected_arm_bar"]) not in ev:
                errs.append(f"missing arm at {trade['expected_arm_bar']}: {ev}")
            if ("tp1_taken", trade["expected_tp1_bar"]) not in ev:
                errs.append(f"missing tp1 at {trade['expected_tp1_bar']}: {ev}")
            if any(k == "exit_signaled" and b == trade["expected_tp1_bar"]
                   for k, b in ev):
                errs.append("EXIT was processed on the TP1 bar (frozen rule: "
                            "no EXIT check on the TP1 bar)")
            if out["mid_close_count"] != 0:
                errs.append("a close existed before the pending EXIT filled "
                            "at the next bar's open")
        details[trade["symbol"]] = {"errors": errs,
                                    "close": out["close"],
                                    "events": ev}
        all_ok = all_ok and not errs
    return {"pass": all_ok, "details": details}


# ---------------------------------------------------------------------------
# S6 — fail-closed on degraded data.
# ---------------------------------------------------------------------------

def check_s6(tracker_module) -> Dict[str, Any]:
    sandbox = Path(tempfile.mkdtemp(prefix="qf80_s6_"))
    root = sandbox / "shadow_ns"
    obs = shadow_core.ShadowObserver(str(root), tracker_module, clock=lambda: T1)
    row = fixtures.TRADE_D_ROW
    sig = fixtures.signal_bar("FIXD")
    s1 = obs.run_shadow_cycle([row], {"FIXD": [sig]},
                              health(["FIXD"], degraded=["FIXD"]), now=T1)
    mid = read_log(root / shadow_core.LOG_FILENAME)
    s2 = obs.run_shadow_cycle([row], {"FIXD": [sig]}, health(["FIXD"]), now=T2)
    records = read_log(root / shadow_core.LOG_FILENAME)
    shutil.rmtree(sandbox, ignore_errors=True)
    signals_mid = sum(1 for r in mid if r["record_kind"] == "shadow_signal")
    cycles_mid = [r for r in mid if r["record_kind"] == "shadow_cycle"]
    signals_end = sum(1 for r in records if r["record_kind"] == "shadow_signal")
    ok = (s1["status"] == "DEGRADED" and signals_mid == 0
          and len(cycles_mid) == 1 and cycles_mid[0]["status"] == "DEGRADED"
          and s2["status"] == "HEALTHY" and signals_end == 1)
    return {"pass": ok,
            "details": {"degraded_cycle_status": s1["status"],
                        "signals_during_degraded_cycle": signals_mid,
                        "degraded_markers": len(cycles_mid),
                        "signals_after_recovery": signals_end,
                        "recovery_cycle_status": s2["status"]}}


# ---------------------------------------------------------------------------

def main() -> int:
    tracker_dir = find_tracker_dir()
    tracker_module = shadow_core.load_pinned_tracker(str(tracker_dir))
    real_before = {rel: sha256_path(MAIN_REPO / rel) for rel in PROD_FILES}

    results: Dict[str, Any] = {
        "suite": "shadow-observation safety checks (TASK -80)",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "tracker": {
            "file": str(tracker_dir / shadow_core.PINNED_TRACKER_FILENAME),
            "sha256_verified": shadow_core.sha256_file(
                str(tracker_dir / shadow_core.PINNED_TRACKER_FILENAME)),
            "pin": shadow_core.PINNED_TRACKER_SHA256,
        },
        "checks": {},
    }

    ctx = scenario_s1_s2_s4(tracker_module)
    results["checks"]["S1_isolation"] = check_s1(ctx)
    results["checks"]["S2_production_hashes"] = check_s2(ctx)
    results["checks"]["S3_static_no_production_opening"] = check_s3(tracker_dir)
    results["checks"]["S4_labeling_and_timestamps"] = check_s4(ctx)
    results["checks"]["S5_frozen_stack_fidelity"] = check_s5(tracker_module)
    results["checks"]["S6_fail_closed_degraded"] = check_s6(tracker_module)

    real_after = {rel: sha256_path(MAIN_REPO / rel) for rel in PROD_FILES}
    results["real_production_files_informational"] = {
        "note": "The production harness is LIVE and may update these "
                "files on its own hourly cycle; recorded for the record, "
                "not asserted. The binding S2 assertion is over the "
                "byte-identical sandbox replica.",
        "before": real_before, "after": real_after,
        "unchanged_during_suite": real_before == real_after,
    }
    results["all_pass"] = all(c["pass"] for c in results["checks"].values())

    (SAFETY_DIR / "results.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8")
    lines = [
        "# SAFETY CHECK RESULTS — TASK -80 shadow-observation design",
        "",
        f"Run: {results['run_at_utc']} · Python {results['python']} · "
        f"pinned tracker sha256 verified: {results['tracker']['sha256_verified']}",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    labels = {
        "S1_isolation": "S1 — writes only inside the shadow namespace",
        "S2_production_hashes": "S2 — production state hashes identical before/after",
        "S3_static_no_production_opening": "S3 — no import/call path to production position-opening",
        "S4_labeling_and_timestamps": "S4 — cohort label + both timestamps on every record",
        "S5_frozen_stack_fidelity": "S5 — Mode B simulation matches hand-computed fixtures",
        "S6_fail_closed_degraded": "S6 — degraded data: zero signals + DEGRADED marker",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | "
                     f"{'PASS' if results['checks'][key]['pass'] else 'FAIL'} |")
    lines += [
        "",
        f"**Overall: {'PASS (6/6)' if results['all_pass'] else 'FAIL'}** — "
        "full machine-readable detail in results.json.",
        "",
        "S5 hand-computed expectations (risk = entry - stop = 5.00 in all "
        "three): FIXA stop-out blended -1.0000R (exit at the 95.00 stop "
        "price); FIXB TP1 at B2 (partial +1.0000R) then runner-exit at the "
        "next bar's open 109.00 (runner +1.8000R) for blended +1.9000R, with "
        "the scanner EXIT on the TP1 bar correctly ignored and no close "
        "before the pending fill; FIXC 30-bar time exit at 101.00 for "
        "+0.2000R, never armed (max favorable +0.40R).",
        "",
        "S2's binding assertion is over a byte-identical sandbox replica of "
        "the production files (the live harness may legitimately update "
        "the real files on its own cycle; the real hashes before/after "
        "the suite are recorded in results.json as informational).",
    ]
    (SAFETY_DIR / "SAFETY_CHECK_RESULTS.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")

    for key, label in labels.items():
        print(f"{'PASS' if results['checks'][key]['pass'] else 'FAIL'}  {label}")
        if not results['checks'][key]['pass']:
            print(json.dumps(results['checks'][key]['details'], indent=2,
                             default=str)[:3000])
    print("ALL PASS" if results["all_pass"] else "SOME CHECKS FAILED")
    return 0 if results["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
