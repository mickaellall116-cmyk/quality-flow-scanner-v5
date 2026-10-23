"""QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13 — successor to -12 STOP_PREFLIGHT.

Governing text: Issue #1 comment 6375433659 (ChatGPT independent adjudication
of -12, package 861f5e2 — that record is IMMUTABLE and is not re-run here).
Ruling A: prospective, versioned canonical candidate-processing order
(symbol, signal_idx) frozen in BOTH the C0 reference control and the stack —
a simulator-consistency repair, not a strategy change. Ruling B: the four
right-censored terminal-open candidates (CRM, SHOP, MRNA, PFE) must enter the
same time-local selection as any candidate; if taken they are held to the
W_DEV cutoff and marked into equity at the last-completed-bar as-of mark; if
rejected, their exact skip reason is ledgered. No fictional exits, no forced
liquidation, no hindsight selection.

Ordered fail-closed operation:
  P0  pins (successor engine [canonical pin + censoring treatment], pristine
      -09 fork, frozen originals, calendar, manifests, archive SHA256SUMS on
      a fresh clone, PAUSED production) + frozen experiment config pin.
  P1  receipt chains (child chain re-walked in full; roots recomputed;
      pilot DEV receipts field-verified). HO content never parsed.
  P2  per-name G1-G6 adjudication on the 43 DEV legs ONLY; PFE ruling and
      G4/VBASIS disposition carried from -12 (disclosed, NOT waived).
  P3  independent replay of the -09 fixtures on three trees (original 0/5,
      pristine fork 5/5, successor 5/5) + the -13 censoring fixture
      (frozen construction VIOLATED / successor HOLDS).
  P4  real-input parity (grid, aggregation incl. SessionVWAP, per-candidate
      formula parity for the 586 closed candidates; censored generation
      cross-checked field-by-field against the -12 census); canonical order
      applied; C0 fidelity TRADE-BY-TRADE (taken identities, per-trade risk
      dollars and exit cash flows, cap/risk skips, terminal inventory,
      equity) between the successor control and the successor stack, incl.
      the terminal-open accounting guard per censored candidate; seeded
      permutation invariance.
  P5  ONLY IF P0-P4 all pass: ONE preregistered chronological 43-name W_DEV
      run under the pinned successor config (frozen C1 configuration:
      R1 rs ranking + R2 sector cap, no R3), gross / 4bps / 25bps views,
      with an in-driver deterministic replay (second execution asserted
      identical).

Labels: EQUITIES-ONLY DEV EXPLORATORY / G4 UNADOPTED / NOT VALIDATED EDGE.
SMCI is pre-declared EXCLUDED (no DEV bytes exist); never fabricated.
"""
import hashlib
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "engine_successor")
ENGINE_FORK09 = os.path.join(HERE, "engine_fork09")
ENGINE_ORIG = os.path.join(HERE, "engine_orig")
SRC09 = os.path.join(HERE, "src", "research_notes", "equity_pit_integrity_20261023_09")
TESTS13 = os.path.join(HERE, "tests")
ARCHIVE = os.path.join(HERE, "archive_clone", "captures")
NS11 = os.path.join(ARCHIVE, "td_capture_equity39_continue_20261023")
NSP = os.path.join(ARCHIVE, "td_pilot_20261023")
REPO = os.path.expanduser("~/workspace/quality-flow-scanner-v5")
OUT = os.environ.get("QF_OUT", HERE)

sys.path.insert(0, HERE)  # asof_benchmark
sys.path.insert(0, ENGINE)
sys.path.insert(0, os.path.join(ENGINE, "pine_stack"))
sys.path.insert(0, os.path.join(ENGINE, "pine_ranking"))
sys.path.insert(0, os.path.join(ENGINE, "pine_exposure"))
sys.path.insert(0, os.path.join(ENGINE, "pine_signal_quality"))

import numpy as np
import pandas as pd

ET = "America/New_York"
FIXED_NOW = pd.Timestamp("2026-10-17 00:00:00", tz=ET)

CHILD_ROOT = "c5628652c5bf59d870103e41fd7e22a23fe4d811c61662fda78a8790abd0444f"
PARENT_ROOT = "ca49892062f1ac5d4ec6d20eaadd37b519aec84ad0b23a995fb11db74dccfd64"
PILOT_ROOT = "79ccdd128e0b36537f56f8ae36a731b719e989b9756f65856b7dc47344327122"
PILOT = ["NVDA", "TSLA", "AAPL", "SPY"]
EXPECTED_ADMITTED = 3653
EXPECTED_BARS_4H = 1043
EXPECTED_CLOSED = 586
SEED = 20261023

EXPECTED_PINS = {
    # -13 successor engine (canonical pin + censoring treatment; deltas are
    # confined to simulate_portfolio / simulate_stack accounting)
    "engine_successor/pine_backtest.py": "874d2a9b1d99171a4d3db709ece9ce4719b4d108a70f7e95b4a082692cc0c99d",
    "engine_successor/pine_stack/pine_stack.py": "8d4a964fd7bb08b4a98a55eb7fae222157ae27f1a768f255e7cbc152c9d15b03",
    # pristine -09 research fork (byte-identical to -12 stage copies)
    "engine_fork09/pine_backtest.py": "becea0824486003daef386b49e137a83ffdf22c1e2d145136498919102fc42f2",
    "engine_fork09/pine_stack/pine_stack.py": "30594231ffc3bac27303f96310e8f274229415c890c371f4dbdfcdb54156cda4",
    "asof_benchmark.py": "f0f4582c4a8aee484c24d330658b0c4ae6e2a169c19f3bf2b1475c2dc2ce2017",
    # shared engine files, byte-identical across successor and fork09 trees
    "engine_successor/scanner_rules.py": "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c",
    "engine_successor/pine_ranking/pine_ranking.py": "77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6",
    "engine_successor/pine_signal_quality/pine_signal_quality.py": "b1b39ee8d0bd4bbb1387b3ce54c7345c1f8dd622f94a5ed390c989fed1d39e69",
    "engine_successor/pine_exposure/pine_exposure.py": "9f646161c27f6b28febe0980d03665bc9c1502fb844d37be6fd1d72ee45102be",
    "engine_fork09/scanner_rules.py": "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c",
    "engine_fork09/pine_ranking/pine_ranking.py": "77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6",
    # frozen originals (unmodified)
    "engine_orig/pine_backtest.py": "447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5",
    "engine_orig/pine_stack/pine_stack.py": "839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb29a5956dfcefa",
    "session_table.json": "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f",
}
HARNESS_SHA = "ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d"

# The -12 terminal-open census (package 861f5e2, results.json P4_candidates):
# the frozen construction's four right-censored positions. The successor
# generator must reproduce these EXACTLY as censored candidates.
EXPECTED_CENSORED = {
    "CRM": {"signal_idx": 1041, "entry": 239.52499, "stop": 230.4129667209627,
            "tp1": 251.56103437204976, "tp1_hit": False,
            "entry_time": "2026-10-16 13:30:00-04:00", "last_close": 240.73},
    "SHOP": {"signal_idx": 1029, "entry": 165.53, "stop": 159.43008617972552,
             "tp1": 173.66321842703263, "tp1_hit": True,
             "entry_time": "2026-10-08 13:30:00-04:00", "last_close": 169.50999},
    "MRNA": {"signal_idx": 965, "entry": 138.985, "stop": 118.51963075494507,
             "tp1": 166.22282566007325, "tp1_hit": True,
             "entry_time": "2026-08-24 13:30:00-04:00", "last_close": 218.0},
    "PFE": {"signal_idx": 1035, "entry": 28.33, "stop": 27.79819120311426,
            "tp1": 29.03907839584765, "tp1_hit": True,
            "entry_time": "2026-10-13 13:30:00-04:00", "last_close": 29.57},
}

