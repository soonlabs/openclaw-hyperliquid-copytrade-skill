import os
import sys
import unittest


SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import runner  # noqa: E402


class TestRiskControls(unittest.TestCase):
    def test_execution_gates_block_when_total_exposure_exceeded(self):
        gates = runner._evaluate_execution_gates(
            score=80.0,
            threshold=70.0,
            proposed_exposure=1.02,
            current_exposure=49.78,
            risk_pct=5.0,
            total_cap_pct=50.0,
            kill_switch=False,
        )
        self.assertFalse(gates["can_execute"])
        self.assertFalse(gates["exposure_ok"])
        self.assertIn("total_exposure>50.0%", gates["fail_reasons"])

    def test_exposure_released_after_close_unblocks_next_follow(self):
        current = 49.7845
        copied = {"exposure_pct": 1.02, "notional": 10.2}
        after_close = runner._apply_close_exposure(
            current_exposure=current,
            copied=copied,
            notional=10.2,
            capital_usd=1000.0,
        )
        self.assertAlmostEqual(after_close, 48.7645, places=4)

        gates = runner._evaluate_execution_gates(
            score=80.0,
            threshold=70.0,
            proposed_exposure=1.02,
            current_exposure=after_close,
            risk_pct=5.0,
            total_cap_pct=50.0,
            kill_switch=False,
        )
        self.assertTrue(gates["can_execute"])

    def test_close_exposure_never_negative(self):
        after_close = runner._apply_close_exposure(
            current_exposure=0.3,
            copied={"exposure_pct": 5.0, "notional": 50.0},
            notional=50.0,
            capital_usd=1000.0,
        )
        self.assertEqual(after_close, 0.0)

    def test_order_level_collapse_keeps_latest_fill_per_order(self):
        events = [
            {
                "event_id": "e1",
                "wallet": "w1",
                "symbol": "BTC",
                "side": "buy",
                "timestamp": 100,
                "raw_fill": {"oid": 123, "tid": 1},
            },
            {
                "event_id": "e2",
                "wallet": "w1",
                "symbol": "BTC",
                "side": "buy",
                "timestamp": 101,
                "raw_fill": {"oid": 123, "tid": 2},
            },
            {
                "event_id": "e3",
                "wallet": "w1",
                "symbol": "BTC",
                "side": "buy",
                "timestamp": 102,
                "raw_fill": {"oid": 124, "tid": 3},
            },
        ]
        collapsed = runner._collapse_events_by_order(events, processed_order_keys=set())
        self.assertEqual(len(collapsed), 2)
        self.assertEqual(collapsed[0]["event_id"], "e2")
        self.assertEqual(collapsed[1]["event_id"], "e3")

    def test_order_level_collapse_skips_already_processed_order(self):
        events = [
            {
                "event_id": "e1",
                "wallet": "w1",
                "symbol": "BTC",
                "side": "buy",
                "timestamp": 100,
                "raw_fill": {"oid": 123, "tid": 1},
            }
        ]
        processed = {"w1:BTC:buy:123"}
        collapsed = runner._collapse_events_by_order(events, processed_order_keys=processed)
        self.assertEqual(collapsed, [])


if __name__ == "__main__":
    unittest.main()
