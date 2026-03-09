import json
import subprocess
from typing import Dict, Optional


def execute_live_order(
    event: Dict,
    notional_usd: float,
    *,
    executor_url: Optional[str],
    executor_bearer: Optional[str],
    timeout_seconds: int = 20,
) -> Dict:
    """
    Send live execution intent to an external signer/executor service.

    Expected request payload:
      {
        "symbol": "BTC",
        "side": "buy",
        "notional_usd": 123.45,
        "source_event_id": "...",
        "source_wallet": "0x...",
        "source_price": 12345.6
      }
    """
    if not executor_url:
        raise RuntimeError("LIVE_EXECUTOR_URL is required for MODE=live")

    payload = {
        "symbol": event.get("symbol"),
        "side": event.get("side"),
        "notional_usd": round(float(notional_usd), 2),
        "source_event_id": event.get("event_id"),
        "source_wallet": event.get("wallet"),
        "source_price": event.get("price"),
        "source_size": event.get("size"),
        "source_timestamp": event.get("timestamp"),
    }

    cmd = [
        "curl",
        "-sS",
        "--fail",
        "-X",
        "POST",
        executor_url,
        "-H",
        "Content-Type: application/json",
    ]
    if executor_bearer:
        cmd += ["-H", f"Authorization: Bearer {executor_bearer}"]
    cmd += ["--data", json.dumps(payload)]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=True,
    )

    if not proc.stdout.strip():
        return {"ok": True, "raw": ""}

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": True, "raw": proc.stdout.strip()}
