"""Test suite for the Text 0 unblock package (2026-10-27).

Covers:
  A. corr3 binding (synthetic fixtures only): positive pool-count
     run under a completed fixture binding; fail-closed on tampered
     inventory, tampered manifest, wrong tier membership,
     out-of-window row, census mismatch; the SHIPPED template
     binding refuses to run; corr2 (the pinned predecessor) refuses
     the same synthetic holdout-domain inventory with the DEV
     census - the recorded STOP blocker, reproduced on fixtures.
  B. AST audit: corr3 vs corr2 - every shared function's AST is
     identical except the enumerated binding functions; the only
     new functions are the binding trio; module-level constants
     differ only in the enumerated binding set.
  C. Builder: dev-validate reproduces the pinned P7b inventory
     byte-for-byte per symbol on a 3-symbol subset (NVDA/AMD/PLTR);
     synthetic holdout-parameterized build on fabricated captures
     produces the exact row schema; a price-moving zero-volume
     admitted bar trips the volume gate; holdout mode is latched
     without the session authorization env var.

No holdout data is read anywhere in this suite. All holdout-domain
fixtures are fabricated.
"""
import ast
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
CORR2 = os.path.join(HERE, "corr2_src", "exp14_buy_corr2.py")
CORR3 = os.path.join(HERE, "exp14_buy_corr3.py")
BUILDER = os.path.join(HERE, "build_holdout_inventory.py")
SHIPPED_MANIFEST = os.path.join(HERE, "holdout_binding_manifest.json")
P7B_INVENTORY = os.path.expanduser(
    "~/workspace/qf_feed_measure_stage/archive_clone/"
    "research_inventory/p7b_20261025/p7b_inventory.jsonl")
P7B_SHA = "a6bbd19a702120cafd48cd01ee4c8ff59b838a8bd6439822415d6c18278ef02f"

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}: {name} {detail}")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=kw.get("timeout", 120))


