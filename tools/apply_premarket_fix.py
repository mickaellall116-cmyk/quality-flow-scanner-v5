from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


ROOT = Path(__file__).resolve().parents[1]

# -----------------------------------------------------------------------------
# scanner_rules.py: canonical premarket math + prior regular-session close.
# -----------------------------------------------------------------------------
rules_path = ROOT / "scanner_rules.py"
rules = rules_path.read_text()
rules = replace_once(rules, 'SCANNER_VERSION = "5.2"\nRULE_VERSION = "2026-09-10-v2"', 'SCANNER_VERSION = "5.3"\nRULE_VERSION = "2026-09-14-v3"', "version bump")

premarket_rules = r'''

# ============================================================
# PREMARKET SESSION SNAPSHOT
# ============================================================
# US premarket runs 04:00-09:30 ET. yfinance only returns those
# bars when the download uses prepost=True. Crypto ("-USD")
# trades 24/7 so it has no premarket session.

PREMARKET_START_MIN = 4 * 60
PREMARKET_END_MIN = 9 * 60 + 30
PREMARKET_STRONG_GAP_PCT = 2.0
PREMARKET_CHASE_GAP_PCT = 5.0


def _premarket_na() -> dict[str, Any]:
    return {
        "pm_high": None,
        "pm_low": None,
        "pm_volume": None,
        "pm_vwap": None,
        "pm_last": None,
        "pm_gap_pct": None,
        "pm_range_pct": None,
        "pm_read": "N/A",
    }


def previous_regular_close(
    daily_df: pd.DataFrame,
    now: Optional[pd.Timestamp] = None,
) -> Optional[float]:
    """Return the last completed regular-session daily close before today ET.

    Yahoo can expose an in-progress daily bar for the current session. Excluding
    today's date prevents premarket gap math from accidentally using today's
    4-hour/daily price as the baseline.
    """
    try:
        if daily_df is None or daily_df.empty or "Close" not in daily_df:
            return None
        data = daily_df.copy().sort_index().dropna(subset=["Close"])
        if data.empty or not isinstance(data.index, pd.DatetimeIndex):
            return None

        current = pd.Timestamp.now(tz="America/New_York") if now is None else pd.Timestamp(now)
        if current.tzinfo is None:
            current = current.tz_localize("America/New_York")
        else:
            current = current.tz_convert("America/New_York")

        if data.index.tz is None:
            dates = data.index.date
        else:
            dates = data.index.tz_convert("America/New_York").date
        completed = data[dates < current.date()]
        if completed.empty:
            return None
        return float(completed["Close"].iloc[-1])
    except Exception:
        return None


def premarket_snapshot(
    df: pd.DataFrame,
    symbol: str,
    prev_close: Optional[float] = None,
    now: Optional[pd.Timestamp] = None,
) -> dict[str, Any]:
    """Summarize today's 04:00-09:30 ET premarket session.

    ``df`` should be 1m/5m/15m bars fetched with ``prepost=True``. ``prev_close``
    must be the previous completed regular-session close. Yahoo premarket volume
    can be absent or incomplete, so BULLISH/BEARISH reads use gap size plus where
    the latest premarket price sits inside the premarket range.
    """
    try:
        if df is None or df.empty or not isinstance(df.index, pd.DatetimeIndex):
            return _premarket_na()
        if str(symbol).upper().endswith("-USD"):
            return _premarket_na()

        data = df.copy().sort_index()
        local = data.index.tz_convert("America/New_York") if data.index.tz is not None else data.index
        current = _now_for_index(data.index, now)
        today = current.tz_convert("America/New_York").date() if current.tzinfo is not None else current.date()

        minutes = local.hour * 60 + local.minute
        session = data[(local.date == today) & (minutes >= PREMARKET_START_MIN) & (minutes < PREMARKET_END_MIN)]
        if session.empty:
            return _premarket_na()

        high = float(session["High"].max())
        low = float(session["Low"].min())
        volume = float(session["Volume"].sum()) if "Volume" in session else 0.0
        typical = (session["High"] + session["Low"] + session["Close"]) / 3.0
        vwap = float((typical * session["Volume"]).sum() / volume) if "Volume" in session and volume > 0 else None
        last = float(session["Close"].iloc[-1])

        gap_pct = None
        range_pct = None
        if prev_close is not None and float(prev_close) > 0:
            baseline = float(prev_close)
            gap_pct = round((last / baseline - 1.0) * 100.0, 2)
            range_pct = round((high - low) / baseline * 100.0, 2)

        read = "NEUTRAL"
        if gap_pct is not None and high > low:
            position = (last - low) / (high - low)
            if gap_pct >= PREMARKET_STRONG_GAP_PCT and position >= 0.75:
                read = "BULLISH"
            elif gap_pct <= -PREMARKET_STRONG_GAP_PCT and position <= 0.25:
                read = "BEARISH"

        return {
            "pm_high": round(high, 2),
            "pm_low": round(low, 2),
            "pm_volume": int(volume),
            "pm_vwap": round(vwap, 2) if vwap is not None else None,
            "pm_last": round(last, 2),
            "pm_gap_pct": gap_pct,
            "pm_range_pct": range_pct,
            "pm_read": read,
        }
    except Exception:
        return _premarket_na()
'''
if "def premarket_snapshot(" not in rules:
    rules = rules.rstrip() + premarket_rules + "\n"
