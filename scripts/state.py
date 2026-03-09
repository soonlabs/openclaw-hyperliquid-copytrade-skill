import json
import os
from typing import Any, Dict


def load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"processed_event_ids": [], "current_exposure_pct": 0.0}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
