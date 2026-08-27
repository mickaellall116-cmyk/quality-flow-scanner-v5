import unittest

import pandas as pd

from scanner_rules import filter_buy_now, is_buy_now_result, resample_closed_4h


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

    def test_crypto_uses_midnight_four_hour_boundaries(self):
        index = pd.date_range("2026-08-27 00:00", periods=6, freq="1h", tz="UTC")
        bars = resample_closed_4h(
            hourly_frame(index),
            "BTC-USD",
            now=pd.Timestamp("2026-08-27 05:00", tz="UTC"),
        )
        self.assertEqual(list(bars.index.hour), [0])


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
            "rank_score": 120,
        }

    def test_accepts_exact_buy_now_contract(self):
        self.assertTrue(is_buy_now_result(self.row))

    def test_rejects_price_above_zone(self):
        row = {**self.row, "price": 101.01}
        self.assertFalse(is_buy_now_result(row))

    def test_rejects_below_vwap(self):
        row = {**self.row, "above_vwap": False}
        self.assertFalse(is_buy_now_result(row))

    def test_filter_ranks_and_limits(self):
        lower = {**self.row, "symbol": "LOW", "rank_score": 90}
        higher = {**self.row, "symbol": "HIGH", "rank_score": 130}
        result = filter_buy_now([lower, higher], limit=1)
        self.assertEqual([row["symbol"] for row in result], ["HIGH"])


if __name__ == "__main__":
    unittest.main()