rules_path.write_text(rules)

# -----------------------------------------------------------------------------
# API integration.
# -----------------------------------------------------------------------------
api_path = ROOT / "masterscanner_api.py"
api = api_path.read_text()
api = replace_once(
    api,
    "    RULE_VERSION,\n    SCANNER_VERSION,\n    annotate_validation,\n    bar_close_at,\n    completed_15m_confirmation,\n    filter_buy_now,\n    is_structural_candidate,\n    resample_closed_4h,\n    trade_levels,\n    timeframe_trend_confirmed,\n",
    "    RULE_VERSION,\n    SCANNER_VERSION,\n    PREMARKET_CHASE_GAP_PCT,\n    annotate_validation,\n    bar_close_at,\n    completed_15m_confirmation,\n    filter_buy_now,\n    is_structural_candidate,\n    premarket_snapshot,\n    previous_regular_close,\n    resample_closed_4h,\n    trade_levels,\n    timeframe_trend_confirmed,\n",
    "API imports",
)
api_insert_after = '''def download_confirmation_data(symbol: str, interval: str, period: str) -> pd.DataFrame:\n    """Download validation data without converting it into scanner 4h bars."""\n    df = yf.download(symbol, interval=interval, period=period, progress=False, auto_adjust=True, threads=False)\n    if isinstance(df.columns, pd.MultiIndex):\n        df.columns = [column[0] for column in df.columns]\n    return df.dropna()\n\n\n'''
api_helpers = '''def download_premarket_data(symbol: str) -> pd.DataFrame:\n    """Download 5m bars including extended hours for today's premarket snapshot."""\n    df = yf.download(symbol, interval="5m", period="2d", prepost=True, progress=False, auto_adjust=True, threads=False)\n    if isinstance(df.columns, pd.MultiIndex):\n        df.columns = [column[0] for column in df.columns]\n    return df.dropna()\n\n\ndef download_daily_close_data(symbol: str) -> pd.DataFrame:\n    """Daily bars used only to resolve the previous completed regular-session close."""\n    df = yf.download(symbol, interval="1d", period="10d", prepost=False, progress=False, auto_adjust=True, threads=False)\n    if isinstance(df.columns, pd.MultiIndex):\n        df.columns = [column[0] for column in df.columns]\n    return df.dropna()\n\n\ndef premarket_fields(symbol: str) -> dict:\n    """Best-effort premarket snapshot; feed problems never kill the scan."""\n    try:\n        prev_close = previous_regular_close(download_daily_close_data(symbol))\n        return premarket_snapshot(download_premarket_data(symbol), symbol, prev_close=prev_close)\n    except Exception:\n        return {"pm_high": None, "pm_low": None, "pm_volume": None, "pm_vwap": None,\n                "pm_last": None, "pm_gap_pct": None, "pm_range_pct": None, "pm_read": "N/A"}\n\n\nPM_EMPTY = {"pm_high": None, "pm_low": None, "pm_volume": None, "pm_vwap": None,\n            "pm_last": None, "pm_gap_pct": None, "pm_range_pct": None, "pm_read": "N/A"}\n\n\n'''
api = replace_once(api, api_insert_after, api_insert_after + api_helpers, "API premarket helpers")
old_api_scan = '''def scan_symbols(tickers, theme_map, interval="4h", period="180d"):\n    regime=get_market_regime(interval,period); market_df=download_data(MARKET_SYMBOL,interval,period); rows=[]\n    for symbol in tickers:\n        try:\n            result=classify_symbol(symbol,theme_map.get(symbol,"Watchlist"),download_data(symbol,interval,period),market_df,regime,interval)\n            if result: rows.append(result)\n        except Exception as exc:\n            rows.append({"rank_score":0,"symbol":symbol,"theme":theme_map.get(symbol,"Watchlist"),"timeframe":interval,"state":"ERROR","entry":"NO","protection":"N/A","score":0,"note":str(exc)})\n    return sorted(rows,key=lambda r:({"YES":1,"WATCH":2,"NO":3}.get(r.get("entry"),9),-int(r.get("rank_score",0)),{"BUY":1,"PULLBACK BUY":2,"EARLY BUY":3,"READY":4,"HOLD":5,"HOT":6,"NEUTRAL":7,"EXIT":8}.get(r.get("state"),99)))\n'''
new_api_scan = '''def scan_symbols(tickers, theme_map, interval="4h", period="180d"):\n    regime=get_market_regime(interval,period); market_df=download_data(MARKET_SYMBOL,interval,period); rows=[]\n    for symbol in tickers:\n        try:\n            df_sym=download_data(symbol,interval,period)\n            result=classify_symbol(symbol,theme_map.get(symbol,"Watchlist"),df_sym,market_df,regime,interval)\n            if result:\n                pm=premarket_fields(symbol)\n                result.update(pm)\n                gap=pm.get("pm_gap_pct")\n                if gap is not None and abs(gap)>=PREMARKET_CHASE_GAP_PCT:\n                    result["note"]=result.get("note","")+f" | Premarket gap {gap:+.1f}%: avoid chasing at open"\n                rows.append(result)\n        except Exception as exc:\n            rows.append({"rank_score":0,"symbol":symbol,"theme":theme_map.get(symbol,"Watchlist"),"timeframe":interval,"state":"ERROR","entry":"NO","protection":"N/A","score":0,"note":str(exc), **PM_EMPTY})\n    return sorted(rows,key=lambda r:({"YES":1,"WATCH":2,"NO":3}.get(r.get("entry"),9),-int(r.get("rank_score",0)),{"BUY":1,"PULLBACK BUY":2,"EARLY BUY":3,"READY":4,"HOLD":5,"HOT":6,"NEUTRAL":7,"EXIT":8}.get(r.get("state"),99)))\n'''
api = replace_once(api, old_api_scan, new_api_scan, "API scan integration")
api = api.replace('MasterScanner V5.2 API', 'MasterScanner V5.3 API').replace('version="5.2-api"', 'version="5.3-api"')
api_path.write_text(api)

