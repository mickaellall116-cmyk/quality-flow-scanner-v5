#!/usr/bin/env python3
"""
test_shadow_signal_observer.py — acceptance suite for the -80
shadow successor (signal-only stage), mapped to the assignment's
fixtures (Issue #1 comment 6353427339):

  A  clean novel post-T0 signal recorded once
  B  old (pre-T0) signal refused
  C  unavailable market frame fails closed
  D  incomplete universe / partial 4H bar / incorrect timezone
     fail closed
  E  interrupted append / restart does not lose or duplicate
  F  production hashes / sentinels unchanged in sandbox

Plus the structural gates: frozen T0, fail-closed health
defaults, pin verification, authorization-before-data, and
module/transitive import isolation. All synthetic; no network;
the live adapter is never constructed except behind the
authorization refusal it must hit first.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
PKG = HERE.parent
sys.path.insert(0, str(PKG))
import shadow_signal_core as core  # noqa: E402
import shadow_signal_runner as runner  # noqa: E402

RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name,
          detail if not cond else "")


T0 = datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 22, 18, 0, tzinfo=timezone.utc)


def fixed_clock():
    return NOW


def sig(signal_id="sig-1", symbol="NVDA",
        start="2026-10-22T09:30:00-04:00",
        close="2026-10-22T13:30:00-04:00"):
    return {
        "signal_id": signal_id, "symbol": symbol,
        "signal_bar_start_at": start, "signal_bar_close_at": close,
        "v54_grade": "B", "stop": 100.0, "tp1": 110.0,
        "market_gate": "CAUTION", "theme": "Forward-UX51",
        "timeframe": "4h", "state": "BUY NOW",
    }


HEALTHY = {"market_ok": True, "scan_complete": True,
           "degraded_symbols": [], "expected_symbols": ["NVDA"]}


def read_log(root):
    path = Path(root) / core.LOG_FILENAME
    if not path.exists():
        return []
    return [json.loads(ln) for ln in
            path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def kinds(root):
    return [r["record_kind"] for r in read_log(root)]


def sandbox_repo(tmp):
    """A repo dir whose six pinned names carry known bytes; returns
    (dir, pins) so the suite can pin honestly without the live
    stack."""
    repo = Path(tmp) / "repo"
    repo.mkdir()
    pins = {}
    for name in runner.PINNED_STACK:
        data = f"synthetic {name}\n".encode()
        (repo / name).write_bytes(data)
        pins[name] = hashlib.sha256(data).hexdigest()
    return repo, pins


def main():
    tmp = tempfile.mkdtemp(prefix="shadow_succ_")

    # ---------- A: novel post-T0 signal, recorded exactly once ----
    root = str(Path(tmp) / "a")
    obs = core.SignalObserver(root, T0, clock=fixed_clock)
    s = obs.run_cycle([sig()], HEALTHY, now=NOW)
    case("A1_recorded_once",
         s["status"] == "HEALTHY" and s["new_signals_recorded"] == 1
         and kinds(root).count("shadow_signal") == 1, str(s))
    rec = [r for r in read_log(root)
           if r["record_kind"] == "shadow_signal"][0]
    case("A2_record_labels",
         rec["cohort"] == "SHADOW_OBSERVATION"
         and rec["counts_as_trade"] is False
         and rec["shadow_id"] == "shadow:sig-1"
         and rec["launch_t0_utc"] == T0.isoformat(), str(rec))
    s = obs.run_cycle([sig()], HEALTHY, now=NOW)
    case("A3_idempotent_same_process",
         s["new_signals_recorded"] == 0
         and s["duplicates_skipped"] == 1
         and kinds(root).count("shadow_signal") == 1, str(s))

    # ---------- B: pre-T0 signal refused (no backfill) ------------
    old = sig("sig-old", start="2026-10-21T09:30:00-04:00",
              close="2026-10-21T13:30:00-04:00")
    s = obs.run_cycle([old], HEALTHY, now=NOW)
    ref = [r for r in read_log(root)
           if r["record_kind"] == "shadow_refusal"]
    case("B1_prelaunch_refused",
         s["new_signals_recorded"] == 0 and len(ref) == 1
         and ref[0]["reason"] == "PRELAUNCH_SIGNAL", str(s))

    # ---------- C: market frame unavailable fails closed ----------
    root_c = str(Path(tmp) / "c")
    obs_c = core.SignalObserver(root_c, T0, clock=fixed_clock)
    s = obs_c.run_cycle([sig()], {"market_ok": False,
                                  "scan_complete": True,
                                  "degraded_symbols": []}, now=NOW)
    case("C1_blind_cycle_degraded_no_signals",
         s["status"] == "DEGRADED"
         and "MARKET_FRAME_NOT_OK" in s["degraded_reasons"]
         and kinds(root_c).count("shadow_signal") == 0, str(s))
    # Health keys ABSENT default to not-ok (the B2 regression guard:
    # -80 defaulted market_ok to True).
    s = obs_c.run_cycle([sig()], {}, now=NOW)
    case("C2_absent_health_fails_closed",
         s["status"] == "DEGRADED"
         and "MARKET_FRAME_NOT_OK" in s["degraded_reasons"]
         and "SCAN_INCOMPLETE" in s["degraded_reasons"], str(s))

    # ---------- D: incomplete / partial / wrong tz ----------------
    s = obs_c.run_cycle([sig()], {"market_ok": True,
                                  "scan_complete": False,
                                  "degraded_symbols": []}, now=NOW)
    case("D1_incomplete_scan_degraded",
         s["status"] == "DEGRADED"
         and kinds(root_c).count("shadow_signal") == 0, str(s))
    root_d = str(Path(tmp) / "d")
    obs_d = core.SignalObserver(root_d, T0, clock=fixed_clock)
    partial = sig("sig-partial", start="2026-10-22T13:30:00-04:00",
                  close="2026-10-22T17:30:00-04:00")  # closes after NOW
    naive = sig("sig-naive", start="2026-10-22T09:30:00",
                close="2026-10-22T13:30:00")
    offgrid = sig("sig-offgrid", start="2026-10-22T10:30:00-04:00",
                  close="2026-10-22T14:30:00-04:00")
    s = obs_d.run_cycle([partial, naive, offgrid, sig("sig-ok")],
                        HEALTHY, now=NOW)
    reasons = {r["source_signal_id"]: r["reason"]
               for r in read_log(root_d)
               if r["record_kind"] == "shadow_refusal"}
    case("D2_partial_bar_refused",
         reasons.get("sig-partial") == "PARTIAL_BAR_NOT_CLOSED",
         str(reasons))
    case("D3_naive_tz_refused",
         reasons.get("sig-naive") == "TZ_NAIVE_OR_UNPARSEABLE_STAMPS",
         str(reasons))
    case("D4_offgrid_refused",
         reasons.get("sig-offgrid") == "OFF_GRID_BAR_START",
         str(reasons))
    case("D5_valid_signal_still_recorded",
         s["new_signals_recorded"] == 1
         and kinds(root_d).count("shadow_signal") == 1, str(s))

    # ---------- E: restart + torn tail ----------------------------
    obs_d2 = core.SignalObserver(root_d, T0, clock=fixed_clock)
    s = obs_d2.run_cycle([sig("sig-ok")], HEALTHY, now=NOW)
    case("E1_restart_no_duplicate",
         s["duplicates_skipped"] == 1
         and kinds(root_d).count("shadow_signal") == 1, str(s))
    # Simulate a crash mid-append: a torn final line.
    with open(Path(root_d) / core.LOG_FILENAME, "a",
              encoding="utf-8") as fh:
        fh.write('{"record_kind": "shadow_signal", "shadow_id": '
                 '"shadow:sig-torn", "source_sig')
    obs_d3 = core.SignalObserver(root_d, T0, clock=fixed_clock)
    torn = sig("sig-torn", start="2026-10-22T13:30:00-04:00",
               close="2026-10-22T17:30:00-04:00")
    s = obs_d3.run_cycle([torn], HEALTHY,
                         now=datetime(2026, 10, 22, 22, 0,
                                      tzinfo=timezone.utc))
    recs = read_log(root_d)  # every line must parse after recovery
    case("E2_torn_tail_recovered_recorded_once",
         s["new_signals_recorded"] == 1
         and sum(1 for r in recs
                 if r.get("shadow_id") == "shadow:sig-torn") == 1
         and any(r["record_kind"] == "shadow_recovery"
                 for r in recs), str(s))
    case("E3_log_fully_parseable_after_recovery",
         all(isinstance(r, dict) for r in recs))

    # ---------- frozen T0 ------------------------------------------
    try:
        core.SignalObserver(root_d, datetime(2026, 10, 23,
                                             tzinfo=timezone.utc),
                            clock=fixed_clock)
        case("G1_t0_mismatch_refused", False, "no raise")
    except core.ShadowError as e:
        case("G1_t0_mismatch_refused", "frozen" in str(e), str(e))
    obs_d4 = core.SignalObserver(root_d, T0, clock=fixed_clock)
    case("G2_same_t0_reopens", obs_d4.t0 == T0)

    # ---------- F: production sandbox untouched --------------------
    prod = Path(tmp) / "prod"
    prod.mkdir()
    (prod / "PAUSE_NEW_ENTRIES").write_text("paused\n")
    (prod / "state.json").write_text('{"runs": 731}\n')

    def tree_hashes(base):
        return {str(p.relative_to(base)):
                hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(Path(base).rglob("*")) if p.is_file()}

    before = tree_hashes(prod)
    root_f = str(Path(tmp) / "f")
    obs_f = core.SignalObserver(root_f, T0, clock=fixed_clock)
    obs_f.run_cycle([sig()], HEALTHY, now=NOW)
    obs_f.run_cycle([sig()], {"market_ok": False}, now=NOW)
    case("F1_production_hashes_unchanged", tree_hashes(prod) == before)
    written = {p.name for p in Path(root_f).iterdir()}
    case("F2_writes_contained_in_shadow_root",
         written == {core.LOG_FILENAME, core.MANIFEST_FILENAME},
         str(written))

    # ---------- pins + authorization gate (runner) -----------------
    repo, pins = sandbox_repo(tmp)
    saved = runner.PINNED_STACK
    runner.PINNED_STACK = pins
    try:
        digests = runner.verify_pins(str(repo))
        case("H1_pins_pass_on_matching_stack",
             digests == pins, str(digests))
        (repo / "v54_rules.py").write_bytes(b"tampered\n")
        try:
            runner.verify_pins(str(repo))
            case("H2_pin_mismatch_refused", False, "no raise")
        except core.ShadowError as e:
            case("H2_pin_mismatch_refused",
                 "pin mismatch" in str(e), str(e))
        # Authorization fires BEFORE any adapter fetch: live main()
        # with no LAUNCH_AUTHORIZED.json must raise and the fixture
        # adapter must stay untouched; nothing is written.
        (repo / "v54_rules.py").write_bytes(b"synthetic v54_rules.py\n")
        adapter = runner.FixtureAdapter([sig()], HEALTHY)
        root_j = str(Path(tmp) / "j")
        try:
            runner._require_launch_authorization(root_j, T0)
            case("J1_live_mode_requires_authorization", False,
                 "no raise")
        except core.ShadowError as e:
            case("J1_live_mode_requires_authorization",
                 "LAUNCH_AUTHORIZED" in str(e)
                 and adapter.fetch_calls == 0
                 and not Path(root_j).exists(), str(e))
        # observe_once: pins verified before the single fetch.
        s = runner.observe_once(str(repo), str(Path(tmp) / "j2"),
                                T0, adapter)
        case("J2_observe_once_one_fetch_after_pins",
             adapter.fetch_calls == 1
             and s["new_signals_recorded"] == 1, str(s))
    finally:
        runner.PINNED_STACK = saved

    # ---------- import isolation (subprocess) -----------------------
    probe = (
        "import sys; sys.path.insert(0, %r);"
        "import shadow_signal_core, shadow_signal_runner;"
        "bad = [m for m in ('v54_engine','v54_rules','scanner_rules',"
        "'masterscanner_api','v54_universe_x2','hybrid_exit_test',"
        "'v54_exit_tracker','v54_forward_harness','pine_backtest')"
        " if m in sys.modules];"
        "print('LOADED:' + ','.join(bad) if bad else 'CLEAN')"
    ) % str(PKG)
    out = subprocess.run([sys.executable, "-B", "-c", probe],
                         capture_output=True, text=True)
    case("I1_no_production_imports",
         out.stdout.strip() == "CLEAN",
         out.stdout + out.stderr)

    # ---------- dry-run main() smoke (subprocess) --------------------
    fixture = {"candidates": [sig()], "health": HEALTHY}
    fx = Path(tmp) / "fixture.json"
    fx.write_text(json.dumps(fixture), encoding="utf-8")
    root_k = str(Path(tmp) / "k")
    real_repo = os.environ.get(
        "QF_REPO_ROOT",
        str(Path.home() / "workspace" / "quality-flow-scanner-v5"))
    out = subprocess.run(
        [sys.executable, "-B", str(PKG / "shadow_signal_runner.py"),
         "--repo-root", real_repo, "--root", root_k,
         "--t0", "2026-10-22T00:00:00+00:00",
         "--dry-run", "--fixture", str(fx)],
        capture_output=True, text=True)
    case("K1_dry_run_main_end_to_end",
         out.returncode == 0
         and kinds(root_k).count("shadow_signal") == 1,
         out.stdout[-400:] + out.stderr[-400:])

    n_pass = sum(1 for _, ok in RESULTS if ok)
    print(f"{n_pass}/{len(RESULTS)} checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
