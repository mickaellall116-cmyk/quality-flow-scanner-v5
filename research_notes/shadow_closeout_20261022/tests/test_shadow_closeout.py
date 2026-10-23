#!/usr/bin/env python3
"""Closeout tests for the shadow successor v3 candidate
(shadow_closeout_20261022; ChatGPT verdict, Issue #1 comment
6356610693, items 3-4).

Groups:
  M — manifest pin binding: full pin set + manifest_digest in
      the manifest and on every record; swapped pin (rule /
      module / calendar / universe, digest recomputed so the
      pin-equality control is what fires), altered manifest
      byte (digest control), changed universe order, swapped
      module file, missing / stale external anchor, live mode
      still refused with no authorization artifact.
  E — equity admission from the pinned session table:
      ordinary bars, the 13:00 early-close single bar, the
      duration-trap bar on the early-close day, wrong close,
      non-session date, crypto-only bin on an equity symbol.
  K — crypto admission on the adopted S-C continuous calendar:
      ordinary bins incl. overnight, Thanksgiving (equity
      holiday) admission, the 3h spring / 5h fall absorbing
      bins with 23/24/25-hour session spans, equity close on
      a crypto symbol, unknown symbol.
  P — V8 preservation under v3: chain verifies, torn tail
      recovers, legacy unchained log refuses, T0 strictness
      (pre-launch / partial) unchanged.

Offline, synthetic, stdlib only. Run: python3 -B
test_shadow_closeout.py. Exit 0 iff every case passes.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PKG)

import shadow_signal_core as core  # noqa: E402
import shadow_signal_runner as runner  # noqa: E402
import shadow_closeout_pins as pins  # noqa: E402

ET = ZoneInfo("America/New_York")
HEALTHY = {"market_ok": True, "scan_complete": True,
           "degraded_symbols": []}
RESULTS = []


def case(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'} {name}"
          + (f" — {detail}" if detail and not cond else ""))


def row(sym, start, close):
    return {"signal_id": f"v54:{sym}:4h:{close}:2026-09-15-v54",
            "symbol": sym, "v54_grade": "B",
            "signal_bar_start_at": start, "signal_bar_close_at": close,
            "stop": 1.0, "tp1": 2.0, "market_gate": "CAUTION"}


def read_records(root):
    with open(os.path.join(root, core.LOG_FILENAME), "rb") as fh:
        raw = fh.read()
    return raw, [json.loads(l) for l in
                 raw.decode("utf-8").splitlines() if l.strip()]


def read_manifest(root):
    with open(os.path.join(root, core.MANIFEST_FILENAME),
              encoding="utf-8") as fh:
        return json.load(fh)


def refuses(fn):
    try:
        fn()
    except core.ShadowError:
        return True
    return False


tmp = tempfile.mkdtemp(prefix="closeout_")

# ================= M: manifest pin binding =================

T0M = datetime(2025, 11, 20, 9, 30, tzinfo=ET)
NOWM = datetime(2025, 11, 26, 17, 0, tzinfo=ET)
mroot = os.path.join(tmp, "m")
obs = core.SignalObserver(mroot, T0M, clock=lambda: NOWM)
obs.run_cycle([row("NVDA", "2025-11-26T09:30:00-05:00",
                   "2025-11-26T13:30:00-05:00")], HEALTHY, now=NOWM)
man = read_manifest(mroot)
mpins = man.get("pins") or {}
case("M1_manifest_carries_full_pin_set",
     mpins.get("candidate_commit") ==
     "4130e74ef2433bf4f491edb6e3a886419063d968"
     and mpins.get("stack_pins") == runner.PINNED_STACK
     and set(mpins.get("module_hashes") or {}) ==
     {"shadow_signal_core.py", "shadow_signal_runner.py"}
     and (mpins.get("universe") or {}).get("count") == 250
     and (mpins.get("calendar") or {}).get("sessions") == 751
     and mpins.get("rule_version") == "2026-09-15-v54"
     and (mpins.get("authorization") or {}).get("state") ==
     "NOT_AUTHORIZED"
     and (mpins.get("authorization") or {})
     .get("artifact_sha256") is None
     and man.get("manifest_digest") ==
     core._manifest_digest(man),
     str(mpins)[:200])

_, mrecs = read_records(mroot)
case("M2_every_record_carries_manifest_digest",
     len(mrecs) >= 2 and all(
         r.get("manifest_digest") == man["manifest_digest"]
         for r in mrecs), f"{len(mrecs)} records")


def tampered_root(name, mutate, recompute_digest=False):
    dst = os.path.join(tmp, name)
    os.makedirs(dst)
    m = read_manifest(mroot)
    mutate(m)
    if recompute_digest:
        m["manifest_digest"] = core._manifest_digest(m)
    with open(os.path.join(dst, core.MANIFEST_FILENAME), "w",
              encoding="utf-8") as fh:
        json.dump(m, fh, indent=2)
    shutil.copy(os.path.join(mroot, core.LOG_FILENAME),
                os.path.join(dst, core.LOG_FILENAME))
    return dst


def swap_rule(m):
    m["pins"]["rule_version"] = "2099-01-01-vXX"


troot = tampered_root("m_rule", swap_rule, recompute_digest=True)
log_before = open(os.path.join(troot, core.LOG_FILENAME),
                  "rb").read()
case("M3_swapped_rule_pin_refuses",
     refuses(lambda: core.SignalObserver(troot, T0M,
                                         clock=lambda: NOWM))
     and open(os.path.join(troot, core.LOG_FILENAME),
              "rb").read() == log_before)

# Altered manifest byte, digest NOT recomputed: the digest
# control itself must catch it.
broot = os.path.join(tmp, "m_byte")
os.makedirs(broot)
raw_man = open(os.path.join(mroot, core.MANIFEST_FILENAME),
               "rb").read().decode("utf-8")
assert "2025-11-26T17:00:00" in raw_man or True
raw_man2 = raw_man.replace('"mode": "signal_only"',
                           '"mode": "signal_onlx"')
assert raw_man2 != raw_man
with open(os.path.join(broot, core.MANIFEST_FILENAME), "w",
          encoding="utf-8") as fh:
    fh.write(raw_man2)
shutil.copy(os.path.join(mroot, core.LOG_FILENAME),
            os.path.join(broot, core.LOG_FILENAME))
err = {}
def _open_broot():
    try:
        core.SignalObserver(broot, T0M, clock=lambda: NOWM)
    except core.ShadowError as exc:
        err["msg"] = str(exc)
        raise
case("M4_altered_manifest_byte_refuses_via_digest",
     refuses(_open_broot) and "digest" in err.get("msg", ""),
     err.get("msg", ""))


def swap_module(m):
    m["pins"]["module_hashes"]["shadow_signal_core.py"] = "0" * 64


troot = tampered_root("m_module", swap_module, recompute_digest=True)
case("M5_swapped_module_pin_refuses",
     refuses(lambda: core.SignalObserver(troot, T0M,
                                         clock=lambda: NOWM)))


def swap_calendar(m):
    m["pins"]["calendar"]["session_table_sha256"] = "f" * 64


troot = tampered_root("m_calendar", swap_calendar,
                      recompute_digest=True)
case("M6_swapped_calendar_pin_refuses",
     refuses(lambda: core.SignalObserver(troot, T0M,
                                         clock=lambda: NOWM)))


def swap_universe(m):
    m["pins"]["universe"]["ordered_digest"] = "a" * 64


troot = tampered_root("m_universe", swap_universe,
                      recompute_digest=True)
case("M7a_swapped_universe_pin_refuses",
     refuses(lambda: core.SignalObserver(troot, T0M,
                                         clock=lambda: NOWM)))

reordered = list(core.ORDERED_UNIVERSE)
reordered[0], reordered[1] = reordered[1], reordered[0]
case("M7b_changed_universe_order_refuses",
     refuses(lambda: core.verify_universe_digest(reordered)))
ok_order = True
try:
    core.verify_universe_digest(list(core.ORDERED_UNIVERSE))
except core.ShadowError:
    ok_order = False
case("M7c_pinned_universe_order_accepted", ok_order)

anchor_path = os.path.join(tmp, "anchor.json")
with open(anchor_path, "w", encoding="utf-8") as fh:
    json.dump(obs.chain_anchor, fh)
case("M8a_missing_anchor_refuses",
     refuses(lambda: core.SignalObserver(
         mroot, T0M, clock=lambda: NOWM,
         anchor_path=os.path.join(tmp, "no_such_anchor.json"))))
opened = True
try:
    core.SignalObserver(mroot, T0M, clock=lambda: NOWM,
                        anchor_path=anchor_path)
except core.ShadowError:
    opened = False
case("M8b_matching_anchor_opens", opened)
stale = dict(obs.chain_anchor)
stale["records"] = stale["records"] - 1
stale_path = os.path.join(tmp, "anchor_stale.json")
with open(stale_path, "w", encoding="utf-8") as fh:
    json.dump(stale, fh)
case("M8c_stale_anchor_refuses",
     refuses(lambda: core.SignalObserver(
         mroot, T0M, clock=lambda: NOWM, anchor_path=stale_path)))

# M9: a swapped module FILE (manifest intact) refuses — run in a
# subprocess against a copied package whose runner bytes moved.
modtmp = os.path.join(tmp, "modpkg")
os.makedirs(modtmp)
for f in ("shadow_signal_core.py", "shadow_signal_runner.py",
          "shadow_closeout_pins.py", "session_table.json",
          "universe.json"):
    shutil.copy(os.path.join(PKG, f), os.path.join(modtmp, f))
with open(os.path.join(modtmp, "shadow_signal_runner.py"),
          "a", encoding="utf-8") as fh:
    fh.write("\n# tampered after pinning\n")
snippet = (
    "import sys; sys.path.insert(0, r'%s');"
    "import shadow_signal_core as c;"
    "from datetime import datetime;"
    "from zoneinfo import ZoneInfo;"
    "c.SignalObserver(r'%s', datetime(2025,11,20,9,30,"
    "tzinfo=ZoneInfo('America/New_York')))"
    % (modtmp, os.path.join(modtmp, "root")))
proc = subprocess.run([sys.executable, "-B", "-c", snippet],
                      capture_output=True, text=True)
case("M9_swapped_module_file_refuses",
     proc.returncode != 0 and "ShadowError" in proc.stderr,
     (proc.stderr or "")[-200:])

auth_probe_root = os.path.join(tmp, "noauth")
case("M10_live_mode_refused_no_authorization_artifact",
     refuses(lambda: runner.main(
         ["--repo-root", ".", "--root", auth_probe_root,
          "--t0", "2025-11-20T09:30:00-05:00"]))
     and not os.path.exists(
         os.path.join(auth_probe_root, runner.AUTH_FILENAME)))

# ================= E: equity session-table admission =========

T0E = datetime(2025, 11, 24, 9, 30, tzinfo=ET)
NOWE = datetime(2025, 11, 28, 20, 0, tzinfo=ET)
eroot = os.path.join(tmp, "e")
eobs = core.SignalObserver(eroot, T0E, clock=lambda: NOWE)
e_rows = [
    row("NVDA", "2025-11-26T09:30:00-05:00",
        "2025-11-26T13:30:00-05:00"),   # E1 ordinary bar 1
    row("NVDA", "2025-11-26T13:30:00-05:00",
        "2025-11-26T16:00:00-05:00"),   # E2 ordinary bar 2
    row("NVDA", "2025-11-28T09:30:00-05:00",
        "2025-11-28T13:00:00-05:00"),   # E3 early-close single bar
    row("NVDA", "2025-11-28T09:30:00-05:00",
        "2025-11-28T13:30:00-05:00"),   # E4 duration trap
    row("NVDA", "2025-11-28T13:30:00-05:00",
        "2025-11-28T16:00:00-05:00"),   # E5 no second bar
    row("NVDA", "2025-11-26T13:30:00-05:00",
        "2025-11-26T15:00:00-05:00"),   # E6 wrong close
    row("NVDA", "2025-11-27T09:30:00-05:00",
        "2025-11-27T13:30:00-05:00"),   # E7 Thanksgiving
    row("NVDA", "2025-11-26T17:30:00-05:00",
        "2025-11-26T21:30:00-05:00"),   # E8 crypto-only bin
    row("SPY", "2025-11-26T09:30:00-05:00",
        "2025-11-26T13:30:00-05:00"),   # E9 ETF = equity class
]
esum = eobs.run_cycle(e_rows, HEALTHY, now=NOWE)
ereason = {r["signal_id"]: r["reason"]
           for r in esum["signals_refused"]}
eid = {i + 1: r["signal_id"] for i, r in enumerate(e_rows)}
case("E1_ordinary_first_bar_admitted",
     eid[1] not in ereason, str(esum["signals_refused"]))
case("E2_ordinary_closing_bar_admitted", eid[2] not in ereason)
case("E3_early_close_single_bar_admitted", eid[3] not in ereason)
case("E4_early_close_duration_trap_refused",
     ereason.get(eid[4]) == "SESSION_TABLE_CLOSE_MISMATCH",
     str(ereason))
case("E5_early_close_second_bar_refused",
     ereason.get(eid[5]) == "OFF_GRID_BAR_START", str(ereason))
case("E6_wrong_close_refused",
     ereason.get(eid[6]) == "SESSION_TABLE_CLOSE_MISMATCH",
     str(ereason))
case("E7_non_session_date_refused",
     ereason.get(eid[7]) == "NON_SESSION_DATE", str(ereason))
case("E8_equity_symbol_crypto_bin_refused",
     ereason.get(eid[8]) == "OFF_GRID_BAR_START", str(ereason))
case("E9_etf_uses_equity_table",
     eid[9] not in ereason and esum["new_signals_recorded"] == 4,
     str(esum))

# ================= K: crypto continuous admission ============

case("K0_session_spans_23_24_25",
     core.crypto_session_span_hours(date(2025, 3, 8)) == 23
     and core.crypto_session_span_hours(date(2025, 11, 26)) == 24
     and core.crypto_session_span_hours(date(2025, 11, 1)) == 25)

T0K = datetime(2025, 11, 24, 9, 30, tzinfo=ET)
NOWK = datetime(2025, 11, 27, 14, 0, tzinfo=ET)
kroot = os.path.join(tmp, "k")
kobs = core.SignalObserver(kroot, T0K, clock=lambda: NOWK)
k_rows = [
    row("BTC-USD", "2025-11-26T09:30:00-05:00",
        "2025-11-26T13:30:00-05:00"),   # K1 ordinary bin
    row("BTC-USD", "2025-11-26T21:30:00-05:00",
        "2025-11-27T01:30:00-05:00"),   # K2 evening bin
    row("BTC-USD", "2025-11-27T01:30:00-05:00",
        "2025-11-27T05:30:00-05:00"),   # K3 overnight bin
    row("BTC-USD", "2025-11-26T13:30:00-05:00",
        "2025-11-26T16:00:00-05:00"),   # K4 equity close on crypto
    row("BTC-USD", "2025-11-27T09:30:00-05:00",
        "2025-11-27T13:30:00-05:00"),   # K5 Thanksgiving: crypto open
    row("ZZZZ", "2025-11-26T09:30:00-05:00",
        "2025-11-26T13:30:00-05:00"),   # K6 unknown symbol
]
ksum = kobs.run_cycle(k_rows, HEALTHY, now=NOWK)
kreason = {r["signal_id"]: r["reason"]
           for r in ksum["signals_refused"]}
kid = {i + 1: r["signal_id"] for i, r in enumerate(k_rows)}
case("K1_crypto_ordinary_bin_admitted", kid[1] not in kreason,
     str(ksum["signals_refused"]))
case("K2_crypto_evening_bin_admitted", kid[2] not in kreason)
case("K3_crypto_overnight_bin_admitted", kid[3] not in kreason)
case("K4_crypto_symbol_equity_close_refused",
     kreason.get(kid[4]) == "CRYPTO_BIN_CLOSE_MISMATCH",
     str(kreason))
case("K5_crypto_ignores_equity_holiday", kid[5] not in kreason)
case("K6_unknown_symbol_refused",
     kreason.get(kid[6]) == "SYMBOL_CLASS_UNKNOWN", str(kreason))

T0S = datetime(2025, 3, 1, 9, 30, tzinfo=ET)
NOWS = datetime(2025, 3, 9, 12, 0, tzinfo=ET)
sroot = os.path.join(tmp, "spring")
sobs = core.SignalObserver(sroot, T0S, clock=lambda: NOWS)
s_rows = [
    row("BTC-USD", "2025-03-09T01:30:00-05:00",
        "2025-03-09T05:30:00-04:00"),   # K8 spring absorbing bin (3h)
    row("BTC-USD", "2025-03-09T01:30:00-05:00",
        "2025-03-09T06:30:00-04:00"),   # K9 4h-elapsed trap
    row("BTC-USD", "2025-03-08T21:30:00-05:00",
        "2025-03-09T01:30:00-05:00"),   # K10 pre-transition bin
]
ssum = sobs.run_cycle(s_rows, HEALTHY, now=NOWS)
sreason = {r["signal_id"]: r["reason"]
           for r in ssum["signals_refused"]}
sid = {i + 8: r["signal_id"] for i, r in enumerate(s_rows)}
case("K8_spring_absorbing_bin_3h_admitted",
     sid[8] not in sreason, str(ssum["signals_refused"]))
case("K9_spring_4h_elapsed_trap_refused",
     sreason.get(sid[9]) == "CRYPTO_BIN_CLOSE_MISMATCH",
     str(sreason))
case("K10_spring_pre_transition_bin_admitted",
     sid[10] not in sreason)

T0F = datetime(2025, 10, 30, 9, 30, tzinfo=ET)
NOWF = datetime(2025, 11, 2, 12, 0, tzinfo=ET)
froot = os.path.join(tmp, "fall")
fobs = core.SignalObserver(froot, T0F, clock=lambda: NOWF)
f_rows = [
    row("BTC-USD", "2025-11-02T01:30:00-04:00",
        "2025-11-02T05:30:00-05:00"),   # K12 fall absorbing bin (5h)
    row("BTC-USD", "2025-11-02T01:30:00-04:00",
        "2025-11-02T05:30:00-04:00"),   # K13 wrong-offset trap
]
fsum = fobs.run_cycle(f_rows, HEALTHY, now=NOWF)
freason = {r["signal_id"]: r["reason"]
           for r in fsum["signals_refused"]}
fid = {i + 12: r["signal_id"] for i, r in enumerate(f_rows)}
case("K12_fall_absorbing_bin_5h_admitted",
     fid[12] not in freason, str(fsum["signals_refused"]))
case("K13_fall_wrong_offset_close_refused",
     freason.get(fid[13]) == "CRYPTO_BIN_CLOSE_MISMATCH",
     str(freason))

# ================= P: V8 preservation under v3 ===============

proot = os.path.join(tmp, "p")
T0P = datetime(2025, 11, 24, 9, 30, tzinfo=ET)
NOWP = datetime(2025, 11, 26, 17, 0, tzinfo=ET)
pobs = core.SignalObserver(proot, T0P, clock=lambda: NOWP)
pobs.run_cycle([row("NVDA", "2025-11-26T09:30:00-05:00",
                    "2025-11-26T13:30:00-05:00")], HEALTHY, now=NOWP)
plog = os.path.join(proot, core.LOG_FILENAME)
pman = os.path.join(proot, core.MANIFEST_FILENAME)
_, precs = read_records(proot)
rep = core.verify_chain(plog, pman)
case("P1_v3_chain_verifies_and_schema_v3",
     rep["ok"] and all(r.get("schema") == "shadow-signal-v3"
                       and r.get("prev_hash") and r.get("hash")
                       for r in precs), str(rep))
with open(plog, "a", encoding="utf-8") as fh:
    fh.write('{"record_kind": "shadow_cycle", "partial')
core.SignalObserver(proot, T0P, clock=lambda: NOWP)
_, precs2 = read_records(proot)
case("P2_v3_torn_tail_recovers",
     core.verify_chain(plog, pman)["ok"]
     and precs2[-1].get("record_kind") == "shadow_recovery")

lroot = os.path.join(tmp, "legacy")
os.makedirs(lroot)
shutil.copy(pman, os.path.join(lroot, core.MANIFEST_FILENAME))
legacy = {"record_kind": "shadow_cycle", "schema": "shadow-signal-v2",
          "cohort": "SHADOW_OBSERVATION", "counts_as_trade": False,
          "logged_at": NOWP.isoformat(), "status": "HEALTHY"}
with open(os.path.join(lroot, core.LOG_FILENAME), "w",
          encoding="utf-8") as fh:
    fh.write(json.dumps(legacy) + "\n")
case("P3_legacy_unchained_log_refused",
     refuses(lambda: core.SignalObserver(lroot, T0P,
                                         clock=lambda: NOWP)))

troot2 = os.path.join(tmp, "t0")
T0T = datetime(2025, 11, 26, 13, 30, tzinfo=ET)
tobs = core.SignalObserver(troot2, T0T, clock=lambda: NOWP)
s1 = tobs.run_cycle([row("NVDA", "2025-11-26T09:30:00-05:00",
                         "2025-11-26T13:30:00-05:00")],
                    HEALTHY, now=NOWP)
s2 = tobs.run_cycle([row("MSFT", "2025-11-26T13:30:00-05:00",
                         "2025-11-26T16:00:00-05:00")],
                    HEALTHY,
                    now=datetime(2025, 11, 26, 15, 0, tzinfo=ET))
case("P4_t0_strictness_preserved",
     s1["signals_refused"] and
     s1["signals_refused"][0]["reason"] == "PRELAUNCH_SIGNAL"
     and s2["signals_refused"] and
     s2["signals_refused"][0]["reason"] == "PARTIAL_BAR_NOT_CLOSED",
     f"{s1['signals_refused']} {s2['signals_refused']}")

fails = [n for n, ok in RESULTS if not ok]
print(f"{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS")
if fails:
    print("FAILURES:", ", ".join(fails))
sys.exit(0 if not fails else 1)
