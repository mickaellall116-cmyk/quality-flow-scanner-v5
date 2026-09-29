#!/usr/bin/env python3
"""Dashboard `entryYes` mirror for the V3.7 signal watcher — OBSERVABILITY ONLY.

Mirrors the TradingView dashboard's ENTRY verdict from
``Quality-Flow-System-V3.7.pine`` so each logged raw ``buySignal`` can be
tagged with the dashboard's plain-English answer ("would the dashboard have
said ENTRY YES on that bar?"). Used for ping filtering and display only.

Pine definition (V3.7, defaults — do not "tune" these):

    entryContextOK  = dailyCode >= 3 and h4Code >= 2 and structureDir >= 0 and trendBull
    entryLocationOK = inBuyZone or inBullFvgSupport or bullSweep or pullbackBuy
    entryRiskOK     = not hotState and not exitSignal and not chop
    entryYes        = entryContextOK and entryLocationOK and entryRiskOK

Hard rules:
  * This module NEVER changes what counts as a signal. The signal decision
    always comes from ``pine_backtest.pine_buy_signal`` via the same import
    path ``pine_live/decompose.py`` uses.
  * Where the identical quantity already exists in Python it is REUSED:
    trendBull / hotState / volumeOK -> ``pine_live.decompose``;
    ema / atr / adx               -> ``pine_backtest`` (same Wilder/EMA math).
    Dashboard-only geometry (structure pivots, sweeps, FVG, buy zone, MTF
    state code) has no Python equivalent and is ported here 1:1 from the
    Pine defaults, for display only.
  * No jargon may leak to the user: plain-English reasons never mention
    internal names (entryLocationOK, bullSweep, ...).

Notes on fidelity (documented, not hidden):
  * ``exitSignal`` requires a live strategy position. The watcher evaluates a
    *new* signal, i.e. Pine's ``strategy.position_size == 0`` case, so
    ``exitSignal`` is False here — exactly as the dashboard computes it when
    flat. (This is the known position-state gap: the log mirrors the
    dashboard-as-if-flat, it does not track Mike's real positions.)
  * Structure pivots use centered pivots on full history; the live chart
    confirms pivots up to 3 bars late, so ``structureDir`` can differ by a few
    bars vs. the chart replay. Only the coarse gate (``>= 0``) is used.
  * ``dailyCode`` is computed from 4H bars resampled to daily (no extra
    download); coarse gate (``>= 3``) only.
"""

from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Plain-English reason strings. No jargon, no internal field names — these are
# what Mike reads in the app and in the ping.
# ---------------------------------------------------------------------------

WHY_YES_LOCATION = {
    # priority order: most specific first
    "sweep": "a spot where sellers got trapped — price dipped under the recent "
             "lows and buyers snapped it right back",
    "fvg": "bullish support — an old price gap is acting as a floor underneath",
    "zone": "the buy zone, right near its short-term average price",
    "pullback": "an orderly pullback — price eased back toward support while "
                "momentum stayed intact",
}

WHY_NO_HOT = ("No — price is overextended, stretched too far above its "
              "short-term average. Buying here usually means chasing a spike.")
WHY_NO_TREND = ("No — the broader trend isn't bullish, so this would be "
                "fighting the prevailing direction.")
WHY_NO_LOCATION = ("No — the trend looks fine but price isn't at a good spot "
                   "to enter. Better to wait for a pullback to support.")
WHY_NO_CHOP_ADX_TMPL = ("No — choppy market: trend strength (ADX {adx:.1f}) is below "
                       "the 20 needed for a clean entry. Signals in chop tend to "
                       "whipsaw.")
WHY_NO_CHOP_VOL = ("No — volatility is too compressed right now (recent price "
                   "ranges are tiny compared to normal). Moves that start from "
                   "this kind of squeeze often fail.")
WHY_NO_OTHER = "No — not all entry conditions line up right now."

