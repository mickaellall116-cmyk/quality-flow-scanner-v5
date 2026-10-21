#!/usr/bin/env python3
"""Synthetic qualification harness — task -70 r1.

ONE attempt. Cases run in order; the FIRST failure stops the run.
Warnings are errors during case execution. Output is a single
deterministic JSON object on stdout (no wall-clock values, no temp
paths). A byte-identity repeat is run by the operator only if this
run passes.

-70 (usage-semantics repair, spec comment 6317623205): Q01-Q20 /
A01-A10 / B01-B08 are the -68 suite re-run against the successor
as the regression block, in the original order. U01-U13 are the
new adversarial cases for the corrected minute/daily semantics
and persist-every-outcome receipts (appended after B08):
  U01 live -69 shape (minute 1/8 + daily 1/800) PASSes; the day
      budget is never charged to the minute bucket
  U02 minute saturation: pinned limiter refuses the 9th credit
      inside the rolling minute and the 801st on the day, before
      any further transport; a saturated minute bucket alone
      does NOT refuse the preflight
  U03 daily remaining below the day's hard remainder -> HOLD
  U04 missing daily fields (exact -69 live body) -> HOLD, with
      the refusal receipt persisted
  U05 malformed minute/daily fields -> schema HOLDs
  U06 contradictory daily fields / non-pinned daily plan -> HOLD
  U07 a huge minute plan_limit cannot satisfy the daily gate
  U08 PASS and REFUSE receipts both hash-match their persisted
      exact body bytes
  U09 simulated receipt-write failure -> HOLD before data
  U10 429/retry accounting (attempts, statuses, receipts)
  U11 stored PASS tampering (body/params/date/manifest/store/
      payload) refused before any transport
  U12 no data transport before valid preflight; Day-1 aggregate
      call count never exceeds the 12 hard ceiling
  U13 credit headers never waive the daily gate; header/body
      contradictions refuse

CHANGED -68 EXPECTATIONS (explicit, per task instruction — the
-68 fixtures encoded the defective semantics):
  * CountUsageTransport and fixtures/fake_transport_module.py
    now serve the corrected body {current_usage:3, plan_limit:8,
    daily_usage:3, plan_daily_limit:800}. The old body
    {current_usage:3, plan_limit:800} has NO daily fields and
    would now HOLD at USAGE_DAILY_SCHEMA (proven by U04/U07).
    This affects Q06 (503 path — outcome unchanged), Q07, Q19,
    B06 (PASS paths — outcomes unchanged, bodies corrected).
  * Q07's stored-receipt assertions read the four-field
    canonical payload via the new parse API and additionally
    assert the persisted body file hash-matches the receipt.
  * A05-A09 / B07 receipt fixtures carry the four-field payload
    and a matching persisted body file (the session now verifies
    body evidence before any cached outcome); A07's weaker-
    headroom scenario is re-expressed on the recorded-headroom
    binding with daily_usage=795/800. Expected tags unchanged.
  * B06 builds its receipts through the real session (unchanged
    construction); its fake body is the corrected one above.
All other -68 cases are byte-identical in construction and
expectation.

Q01-Q20 are the -65 qualification set re-run against the successor
package (regression). A01-A10 are the -66 adversarial cases for the
three repaired defects (adjudication comment 6310607516):
  A01 mixed factor/1 pre-split volume        (defect 1)
  A02 swapped request IDs, twin + revision    (defect 2)
  A03 duplicate / out-of-order / out-of-window bars (defect 2)
  A04 snapshot meta symbol/interval mismatch  (defect 2)
  A05 edited usage PASS cache                 (defect 3)
  A06 cross-manifest usage cache              (defect 3)
  A07 weaker cached headroom                  (defect 3)
  A08 stale usage cache timestamp             (defect 3)
  A09 future usage cache timestamp            (defect 3)
  A10 empty pre / post coverage for C2        (defect 1)
Every cache refusal (A05-A09) is proven to occur BEFORE any data
fetch (zero data-transport and zero usage-transport calls).
B01-B08 are the -67 closure adversarial cases (adjudication
comment 6311907793):
  B01 legacy-argument omission at both analyzer entrypoints
  B02 blank / None / identical expectations -> HOLD pre-analysis
  B03 identical meta-wrong revision snapshots -> HOLD (C5 order)
  B04 identical out-of-window revision snapshots -> HOLD
  B05 identical duplicate-bar revision snapshots -> HOLD
  B06 cross-midnight usage cache reuse (age <24h) refused before
      data AND usage transport; same-day reuse still served
  B07 cached usage receipt with wrong endpoint params refused
  B08 malformed OHLC/volume numeric strings -> HOLD, no exception
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
WIN = ("2023-12-13T00:00:00", "2024-06-21T23:59:59")
# -68 clock alignment (the ONLY functional change vs -67): the -67
# harness clock (2023-11-14) predated the committed fixture receipts
# (BASE_TS_MS = 1_760_000_000_000, 2025-10-09 08:53:20 UTC; max
# fixture receipt = base + 7d), so the mandatory RECEIPT_TS_FUTURE
# check refused every fixture (Q11 stop). NOW is the fixture epoch
# + 31 days, advanced within the same UTC date to 23:13:20 UTC so
# B06's +1h step crosses the UTC date boundary it exercises:
#   1_760_000_000_000 + 31 * 86_400_000 + 51_600_000
#   = 1_762_730_000_000 ms = 2025-11-09 23:13:20 UTC.
NOW_S = 1762730000.0
NOW_MS = 1762730000000


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
            {"current_usage": 3, "plan_limit": 8,
             "daily_usage": 3, "plan_daily_limit": 800}).encode()


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
    # defect-3 repair: the persisted receipt is integrity-bound
    stored = json.loads(
        (CTX["store"] / "api_usage.D1.receipt.json").read_text())
    assert stored["manifest_sha256"] == MANIFEST_SHA
    assert stored["required_headroom"] == 10
    assert stored["store_marker_sha256"] == ap.store_marker_sha256(
        rn.store_marker_string(CTX["store"]))
    fields = ap.parse_usage_body(stored["response_payload"].encode())
    assert fields["daily_present"] is True
    assert (fields["current_usage"], fields["plan_limit"],
            fields["daily_usage"], fields["plan_daily_limit"]) == \
        (stored["current_usage"], stored["plan_limit"],
         stored["daily_usage"], stored["plan_daily_limit"])
    assert hashlib.sha256(
        stored["response_payload"].encode()).hexdigest() == \
        stored["response_sha256"]
    # -70: the exact body bytes are persisted beside the receipt
    body_bytes = (CTX["store"] / "api_usage.D1.body.bin").read_bytes()
    assert hashlib.sha256(body_bytes).hexdigest() == stored["sha256"]
    assert len(body_bytes) == stored["bytes"]
    assert stored["execution_date_utc"] == ap.utc_date_string(
        stored["receipt_ts_ms"])
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
    return "D1 OK; bound usage receipt re-verified + reused once/day"


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


def _id_kwargs():
    return {"expected_request_id_splits": "REQ-ADJ-01",
            "expected_request_id_none": "REQ-ADJ-01N",
            "expected_symbol": "NVDA", "expected_interval": "1h",
            "expected_window": WIN, "now_ms": NOW_MS}


def _rev_kwargs():
    return {"expected_base_request_id": "REQ-ADJ-01",
            "expected_rev_request_id": "REQ-ADJ-01R7",
            "expected_symbol": "NVDA", "expected_interval": "1h",
            "expected_window": WIN, "now_ms": NOW_MS}


def _window(splits_stem):
    return az.analyze_window(
        splits_receipt=FIX / f"{splits_stem}.receipt.json",
        splits_snapshot=FIX / f"{splits_stem}.json",
        none_receipt=FIX / "nvda_none_uniform.receipt.json",
        none_snapshot=FIX / "nvda_none_uniform.json",
        expected_params_splits=_params("splits"),
        expected_params_none=_params("none"),
        factor=Decimal(10), split_date="2024-06-10", **_id_kwargs())


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
        expected_params=_params("splits"), **_rev_kwargs())
    assert same["verdict"] == "PASS" and same["C5"]["identical"]
    diff = az.analyze_revision(
        base_receipt=FIX / "nvda_splits_uniform.receipt.json",
        base_snapshot=FIX / "nvda_splits_uniform.json",
        rev_receipt=FIX / "nvda_splits_rev_different.receipt.json",
        rev_snapshot=FIX / "nvda_splits_rev_different.json",
        expected_params=_params("splits"), **_rev_kwargs())
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
        factor=Decimal(10), split_date="2024-06-10", **_id_kwargs())
    assert corrupt["verdict"] == "HOLD"
    assert corrupt["hold_tag"] == "SNAPSHOT_SHA_MISMATCH"
    wrong = az.analyze_window(
        splits_receipt=FIX / "nvda_splits_wrongparams.receipt.json",
        splits_snapshot=FIX / "nvda_splits_uniform.json",
        none_receipt=FIX / "nvda_none_uniform.receipt.json",
        none_snapshot=FIX / "nvda_none_uniform.json",
        expected_params_splits=_params("splits"),
        expected_params_none=_params("none"),
        factor=Decimal(10), split_date="2024-06-10", **_id_kwargs())
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
               "TD_FAKE_NOW_S": "1762730000"}
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


# ---------------- -66 adversarial cases ----------------

def a01_mixed_volume_conventions():
    rep = _window("nvda_splits_vol_mixed_conventions")
    assert rep["verdict"] == "DATA_UNQUALIFIED", rep
    assert rep["checks"]["C1"]["status"] == "PASS", rep
    assert rep["checks"]["C2"]["status"] == "FAIL"
    assert rep["checks"]["C2"]["convention"] == "INCONSISTENT"
    assert "mixed" in rep["checks"]["C2"]["detail"]
    return "pre-split volume mixing factor-scaled + unscaled bars " \
           "-> C2 FAIL/INCONSISTENT (the -65 false PASS is closed); " \
           "prices uniform so C1 PASS isolates the defect"


def a02_swapped_request_ids():
    kw = _id_kwargs()
    twin_s = az.analyze_window(
        splits_receipt=FIX / "nvda_splits_swappedid.receipt.json",
        splits_snapshot=FIX / "nvda_splits_uniform.json",
        none_receipt=FIX / "nvda_none_uniform.receipt.json",
        none_snapshot=FIX / "nvda_none_uniform.json",
        expected_params_splits=_params("splits"),
        expected_params_none=_params("none"),
        factor=Decimal(10), split_date="2024-06-10", **kw)
    assert twin_s["verdict"] == "HOLD" and \
        twin_s["hold_tag"] == "RECEIPT_ID_MISMATCH", twin_s
    twin_n = az.analyze_window(
        splits_receipt=FIX / "nvda_splits_uniform.receipt.json",
        splits_snapshot=FIX / "nvda_splits_uniform.json",
        none_receipt=FIX / "nvda_none_swappedid.receipt.json",
        none_snapshot=FIX / "nvda_none_uniform.json",
        expected_params_splits=_params("splits"),
        expected_params_none=_params("none"),
        factor=Decimal(10), split_date="2024-06-10", **kw)
    assert twin_n["verdict"] == "HOLD" and \
        twin_n["hold_tag"] == "RECEIPT_ID_MISMATCH", twin_n
    rk = _rev_kwargs()
    base_swap = az.analyze_revision(
        base_receipt=FIX / "nvda_splits_base_revid.receipt.json",
        base_snapshot=FIX / "nvda_splits_uniform.json",
        rev_receipt=FIX / "nvda_splits_rev_identical.receipt.json",
        rev_snapshot=FIX / "nvda_splits_uniform.json",
        expected_params=_params("splits"), **rk)
    assert base_swap["verdict"] == "HOLD" and \
        base_swap["C5"]["hold_tag"] == "RECEIPT_ID_MISMATCH", base_swap
    rev_swap = az.analyze_revision(
        base_receipt=FIX / "nvda_splits_uniform.receipt.json",
        base_snapshot=FIX / "nvda_splits_uniform.json",
        rev_receipt=FIX / "nvda_splits_rev_baseid.receipt.json",
        rev_snapshot=FIX / "nvda_splits_rev_different.json",
        expected_params=_params("splits"), **rk)
    assert rev_swap["verdict"] == "HOLD" and \
        rev_swap["C5"]["hold_tag"] == "RECEIPT_ID_MISMATCH", rev_swap
    return "twin splits/none ID swaps and base/revision ID swaps " \
           "all -> HOLD RECEIPT_ID_MISMATCH before analysis"


def a03_bar_set_defects():
    for stem, tag in (
            ("nvda_splits_dup_bars", "BARS_NOT_STRICTLY_ASCENDING"),
            ("nvda_splits_ooo_bars", "BARS_NOT_STRICTLY_ASCENDING"),
            ("nvda_splits_oow_bars", "BAR_OUT_OF_WINDOW")):
        rep = _window(stem)
        assert rep["verdict"] == "HOLD" and \
            rep["hold_tag"] == tag, (stem, rep)
    return "duplicate / out-of-order / out-of-window bars -> HOLD " \
           "with structural tags, before any C1-C6 check"


def a04_meta_mismatch():
    for stem in ("nvda_splits_meta_symbol",
                 "nvda_splits_meta_interval"):
        rep = _window(stem)
        assert rep["verdict"] == "HOLD" and \
            rep["hold_tag"] == "SNAPSHOT_META_MISMATCH", (stem, rep)
    return "meta symbol and meta interval mismatches -> HOLD"


def _marker_dict():
    return {"manifest_sha256": MANIFEST_SHA,
            "runner": "td_probe_runner_candidate_70"}


def _marker_str():
    return json.dumps(_marker_dict(), sort_keys=True)


def _raw_usage_body(cur, lim, dcur, dlim):
    return json.dumps({"current_usage": cur, "plan_limit": lim,
                       "daily_usage": dcur,
                       "plan_daily_limit": dlim}).encode()


def _bound_usage_receipt(*, cur=3, lim=8, dcur=3, dlim=800,
                         headroom=10, manifest_sha=MANIFEST_SHA,
                         rcpt_ts_ms=NOW_MS, execution_date=None):
    # -70: four-field semantics (lim is the MINUTE bucket; the
    # daily pair is explicit). Returns (receipt, exact body bytes)
    # — the session now persists and verifies body evidence, so
    # the fixture writes both files.
    fields = {"current_usage": cur, "plan_limit": lim,
              "daily_usage": dcur, "plan_daily_limit": dlim,
              "daily_present": True}
    payload = ap.canonical_usage_payload(fields)
    body = _raw_usage_body(cur, lim, dcur, dlim)
    receipt = {
        "request_id": "API-USAGE-PREFLIGHT", "attempt": 1,
        "attempts": 1, "attempt_statuses": [200],
        "request_ts_ms": rcpt_ts_ms - 1000,
        "receipt_ts_ms": rcpt_ts_ms,
        "http_status": 200, "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "params": {"endpoint": "/api_usage"},
        "execution_date_utc": execution_date
        if execution_date is not None
        else ap.utc_date_string(rcpt_ts_ms),
        "credits_headers": {},
        "current_usage": cur, "plan_limit": lim,
        "daily_usage": dcur, "plan_daily_limit": dlim,
        "response_payload": payload,
        "response_sha256": hashlib.sha256(
            payload.encode()).hexdigest(),
        "verdict": "PASS", "terminal_reason": None, "day": "D1",
        "manifest_sha256": manifest_sha,
        "store_marker_sha256": ap.store_marker_sha256(_marker_str()),
        "required_headroom": headroom,
    }
    return receipt, body


def _expect_cache_refusal(td, receipt_obj, body_bytes, tag_part):
    store = Path(td) / "store"
    store.mkdir(parents=True)
    (store / "probe_store.json").write_text(
        json.dumps(_marker_dict(), indent=2))
    (store / "api_usage.D1.body.bin").write_bytes(body_bytes)
    (store / "api_usage.D1.receipt.json").write_text(
        json.dumps(receipt_obj, indent=2))
    data = CountDataTransport()
    usage = CountUsageTransport()
    try:
        rn.run_probe_day(
            repo_root=REPO_ROOT, manifest_path=MANIFEST_PATH,
            manifest_sha256=MANIFEST_SHA, day="D1",
            store_dir=store, data_transport=data,
            usage_transport=usage,
            clock=FTM.FakeClock(NOW_S, 7.0), sleeper=lambda s: None)
    except RuntimeError as e:
        assert tag_part in str(e), str(e)
    else:
        raise AssertionError(f"cache refusal {tag_part} did not abort")
    assert len(data.calls) == 0, "data fetched despite cache refusal"
    assert len(usage.calls) == 0, "usage re-called despite refusal"
    return f"refused with {tag_part} before any data/usage fetch"


def a05_edited_usage_pass():
    with tempfile.TemporaryDirectory() as td:
        rcpt, body = _bound_usage_receipt()
        rcpt["current_usage"] = 0  # edited after the fact
        detail = _expect_cache_refusal(td, rcpt, body,
                                       "USAGE_CACHE_BODY_ALTERED")
    return "edited cached PASS (field != persisted payload) -> " + \
        detail


def a06_cross_manifest_cache():
    with tempfile.TemporaryDirectory() as td:
        rcpt, body = _bound_usage_receipt(manifest_sha="a" * 64)
        detail = _expect_cache_refusal(td, rcpt, body,
                                       "USAGE_CACHE_BINDING")
    return "cache bound to another manifest -> " + detail


def a07_weaker_cached_headroom():
    with tempfile.TemporaryDirectory() as td:
        # -70 re-expression: the receipt was written for a daily
        # headroom of 2 (daily 795/800) while the session requires
        # 10 — the recorded-headroom binding refuses first.
        rcpt, body = _bound_usage_receipt(dcur=795, headroom=2)
        detail = _expect_cache_refusal(td, rcpt, body,
                                       "USAGE_CACHE_BINDING")
    return "cache written for headroom 2, session requires 10 -> " + \
        detail


def a08_stale_usage_timestamp():
    with tempfile.TemporaryDirectory() as td:
        rcpt, body = _bound_usage_receipt(
            rcpt_ts_ms=NOW_MS - 25 * 3600 * 1000)
        detail = _expect_cache_refusal(td, rcpt, body,
                                       "USAGE_CACHE_TIMESTAMP")
    return "cached receipt 25h old -> " + detail


def a09_future_usage_timestamp():
    with tempfile.TemporaryDirectory() as td:
        rcpt, body = _bound_usage_receipt(
            rcpt_ts_ms=NOW_MS + 3600 * 1000)
        detail = _expect_cache_refusal(td, rcpt, body,
                                       "USAGE_CACHE_TIMESTAMP")
    return "cached receipt 1h in the future -> " + detail


def a10_coverage_empty():
    kw = _id_kwargs()
    post = az.analyze_window(
        splits_receipt=FIX / "nvda_splits_post_only.receipt.json",
        splits_snapshot=FIX / "nvda_splits_post_only.json",
        none_receipt=FIX / "nvda_none_post_only.receipt.json",
        none_snapshot=FIX / "nvda_none_post_only.json",
        expected_params_splits=_params("splits"),
        expected_params_none=_params("none"),
        factor=Decimal(10), split_date="2024-06-10", **kw)
    assert post["verdict"] == "HOLD" and \
        post["hold_tag"] == "C2_PRE_COVERAGE_EMPTY", post
    pre = az.analyze_window(
        splits_receipt=FIX / "nvda_splits_pre_only.receipt.json",
        splits_snapshot=FIX / "nvda_splits_pre_only.json",
        none_receipt=FIX / "nvda_none_pre_only.receipt.json",
        none_snapshot=FIX / "nvda_none_pre_only.json",
        expected_params_splits=_params("splits"),
        expected_params_none=_params("none"),
        factor=Decimal(10), split_date="2024-06-10", **kw)
    assert pre["verdict"] == "HOLD" and \
        pre["hold_tag"] == "C2_POST_COVERAGE_EMPTY", pre
    return "post-only window -> HOLD C2_PRE_COVERAGE_EMPTY; " \
           "pre-only window -> HOLD C2_POST_COVERAGE_EMPTY"


# ---------------- -67 closure adversarial cases ----------------

def _win_base_kwargs():
    return dict(
        splits_receipt=FIX / "nvda_splits_uniform.receipt.json",
        splits_snapshot=FIX / "nvda_splits_uniform.json",
        none_receipt=FIX / "nvda_none_uniform.receipt.json",
        none_snapshot=FIX / "nvda_none_uniform.json",
        expected_params_splits=_params("splits"),
        expected_params_none=_params("none"),
        factor=Decimal(10), split_date="2024-06-10")


def _rev_base_kwargs():
    return dict(
        base_receipt=FIX / "nvda_splits_uniform.receipt.json",
        base_snapshot=FIX / "nvda_splits_uniform.json",
        rev_receipt=FIX / "nvda_splits_rev_identical.receipt.json",
        rev_snapshot=FIX / "nvda_splits_uniform.json",
        expected_params=_params("splits"))


def b01_legacy_argument_omission():
    omitted = 0
    for omit in ("expected_request_id_splits",
                 "expected_request_id_none", "expected_symbol",
                 "expected_interval", "expected_window", "now_ms"):
        kw = dict(_id_kwargs())
        kw.pop(omit)
        try:
            az.analyze_window(**_win_base_kwargs(), **kw)
        except TypeError:
            omitted += 1
        else:
            raise AssertionError(
                f"analyze_window ran without {omit}")
    for omit in ("expected_base_request_id",
                 "expected_rev_request_id", "expected_symbol",
                 "expected_interval", "expected_window", "now_ms"):
        kw = dict(_rev_kwargs())
        kw.pop(omit)
        try:
            az.analyze_revision(**_rev_base_kwargs(), **kw)
        except TypeError:
            omitted += 1
        else:
            raise AssertionError(
                f"analyze_revision ran without {omit}")
    assert omitted == 12, omitted
    return "omitting any of the 6 mandatory expectations at either " \
           "entrypoint raises TypeError — the legacy -66 call " \
           "shape cannot execute at all"


def b02_blank_or_ambiguous_expectations():
    for over in ({"expected_request_id_splits": ""},
                 {"expected_request_id_splits": "   "},
                 {"expected_request_id_splits": None},
                 {"expected_request_id_none": ""},
                 {"expected_symbol": ""},
                 {"expected_interval": " "},
                 {"expected_window": None},
                 {"expected_window": ("2024-06-21T23:59:59",
                                      "2023-12-13T00:00:00")},
                 {"now_ms": None}, {"now_ms": 0}):
        kw = dict(_id_kwargs())
        kw.update(over)
        rep = az.analyze_window(**_win_base_kwargs(), **kw)
        assert rep["verdict"] == "HOLD" and \
            rep["hold_tag"].startswith("EXPECTATION"), (over, rep)
        assert rep["checks"] == {}
    kw = dict(_rev_kwargs())
    kw["expected_rev_request_id"] = kw["expected_base_request_id"]
    rep = az.analyze_revision(**_rev_base_kwargs(), **kw)
    assert rep["verdict"] == "HOLD" and \
        rep["C5"]["hold_tag"] == "EXPECTATION_AMBIGUOUS", rep
    return "blank/None/reversed/zero expectations and identical " \
           "base==revision expected IDs -> HOLD EXPECTATION_* " \
           "before any receipt read or C1-C6 check"


def _rev_same_snapshot(stem):
    return az.analyze_revision(
        base_receipt=FIX / f"{stem}.base.receipt.json",
        base_snapshot=FIX / f"{stem}.json",
        rev_receipt=FIX / f"{stem}.rev.receipt.json",
        rev_snapshot=FIX / f"{stem}.json",
        expected_params=_params("splits"), **_rev_kwargs())


def b03_identical_meta_wrong_revision():
    rep = _rev_same_snapshot("nvda_splits_revmeta_identical")
    assert rep["verdict"] == "HOLD" and \
        rep["C5"]["hold_tag"] == "SNAPSHOT_META_MISMATCH", rep
    return "byte-identical revision pair over a TSLA-meta snapshot " \
           "-> HOLD SNAPSHOT_META_MISMATCH (structure before bytes)"


def b04_identical_out_of_window_revision():
    rep = _rev_same_snapshot("nvda_splits_revoow_identical")
    assert rep["verdict"] == "HOLD" and \
        rep["C5"]["hold_tag"] == "BAR_OUT_OF_WINDOW", rep
    return "byte-identical revision pair containing a 2024-06-24 " \
           "bar -> HOLD BAR_OUT_OF_WINDOW"


def b05_identical_duplicate_revision():
    rep = _rev_same_snapshot("nvda_splits_revdup_identical")
    assert rep["verdict"] == "HOLD" and \
        rep["C5"]["hold_tag"] == "BARS_NOT_STRICTLY_ASCENDING", rep
    return "byte-identical revision pair with a duplicated bar -> " \
           "HOLD BARS_NOT_STRICTLY_ASCENDING"


def b06_cross_midnight_usage_cache():
    assert ap.utc_date_string(NOW_MS) == "2025-11-09"
    assert ap.utc_date_string(NOW_MS + 3600 * 1000) == "2025-11-10"
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "store"
        usage1 = CountUsageTransport()
        clock1 = FTM.FakeClock(NOW_S, 0.0)
        s1 = ap.DailyUsageSession(
            store, "D1",
            ap.AccountPreflight(usage1, clock=clock1,
                                required_headroom=10),
            manifest_sha256=MANIFEST_SHA,
            store_marker=_marker_str(), required_headroom=10,
            clock=clock1)
        assert s1() == [] and len(usage1.calls) == 1
        stored = json.loads(
            (store / "api_usage.D1.receipt.json").read_text())
        assert stored["execution_date_utc"] == "2025-11-09"
        # same-day reuse: served from cache, no new usage call
        usage_same = CountUsageTransport()
        clock_same = FTM.FakeClock(NOW_S + 60.0, 0.0)
        s_same = ap.DailyUsageSession(
            store, "D1",
            ap.AccountPreflight(usage_same, clock=clock_same,
                                required_headroom=10),
            manifest_sha256=MANIFEST_SHA,
            store_marker=_marker_str(), required_headroom=10,
            clock=clock_same)
        assert s_same() == [] and len(usage_same.calls) == 0
        # cross-midnight: receipt is 1h old (< 24h age limit) but
        # the execution date has rolled -> refuse before transport
        usage2 = CountUsageTransport()
        data2 = CountDataTransport()
        clock2 = FTM.FakeClock(NOW_S + 3600.0, 0.0)
        s2 = ap.DailyUsageSession(
            store, "D1",
            ap.AccountPreflight(usage2, clock=clock2,
                                required_headroom=10),
            manifest_sha256=MANIFEST_SHA,
            store_marker=_marker_str(), required_headroom=10,
            clock=clock2)
        reasons = s2()
        assert reasons and "USAGE_CACHE_DATE" in reasons[0], reasons
        assert len(usage2.calls) == 0 and len(data2.calls) == 0
    return "usage receipt written 23:xx UTC refuses reuse at " \
           "00:xx UTC next date (age 1h < 24h) with " \
           "USAGE_CACHE_DATE before any usage/data transport; " \
           "same-date reuse still served from cache"


def b07_wrong_usage_endpoint_params():
    with tempfile.TemporaryDirectory() as td:
        rcpt, body = _bound_usage_receipt()
        rcpt["params"] = {"endpoint": "/time_series"}
        detail = _expect_cache_refusal(td, rcpt, body,
                                       "USAGE_CACHE_PARAMS")
    return "cached usage receipt bound to /time_series params -> " \
        + detail


def b08_malformed_numeric_strings():
    for stem in ("nvda_splits_badnum_close",
                 "nvda_splits_badnum_volume"):
        rep = az.analyze_window(
            splits_receipt=FIX / f"{stem}.receipt.json",
            splits_snapshot=FIX / f"{stem}.json",
            none_receipt=FIX / "nvda_none_uniform.receipt.json",
            none_snapshot=FIX / "nvda_none_uniform.json",
            expected_params_splits=_params("splits"),
            expected_params_none=_params("none"),
            factor=Decimal(10), split_date="2024-06-10",
            **_id_kwargs())
        assert rep["verdict"] == "HOLD" and \
            rep["hold_tag"] == "SNAPSHOT_MALFORMED", (stem, rep)
    return "non-decimal close and non-decimal volume strings -> " \
           "HOLD SNAPSHOT_MALFORMED; no exception escapes"


# ---------------- -70 usage-semantics adversarial cases --------

GOOD_USAGE = {"current_usage": 1, "plan_limit": 8,
              "daily_usage": 1, "plan_daily_limit": 800}


def _load_limiter_module():
    spec = importlib.util.spec_from_file_location(
        "rate_limiter_td70", REPO_ROOT / rn.RATE_LIMITER_REL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RL = _load_limiter_module()
assert hashlib.sha256(
    (REPO_ROOT / rn.RATE_LIMITER_REL).read_bytes()).hexdigest() == \
    rn.RATE_LIMITER_SHA256


class SeqUsageTransport:
    """Serves a scripted sequence of (status, headers, body);
    the last response repeats. Counts every fetch."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def fetch(self, url):
        self.calls.append(url)
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


