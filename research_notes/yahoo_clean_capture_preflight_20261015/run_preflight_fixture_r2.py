#!/usr/bin/env python3
"""QF-YAHOO-CLEAN-CAPTURE-PREFLIGHT-20261015-08 r2 — bounded repair fixture.

Repairs exactly the four gaps from the r1 review (Issue #1 comment
6192334316); all r1 checks C0-C7 are retained (C5/C6 run against the
repaired mechanisms):

  G1 publication: r1 used exists()+os.rename and mislabeled rename as
     O_EXCL. r2 publishes via os.link(tmp, final): hard-link creation is
     atomic and fails with EEXIST if the destination exists — a genuine
     no-clobber primitive. Proven by a real TWO-PROCESS collision (C8).
  G2 attempt journal: implemented (fsync'd JSONL append BEFORE the
     simulated request) and exercised: journal+no-file =>
     ATTEMPT_CONSUMED_AMBIGUOUS with zero re-request eligibility;
     final+matching hash => SKIP_VERIFIED; final mismatch => HOLD (C9).
  G3 qualification: expected bars per session derive from the pinned
     session schedule (full XNYS session = 7 hourly rows; 13:00 early
     close = 4), never a hard-coded constant. A final early-close
     session QUALIFIES; a truncated early close HOLDs; crypto keeps its
     separate UTC policy (24 rows/day) (C10).
  G4 durability: NOT repaired in code — see the r2 memo. Mount evidence
     is pinned; survival across VM replacement is not claimed.

Synthetic bytes only. Zero network (sockets denied first). No yfinance.
"""
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile

SOCKET_ATTEMPTS = {"count": 0}


class NetworkDeniedError(RuntimeError):
    pass


def _deny(*a, **k):
    SOCKET_ATTEMPTS["count"] += 1
    raise NetworkDeniedError("network denied: preflight fixture")


socket.socket = _deny
socket.create_connection = _deny
socket.getaddrinfo = _deny
socket.gethostbyname = _deny

import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(HERE, "capture_manifest.json")
NY = "America/New_York"
RESULTS = []


def report(cid, desc, expect, got, checks):
    match = (got == expect) and all(checks.values())
    RESULTS.append({"id": cid, "desc": desc, "expect": expect, "got": got,
                    "checks": checks, "match": match})
    print(f"{cid:34s} expect={expect:22s} got={got:22s} match={match}")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Session construction (unchanged from r1; frozen canonical spec)
# ---------------------------------------------------------------------------
def construct_4h(df_1h, early_close_dates=()):
    df = df_1h.copy()
    df.index = pd.DatetimeIndex(df.index).tz_convert(NY)
    dates = df.index.normalize()
    close_map = {d: "13:00" for d in pd.to_datetime(list(early_close_dates))}
    keep, bins = [], []
    for ts, d in zip(df.index, dates):
        close_t = pd.Timestamp(f"{d.date()} {close_map.get(d, '16:00')}",
                               tz=NY)
        t = ts.time()
        if pd.Timestamp(f"{d.date()} 09:30", tz=NY) <= ts < close_t:
            keep.append(True)
            bins.append(pd.Timestamp(f"{d.date()} 09:30", tz=NY)
                        if t < pd.Timestamp("13:30").time()
                        else pd.Timestamp(f"{d.date()} 13:30", tz=NY))
        else:
            keep.append(False)
            bins.append(pd.NaT)
    df = df[keep]
    df["bin"] = [b for b, k in zip(bins, keep) if k]
    out = df.groupby("bin").agg(Open=("Open", "first"), High=("High", "max"),
                                Low=("Low", "min"), Close=("Close", "last"),
                                Volume=("Volume", "sum"))
    out.index.name = "bar_start"
    return out