# ---------------------------------------------------------------------------
# Ping alert template (exact format the cron worker uses for ENTRY YES pings).
# ---------------------------------------------------------------------------
# 🟢 BUY — {SYMBOL} @ ${entry} ({Day} {time} ET)
# Why: {plain-English reason}
# Stop ${stop} · Target ${tp1}
# You own: {qty} @ ${avg}          <- omit this line when there is no position


def _mtf_state_codes(df: pd.DataFrame) -> pd.Series:
    """Port of Pine f_stateCode(): 5=HOT, 4=BUY/HOLD, 3=EARLY, 2=READY,
    1=NEUTRAL, 0=BEAR. df must carry e9/e21/e55/e200/atr/atr_base/atr_ratio/adx
    (exactly what pine_backtest.add_pine_indicators produces)."""
    c = df["Close"]
    e9, e21, e55, e200 = df["e9"], df["e21"], df["e55"], df["e200"]
    a, ab, ar, ax = df["atr"], df["atr_base"], df["atr_ratio"], df["adx"]
    t_bull = (e21 > e55) & (c > e200)
    t_bear = (e21 < e55) & (c < e200)
    hot = c > e9 + a * 1.5                      # hotATR default 1.5
    ready = (c < e21) & (c > e55) & (e21 > e55) & (ar > 0.85)
    early = (e9 > e21) & (c > e55) & (ar > 0.85)
    buy = (c > e21) & (e21 > e55) & (c > e200) & (ax > 18)
    # Pine ternary chain: tBear ? 0 : hot and tBull ? 5 : buy ? 4 : early ? 3
    #                      : ready ? 2 : tBull ? 4 : 1
    conds = [t_bear, hot & t_bull, buy, early, ready, t_bull]
    return pd.Series(np.select(conds, [0, 5, 4, 3, 2, 4], default=1),
                     index=df.index).astype(int)


def _resample_daily(df4h: pd.DataFrame) -> pd.DataFrame:
    """Collapse 4H bars to daily OHLCV by ET calendar date (for dailyCode)."""
    from pine_backtest import add_pine_indicators  # deferred: keep import cheap

    idx = df4h.index
    if idx.tz is None:
        days = idx.normalize()
    else:
        days = idx.tz_convert("America/New_York").normalize()
    g = df4h.assign(_day=days).groupby("_day")
    d = pd.DataFrame({
        "Open": g["Open"].first(),
        "High": g["High"].max(),
        "Low": g["Low"].min(),
        "Close": g["Close"].last(),
        "Volume": g["Volume"].sum(),
    })
    d.index.name = None
    return add_pine_indicators(d)


def _structure_dir(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                   pivot_len: int = 3) -> np.ndarray:
    """Port of the Pine structure state machine (pivotLen=3). Returns the
    structureDir value at every bar."""
    n = len(close)
    piv_h = np.full(n, np.nan)
    piv_l = np.full(n, np.nan)
    w = 2 * pivot_len + 1
    for j in range(pivot_len, n - pivot_len):
        win_h = high[j - pivot_len:j + pivot_len + 1]
        if high[j] >= win_h.max():
            piv_h[j] = high[j]
        win_l = low[j - pivot_len:j + pivot_len + 1]
        if low[j] <= win_l.min():
            piv_l[j] = low[j]
    last_sh, last_sl = np.nan, np.nan
    sdir = 0
    out = np.zeros(n, dtype=int)
    for j in range(n):
        if not np.isnan(piv_h[j]):
            last_sh = piv_h[j]
        if not np.isnan(piv_l[j]):
            last_sl = piv_l[j]
        if j > 0:
            bos_up = (not np.isnan(last_sh) and close[j] > last_sh
                      and close[j - 1] <= last_sh)
            bos_dn = (not np.isnan(last_sl) and close[j] < last_sl
                      and close[j - 1] >= last_sl)
            if bos_up:
                sdir = 1
            if bos_dn:
                sdir = -1
        out[j] = sdir
    return out