def _usage_resp(obj, headers=None, status=200):
    return status, (headers or {}), json.dumps(obj).encode()


def _expect_preflight_refusal(obj, tag, headers=None, headroom=10):
    raw = json.dumps(obj).encode()
    t = SeqUsageTransport([(200, headers or {}, raw)])
    pf = ap.AccountPreflight(t, clock=FTM.FakeClock(NOW_S, 0.0),
                             sleeper=lambda s: None,
                             required_headroom=headroom)
    try:
        pf.check()
    except ap.PreflightRefusal as e:
        assert e.tag == tag, f"tag {e.tag} != {tag}"
        r = e.receipt
        assert r is not None and r["verdict"] == "REFUSE", r
        assert r["sha256"] == hashlib.sha256(raw).hexdigest()
        assert r["bytes"] == len(raw)
        return e
    raise AssertionError(f"no refusal, wanted {tag}")


def _run_d1(td, data, usage, clock_s=NOW_S):
    return rn.run_probe_day(
        repo_root=REPO_ROOT, manifest_path=MANIFEST_PATH,
        manifest_sha256=MANIFEST_SHA, day="D1",
        store_dir=Path(td) / "store", data_transport=data,
        usage_transport=usage,
        clock=FTM.FakeClock(clock_s, 7.0), sleeper=lambda s: None)