# -----------------------------------------------------------------------------
# Both Streamlit apps share the same base and get identical premarket behavior.
# -----------------------------------------------------------------------------
for filename in ["scanner_streamlit_v5_1_morning_action.py", "scanner_streamlit_v5_mode_aware.py"]:
    path = ROOT / filename
    text = path.read_text()
    text = replace_once(
        text,
        '    RULE_VERSION, SCANNER_VERSION, annotate_validation, bar_close_at,\n    completed_15m_confirmation, is_buy_now_result, is_structural_candidate,\n    resample_closed_4h, timeframe_trend_confirmed, trade_levels,\n',
        '    RULE_VERSION, SCANNER_VERSION, PREMARKET_CHASE_GAP_PCT, annotate_validation, bar_close_at,\n    completed_15m_confirmation, is_buy_now_result, is_structural_candidate,\n    premarket_snapshot, previous_regular_close, resample_closed_4h, timeframe_trend_confirmed, trade_levels,\n',
        f"{filename} imports",
    )
    marker = '''def download_confirmation_data(symbol: str, interval: str, period: str) -> pd.DataFrame:\n    df = yf.download(symbol, interval=interval, period=period, progress=False, auto_adjust=True, threads=False)\n    if isinstance(df.columns, pd.MultiIndex):\n        df.columns = [column[0] for column in df.columns]\n    return df.dropna()\n\n\n'''
    helpers = '''@st.cache_data(ttl=120, show_spinner=False)\ndef download_premarket_data(symbol: str) -> pd.DataFrame:\n    """5m bars including extended hours for today's premarket snapshot."""\n    df = yf.download(symbol, interval="5m", period="2d", prepost=True, progress=False, auto_adjust=True, threads=False)\n    if isinstance(df.columns, pd.MultiIndex):\n        df.columns = [column[0] for column in df.columns]\n    return df.dropna()\n\n\n@st.cache_data(ttl=300, show_spinner=False)\ndef download_daily_close_data(symbol: str) -> pd.DataFrame:\n    """Daily bars used to resolve the previous completed regular-session close."""\n    df = yf.download(symbol, interval="1d", period="10d", prepost=False, progress=False, auto_adjust=True, threads=False)\n    if isinstance(df.columns, pd.MultiIndex):\n        df.columns = [column[0] for column in df.columns]\n    return df.dropna()\n\n\ndef premarket_fields(symbol: str) -> Dict:\n    """Best-effort premarket snapshot; a feed hiccup cannot kill the scan."""\n    try:\n        prev_close = previous_regular_close(download_daily_close_data(symbol))\n        return premarket_snapshot(download_premarket_data(symbol), symbol, prev_close=prev_close)\n    except Exception:\n        return {"pm_high": None, "pm_low": None, "pm_volume": None, "pm_vwap": None,\n                "pm_last": None, "pm_gap_pct": None, "pm_range_pct": None, "pm_read": "N/A"}\n\n\nPM_EMPTY = {"pm_high": np.nan, "pm_low": np.nan, "pm_volume": np.nan, "pm_vwap": np.nan,\n            "pm_last": np.nan, "pm_gap_pct": np.nan, "pm_range_pct": np.nan, "pm_read": "N/A"}\n\n\n'''
    text = replace_once(text, marker, marker + helpers, f"{filename} helpers")

    old_result = '''            if result:\n                row = result.__dict__\n                row["market_gate"] = market_regime.get("gate", "BLOCK")\n                if interval.lower() == "4h" and not df.empty:\n'''
    new_result = '''            if result:\n                row = result.__dict__\n                row["market_gate"] = market_regime.get("gate", "BLOCK")\n                pm = premarket_fields(symbol)\n                row.update(pm)\n                gap = pm.get("pm_gap_pct")\n                if gap is not None and not pd.isna(gap) and abs(gap) >= PREMARKET_CHASE_GAP_PCT:\n                    row["note"] = row.get("note", "") + f" | Premarket gap {gap:+.1f}%: avoid chasing at open"\n                if interval.lower() == "4h" and not df.empty:\n'''
    text = replace_once(text, old_result, new_result, f"{filename} row integration")

    old_no_data = '''                    "atr_pct": np.nan, "rel_vol": np.nan, "rs_qqq": np.nan, "extension_pct": np.nan,\n                    "note": "Not enough data or no Yahoo data returned",\n                })'''
    new_no_data = '''                    "atr_pct": np.nan, "rel_vol": np.nan, "rs_qqq": np.nan, "extension_pct": np.nan,\n                    "note": "Not enough data or no Yahoo data returned",\n                    **PM_EMPTY,\n                })'''
    text = replace_once(text, old_no_data, new_no_data, f"{filename} no-data PM fields")

    old_error = '''                "atr_pct": np.nan, "rel_vol": np.nan, "rs_qqq": np.nan, "extension_pct": np.nan,\n                "note": str(exc),\n            })'''
    new_error = '''                "atr_pct": np.nan, "rel_vol": np.nan, "rs_qqq": np.nan, "extension_pct": np.nan,\n                "note": str(exc),\n                **PM_EMPTY,\n            })'''
    text = replace_once(text, old_error, new_error, f"{filename} error PM fields")

    text = replace_once(
        text,
        '        "atr_pct": "ATR%", "rel_vol": "RVOL", "rs_qqq": "RS vs QQQ%", "extension_pct": "Ext%",\n        "note": "Note",\n',
        '        "atr_pct": "ATR%", "rel_vol": "RVOL", "rs_qqq": "RS vs QQQ%", "extension_pct": "Ext%",\n        "pm_gap_pct": "PM Gap%", "pm_high": "PM High", "pm_low": "PM Low", "pm_read": "PM Read",\n        "note": "Note",\n',
        f"{filename} display rename",
    )
    text = replace_once(
        text,
        '        cols = ["Symbol", "Theme", "Suggested Mode", "Personality", "Mode Setup", "Entry", "State", "Protection", "Rank Score", "Score", "Price", "Buy Zone", "Stop", "TP1", "RVOL", "RS vs QQQ%", "Ext%", "Note"]',
        '        cols = ["Symbol", "Theme", "Suggested Mode", "Personality", "Mode Setup", "Entry", "State", "Protection", "Rank Score", "Score", "Price", "PM Gap%", "PM Read", "Buy Zone", "Stop", "TP1", "RVOL", "RS vs QQQ%", "Ext%", "Note"]',
        f"{filename} compact columns",
    )
    text = replace_once(
        text,
        '        cols = ["Symbol", "Theme", "TF", "Suggested Mode", "Personality", "Mode Setup", "Entry", "State", "Protection", "Rank Score", "Agg Score", "Hybrid Score", "Cons Score", "EMA Respect%", "Score", "Price", "Buy Zone", "Stop", "TP1", "Trend", "Momentum", "Volume", "RS", "Risk", "EMA9", "EMA21", "EMA55", "EMA200", "VWAP", "Above VWAP", "ADX", "ATR%", "RVOL", "RS vs QQQ%", "Ext%", "Note"]',
        '        cols = ["Symbol", "Theme", "TF", "Suggested Mode", "Personality", "Mode Setup", "Entry", "State", "Protection", "Rank Score", "Agg Score", "Hybrid Score", "Cons Score", "EMA Respect%", "Score", "Price", "PM Gap%", "PM High", "PM Low", "PM Read", "Buy Zone", "Stop", "TP1", "Trend", "Momentum", "Volume", "RS", "Risk", "EMA9", "EMA21", "EMA55", "EMA200", "VWAP", "Above VWAP", "ADX", "ATR%", "RVOL", "RS vs QQQ%", "Ext%", "Note"]',
        f"{filename} full columns",
    )
    text = replace_once(
        text,
        '    for c in ["Price", "Stop", "TP1", "EMA9", "EMA21", "EMA55", "EMA200", "VWAP"]:',
        '    for c in ["Price", "Stop", "TP1", "EMA9", "EMA21", "EMA55", "EMA200", "VWAP", "PM High", "PM Low"]:',
        f"{filename} price formatting",
    )
    text = replace_once(
        text,
        '    for c in ["ADX", "ATR%", "RVOL", "RS vs QQQ%", "Ext%", "EMA Respect%"]:',
        '    for c in ["ADX", "ATR%", "RVOL", "RS vs QQQ%", "Ext%", "EMA Respect%", "PM Gap%"]:',
        f"{filename} percentage formatting",
    )
    text = text.replace("V5.2", "V5.3")
    path.write_text(text)