def _location_state(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                    e21: np.ndarray, atr: np.ndarray):
    """Port of Pine sweep / FVG / buy-zone geometry (defaults:
    sweepLookback=20, buyZoneAtrWidth=0.35, nearZoneATR=0.50). Returns dicts of
    boolean arrays keyed 'sweep', 'fvg', 'zone', 'near'."""
    n = len(close)
    sweep = np.zeros(n, bool)
    in_fvg = np.zeros(n, bool)
    in_zone = np.zeros(n, bool)
    near_zone = np.zeros(n, bool)
    last_fvg_low, last_fvg_high = np.nan, np.nan
    for j in range(n):
        # Bullish FVG forms when low gaps above the high two bars back.
        if j >= 2 and low[j] > high[j - 2]:
            last_fvg_low = high[j - 2]
            last_fvg_high = low[j]
        # Liquidity sweep: dip under the prior 20-bar low, close back above.
        if j >= 20:
            ref = low[j - 20:j].min()
            sweep[j] = bool(low[j] < ref and close[j] > ref)
        # Buy zone around EMA21, widened to include a nearby bull FVG.
        ez_low = e21[j] - atr[j] * 0.35
        ez_high = e21[j] + atr[j] * 0.35
        use_fvg = (not np.isnan(last_fvg_low)
                   and abs(close[j] - last_fvg_high) <= atr[j] * 3
                   and last_fvg_high <= close[j] * 1.08)
        zl = min(ez_low, last_fvg_low) if use_fvg else ez_low
        zh = max(ez_high, last_fvg_high) if use_fvg else ez_high
        in_zone[j] = bool(zl <= close[j] <= zh)
        near_zone[j] = bool(abs(close[j] - zh) <= atr[j] * 0.5
                            or abs(close[j] - zl) <= atr[j] * 0.5
                            or in_zone[j])
        if not np.isnan(last_fvg_low):
            in_fvg[j] = bool(low[j] <= last_fvg_high
                             and close[j] >= last_fvg_low)
    return {"sweep": sweep, "fvg": in_fvg, "zone": in_zone, "near": near_zone}


class EntryAssessor:
    """Precompute per-symbol dashboard state once, then assess signal bars."""

    def __init__(self, df4h: pd.DataFrame):
        close = df4h["Close"].to_numpy()
        high = df4h["High"].to_numpy()
        low = df4h["Low"].to_numpy()
        self.h4_code = _mtf_state_codes(df4h).to_numpy()
        daily = _resample_daily(df4h)
        self._daily_code = _mtf_state_codes(daily)
        self._daily_dates = daily.index
        self.sdir = _structure_dir(high, low, close)
        self.loc = _location_state(high, low, close,
                                   df4h["e21"].to_numpy(),
                                   df4h["atr"].to_numpy())
        # ET calendar date of each 4H bar, for the dailyCode lookup.
        idx = df4h.index
        if idx.tz is None:
            self._bar_days = idx.normalize()
        else:
            self._bar_days = idx.tz_convert("America/New_York").normalize()

    def daily_code_at(self, i: int) -> int:
        day = self._bar_days[i]
        pos = self._daily_dates.searchsorted(day, side="right") - 1
        if pos < 0:
            return 1
        v = self._daily_code.iloc[pos]
        return int(v) if not pd.isna(v) else 1

    def assess(self, df4h: pd.DataFrame, i: int, d: dict) -> dict:
        """Dashboard ENTRY verdict for the signal bar i.

        d is the pine_live.decompose dict for the same bar (reused for
        trendBull / hotState / volumeOK — identical definitions).
        Returns entry_yes, entry_why (plain English), and components.
        """
        r = df4h.iloc[i]
        close = float(r["Close"])
        adx = float(r["adx"])
        atr_ratio = float(r["atr_ratio"])
        e21 = float(r["e21"])

        trend_bull = bool(d["trend_bull"])      # == Pine trendBull
        hot = bool(d["hot"])                   # == Pine hotState
        volume_ok = bool(d["volume_ok"])       # == Pine volumeOK (filter on)
        chop_adx = adx < 18
        chop_vol = atr_ratio < 0.75
        chop = bool(chop_adx or chop_vol)       # == Pine chop
        # exitSignal needs a live position; a *new* signal means flat, so False
        # — exactly what the dashboard computes when strategy.position_size==0.
        exit_signal = False

        h4_code = int(self.h4_code[i])
        daily_code = self.daily_code_at(i)
        sdir = int(self.sdir[i])

        entry_context_ok = bool(daily_code >= 3 and h4_code >= 2
                                and sdir >= 0 and trend_bull)

        loc = self.loc
        in_zone = bool(loc["zone"][i])
        in_fvg = bool(loc["fvg"][i])
        sweep = bool(loc["sweep"][i])
        pullback = bool(trend_bull and loc["near"][i] and close >= e21
                        and adx > 18 and volume_ok and not hot)
        entry_location_ok = bool(in_zone or in_fvg or sweep or pullback)

        entry_risk_ok = bool(not hot and not exit_signal and not chop)
        entry_yes = bool(entry_context_ok and entry_location_ok
                         and entry_risk_ok)

        if entry_yes:
            for key in ("sweep", "fvg", "zone", "pullback"):
                hit = {"sweep": sweep, "fvg": in_fvg,
                       "zone": in_zone, "pullback": pullback}[key]
                if hit:
                    entry_why = (f"Yes — uptrend, price holding at "
                                 f"{WHY_YES_LOCATION[key]}.")
                    break
        elif hot:
            entry_why = WHY_NO_HOT
        elif not trend_bull:
            entry_why = WHY_NO_TREND
        elif not entry_location_ok:
            entry_why = WHY_NO_LOCATION
        elif chop:
            entry_why = (WHY_NO_CHOP_ADX_TMPL.format(adx=adx) if chop_adx
                         else WHY_NO_CHOP_VOL)
        else:
            entry_why = WHY_NO_OTHER

        return {
            "entry_yes": entry_yes,
            "entry_why": entry_why,
            "components": {
                "daily_code": daily_code,
                "h4_code": h4_code,
                "structure_dir": sdir,
                "trend_bull": trend_bull,
                "in_buy_zone": in_zone,
                "in_bull_fvg_support": in_fvg,
                "bull_sweep": sweep,
                "pullback": pullback,
                "hot": hot,
                "chop": chop,
                "adx": round(adx, 1),
            },
        }


