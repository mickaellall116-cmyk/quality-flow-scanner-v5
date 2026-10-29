"""Test suite for the Text 0 unblock SUCCESSOR package (corr4).

One command runs the whole suite from the package directory:

    python3 test_text0_unblock_successor.py

(An interpreter with pandas + pandas_market_calendars is required -
the frozen engine's documented dependency; see PACKAGE.md.)

Covers:
  A. corr4 binding (fabricated fixtures only): positive pool-count
     run under a fixture Stage-1/Stage-2 binding; fail-closed on
     tampered inventory, tampered manifest (shipped pin AND fixture
     pin), wrong tier membership (extra symbol, missing Tier 3 ->
     the NAMED TIER3_INVENTORY_MISSING error, missing Tier 2),
     out-of-window row, census mismatch, addendum referencing the
     wrong binding content; override attempts (--symbols / --window
     / --manifest) rejected by the interface itself; the SHIPPED
     package refuses to run (no Stage-2 addendum exists - the
     designed state); corr2 (the pinned predecessor) refuses the
     same fixture inventory with the DEV census - the recorded
     Text 0 STOP blocker, reproduced on fixtures.
  B. AST audit: corr4 vs corr2 - every shared function AST-identical
     except the enumerated binding set; the only new functions are
     the binding quartet; module constants differ only in the
     enumerated binding set; classes unchanged.
  C. Builder: interface rejects the removed override flags
     (including --raw-dir: the raw directory is derived from the
     session layout, never a caller input); refuses without a
     session authorization, with a wrong-content authorization,
     with a single-operator authorization; a missing Tier 3
     capture exits 3 with the NAMED TIER3_CAPTURE_MISSING error
     and writes nothing; a poisoned capture whose bytes ARE the
     receipt-pinned bytes STOPs the build at the admission gates;
     raw captures are hash-bound BEFORE parsing - a capture that
     parses cleanly but fails its receipt pin is rejected with
     RAW_CAPTURE_HASH_MISMATCH (and an unparseable capture fails
     with the same hash error, proving no parse happened first),
     a tampered receipt fails RAW_RECEIPT_MANIFEST_HASH_MISMATCH,
     an authorization naming the wrong receipt hash fails the
     same way, an extra unlisted file fails
     RAW_CAPTURE_UNLISTED_FILE, and a symlinked capture fails
     RAW_CAPTURE_PATH_SUBSTITUTED; a full fabricated build over
     the REAL pinned window (227 sessions x 30 pinned symbols)
     produces the exact row schema, 452 bars per symbol, a
     summary whose hash/census reconcile and whose input hashes
     are the pre-parse verified receipt pins; the same build in a
     COPIED package tree reproduces the identical inventory hash
     (self-containment proof).
  D. Package integrity: SHA256_MANIFEST verifies; the Stage-1
     manifest's binding content hashes to the literal compiled
     into BOTH corr4 and the builder; tier membership re-derives
     from tier_derivation.json; the DECISION CARD names both named
     errors; fixture files regenerate byte-identically.

No holdout data is read anywhere in this suite. Every
holdout-domain fixture is fabricated. No vendor call is made.
"""
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
WORK = os.path.join(FIX, "work")
CORR2 = os.path.join(HERE, "corr2_src", "exp14_buy_corr2.py")
CORR4 = os.path.join(HERE, "exp14_buy_corr4.py")
BUILDER = os.path.join(HERE, "build_holdout_inventory_corr4.py")
MANIFEST = os.path.join(HERE, "stage1_manifest.json")
TABLE = os.path.join(HERE, "session_table_751.json")
PIN_CORR2 = "77bd53e82963d65ab743a57f1eff0d23b54467a0e17aaf1831b42e6e96b6f3d8"

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}: {name} {detail}",
          flush=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode()).hexdigest()


def run(cmd, timeout=120, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, cwd=cwd)


def load_rows(path):
    return [json.loads(l) for l in open(path)]


