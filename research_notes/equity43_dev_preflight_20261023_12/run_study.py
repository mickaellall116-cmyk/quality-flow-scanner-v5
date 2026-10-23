"""QF-EQUITY43-DEV-PREFLIGHT-20261023-12 — gated 43-equity DEV study driver.

Governing text: Issue #1 comment 6375014605 (ChatGPT GO, Mike's equities-first
decision). Ordered fail-closed operation:
  P0  pins (corrected engine fork + frozen originals, calendar, manifests,
      archive SHA256SUMS integrity for BOTH namespaces, PAUSED production)
  P1  receipt chains (child chain from GENESIS(c5628652...) re-walked in full
      on fresh-clone archive bytes; parent + child root digests recomputed;
      pilot DEV receipts field-verified). HO market content is NEVER parsed:
      HO legs are touched only as SHA256SUMS hashes / receipt-chain metadata.
  P2  per-name G1-G6 adjudication on the 43 DEV legs ONLY (calendar-bound
      admission vs the pinned 751-session table; generic early-close
      exclusion class; volume completeness). PFE 2024-12-24 14:30 stamp ruled
      explicitly under the generic rule. G4/VBASIS carried disclosed.
  P3  independent replay of the -09 fixtures (original expect 0/5 exit 1;
      fork expect 5/5 exit 0) against pinned trees.
  P4  real-input parity on admitted DEV bytes (session-anchored 4H grid vs
      pinned table; aggregation parity incl. SessionVWAP on every bar;
      per-candidate signal/level parity; terminal-open coverage tally;
      C0 fidelity invariant of the corrected simulators; sector coverage;
      as-of benchmark liveness evidence).
  P5  ONLY IF P0-P4 all pass: ONE preregistered chronological 43-name W_DEV
      run on the corrected research-only fork, frozen C1 configuration
      (R1 rs ranking + R2 sector cap, no R3), gross / 4bps / 25bps views.

Labels: EQUITIES-ONLY DEV EXPLORATORY / G4 UNADOPTED / NOT VALIDATED EDGE.
SMCI is pre-declared EXCLUDED (no DEV bytes exist); it is never fabricated.
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "engine")
ENGINE_ORIG = os.path.join(HERE, "engine_orig")
SRC09 = os.path.join(HERE, "src", "research_notes", "equity_pit_integrity_20261023_09")
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

EXPECTED_PINS = {
    # corrected research-only fork (-09 aad5563, byte-identical copies)
    "engine/pine_backtest.py": "becea0824486003daef386b49e137a83ffdf22c1e2d145136498919102fc42f2",
    "engine/pine_stack/pine_stack.py": "30594231ffc3bac27303f96310e8f274229415c890c371f4dbdfcdb54156cda4",
    "asof_benchmark.py": "f0f4582c4a8aee484c24d330658b0c4ae6e2a169c19f3bf2b1475c2dc2ce2017",
    # frozen originals (unmodified)
    "engine/scanner_rules.py": "62aa743ac28f05de9b6ec0ab962ee28bb7e5152bbef00bff5afa611a480f473c",
    "engine/pine_ranking/pine_ranking.py": "77afae0df120e3a2ad77a6d2d43247c8aea0ad296f08c273bff7d1cc833aaae6",
    "engine/pine_signal_quality/pine_signal_quality.py": "b1b39ee8d0bd4bbb1387b3ce54c7345c1f8dd622f94a5ed390c989fed1d39e69",
    "engine/pine_exposure/pine_exposure.py": "9f646161c27f6b28febe0980d03665bc9c1502fb844d37be6fd1d72ee45102be",
    "engine_orig/pine_backtest.py": "447a9a13bb2ec7ab0be246fdf6d3f2df06633bc6cb7fbdb76a24e23935d160e5",
    "engine_orig/pine_stack/pine_stack.py": "839e4800624de253514095b5c007e8088afc0ab6c6ef45c86fb29a5956dfcefa",
    "session_table.json": "00c5555c26d391444509e54de322841fa3269b64f3161a50aa507bf1d2bd416f",
}
HARNESS_SHA = "ce7c902ce182683ca1723468a0109747abd80db287c39556ea4db78210a0833d"

report = {"task": "QF-EQUITY43-DEV-PREFLIGHT-20261023-12",
          "labels": ["EQUITIES-ONLY DEV EXPLORATORY", "G4 UNADOPTED",
                     "NOT VALIDATED EDGE"],
          "experiment_id": "QF-EQUITY43-DEV-20261023-12",
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


# ---------------------------------------------------------------- Phase 0
def phase0():
    ph = {"pins": {}}
    for rel, want in EXPECTED_PINS.items():
        got = sha256_file(os.path.join(HERE, rel))
        ph["pins"][rel] = got
        if got != want:
            fail("P0", f"pin mismatch {rel}: {got} != {want}")
    # archive SHA256SUMS integrity for both namespaces (hash-only for HO)
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
    if pp["harness_sha256"] != HARNESS_SHA or not pp["pause_new_entries_present"] \
            or pp["resume_new_entries_present"]:
        fail("P0", f"PAUSED production pins not as expected: {pp}")
    report["phases"]["P0_pins"] = ph
    print(f"P0 done: engine pins ok; archive files verified "
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
    # full child chain walk on fresh-clone archive bytes, manifest order
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
    # pilot DEV receipts (field verification per -08; pilot chain is per-leg)
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
        # generic-class check on every excluded stamp: the stamp's date must be
        # a pinned EARLY-CLOSE session and the stamp time must be >= the pinned
        # close (post-close). Anything else is a material anomaly -> STOP.
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
    # ---- PFE ruling, in writing (generic rule, exact evidence preserved)
    report["phases"]["P2_PFE_ruling"] = {
        "symbol": "PFE", "leg": "PFE/DEV",
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
            "with this variant evidence preserved verbatim. Had the stamp "
            "fallen inside the pinned grid, or on a non-early-close date, the "
            "leg would have failed G-4 and stopped the study."),
        "admitted_rows": legs.get("PFE", {}).get("admitted_rows"),
    }
    report["phases"]["P2_G4_VBASIS_disposition"] = (
        "G4/VBASIS remains CONVENTION_BREAK_SUSPECT and UNADOPTED (checker "
        "candidate-2, -02 disposition stands for the program; -11 G-7 line "
        "identical). It is carried here as an explicit qualification BLOCKER, "
        "not a silent pass and not waived: every input to this study is "
        "candidate-grade (CAPTURED_G1_G6_CANDIDATE_G4_UNADOPTED), NOT fully "
        "QUALIFIED. Price-side evidence on the admitted DEV bytes: "
        "adjust=splits in force per receipts, admission/completeness exact on "
        "all 43 legs, zero price-moving zero-volume admitted bars. No "
        "threshold was set, tuned, or touched. This disposition authorizes "
        "only the labeled exploratory run the GO prescribes; any QUALIFIED "
        "claim remains blocked pending G4 adoption.")
    return admitted_frames


# ---------------------------------------------------------------- Phase 3
def phase3():
    test = os.path.join(SRC09, "tests", "test_pit_integrity.py")
    out = {}
    for impl, eng, want_exit in (("original", ENGINE_ORIG, 1), ("fork", ENGINE, 0)):
        p = subprocess.run([sys.executable, test, "--impl", impl, "--engine", eng],
                           capture_output=True, text=True)
        summary = [ln for ln in p.stdout.splitlines() if ln.startswith("SUMMARY")]
        out[impl] = {"exit_code": p.returncode, "summary": summary,
                     "engine": eng}
        if p.returncode != want_exit:
            fail("P3", f"fixture replay impl={impl}: exit {p.returncode} "
                       f"(want {want_exit}); {summary}; stderr tail: "
                       f"{p.stderr.strip()[-300:]}")
        print(f"P3 {impl}: exit {p.returncode} {summary}", flush=True)
    report["phases"]["P3_fork_fixture_replay"] = out


# ---------------------------------------------------------------- Phase 4
def gen_candidates_counted(sym, df):
    """Counting variant of the frozen pine_ranking.gen_candidates: identical
    logic, plus the terminal-open inventory (a position still open when the
    bars end produces NO candidate under the frozen construction — counted
    here, never silently dropped)."""
    import pine_backtest as pb
    trades, skipped_gap = [], 0
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
    terminal = []
    if in_trade and pos is not None:
        last_close = float(df["Close"].iloc[-1])
        risk_frac = (pos["entry"] - pos["stop"]) / pos["entry"]
        terminal.append({
            "symbol": sym, "entry": pos["entry"], "stop": pos["stop"],
            "tp1": pos["tp1"], "tp1_hit": pos["tp_hit"],
            "entry_time": str(pos["entry_time"]),
            "signal_idx": pos["signal_idx"],
            "last_bar": str(df.index[-1]), "last_close": last_close,
            "unrealized_r_at_last_close": round(
                (last_close - pos["entry"]) / pos["entry"] / risk_frac, 4)})
    return trades, skipped_gap, terminal


def phase4(admitted, dev_sessions, symbols43):
    import scanner_rules as sr
    import pine_backtest as pb
    from pine_ranking import gen_candidates
    from pine_exposure import SECTOR
    out, bars4h, terminal_all = {}, {}, []
    table = {s["date"]: s for s in dev_sessions}
    missing_sector = [s for s in symbols43 if s not in SECTOR]
    if missing_sector:
        fail("P4", f"symbols missing from frozen SECTOR map: {missing_sector}")
    report["phases"]["P4_sector_coverage"] = {
        "all_43_mapped": not missing_sector, "missing": missing_sector,
        "sector_map": {s: SECTOR[s] for s in symbols43}}
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
    """Indicators, candidates (frozen generator + counted variant cross-check),
    candidate parity, as-of benchmark. Returns run inputs or None on failure."""
    import pine_backtest as pb
    from pine_ranking import gen_candidates, compute_features
    import asof_benchmark
    data, closes = {}, {}
    for sym in symbols43:
        data[sym] = pb.add_pine_indicators(bars4h[sym])
        closes[sym] = data[sym]["Close"]
    all_trades, skipped_gap, terminal_all = [], 0, []
    for sym in symbols43:
        tr, sg = gen_candidates(sym, data[sym])
        tr2, sg2, term = gen_candidates_counted(sym, data[sym])
        same = (sg == sg2 and len(tr) == len(tr2) and all(
            a["entry"] == b["entry"] and a["stop"] == b["stop"]
            and a["exit"] == b["exit"] and a["entry_time"] == b["entry_time"]
            and a["exit_time"] == b["exit_time"] and a["signal_idx"] == b["signal_idx"]
            for a, b in zip(tr, tr2)))
        if not same:
            fail("P4", f"{sym}: counted variant diverges from frozen gen_candidates")
        skipped_gap += sg
        terminal_all.extend(term)
        all_trades.extend(tr)
    # per-candidate parity vs frozen formulas at recorded indices
    parity_bad = []
    for tr in all_trades:
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
        fail("P4", f"candidate parity failures: {parity_bad[:5]}")
    # as-of benchmark (fork) + liveness vs the original midnight construction
    bench_asof = {"SPY": asof_benchmark.build_daily_asof(admitted["SPY"])}
    bench_mid = {"SPY": asof_benchmark.build_daily_midnight(admitted["SPY"])}
    feats = compute_features(all_trades, data, bench_asof)
    feats_mid = compute_features(all_trades, data, bench_mid)
    n_rs_diff = sum(1 for i in range(len(all_trades))
                    if abs(feats[i]["rs"] - feats_mid[i]["rs"]) > 1e-12)
    report["phases"]["P4_candidates"] = {
        "candidates": len(all_trades), "parity_bad": len(parity_bad),
        "skipped_gap_below_stop": skipped_gap,
        "terminal_open_positions": terminal_all,
        "terminal_open_count": len(terminal_all),
        "rs_differs_asof_vs_midnight_candidates": n_rs_diff,
        "benchmark_policy": "daily SPY bars stamped at session completion "
                            "(16:00 ET) — fork asof_benchmark.build_daily_asof; "
                            "frozen bench_ret selection unchanged"}
    print(f"P4 candidates={len(all_trades)} parity_bad={len(parity_bad)} "
          f"terminal_open={len(terminal_all)} rs_changed_by_asof={n_rs_diff}",
          flush=True)
    return data, closes, all_trades, skipped_gap, terminal_all, feats


def phase4_fidelity(all_trades, closes):
    import pine_backtest as pb
    import pine_stack as st
    from pine_exposure import SECTOR
    port_pb = pb.simulate_portfolio(all_trades, closes, pb.COSTS["4bps"], pb.RISK_PCT)
    port_c0 = st.simulate_stack(all_trades, closes, pb.COSTS["4bps"],
                                False, False, False, SECTOR)
    ok = (abs(port_pb["final_equity"] - port_c0["final_equity"]) < 1e-6
          and port_pb["skipped_cap_count"] == port_c0["skipped_cap"])
    report["phases"]["P4_c0_fidelity_corrected"] = {
        "pass": bool(ok), "pb_final_equity": port_pb["final_equity"],
        "stack_c0_final_equity": port_c0["final_equity"],
        "pb_skipped_cap_count": port_pb["skipped_cap_count"],
        "stack_c0_skipped_cap": port_c0["skipped_cap"]}
    if not ok:
        fail("P4", "corrected-simulator C0 fidelity invariant failed")
    print(f"P4 C0 fidelity (corrected): pass={ok}", flush=True)


# ---------------------------------------------------------------- Phase 5
def phase5(all_trades, closes, skipped_gap, terminal_all, feats, symbols43):
    import pine_backtest as pb
    import pine_stack as st
    from pine_exposure import SECTOR
    from pine_signal_quality import extend_row
    pb.COSTS.setdefault("gross", 0.0)
    st.rs = {id(tr): feats[i]["rs"] for i, tr in enumerate(all_trades)}
    views, taken_by_view = {}, {}
    for cost_name in ("gross", "4bps", "25bps"):
        cost = pb.COSTS[cost_name]
        port = st.simulate_stack(all_trades, closes, cost, True, True, False, SECTOR)
        taken = [all_trades[i] for i in port["taken"]]
        taken_by_view[cost_name] = taken
        row = pb.summarize("EQUITY43_DEV_C1CFG_CORRECTED", taken, port,
                           skipped_gap, cost_name)
        row = extend_row(row, taken, cost_name)
        row["candidates_available"] = len(all_trades)
        row["rank_skips"] = port["skipped_rank"]
        row["max_position_skips"] = port["skipped_cap"]
        row["risk_gate_skips"] = port["skipped_risk"]
        row["sector_cap_skips"] = port["skipped_gate"]
        # max concurrency actually reached by the taken set
        events = []
        for t in taken:
            events.append((t["entry_time"], 1))
            events.append((t["exit_time"], -1))
        events.sort(key=lambda e: (e[0], -e[1]))
        cur = mx = 0
        for _, d in events:
            cur += d
            mx = max(mx, cur)
        row["max_concurrent_positions"] = mx
        # calendar slices by entry year (descriptive)
        slices = {}
        for t in taken:
            y = str(t["entry_time"].year)
            _, _, nr, _ = pb._outcome(t["entry"], t["stop"], t["exit"], cost)
            s = slices.setdefault(y, {"trades": 0, "sum_net_r": 0.0})
            s["trades"] += 1
            s["sum_net_r"] += nr
        for y, s in slices.items():
            s["mean_net_r"] = round(s["sum_net_r"] / s["trades"], 3)
            s["sum_net_r"] = round(s["sum_net_r"], 3)
        row["entry_year_slices"] = slices
        views[cost_name] = row
        print(f"P5 [{cost_name}] taken={len(taken)} exp={row['expectancy_net_r']}R "
              f"PF={row['profit_factor']} ret={row['total_return_pct']}% "
              f"dd={row['max_drawdown_pct']}% win={row['win_rate_pct']}% "
              f"rank_skips={row['rank_skips']} sector_skips={row['sector_cap_skips']} "
              f"cap_skips={row['max_position_skips']} risk_skips={row['risk_gate_skips']}",
              flush=True)
    report["phases"]["P5_run"] = views
    # per-symbol table (on the 4bps taken set) + full ledger
    taken4_ids = {id(t) for t in taken_by_view["4bps"]}
    taken25_ids = {id(t) for t in taken_by_view["25bps"]}
    takeng_ids = {id(t) for t in taken_by_view["gross"]}
    ledger = []
    for i, t in enumerate(all_trades):
        _, gr, _, _ = pb._outcome(t["entry"], t["stop"], t["exit"], 0.0)
        _, _, nr4, _ = pb._outcome(t["entry"], t["stop"], t["exit"], pb.COSTS["4bps"])
        _, _, nr25, _ = pb._outcome(t["entry"], t["stop"], t["exit"], pb.COSTS["25bps"])
        ledger.append({
            "symbol": t["symbol"], "sector": SECTOR[t["symbol"]],
            "signal_time": t["signal_time"], "signal_idx": t["signal_idx"],
            "entry_time": str(t["entry_time"]), "exit_time": str(t["exit_time"]),
            "entry": t["entry"], "stop": t["stop"], "tp1": t["tp1"],
            "exit_synth": t["exit"], "reason": t["reason"],
            "tp1_hit": t["tp1_hit"], "hold_bars": t["hold_bars"],
            "rs": feats[i]["rs"],
            "gross_r": round(gr, 4), "net_r_4bps": round(nr4, 4),
            "net_r_25bps": round(nr25, 4),
            "taken_gross": id(t) in takeng_ids, "taken_4bps": id(t) in taken4_ids,
            "taken_25bps": id(t) in taken25_ids})
    per_symbol = {}
    for sym in symbols43:
        cand = [x for x in ledger if x["symbol"] == sym]
        tk = [x for x in cand if x["taken_4bps"]]
        per_symbol[sym] = {
            "sector": SECTOR[sym], "candidates": len(cand), "taken_4bps": len(tk),
            "mean_net_r_4bps": round(float(np.mean([x["net_r_4bps"] for x in tk])), 3) if tk else None,
            "sum_net_r_4bps": round(float(np.sum([x["net_r_4bps"] for x in tk])), 3) if tk else None,
            "mean_gross_r_taken": round(float(np.mean([x["gross_r"] for x in tk])), 3) if tk else None,
            "win_rate_4bps_pct": round(100.0 * float(np.mean([x["net_r_4bps"] > 0 for x in tk])), 1) if tk else None}
    report["phases"]["P5_per_symbol"] = per_symbol
    report["phases"]["P5_terminal_open_disclosure"] = {
        "count": len(terminal_all), "inventory": terminal_all,
        "treatment": "Positions still open at the last DEV bar produce NO "
                     "candidate under the frozen gen_candidates construction "
                     "(identical to C1); they are counted and disclosed here "
                     "with marked value at the last close and are NOT in "
                     "account equity."}
    with open(os.path.join(OUT, "trade_ledger.json"), "w") as f:
        json.dump(ledger, f, indent=1, default=str)
    print(f"P5 ledger: {len(ledger)} candidates written", flush=True)


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
    if not failures:
        data, closes, all_trades, skipped_gap, terminal_all, feats = \
            build_inputs(bars, admitted, symbols43)
    if not failures:
        phase4_fidelity(all_trades, closes)
    if failures:
        report["verdict"] = "STOP_PREFLIGHT"
        report["blockers"] = failures
        json.dump(report, open(os.path.join(OUT, "results.json"), "w"),
                  indent=1, default=str)
        print("STOP: preflight failed; NO performance figures produced.", flush=True)
        return 2
    phase5(all_trades, closes, skipped_gap, terminal_all, feats, symbols43)
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