# =====================================================================
# Fixtures: synthetic holdout-domain inventory + completed binding
# =====================================================================
def synth_inventory(path, extra_symbol=False, out_of_window=False):
    """3 symbols x 60 bars (30 sessions x 2 bins), fabricated prices,
    domain fires planted at known indices."""
    import datetime as dt
    days = []
    d = dt.date(2023, 10, 19)
    while len(days) < 30:
        if d.weekday() < 5:
            days.append(d)
        d += dt.timedelta(days=1)
    planted = {"FAA": [10, 35], "FBB": [12], "FCC": [10, 35, 50]}
    rows = []
    for sym, fires in planted.items():
        for i in range(60):
            sess = days[i // 2]
            bin_ = "09:30" if i % 2 == 0 else "13:30"
            off = "-04:00" if sess < dt.date(2023, 11, 5) else "-05:00"
            close = 100.0 + (i % 7)
            row = {
                "symbol": sym, "idx": i,
                "ts": f"{sess.isoformat()}T{bin_}:00{off}",
                "session_date": sess.isoformat(),
                "session_ordinal": i // 2, "bin": bin_,
                "close": close, "atr": 2.0, "atr_pct": 0.02,
                "ema21": close - 1.0, "ema55": close - 2.0,
                "ema200": close - 3.0,
                "signal": i in fires,
                "in_generator_domain": i >= 5,
            }
            if out_of_window and sym == "FAA" and i == 59:
                row["session_date"] = "2024-12-02"
            rows.append(row)
    if extra_symbol:
        for i in range(60):
            r = dict(rows[i])
            r["symbol"] = "FDD"
            rows.append(r)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    census = sum(1 for r in rows
                 if r["in_generator_domain"] and r["signal"])
    return census


def write_manifest(path, inv_sha, census, tiers=None):
    m = {
        "binding_id": "FIXTURE-BINDING",
        "status": "fixture",
        "window_start": "2023-10-19", "window_end": "2024-09-15",
        "tiers": tiers or {"tier2": ["FAA", "FBB"], "tier3": ["FCC"]},
        "inventory_sha256": inv_sha, "expected_fires": census,
    }
    with open(path, "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    return sha256_file(path)


def pin_corr3(dst, manifest_sha):
    src = open(CORR3).read()
    shipped = json.loads(open(SHIPPED_MANIFEST).read())
    shipped_sha = sha256_file(SHIPPED_MANIFEST)
    assert src.count(shipped_sha) == 1
    src = src.replace(shipped_sha, manifest_sha)
    with open(dst, "w") as f:
        f.write(src)
    return dst


def corr3_cli(script, inv, inv_sha, manifest, out_report):
    return run([sys.executable, script, "--inventory", inv,
                "--inventory-sha", inv_sha, "--manifest", manifest,
                "--mode", "pool-counts", "--out-report", out_report])


def part_a():
    os.makedirs(FIX, exist_ok=True)
    inv = os.path.join(FIX, "synth_inventory.jsonl")
    census = synth_inventory(inv)
    inv_sha = sha256_file(inv)
    man = os.path.join(FIX, "fixture_manifest.json")
    man_sha = write_manifest(man, inv_sha, census)
    script = pin_corr3(os.path.join(FIX, "corr3_fixture.py"), man_sha)
    rep = os.path.join(FIX, "report.json")

    r = corr3_cli(script, inv, inv_sha, man, rep)
    check("A1 corr3 positive run under completed fixture binding",
          r.returncode == 0 and os.path.exists(rep),
          f"(rc={r.returncode})")
    if r.returncode == 0:
        report = json.load(open(rep))
        check("A1b census reconciled to planted fires",
              report["census_fires_reconciled"] == census,
              f"({report['census_fires_reconciled']} vs {census})")
        check("A1c cohort = planted window-complete events (2+1+2)",
              report["cohort_events_single_rule_h20"] == 5,
              f"({report['cohort_events_single_rule_h20']})")
        check("A1d report is outcome-blind (no return fields)",
              "outcome_blind" in report
              and not any("return" in k for k in report))

    # tampered inventory -> hash binding refuses (exit 1 SystemExit)
    bad_inv = os.path.join(FIX, "synth_inventory_tampered.jsonl")
    with open(inv, "rb") as f:
        data = f.read()
    with open(bad_inv, "wb") as f:
        f.write(data + b"\n")
    r = corr3_cli(script, bad_inv, sha256_file(bad_inv), man,
                  os.path.join(FIX, "r2.json"))
    check("A2 tampered inventory refused by manifest hash binding",
          r.returncode != 0 and "FAIL-CLOSED" in (r.stdout + r.stderr),
          f"(rc={r.returncode})")

    # tampered manifest -> compiled-in pin refuses (exit 2)
    bad_man = os.path.join(FIX, "fixture_manifest_tampered.json")
    m = json.load(open(man))
    m["tiers"]["tier3"] = ["FCX"]
    with open(bad_man, "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    r = corr3_cli(script, inv, inv_sha, bad_man,
                  os.path.join(FIX, "r3.json"))
    check("A3 tampered manifest refused by compiled-in pin",
          r.returncode == 2 and "FAIL-CLOSED" in r.stderr,
          f"(rc={r.returncode})")

    # wrong tier membership (extra symbol), honestly re-pinned
    inv_x = os.path.join(FIX, "synth_inventory_extra.jsonl")
    census_x = synth_inventory(inv_x, extra_symbol=True)
    man_x = os.path.join(FIX, "fixture_manifest_extra.json")
    man_x_sha = write_manifest(man_x, sha256_file(inv_x), census_x)
    script_x = pin_corr3(os.path.join(FIX, "corr3_fixture_x.py"),
                         man_x_sha)
    r = corr3_cli(script_x, inv_x, sha256_file(inv_x), man_x,
                  os.path.join(FIX, "r4.json"))
    check("A4 extra symbol refused by tier-membership binding",
          r.returncode == 2 and "symbol set" in r.stderr,
          f"(rc={r.returncode})")

    # out-of-window row, honestly re-pinned
    inv_w = os.path.join(FIX, "synth_inventory_oow.jsonl")
    census_w = synth_inventory(inv_w, out_of_window=True)
    man_w = os.path.join(FIX, "fixture_manifest_oow.json")
    man_w_sha = write_manifest(man_w, sha256_file(inv_w), census_w)
    script_w = pin_corr3(os.path.join(FIX, "corr3_fixture_w.py"),
                         man_w_sha)
    r = corr3_cli(script_w, inv_w, sha256_file(inv_w), man_w,
                  os.path.join(FIX, "r5.json"))
    check("A5 out-of-window row refused by window binding",
          r.returncode == 2 and "outside the sealed window" in r.stderr,
          f"(rc={r.returncode})")

    # census mismatch, honestly re-pinned
    man_c = os.path.join(FIX, "fixture_manifest_census.json")
    man_c_sha = write_manifest(man_c, inv_sha, census + 1)
    script_c = pin_corr3(os.path.join(FIX, "corr3_fixture_c.py"),
                         man_c_sha)
    r = corr3_cli(script_c, inv, inv_sha, man_c,
                  os.path.join(FIX, "r6.json"))
    check("A6 census mismatch fail-closed vs pinned holdout census",
          r.returncode != 0 and "pinned holdout census"
          in (r.stdout + r.stderr), f"(rc={r.returncode})")

    # shipped template binding can never run (real corr3, real pin)
    r = corr3_cli(CORR3, inv, inv_sha, SHIPPED_MANIFEST,
                  os.path.join(FIX, "r7.json"))
    check("A7 shipped STAGING TEMPLATE binding refuses to run",
          r.returncode == 2 and "STAGING TEMPLATE" in r.stderr,
          f"(rc={r.returncode})")

    # corr2 control: the pinned predecessor refuses this domain
    r = run([sys.executable, CORR2, "--inventory", inv,
             "--inventory-sha", inv_sha, "--mode", "pool-counts"])
    check("A8 corr2 (pinned) refuses synthetic holdout inventory "
          "with the DEV census - the STOP blocker",
          r.returncode != 0 and "P7 census 2892" in (r.stdout + r.stderr),
          f"(rc={r.returncode})")


def part_b():
    def funcs(path):
        tree = ast.parse(open(path).read())
        out = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[node.name] = ast.dump(node)
        return out, tree

    f2, t2 = funcs(CORR2)
    f3, t3 = funcs(CORR3)
    renamed = {"_check_dev_ts": "_check_window_ts"}
    changed_allowed = {"run_pool_counts", "main", "_check_window_ts",
                       "_analysis_impl"}
    new_allowed = {"load_binding", "require_completed_binding",
                   "verify_holdout_binding"}
    only3 = set(f3) - set(f2) - {"_check_window_ts"}
    only2 = set(f2) - set(f3) - {"_check_dev_ts"}
    check("B1 corr3-only functions are exactly the binding trio",
          only3 == new_allowed, f"({sorted(only3)})")
    check("B2 corr2-only function is exactly _check_dev_ts (renamed)",
          only2 == set(), f"({sorted(only2)})")
    diffs = []
    for name, dump in f2.items():
        if name in renamed:
            continue
        if name not in f3:
            diffs.append(f"missing:{name}")
        elif f3[name] != dump and name not in changed_allowed:
            diffs.append(name)
    check("B3 all non-binding shared functions AST-identical",
          not diffs, f"({diffs})")

    def normalize(dump):
        return (dump.replace("_check_dev_ts", "_check_window_ts")
                    .replace("DEV_START", "WINDOW_START")
                    .replace("DEV_END", "WINDOW_END")
                    .replace("non-DEV timestamp", "out-of-window timestamp"))
    check("B3b _analysis_impl identical modulo the renamed window "
          "check at its two call sites",
          normalize(f2["_analysis_impl"]) == f3["_analysis_impl"])
    check("B3c _check_window_ts identical to _check_dev_ts modulo "
          "the window binding tokens",
          normalize(f2["_check_dev_ts"]) == f3["_check_window_ts"])

    def assigns(tree):
        out = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        out[t.id] = ast.dump(node.value)
        return out

    a2, a3 = assigns(t2), assigns(t3)
    removed = set(a2) - set(a3)
    added = set(a3) - set(a2)
    changed = {k for k in set(a2) & set(a3) if a2[k] != a3[k]}
    check("B4 module constants: removed = DEV binding only",
          removed == {"EXPECTED_FIRES", "DEV_START", "DEV_END"},
          f"({sorted(removed)})")
    check("B5 module constants: added = CORR3 binding only",
          added == {"PINNED_MANIFEST_SHA256", "WINDOW_START",
                    "WINDOW_END", "MANIFEST_KEYS"},
          f"({sorted(added)})")
    check("B6 no other module constant changed (ladder/seeds/pins)",
          changed == set(), f"({sorted(changed)})")


# =====================================================================
# Builder fixtures
# =====================================================================
def synth_raw_capture(path, sessions, poison=False):
    import datetime as dt
    values = []
    base = 100.0
    k = 0
    for si, (date, close_hhmm) in enumerate(sessions):
        starts = []
        mins = 9 * 60 + 30
        ch, cm = map(int, close_hhmm.split(":"))
        while mins < ch * 60 + cm:
            starts.append(f"{mins // 60:02d}:{mins % 60:02d}")
            mins += 60
        for st in starts:
            k += 1
            px = base + 0.1 * k
            vol = 1000.0
            if poison and si == 5 and st == "10:30":
                vol = 0.0  # price-moving zero-volume admitted bar
            values.append({
                "datetime": f"{date} {st}:00", "open": px,
                "high": px + 0.5, "low": px - 0.5, "close": px + 0.2,
                "volume": vol})
    raw = {"meta": {"exchange_timezone": "America/New_York",
                    "interval": "1h"},
           "values": values}
    with open(path, "w") as f:
        json.dump(raw, f)


def part_c():
    inv_ref_ok = os.path.exists(P7B_INVENTORY) \
        and sha256_file(P7B_INVENTORY) == P7B_SHA
    check("C0 pinned P7b reference inventory present + hash-verified",
          inv_ref_ok)
    out = os.path.join(FIX, "builder_dev_inventory.jsonl")
    summ = os.path.join(FIX, "builder_dev_summary.json")
    if inv_ref_ok:
        r = run([sys.executable, BUILDER, "--mode", "dev-validate",
                 "--symbols", "NVDA,AMD,PLTR",
                 "--reference-inventory", P7B_INVENTORY,
                 "--out", out, "--summary", summ], timeout=900)
        ok = r.returncode == 0 and os.path.exists(summ)
        detail = ""
        if ok:
            s = json.load(open(summ))
            v = s["dev_validation"]
            ok = v["byte_exact_per_symbol"] \
                and v["rows_compared"] == 3 * 1043
            detail = f"(rows {v['rows_compared']})"
        check("C1 builder dev-validate: byte-exact vs pinned P7b "
              "inventory (NVDA/AMD/PLTR)", ok,
              detail or f"(rc={r.returncode}, tail={r.stdout[-200:]})")

    # synthetic holdout-parameterized build. The session list is
    # taken from the REAL adopted table (the frozen resample
    # consults the exchange calendar internally, so fabricated
    # closes on real dates would disagree with it - the fixture
    # uses 40 real sessions, incl. the 2023-11-24 early close).
    stage_table = json.load(open(os.path.expanduser(
        "~/workspace/qf_fix29_stage/home/session_table.json")))
    real = [s for s in stage_table["sessions"]
            if s["date"] >= "2023-10-19"][:40]
    sessions = [(s["date"], s["close"]) for s in real]
    days = [day for day, _ in sessions]
    n_early = sum(1 for _, cl in sessions if cl == "13:00")
    exp_bars = 2 * len(sessions) - n_early
    rawdir = os.path.join(FIX, "raw")
    os.makedirs(rawdir, exist_ok=True)
    for sym in ("FAA", "FBB"):
        synth_raw_capture(os.path.join(rawdir, f"{sym}__HO.json"),
                          sessions)
    table = {"session_count": len(sessions),
             "sessions": [{"date": day, "close": cl}
                          for day, cl in sessions]}
    table_path = os.path.join(FIX, "fixture_session_table.json")
    with open(table_path, "w") as f:
        json.dump(table, f)
    man = {"binding_id": "FIXTURE", "status": "fixture",
           "window_start": days[0], "window_end": days[-1],
           "tiers": {"tier2": ["FAA"], "tier3": ["FBB"]},
           "inventory_sha256": None, "expected_fires": None}
    man_path = os.path.join(FIX, "builder_manifest.json")
    with open(man_path, "w") as f:
        json.dump(man, f)
    out2 = os.path.join(FIX, "builder_synth_inventory.jsonl")
    summ2 = os.path.join(FIX, "builder_synth_summary.json")
    r = run([sys.executable, BUILDER, "--mode", "synthetic",
             "--manifest", man_path, "--raw-dir", rawdir,
             "--session-table", table_path, "--fixture-table",
             "--out", out2, "--summary", summ2], timeout=300)
    ok = r.returncode == 0 and os.path.exists(out2)
    check("C2 builder synthetic holdout-parameterized build runs",
          ok, f"(rc={r.returncode}, tail={(r.stdout + r.stderr)[-200:]})")
    if ok:
        rows = [json.loads(l) for l in open(out2)]
        keys = {"symbol", "idx", "ts", "session_date",
                "session_ordinal", "bin", "close", "atr", "atr_pct",
                "ema21", "ema55", "ema200", "signal",
                "in_generator_domain"}
        check("C2b emitted rows carry exactly the corr3 row schema",
              all(set(r) == keys for r in rows))
        check("C2c bar count per symbol = 2*sessions - early closes",
              all(sum(1 for r in rows if r["symbol"] == s) == exp_bars
                  for s in ("FAA", "FBB")),
              f"(expected {exp_bars})")
        check("C2d bins and ordinals are session-consistent",
              all(r["bin"] in ("09:30", "13:30")
                  and 0 <= r["session_ordinal"] < 40 for r in rows))
        s2 = json.load(open(summ2))
        check("C2e summary records inventory hash + census for the "
              "manifest completion step",
              s2["inventory_sha256"] == sha256_file(out2)
              and "census_fires_in_generator_domain" in s2)

    # poisoned capture: price-moving zero-volume admitted bar
    rawdir_p = os.path.join(FIX, "raw_poison")
    os.makedirs(rawdir_p, exist_ok=True)
    for sym in ("FAA", "FBB"):
        synth_raw_capture(os.path.join(rawdir_p, f"{sym}__HO.json"),
                          sessions, poison=True)
    out3 = os.path.join(FIX, "builder_poison_inventory.jsonl")
    r = run([sys.executable, BUILDER, "--mode", "synthetic",
             "--manifest", man_path, "--raw-dir", rawdir_p,
             "--session-table", table_path, "--fixture-table",
             "--out", out3, "--summary",
             os.path.join(FIX, "builder_poison_summary.json")],
            timeout=300)
    check("C3 builder volume gate: poisoned capture STOPs, "
          "no inventory written",
          r.returncode == 2 and not os.path.exists(out3),
          f"(rc={r.returncode})")

    # holdout latch
    env = dict(os.environ)
    env.pop("TEXT0_SESSION_AUTHORIZED", None)
    r = subprocess.run(
        [sys.executable, BUILDER, "--mode", "holdout",
         "--manifest", man_path, "--out",
         os.path.join(FIX, "never.jsonl"), "--summary",
         os.path.join(FIX, "never.json")],
        capture_output=True, text=True, env=env, timeout=60)
    check("C4 holdout mode latched without session authorization",
          r.returncode == 2 and "latched" in r.stdout,
          f"(rc={r.returncode})")


if __name__ == "__main__":
    part_a()
    part_b()
    part_c()
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("FAILED:", failed)
        sys.exit(1)