def u01_minute_bucket_not_daily_budget():
    with tempfile.TemporaryDirectory() as td:
        data = CountDataTransport()
        usage = SeqUsageTransport([_usage_resp(
            GOOD_USAGE,
            {"api-credits-used": "1", "api-credits-left": "7"})])
        s = _run_d1(td, data, usage)
        assert s["ok"], s
        assert len(data.calls) == 5 and len(usage.calls) == 1
        stored = json.loads(
            (Path(td) / "store" / "api_usage.D1.receipt.json")
            .read_text())
        assert stored["verdict"] == "PASS"
        assert stored["plan_limit"] == 8  # minute bucket, recorded
        assert stored["plan_daily_limit"] == 800
        assert stored["credits_headers"] == {
            "api-credits-used": "1", "api-credits-left": "7"}
    return "live -69 shape minute 1/8 + daily 1/800 PASSes and " \
           "D1 runs (5 data calls); the 10-attempt day budget is " \
           "charged to the daily allowance, never to plan_limit=8"


def u02_minute_saturation_limiter():
    clk = RL.FakeWallClock(1762730000.0)
    lim = RL.RollingCreditLimiter(8, 800, clock=clk)
    assert [lim.try_acquire(1, f"m{i}") for i in range(8)] == \
        [True] * 8
    assert lim.try_acquire(1, "ninth") is False  # rolling min full
    clk.advance(61.0)
    assert lim.try_acquire(1, "after-slide") is True
    clk2 = RL.FakeWallClock(1762730000.0)
    lim2 = RL.RollingCreditLimiter(8, 800, clock=clk2)
    for i in range(100):
        assert lim2.try_acquire(8, f"d{i}") is True
        clk2.advance(61.0)
    assert lim2.daily_spent == 800
    assert lim2.try_acquire(1, "over-day") is False
    sat = dict(GOOD_USAGE, current_usage=8)
    t = SeqUsageTransport([_usage_resp(sat)])
    rcpt = ap.AccountPreflight(
        t, clock=FTM.FakeClock(NOW_S, 0.0),
        sleeper=lambda s: None, required_headroom=10).check()
    assert rcpt["verdict"] == "PASS"
    return "pinned limiter refuses the 9th credit inside the " \
           "rolling minute and any credit past 800/day BEFORE " \
           "further transport; a saturated minute bucket alone " \
           "does not refuse the preflight (spacing is the " \
           "limiter's job, pacing is not a budget refusal)"


