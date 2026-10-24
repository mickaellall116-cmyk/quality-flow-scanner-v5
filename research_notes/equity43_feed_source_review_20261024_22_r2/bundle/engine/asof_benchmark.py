"""QF-EQUITY-PIT-INTEGRITY-20261023-09 — research-only benchmark construction.

B1 (ChatGPT adjudication of -08, Issue #1 comment 6373962624): the -08 driver
(run_diagnostic.py lines 310-320, mirroring load_benchmarks' handling) built
SPY daily bars from the full day and indexed each at ET MIDNIGHT of the day it
describes. pine_signal_quality.bench_ret selects the last daily bar with
index <= t, so for a 4H signal at 09:30 or 13:30 ET the SAME DAY's bar was
selected and its Close — the 16:00 close, hours in the future — entered the
RS ranking feature. The helper's 'no lookahead' docstring was wrong for
midnight-stamped daily bars.

FROZEN AS-OF POLICY (this fork, integrity-only, decided from time semantics):
a daily benchmark bar becomes visible only when its session COMPLETES.
Daily bars are stamped at 16:00 ET on the session date (the regular-session
close). Early-close sessions actually complete at 13:00 ET but are stamped
16:00 ET uniformly — conservative (later, never earlier), so the policy can
only delay, never leak. With completion-stamped bars, the UNCHANGED frozen
bench_ret selection rule (last index <= t) is causally correct: at 09:30 or
13:30 ET on day D it selects day D-1's completed session. bench_ret itself is
NOT modified by this fork.

build_daily_midnight below reproduces the -08 construction verbatim (same
grouping, same midnight stamp) so the fail-before side of the fixtures runs
the exact original semantics. No strategy filter, threshold, or parameter is
changed anywhere in this fork.
"""
import pandas as pd

ET = "America/New_York"
SESSION_CLOSE = pd.Timedelta(hours=16)  # 16:00 ET on the session date


def _aggregate(intraday):
    """Group an admitted intraday (1h) frame into daily OHLCV dicts by ET date.
    Identical aggregation to run_diagnostic.py lines 312-316."""
    daily = {}
    for d, grp in intraday.groupby(intraday.index.strftime("%Y-%m-%d")):
        daily[d] = {"Open": grp["Open"].iloc[0], "High": grp["High"].max(),
                    "Low": grp["Low"].min(), "Close": grp["Close"].iloc[-1],
                    "Volume": grp["Volume"].sum()}
    return daily


def build_daily_midnight(intraday):
    """ORIGINAL -08 construction (fail-before): daily bars indexed at ET
    midnight of the session date, converted to UTC."""
    daily = _aggregate(intraday)
    didx = pd.DatetimeIndex([pd.Timestamp(d) for d in daily]).tz_localize(ET).tz_convert("UTC")
    return pd.DataFrame([daily[d] for d in daily], index=didx).sort_index()


def build_daily_asof(intraday):
    """FORK construction (pass-after): identical aggregation; each daily bar
    stamped at its session COMPLETION (16:00 ET), converted to UTC."""
    daily = _aggregate(intraday)
    didx = (pd.DatetimeIndex([pd.Timestamp(d) for d in daily]) + SESSION_CLOSE
            ).tz_localize(ET).tz_convert("UTC")
    return pd.DataFrame([daily[d] for d in daily], index=didx).sort_index()
