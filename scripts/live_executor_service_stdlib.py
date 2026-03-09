#!/usr/bin/env python3
"""
Live executor service (stdlib HTTP server) with optional real Hyperliquid execution.

Endpoints:
- GET  /health
- POST /execute

Auth:
- Optional bearer token via EXECUTOR_BEARER env var.

Execution modes:
- HL_REAL_EXECUTION=false -> mock accept
- HL_REAL_EXECUTION=true  -> signed market order via hyperliquid-python-sdk
"""

import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

HOST = os.getenv("EXECUTOR_HOST", "127.0.0.1")
PORT = int(os.getenv("EXECUTOR_PORT", "8787"))
EXPECTED_BEARER = os.getenv("EXECUTOR_BEARER", "").strip()

HL_REAL_EXECUTION = os.getenv("HL_REAL_EXECUTION", "false").lower() in {"1", "true", "yes", "on"}
HL_API_URL = os.getenv("HL_API_URL", "https://api.hyperliquid.xyz")
HYPERLIQUID_WALLET_PRIVATE_KEY = os.getenv("HYPERLIQUID_WALLET_PRIVATE_KEY", "").strip()
HL_SLIPPAGE = float(os.getenv("HL_MARKET_SLIPPAGE", "0.05"))


def _json(handler: BaseHTTPRequestHandler, code: int, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _execute_real(body: Dict[str, Any]) -> Dict[str, Any]:
    if not HYPERLIQUID_WALLET_PRIVATE_KEY:
        raise RuntimeError("HYPERLIQUID_WALLET_PRIVATE_KEY missing")

    from eth_account import Account
    from hyperliquid.exchange import Exchange
    from hyperliquid.info import Info

    symbol = str(body.get("symbol") or "").strip()
    side = str(body.get("side") or "").strip().lower()
    notional = float(body.get("notional_usd") or 0)
    px = float(body.get("source_price") or 0)

    if not symbol:
        raise RuntimeError("symbol missing")
    if side not in {"buy", "sell"}:
        raise RuntimeError(f"unsupported side: {side}")
    if notional <= 0:
        raise RuntimeError("notional_usd must be > 0")
    if px <= 0:
        raise RuntimeError("source_price must be > 0 for size conversion")

    raw_size = notional / px
    if raw_size <= 0:
        raise RuntimeError("computed size <= 0")

    acct = Account.from_key(HYPERLIQUID_WALLET_PRIVATE_KEY)
    info = Info(base_url=HL_API_URL, skip_ws=True)
    meta = info.meta()
    universe = meta.get("universe", []) if isinstance(meta, dict) else []
    sz_decimals = None
    for a in universe:
        if str(a.get("name", "")).upper() == symbol.upper():
            sz_decimals = int(a.get("szDecimals", 0))
            break
    if sz_decimals is None:
        raise RuntimeError(f"symbol not found in meta universe: {symbol}")

    size = round(raw_size, sz_decimals)
    if size <= 0:
        raise RuntimeError(f"rounded size <= 0 with szDecimals={sz_decimals}")

    ex = Exchange(acct, base_url=HL_API_URL, meta=meta)

    resp = ex.market_open(
        name=symbol,
        is_buy=(side == "buy"),
        sz=float(size),
        slippage=HL_SLIPPAGE,
    )

    return {
        "ok": True,
        "mode": "real",
        "symbol": symbol,
        "side": side,
        "notional_usd": notional,
        "source_price": px,
        "computed_size": size,
        "exchange_response": resp,
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            return _json(self, 404, {"ok": False, "error": "not_found"})
        return _json(
            self,
            200,
            {
                "ok": True,
                "ts": int(time.time()),
                "mode": "real" if HL_REAL_EXECUTION else "mock",
                "api_url": HL_API_URL,
            },
        )

    def do_POST(self):
        if self.path != "/execute":
            return _json(self, 404, {"ok": False, "error": "not_found"})

        if EXPECTED_BEARER:
            auth = self.headers.get("Authorization", "")
            if not auth.lower().startswith("bearer "):
                return _json(self, 401, {"ok": False, "error": "missing_bearer"})
            token = auth.split(" ", 1)[1].strip()
            if token != EXPECTED_BEARER:
                return _json(self, 403, {"ok": False, "error": "invalid_bearer"})

        try:
            n = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(n).decode("utf-8")
            body = json.loads(raw)
        except Exception as e:
            return _json(self, 400, {"ok": False, "error": f"bad_json: {e}"})

        if not HL_REAL_EXECUTION:
            return _json(
                self,
                200,
                {
                    "ok": True,
                    "mode": "mock-stdlib",
                    "received": body,
                    "note": "Mock accepted intent. Set HL_REAL_EXECUTION=true for real order.",
                },
            )

        try:
            result = _execute_real(body)
            return _json(self, 200, result)
        except Exception as e:
            return _json(self, 500, {"ok": False, "mode": "real", "error": str(e), "received": body})

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    print(f"[live-executor-stdlib] listening on http://{HOST}:{PORT} mode={'real' if HL_REAL_EXECUTION else 'mock'}")
    server.serve_forever()