def u03_daily_headroom_hold():
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "store"
        data = CountDataTransport()
        usage = SeqUsageTransport([_usage_resp(
            dict(GOOD_USAGE, daily_usage=795))])
        try:
            _run_d1(td, data, usage)
        except RuntimeError as e:
            assert "USAGE_DAILY_HEADROOM" in str(e), str(e)
        else:
            raise AssertionError("daily headroom HOLD did not abort")
        assert len(data.calls) == 0 and len(usage.calls) == 1
        stored = json.loads(
            (store / "api_usage.D1.receipt.json").read_text())
        assert stored["verdict"] == "REFUSE"
        assert "USAGE_DAILY_HEADROOM" in stored["terminal_reason"]
    return "daily 795 + required 10 > 800 -> HOLD before data, " \
           "and the REFUSE outcome receipt is persisted (the -69 " \
           "refusal left no body; this one leaves both files)"


def u04_missing_daily_fields_hold():
    live69 = {"current_usage": 1, "plan_limit": 8}  # exact -69 body
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "store"
        data = CountDataTransport()
        usage = SeqUsageTransport([_usage_resp(live69)])
        try:
            _run_d1(td, data, usage)
        except RuntimeError as e:
            assert "USAGE_DAILY_SCHEMA" in str(e), str(e)
        else:
            raise AssertionError("missing-daily HOLD did not abort")
        assert len(data.calls) == 0 and len(usage.calls) == 1
        stored = json.loads(
            (store / "api_usage.D1.receipt.json").read_text())
        assert stored["verdict"] == "REFUSE"
        body = (store / "api_usage.D1.body.bin").read_bytes()
        assert body == json.dumps(live69).encode()
        assert stored["sha256"] == hashlib.sha256(body).hexdigest()
    return "the exact -69 live body (minute pair only) HOLDs at " \
           "USAGE_DAILY_SCHEMA — daily schema unestablishable, " \
           "no headroom invented — and the refusal body is " \
           "persisted for audit this time"