# ---------------------------------------------------------------------------
# Positions + alert rendering
# ---------------------------------------------------------------------------

def load_positions(path: str | None = None) -> dict:
    """Mike's positions for the 'You own:' alert line.

    From memory — flagged in the file itself as NEEDING HIS VERIFICATION.
    Returns {SYMBOL: {"qty": float, "avg": float, "note": str}}.
    """
    import yaml

    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "positions.yaml")
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return {}
    out = {}
    for sym, p in (data.get("positions") or {}).items():
        try:
            out[str(sym).upper()] = {
                "qty": float(p["qty"]),
                "avg": float(p["avg"]),
                "note": str(p.get("note") or ""),
            }
        except Exception:
            continue
    return out


def _et_stamp(iso_ts: str) -> str:
    dt = datetime.fromisoformat(iso_ts)
    et = dt.astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
    # "Fri 1:30 PM ET" — strip leading zero from the hour.
    return et.strftime("%a %-I:%M %p ET")


def format_alert(event: dict, positions: dict | None = None) -> str:
    """Render the exact ping text for an ENTRY YES signal. Tight, no jargon::

        🟢 BUY — {SYMBOL} @ ${entry} ({Day} {time} ET)
        Why: {plain-English reason}
        Stop ${stop} · Target ${tp1}
        You own: {qty} @ ${avg}
    """
    positions = positions or {}
    sym = str(event["symbol"]).upper()
    lines = [
        f"🟢 BUY — {sym} @ ${event['entry_px']:.2f} "
        f"({_et_stamp(event['signal_bar_close'])})",
        f"Why: {event['entry_why']}",
        f"Stop ${event['stop_px']:.2f} · Target ${event['tp1_px']:.2f}",
    ]
    pos = positions.get(sym)
    if pos:
        lines.append(f"You own: {pos['qty']:g} @ ${pos['avg']:.2f}")
    return "\n".join(lines)