EXPERIMENT_CONFIG = {
    "experiment_id": "QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13",
    "predecessor": "QF-EQUITY43-DEV-PREFLIGHT-20261023-12 STOP_PREFLIGHT "
                   "(package 861f5e2, immutable; not re-run, not superseded "
                   "silently — this is a new versioned experiment)",
    "candidate_processing_order": "canonical (symbol, signal_idx) ascending; "
                                  "the candidate list is sorted by this total "
                                  "key before BOTH simulator paths; "
                                  "(symbol, signal_idx) is unique per "
                                  "candidate, so no secondary key is needed",
    "censoring_treatment": "successor v1: a position still open at the last "
                           "bar is emitted as a candidate with censored=true, "
                           "exit/exit_time null; it enters the identical "
                           "time-local rank/cap/sector/risk selection; if "
                           "taken it is held to the W_DEV cutoff and valued "
                           "in equity at the last-completed-bar as-of mark; "
                           "if skipped it is ledgered with its gate reason; "
                           "no exit, cash flow, or trade R is fabricated",
    "cutoff_rule": "max over symbols of (last 4H bar start) + 4h "
                   "(= 2026-10-16 17:30 America/New_York)",
    "strategy_config": "frozen C1 configuration: V3.6 hybrid signal + frozen "
                       "exits, R1 rs_top2 ranking + R2 sector cap, no R3; "
                       "1% risk, max 5 concurrent, 5% portfolio risk cap; "
                       "strategy source files byte-identical to -12 pins",
    "engine": "successor copies of the -09 research fork; deltas confined to "
              "simulate_portfolio / simulate_stack accounting (canonical "
              "pipeline order is a driver-level pin; censoring treatment in "
              "both simulators); pins in P0",
    "cost_views": ["gross", "4bps", "25bps"],
    "universe": "43 DEV equities (UX51 equities minus SMCI: no DEV bytes "
                "exist; excluded pre-declared, never imputed)",
    "labels": ["EQUITIES-ONLY DEV EXPLORATORY", "G4 UNADOPTED",
               "NOT VALIDATED EDGE"],
}
CONFIG_SHA256 = hashlib.sha256(json.dumps(
    EXPERIMENT_CONFIG, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()

report = {"task": "QF-EQUITY43-DEV-ORDER-CENSOR-20261023-13",
          "labels": EXPERIMENT_CONFIG["labels"],
          "experiment_id": EXPERIMENT_CONFIG["experiment_id"],
          "experiment_config": EXPERIMENT_CONFIG,
          "experiment_config_sha256": CONFIG_SHA256,
          "phases": {}}
failures = []


def fail(phase, msg):
    failures.append(f"{phase}: {msg}")
    print(f"FAIL [{phase}] {msg}", flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def paused_pins():
    return {"harness_sha256": sha256_file(os.path.join(REPO, "v54_forward_harness.py")),
            "pause_new_entries_present": os.path.exists(
                os.path.join(REPO, "forward_test", "PAUSE_NEW_ENTRIES")),
            "resume_new_entries_present": os.path.exists(
                os.path.join(REPO, "forward_test", "RESUME_NEW_ENTRIES"))}


def paused_ok(pp):
    return pp["harness_sha256"] == HARNESS_SHA and pp["pause_new_entries_present"] \
        and not pp["resume_new_entries_present"]


# ---------------------------------------------------------------- Phase 0
def phase0():
    ph = {"pins": {}}
    for rel, want in EXPECTED_PINS.items():
        got = sha256_file(os.path.join(HERE, rel))
        ph["pins"][rel] = got
        if got != want:
            fail("P0", f"pin mismatch {rel}: {got} != {want}")
    for ns_name, ns in (("continue11", NS11), ("pilot", NSP)):
        sums = {}
        with open(os.path.join(ns, "SHA256SUMS")) as f:
            for line in f:
                line = line.strip()
                if line:
                    digest, rel = line.split(None, 1)
                    sums[rel.strip()] = digest
        bad = [rel for rel, want in sums.items()
               if sha256_file(os.path.join(ns, rel)) != want]
        ph[f"archive_{ns_name}_files"] = len(sums)
        ph[f"archive_{ns_name}_mismatches"] = bad
        if bad:
            fail("P0", f"archive {ns_name} SHA256SUMS mismatches: {bad}")
    pp = paused_pins()
    ph["paused_production_before"] = pp
    if not paused_ok(pp):
        fail("P0", f"PAUSED production pins not as expected: {pp}")
    ph["experiment_config_sha256"] = CONFIG_SHA256
    report["phases"]["P0_pins"] = ph
    print(f"P0 done: successor/fork/original pins ok; config pin "
          f"{CONFIG_SHA256[:16]}…; archive verified "
          f"({ph['archive_continue11_files']} + {ph['archive_pilot_files']}); "
          f"PAUSED pins ok", flush=True)


# ---------------------------------------------------------------- Phase 1
def recompute_root(manifest_path):
    m = json.load(open(manifest_path))
    body = dict(m)
    root = body.pop("root_digest_sha256")
    body.pop("root_digest_construction", None)
    calc = hashlib.sha256(json.dumps(body, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()
    return root, calc


def phase1(child_manifest):
    ph = {}
    root, calc = recompute_root(os.path.join(HERE, "child_manifest.json"))
    ph["child_root_committed"] = root
    ph["child_root_recomputed"] = calc
    if root != CHILD_ROOT or calc != CHILD_ROOT:
        fail("P1", f"child root mismatch: committed {root} recomputed {calc}")
    proot, pcalc = recompute_root(os.path.join(HERE, "capture_manifest_equity39.json"))
    ph["parent_root_committed"] = proot
    ph["parent_root_recomputed"] = pcalc
    if proot != PARENT_ROOT or pcalc != PARENT_ROOT:
        fail("P1", f"parent root mismatch: committed {proot} recomputed {pcalc}")
    prev = "GENESIS:" + CHILD_ROOT
    n_receipts, n_quar = 0, 0
    quar_dir = os.path.join(NS11, "quarantine")
    quar_files = set(os.listdir(quar_dir)) if os.path.isdir(quar_dir) else set()
    for spec in child_manifest["legs"]:
        lid = spec["leg_id"]
        rp = os.path.join(NS11, "receipts", lid.replace("/", "__") + ".receipt.json")
        if os.path.exists(rp):
            r = json.load(open(rp))
            if r["chain"]["prev_receipt_hash"] != prev:
                fail("P1", f"chain break at {lid}")
                break
            raw = open(os.path.join(NS11, "raw",
                                    lid.replace("/", "__") + ".json"), "rb").read()
            if hashlib.sha256(raw).hexdigest() != r["response"]["sha256"]:
                fail("P1", f"raw hash mismatch {lid}")
                break
            if r["manifest_root_digest_sha256"] != CHILD_ROOT or \
                    r["parent_manifest_root_digest_sha256"] != PARENT_ROOT:
                fail("P1", f"root pin mismatch {lid}")
                break
            prev = r["chain"]["receipt_hash"]
            n_receipts += 1
        else:
            q = lid.replace("/", "__") + ".json"
            if q not in quar_files and not any(f.startswith(lid.replace("/", "__"))
                                              for f in quar_files):
                fail("P1", f"leg {lid} has neither receipt nor quarantine record")
                break
            n_quar += 1
    ph["child_chain_receipts_verified"] = n_receipts
    ph["child_chain_head"] = prev
    ph["legs_without_receipt_quarantined"] = n_quar
    if n_receipts != 54:
        fail("P1", f"expected 54 child receipts, walked {n_receipts}")
    ph["pilot_receipts"] = {}
    for sym in PILOT:
        rc = json.load(open(os.path.join(NSP, "receipts", f"{sym}__DEV.receipt.json")))
        body = sha256_file(os.path.join(NSP, "raw", f"{sym}__DEV.json"))
        ok = (rc["response"]["sha256"] == body
              and rc["manifest_root_digest_sha256"] == PILOT_ROOT
              and rc["request"]["adjust"] == "splits"
              and rc["request"]["interval"] == "1h")
        ph["pilot_receipts"][sym] = {"response_sha256": rc["response"]["sha256"],
                                     "rows": rc["response"]["rows"], "ok": ok}
        if not ok:
            fail("P1", f"pilot receipt mismatch {sym}/DEV")
    report["phases"]["P1_chains"] = ph
    print(f"P1 done: child chain {n_receipts} receipts verified from GENESIS, "
          f"{n_quar} legs quarantined w/o receipt; pilot receipts ok", flush=True)


# ---------------------------------------------------------------- Phase 2
def load_session_table():
    t = json.load(open(os.path.join(HERE, "session_table.json")))
    assert t["session_count"] == 751
    dev = [s for s in t["sessions"] if s["date"] >= "2024-09-16"]
    assert len(dev) == 524, len(dev)
    return t, dev


def expected_starts(session):
    close_h, close_m = map(int, session["close"].split(":"))
    starts, mins = [], 9 * 60 + 30
    while mins < close_h * 60 + close_m:
        starts.append(f"{mins // 60:02d}:{mins % 60:02d}")
        mins += 60
    return starts


def phase2(table, dev_sessions, symbols43):
    sessions = {s["date"]: s for s in table["sessions"]}
    expected = {}
    for s in dev_sessions:
        for st in expected_starts(s):
            expected[(s["date"], st)] = True
    assert len(expected) == EXPECTED_ADMITTED, len(expected)
    legs, admitted_frames = {}, {}
    pfe_evidence = None
    for sym in symbols43:
        ns = NSP if sym in PILOT else NS11
        raw = json.load(open(os.path.join(ns, "raw", f"{sym}__DEV.json")))
        meta = raw["meta"]
        leg = {"source_namespace": "td_pilot_20261023" if sym in PILOT
               else "td_capture_equity39_continue_20261023",
               "meta_exchange_timezone": meta.get("exchange_timezone"),
               "meta_interval": meta.get("interval")}
        if meta.get("exchange_timezone") != ET or meta.get("interval") != "1h":
            fail("P2", f"{sym}: meta mismatch {meta}")
        rows = raw["values"]
        leg["raw_rows"] = len(rows)
        seen, admitted, excluded = {}, [], []
        parse_ok = True
        for r in rows:
            try:
                ts = pd.Timestamp(r["datetime"])
                o, h, l, c = (float(r[k]) for k in ("open", "high", "low", "close"))
                v = float(r["volume"])
            except Exception:
                parse_ok = False
                break
            if not all(np.isfinite(x) for x in (o, h, l, c, v)):
                fail("P2", f"{sym}: non-finite value at {r['datetime']}")
                parse_ok = False
                break
            if min(o, h, l, c) <= 0 or v < 0:
                fail("P2", f"{sym}: non-positive price / negative volume at {r['datetime']}")
                parse_ok = False
                break
            key = (r["datetime"][:10], r["datetime"][11:16])
            if key in seen:
                fail("P2", f"{sym}: duplicate stamp {r['datetime']}")
                parse_ok = False
                break
            seen[key] = True
            rec = {"ts": ts, "Open": o, "High": h, "Low": l, "Close": c, "Volume": v}
            if key in expected:
                admitted.append(rec)
            else:
                excluded.append({"datetime": r["datetime"], "open": o, "high": h,
                                 "low": l, "close": c, "volume": v})
        if not parse_ok:
            legs[sym] = leg
            continue
        bad_class = []
        for e in excluded:
            sess = sessions.get(e["datetime"][:10])
            if sess is None or sess["close"] != "13:00" \
                    or e["datetime"][11:16] < sess["close"]:
                bad_class.append(e["datetime"])
        leg["excluded"] = excluded
        leg["excluded_outside_generic_early_close_class"] = bad_class
        if bad_class:
            fail("P2", f"{sym}: excluded stamps outside the generic early-close "
                       f"class: {bad_class}")
        stamps = {(a["ts"].strftime("%Y-%m-%d"), a["ts"].strftime("%H:%M"))
                  for a in admitted}
        leg["admitted_rows"] = len(admitted)
        gates = {"G-2_calendar_admission": stamps == set(expected)
                 and len(admitted) == EXPECTED_ADMITTED,
                 "G-3_completeness_exact": len(admitted) == EXPECTED_ADMITTED,
                 "G-4_phantom_exclusion_generic": not bad_class,
                 "G-6_schema_instant_hygiene": len(seen) == len(rows)}
        zv = [a for a in admitted if a["Volume"] == 0]
        zv_moving = [a for a in zv
                     if not (a["Open"] == a["High"] == a["Low"] == a["Close"])]
        leg["zero_volume_admitted"] = len(zv)
        leg["zero_volume_price_moving"] = len(zv_moving)
        gates["G-5_volume_completeness"] = len(zv_moving) == 0
        leg["gates_G2_G6"] = gates
        if not all(gates.values()):
            fail("P2", f"{sym}: gate failure {gates}")
        idx = pd.DatetimeIndex([a["ts"] for a in admitted]).tz_localize(ET)
        if not idx.is_monotonic_increasing:
            fail("P2", f"{sym}: admitted stamps not strictly increasing")
        admitted_frames[sym] = pd.DataFrame(
            [{k: a[k] for k in ("Open", "High", "Low", "Close", "Volume")}
             for a in admitted], index=idx)
        if sym == "PFE":
            pfe_evidence = {"excluded": excluded,
                            "session_2024-12-24": sessions["2024-12-24"]}
        legs[sym] = leg
        print(f"P2 {sym}: raw {leg['raw_rows']} admitted {len(admitted)} "
              f"excluded {[e['datetime'] for e in excluded]} "
              f"zv {len(zv)}/{len(zv_moving)} moving", flush=True)
    report["phases"]["P2_adjudication"] = legs
    report["phases"]["P2_PFE_ruling"] = {
        "symbol": "PFE", "leg": "PFE/DEV",
        "carried_from": "QF-EQUITY43-DEV-PREFLIGHT-20261023-12 (package "
                        "861f5e2) — re-verified on identical admitted bytes "
                        "in this successor; ruling text unchanged",
        "excluded_rows_exact": pfe_evidence["excluded"] if pfe_evidence else None,
        "pinned_session_2024-12-24": pfe_evidence["session_2024-12-24"]
        if pfe_evidence else None,
        "generic_rule": (
            "A raw 1h bar is admitted iff its bar-open stamp belongs to the "
            "pinned session table's expected stamp set for its date "
            "([09:30, close) on the hourly grid). Exclusion is decided SOLELY "
            "by non-membership in that pinned set; the criterion is "
            "stamp-value-agnostic and is applied uniformly to all 43 legs. "
            "On 2024-12-24 the pinned close is 13:00, so the expected opens "
            "are exactly 09:30/10:30/11:30/12:30."),
        "ruling": (
            "PFE/DEV's single excluded row (2024-12-24 14:30) is a post-close "
            "stamp on a pinned 13:00 early-close session and is EXCLUDED under "
            "the same generic pinned-session rule that excludes the 15:30 "
            "stamps on the pilot legs; the 14:30 clock value is not the "
            "criterion and no PFE-specific whitelist exists or was applied. "
            "PFE/DEV is ADMITTED to the study at exactly 3,653 admitted rows "
            "with this variant evidence preserved verbatim."),
        "admitted_rows": legs.get("PFE", {}).get("admitted_rows"),
    }
    report["phases"]["P2_G4_VBASIS_disposition"] = (
        "G4/VBASIS remains CONVENTION_BREAK_SUSPECT and UNADOPTED (checker "
        "candidate-2, -02 disposition stands for the program; -11 G-7 line "
        "identical). Carried from -12 unchanged: it is an explicit "
        "qualification BLOCKER, not a silent pass and not waived: every input "
        "to this study is candidate-grade (CAPTURED_G1_G6_CANDIDATE_G4_"
        "UNADOPTED), NOT fully QUALIFIED. Price-side evidence on the admitted "
        "DEV bytes: adjust=splits in force per receipts, admission/"
        "completeness exact on all 43 legs, zero price-moving zero-volume "
        "admitted bars. No threshold was set, tuned, or touched.")
    return admitted_frames


# ---------------------------------------------------------------- Phase 3
def phase3():
    test09 = os.path.join(SRC09, "tests", "test_pit_integrity.py")
    out = {}
    for impl, eng, want_exit in (("original", ENGINE_ORIG, 1),
                                 ("fork09_pristine", ENGINE_FORK09, 0),
                                 ("fork_successor", ENGINE, 0)):
        impl_arg = "original" if impl == "original" else "fork"
        p = subprocess.run([sys.executable, test09, "--impl", impl_arg,
                            "--engine", eng],
                           capture_output=True, text=True)
        summary = [ln for ln in p.stdout.splitlines() if ln.startswith("SUMMARY")]
        out[f"pit09_{impl}"] = {"exit_code": p.returncode, "summary": summary,
                                "engine": eng}
        if p.returncode != want_exit:
            fail("P3", f"-09 fixture replay {impl}: exit {p.returncode} "
                       f"(want {want_exit}); {summary}; stderr tail: "
                       f"{p.stderr.strip()[-300:]}")
        print(f"P3 -09 fixtures [{impl}]: exit {p.returncode} {summary}",
              flush=True)
    test13 = os.path.join(TESTS13, "test_censoring.py")
    for impl, eng, want_exit in (("frozen", ENGINE_FORK09, 1),
                                 ("successor", ENGINE, 0)):
        p = subprocess.run([sys.executable, test13, "--impl", impl,
                            "--engine", eng],
                           capture_output=True, text=True)
        summary = [ln for ln in p.stdout.splitlines() if ln.startswith("SUMMARY")]
        out[f"censoring_{impl}"] = {"exit_code": p.returncode,
                                    "summary": summary, "engine": eng,
                                    "assertions": p.stdout.strip().splitlines()}
        if p.returncode != want_exit:
            fail("P3", f"censoring fixture {impl}: exit {p.returncode} "
                       f"(want {want_exit}); {summary}; stderr tail: "
                       f"{p.stderr.strip()[-300:]}")
        print(f"P3 censoring fixture [{impl}]: exit {p.returncode} {summary}",
              flush=True)
    report["phases"]["P3_fixture_replay"] = out


# ---------------------------------------------------------------- Phase 4
def gen_candidates_censored(sym, df):
    """Successor candidate generation: logic identical to the frozen
    pine_ranking.gen_candidates for closed trades (verified field-by-field
    against it in build_inputs), PLUS the successor censoring treatment —
    a position still open when the bars end is emitted as a right-censored
    candidate (censored=True, exit/exit_time None) carrying exactly the
    terms known at signal time. No exit is invented for it."""
    import pine_backtest as pb
    trades, censored, skipped_gap = [], [], 0
    n = len(df)
    i = pb.WARMUP
    in_trade, pos = False, None
    while i < n - 1:
        if not in_trade:
            if pb.pine_buy_signal(df, i):
                sig = df.iloc[i]
                entry = float(df["Open"].iloc[i + 1])
                stop0 = float(sig["Close"] - sig["atr"] * pb.SL_ATR)
                if entry <= stop0:
                    skipped_gap += 1
                    i += 1
                    continue
                in_trade = True
                pos = {"symbol": sym, "entry": entry, "stop": stop0,
                       "tp1": entry + float(sig["atr"]) * pb.TP_ATR,
                       "tp_hit": False, "runner": stop0,
                       "entry_idx": i + 1, "signal_idx": i,
                       "entry_time": df.index[i + 1]}
                i += 1
                continue
            i += 1
            continue
        bar = df.iloc[i]
        lo, hi, close = float(bar["Low"]), float(bar["High"]), float(bar["Close"])
        if not pos["tp_hit"] and hi >= pos["tp1"]:
            pos["tp_hit"] = True
        if pos["tp_hit"]:
            pos["runner"] = max(pos["runner"], close - float(bar["atr"]) * pb.TRAIL_ATR)
        trend_bear = bar["e21"] < bar["e55"] and close < bar["e200"]
        done = False
        if close < pos["runner"]:
            reason, done = "stop", True
        elif close < bar["e55"] or trend_bear:
            reason, done = ("ema55-bear" if trend_bear else "ema55-break"), True
        if done:
            if i + 1 < n:
                exit_px = float(df["Open"].iloc[i + 1])
                exit_idx, exit_time = i + 1, df.index[i + 1]
            else:
                exit_px, exit_time = close, df.index[i]
                exit_idx = i
            risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
            r1 = (pos["tp1"] - pos["entry"]) / pos["entry"] / risk_frac \
                if pos["tp_hit"] else None
            r2 = (exit_px - pos["entry"]) / pos["entry"] / risk_frac
            r_blend = (0.5 * r1 + 0.5 * r2) if r1 is not None else r2
            exit_synth = pos["entry"] * (1 + r_blend * risk_frac)
            trades.append({
                "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
                "tp1": pos["tp1"], "exit": exit_synth, "reason": reason,
                "tp1_hit": pos["tp_hit"], "entry_time": pos["entry_time"],
                "exit_time": exit_time, "hold_bars": exit_idx - pos["entry_idx"],
                "signal_time": df.index[pos["entry_idx"] - 1].isoformat(),
                "signal_idx": pos["signal_idx"]})
            in_trade, pos = False, None
        i += 1
    if in_trade and pos is not None:
        censored.append({
            "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
            "tp1": pos["tp1"], "exit": None, "reason": "censored_terminal_open",
            "tp1_hit": pos["tp_hit"], "entry_time": pos["entry_time"],
            "exit_time": None, "hold_bars": None,
            "signal_time": df.index[pos["signal_idx"]].isoformat(),
            "signal_idx": pos["signal_idx"], "censored": True})
    return trades, censored, skipped_gap


def phase4(admitted, dev_sessions, symbols43):
    import scanner_rules as sr
    import pine_backtest as pb
    out, bars4h = {}, {}
    table = {s["date"]: s for s in dev_sessions}
    for sym in symbols43:
        df = admitted[sym]
        bars = sr.resample_closed_4h_session_anchored(df, sym, now=FIXED_NOW)
        grid_ok, detail = True, {}
        by_date = {}
        for ts in bars.index:
            by_date.setdefault(ts.strftime("%Y-%m-%d"), []).append(ts.strftime("%H:%M"))
        if set(by_date) != set(table):
            grid_ok, detail["date_set_mismatch"] = False, True
        else:
            for d, sess in table.items():
                want = ["09:30"] if sess["close"] == "13:00" else ["09:30", "13:30"]
                if by_date[d] != want:
                    grid_ok, detail[d] = (by_date[d], want)
                    break
        if len(bars) != EXPECTED_BARS_4H:
            grid_ok, detail["bar_count"] = (len(bars), EXPECTED_BARS_4H)
        agg_bad = 0
        sess_rows = {}
        for ts, row in df.iterrows():
            sess_rows.setdefault(ts.strftime("%Y-%m-%d"), []).append((ts, row))
        for bts, brow in bars.iterrows():
            d = bts.strftime("%Y-%m-%d")
            bin_rows = [(ts, r) for ts, r in sess_rows[d]
                        if (ts.strftime("%H:%M") < "13:30") == (bts.strftime("%H:%M") == "09:30")]
            o = bin_rows[0][1]["Open"]; h = max(r["High"] for _, r in bin_rows)
            l = min(r["Low"] for _, r in bin_rows); c = bin_rows[-1][1]["Close"]
            v = sum(r["Volume"] for _, r in bin_rows)
            if not (o == brow["Open"] and h == brow["High"] and l == brow["Low"]
                    and c == brow["Close"] and v == brow["Volume"]):
                agg_bad += 1
            upto = [r for ts, r in sess_rows[d] if ts <= bin_rows[-1][0]]
            pv = sum(((r["High"] + r["Low"] + r["Close"]) / 3.0) * r["Volume"] for r in upto)
            vv = sum(r["Volume"] for r in upto)
            vwap = pv / vv if vv > 0 else np.nan
            if not np.isclose(vwap, brow["SessionVWAP"], rtol=1e-9, atol=1e-9):
                agg_bad += 1
        if agg_bad:
            fail("P4", f"{sym}: {agg_bad} bars fail aggregation parity")
        if not grid_ok:
            fail("P4", f"{sym}: 4H grid != pinned session table: {detail}")
        bars4h[sym] = bars
        out[sym] = {"bars_4h": len(bars), "grid_matches_pinned_table": grid_ok,
                    "aggregation_parity_bad_bars": agg_bad}
        print(f"P4 {sym}: {len(bars)} 4H bars grid_ok={grid_ok} agg_bad={agg_bad}",
              flush=True)
    report["phases"]["P4_grid_parity"] = out
    return bars4h


def build_inputs(bars4h, admitted, symbols43):
    """Candidates: frozen closed set (verified identical to the frozen
    generator) + successor censored set (verified against the -12 census);
    canonical (symbol, signal_idx) order applied; as-of benchmark features."""
    import pine_backtest as pb
    from pine_ranking import gen_candidates, compute_features
    from pine_exposure import SECTOR
    import asof_benchmark
    data, closes = {}, {}
    for sym in symbols43:
        data[sym] = pb.add_pine_indicators(bars4h[sym])
        closes[sym] = data[sym]["Close"]
    missing_sector = [s for s in symbols43 if s not in SECTOR]
    if missing_sector:
        fail("P4", f"symbols missing from frozen SECTOR map: {missing_sector}")
    report["phases"]["P4_sector_coverage"] = {
        "all_43_mapped": not missing_sector, "missing": missing_sector,
        "sector_map": {s: SECTOR[s] for s in symbols43}}
    closed_all, censored_all, skipped_gap = [], [], 0
    for sym in symbols43:
        tr_frozen, sg_frozen = gen_candidates(sym, data[sym])
        tr, cens, sg = gen_candidates_censored(sym, data[sym])
        same = (sg == sg_frozen and len(tr) == len(tr_frozen) and all(
            a["entry"] == b["entry"] and a["stop"] == b["stop"]
            and a["exit"] == b["exit"] and a["entry_time"] == b["entry_time"]
            and a["exit_time"] == b["exit_time"] and a["signal_idx"] == b["signal_idx"]
            for a, b in zip(tr, tr_frozen)))
        if not same:
            fail("P4", f"{sym}: successor closed generation diverges from "
                       f"frozen gen_candidates")
        skipped_gap += sg
        closed_all.extend(tr)
        censored_all.extend(cens)
    if len(closed_all) != EXPECTED_CLOSED:
        fail("P4", f"closed candidates {len(closed_all)} != {EXPECTED_CLOSED}")
    # censored set must reproduce the -12 census field-by-field
    cens_by_sym = {c["symbol"]: c for c in censored_all}
    if set(cens_by_sym) != set(EXPECTED_CENSORED):
        fail("P4", f"censored symbols {sorted(cens_by_sym)} != -12 census "
                   f"{sorted(EXPECTED_CENSORED)}")
    cens_check = {}
    for sym, want in EXPECTED_CENSORED.items():
        c = cens_by_sym.get(sym)
        if c is None:
            continue
        ok = (c["signal_idx"] == want["signal_idx"]
              and abs(c["entry"] - want["entry"]) < 1e-9
              and abs(c["stop"] - want["stop"]) < 1e-9
              and abs(c["tp1"] - want["tp1"]) < 1e-9
              and c["tp1_hit"] == want["tp1_hit"]
              and str(c["entry_time"]) == want["entry_time"]
              and abs(float(closes[sym].iloc[-1]) - want["last_close"]) < 1e-9
              and c["exit"] is None and c["exit_time"] is None)
        cens_check[sym] = {"matches_12_census": bool(ok), "candidate": {
            "symbol": sym, "signal_idx": c["signal_idx"], "entry": c["entry"],
            "stop": c["stop"], "tp1": c["tp1"], "tp1_hit": c["tp1_hit"],
            "entry_time": str(c["entry_time"]),
            "last_close": float(closes[sym].iloc[-1])}}
        if not ok:
            fail("P4", f"{sym}: censored candidate != -12 census: {c}")
    report["phases"]["P4_censored_generation"] = cens_check
    # per-candidate formula parity for closed candidates (as -12)
    parity_bad = []
    for tr in closed_all:
        df = data[tr["symbol"]]
        i = tr["signal_idx"]
        sig = df.iloc[i]
        ok = (pb.pine_buy_signal(df, i)
              and tr["entry"] == float(df["Open"].iloc[i + 1])
              and abs(tr["stop"] - float(sig["Close"] - sig["atr"] * pb.SL_ATR)) < 1e-9
              and abs(tr["tp1"] - (tr["entry"] + float(sig["atr"]) * pb.TP_ATR)) < 1e-9
              and tr["entry_time"] == df.index[i + 1]
              and tr["exit_time"] >= tr["entry_time"])
        if not ok:
            parity_bad.append((tr["symbol"], tr["signal_time"]))
    if parity_bad:
        fail("P4", f"closed-candidate parity failures: {parity_bad[:5]}")
    for c in censored_all:
        df = data[c["symbol"]]
        i = c["signal_idx"]
        sig = df.iloc[i]
        ok = (pb.pine_buy_signal(df, i)
              and c["entry"] == float(df["Open"].iloc[i + 1])
              and abs(c["stop"] - float(sig["Close"] - sig["atr"] * pb.SL_ATR)) < 1e-9
              and abs(c["tp1"] - (c["entry"] + float(sig["atr"]) * pb.TP_ATR)) < 1e-9
              and c["entry_time"] == df.index[i + 1])
        if not ok:
            fail("P4", f"censored-candidate parity failure: {c['symbol']}")
    # canonical order (the Ruling A pin) applied to the full candidate list
    canonical = sorted(closed_all + censored_all,
                       key=lambda t: (t["symbol"], t["signal_idx"]))
    bench_asof = {"SPY": asof_benchmark.build_daily_asof(admitted["SPY"])}
    bench_mid = {"SPY": asof_benchmark.build_daily_midnight(admitted["SPY"])}
    feats = compute_features(canonical, data, bench_asof)
    feats_mid = compute_features(canonical, data, bench_mid)
    n_rs_diff_closed = sum(1 for i, t in enumerate(canonical)
                           if not t.get("censored")
                           and abs(feats[i]["rs"] - feats_mid[i]["rs"]) > 1e-12)
    report["phases"]["P4_candidates"] = {
        "closed_candidates": len(closed_all),
        "censored_candidates": len(censored_all),
        "total_candidates": len(canonical),
        "parity_bad": len(parity_bad),
        "skipped_gap_below_stop": skipped_gap,
        "canonical_order": "list sorted by (symbol, signal_idx); keys unique",
        "canonical_keys_sha256": hashlib.sha256(json.dumps(
            [(t["symbol"], t["signal_idx"]) for t in canonical]).encode()
        ).hexdigest(),
        "rs_differs_asof_vs_midnight_closed_candidates": n_rs_diff_closed,
        "benchmark_policy": "daily SPY bars stamped at session completion "
                            "(16:00 ET) — fork asof_benchmark.build_daily_asof; "
                            "frozen bench_ret selection unchanged"}
    print(f"P4 candidates: closed={len(closed_all)} censored={len(censored_all)} "
          f"parity_bad={len(parity_bad)} rs_changed_by_asof(closed)="
          f"{n_rs_diff_closed}", flush=True)
    return data, closes, canonical, closed_all, censored_all, skipped_gap, feats


# ------------------------------------------------------- Phase 4 fidelity
def sim_struct_pb(port):
    taken_seq = [tuple(e["key"]) for e in port["ledger"] if e["action"] == "taken"]
    taken_risk = {tuple(e["key"]): e["risk_dollars"] for e in port["ledger"]
                  if e["action"] == "taken"}
    exits = {tuple(e["key"]): e["cash_flow"] for e in port["ledger"]
             if e["action"] == "exit"}
    disp = {tuple(e["key"]): e["action"] for e in port["ledger"]
            if e["action"] != "exit"}
    term = {x["symbol"]: x for x in port["terminal_open"]}
    return {"taken_seq": taken_seq, "taken_risk": taken_risk, "exits": exits,
            "disposition": disp, "terminal": term,
            "final_equity": port["final_equity"],
            "realized_equity": port["realized_equity"],
            "skipped_cap": port["skipped_cap_count"],
            "skipped_risk": port["skipped_cap_risk"]}


def sim_struct_stack(port, trades):
    taken_seq = [(trades[i]["symbol"], trades[i]["signal_idx"])
                 for i in port["taken"]]
    taken_risk = {tuple(e["key"]): e["risk_dollars"]
                  for e in port["exit_cashflows"]}
    for x in port["terminal_open"]:
        taken_risk[(x["symbol"], x["signal_idx"])] = x["risk_dollars"]
    exits = {tuple(e["key"]): e["cash_flow"] for e in port["exit_cashflows"]}
    disp = {(trades[i]["symbol"], trades[i]["signal_idx"]): v
            for i, v in port["disposition"].items()}
    term = {x["symbol"]: x for x in port["terminal_open"]}
    return {"taken_seq": taken_seq, "taken_risk": taken_risk, "exits": exits,
            "disposition": disp, "terminal": term,
            "final_equity": port["final_equity"],
            "realized_equity": port["realized_equity"],
            "skipped_cap": port["skipped_cap"],
            "skipped_risk": port["skipped_risk"]}


def compare_structs(a, b, tol=1e-9):
    diffs = []
    if a["taken_seq"] != b["taken_seq"]:
        diffs.append("taken sequence differs")
    for k in set(a["taken_risk"]) | set(b["taken_risk"]):
        if k not in a["taken_risk"] or k not in b["taken_risk"]:
            diffs.append(f"taken risk key mismatch {k}")
        elif abs(a["taken_risk"][k] - b["taken_risk"][k]) > tol:
            diffs.append(f"taken risk_dollars differ {k}")
    for k in set(a["exits"]) | set(b["exits"]):
        if k not in a["exits"] or k not in b["exits"]:
            diffs.append(f"exit key mismatch {k}")
        elif abs(a["exits"][k] - b["exits"][k]) > tol:
            diffs.append(f"exit cash flow differs {k}")
    if a["disposition"] != b["disposition"]:
        diffs.append("per-candidate dispositions differ")
    if a["skipped_cap"] != b["skipped_cap"] or a["skipped_risk"] != b["skipped_risk"]:
        diffs.append(f"skip counts differ cap {a['skipped_cap']} vs "
                     f"{b['skipped_cap']}, risk {a['skipped_risk']} vs "
                     f"{b['skipped_risk']}")
    if set(a["terminal"]) != set(b["terminal"]):
        diffs.append("terminal inventory symbol sets differ")
    else:
        for s, x in a["terminal"].items():
            y = b["terminal"][s]
            if abs(x["mark"] - y["mark"]) > tol or \
                    abs(x["unreal_dollars"] - y["unreal_dollars"]) > tol or \
                    abs(x["risk_dollars"] - y["risk_dollars"]) > tol:
                diffs.append(f"terminal accounting differs {s}")
    if abs(a["final_equity"] - b["final_equity"]) > tol:
        diffs.append(f"final equity differs {a['final_equity']} vs "
                     f"{b['final_equity']}")
    if abs(a["realized_equity"] - b["realized_equity"]) > tol:
        diffs.append("realized equity differs")
    return diffs


def phase4_fidelity(canonical, closes, censored_all, cutoff):
    import pine_backtest as pb
    import pine_stack as st
    from pine_exposure import SECTOR
    cost = pb.COSTS["4bps"]
    port_pb = pb.simulate_portfolio(canonical, closes, cost, pb.RISK_PCT,
                                    cutoff=cutoff)
    port_st = st.simulate_stack(canonical, closes, cost, False, False, False,
                                SECTOR, cutoff=cutoff)
    a, b = sim_struct_pb(port_pb), sim_struct_stack(port_st, canonical)
    diffs = compare_structs(a, b)
    # equity decomposition identity in BOTH paths: final == realized + marks
    decomp = {}
    for name, s in (("pb", a), ("stack", b)):
        tot = s["realized_equity"] + sum(x["unreal_dollars"]
                                         for x in s["terminal"].values())
        decomp[name] = {"final_equity": s["final_equity"],
                        "realized_plus_terminal_marks": tot,
                        "abs_diff": abs(tot - s["final_equity"])}
        if abs(tot - s["final_equity"]) > 1e-9:
            diffs.append(f"{name}: equity decomposition identity fails")
    if diffs:
        fail("P4", f"C0 trade-by-trade fidelity failed: {diffs[:6]}")
    # terminal-open accounting guard (Ruling B), C0 selection outcomes
    guard = {}
    for c in censored_all:
        key = (c["symbol"], c["signal_idx"])
        row = {"symbol": c["symbol"], "signal_idx": c["signal_idx"],
               "pb_disposition": a["disposition"].get(key),
               "stack_disposition": b["disposition"].get(key)}
        if row["pb_disposition"] == "taken":
            t = a["terminal"].get(c["symbol"])
            row.update({"in_terminal_inventory": t is not None,
                        "mark": t["mark"] if t else None,
                        "unreal_dollars": t["unreal_dollars"] if t else None,
                        "risk_dollars": t["risk_dollars"] if t else None})
        else:
            row["in_terminal_inventory"] = False
        guard[c["symbol"]] = row
        if row["pb_disposition"] is None or \
                row["pb_disposition"] != row["stack_disposition"]:
            fail("P4", f"guard: censored {c['symbol']} disposition mismatch "
                       f"{row}")
        if row["pb_disposition"] == "taken" and not row["in_terminal_inventory"]:
            fail("P4", f"guard: censored {c['symbol']} taken but absent from "
                       f"terminal inventory")
    report["phases"]["P4_c0_fidelity_trade_by_trade"] = {
        "pass": not diffs, "diffs": diffs,
        "taken_count": len(a["taken_seq"]),
        "exit_cashflows_compared": len(a["exits"]),
        "skipped_cap": a["skipped_cap"], "skipped_risk": a["skipped_risk"],
        "pb_final_equity": a["final_equity"],
        "stack_final_equity": b["final_equity"],
        "equity_decomposition": decomp}
    report["phases"]["P4_terminal_open_guard_C0"] = guard
    print(f"P4 C0 fidelity trade-by-trade: pass={not diffs} "
          f"taken={len(a['taken_seq'])} exits compared={len(a['exits'])} "
          f"final={a['final_equity']:.4f}", flush=True)
    # seeded permutation invariance: shuffle -> canonical pipeline -> rerun
    shuffled = list(canonical)
    random.Random(SEED).shuffle(shuffled)
    recanon = sorted(shuffled, key=lambda t: (t["symbol"], t["signal_idx"]))
    if [(t["symbol"], t["signal_idx"]) for t in recanon] != \
            [(t["symbol"], t["signal_idx"]) for t in canonical]:
        fail("P4", "canonical re-sort of shuffled list != canonical list")
    p_pb2 = pb.simulate_portfolio(recanon, closes, cost, pb.RISK_PCT,
                                  cutoff=cutoff)
    p_st2 = st.simulate_stack(recanon, closes, cost, False, False, False,
                              SECTOR, cutoff=cutoff)
    d2 = compare_structs(sim_struct_pb(p_pb2), a) + \
        compare_structs(sim_struct_stack(p_st2, recanon), b)
    p_st3 = st.simulate_stack(shuffled, closes, cost, False, False, False,
                              SECTOR, cutoff=cutoff)
    d3 = compare_structs(sim_struct_stack(p_st3, shuffled), b)
    perm_ok = not (d2 or d3)
    if not perm_ok:
        fail("P4", f"permutation invariance failed: {(d2 + d3)[:4]}")
    report["phases"]["P4_permutation_invariance"] = {
        "pass": perm_ok, "seed": SEED,
        "pipeline_recanonicalized_diffs": d2,
        "stack_raw_shuffled_diffs": d3}
    print(f"P4 permutation invariance (seed {SEED}): pass={perm_ok}",
          flush=True)


# ---------------------------------------------------------------- Phase 5
def run_views(canonical, closes, feats, skipped_gap, cutoff):
    import pine_backtest as pb
    import pine_stack as st
    from pine_exposure import SECTOR
    from pine_signal_quality import extend_row
    pb.COSTS.setdefault("gross", 0.0)
    st.rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(canonical)}
    views, ports = {}, {}
    for cost_name in ("gross", "4bps", "25bps"):
        cost = pb.COSTS[cost_name]
        port = st.simulate_stack(canonical, closes, cost, True, True, False,
                                 SECTOR, cutoff=cutoff)
        ports[cost_name] = port
        taken = [canonical[i] for i in port["taken"]]
        taken_closed = [t for t in taken if not t.get("censored")]
        term = port["terminal_open"]
        row = pb.summarize("EQUITY43_DEV_C1CFG_SUCCESSOR13", taken_closed,
                           port, skipped_gap, cost_name)
        row = extend_row(row, taken_closed, cost_name)
        row["candidates_available"] = len(canonical)
        row["closed_trades"] = len(taken_closed)
        row["terminal_open_taken_count"] = len(term)
        row["terminal_open_inventory"] = term
        row["terminal_open_unreal_dollars"] = \
            sum(x["unreal_dollars"] for x in term)
        row["realized_equity"] = port["realized_equity"]
        row["final_equity"] = port["final_equity"]
        row["rank_skips"] = port["skipped_rank"]
        row["max_position_skips"] = port["skipped_cap"]
        row["risk_gate_skips"] = port["skipped_risk"]
        row["sector_cap_skips"] = port["skipped_gate"]
        # concurrency under simulator semantics: at a shared timestamp exits
        # are processed BEFORE entries (kind 0 = exit, kind 1 = entry);
        # a taken censored position occupies its slot until the cutoff.
        events = []
        for t in taken:
            events.append((t["entry_time"], 1, 1))
            events.append((t["exit_time"] if not t.get("censored") else cutoff,
                           0, -1))
        events.sort(key=lambda e: (e[0], e[1]))
        cur = mx = 0
        for _, _, d in events:
            cur += d
            mx = max(mx, cur)
        row["max_concurrent_positions"] = mx
        slices = {}
        for t in taken_closed:
            y = str(t["entry_time"].year)
            _, _, nr, _ = pb._outcome(t["entry"], t["stop"], t["exit"], cost)
            s = slices.setdefault(y, {"trades": 0, "sum_net_r": 0.0})
            s["trades"] += 1
            s["sum_net_r"] += nr
        for y, s in slices.items():
            s["mean_net_r"] = round(s["sum_net_r"] / s["trades"], 3)
            s["sum_net_r"] = round(s["sum_net_r"], 3)
        row["entry_year_slices_closed_trades"] = slices
        views[cost_name] = row
        print(f"P5 [{cost_name}] taken_closed={len(taken_closed)} "
              f"terminal_open={len(term)} exp={row['expectancy_net_r']}R "
              f"PF={row['profit_factor']} ret={row['total_return_pct']}% "
              f"dd={row['max_drawdown_pct']}% win={row['win_rate_pct']}% "
              f"rank_skips={row['rank_skips']} sector_skips="
              f"{row['sector_cap_skips']} cap_skips={row['max_position_skips']} "
              f"risk_skips={row['risk_gate_skips']} final_eq="
              f"{port['final_equity']:.2f} realized={port['realized_equity']:.2f}",
              flush=True)
    return views, ports


def phase5(canonical, closes, feats, skipped_gap, censored_all, symbols43,
           cutoff):
    import pine_backtest as pb
    from pine_exposure import SECTOR
    views, ports = run_views(canonical, closes, feats, skipped_gap, cutoff)
    # deterministic replay: full second execution, asserted identical
    views2, ports2 = run_views(canonical, closes, feats, skipped_gap, cutoff)
    replay_ok = json.dumps(views, sort_keys=True, default=str) == \
        json.dumps(views2, sort_keys=True, default=str)
    for cn in ports:
        if ports[cn]["taken"] != ports2[cn]["taken"] or \
                ports[cn]["disposition"] != ports2[cn]["disposition"] or \
                ports[cn]["terminal_open"] != ports2[cn]["terminal_open"]:
            replay_ok = False
    report["phases"]["P5_replay"] = {"byte_identical_views": bool(replay_ok)}
    if not replay_ok:
        fail("P5", "deterministic replay diverged")
    report["phases"]["P5_run"] = views
    # full candidate ledger with per-view outcomes
    taken_ids = {cn: {id(canonical[i]) for i in ports[cn]["taken"]}
                 for cn in ports}
    disp4 = ports["4bps"]["disposition"]
    term_by_view = {cn: {x["symbol"]: x for x in ports[cn]["terminal_open"]}
                    for cn in ports}
    ledger = []
    for i, t in enumerate(canonical):
        row = {"symbol": t["symbol"], "sector": SECTOR[t["symbol"]],
               "signal_time": t["signal_time"], "signal_idx": t["signal_idx"],
               "entry_time": str(t["entry_time"]),
               "entry": t["entry"], "stop": t["stop"], "tp1": t["tp1"],
               "tp1_hit": t["tp1_hit"], "rs": feats[i]["rs"],
               "censored": bool(t.get("censored")),
               "taken_gross": id(t) in taken_ids["gross"],
               "taken_4bps": id(t) in taken_ids["4bps"],
               "taken_25bps": id(t) in taken_ids["25bps"],
               "disposition_4bps_c1": disp4.get(i)}
        if t.get("censored"):
            row.update({"exit_time": None, "exit_synth": None,
                        "reason": "censored_terminal_open", "hold_bars": None,
                        "gross_r": None, "net_r_4bps": None,
                        "net_r_25bps": None,
                        "terminal_by_view": {
                            cn: ({"mark": term_by_view[cn][t["symbol"]]["mark"],
                                  "unreal_dollars":
                                      term_by_view[cn][t["symbol"]]["unreal_dollars"],
                                  "risk_dollars":
                                      term_by_view[cn][t["symbol"]]["risk_dollars"]}
                                 if t["symbol"] in term_by_view[cn] else None)
                            for cn in ports}})
        else:
            _, gr, _, _ = pb._outcome(t["entry"], t["stop"], t["exit"], 0.0)
            _, _, nr4, _ = pb._outcome(t["entry"], t["stop"], t["exit"],
                                       pb.COSTS["4bps"])
            _, _, nr25, _ = pb._outcome(t["entry"], t["stop"], t["exit"],
                                        pb.COSTS["25bps"])
            row.update({"exit_time": str(t["exit_time"]),
                        "exit_synth": t["exit"], "reason": t["reason"],
                        "hold_bars": t["hold_bars"],
                        "gross_r": round(gr, 4), "net_r_4bps": round(nr4, 4),
                        "net_r_25bps": round(nr25, 4)})
        ledger.append(row)
    per_symbol = {}
    for sym in symbols43:
        cand = [x for x in ledger if x["symbol"] == sym]
        tk = [x for x in cand if x["taken_4bps"] and not x["censored"]]
        per_symbol[sym] = {
            "sector": SECTOR[sym], "candidates": len(cand),
            "censored_candidates": sum(1 for x in cand if x["censored"]),
            "taken_4bps_closed": len(tk),
            "mean_net_r_4bps": round(float(np.mean([x["net_r_4bps"] for x in tk])), 3) if tk else None,
            "sum_net_r_4bps": round(float(np.sum([x["net_r_4bps"] for x in tk])), 3) if tk else None,
            "mean_gross_r_taken": round(float(np.mean([x["gross_r"] for x in tk])), 3) if tk else None,
            "win_rate_4bps_pct": round(100.0 * float(np.mean([x["net_r_4bps"] > 0 for x in tk])), 1) if tk else None}
    report["phases"]["P5_per_symbol"] = per_symbol
    report["phases"]["P5_terminal_open_disclosure"] = {
        "censored_candidates": len(censored_all),
        "treatment": EXPERIMENT_CONFIG["censoring_treatment"],
        "c1_outcomes_by_view": {
            cn: [{"symbol": x["symbol"], "mark": x["mark"],
                  "unreal_dollars": x["unreal_dollars"],
                  "risk_dollars": x["risk_dollars"]}
                 for x in ports[cn]["terminal_open"]] for cn in ports},
        "note": "Expectancy / PF / win-rate are computed over CLOSED taken "
                "trades only; final equity and total return include the "
                "terminal as-of marks of the open inventory above, per the "
                "adjudicated gate-3 accounting (terminal opens included in "
                "account equity and explicit ledger). No censored position "
                "was assigned an exit, a cash flow, or a trade R."}
    with open(os.path.join(OUT, "trade_ledger.json"), "w") as f:
        json.dump(ledger, f, indent=1, default=str)
    print(f"P5 ledger: {len(ledger)} candidates written; replay identical="
          f"{replay_ok}", flush=True)


# ------------------------------------------------------------------- main
def main():
    child_manifest = json.load(open(os.path.join(HERE, "child_manifest.json")))
    symbols43 = PILOT + [l["symbol"] for l in child_manifest["legs"]
                         if l["window"] == "W_DEV"]
    assert len(symbols43) == 43 and len(set(symbols43)) == 43, symbols43
    report["universe_43_order"] = symbols43
    report["universe_excluded"] = {
        "SMCI": "EXCLUDED pre-declared: no DEV bytes exist (TD SMCI/HO "
                "NOT_EVALUABLE_PROVIDER_VOLUME; DEV never captured). Never "
                "fabricated or imputed."}
    phase0()
    if not failures:
        phase1(child_manifest)
    table, dev_sessions = load_session_table()
    admitted = {}
    if not failures:
        admitted = phase2(table, dev_sessions, symbols43)
    if not failures:
        phase3()
    bars = {}
    if not failures:
        bars = phase4(admitted, dev_sessions, symbols43)
    cutoff = None
    if not failures:
        cutoff = max(bars[s].index[-1] for s in symbols43) \
            + pd.Timedelta(hours=4)
        report["phases"]["P4_cutoff"] = {
            "cutoff": str(cutoff),
            "rule": EXPERIMENT_CONFIG["cutoff_rule"]}
        print(f"P4 cutoff: {cutoff}", flush=True)
    if not failures:
        data, closes, canonical, closed_all, censored_all, skipped_gap, \
            feats = build_inputs(bars, admitted, symbols43)
    if not failures:
        phase4_fidelity(canonical, closes, censored_all, cutoff)
    if failures:
        report["verdict"] = "STOP_PREFLIGHT"
        report["blockers"] = failures
        json.dump(report, open(os.path.join(OUT, "results.json"), "w"),
                  indent=1, default=str)
        print("STOP: successor preflight failed; NO performance figures "
              "produced.", flush=True)
        return 2
    phase5(canonical, closes, feats, skipped_gap, censored_all, symbols43,
           cutoff)
    pp = paused_pins()
    report["paused_production_after"] = pp
    if not paused_ok(pp):
        fail("P5", f"PAUSED production pins changed during run: {pp}")
    if failures:
        report["verdict"] = "STOP_RUN"
        report["blockers"] = failures
    else:
        report["verdict"] = "EXPLORATORY_RUN_COMPLETE"
    json.dump(report, open(os.path.join(OUT, "results.json"), "w"),
              indent=1, default=str)
    print(f"VERDICT: {report['verdict']}", flush=True)
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())