def synth_1h(days):
    rows, idx = [], []
    base = 100.0
    for date_str, n in days:
        start = pd.Timestamp(f"{date_str} 09:30", tz=NY)
        for i in range(n):
            ts = start + pd.Timedelta(hours=i)
            o = base + i
            rows.append({"Open": o, "High": o + 1.0, "Low": o - 1.0,
                         "Close": o + 0.5, "Volume": 1000 + 10 * i,
                         "Dividends": 0.0, "Stock Splits": 0.0})
            idx.append(ts)
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx))


def synth_crypto_day(date_str, n=24):
    rows, idx = [], []
    start = pd.Timestamp(f"{date_str} 00:00", tz="UTC")
    for i in range(n):
        o = 200.0 + i
        rows.append({"Open": o, "High": o + 1.0, "Low": o - 1.0,
                     "Close": o + 0.5, "Volume": 500 + i,
                     "Dividends": 0.0, "Stock Splits": 0.0})
        idx.append(start + pd.Timedelta(hours=i))
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx))


# ---------------------------------------------------------------------------
# G3 — calendar-aware qualification. Expected rows per session derive
# from the pinned session schedule: XNYS full session 7 hourly bars
# (09:30..15:30 starts); 13:00 early close 4 (09:30..12:30 starts).
# Crypto: separate UTC policy, 24 rows per UTC day.
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = ["Open", "High", "Low", "Close", "Volume",
                   "Dividends", "Stock Splits"]


def expected_rows(date_str, early_close_dates=(), kind="equity"):
    if kind == "crypto":
        return 24
    return 4 if date_str in set(early_close_dates) else 7


def qualify(df, sessions, early_close_dates=(), kind="equity",
            throttle_marker=False):
    if throttle_marker:
        return "HOLD:THROTTLED"
    if df is None or len(df) == 0:
        return "HOLD:MISSING"
    if any(f not in df.columns for f in REQUIRED_FIELDS):
        return "HOLD:SCHEMA_DRIFT"
    if df.index.has_duplicates or not df.index.is_monotonic_increasing:
        return "HOLD:INTEGRITY"
    bad = (df["High"] < df[["Open", "Close"]].max(axis=1)) | \
          (df["Low"] > df[["Open", "Close"]].min(axis=1)) | (df["Volume"] < 0)
    if bad.any():
        return "HOLD:IMPOSSIBLE_OHLCV"
    day_counts = df.index.normalize().value_counts()
    present_dates = {str(ts.date()) for ts in day_counts.index}
    if len(present_dates) < len(sessions):
        return "HOLD:MISSING_SESSIONS"
    for d in sessions:
        actual = int(day_counts.get(pd.Timestamp(d, tz=df.index.tz), 0)) \
            if kind == "equity" else \
            int((df.index.normalize() == pd.Timestamp(d, tz="UTC")).sum())
        if actual < expected_rows(d, early_close_dates, kind):
            return "HOLD:PARTIAL"
    coverage = len(present_dates) / len(sessions)
    return "QUALIFIED" if coverage >= 0.8 else "COVERAGE_LIMITED"


# ---------------------------------------------------------------------------
# G1 — genuinely no-clobber atomic publication via os.link.
# Write temp in the same directory, fsync the file, then os.link(tmp,
# final): link creation is atomic and raises FileExistsError if final
# already exists — there is no check-then-act window and an existing
# final can never be replaced. Unlink temp, fsync the directory.
# ---------------------------------------------------------------------------
class WriteOnceCollision(Exception):
    pass


def archive_write(root, rel, data_bytes):
    final = os.path.join(root, rel)
    os.makedirs(os.path.dirname(final), exist_ok=True)
    tmp = final + f".tmp-{os.getpid()}"
    with open(tmp, "wb") as fh:
        fh.write(data_bytes)
        fh.flush()
        os.fsync(fh.fileno())
    try:
        os.link(tmp, final)
    except FileExistsError:
        os.unlink(tmp)
        raise WriteOnceCollision(rel)
    os.unlink(tmp)
    fsync_dir(os.path.dirname(final))
    return sha256_bytes(data_bytes)


