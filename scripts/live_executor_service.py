#!/usr/bin/env python3
"""
Minimal live executor service (FastAPI).

Purpose:
- Accept execution intents from runner.py
- Validate bearer token
- (Current) return a safe mock response
- (Next) wire Hyperliquid signed /exchange order placement
"""

import os
import time
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


class ExecIntent(BaseModel):
    symbol: str = Field(..., min_length=1)
    side: str = Field(..., pattern="^(buy|sell)$")
    notional_usd: float = Field(..., gt=0)
    source_event_id: str
    source_wallet: str
    source_price: Optional[float] = None
    source_size: Optional[float] = None
    source_timestamp: Optional[int] = None


app = FastAPI(title="hyperliquid-live-executor", version="0.1.0")


def _check_auth(auth: Optional[str]) -> None:
    expected = os.getenv("EXECUTOR_BEARER", "").strip()
    if not expected:
        return
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid bearer token")


@app.get("/health")
def health():
    return {"ok": True, "ts": int(time.time())}


@app.post("/execute")
def execute(intent: ExecIntent, authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)

    # TODO: Replace this section with real Hyperliquid signed /exchange order placement.
    # Keep response shape stable so runner can log it.
    return {
        "ok": True,
        "mode": "mock",
        "received": intent.model_dump(),
        "note": "Mock executor accepted intent. Wire signer before real funds.",
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("EXECUTOR_HOST", "127.0.0.1")
    port = int(os.getenv("EXECUTOR_PORT", "8787"))
    uvicorn.run(app, host=host, port=port)