def u05_malformed_fields_hold():
    cases = [
        (dict(GOOD_USAGE, daily_usage="1"), "USAGE_DAILY_SCHEMA"),
        (dict(GOOD_USAGE, daily_usage=1.5), "USAGE_DAILY_SCHEMA"),
        (dict(GOOD_USAGE, daily_usage=True), "USAGE_DAILY_SCHEMA"),
        (dict(GOOD_USAGE, plan_daily_limit=-800),
         "USAGE_DAILY_SCHEMA"),
        ({"current_usage": 1, "daily_usage": 1,
          "plan_daily_limit": 800}, "USAGE_SCHEMA"),
        (dict(GOOD_USAGE, current_usage=-1), "USAGE_SCHEMA"),
        (dict(GOOD_USAGE, plan_limit="8"), "USAGE_SCHEMA"),
    ]
    for obj, tag in cases:
        _expect_preflight_refusal(obj, tag)
    return "string/float/bool/negative daily fields and " \
           "missing/negative/string minute fields -> " \
           "USAGE_DAILY_SCHEMA / USAGE_SCHEMA refusals, each " \
           "carrying its REFUSE outcome receipt"


def u06_contradictory_daily_hold():
    cases = [
        ({"current_usage": 1, "plan_limit": 8, "daily_usage": 1},
         "USAGE_DAILY_SCHEMA"),
        ({"current_usage": 1, "plan_limit": 8,
          "plan_daily_limit": 800}, "USAGE_DAILY_SCHEMA"),
        (dict(GOOD_USAGE, daily_usage=900), "USAGE_DAILY_SCHEMA"),
        (dict(GOOD_USAGE, plan_daily_limit=400), "USAGE_DAILY_PLAN"),
        (dict(GOOD_USAGE, plan_daily_limit=10000),
         "USAGE_DAILY_PLAN"),
    ]
    for obj, tag in cases:
        _expect_preflight_refusal(obj, tag)
    return "half-present daily pairs, daily_usage > limit, and " \
           "any plan_daily_limit != pinned 800 (400 or 10000) " \
           "-> HOLD; no daily allowance but the pinned Basic " \
           "800/day is ever honored"


