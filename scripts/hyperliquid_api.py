import json
import subprocess
import time
from typing import Dict, List, Optional

INFO_URL = "https://api.hyperliquid.xyz/info"


def _post_info(payload: Dict) -> Dict:
    # Use curl for transport reliability across host Python SSL variants.
    body = json.dumps(payload)
    proc = subprocess.run(
        [
            "curl",
            "-sS",
            "--fail",
            "-X",
            "POST",
            INFO_URL,
            "-H",
            "Content-Type: application/json",
            "--data",
            body,
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    return json.loads(proc.stdout)


def fetch_user_fills(wallet: str, limit: int = 2000) -> List[Dict]:
    # Hyperliquid returns most recent fills first for userFills
    rows = _post_info({"type": "userFills", "user": wallet})
    if not isinstance(rows, list):
        return []
    # Keep ordering stable (oldest -> newest) for replay
    rows = sorted(rows, key=lambda x: x.get("time", 0))
    if limit > 0:
        rows = rows[-limit:]
    return rows


def fetch_user_fills_by_time(wallet: str, start_ms: int, end_ms: Optional[int] = None) -> List[Dict]:
    payload = {
        "type": "userFillsByTime",
        "user": wallet,
        "startTime": int(start_ms),
        "endTime": int(end_ms or int(time.time() * 1000)),
    }
    rows = _post_info(payload)
    if not isinstance(rows, list):
        return []
    return sorted(rows, key=lambda x: x.get("time", 0))


def fetch_clearinghouse_state(wallet: str) -> Dict:
    # Perp account state including assetPositions
    data = _post_info({"type": "clearinghouseState", "user": wallet})
    if not isinstance(data, dict):
        return {}
    return data


def extract_open_positions(wallet: str) -> List[Dict]:
    ch = fetch_clearinghouse_state(wallet)
    positions = []
    for ap in ch.get("assetPositions", []) or []:
        pos = (ap or {}).get("position", {})
        if not isinstance(pos, dict):
            continue
        szi_raw = pos.get("szi", 0)
        try:
            szi = float(szi_raw)
        except Exception:
            szi = 0.0
        if abs(szi) < 1e-12:
            continue
        positions.append(
            {
                "wallet": wallet,
                "coin": pos.get("coin", "UNKNOWN"),
                "side": "long" if szi > 0 else "short",
                "size": abs(szi),
                "signed_size": szi,
                "entry_px": float(pos.get("entryPx", 0) or 0),
                "position_value": float(pos.get("positionValue", 0) or 0),
                "unrealized_pnl": float(pos.get("unrealizedPnl", 0) or 0),
                "margin_used": float(pos.get("marginUsed", 0) or 0),
                "leverage": (pos.get("leverage") or {}).get("value"),
            }
        )
    return positions


def normalize_fill_to_event(fill: Dict, wallet: str) -> Dict:
    # side: B (buy) / A (sell)
    side_raw = (fill.get("side") or "").upper()
    side = "buy" if side_raw == "B" else "sell"

    oid = fill.get("oid", "na")
    tid = fill.get("tid", "na")
    ts = int(fill.get("time", 0))

    event_id = f"{wallet}:{tid}:{oid}:{ts}"
    return {
        "event_id": event_id,
        "wallet": wallet,
        "symbol": fill.get("coin", "UNKNOWN"),
        "side": side,
        "size": float(fill.get("sz", 0) or 0),
        "price": float(fill.get("px", 0) or 0),
        "timestamp": ts // 1000 if ts > 10_000_000_000 else ts,
        "raw_fill": fill,
    }