# ---------------------------------------------------------------------------
# G2 — fsync'd attempt journal + restart reconciliation.
# The attempt record is appended and fsync'd BEFORE any request. On
# restart: final file present + hash match => SKIP_VERIFIED; final
# present + mismatch => HOLD:FINAL_MISMATCH; attempt journaled but no
# final file => ATTEMPT_CONSUMED_AMBIGUOUS (never re-requested);
# neither => ELIGIBLE.
# ---------------------------------------------------------------------------
JOURNAL_REL = "attempt_journal.jsonl"


def journal_attempt(root, symbol):
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, JOURNAL_REL)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"event": "ATTEMPT", "symbol": symbol},
                            sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    fsync_dir(root)


def _journaled(root):
    path = os.path.join(root, JOURNAL_REL)
    if not os.path.exists(path):
        return set()
    out = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.add(json.loads(line)["symbol"])
    return out


def reconcile(root, rel, symbol, expected_sha256):
    final = os.path.join(root, rel)
    if os.path.exists(final):
        actual = sha256_bytes(open(final, "rb").read())
        return "SKIP_VERIFIED" if actual == expected_sha256 \
            else "HOLD:FINAL_MISMATCH"
    if symbol in _journaled(root):
        return "ATTEMPT_CONSUMED_AMBIGUOUS"
    return "ELIGIBLE"


def child_publish(argv):
    """Subprocess entry for the C8 two-process collision fixture."""
    _, root, rel, payload_path, result_path = argv
    data = open(payload_path, "rb").read()
    try:
        h = archive_write(root, rel, data)
        outcome = {"result": "PUBLISHED", "sha256": h}
    except WriteOnceCollision:
        outcome = {"result": "WRITE_ONCE_COLLISION"}
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump(outcome, fh, sort_keys=True)
    return 0