def u07_minute_cannot_satisfy_daily():
    _expect_preflight_refusal(
        {"current_usage": 0, "plan_limit": 100000},
        "USAGE_DAILY_SCHEMA")
    return "plan_limit=100000 with no daily pair still HOLDs — " \
           "minute fields never satisfy the daily gate (under " \
           "the -68 reading this body passed any headroom)"


def _direct_session(store, usage, clock=None):
    clock = clock or FTM.FakeClock(NOW_S, 0.0)
    return ap.DailyUsageSession(
        Path(store), "D1",
        ap.AccountPreflight(usage, clock=clock,
                            sleeper=lambda s: None,
                            required_headroom=10),
        manifest_sha256=MANIFEST_SHA, store_marker=_marker_str(),
        required_headroom=10, clock=clock)


def u08_receipt_body_hash_match():
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "refuse_store"
        usage = SeqUsageTransport([_usage_resp(
            {"current_usage": 1, "plan_limit": 8})])
        reasons = _direct_session(store, usage)()
        assert reasons and "USAGE_DAILY_SCHEMA" in reasons[0]
        stored = json.loads(
            (store / "api_usage.D1.receipt.json").read_text())
        body = (store / "api_usage.D1.body.bin").read_bytes()
        assert stored["verdict"] == "REFUSE"
        assert hashlib.sha256(body).hexdigest() == stored["sha256"]
        assert len(body) == stored["bytes"]
        usage2 = SeqUsageTransport([_usage_resp(GOOD_USAGE)])
        reasons2 = _direct_session(store, usage2)()
        assert reasons2 == reasons and len(usage2.calls) == 0
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "pass_store"
        usage = SeqUsageTransport([_usage_resp(GOOD_USAGE)])
        assert _direct_session(store, usage)() == []
        stored = json.loads(
            (store / "api_usage.D1.receipt.json").read_text())
        body = (store / "api_usage.D1.body.bin").read_bytes()
        assert stored["verdict"] == "PASS"
        assert hashlib.sha256(body).hexdigest() == stored["sha256"]
        assert len(body) == stored["bytes"]
    return "REFUSE and PASS receipts both persist exact body " \
           "bytes hash-matching the receipt (count + SHA-256); " \
           "a recorded refusal is sticky — a later session " \
           "returns it with zero re-calls"


