"""Text 0 holdout-inventory builder, CORR4 (successor package).

Successor of the CORR3-draft builder (package commit e3f5e8e),
rebuilt against ChatGPT's HOLD blockers 1-2:

  - SELF-CONTAINED: the frozen pipeline modules (run_study13
    phase2/phase4 semantics, pine_backtest, scanner_rules) and the
    adopted 751-session table are VENDORED in this package
    (engine/, session_table_751.json) and hash-verified against
    stage1_manifest.json before anything is imported or read.
    Nothing is read from a stage home, an archive clone, or any
    path outside this package plus the session layout below.
  - NO OVERRIDES: the CLI is exactly --session-auth, --out,
    --summary. There is no --raw-dir, --symbols, --manifest,
    --session-table, or --mode argument, and no environment
    variable authorizes anything. The raw-capture directory is
    NOT a caller input: it is derived deterministically from the
    session layout - the "raw" subdirectory of the directory
    holding the session-authorization artifact (the Stage-1
    manifest pins this layout in its raw_capture binding).
  - SESSION AUTHORIZATION replaces the env latch: the build runs
    only under a session-authorization artifact (JSON) that names
    the pinned binding-content hash, this builder's own sha256,
    the pinned window and tier membership, the mode string
    TEXT0_STAGE2_INVENTORY_BUILD, a session id, and exactly two
    operators. It ALSO names the raw-capture receipt manifest's
    file sha256 and receipt root (below), so the capture bytes
    are pinned by an artifact issued before the build, not by
    anything the build itself computes first. The artifact is a
    governance record, not a secret: its force is pin
    verification plus the logged two-person session and the
    freeze-record entry of the Stage-2 addendum hash (see
    PACKAGE.md).
  - RAW CAPTURES ARE HASH-BOUND BEFORE PARSING: the raw
    directory must contain a receipt manifest
    (receipt_manifest.json, a fixed name inside the raw
    directory) listing the exact pinned 30 symbols and each
    capture file's sha256, with a receipt root = the canonical
    sha256 of that per-symbol hash map. The builder hashes the
    receipt file and compares it to the session authorization
    BEFORE parsing anything, verifies the receipt's root and
    symbol set against the authorization and the Stage-1 tiers,
    then hashes EVERY capture file and compares it to the
    receipt BEFORE any capture is parsed. Extra, missing,
    unlisted, symlinked (path-substituted), or hash-mismatched
    bytes fail closed with named errors. Only after every hash
    matches does the frozen phase2 parsing begin.
  - MISSING BYTES FAIL NAMED: before any symbol is built, every
    pinned symbol must have a capture file in the raw directory.
    A missing Tier 3 capture exits 3 with
    TIER3_CAPTURE_MISSING:<symbol>; Tier 2 likewise. The tier is
    never silently shrunk.

The admission gates and the resample are the frozen -13 phase2 /
phase4 code paths (vendored run_study13.phase4; admission gates
reproduced from phase2 verbatim, as in the P7b builder). The
builder computes NO performance quantity: it emits sealed-window
inventory rows + a provenance summary whose inventory hash and
census are the inputs to the Stage-2 addendum.
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.join(HERE, "engine")
MANIFEST_PATH = os.path.join(HERE, "stage1_manifest.json")
TABLE_PATH = os.path.join(HERE, "session_table_751.json")
RAW_NAME = "{sym}.json"
AUTH_MODE = "TEXT0_STAGE2_INVENTORY_BUILD"
RECEIPT_FILE = "receipt_manifest.json"
RAW_LAYOUT = "session_auth_dir/raw"
RECEIPT_KEYS = {"receipt_id", "binding_content_sha256", "symbols",
                "per_symbol_sha256", "receipt_root_sha256"}

PINNED_BINDING_CONTENT_SHA256 = "a6af811edd60692503abcf115c41a1b11263d69a02eb4e798337fd6708742fc6"
MANIFEST_FILE_KEYS = {"binding_id", "stage", "status",
                      "window_start", "window_end", "tiers",
                      "session_table_sha256", "corr2_source_sha256",
                      "engine", "builder", "stage2_addendum_file",
                      "raw_capture"}
MANIFEST_CONTENT_KEYS = ("binding_id", "stage", "window_start",
                         "window_end", "tiers",
                         "session_table_sha256",
                         "corr2_source_sha256", "engine",
                         "raw_capture")
AUTH_KEYS = {"auth_id", "binding_content_sha256", "builder_sha256",
             "window_start", "window_end", "tiers", "mode",
             "session_id", "operators", "date",
             "raw_receipt_manifest_sha256",
             "raw_receipt_root_sha256"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode()).hexdigest()


def binding_fail(msg):
    print(f"FAIL-CLOSED (corr4 builder binding): {msg}")
    sys.exit(2)


def load_and_verify_manifest():
    """Verify, in order: manifest shape; binding content against
    the compiled-in pin; this builder's own bytes against the
    manifest's builder pin; the vendored engine files against the
    manifest's engine pins; the vendored session table against the
    manifest's table pin. Returns the manifest. Any drift exits 2
    before any capture or engine code is touched."""
    if not os.path.exists(MANIFEST_PATH):
        binding_fail("STAGE1_MANIFEST_MISSING: stage1_manifest.json "
                     "not found beside the builder")
    try:
        with open(MANIFEST_PATH) as f:
            m = json.load(f)
    except Exception as e:
        binding_fail(f"stage1 manifest unparseable: {e}")
    if set(m) != MANIFEST_FILE_KEYS:
        binding_fail(f"stage1 manifest key set drift: {sorted(m)}")
    content = {k: m[k] for k in MANIFEST_CONTENT_KEYS}
    if canonical_sha(content) != PINNED_BINDING_CONTENT_SHA256:
        binding_fail("stage1 manifest binding content != "
                     "compiled-in pin")
    if m["stage"] != 1 or m["status"] != "STAGE1-PINS-COMMITTED":
        binding_fail("stage1 manifest stage/status drift")
    own = sha256_file(os.path.abspath(__file__))
    if m["builder"]["sha256"] != own:
        binding_fail(f"builder self-hash {own} != Stage-1 builder "
                     f"pin {m['builder']['sha256']}")
    for name, want in m["engine"].items():
        p = os.path.join(ENGINE_DIR, name)
        if not os.path.exists(p) or sha256_file(p) != want:
            binding_fail(f"vendored engine pin drift: {name}")
    if not os.path.exists(TABLE_PATH) \
            or sha256_file(TABLE_PATH) != m["session_table_sha256"]:
        binding_fail("vendored session table pin drift")
    rc = m["raw_capture"]
    n_sym = len(m["tiers"]["tier2"]) + len(m["tiers"]["tier3"])
    if not isinstance(rc, dict) \
            or rc.get("raw_dir") != RAW_LAYOUT \
            or rc.get("receipt_file") != RECEIPT_FILE \
            or rc.get("file_template") != RAW_NAME \
            or rc.get("symbol_count") != n_sym:
        binding_fail("stage1 raw_capture binding drift: the "
                     "manifest's raw-capture layout / receipt "
                     "binding != the compiled-in session layout")
    return m


def verify_session_auth(path, manifest):
    """The session-authorization artifact must name exactly the
    pinned binding content, this builder's hash, the pinned window
    and tiers, the build mode string, a session id, a date, and
    exactly two distinct operators. Verified BEFORE the raw
    directory is touched."""
    if not os.path.exists(path):
        binding_fail(f"SESSION_AUTH_MISSING: {path} not found - "
                     "no build without a session authorization")
    try:
        with open(path) as f:
            a = json.load(f)
    except Exception as e:
        binding_fail(f"session auth unparseable: {e}")
    if set(a) != AUTH_KEYS:
        binding_fail(f"session auth key set drift: {sorted(a)}")
    if a["binding_content_sha256"] != PINNED_BINDING_CONTENT_SHA256:
        binding_fail("session auth does not name the pinned "
                     "binding content")
    if a["builder_sha256"] != sha256_file(os.path.abspath(__file__)):
        binding_fail("session auth builder hash != this builder")
    if a["window_start"] != manifest["window_start"] \
            or a["window_end"] != manifest["window_end"]:
        binding_fail("session auth window != pinned window")
    if a["tiers"] != manifest["tiers"]:
        binding_fail("session auth tiers != pinned tier membership")
    if a["mode"] != AUTH_MODE:
        binding_fail(f"session auth mode != {AUTH_MODE}")
    ops = a["operators"]
    if not isinstance(ops, list) or len(ops) != 2 \
            or len(set(ops)) != 2 \
            or not all(isinstance(o, str) and o for o in ops):
        binding_fail("session auth must name exactly two distinct "
                     "operators")
    if not a["auth_id"] or not a["session_id"] or not a["date"]:
        binding_fail("session auth id/session/date empty")
    for k in ("raw_receipt_manifest_sha256",
              "raw_receipt_root_sha256"):
        v = a[k]
        if not isinstance(v, str) or len(v) != 64 \
                or any(c not in "0123456789abcdef" for c in v):
            binding_fail(f"session auth {k} is not a sha256 hex "
                         "digest - the raw captures must be "
                         "pinned by the authorization before the "
                         "build touches them")
    return a


def derive_raw_dir(auth_path):
    """The raw-capture directory is derived, never supplied: the
    "raw" subdirectory of the directory holding the
    session-authorization artifact (the Stage-1 raw_capture
    binding pins this layout). No CLI argument can name it."""
    return os.path.join(
        os.path.dirname(os.path.abspath(auth_path)), "raw")


def verify_raw_captures_before_parse(manifest, auth, raw_dir):
    """Hash-bind the raw captures BEFORE any parsing, in order:

    1. the receipt manifest file's sha256 must equal the pin in
       the session authorization (hashed as bytes, before it is
       parsed);
    2. the parsed receipt must name this binding, the exact
       pinned symbol set in pinned order, and a receipt root
       (canonical sha256 of the per-symbol hash map) equal to
       the authorization's root pin and to its own contents;
    3. the raw directory must contain exactly the receipt plus
       one file per pinned symbol - extra or unlisted bytes are
       rejected, a missing capture fails with the named
       tier-aware error (exit 3), and a symlinked capture is a
       path substitution;
    4. EVERY capture file is hashed and compared to the receipt
       BEFORE any capture is parsed; a mismatch fails closed
       with RAW_CAPTURE_HASH_MISMATCH.

    Returns the verified per-symbol sha256 map. No capture byte
    is parsed before this function returns."""
    symbols = list(manifest["tiers"]["tier2"]) \
        + list(manifest["tiers"]["tier3"])
    if not os.path.isdir(raw_dir):
        binding_fail(f"RAW_CAPTURE_DIR_MISSING: derived raw "
                     f"directory {raw_dir} does not exist")
    receipt_path = os.path.join(raw_dir, RECEIPT_FILE)
    if os.path.islink(receipt_path):
        binding_fail("RAW_CAPTURE_PATH_SUBSTITUTED: "
                     f"{RECEIPT_FILE} is a symlink")
    if not os.path.exists(receipt_path):
        binding_fail(f"RAW_RECEIPT_MANIFEST_MISSING: "
                     f"{RECEIPT_FILE} not found in the derived "
                     "raw directory - captures are not pinned")
    if sha256_file(receipt_path) \
            != auth["raw_receipt_manifest_sha256"]:
        binding_fail("RAW_RECEIPT_MANIFEST_HASH_MISMATCH: "
                     "receipt manifest bytes != the session "
                     "authorization pin")
    try:
        with open(receipt_path) as f:
            receipt = json.load(f)
    except Exception as e:
        binding_fail(f"raw receipt manifest unparseable: {e}")
    if set(receipt) != RECEIPT_KEYS:
        binding_fail(f"raw receipt manifest key set drift: "
                     f"{sorted(receipt)}")
    if receipt["binding_content_sha256"] \
            != PINNED_BINDING_CONTENT_SHA256:
        binding_fail("RAW_RECEIPT_BINDING_MISMATCH: receipt does "
                     "not name the pinned binding content")
    if receipt["symbols"] != symbols:
        binding_fail("RAW_RECEIPT_SYMBOL_SET_MISMATCH: receipt "
                     "symbol list != pinned tier membership in "
                     "pinned order")
    per_symbol = receipt["per_symbol_sha256"]
    if not isinstance(per_symbol, dict) \
            or set(per_symbol) != set(symbols):
        binding_fail("RAW_RECEIPT_SYMBOL_SET_MISMATCH: receipt "
                     "per-symbol hash map != pinned symbol set")
    if canonical_sha(per_symbol) != receipt["receipt_root_sha256"]:
        binding_fail("RAW_RECEIPT_ROOT_MISMATCH: receipt root != "
                     "canonical hash of its per-symbol hash map")
    if receipt["receipt_root_sha256"] \
            != auth["raw_receipt_root_sha256"]:
        binding_fail("RAW_RECEIPT_ROOT_MISMATCH: receipt root != "
                     "the session authorization root pin")
    entries = set(os.listdir(raw_dir))
    expected_entries = {RECEIPT_FILE} | {
        RAW_NAME.format(sym=s) for s in symbols}
    # Missing captures first (named, tier-aware, exit 3) so a
    # shrunken tier is reported as such, never silently.
    for tier_name in ("tier3", "tier2"):
        for sym in manifest["tiers"][tier_name]:
            if RAW_NAME.format(sym=sym) not in entries:
                named = ("TIER3_CAPTURE_MISSING" if tier_name
                         == "tier3" else "TIER2_CAPTURE_MISSING")
                print(f"{named}: {sym} - no capture file in the "
                      "derived raw directory; failing closed, "
                      "tier not shrunk")
                sys.exit(3)
    extra = sorted(entries - expected_entries)
    if extra:
        binding_fail(f"RAW_CAPTURE_UNLISTED_FILE: raw directory "
                     f"carries byte(s) the receipt does not "
                     f"list: {extra}")
    for sym in symbols:
        p = os.path.join(raw_dir, RAW_NAME.format(sym=sym))
        if os.path.islink(p):
            binding_fail(f"RAW_CAPTURE_PATH_SUBSTITUTED: {sym} "
                         "capture is a symlink, not the pinned "
                         "file")
    # Hash-compare EVERY capture before parsing ANY capture.
    verified = {}
    for sym in symbols:
        p = os.path.join(raw_dir, RAW_NAME.format(sym=sym))
        actual = sha256_file(p)
        if actual != per_symbol[sym]:
            binding_fail(f"RAW_CAPTURE_HASH_MISMATCH: {sym} "
                         "capture bytes != receipt pin - "
                         "rejected before parsing")
        verified[sym] = actual
    return verified


# =====================================================================
# Frozen phase2 admission (reproduced verbatim from the -13 study /
# P7b builder, as in the CORR3 draft): a sealed-window capture is
# admitted only if it passes every gate below.
# =====================================================================
import pandas as pd

ZERO_VOL_EPS = 1e-9
EXPECTED_STARTS = ["13:30", "14:30", "15:30", "16:30", "17:30",
                   "18:30", "19:30", "20:30", "21:30", "22:30",
                   "23:30", "00:30", "01:30", "02:30", "03:30"]
EXPECTED_STARTS_EARLY = EXPECTED_STARTS[:8]
_XNYS = None


def _xnys():
    global _XNYS
    if _XNYS is None:
        import pandas_market_calendars as mcal
        _XNYS = mcal.get_calendar("XNYS")
    return _XNYS


def expected_for_date(d):
    cal = _xnys()
    day = cal.schedule(start_date=d, end_date=d)
    if day.empty:
        return None
    o = day.iloc[0]["market_open"].tz_convert("UTC")
    c = day.iloc[0]["market_close"].tz_convert("UTC")
    out, t = [], o
    while t < c:
        out.append(t)
        t += pd.Timedelta(hours=1)
    return out


def admission_failures(df, expected):
    """EXACT reproduction of the frozen phase2 gates + file-level
    gates. Returns a list of failure strings; [] = admitted."""
    fails = []
    meta = {"rows": int(len(df))}
    idx = df.index
    if str(idx.tz) != "America/New_York":
        fails.append(f"index tz {idx.tz} != America/New_York")
    if not idx.is_monotonic_increasing or idx.has_duplicates:
        fails.append("index not strictly increasing / duplicates")
    if len(df) and not bool((df["Volume"] >= 0).all()):
        fails.append("negative volume")
    if len(df) and not bool((df[["Open", "High", "Low", "Close"]] > 0)
                            .all().all()):
        fails.append("nonpositive price")
    if idx.tz is not None and len(df):
        utc = idx.tz_convert("UTC")
        have = sorted({t.strftime("%H:%M") for t in utc})
        exp = sorted({t.strftime("%H:%M") for t in expected})
        if have != exp:
            fails.append(f"per-date start-set mismatch: "
                         f"have {have} expected {exp}")
    if len(df) != len(expected):
        fails.append(f"row count {len(df)} != expected "
                     f"{len(expected)}")
    if len(df) and len(expected) and len(df) == len(expected):
        diffs = [abs((a - b).total_seconds())
                 for a, b in zip(idx, expected)]
        if max(diffs) != 0.0:
            fails.append(f"timestamp set mismatch: max diff "
                         f"{max(diffs)}s")
    # Volume gates on admitted prelim bars (exact -13 semantics).
    import numpy as np
    o = df["Open"].to_numpy(float)
    h = df["High"].to_numpy(float)
    low = df["Low"].to_numpy(float)
    c = df["Close"].to_numpy(float)
    v = df["Volume"].to_numpy(float)
    span = h - low
    tol = 1e-9 * np.maximum(1.0, np.abs(span))
    price_moving = (np.abs(c - o) > tol) | (span > tol)
    n_pmzv = int((price_moving & (v <= ZERO_VOL_EPS)).sum())
    n_zv = int((v <= ZERO_VOL_EPS).sum())
    meta.update({"prelim_rows": int(len(df)),
                 "zero_volume_rows": n_zv,
                 "price_moving_zero_volume_rows": n_pmzv})
    if n_zv:
        fails.append(f"{n_zv} zero-volume rows in admitted set")
    if n_pmzv:
        fails.append(f"{n_pmzv} price-moving zero-volume rows in "
                     "admitted set")
    return fails, meta


def td12_to_frame(raw):
    meta = raw.get("meta") or {}
    if meta.get("exchange_timezone") != "America/New_York" \
            or meta.get("interval") != "1h" \
            or raw.get("status") == "error":
        return None
    vals = raw.get("values")
    if not vals:
        return None
    df = pd.DataFrame(vals)
    need = {"datetime", "open", "high", "low", "close", "volume"}
    if not need.issubset(df.columns):
        return None
    df = df[["datetime", "open", "high", "low", "close", "volume"]]
    ts = pd.to_datetime(df["datetime"], format="%Y-%m-%d %H:%M:%S")
    df.index = pd.DatetimeIndex(ts).tz_localize("America/New_York")
    df = df.drop(columns=["datetime"]).astype(float)
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    return df


def is_qualifying_file(path, expected):
    """Reproduction of the -13 phase2 file gates (unchanged)."""
    try:
        with open(path) as f:
            raw = json.load(f)
    except Exception as e:
        return None, {"f1_parse": str(e)[:80]}
    meta = raw.get("meta") or {}
    info = {"meta_symbol": meta.get("symbol"),
            "meta_interval": meta.get("interval"),
            "meta_tz": meta.get("exchange_timezone"),
            "declared_rows": len(raw.get("values") or [])}
    sym = os.path.basename(path).split("__")[0].split(".")[0]
    if meta.get("symbol") not in (None, sym):
        info["f2_symbol_mismatch"] = meta.get("symbol")
        return None, info
    df = td12_to_frame(raw)
    if df is None:
        info["f3_frame"] = False
        return None, info
    if df.index.has_duplicates:
        info["f4_dup_timestamps"] = True
        return None, info
    if not df.index.is_monotonic_increasing:
        df = df.sort_index()
    return df, info


def build(manifest, auth, raw_dir, out_path, summary_path):
    import numpy as np
    tiers = manifest["tiers"]
    symbols = list(tiers["tier2"]) + list(tiers["tier3"])
    ws, we = manifest["window_start"], manifest["window_end"]

    # Capture binding FIRST: the receipt manifest and every
    # capture file are hash-verified against the session
    # authorization's pre-issued pins before ANY capture byte is
    # parsed (and before the session table is read). Named,
    # tier-aware, fail-closed; the tier is never silently shrunk.
    hashes = verify_raw_captures_before_parse(manifest, auth,
                                              raw_dir)

    with open(TABLE_PATH) as f:
        table = json.load(f)
    window_sessions = [s for s in table["sessions"]
                       if ws <= s["date"] <= we]
    if not window_sessions:
        binding_fail("session table carries no sessions inside "
                     "the pinned window")
    n_early = sum(1 for s in window_sessions
                  if s["close"] == "13:00")
    expected_bars = 2 * len(window_sessions) - n_early
    expected = []
    for s in window_sessions:
        expected.extend(expected_for_date(s["date"]))
    expected = pd.DatetimeIndex(expected)

    admitted = {}
    for sym in symbols:
        path = os.path.join(raw_dir, RAW_NAME.format(sym=sym))
        df, _info = is_qualifying_file(path, expected)
        if df is None:
            print(f"STOP {sym}: capture fails phase2 file gates "
                  f"{_info}")
            sys.exit(2)
        fails, _meta = admission_failures(df, expected)
        if fails:
            print(f"STOP {sym}: capture fails phase2 admission: "
                  f"{fails}")
            sys.exit(2)
        admitted[sym] = df

    sys.path.insert(0, ENGINE_DIR)
    import run_study13 as drv
    import pine_backtest as pb
    saved = drv.EXPECTED_BARS_4H
    drv.EXPECTED_BARS_4H = expected_bars
    try:
        bars4h = drv.phase4(admitted, window_sessions, symbols)
    finally:
        drv.EXPECTED_BARS_4H = saved
    if drv.failures:
        print(f"STOP: phase4 failures: {drv.failures}")
        sys.exit(2)

    # ---- rows (identical construction to the P7b builder, as in
    # the CORR3 draft: ema21/55/200 are the engine's e21/e55/e200,
    # atr_pct = atr/close, NaN -> null, and the generator domain is
    # positional: WARMUP <= i <= n-2) --------------------------------
    ordinal = {s["date"]: i for i, s in enumerate(window_sessions)}
    rows, per_symbol, census = [], {}, 0
    for sym in symbols:
        df = pb.add_pine_indicators(bars4h[sym])
        n = len(df)
        miss = {"atr": 0, "atr_pct": 0, "ema21": 0, "ema55": 0,
                "ema200": 0}
        miss_dom = dict(miss)
        bins = {"09:30": 0, "13:30": 0}
        fires_dom = 0
        for i in range(n):
            r = df.iloc[i]
            ts = df.index[i]
            close = float(r["Close"])
            atr = None if r["atr"] != r["atr"] else float(r["atr"])
            e21 = None if r["e21"] != r["e21"] else float(r["e21"])
            e55 = None if r["e55"] != r["e55"] else float(r["e55"])
            e200 = None if r["e200"] != r["e200"] \
                else float(r["e200"])
            atr_pct = (atr / close) if atr is not None else None
            in_dom = pb.WARMUP <= i <= n - 2
            sig = bool(pb.pine_buy_signal(df, i)) if i >= 1 \
                else False
            vals = {"atr": atr, "atr_pct": atr_pct, "ema21": e21,
                    "ema55": e55, "ema200": e200}
            for k, v in vals.items():
                if v is None:
                    miss[k] += 1
                    if in_dom:
                        miss_dom[k] += 1
            bin_start = ts.strftime("%H:%M")
            if bin_start in bins:
                bins[bin_start] += 1
            if in_dom and sig:
                fires_dom += 1
            rows.append({
                "symbol": sym, "idx": i, "ts": ts.isoformat(),
                "session_date": ts.strftime("%Y-%m-%d"),
                "session_ordinal": ordinal[ts.strftime("%Y-%m-%d")],
                "bin": bin_start, "close": close, "atr": atr,
                "atr_pct": atr_pct, "ema21": e21, "ema55": e55,
                "ema200": e200, "signal": sig,
                "in_generator_domain": in_dom,
            })
        census += fires_dom
        per_symbol[sym] = {
            "bars": n, "first_ts": df.index[0].isoformat(),
            "last_ts": df.index[-1].isoformat(),
            "domain_bars": sum(1 for i in range(n)
                               if pb.WARMUP <= i <= n - 2),
            "bin_counts": bins, "fires_in_domain": fires_dom,
            "missing_fields_full_series": miss,
            "missing_fields_generator_domain": miss_dom,
        }
        print(f"INV {sym}: bars {n} fires_domain {fires_dom} "
              f"missing_dom {miss_dom}", flush=True)

    with open(out_path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    inv_sha = sha256_file(out_path)
    summary = {
        "builder": "build_holdout_inventory_corr4.py (successor "
                   "package, 2026-10-29)",
        "binding": {
            "binding_id": manifest["binding_id"],
            "binding_content_sha256":
                PINNED_BINDING_CONTENT_SHA256,
            "stage1_manifest_file_sha256": sha256_file(
                MANIFEST_PATH),
            "builder_sha256": sha256_file(
                os.path.abspath(__file__)),
            "engine_sha256": dict(manifest["engine"]),
            "session_table_sha256":
                manifest["session_table_sha256"],
            "session_auth_id": auth["auth_id"],
            "session_id": auth["session_id"],
            "raw_receipt_manifest_sha256":
                auth["raw_receipt_manifest_sha256"],
            "raw_receipt_root_sha256":
                auth["raw_receipt_root_sha256"],
            "raw_dir_layout": RAW_LAYOUT,
        },
        "window": {"start": ws, "end": we,
                   "sessions": len(window_sessions),
                   "early_closes": n_early,
                   "expected_bars_per_symbol": expected_bars},
        "tiers": tiers,
        "per_symbol": per_symbol,
        "input_file_sha256": hashes,
        "inventory_sha256": inv_sha,
        "census_fires_in_generator_domain": census,
        "stage2_addendum_inputs": {
            "inventory_sha256": inv_sha,
            "expected_fires": census},
        "note": "The Stage-2 addendum is a separate reviewed "
                "artifact created after this build; its hash is "
                "entered in the freeze record before any counting "
                "run. This summary is provenance evidence, not a "
                "pin.",
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    print(f"INVENTORY sha256: {inv_sha} | bars "
          f"{len(rows)} | census fires {census}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session-auth", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()
    manifest = load_and_verify_manifest()
    auth = verify_session_auth(args.session_auth, manifest)
    return build(manifest, auth, derive_raw_dir(args.session_auth),
                 args.out, args.summary)


if __name__ == "__main__":
    sys.exit(main())
