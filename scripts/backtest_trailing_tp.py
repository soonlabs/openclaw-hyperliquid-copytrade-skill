#!/usr/bin/env python3
"""Lightweight replay backtest for trailing TP/SL behavior.

Usage:
  python3 skills/openclaw-hyperliquid-copytrade/scripts/backtest_trailing_tp.py \
    --side buy --entry 100 --prices 102,106,110,108
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import runner  # noqa: E402


def simulate_price_path(
    side: str,
    entry: float,
    prices: List[float],
    *,
    auto_tp_pct: float = 6.0,
    auto_sl_pct: float = 3.0,
    trailing_tp_enable: bool = True,
    trailing_tp_callback_pct: float = 1.0,
) -> Dict:
    copied = {
        "side": side,
        "entry_price": float(entry),
        "notional": 100.0,
        "high_watermark_price": float(entry),
        "low_watermark_price": float(entry),
        "watermark_price": float(entry),
        "watermark_pnl_pct": 0.0,
    }

    history = []
    triggered = None
    for idx, px in enumerate(prices):
        trigger, note = runner._evaluate_tp_sl_trigger(
            copied=copied,
            price=float(px),
            auto_tp_pct=float(auto_tp_pct),
            auto_sl_pct=float(auto_sl_pct),
            trailing_tp_enable=bool(trailing_tp_enable),
            trailing_tp_callback_pct=float(trailing_tp_callback_pct),
        )
        row = {
            "step": idx,
            "price": float(px),
            "high_watermark_price": copied["high_watermark_price"],
            "low_watermark_price": copied["low_watermark_price"],
            "watermark_pnl_pct": copied["watermark_pnl_pct"],
            "note": note,
            "trigger": trigger,
        }
        history.append(row)
        if trigger and triggered is None:
            triggered = row
            break

    return {
        "input": {
            "side": side,
            "entry": float(entry),
            "prices": [float(x) for x in prices],
            "auto_tp_pct": float(auto_tp_pct),
            "auto_sl_pct": float(auto_sl_pct),
            "trailing_tp_enable": bool(trailing_tp_enable),
            "trailing_tp_callback_pct": float(trailing_tp_callback_pct),
        },
        "triggered": triggered,
        "history": history,
    }


def _parse_prices(csv: str) -> List[float]:
    return [float(x.strip()) for x in csv.split(",") if x.strip()]


def main() -> None:
    p = argparse.ArgumentParser(description="Replay backtest for trailing TP")
    p.add_argument("--side", choices=["buy", "sell"], required=True)
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--prices", type=str, required=True, help="CSV price path, e.g. 102,106,110,108")
    p.add_argument("--auto-tp-pct", type=float, default=6.0)
    p.add_argument("--auto-sl-pct", type=float, default=3.0)
    p.add_argument("--trailing-enable", action="store_true", default=False)
    p.add_argument("--trailing-callback-pct", type=float, default=1.0)
    args = p.parse_args()

    result = simulate_price_path(
        side=args.side,
        entry=args.entry,
        prices=_parse_prices(args.prices),
        auto_tp_pct=args.auto_tp_pct,
        auto_sl_pct=args.auto_sl_pct,
        trailing_tp_enable=args.trailing_enable,
        trailing_tp_callback_pct=args.trailing_callback_pct,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