def u09_receipt_write_failure_hold():
    with tempfile.TemporaryDirectory() as td:
        store = Path(td) / "store"
        rn.check_store(store, MANIFEST_SHA)  # valid marker first
        (store / "api_usage.D1.body.bin").mkdir()  # write must fail
        data = CountDataTransport()
        usage = SeqUsageTransport([_usage_resp(GOOD_USAGE)])
        try:
            rn.run_probe_day(
                repo_root=REPO_ROOT, manifest_path=MANIFEST_PATH,
                manifest_sha256=MANIFEST_SHA, day="D1",
                store_dir=store, data_transport=data,
                usage_transport=usage,
                clock=FTM.FakeClock(NOW_S, 7.0),
                sleeper=lambda s: None)
        except RuntimeError as e:
            assert "USAGE_RECEIPT_PERSIST_FAILED" in str(e), str(e)
        else:
            raise AssertionError("persist failure did not HOLD")
        assert len(data.calls) == 0
    return "body-write failure (path is a directory) -> " \
           "USAGE_RECEIPT_PERSIST_FAILED before any data fetch; " \
           "a PASS that cannot be evidenced is not a PASS"


def u10_retry_429_accounting():
    good = _usage_resp(GOOD_USAGE)
    t = SeqUsageTransport([(429, {}, b'{"status":"error"}'), good])
    pf = ap.AccountPreflight(t, clock=FTM.FakeClock(NOW_S, 0.0),
                             sleeper=lambda s: None,
                             required_headroom=10)
    rcpt = pf.check()
    assert rcpt["verdict"] == "PASS" and rcpt["attempts"] == 2
    assert rcpt["attempt_statuses"] == [429, 200]
    assert len(t.calls) == 2 and pf.attempts_made == 2
    t2 = SeqUsageTransport([(429, {}, b'{"status":"error"}')])
    pf2 = ap.AccountPreflight(t2, clock=FTM.FakeClock(NOW_S, 0.0),
                              sleeper=lambda s: None,
                              required_headroom=10)
    try:
        pf2.check()
    except ap.PreflightRefusal as e:
        assert e.tag == "USAGE_RETRIES_EXHAUSTED"
        assert e.receipt["attempts"] == 2
        assert e.receipt["attempt_statuses"] == [429, 429]
        assert e.receipt["verdict"] == "REFUSE"
    else:
        raise AssertionError("429x2 did not exhaust")
    assert len(t2.calls) == 2
    return "429 then 200 -> PASS at attempt 2, statuses " \
           "[429, 200] accounted in the receipt; 429 x2 -> " \
           "USAGE_RETRIES_EXHAUSTED with a REFUSE receipt; " \
           "never a third attempt"


def _pass_store(td):
    store = Path(td) / "store"
    usage = SeqUsageTransport([_usage_resp(GOOD_USAGE)])
    assert _direct_session(store, usage)() == []
    assert len(usage.calls) == 1
    return store


def _reuse_reasons(store, tag_part, marker=None,
                   manifest_sha=MANIFEST_SHA):
    usage = SeqUsageTransport([_usage_resp(GOOD_USAGE)])
    sess = ap.DailyUsageSession(
        Path(store), "D1",
        ap.AccountPreflight(usage, clock=FTM.FakeClock(NOW_S, 0.0),
                            sleeper=lambda s: None,
                            required_headroom=10),
        manifest_sha256=manifest_sha,
        store_marker=_marker_str() if marker is None else marker,
        required_headroom=10, clock=FTM.FakeClock(NOW_S, 0.0))
    reasons = sess()
    assert reasons and tag_part in reasons[0], reasons
    assert len(usage.calls) == 0, "tampered cache triggered a call"
    return reasons[0]


