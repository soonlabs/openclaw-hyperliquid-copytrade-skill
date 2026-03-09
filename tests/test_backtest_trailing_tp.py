import os
import sys
import unittest


SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import backtest_trailing_tp  # noqa: E402


class TestBacktestTrailingTP(unittest.TestCase):
    def test_long_trailing_trigger_path(self):
        result = backtest_trailing_tp.simulate_price_path(
            side="buy",
            entry=100,
            prices=[102, 106, 110, 108],
            auto_tp_pct=6,
            auto_sl_pct=3,
            trailing_tp_enable=True,
            trailing_tp_callback_pct=1,
        )
        self.assertIsNotNone(result["triggered"])
        self.assertIn("Trailing TP retrace", result["triggered"]["trigger"])

    def test_short_trailing_trigger_path(self):
        result = backtest_trailing_tp.simulate_price_path(
            side="sell",
            entry=100,
            prices=[98, 95, 90, 92],
            auto_tp_pct=6,
            auto_sl_pct=3,
            trailing_tp_enable=True,
            trailing_tp_callback_pct=1,
        )
        self.assertIsNotNone(result["triggered"])
        self.assertIn("Trailing TP retrace", result["triggered"]["trigger"])

    def test_no_trigger_when_only_uptrend_long(self):
        result = backtest_trailing_tp.simulate_price_path(
            side="buy",
            entry=100,
            prices=[101, 103, 106, 109],
            auto_tp_pct=6,
            auto_sl_pct=3,
            trailing_tp_enable=True,
            trailing_tp_callback_pct=1,
        )
        self.assertIsNone(result["triggered"])

    def test_sl_trigger(self):
        result = backtest_trailing_tp.simulate_price_path(
            side="buy",
            entry=100,
            prices=[99, 98, 96],
            auto_tp_pct=6,
            auto_sl_pct=3,
            trailing_tp_enable=True,
            trailing_tp_callback_pct=1,
        )
        self.assertIsNotNone(result["triggered"])
        self.assertIn("SL hit", result["triggered"]["trigger"])


if __name__ == "__main__":
    unittest.main()