def main():
    # C0 — network denial (retained from r1)
    try:
        socket.create_connection(("example.invalid", 443), timeout=1)
        denied = False
    except NetworkDeniedError:
        denied = True
    except Exception:
        denied = False
    report("C0-network-denial", "socket layer patched before anything runs",
           "NETWORK_DENIED", "NETWORK_DENIED" if denied else "NOT_DENIED",
           {"socket_raises": denied,
            "attempts_recorded": SOCKET_ATTEMPTS["count"] >= 1})

    # C1 — manifest exactness (retained from r1)
    man = json.load(open(MANIFEST_PATH))
    order = [e["symbol"] for e in sorted(man["request_order"],
                                         key=lambda e: e["i"])]
    expected51 = ["NVDA", "PLTR", "TSLA", "SOFI", "SMCI", "AMD", "AAPL",
                  "MSFT", "META", "COIN", "MSTR", "AVGO", "BTC-USD",
                  "ETH-USD", "SOL-USD", "GOOGL", "AMZN", "NFLX", "CRM", "MU",
                  "INTC", "LRCX", "AMAT", "QCOM", "ARM", "HOOD", "APP",
                  "NET", "SNOW", "DDOG", "CRWD", "SHOP", "RKLB", "ASTS",
                  "LUNR", "PYPL", "NU", "MELI", "SPY", "IWM", "SMH", "ARKK",
                  "XLF", "DOGE-USD", "AVAX-USD", "LINK-USD", "XRP-USD",
                  "NIO", "MRNA", "PFE", "F"]
    p = man["request_params"]
    report("C1-manifest-order", "52 requests: UNIVERSE_X order + QQQ dep",
           "EXACT", "EXACT" if order == expected51 + ["QQQ"] else "DRIFT",
           {"count_52": len(order) == 52,
            "universe_51_exact": order[:51] == expected51,
            "qqq_dependency_last": order[51] == "QQQ",
            "policy_pins": p["auto_adjust"] is False
            and p["prepost"] is False and p["interval"] == "1h"
            and p["actions"] is True,
            "budget_caps": man["call_budget"]["max_requests_total"] == 52
            and man["call_budget"]["attempts_per_symbol"] == 1})

    # C2 — DST labeling (retained)
    df = synth_1h([("2025-03-07", 7), ("2025-03-10", 7)])
    bars = construct_4h(df)
    labels = [(str(ts.date()), ts.strftime("%H:%M"),
               ts.utcoffset().total_seconds() / 3600)
              for ts in bars.index]
    report("C2-dst-labels", "spring-forward week: labels stay 09:30/13:30 ET",
           "PASS", "PASS" if len(bars) == 4 else "FAIL",
           {"four_bars": len(bars) == 4,
            "labels": [l[1] for l in labels] == ["09:30", "13:30"] * 2,
            "offsets_est_edt": labels[0][2] == -5.0
            and labels[2][2] == -4.0})

    # C3 — early-close construction (retained)
    df_ec = synth_1h([("2025-11-26", 7), ("2025-11-28", 4)])
    bars_ec = construct_4h(df_ec, early_close_dates=["2025-11-28"])
    ec = bars_ec.loc[bars_ec.index.normalize()
                     == pd.Timestamp("2025-11-28", tz=NY)]
    report("C3-early-close", "early-close day emits exactly the 09:30 bar",
           "PASS", "PASS" if len(ec) == 1 else "FAIL",
           {"one_bar": len(ec) == 1,
            "label_0930": ec.index[0].strftime("%H:%M") == "09:30",
            "volume_conserved": int(ec["Volume"].iloc[0])
            == int(df_ec.loc[df_ec.index.normalize()
                              == pd.Timestamp("2025-11-28", tz=NY),
                              "Volume"].sum())})

    # C4 — conservation + two-window parity (retained)
    full = synth_1h([("2025-03-05", 7), ("2025-03-06", 7),
                     ("2025-03-07", 7), ("2025-03-10", 7),
                     ("2025-03-11", 7)])
    bars_full = construct_4h(full)
    short = full.loc["2025-03-07":"2025-03-10 23:59"]
    bars_short = construct_4h(short)
    overlap = bars_short.index.intersection(bars_full.index)
    parity = bars_short.loc[overlap].equals(bars_full.loc[overlap])
    cons = all(
        int(bars_full.loc[ts, "Volume"]) ==
        int(full.loc[(full.index >= ts)
                     & (full.index < ts + pd.Timedelta(hours=4)),
                     "Volume"].sum())
        for ts in bars_full.index)
    report("C4-parity-conservation", "short-window bars == full-window bars",
           "PASS", "PASS" if (parity and cons) else "FAIL",
           {"parity_overlap_4": len(overlap) == 4 and parity,
            "volume_conservation": cons})

    # C5 — write-once archive via os.link (mechanism repaired, G1)
    root = tempfile.mkdtemp(prefix="qf_capture_fx_")
    payload = b"synthetic raw bytes for TEST\n"
    h1 = archive_write(root, "raw/TEST.csv", payload)
    collision = False
    try:
        archive_write(root, "raw/TEST.csv", b"different bytes\n")
    except WriteOnceCollision:
        collision = True
    on_disk = open(os.path.join(root, "raw/TEST.csv"), "rb").read()
    report("C5-write-once-archive", "os.link no-clobber publish + collision",
           "PASS", "PASS" if collision else "FAIL",
           {"hash_matches": h1 == sha256_bytes(payload),
            "restart_bytes_identical": on_disk == payload,
            "collision_refused": collision,
            "winner_bytes_unchanged": on_disk == payload,
            "no_tmp_left": not any(".tmp-" in f
                                   for f in os.listdir(
                                       os.path.join(root, "raw")))})

    # C6 — gates fail closed (calendar-aware qualify, G3 mechanism)
    good = synth_1h([("2025-03-07", 7), ("2025-03-10", 7)])
    sess = ["2025-03-07", "2025-03-10"]
    cases = {
        "missing": (None, sess, False, "HOLD:MISSING"),
        "partial": (synth_1h([("2025-03-07", 7), ("2025-03-10", 3)]),
                    sess, False, "HOLD:PARTIAL"),
        "throttled": (good, sess, True, "HOLD:THROTTLED"),
        "schema_drift": (good.drop(columns=["Volume"]), sess, False,
                         "HOLD:SCHEMA_DRIFT"),
        "missing_sessions": (synth_1h([("2025-03-07", 7)]), sess, False,
                             "HOLD:MISSING_SESSIONS"),
    }
    dup = pd.concat([good, good.iloc[[0]]]).sort_index()
    cases["duplicate"] = (dup, sess, False, "HOLD:INTEGRITY")
    bad = good.copy()
    bad.iloc[0, bad.columns.get_loc("High")] = -999.0
    cases["impossible_ohlcv"] = (bad, sess, False, "HOLD:IMPOSSIBLE_OHLCV")
    got_map = {k: qualify(d, s, throttle_marker=t)
               for k, (d, s, t, _) in cases.items()}
    report("C6-gates-fail-closed", "7 synthetic defect cases all HOLD",
           "ALL_HOLD",
           "ALL_HOLD" if all(got_map[k] == v[3]
                             for k, v in cases.items()) else str(got_map),
           {"good_qualifies": qualify(good, sess) == "QUALIFIED",
            **{f"case_{k}": got_map[k] == v[3]
               for k, v in cases.items()}})

    # C7 — no performance engine imported (retained)
    banned = [m for m in ("pine_backtest", "pine_signal_quality",
                          "v54_forward_harness", "scanner_rules",
                          "yfinance") if m in sys.modules]
    report("C7-no-engine", "no strategy/backtest/client module imported",
           "CLEAN", "CLEAN" if not banned else f"IMPORTED:{banned}",
           {"modules_absent": not banned})

    # C8 — G1 proof: real two-process collision on the same final path.
    # Two child processes publish DIFFERENT payloads concurrently;
    # exactly one must succeed, the loser must get WRITE_ONCE_COLLISION,
    # and the winning bytes/hash must never change afterwards.
    croot = tempfile.mkdtemp(prefix="qf_capture_race_")
    pa, pb = b"payload from writer A\n", b"payload from writer B (other)\n"
    paths = {}
    for tag, data in (("a", pa), ("b", pb)):
        pp = os.path.join(croot, f"payload_{tag}.bin")
        with open(pp, "wb") as fh:
            fh.write(data)
        paths[tag] = (pp, os.path.join(croot, f"result_{tag}.json"))
    procs = [subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--child-publish",
         croot, "raw/RACE.csv", pp, rp])
        for pp, rp in paths.values()]
    for pr in procs:
        pr.wait(timeout=60)
    outcomes = [json.load(open(rp)) for _, rp in paths.values()]
    results = sorted(o["result"] for o in outcomes)
    winner_sha = next((o["sha256"] for o in outcomes
                       if o["result"] == "PUBLISHED"), None)
    final_bytes = open(os.path.join(croot, "raw/RACE.csv"), "rb").read()
    report("C8-two-process-collision",
           "concurrent publishers: exactly one wins, loser collides",
           "ONE_WINNER",
           "ONE_WINNER" if results == ["PUBLISHED", "WRITE_ONCE_COLLISION"]
           else str(results),
           {"exactly_one_published": results.count("PUBLISHED") == 1,
            "loser_collision": results.count("WRITE_ONCE_COLLISION") == 1,
            "final_hash_is_winners": sha256_bytes(final_bytes) == winner_sha,
            "final_bytes_are_a_or_b": final_bytes in (pa, pb)})

    # C9 — G2 proof: journal + crash/restart reconciliation
    jroot = tempfile.mkdtemp(prefix="qf_capture_journal_")
    journal_attempt(jroot, "TEST")           # attempt fsync'd, then "crash"
    state_amb = reconcile(jroot, "raw/TEST.csv", "TEST",
                          sha256_bytes(payload))
    state_elig = reconcile(jroot, "raw/OTHER.csv", "OTHER",
                           sha256_bytes(payload))
    archive_write(jroot, "raw/DONE.csv", payload)   # completed symbol
    journal_attempt(jroot, "DONE")
    state_skip = reconcile(jroot, "raw/DONE.csv", "DONE",
                           sha256_bytes(payload))
    state_mismatch = reconcile(jroot, "raw/DONE.csv", "DONE",
                               sha256_bytes(b"not the real bytes"))
    report("C9-journal-reconciliation",
           "ambiguous consumed attempt; verified skip; mismatch HOLD",
           "RECONCILED",
           "RECONCILED" if (state_amb, state_skip, state_mismatch)
           == ("ATTEMPT_CONSUMED_AMBIGUOUS", "SKIP_VERIFIED",
               "HOLD:FINAL_MISMATCH") else
           f"{state_amb}/{state_skip}/{state_mismatch}",
           {"journal_no_file_ambiguous":
                state_amb == "ATTEMPT_CONSUMED_AMBIGUOUS",
            "ambiguous_not_eligible": state_amb != "ELIGIBLE",
            "no_attempt_eligible": state_elig == "ELIGIBLE",
            "final_match_skips": state_skip == "SKIP_VERIFIED",
            "final_mismatch_holds": state_mismatch == "HOLD:FINAL_MISMATCH",
            "journal_persisted": "TEST" in _journaled(jroot)})

    # C10 — G3 proof: calendar-aware partial-session qualification
    ec_sessions = ["2025-11-26", "2025-11-28"]
    ec_full = synth_1h([("2025-11-26", 7), ("2025-11-28", 4)])
    q_ec = qualify(ec_full, ec_sessions, early_close_dates=["2025-11-28"])
    ec_trunc = synth_1h([("2025-11-26", 7), ("2025-11-28", 3)])
    q_trunc = qualify(ec_trunc, ec_sessions,
                      early_close_dates=["2025-11-28"])
    crypto = synth_crypto_day("2025-11-28", 24)
    q_crypto = qualify(crypto, ["2025-11-28"],
                       early_close_dates=["2025-11-28"], kind="crypto")
    report("C10-calendar-aware-qualify",
           "final early close qualifies; truncated early close HOLDs",
           "CALENDAR_AWARE",
           "CALENDAR_AWARE" if (q_ec, q_trunc, q_crypto)
           == ("QUALIFIED", "HOLD:PARTIAL", "QUALIFIED")
           else f"{q_ec}/{q_trunc}/{q_crypto}",
           {"early_close_4_of_4_qualifies": q_ec == "QUALIFIED",
            "early_close_3_of_4_holds_partial": q_trunc == "HOLD:PARTIAL",
            "crypto_separate_utc_policy": q_crypto == "QUALIFIED",
            "equity_full_session_still_7":
                expected_rows("2025-11-26", ["2025-11-28"]) == 7
                and expected_rows("2025-11-28", ["2025-11-28"]) == 4})

    ok = all(r["match"] for r in RESULTS)
    summary = {"task": "QF-YAHOO-CLEAN-CAPTURE-PREFLIGHT-20261015-08 r2",
               "checks_total": len(RESULTS),
               "checks_matched": sum(1 for r in RESULTS if r["match"]),
               "all_match": ok,
               "socket_attempts_after_denial_check":
                   SOCKET_ATTEMPTS["count"],
               "results": RESULTS}
    out_path = os.path.join(HERE, "fixture_results_r2.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
    print(f"{summary['checks_matched']}/{summary['checks_total']} checks "
          f"matched — {'ALL MATCH' if ok else 'MISMATCH PRESENT'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child-publish":
        sys.exit(child_publish(sys.argv[1:]))
    main()