def u11_stored_pass_tampering():
    import shutil
    with tempfile.TemporaryDirectory() as td:
        base = _pass_store(td)
        variants = []
        d = Path(td) / "va"
        shutil.copytree(base, d)
        b = bytearray((d / "api_usage.D1.body.bin").read_bytes())
        b[0] ^= 1
        (d / "api_usage.D1.body.bin").write_bytes(bytes(b))
        variants.append((d, "USAGE_RECEIPT_BODY_MISMATCH"))
        d = Path(td) / "vb"
        shutil.copytree(base, d)
        r = json.loads((d / "api_usage.D1.receipt.json").read_text())
        r["params"] = {"endpoint": "/time_series"}
        (d / "api_usage.D1.receipt.json").write_text(json.dumps(r))
        variants.append((d, "USAGE_CACHE_PARAMS"))
        d = Path(td) / "vc"
        shutil.copytree(base, d)
        r = json.loads((d / "api_usage.D1.receipt.json").read_text())
        r["execution_date_utc"] = "2025-11-08"
        (d / "api_usage.D1.receipt.json").write_text(json.dumps(r))
        variants.append((d, "USAGE_CACHE_DATE"))
        d = Path(td) / "vd"
        shutil.copytree(base, d)
        r = json.loads((d / "api_usage.D1.receipt.json").read_text())
        r["manifest_sha256"] = "0" * 64
        (d / "api_usage.D1.receipt.json").write_text(json.dumps(r))
        variants.append((d, "USAGE_CACHE_BINDING"))
        d = Path(td) / "vf"
        shutil.copytree(base, d)
        r = json.loads((d / "api_usage.D1.receipt.json").read_text())
        r["response_payload"] = r["response_payload"].replace(
            '"daily_usage":1', '"daily_usage":0')
        (d / "api_usage.D1.receipt.json").write_text(json.dumps(r))
        variants.append((d, "USAGE_CACHE_BODY_ALTERED"))
        tags = [_reuse_reasons(d, tag) for d, tag in variants]
        _reuse_reasons(base, "USAGE_CACHE_BINDING",
                       marker="some-other-store")
    return "flipped body bytes, altered params / execution " \
           "date / manifest pin, edited payload, and a session " \
           "bound to another store marker all refuse before " \
           "any transport (" + "; ".join(
               t.split(":")[0] for t in tags) + ")"


def u12_aggregate_ceiling_day1():
    with tempfile.TemporaryDirectory() as td:
        data = CountDataTransport()
        usage = SeqUsageTransport([_usage_resp(
            dict(GOOD_USAGE, daily_usage=795))])
        try:
            _run_d1(td, data, usage)
        except RuntimeError:
            pass
        else:
            raise AssertionError("expected preflight abort")
        assert len(usage.calls) + len(data.calls) == 1
    with tempfile.TemporaryDirectory() as td:
        data = CountDataTransport(
            fail_symbols=("NVDA", "TSLA", "AAPL"))
        usage = SeqUsageTransport([_usage_resp(GOOD_USAGE)])
        s = _run_d1(td, data, usage)
        total = len(usage.calls) + len(data.calls)
        assert len(data.calls) == 10 and total == 11, total
        assert total <= 12 and not s["ok"]
    return "refusal day totals exactly 1 call (0 data); all-fail " \
           "Day 1 totals 1 usage + 10 data = 11 <= the 12 hard " \
           "ceiling; clean days total 6 (U01/Q07)"


def u13_headers_never_waive():
    _expect_preflight_refusal(
        dict(GOOD_USAGE, daily_usage=795), "USAGE_DAILY_HEADROOM",
        headers={"api-credits-used": "795",
                 "api-credits-left": "100000"})
    _expect_preflight_refusal(
        GOOD_USAGE, "USAGE_HEADER_MISMATCH",
        headers={"api-credits-used": "5", "api-credits-left": "3"})
    _expect_preflight_refusal(
        GOOD_USAGE, "USAGE_HEADER_MISMATCH",
        headers={"api-credits-used": "1",
                 "api-credits-left": "999"})
    return "api-credits-left=100000 cannot waive a failed daily " \
           "gate (gate refuses first); used != current_usage " \
           "and used+left != plan_limit both refuse " \
           "USAGE_HEADER_MISMATCH — headers reconcile or " \
           "refuse, they never authorize"


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
    ("A01_mixed_volume_conventions", a01_mixed_volume_conventions),
    ("A02_swapped_request_ids", a02_swapped_request_ids),
    ("A03_bar_set_defects", a03_bar_set_defects),
    ("A04_meta_mismatch", a04_meta_mismatch),
    ("A05_edited_usage_pass", a05_edited_usage_pass),
    ("A06_cross_manifest_cache", a06_cross_manifest_cache),
    ("A07_weaker_cached_headroom", a07_weaker_cached_headroom),
    ("A08_stale_usage_timestamp", a08_stale_usage_timestamp),
    ("A09_future_usage_timestamp", a09_future_usage_timestamp),
    ("A10_coverage_empty", a10_coverage_empty),
    ("B01_legacy_argument_omission", b01_legacy_argument_omission),
    ("B02_blank_or_ambiguous_expectations",
     b02_blank_or_ambiguous_expectations),
    ("B03_identical_meta_wrong_revision",
     b03_identical_meta_wrong_revision),
    ("B04_identical_out_of_window_revision",
     b04_identical_out_of_window_revision),
    ("B05_identical_duplicate_revision",
     b05_identical_duplicate_revision),
    ("B06_cross_midnight_usage_cache", b06_cross_midnight_usage_cache),
    ("B07_wrong_usage_endpoint_params",
     b07_wrong_usage_endpoint_params),
    ("B08_malformed_numeric_strings", b08_malformed_numeric_strings),
    ("U01_minute_bucket_not_daily_budget",
     u01_minute_bucket_not_daily_budget),
    ("U02_minute_saturation_limiter", u02_minute_saturation_limiter),
    ("U03_daily_headroom_hold", u03_daily_headroom_hold),
    ("U04_missing_daily_fields_hold", u04_missing_daily_fields_hold),
    ("U05_malformed_fields_hold", u05_malformed_fields_hold),
    ("U06_contradictory_daily_hold", u06_contradictory_daily_hold),
    ("U07_minute_cannot_satisfy_daily",
     u07_minute_cannot_satisfy_daily),
    ("U08_receipt_body_hash_match", u08_receipt_body_hash_match),
    ("U09_receipt_write_failure_hold",
     u09_receipt_write_failure_hold),
    ("U10_retry_429_accounting", u10_retry_429_accounting),
    ("U11_stored_pass_tampering", u11_stored_pass_tampering),
    ("U12_aggregate_ceiling_day1", u12_aggregate_ceiling_day1),
    ("U13_headers_never_waive", u13_headers_never_waive),
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
    print(json.dumps({"harness": "td70_qualification_r1",
                      "all_pass": all_pass, "cases": results},
                     indent=1, sort_keys=True))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
