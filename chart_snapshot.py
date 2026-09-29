#!/usr/bin/env python3
"""Render a signal chart snapshot (candlesticks + entry/stop/TP1 lines).

Shared by the rotation watcher and the V3.7 signal-log watcher.
Observability only: never touches strategy logic. Fail-soft — any error
returns None and the alert flow continues without a chart.
"""
import os
import traceback
from datetime import datetime

REPO = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(REPO, "signal_log", "charts")
LOOKBACK_BARS = 120


def _ensure_dir():
    try:
        os.makedirs(CHART_DIR, exist_ok=True)
    except Exception:
        pass


def _download(symbol):
    from masterscanner_api import download_data

    return download_data(symbol, "4h", "180d")


def render_signal_chart(symbol, entry, stop, tp1, signal_time_iso,
                        df=None, outdir=None):
    """Return PNG path or None. df optional (4H OHLC with Open/High/Low/Close)."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle

        if df is None or getattr(df, "empty", True):
            df = _download(symbol)
        if df is None or df.empty or len(df) < 10:
            return None

        outdir = outdir or CHART_DIR
        _ensure_dir()

        data = df.tail(LOOKBACK_BARS)
        opens = data["Open"].to_numpy()
        highs = data["High"].to_numpy()
        lows = data["Low"].to_numpy()
        closes = data["Close"].to_numpy()
        n = len(data)

        # Locate the signal bar inside the window for the marker.
        sig_idx = n - 1
        try:
            if signal_time_iso:
                sig_ts = str(signal_time_iso)[:16]
                for k, ts in enumerate(data.index):
                    if str(ts)[:16] == sig_ts:
                        sig_idx = k
                        break
        except Exception:
            pass

        fig, ax = plt.subplots(figsize=(10, 5.5), dpi=100)
        fig.patch.set_facecolor("#0e1117")
        ax.set_facecolor("#0e1117")

        for i in range(n):
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            color = "#26a69a" if c >= o else "#ef5350"
            ax.plot([i, i], [l, h], color=color, linewidth=1)
            ax.add_patch(Rectangle((i - 0.35, min(o, c)), 0.7, abs(c - o) or 1e-9,
                                   facecolor=color, edgecolor=color))

        lo_pad = min(lows.min(), stop) * 0.995
        hi_pad = max(highs.max(), tp1) * 1.005
        ax.set_ylim(lo_pad, hi_pad)

        ax.axhline(entry, color="#4da3ff", linestyle="--", linewidth=1.2,
                   label=f"Entry {entry:.2f}")
        ax.axhline(stop, color="#ef5350", linestyle="--", linewidth=1.2,
                   label=f"Stop {stop:.2f}")
        ax.axhline(tp1, color="#26a69a", linestyle="--", linewidth=1.2,
                   label=f"TP1 {tp1:.2f}")
        ax.axvline(sig_idx, color="#888888", linestyle=":", linewidth=1,
                   label="Signal bar")

        ax.set_title(f"{symbol} 4H — signal {str(signal_time_iso)[:16]}",
                     color="white", fontsize=12)
        ax.tick_params(colors="#aaaaaa")
        for spine in ax.spines.values():
            spine.set_color("#333333")
        leg = ax.legend(facecolor="#1a1d24", edgecolor="#333333", fontsize=9)
        for text in leg.get_texts():
            text.set_color("white")
        fig.tight_layout()

        safe_ts = "".join(c if c.isalnum() else "_" for c in str(signal_time_iso)[:16])
        path = os.path.join(outdir, f"{symbol}_{safe_ts}.png")
        fig.savefig(path, facecolor=fig.get_facecolor())
        plt.close(fig)
        return path
    except Exception:
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import sys

    # smoke test: python3 chart_snapshot.py IREN
    sym = sys.argv[1] if len(sys.argv) > 1 else "IREN"
    df = _download(sym)
    c = float(df["Close"].iloc[-1])
    p = render_signal_chart(sym, c, c * 0.96, c * 1.09,
                            datetime.now().strftime("%Y-%m-%dT%H:%M"), df=df)
    print(p)