def write_rows(path, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def census_of(rows):
    return sum(1 for r in rows
               if r["in_generator_domain"] and r["signal"])


# =====================================================================
# Part A - corr4 matcher binding
# =====================================================================
def fixture_content_hash():
    m = json.load(open(os.path.join(FIX,
                                    "fixture_stage1_manifest.json")))
    keys = ("binding_id", "stage", "window_start", "window_end",
            "tiers", "session_table_sha256", "corr2_source_sha256",
            "engine", "raw_capture")
    return canonical_sha({k: m[k] for k in keys})


def pin_fixture_copy(dst_dir):
    """Copy corr4 into dst_dir with its compiled-in literals
    re-pinned to the fixture binding (the same pinning operation
    build_corr4.py performs for the real package), and place the
    fixture Stage-1 manifest + Stage-2 addendum beside it under
    their fixed names."""
    os.makedirs(dst_dir, exist_ok=True)
    src = open(CORR4).read()
    src, n = re.subn(r'PINNED_BINDING_CONTENT_SHA256 = "[0-9a-f]{64}"',
                     f'PINNED_BINDING_CONTENT_SHA256 = '
                     f'"{fixture_content_hash()}"', src)
    assert n == 1
    src, n = re.subn(r'TIER2 = \[.*?\]', 'TIER2 = ["FAA", "FBB"]',
                     src, flags=re.S)
    assert n == 1
    src, n = re.subn(r'TIER3 = \[.*?\]', 'TIER3 = ["FCC"]',
                     src, flags=re.S)
    assert n == 1
    assert src.count("00c5555c26d391444509e54de322841fa3269b64"
                     "f3161a50aa507bf1d2bd416f") == 1
    src = src.replace("00c5555c26d391444509e54de322841fa3269b64"
                      "f3161a50aa507bf1d2bd416f", "aa" * 32)
    assert src.count(PIN_CORR2) == 1
    src = src.replace(PIN_CORR2, "bb" * 32)
    script = os.path.join(dst_dir, "corr4_fixture.py")
    with open(script, "w") as f:
        f.write(src)
    shutil.copy(os.path.join(FIX, "fixture_stage1_manifest.json"),
                os.path.join(dst_dir, "stage1_manifest.json"))
    shutil.copy(os.path.join(FIX, "fixture_stage2_addendum.json"),
                os.path.join(dst_dir, "stage2_addendum.json"))
    return script


def write_addendum(dst_dir, inv_path, census, content_hash=None):
    a = {
        "binding_id": "FIXTURE-BINDING", "stage": 2,
        "binding_content_sha256": content_hash
        or fixture_content_hash(),
        "inventory_sha256": sha256_file(inv_path),
        "expected_fires": census,
        "builder_sha256": "ff" * 32,
        "session_table_sha256": "aa" * 32,
        "session": {"id": "FIXTURE-SESSION", "date": "2026-10-29",
                    "operators": ["fixture-op-1", "fixture-op-2"]},
    }
    with open(os.path.join(dst_dir, "stage2_addendum.json"),
              "w") as f:
        json.dump(a, f, indent=1, sort_keys=True)
        f.write("\n")


def corr4_cli(script, inv, out_report):
    return run([sys.executable, script, "--inventory", inv,
                "--inventory-sha", sha256_file(inv),
                "--mode", "pool-counts", "--out-report", out_report])


def part_a():
    w = os.path.join(WORK, "a")
    shutil.rmtree(w, ignore_errors=True)
    os.makedirs(w)
    script = pin_fixture_copy(w)
    inv = os.path.join(FIX, "synth_inventory.jsonl")
    rep = os.path.join(w, "report.json")

    r = corr4_cli(script, inv, rep)
    check("A1 corr4 positive run under fixture staged binding",
          r.returncode == 0 and os.path.exists(rep),
          f"(rc={r.returncode})")
    if r.returncode == 0:
        report = json.load(open(rep))
        check("A1b census reconciled to planted fires (6)",
              report["census_fires_reconciled"] == 6,
              f"({report['census_fires_reconciled']})")
        check("A1c cohort = planted window-complete events (5)",
              report["cohort_events_single_rule_h20"] == 5,
              f"({report['cohort_events_single_rule_h20']})")
        check("A1d report is outcome-blind (no return fields)",
              "outcome_blind" in report
              and not any("return" in k for k in report))

    # tampered inventory: hash no longer matches the addendum pin
    bad_inv = os.path.join(w, "tampered.jsonl")
    with open(inv, "rb") as f:
        data = f.read()
    with open(bad_inv, "wb") as f:
        f.write(data + b"\n")
    r = corr4_cli(script, bad_inv, os.path.join(w, "r2.json"))
    check("A2 tampered inventory refused (addendum hash binding)",
          r.returncode != 0 and "FAIL-CLOSED" in (r.stdout + r.stderr),
          f"(rc={r.returncode})")

    # tampered manifest beside the fixture copy: content drifts
    w3 = os.path.join(WORK, "a3")
    script3 = pin_fixture_copy(w3)
    m = json.load(open(os.path.join(w3, "stage1_manifest.json")))
    m["tiers"]["tier3"] = ["FCX"]
    with open(os.path.join(w3, "stage1_manifest.json"), "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    r = corr4_cli(script3, inv, os.path.join(w3, "r3.json"))
    check("A3 tampered manifest refused by compiled-in content pin",
          r.returncode == 2 and "binding content" in r.stderr,
          f"(rc={r.returncode})")

    # tampered SHIPPED manifest (copy) against the SHIPPED pin
    w3b = os.path.join(WORK, "a3b")
    os.makedirs(w3b)
    shutil.copy(CORR4, os.path.join(w3b, "corr4_shipped_copy.py"))
    m = json.load(open(MANIFEST))
    m["window_end"] = "2024-09-16"
    with open(os.path.join(w3b, "stage1_manifest.json"), "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    r = corr4_cli(os.path.join(w3b, "corr4_shipped_copy.py"), inv,
                  os.path.join(w3b, "r3b.json"))
    check("A3b shipped corr4 pin refuses a drifted manifest copy",
          r.returncode == 2 and "binding content" in r.stderr,
          f"(rc={r.returncode})")

    rows = load_rows(inv)

    def variant(name, new_rows):
        d = os.path.join(WORK, name)
        s = pin_fixture_copy(d)
        p = os.path.join(d, "inv.jsonl")
        write_rows(p, new_rows)
        write_addendum(d, p, census_of(new_rows))
        return s, p, d

    # extra symbol
    extra = rows + [dict(r, symbol="FDD")
                    for r in rows if r["symbol"] == "FAA"]
    s, p, d = variant("a4", extra)
    r = corr4_cli(s, p, os.path.join(d, "r4.json"))
    check("A4 extra symbol refused by tier-membership binding",
          r.returncode == 2 and "unexpected symbol" in r.stderr,
          f"(rc={r.returncode})")

    # missing Tier 3 symbol -> NAMED error
    s, p, d = variant("a5", [r for r in rows
                             if r["symbol"] != "FCC"])
    r = corr4_cli(s, p, os.path.join(d, "r5.json"))
    check("A5 missing Tier 3 -> named TIER3_INVENTORY_MISSING",
          r.returncode == 2 and "TIER3_INVENTORY_MISSING" in r.stderr,
          f"(rc={r.returncode})")

    # missing Tier 2 symbol -> NAMED error
    s, p, d = variant("a6", [r for r in rows
                             if r["symbol"] != "FBB"])
    r = corr4_cli(s, p, os.path.join(d, "r6.json"))
    check("A6 missing Tier 2 -> named TIER2_INVENTORY_MISSING",
          r.returncode == 2 and "TIER2_INVENTORY_MISSING" in r.stderr,
          f"(rc={r.returncode})")

    # out-of-window row
    oow = [dict(r) for r in rows]
    for r in oow:
        if r["symbol"] == "FAA" and r["idx"] == 59:
            r["session_date"] = "2024-12-02"
    s, p, d = variant("a7", oow)
    r = corr4_cli(s, p, os.path.join(d, "r7.json"))
    check("A7 out-of-window row refused by window binding",
          r.returncode == 2 and "outside the sealed window"
          in r.stderr, f"(rc={r.returncode})")

    # census mismatch (addendum census off by one)
    d = os.path.join(WORK, "a8")
    s = pin_fixture_copy(d)
    write_addendum(d, inv, census_of(rows) + 1)
    r = corr4_cli(s, inv, os.path.join(d, "r8.json"))
    check("A8 census mismatch fail-closed vs addendum census",
          r.returncode != 0 and "pinned holdout census"
          in (r.stdout + r.stderr), f"(rc={r.returncode})")

    # addendum referencing the wrong binding content
    d = os.path.join(WORK, "a9")
    s = pin_fixture_copy(d)
    write_addendum(d, inv, census_of(rows), content_hash="00" * 32)
    r = corr4_cli(s, inv, os.path.join(d, "r9.json"))
    check("A9 addendum w/ wrong content ref refused",
          r.returncode == 2 and "binding content" in r.stderr,
          f"(rc={r.returncode})")

    # override attempts: the interface itself rejects them
    for flag, val in (("--symbols", "FAA"), ("--window", "2023-10-19"),
                      ("--manifest", "x.json")):
        rep_o = os.path.join(w, "ro.json")
        r = run([sys.executable, script, "--inventory", inv,
                 "--inventory-sha", sha256_file(inv),
                 "--mode", "pool-counts", "--out-report", rep_o,
                 flag, val])
        check(f"A10 override attempt {flag} rejected by interface",
              r.returncode == 2 and not os.path.exists(rep_o),
              f"(rc={r.returncode})")

    # shipped package state: no addendum exists -> named refusal
    check("A11a package ships without a Stage-2 addendum",
          not os.path.exists(os.path.join(HERE,
                                          "stage2_addendum.json")))
    r = corr4_cli(CORR4, inv, os.path.join(w, "r11.json"))
    check("A11b shipped corr4 refuses: STAGE2_ADDENDUM_MISSING",
          r.returncode == 2 and "STAGE2_ADDENDUM_MISSING" in r.stderr,
          f"(rc={r.returncode})")

    # corr2 control: the pinned predecessor refuses this domain
    r = run([sys.executable, CORR2, "--inventory", inv,
             "--inventory-sha", sha256_file(inv),
             "--mode", "pool-counts"])
    check("A12 corr2 (pinned) refuses fixture holdout inventory "
          "with the DEV census - the STOP blocker",
          r.returncode != 0 and "P7 census 2892"
          in (r.stdout + r.stderr), f"(rc={r.returncode})")


# =====================================================================
# Part B - AST audit corr4 vs corr2
# =====================================================================
def part_b():
    def funcs(path):
        tree = ast.parse(open(path).read())
        out, classes = {}, set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
                out[node.name] = ast.dump(node)
            elif isinstance(node, ast.ClassDef):
                classes.add(node.name)
        return out, tree, classes

    f2, t2, c2 = funcs(CORR2)
    f4, t4, c4 = funcs(CORR4)
    renamed = {"_check_dev_ts": "_check_window_ts"}
    changed_allowed = {"run_pool_counts", "main", "_check_window_ts",
                       "_analysis_impl"}
    new_allowed = {"_package_path", "load_stage1_manifest",
                   "load_stage2_addendum", "verify_holdout_binding"}
    only4 = set(f4) - set(f2) - {"_check_window_ts"}
    only2 = set(f2) - set(f4) - {"_check_dev_ts"}
    check("B1 corr4-only functions are exactly the binding quartet",
          only4 == new_allowed, f"({sorted(only4)})")
    check("B2 corr2-only function is exactly _check_dev_ts (renamed)",
          only2 == set(), f"({sorted(only2)})")
    diffs = []
    for name, dump in f2.items():
        if name in renamed:
            continue
        if name not in f4:
            diffs.append(f"missing:{name}")
        elif f4[name] != dump and name not in changed_allowed:
            diffs.append(name)
    check("B3 all non-binding shared functions AST-identical",
          not diffs, f"({diffs})")

    def normalize(dump):
        return (dump.replace("_check_dev_ts", "_check_window_ts")
                    .replace("DEV_START", "WINDOW_START")
                    .replace("DEV_END", "WINDOW_END")
                    .replace("non-DEV timestamp",
                             "out-of-window timestamp"))
    check("B3b _analysis_impl identical modulo the renamed window "
          "check at its two call sites",
          normalize(f2["_analysis_impl"]) == f4["_analysis_impl"])
    check("B3c _check_window_ts identical to _check_dev_ts modulo "
          "the window binding tokens",
          normalize(f2["_check_dev_ts"]) == f4["_check_window_ts"])
    check("B3d classes unchanged", c2 == c4, f"({sorted(c4)})")

    def assigns(tree):
        out = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        out[t.id] = ast.dump(node.value)
        return out

    a2, a4 = assigns(t2), assigns(t4)
    removed = set(a2) - set(a4)
    added = set(a4) - set(a2)
    changed = {k for k in set(a2) & set(a4) if a2[k] != a4[k]}
    check("B4 module constants: removed = DEV binding only",
          removed == {"EXPECTED_FIRES", "DEV_START", "DEV_END"},
          f"({sorted(removed)})")
    check("B5 module constants: added = CORR4 binding only",
          added == {"WINDOW_START", "WINDOW_END", "TIER2", "TIER3",
                    "PINNED_BINDING_CONTENT_SHA256",
                    "SESSION_TABLE_SHA256", "CORR2_SOURCE_SHA256",
                    "STAGE1_MANIFEST_NAME", "STAGE2_ADDENDUM_NAME",
                    "MANIFEST_FILE_KEYS", "MANIFEST_CONTENT_KEYS",
                    "ADDENDUM_KEYS"},
          f"({sorted(added)})")
    check("B6 no other module constant changed (ladder/seeds/pins)",
          changed == set(), f"({sorted(changed)})")
    check("B7 corr2_src copy hashes to the P11 pin",
          sha256_file(CORR2) == PIN_CORR2)


# =====================================================================
# Part C - builder
# =====================================================================
def synth_raw_capture(path, sessions, poison=False):
    """Fabricated TwelveData-shaped capture: ET wall-clock hourly
    bars 09:30 -> session close, ascending invented prices. Mirrors
    the CORR3-draft fixture generator, which passed the frozen
    admission gates against the real session table."""
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


def window_sessions():
    table = json.load(open(TABLE))
    m = json.load(open(MANIFEST))
    return [(s["date"], s["close"]) for s in table["sessions"]
            if m["window_start"] <= s["date"] <= m["window_end"]]


def content_sha_of(manifest):
    keys = ("binding_id", "stage", "window_start", "window_end",
            "tiers", "session_table_sha256", "corr2_source_sha256",
            "engine", "raw_capture")
    return canonical_sha({k: manifest[k] for k in keys})


def write_receipt(raw_dir):
    """Fabricated raw-capture receipt manifest for the raw files
    currently in raw_dir: exact pinned symbol set in pinned
    order, per-symbol sha256, receipt root = canonical sha256 of
    the per-symbol map. Mirrors the format the builder verifies
    (fixtures may carry fabricated pins; the ORDER of
    verification is what the suite proves)."""
    m = json.load(open(MANIFEST))
    symbols = m["tiers"]["tier2"] + m["tiers"]["tier3"]
    per_symbol = {s: sha256_file(os.path.join(raw_dir, f"{s}.json"))
                  for s in symbols}
    receipt = {
        "receipt_id": "SUITE-RECEIPT",
        "binding_content_sha256": content_sha_of(m),
        "symbols": symbols,
        "per_symbol_sha256": per_symbol,
        "receipt_root_sha256": canonical_sha(per_symbol),
    }
    with open(os.path.join(raw_dir, "receipt_manifest.json"),
              "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)
        f.write("\n")
    return receipt


def receipt_pins(raw_dir):
    rp = os.path.join(raw_dir, "receipt_manifest.json")
    receipt = json.load(open(rp))
    return sha256_file(rp), receipt["receipt_root_sha256"]


def make_auth(path, raw_dir=None, **over):
    m = json.load(open(MANIFEST))
    if raw_dir is not None:
        file_sha, root = receipt_pins(raw_dir)
    else:
        file_sha, root = "00" * 32, "11" * 32
    a = {
        "auth_id": "SUITE-AUTH",
        "binding_content_sha256": content_sha_of(m),
        "builder_sha256": sha256_file(BUILDER),
        "window_start": m["window_start"],
        "window_end": m["window_end"],
        "tiers": m["tiers"],
        "mode": "TEXT0_STAGE2_INVENTORY_BUILD",
        "session_id": "SUITE-SESSION",
        "operators": ["suite-op-a", "suite-op-b"],
        "date": "2026-10-29",
        "raw_receipt_manifest_sha256": file_sha,
        "raw_receipt_root_sha256": root,
    }
    a.update(over)
    with open(path, "w") as f:
        json.dump(a, f, indent=1, sort_keys=True)
        f.write("\n")
    return path


def make_session(base, name, raw_source, tamper=None):
    """A session layout for a builder variant: <base>/<name>/
    holds session_auth.json beside raw/ (the derived layout).
    The receipt is written over the UNTAMPERED copy and the auth
    names its pins; `tamper(raw_dir)` then mutates the raw bytes
    so the negative fixtures exercise the pre-parse binding."""
    sess = os.path.join(base, name)
    os.makedirs(sess)
    raw_dir = os.path.join(sess, "raw")
    shutil.copytree(raw_source, raw_dir)
    write_receipt(raw_dir)
    auth = make_auth(os.path.join(sess, "session_auth.json"),
                     raw_dir=raw_dir)
    if tamper is not None:
        tamper(raw_dir)
    return sess, raw_dir, auth


def builder_cli(builder, auth, out, summ, timeout=1500):
    # No --raw-dir exists: the builder derives the raw directory
    # from the authorization's location (session layout).
    return run([sys.executable, builder,
                "--session-auth", auth, "--out", out,
                "--summary", summ], timeout=timeout)


def part_c():
    w = os.path.join(WORK, "c")
    shutil.rmtree(w, ignore_errors=True)
    os.makedirs(w)
    sessions = window_sessions()
    check("C0 pinned window subset = 227 sessions",
          len(sessions) == 227, f"({len(sessions)})")
    m = json.load(open(MANIFEST))
    symbols = m["tiers"]["tier2"] + m["tiers"]["tier3"]
    rawdir = os.path.join(w, "raw")
    os.makedirs(rawdir)
    for sym in symbols:
        synth_raw_capture(os.path.join(rawdir, f"{sym}.json"),
                          sessions)
    write_receipt(rawdir)
    auth = make_auth(os.path.join(w, "auth.json"), raw_dir=rawdir)
    out = os.path.join(w, "inventory.jsonl")
    summ = os.path.join(w, "summary.json")

    # override attempts: removed flags are rejected by argparse.
    # --raw-dir is among them: the raw directory is derived from
    # the session layout, never a caller input.
    for flag in ("--symbols", "--manifest", "--session-table",
                 "--mode", "--raw-dir"):
        r = run([sys.executable, BUILDER,
                 "--session-auth", auth, "--out", out,
                 "--summary", summ, flag, "x"])
        check(f"C1 builder interface rejects {flag}",
              r.returncode == 2, f"(rc={r.returncode})")

    # missing / broken authorizations refuse before any build
    r = builder_cli(BUILDER, os.path.join(w, "nope.json"),
                    out, summ, timeout=60)
    check("C2 build refuses without a session authorization",
          r.returncode == 2 and "SESSION_AUTH_MISSING"
          in r.stdout and not os.path.exists(out),
          f"(rc={r.returncode})")
    bad_auth = make_auth(os.path.join(w, "auth_bad.json"),
                         binding_content_sha256="00" * 32)
    r = builder_cli(BUILDER, bad_auth, out, summ, timeout=60)
    check("C3 build refuses auth naming wrong binding content",
          r.returncode == 2 and not os.path.exists(out),
          f"(rc={r.returncode})")
    one_op = make_auth(os.path.join(w, "auth_oneop.json"),
                       operators=["solo"])
    r = builder_cli(BUILDER, one_op, out, summ, timeout=60)
    check("C4 build refuses a single-operator authorization",
          r.returncode == 2 and not os.path.exists(out),
          f"(rc={r.returncode})")

    # missing Tier 3 capture -> NAMED exit-3 error (the receipt
    # pins the full set; the file itself is then removed)
    _, _, auth_m = make_session(
        w, "sess_missing", rawdir,
        tamper=lambda rd: os.remove(os.path.join(rd, "TWLO.json")))
    out_m = os.path.join(w, "inventory_missing.jsonl")
    r = builder_cli(BUILDER, auth_m, out_m,
                    os.path.join(w, "summary_missing.json"),
                    timeout=60)
    check("C5 missing Tier 3 capture -> named TIER3_CAPTURE_MISSING",
          r.returncode == 3 and "TIER3_CAPTURE_MISSING: TWLO"
          in r.stdout and not os.path.exists(out_m),
          f"(rc={r.returncode})")

    # poisoned capture whose bytes ARE receipt-pinned -> the hash
    # binding passes and the volume gate STOPs the build
    sess_p, _, _ = make_session(w, "sess_poison", rawdir)
    raw_poison = os.path.join(sess_p, "raw")
    synth_raw_capture(os.path.join(raw_poison, "AAPL.json"),
                      sessions, poison=True)
    write_receipt(raw_poison)
    auth_p = make_auth(os.path.join(sess_p, "session_auth.json"),
                       raw_dir=raw_poison)
    out_p = os.path.join(w, "inventory_poison.jsonl")
    r = builder_cli(BUILDER, auth_p, out_p,
                    os.path.join(w, "summary_poison.json"))
    check("C6 poisoned capture STOPs the build, no inventory",
          r.returncode == 2 and "STOP AAPL" in r.stdout
          and not os.path.exists(out_p),
          f"(rc={r.returncode})")

    # --- pre-parse hash binding negatives -----------------------
    # C9a: a capture that parses cleanly (shifted prices - it
    # would change the inventory if it were ever parsed) but
    # whose bytes fail the receipt pin is rejected BEFORE parse.
    def tamper_clean(rd):
        p = os.path.join(rd, "AAPL.json")
        raw = json.load(open(p))
        for v in raw["values"]:
            for k in ("open", "high", "low", "close"):
                v[k] = v[k] + 7.0
        with open(p, "w") as f:
            json.dump(raw, f)

    _, _, auth_9a = make_session(w, "sess_badhash_clean", rawdir,
                                 tamper=tamper_clean)
    out_9a = os.path.join(w, "inventory_badhash_clean.jsonl")
    r = builder_cli(BUILDER, auth_9a, out_9a,
                    os.path.join(w, "summary_badhash_clean.json"),
                    timeout=60)
    check("C9a clean-parsing capture failing its pin rejected "
          "before parse (RAW_CAPTURE_HASH_MISMATCH)",
          r.returncode == 2 and "RAW_CAPTURE_HASH_MISMATCH: AAPL"
          in r.stdout and not os.path.exists(out_9a),
          f"(rc={r.returncode})")

    # C9b: an UNPARSEABLE capture failing its pin fails with the
    # hash error, not a parse/gate error - proof the hash check
    # runs before any parsing of capture contents.
    def tamper_garbage(rd):
        with open(os.path.join(rd, "AAPL.json"), "w") as f:
            f.write("{this is not json")

    _, _, auth_9b = make_session(w, "sess_badhash_garbage", rawdir,
                                 tamper=tamper_garbage)
    out_9b = os.path.join(w, "inventory_badhash_garbage.jsonl")
    r = builder_cli(BUILDER, auth_9b, out_9b,
                    os.path.join(w, "summary_badhash_garbage.json"),
                    timeout=60)
    check("C9b unparseable capture failing its pin rejected "
          "before parse (RAW_CAPTURE_HASH_MISMATCH)",
          r.returncode == 2 and "RAW_CAPTURE_HASH_MISMATCH: AAPL"
          in r.stdout and "STOP AAPL" not in r.stdout
          and not os.path.exists(out_9b),
          f"(rc={r.returncode})")

    # C10: an extra, unlisted file in the raw directory
    def tamper_extra(rd):
        shutil.copy(os.path.join(rd, "AAPL.json"),
                    os.path.join(rd, "UNLISTED.json"))

    _, _, auth_10 = make_session(w, "sess_extra", rawdir,
                                 tamper=tamper_extra)
    out_10 = os.path.join(w, "inventory_extra.jsonl")
    r = builder_cli(BUILDER, auth_10, out_10,
                    os.path.join(w, "summary_extra.json"),
                    timeout=60)
    check("C10 extra unlisted raw file rejected "
          "(RAW_CAPTURE_UNLISTED_FILE)",
          r.returncode == 2 and "RAW_CAPTURE_UNLISTED_FILE"
          in r.stdout and not os.path.exists(out_10),
          f"(rc={r.returncode})")

    # C11: receipt manifest tampered after the auth pinned it
    def tamper_receipt(rd):
        rp = os.path.join(rd, "receipt_manifest.json")
        receipt = json.load(open(rp))
        receipt["per_symbol_sha256"]["AAPL"] = "00" * 32
        with open(rp, "w") as f:
            json.dump(receipt, f, indent=1, sort_keys=True)

    _, _, auth_11 = make_session(w, "sess_receipt_tamper", rawdir,
                                 tamper=tamper_receipt)
    out_11 = os.path.join(w, "inventory_receipt_tamper.jsonl")
    r = builder_cli(BUILDER, auth_11, out_11,
                    os.path.join(w, "summary_receipt_tamper.json"),
                    timeout=60)
    check("C11 tampered receipt rejected "
          "(RAW_RECEIPT_MANIFEST_HASH_MISMATCH)",
          r.returncode == 2
          and "RAW_RECEIPT_MANIFEST_HASH_MISMATCH" in r.stdout
          and not os.path.exists(out_11),
          f"(rc={r.returncode})")

    # C12: the authorization names the wrong receipt hash
    sess_12, raw_12, _ = make_session(w, "sess_auth_receipt", rawdir)
    auth_12 = make_auth(os.path.join(sess_12, "session_auth.json"),
                        raw_dir=raw_12,
                        raw_receipt_manifest_sha256="00" * 32)
    out_12 = os.path.join(w, "inventory_auth_receipt.jsonl")
    r = builder_cli(BUILDER, auth_12, out_12,
                    os.path.join(w, "summary_auth_receipt.json"),
                    timeout=60)
    check("C12 auth naming wrong receipt hash rejected "
          "(RAW_RECEIPT_MANIFEST_HASH_MISMATCH)",
          r.returncode == 2
          and "RAW_RECEIPT_MANIFEST_HASH_MISMATCH" in r.stdout
          and not os.path.exists(out_12),
          f"(rc={r.returncode})")

    # C13: a capture replaced by a symlink (path substitution)
    def tamper_symlink(rd):
        p = os.path.join(rd, "NVDA.json")
        os.remove(p)
        os.symlink(os.path.join(rd, "AAPL.json"), p)

    _, _, auth_13 = make_session(w, "sess_symlink", rawdir,
                                 tamper=tamper_symlink)
    out_13 = os.path.join(w, "inventory_symlink.jsonl")
    r = builder_cli(BUILDER, auth_13, out_13,
                    os.path.join(w, "summary_symlink.json"),
                    timeout=60)
    check("C13 symlinked capture rejected "
          "(RAW_CAPTURE_PATH_SUBSTITUTED)",
          r.returncode == 2 and "RAW_CAPTURE_PATH_SUBSTITUTED: NVDA"
          in r.stdout and not os.path.exists(out_13),
          f"(rc={r.returncode})")

    # full fabricated build over the real pinned window
    r = builder_cli(BUILDER, auth, out, summ)
    ok = r.returncode == 0 and os.path.exists(out)
    check("C7 full fabricated build (30 symbols x 227 sessions)",
          ok, f"(rc={r.returncode}, "
              f"tail={(r.stdout + r.stderr)[-200:]})")
    inv_sha = None
    if ok:
        rows = load_rows(out)
        keys = {"symbol", "idx", "ts", "session_date",
                "session_ordinal", "bin", "close", "atr", "atr_pct",
                "ema21", "ema55", "ema200", "signal",
                "in_generator_domain"}
        check("C7b rows carry exactly the corr4 row schema",
              all(set(x) == keys for x in rows))
        check("C7c 452 bars per symbol (2*227 - 2 early closes)",
              all(sum(1 for x in rows if x["symbol"] == s) == 452
                  for s in symbols))
        check("C7d every symbol covers all 227 session ordinals",
              all({x["session_ordinal"] for x in rows
                   if x["symbol"] == s} == set(range(227))
                  for s in symbols))
        s7 = json.load(open(summ))
        inv_sha = sha256_file(out)
        check("C7e summary hash + census reconcile with inventory",
              s7["inventory_sha256"] == inv_sha
              and s7["census_fires_in_generator_domain"]
              == census_of(rows)
              and s7["stage2_addendum_inputs"]["expected_fires"]
              == census_of(rows))
        check("C7f summary binding block pins builder + manifest",
              s7["binding"]["builder_sha256"] == sha256_file(BUILDER)
              and s7["binding"]["stage1_manifest_file_sha256"]
              == sha256_file(MANIFEST))
        receipt = json.load(open(os.path.join(
            rawdir, "receipt_manifest.json")))
        check("C7g summary input hashes are the pre-parse verified "
              "receipt pins (+ receipt pins in binding block)",
              s7["input_file_sha256"]
              == receipt["per_symbol_sha256"]
              and s7["binding"]["raw_receipt_root_sha256"]
              == receipt["receipt_root_sha256"]
              and s7["binding"]["raw_receipt_manifest_sha256"]
              == sha256_file(os.path.join(
                  rawdir, "receipt_manifest.json")))

    # self-containment: the same build in a copied package tree
    copy_root = os.path.join(w, "pkgcopy")
    shutil.copytree(HERE, copy_root,
                    ignore=shutil.ignore_patterns("work", "__pycache__"))
    out_c = os.path.join(w, "inventory_copy.jsonl")
    r = builder_cli(os.path.join(copy_root,
                                 "build_holdout_inventory_corr4.py"),
                    auth, out_c,
                    os.path.join(w, "summary_copy.json"))
    check("C8 copied-tree build reproduces the identical inventory",
          r.returncode == 0 and inv_sha is not None
          and sha256_file(out_c) == inv_sha,
          f"(rc={r.returncode})")


# =====================================================================
# Part D - package integrity
# =====================================================================
def part_d():
    bad = []
    for line in open(os.path.join(HERE, "SHA256_MANIFEST.txt")):
        line = line.strip()
        if not line:
            continue
        want, rel = line.split("  ", 1)
        p = os.path.join(HERE, rel)
        if not os.path.exists(p) or sha256_file(p) != want:
            bad.append(rel)
    check("D1 SHA256_MANIFEST verifies for every package file",
          not bad, f"({bad})")

    m = json.load(open(MANIFEST))
    keys = ("binding_id", "stage", "window_start", "window_end",
            "tiers", "session_table_sha256", "corr2_source_sha256",
            "engine", "raw_capture")
    content_sha = canonical_sha({k: m[k] for k in keys})
    lit4 = re.search(r'PINNED_BINDING_CONTENT_SHA256 = '
                     r'"([0-9a-f]{64})"', open(CORR4).read()).group(1)
    litb = re.search(r'PINNED_BINDING_CONTENT_SHA256 = '
                     r'"([0-9a-f]{64})"',
                     open(BUILDER).read()).group(1)
    check("D2 manifest content hash == literals in corr4 + builder",
          content_sha == lit4 == litb, f"({content_sha[:12]}...)")

    d = json.load(open(os.path.join(HERE, "tier_derivation.json")))
    t2 = d["tier2_derivation"]
    derived2 = sorted(set(t2["ux51_equities_ordered"])
                      - set(t2["quarantined_ho_legs_23"])
                      - {t2["plus_first_capture"],
                         t2["plus_pilot_step1"]})
    t3 = d["tier3_derivation"]
    derived3 = sorted(set(t3["frozen_12"]) - set(t3["excluded"]))
    check("D3 tier membership re-derives (19 Tier 2 + 11 Tier 3)",
          derived2 == m["tiers"]["tier2"] == t2["tier2_result_sorted"]
          and derived3 == m["tiers"]["tier3"]
          == t3["tier3_result_sorted"]
          and len(derived2) == 19 and len(derived3) == 11)

    card = open(os.path.join(HERE,
                             "DECISION_CARD_TIER3_BYTES.md")).read()
    check("D4 DECISION CARD names both named errors + the absence",
          "TIER3_CAPTURE_MISSING" in card
          and "TIER3_INVENTORY_MISSING" in card
          and "do not exist" in card)

    pkg = open(os.path.join(HERE, "PACKAGE.md")).read()
    check("D5 PACKAGE.md states the staged design AND the "
          "corrected inventory-hash disclosure (no absolute "
          "no-post-access-pin claim)",
          "Stage 1" in pkg and "Stage 2" in pkg
          and "builder emits the inventory hash" in pkg
          and "At no point does a step that has touched sealed "
              "data create or alter a pin" not in pkg
          and "RAW_CAPTURE_HASH_MISMATCH" in pkg
          and "receipt" in pkg)

    # fixture determinism: regenerate and compare bytes
    tmp = os.path.join(WORK, "fixture_regen")
    shutil.rmtree(tmp, ignore_errors=True)
    r = run([sys.executable,
             os.path.join(FIX, "make_fixtures.py"), tmp])
    same = r.returncode == 0 and all(
        sha256_file(os.path.join(tmp, f)) == sha256_file(
            os.path.join(FIX, f))
        for f in ("synth_inventory.jsonl",
                  "fixture_stage1_manifest.json",
                  "fixture_stage2_addendum.json"))
    check("D6 committed fixtures regenerate byte-identically", same)


if __name__ == "__main__":
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    part_a()
    part_b()
    part_c()
    part_d()
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} "
          "checks passed")
    if failed:
        print("FAILED:", failed)
        sys.exit(1)
