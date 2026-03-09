import os
import sys
import unittest


SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import runner  # noqa: E402


class TestTrailingTpLogic(unittest.TestCase):
    def test_calc_pnl_pct_long_and_short(self):
        self.assertAlmostEqual(runner._calc_pnl_pct(100.0, 105.0, "buy"), 5.0)
        self.assertAlmostEqual(runner._calc_pnl_pct(100.0, 95.0, "sell"), 5.0)

    def test_normalize_copied_position_backfills_watermarks(self):
        copied = {"side": "buy", "entry_price": 100.0, "notional": 50.0}
        normalized = runner._normalize_copied_position(copied)
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["high_watermark_price"], 100.0)
        self.assertEqual(normalized["low_watermark_price"], 100.0)
        self.assertEqual(normalized["watermark_price"], 100.0)
        self.assertAlmostEqual(normalized["watermark_pnl_pct"], 0.0)

    def test_trailing_tp_triggers_after_retrace_for_long(self):
        copied = {
            "side": "buy",
            "entry_price": 100.0,
            "high_watermark_price": 110.0,
            "low_watermark_price": 100.0,
            "watermark_pnl_pct": 10.0,
        }
        trigger, note = runner._evaluate_tp_sl_trigger(
            copied=copied,
            price=108.0,
            auto_tp_pct=6.0,
            auto_sl_pct=3.0,
            trailing_tp_enable=True,
            trailing_tp_callback_pct=1.0,
        )
        self.assertIn("Trailing TP retrace", trigger or "")
        self.assertIn("peak=10.00%", note)
        self.assertIn("retrace=2.00%", note)

    def test_trailing_tp_not_triggered_before_tp_threshold(self):
        copied = {
            "side": "buy",
            "entry_price": 100.0,
            "high_watermark_price": 104.0,
            "low_watermark_price": 100.0,
            "watermark_pnl_pct": 4.0,
        }
        trigger, _ = runner._evaluate_tp_sl_trigger(
            copied=copied,
            price=102.0,
            auto_tp_pct=6.0,
            auto_sl_pct=3.0,
            trailing_tp_enable=True,
            trailing_tp_callback_pct=1.0,
        )
        self.assertIsNone(trigger)

    def test_trailing_tp_triggers_after_retrace_for_short(self):
        copied = {
            "side": "sell",
            "entry_price": 100.0,
            "high_watermark_price": 100.0,
            "low_watermark_price": 90.0,
            "watermark_pnl_pct": 10.0,
        }
        trigger, note = runner._evaluate_tp_sl_trigger(
            copied=copied,
            price=92.0,
            auto_tp_pct=6.0,
            auto_sl_pct=3.0,
            trailing_tp_enable=True,
            trailing_tp_callback_pct=1.0,
        )
        self.assertIn("Trailing TP retrace", trigger or "")
        self.assertIn("peak=10.00%", note)
        self.assertIn("retrace=2.00%", note)

    def test_trailing_tp_short_tracks_new_low(self):
        copied = {
            "side": "sell",
            "entry_price": 100.0,
            "high_watermark_price": 100.0,
            "low_watermark_price": 95.0,
            "watermark_pnl_pct": 5.0,
        }
        trigger, note = runner._evaluate_tp_sl_trigger(
            copied=copied,
            price=90.0,
            auto_tp_pct=6.0,
            auto_sl_pct=3.0,
            trailing_tp_enable=True,
            trailing_tp_callback_pct=1.0,
        )
        self.assertIsNone(trigger)
        self.assertEqual(copied["low_watermark_price"], 90.0)
        self.assertIn("peak=10.00%", note)

    def test_sl_priority_over_trailing(self):
        copied = {
            "side": "buy",
            "entry_price": 100.0,
            "high_watermark_price": 110.0,
            "low_watermark_price": 90.0,
            "watermark_pnl_pct": 10.0,
        }
        trigger, _ = runner._evaluate_tp_sl_trigger(
            copied=copied,
            price=95.0,
            auto_tp_pct=6.0,
            auto_sl_pct=3.0,
            trailing_tp_enable=True,
            trailing_tp_callback_pct=1.0,
        )
        self.assertIn("SL hit", trigger or "")


if __name__ == "__main__":
    unittest.main()
