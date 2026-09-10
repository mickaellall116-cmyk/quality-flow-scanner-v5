import unittest

import pandas as pd

from scanner_rules import (
    RULE_VERSION,
    closed_higher_timeframe,
    filter_buy_now,
    is_buy_now_result,
    resample_closed_4h,
    validation_reasons,
)


def hourly_frame(index: pd.DatetimeIndex) -> pd.DataFrame:
    values = list(range(1, len(index) + 1))
    return pd.DataFrame(
        {
            "Open": values,
            "High": [value + 1 for value in values],
            "Low": [value - 1 for value in values],
            "Close": values,
            "Volume": [100] * len(values),
        },
        index=index,
    )


class ClosedFourHourBarsTests(unittest.TestCase):
    def test_stock_bar_is_aligned_to_0930_and_excludes_active_bar(self):
        index = pd.date_range(
            "2026-08-27 09:30",
            periods=7,
            freq="1h",
            tz="America/New_York",
        )
        bars = resample_closed_4h(
            hourly_frame(index),
            "MSFT",
            now=pd.Timestamp("2026-08-27 14:00", tz="America/New_York"),
        )
        self.assertEqual(list(bars.index.hour), [9])
        self.assertEqual(list(bars.index.minute), [30])

    def test_stock_final_session_bar_closes_at_1600(self):
        index = pd.date_range(
            "2026-08-27 09:30",
            periods=7,
            freq="1h",
            tz="America/New_York",
        )
        bars = resample_closed_4h(
            hourly_frame(index),
            "MSFT",
            now=pd.Timestamp("2026-08-27 16:01", tz="America/New_York"),
        )
        self.assertEqual([(stamp.hour, stamp.minute) for stamp in bars.index], [(9, 30), (13, 30)])
        self.assertEqual(bars.attrs["last_bar_close_at"], "2026-08-27T16:00:00-04:00")

    def test_stock_bars_include_regular_session_vwap(self):
        index = pd.date_range("2026-08-27 09:30", periods=7, freq="1h", tz="America/New_York")
        bars = resample_closed_4h(
            hourly_frame(index), "MSFT", now=pd.Timestamp("2026-08-27 16:01", tz="America/New_York")
        )
        self.assertIn("SessionVWAP", bars.columns)
        self.assertGreater(float(bars["SessionVWAP"].iloc[-1]), 0)

    def test_crypto_uses_midnight_four_hour_boundaries(self):
        index = pd.date_range("2026-08-27 00:00", periods=6, freq="1h", tz="UTC")
        bars = resample_closed_4h(
            hourly_frame(index),
            "BTC-USD",
            now=pd.Timestamp("2026-08-27 05:00", tz="UTC"),
        )
        self.assertEqual(list(bars.index.hour), [0])


class HigherTimeframeTests(unittest.TestCase):
    def test_active_daily_bar_is_removed_before_close(self):
        frame = hourly_frame(pd.date_range("2026-08-31", periods=3, freq="1d"))
        closed = closed_higher_timeframe(frame, "1d", pd.Timestamp("2026-09-02 13:00", tz="America/New_York"))
        self.assertEqual(len(closed), 2)

    def test_daily_bar_is_kept_after_close(self):
        frame = hourly_frame(pd.date_range("2026-08-31", periods=3, freq="1d"))
        closed = closed_higher_timeframe(frame, "1d", pd.Timestamp("2026-09-02 16:01", tz="America/New_York"))
        self.assertEqual(len(closed), 3)


class BuyNowRulesTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "symbol": "TEST",
            "entry": "YES",
            "protection": "SAFE",
            "state": "PULLBACK BUY",
            "above_vwap": True,
            "price": 100.0,
            "buy_zone": "99.00-101.00",
            "stop": 98.0,
            "tp1": 104.0,
            "rank_score": 120,
            "market_gate": "CONFIRM",
            "adx": 25.0,
            "rel_vol": 1.2,
            "mtf_confirmed": True,
            "confirmation_15m": True,
        }

    def test_accepts_exact_buy_now_contract(self):
        self.assertTrue(is_buy_now_result(self.row))

    def test_rejects_price_above_zone(self):
        row = {**self.row, "price": 101.01}
        self.assertFalse(is_buy_now_result(row))

    def test_rejects_below_vwap(self):
        row = {**self.row, "above_vwap": False}
        self.assertFalse(is_buy_now_result(row))

    def test_rejects_weak_volume_even_when_old_contract_passes(self):
        row = {**self.row, "rel_vol": 0.5}
        self.assertFalse(is_buy_now_result(row))
        self.assertIn("relative volume below 0.80x", validation_reasons(row))

    def test_rejects_market_block_and_missing_15m_confirmation(self):
        row = {**self.row, "market_gate": "BLOCK", "confirmation_15m": False}
        reasons = validation_reasons(row)
        self.assertIn("market gate is BLOCK", reasons)
        self.assertIn("completed 15-minute confirmation missing", reasons)

    def test_rule_version_is_exposed(self):
        self.assertEqual(RULE_VERSION, "2026-09-10-v2")

    def test_filter_ranks_and_limits(self):
        lower = {**self.row, "symbol": "LOW", "rank_score": 90}
        higher = {**self.row, "symbol": "HIGH", "rank_score": 130}
        result = filter_buy_now([lower, higher], limit=1)
        self.assertEqual([row["symbol"] for row in result], ["HIGH"])


if __name__ == "__main__":
    unittest.main()
