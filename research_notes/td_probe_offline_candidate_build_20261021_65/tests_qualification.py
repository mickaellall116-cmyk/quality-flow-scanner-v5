#!/usr/bin/env python3
"""Synthetic qualification harness — task -65 r1.

ONE attempt. Cases run in order; the FIRST failure stops the run.
Warnings are errors during case execution. Output is a single
deterministic JSON object on stdout (no wall-clock values, no temp
paths). A byte-identity repeat is run by the operator only if this
run passes.

Coverage maps to spec section 6's minimum case list (see case names).
SYNTHETIC FIXTURES ONLY — no vendor contact of any kind.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import warnings
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
FIX = HERE / "fixtures"
sys.path.insert(0, str(HERE))

import account_preflight as ap  # noqa: E402
import probe_analyzer as az  # noqa: E402
import probe_runner as rn  # noqa: E402
import temporal_gate as tg  # noqa: E402


def _load_fixture_module():
    spec = importlib.util.spec_from_file_location(
        "fake_transport_module", FIX / "fake_transport_module.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FTM = _load_fixture_module()
MANIFEST_PATH = HERE / "probe_manifest.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text())
MANIFEST_SHA = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
PILOT = rn.load_pilot(REPO_ROOT)


class CountDataTransport:
    def __init__(self, fail_symbols=(), big_symbols=()):
        self.calls = []
        self.fail_symbols = set(fail_symbols)
        self.big_symbols = set(big_symbols)

    def fetch(self, url):
        self.calls.append(url)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        sym = q["symbol"][0]
        if sym in self.fail_symbols:
            return 503, {}, b'{"status":"error"}'
        if sym in self.big_symbols:
            bars = []
            for i in range(5000):
                bars.append({
                    "datetime": f"2024-01-{(i % 28) + 1:02d} "
                                f"{i % 24:02d}:30:00",
                    "open": "10.00", "high": "10.00", "low": "10.00",
                    "close": "10.00", "volume": "100"})
            obj = {"meta": {"symbol": sym, "interval": "1h"},
                   "values": bars, "status": "ok"}
            return 200, {"content-type": "application/json"}, \
                json.dumps(obj).encode()
        return 200, {"content-type": "application/json"}, \
            FTM._payload(sym)


class CountUsageTransport:
    def __init__(self, status=200):
        self.calls = []
        self.status = status

    def fetch(self, url):
        self.calls.append(url)
        if self.status != 200:
            return self.status, {}, b'{"status":"error"}'
        return 200, {"content-type": "application/json"}, json.dumps(
            {"current_usage": 3, "plan_limit": 800}).encode()


def make_driver(store, transport, clock):
    return PILOT.ManifestDriver(
        MANIFEST_PATH, Path(store),
        PILOT.RollingCreditLimiter(8, 800, clock=clock),
        transport, clock=clock, sleeper=lambda s: None,
        preflight=lambda: [])


def expect_refusal(fn, tag):
    try:
        fn()
    except rn.RunnerRefusal as e:
        assert e.tag == tag, f"tag {e.tag} != {tag}"
        return
    raise AssertionError(f"no refusal raised, wanted {tag}")


CTX = {}


def q01_scope_isolation():
    rn.validate_scope(MANIFEST)
    bad = json.loads(json.dumps(MANIFEST))
    bad["requests"].append(dict(bad["requests"][0],
                                request_id="REQ-SPT-01"))
    expect_refusal(lambda: rn.validate_scope(bad),
                   "UNEXPECTED_REQUEST_ID")
    bad2 = json.loads(json.dumps(MANIFEST))
    for r in bad2["requests"]:
        if r["request_id"] == "REQ-ADJ-01N":
            r["adjust"] = "splits"
    expect_refusal(lambda: rn.validate_scope(bad2),
                   "SCOPE_FIELD_MISMATCH")
    bad3 = json.loads(json.dumps(MANIFEST))
    bad3["requests"][0]["max_attempts"] = 3
    expect_refusal(lambda: rn.validate_scope(bad3),
                   "SCOPE_FIELD_MISMATCH")
    bad4 = json.loads(json.dumps(MANIFEST))
    bad4["requests"] = bad4["requests"][:-1]
    expect_refusal(lambda: rn.validate_scope(bad4), "SCOPE_INCOMPLETE")
    return "allowlist accepts packet shape; rejects SPOT leg, " \
           "adjust flip, attempts=3, missing leg"


def q02_none_splits_mapping():
    with tempfile.TemporaryDirectory() as td:
        drv = make_driver(td, CountDataTransport(),
                          FTM.FakeClock(1700000000.0, 61.0))
        specs = {r["request_id"]: drv._to_spec(r)
                 for r in MANIFEST["requests"]}
        assert specs["REQ-ADJ-01"].adjust == "splits"
        assert specs["REQ-ADJ-01N"].adjust == "none"
        assert specs["REQ-ADJ-02N"].adjust == "none"
        _, params = drv.wrapper._build_url(specs["REQ-ADJ-01N"])
        assert params["adjust"] == "none"
        _, params = drv.wrapper._build_url(specs["REQ-ADJ-01"])
        assert params["adjust"] == "splits"
    return "twins map to adjust=none; bases to adjust=splits in URL"


def q03_attempt_ceiling_arithmetic():
    assert rn.program_ceiling(MANIFEST) == (12, 24)
    b = MANIFEST["budget"]
    assert b["expected_total"] == 9 and b["max_total"] == 18
    pc = b["program_ceiling_incl_usage_preflight"]
    assert pc["expected_total"] == 12 and pc["hard_max_total"] == 24
    return "expected 12 (9 data + 3 usage); hard max 24 (18 + 6)"


def q04_attempt_cap_live():
    with tempfile.TemporaryDirectory() as td:
        t = CountDataTransport(fail_symbols=("NVDA",))
        # NVDA splits (ADJ-01) is D1's first request; it must stop
        # at exactly 2 attempts (manifest cap), never 3.
        drv = make_driver(td, t, FTM.FakeClock(1700000000.0, 61.0))
        outcomes = drv.run_day("D1")
        assert outcomes[0].request_id == "REQ-ADJ-01"
        assert outcomes[0].attempts == 2, outcomes[0].attempts
        assert outcomes[0].outcome == "RETRIES_EXHAUSTED"
        assert len(t.calls) == 2
    return "failing request stops at exactly 2 attempts"


def q05_no_pagination():
    with tempfile.TemporaryDirectory() as td:
        t = CountDataTransport(big_symbols=("NVDA",))
        drv = make_driver(td, t, FTM.FakeClock(1700000000.0, 61.0))
        outcomes = drv.run_day("D1")
        ids = [o.request_id for o in outcomes]
        assert ids == ["REQ-ADJ-01", "REQ-ADJ-02", "REQ-ADJ-03",
                       "REQ-ADJ-01N", "REQ-ADJ-02N"], ids
        assert all(o.outcome == "OK" for o in outcomes)
        assert len(t.calls) == 5
        snap = json.loads((Path(td) / "REQ-ADJ-01.json").read_text())
        assert len(snap["values"]) == 5000
    return "5000-row ADJ response fires no pagination child"


def q06_usage_failure_before_data():
    with tempfile.TemporaryDirectory() as td:
        data = CountDataTransport()
        usage = CountUsageTransport(status=503)
        try:
            rn.run_probe_day(
                repo_root=REPO_ROOT, manifest_path=MANIFEST_PATH,
                manifest_sha256=MANIFEST_SHA, day="D1",
                store_dir=Path(td) / "store", data_transport=data,
                usage_transport=usage,
                clock=FTM.FakeClock(1700000000.0, 7.0),
                sleeper=lambda s: None)
        except RuntimeError as e:
            assert "USAGE_RETRIES_EXHAUSTED" in str(e), str(e)
        else:
            raise AssertionError("preflight failure did not abort")
        assert len(data.calls) == 0
        assert len(usage.calls) == 2
    return "usage 503x2 aborts before any data fetch"


def q07_d1_run_and_usage_once_per_day():
    td = tempfile.mkdtemp()
    CTX["store"] = Path(td) / "store"
    data = CountDataTransport()
    usage = CountUsageTransport()
    clock = FTM.FakeClock(1700000000.0, 7.0)
    s1 = rn.run_probe_day(
        repo_root=REPO_ROOT, manifest_path=MANIFEST_PATH,
        manifest_sha256=MANIFEST_SHA, day="D1",
        store_dir=CTX["store"], data_transport=data,
        usage_transport=usage, clock=clock, sleeper=lambda s: None)
    assert s1["ok"] and s1["usage_attempts"] == 1
    assert len(usage.calls) == 1 and len(data.calls) == 5
    s2 = rn.run_probe_day(
        repo_root=REPO_ROOT, manifest_path=MANIFEST_PATH,
        manifest_sha256=MANIFEST_SHA, day="D1",
        store_dir=CTX["store"], data_transport=data,
        usage_transport=usage,
        clock=FTM.FakeClock(1700000000.0, 7.0),
        sleeper=lambda s: None)
    assert all(o["outcome"] == "SKIPPED_RESUMED"
               for o in s2["outcomes"])
    assert len(usage.calls) == 1, "usage preflight ran twice in a day"
    assert len(data.calls) == 5
    CTX["summary_d1"] = s1
    return "D1 OK; resume skips all; usage preflight exactly once/day"


def q08_sanitized_receipts():
    store = CTX["store"]
    blobs = []
    for p in sorted(store.glob("*.receipt.json")) + \
            sorted(store.glob("*.attempts.jsonl")):
        blobs.append(p.read_text())
    joined = "\n".join(blobs).lower()
    assert "apikey" not in joined
    assert "api_key" not in joined
    usage_rcpt = json.loads(
        (store / "api_usage.D1.receipt.json").read_text())
    assert usage_rcpt["params"] == {"endpoint": "/api_usage"}
    assert usage_rcpt["verdict"] == "PASS"
    return "no key material in any receipt/attempt log"


def q09_base_linkage():
    bad = json.loads(json.dumps(MANIFEST))
    rev = next(r for r in bad["requests"]
               if r["request_id"] == "REQ-ADJ-01R7")
    bad["requests"].remove(rev)
    bad["requests"].insert(0, rev)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad_manifest.json"
        p.write_text(json.dumps(bad))
        try:
            PILOT.ManifestDriver(
                p, Path(td) / "s",
                PILOT.RollingCreditLimiter(8, 800), CountDataTransport(),
                preflight=lambda: [])
        except ValueError as e:
            assert "base_request_id" in str(e)
        else:
            raise AssertionError("REV-before-base manifest accepted")
    with tempfile.TemporaryDirectory() as td:
        expect_refusal(
            lambda: rn.run_probe_day(
                repo_root=REPO_ROOT, manifest_path=MANIFEST_PATH,
                manifest_sha256=MANIFEST_SHA, day="D7",
                store_dir=Path(td) / "store",
                data_transport=CountDataTransport(),
                usage_transport=CountUsageTransport(),
                clock=FTM.FakeClock(1700000000.0, 7.0),
                sleeper=lambda s: None),
            "BASE_RECEIPT_MISSING")
    return "manifest rejects REV-before-base; D7 without base refuses"


def _gate_store(td, receipt_name="nvda_splits_uniform.receipt.json",
                snap_src="nvda_splits_uniform.json", tamper=False):
    store = Path(td)
    body = (FIX / snap_src).read_bytes()
    if tamper:
        body = body[:-2] + b"xx"
    (store / "REQ-ADJ-01.json").write_bytes(body)
    (store / "REQ-ADJ-01.receipt.json").write_bytes(
        (FIX / receipt_name).read_bytes())
    return store


def q10_temporal_boundaries():
    rev7 = next(r for r in MANIFEST["requests"]
                if r["request_id"] == "REQ-ADJ-01R7")
    rev30 = next(r for r in MANIFEST["requests"]
                 if r["request_id"] == "REQ-ADJ-01R30")
    B = 1_760_000_000_000
    D = 86_400_000
    with tempfile.TemporaryDirectory() as td:
        store = _gate_store(td)

        def at(now, req=rev7):
            return tg.check_rev_eligibility(store, MANIFEST, req, now)

        for now, want_ok in ((B + 7 * D - 1, False), (B + 7 * D, True),
                             (B + 7 * D + 1, True)):
            if want_ok:
                assert at(now)["eligible"] is True
            else:
                try:
                    at(now)
                except tg.GateRefusal as e:
                    assert e.tag == "REV_NOT_YET_ELIGIBLE"
                else:
                    raise AssertionError(f"early REV accepted {now}")
        try:
            at(B + 30 * D - 1, rev30)
        except tg.GateRefusal as e:
            assert e.tag == "REV_NOT_YET_ELIGIBLE"
        else:
            raise AssertionError("early REV30 accepted")
        assert at(B + 30 * D, rev30)["eligible"] is True
        try:
            at(B - 1)
        except tg.GateRefusal as e:
            assert e.tag == "BASE_TS_FUTURE"
        else:
            raise AssertionError("future base accepted")
    with tempfile.TemporaryDirectory() as td:
        store = _gate_store(td, tamper=True)
        try:
            tg.check_rev_eligibility(store, MANIFEST, rev7, B + 7 * D)
        except tg.GateRefusal as e:
            assert e.tag == "BASE_EVIDENCE_TAMPERED"
        else:
            raise AssertionError("tampered snapshot accepted")
    with tempfile.TemporaryDirectory() as td:
        store = _gate_store(td, "nvda_splits_wrongparams.receipt.json")
        try:
            tg.check_rev_eligibility(store, MANIFEST, rev7, B + 7 * D)
        except tg.GateRefusal as e:
            assert e.tag == "BASE_RECEIPT_PARAMS"
        else:
            raise AssertionError("params-mismatched receipt accepted")
    with tempfile.TemporaryDirectory() as td:
        store = Path(td)
        (store / "REQ-ADJ-01.receipt.json").write_bytes(b"{not json")
        try:
            tg.check_rev_eligibility(store, MANIFEST, rev7, B + 7 * D)
        except tg.GateRefusal as e:
            assert e.tag in ("BASE_RECEIPT_MALFORMED",
                            "BASE_SNAPSHOT_MISSING")
        else:
            raise AssertionError("malformed receipt accepted")
    return "R7/R30 refuse at -1ms, pass at =/+1ms; future/tamper/" \
           "params/malformed all refuse"


def _params(adjust):
    return {"symbol": "NVDA", "interval": "1h",
            "start_date": "2023-12-13T00:00:00",
            "end_date": "2024-06-21T23:59:59",
            "timezone": "America/New_York", "outputsize": "5000",
            "order": "ASC", "adjust": adjust}


def _window(splits_stem):
    return az.analyze_window(
        splits_receipt=FIX / f"{splits_stem}.receipt.json",
        splits_snapshot=FIX / f"{splits_stem}.json",
        none_receipt=FIX / "nvda_none_uniform.receipt.json",
        none_snapshot=FIX / "nvda_none_uniform.json",
        expected_params_splits=_params("splits"),
        expected_params_none=_params("none"),
        factor=Decimal(10), split_date="2024-06-10")


def q11_uniform_factor_pass():
    rep = _window("nvda_splits_uniform")
    CTX["rep_uniform"] = rep
    assert rep["verdict"] == "PASS", rep
    for c in ("C1", "C2", "C3", "C4", "C6"):
        assert rep["checks"][c]["status"] == "PASS", (c, rep)
    assert rep["checks"]["C2"]["convention"] == "SCALED_BY_FACTOR"
    assert rep["checks"]["C3"]["flip_datetime"] == \
        "2024-06-10 09:30:00"
    assert rep["checks"]["C3"]["relation_to_effective_date"] == \
        "ON_EFFECTIVE_DATE"
    return "uniform window PASS; flip on effective date; vol scaled"


def q12_mixed_ohlc_fail():
    rep = _window("nvda_splits_mixed")
    assert rep["verdict"] == "DATA_UNQUALIFIED", rep
    assert rep["checks"]["C1"]["status"] == "FAIL"
    assert rep["checks"]["C1"]["n_deviations"] >= 1
    return "one unadjusted bar in splits series -> C1 FAIL"


def q13_volume_conventions():
    rep_u = _window("nvda_splits_vol_unscaled")
    assert rep_u["verdict"] == "PASS", rep_u
    assert rep_u["checks"]["C2"]["convention"] == "UNSCALED"
    rep_i = _window("nvda_splits_vol_inconsistent")
    assert rep_i["verdict"] == "DATA_UNQUALIFIED", rep_i
    assert rep_i["checks"]["C2"]["status"] == "FAIL"
    assert rep_i["checks"]["C2"]["convention"] == "INCONSISTENT"
    return "unscaled convention reported PASS; inconsistent -> FAIL"


def q14_missing_volume():
    rep = _window("nvda_splits_missing_volume")
    assert rep["verdict"] == "DATA_UNQUALIFIED", rep
    assert rep["checks"]["C2"]["convention"] == "MISSING_VOLUME"
    return "missing volume -> C2 FAIL (MISSING_VOLUME)"


def q15_revision_identical_different():
    same = az.analyze_revision(
        base_receipt=FIX / "nvda_splits_uniform.receipt.json",
        base_snapshot=FIX / "nvda_splits_uniform.json",
        rev_receipt=FIX / "nvda_splits_rev_identical.receipt.json",
        rev_snapshot=FIX / "nvda_splits_uniform.json",
        expected_params=_params("splits"))
    assert same["verdict"] == "PASS" and same["C5"]["identical"]
    diff = az.analyze_revision(
        base_receipt=FIX / "nvda_splits_uniform.receipt.json",
        base_snapshot=FIX / "nvda_splits_uniform.json",
        rev_receipt=FIX / "nvda_splits_rev_different.receipt.json",
        rev_snapshot=FIX / "nvda_splits_rev_different.json",
        expected_params=_params("splits"))
    CTX["rep_revision"] = diff
    assert diff["verdict"] == "HOLD", diff
    assert diff["C5"]["status"] == "DIFFERS"
    hits = [d for d in diff["C5"]["diffs"]
            if d.get("field") == "close"
            and d["datetime"] == "2024-06-10 09:30:00"]
    assert hits and hits[0]["base"] == "126.00" \
        and hits[0]["revision"] == "126.25"
    return "identical revision PASS; differing revision HOLD + diff"


def q16_malformed_evidence():
    rep = _window("nvda_splits_uniform")
    assert rep["verdict"] == "PASS"  # control
    corrupt = az.analyze_window(
        splits_receipt=FIX / "nvda_splits_corrupt.receipt.json",
        splits_snapshot=FIX / "nvda_splits_uniform.json",
        none_receipt=FIX / "nvda_none_uniform.receipt.json",
        none_snapshot=FIX / "nvda_none_uniform.json",
        expected_params_splits=_params("splits"),
        expected_params_none=_params("none"),
        factor=Decimal(10), split_date="2024-06-10")
    assert corrupt["verdict"] == "HOLD"
    assert corrupt["hold_tag"] == "SNAPSHOT_SHA_MISMATCH"
    wrong = az.analyze_window(
        splits_receipt=FIX / "nvda_splits_wrongparams.receipt.json",
        splits_snapshot=FIX / "nvda_splits_uniform.json",
        none_receipt=FIX / "nvda_none_uniform.receipt.json",
        none_snapshot=FIX / "nvda_none_uniform.json",
        expected_params_splits=_params("splits"),
        expected_params_none=_params("none"),
        factor=Decimal(10), split_date="2024-06-10")
    assert wrong["verdict"] == "HOLD"
    assert wrong["hold_tag"] == "RECEIPT_PARAMS_MISMATCH"
    return "corrupt SHA and wrong-params receipts -> HOLD pre-parse"


def q17_decimal_rounding_boundary():
    b = json.loads((FIX / "rounding_boundary.json").read_text())
    p, f = b["pass_pair"], b["fail_pair"]
    assert az.ratio_within(p["none"], p["splits"], Decimal(10))
    assert not az.ratio_within(f["none"], f["splits"], Decimal(10))
    assert Decimal(p["deviation"]) <= Decimal(p["tolerance"])
    assert Decimal(f["deviation"]) > Decimal(f["tolerance"])
    return "deviation at/below tolerance passes; above fails"


def _cli(args, cwd, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(HERE / "probe_runner.py")] + args,
        cwd=cwd, env=env, capture_output=True, text=True, timeout=120)


def q18_cli_refusals():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        marker = td / "marker.txt"
        env = {"TD_FAKE_MARKER": str(marker)}
        tm = str(FIX / "fake_transport_module.py")
        base = ["--repo-root", str(REPO_ROOT),
                "--manifest", str(MANIFEST_PATH),
                "--store", "store", "--transport-module", tm]
        r = _cli(base + ["--manifest-sha256", "0" * 64, "--day", "D1"],
                 td, env)
        assert r.returncode == 3 and \
            "MANIFEST_HASH_MISMATCH" in r.stderr, r.stderr
        assert not marker.exists()
        tampered = json.loads(json.dumps(MANIFEST))
        tampered["requests"].append(dict(
            tampered["requests"][0], request_id="REQ-SPT-99"))
        tp = td / "tampered.json"
        tp.write_text(json.dumps(tampered))
        tsha = hashlib.sha256(tp.read_bytes()).hexdigest()
        r = _cli(["--repo-root", str(REPO_ROOT), "--manifest", str(tp),
                  "--manifest-sha256", tsha, "--day", "D1",
                  "--store", "store", "--transport-module", tm], td, env)
        assert r.returncode == 3 and \
            "UNEXPECTED_REQUEST_ID" in r.stderr, r.stderr
        assert not marker.exists(), \
            "transport constructed before scope check"
        r = _cli(base + ["--manifest-sha256", MANIFEST_SHA,
                         "--day", "D9"], td, env)
        assert r.returncode == 3 and "UNRECOGNIZED_DAY" in r.stderr
        assert not marker.exists()
        r = _cli(["--repo-root", str(REPO_ROOT), "--manifest",
                  str(MANIFEST_PATH), "--manifest-sha256", MANIFEST_SHA,
                  "--day", "D1", "--store", "../escape",
                  "--transport-module", tm], td, env)
        assert r.returncode == 3 and \
            "STORE_PATH_TRAVERSAL" in r.stderr, r.stderr
        assert not marker.exists()
        store = td / "store2"
        store.mkdir()
        (store / "probe_store.json").write_text(json.dumps(
            {"manifest_sha256": "f" * 64}))
        r = _cli(["--repo-root", str(REPO_ROOT), "--manifest",
                  str(MANIFEST_PATH), "--manifest-sha256", MANIFEST_SHA,
                  "--day", "D1", "--store", "store2",
                  "--transport-module", tm], td, env)
        assert r.returncode == 3 and "STORE_CONFLICT" in r.stderr, \
            r.stderr
    return "CLI refuses hash/scope/day/traversal/conflict pre-run"


def q19_cli_end_to_end_days():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        marker = td / "marker.txt"
        tm = str(FIX / "fake_transport_module.py")
        common = ["--repo-root", str(REPO_ROOT), "--manifest",
                  str(MANIFEST_PATH), "--manifest-sha256", MANIFEST_SHA,
                  "--store", "store", "--transport-module", tm]
        env = {"TD_FAKE_MARKER": str(marker),
               "TD_FAKE_NOW_S": "1700000000"}
        r = _cli(common + ["--day", "D1"], td, env)
        assert r.returncode == 0, r.stderr
        store = td / "store"
        for rid in ("REQ-ADJ-01", "REQ-ADJ-02", "REQ-ADJ-03",
                    "REQ-ADJ-01N", "REQ-ADJ-02N"):
            assert (store / f"{rid}.receipt.json").exists(), rid
        assert (store / "api_usage.D1.receipt.json").exists()
        base_ts = json.loads(
            (store / "REQ-ADJ-01.receipt.json").read_text()
        )["receipt_ts_ms"]
        early = str(base_ts / 1000 + 30 * 86400 - 3600)
        r = _cli(common + ["--day", "D30"], td,
                 {"TD_FAKE_MARKER": str(marker),
                  "TD_FAKE_NOW_S": early})
        assert r.returncode == 3 and \
            "REV_NOT_YET_ELIGIBLE" in r.stderr, r.stderr
        ok7 = str(base_ts / 1000 + 7 * 86400 + 3600)
        r = _cli(common + ["--day", "D7"], td,
                 {"TD_FAKE_MARKER": str(marker),
                  "TD_FAKE_NOW_S": ok7})
        assert r.returncode == 0, r.stderr
        assert (store / "REQ-ADJ-01R7.receipt.json").exists()
        ok30 = str(base_ts / 1000 + 30 * 86400 + 3600)
        r = _cli(common + ["--day", "D30"], td,
                 {"TD_FAKE_MARKER": str(marker),
                  "TD_FAKE_NOW_S": ok30})
        assert r.returncode == 0, r.stderr
        assert (store / "REQ-ADJ-01R30.receipt.json").exists()
        CTX["cli_days"] = "D1,D7,D30"
    return "CLI runs D1; D30 early refused; D7/D30 run when eligible"


def q20_no_global_verdict():
    payloads = [json.dumps(CTX["rep_uniform"]),
                json.dumps(CTX["rep_revision"]),
                json.dumps(CTX["summary_d1"])]
    for p in payloads:
        assert "KEEP" not in p and "REPLACE" not in p
    verdicts = {CTX["rep_uniform"]["verdict"],
                CTX["rep_revision"]["verdict"]}
    assert verdicts <= {"PASS", "DATA_UNQUALIFIED", "HOLD"}
    return "outputs carry sampled-window verdicts only"


CASES = [
    ("Q01_scope_isolation", q01_scope_isolation),
    ("Q02_none_splits_mapping", q02_none_splits_mapping),
    ("Q03_attempt_ceiling_arithmetic", q03_attempt_ceiling_arithmetic),
    ("Q04_attempt_cap_live", q04_attempt_cap_live),
    ("Q05_no_pagination", q05_no_pagination),
    ("Q06_usage_failure_before_data", q06_usage_failure_before_data),
    ("Q07_d1_run_and_usage_once_per_day",
     q07_d1_run_and_usage_once_per_day),
    ("Q08_sanitized_receipts", q08_sanitized_receipts),
    ("Q09_base_linkage", q09_base_linkage),
    ("Q10_temporal_boundaries", q10_temporal_boundaries),
    ("Q11_uniform_factor_pass", q11_uniform_factor_pass),
    ("Q12_mixed_ohlc_fail", q12_mixed_ohlc_fail),
    ("Q13_volume_conventions", q13_volume_conventions),
    ("Q14_missing_volume", q14_missing_volume),
    ("Q15_revision_identical_different",
     q15_revision_identical_different),
    ("Q16_malformed_evidence", q16_malformed_evidence),
    ("Q17_decimal_rounding_boundary", q17_decimal_rounding_boundary),
    ("Q18_cli_refusals", q18_cli_refusals),
    ("Q19_cli_end_to_end_days", q19_cli_end_to_end_days),
    ("Q20_no_global_verdict", q20_no_global_verdict),
]


def main():
    results = []
    all_pass = True
    for name, fn in CASES:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            try:
                detail = fn()
            except Exception as e:
                results.append({"case": name, "pass": False,
                                "detail": f"{type(e).__name__}: "
                                          f"{str(e)[:200]}"})
                all_pass = False
                break
        results.append({"case": name, "pass": True,
                        "detail": detail})
    print(json.dumps({"harness": "td65_qualification_r1",
                      "all_pass": all_pass, "cases": results},
                     indent=1, sort_keys=True))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