# -----------------------------------------------------------------------------
# Regression tests.
# -----------------------------------------------------------------------------
tests_path = ROOT / "tests" / "test_scanner_rules.py"
tests = tests_path.read_text()
tests = replace_once(
    tests,
    '    is_buy_now_result,\n    resample_closed_4h,\n',
    '    is_buy_now_result,\n    premarket_snapshot,\n    previous_regular_close,\n    resample_closed_4h,\n',
    "test imports",
)

new_tests = r'''


def premarket_frame() -> pd.DataFrame:
    index = pd.DatetimeIndex(
        [
            pd.Timestamp("2026-09-14 04:05", tz="America/New_York"),
            pd.Timestamp("2026-09-14 06:30", tz="America/New_York"),
            pd.Timestamp("2026-09-14 09:00", tz="America/New_York"),
            pd.Timestamp("2026-09-14 10:00", tz="America/New_York"),
        ]
    )
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0, 103.0],
            "High": [100.5, 102.5, 103.0, 104.0],
            "Low": [99.5, 100.8, 101.5, 102.5],
            "Close": [100.2, 102.0, 102.8, 103.5],
            "Volume": [1000, 2000, 1500, 5000],
        },
        index=index,
    )


class PremarketSnapshotTests(unittest.TestCase):
    def test_crypto_has_no_premarket(self):
        snap = premarket_snapshot(premarket_frame(), "BTC-USD", prev_close=100.0)
        self.assertEqual(snap["pm_read"], "N/A")
        self.assertIsNone(snap["pm_high"])

    def test_empty_frame_is_na(self):
        snap = premarket_snapshot(pd.DataFrame(), "AAPL", prev_close=100.0)
        self.assertEqual(snap["pm_read"], "N/A")

    def test_snapshot_uses_only_premarket_bars(self):
        now = pd.Timestamp("2026-09-14 09:15", tz="America/New_York")
        snap = premarket_snapshot(premarket_frame(), "AAPL", prev_close=100.0, now=now)
        self.assertEqual(snap["pm_high"], 103.0)
        self.assertEqual(snap["pm_low"], 99.5)
        self.assertEqual(snap["pm_volume"], 4500)
        self.assertEqual(snap["pm_last"], 102.8)
        self.assertEqual(snap["pm_gap_pct"], 2.8)
        self.assertEqual(snap["pm_read"], "BULLISH")

    def test_bearish_read_on_gap_down_near_premarket_low(self):
        frame = premarket_frame()
        frame.loc[frame.index[:3], ["Open", "High", "Low", "Close"]] = [
            [99.5, 100.0, 98.5, 99.0],
            [98.8, 99.0, 97.5, 98.0],
            [98.0, 98.2, 97.0, 97.5],
        ]
        now = pd.Timestamp("2026-09-14 09:15", tz="America/New_York")
        snap = premarket_snapshot(frame, "AAPL", prev_close=100.0, now=now)
        self.assertEqual(snap["pm_gap_pct"], -2.5)
        self.assertEqual(snap["pm_read"], "BEARISH")

    def test_neutral_on_small_gap(self):
        now = pd.Timestamp("2026-09-14 09:15", tz="America/New_York")
        snap = premarket_snapshot(premarket_frame(), "AAPL", prev_close=102.5, now=now)
        self.assertAlmostEqual(snap["pm_gap_pct"], 0.29, places=1)
        self.assertEqual(snap["pm_read"], "NEUTRAL")

    def test_previous_regular_close_excludes_todays_in_progress_bar(self):
        daily = pd.DataFrame(
            {"Close": [98.0, 100.0, 105.0]},
            index=pd.DatetimeIndex([
                pd.Timestamp("2026-09-10"),
                pd.Timestamp("2026-09-11"),
                pd.Timestamp("2026-09-14"),
            ]),
        )
        now = pd.Timestamp("2026-09-14 13:30", tz="America/New_York")
        self.assertEqual(previous_regular_close(daily, now=now), 100.0)
'''
needle = '\n\nif __name__ == "__main__":\n    unittest.main()\n'
if "class PremarketSnapshotTests" not in tests:
    tests = replace_once(tests, needle, new_tests + needle, "append premarket tests")
tests_path.write_text(tests)

print("Premarket patch applied to MasterScanner V5.3")
