import json
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def _curl_json(args, timeout=20):
    proc = subprocess.run(
        ["curl", "-sS", "--fail", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    return json.loads(proc.stdout)


def get_updates(bot_token: str, offset: Optional[int] = None, timeout_sec: int = 0):
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    payload = {"timeout": timeout_sec}
    if offset is not None:
        payload["offset"] = offset
    return _curl_json([
        "-X",
        "POST",
        url,
        "-H",
        "Content-Type: application/json",
        "--data",
        json.dumps(payload),
    ])


def read_offset(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return int(json.loads(path.read_text(encoding="utf-8")).get("offset", 0))
    except Exception:
        return 0


def write_offset(path: Path, offset: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"offset": int(offset)}, indent=2), encoding="utf-8")


def detect_lang_from_text(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text or ""):
        return "zh"
    return "en"


def _normalize_lang_code(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    c = code.lower()
    if c.startswith("zh"):
        return "zh"
    if c.startswith("en"):
        return "en"
    return None


def poll_yes_no_decision(bot_token: str, chat_id: str, offset_path: str) -> Tuple[Optional[str], int, Optional[str]]:
    p = Path(offset_path)
    offset = read_offset(p)
    resp = get_updates(bot_token, offset=offset, timeout_sec=0)
    if not resp.get("ok"):
        return None, offset, None

    decision = None
    detected_lang = None
    new_offset = offset

    yes_tokens = {"yes", "y", "是", "好", "可以", "行", "要"}
    no_tokens = {"no", "n", "否", "不要", "不", "不用", "算了"}

    for item in resp.get("result", []):
        upd_id = int(item.get("update_id", 0))
        new_offset = max(new_offset, upd_id + 1)

        msg = item.get("message") or item.get("edited_message") or {}
        chat = msg.get("chat", {})
        if str(chat.get("id")) != str(chat_id):
            continue

        user_lang = _normalize_lang_code((msg.get("from") or {}).get("language_code"))
        if user_lang in {"zh", "en"}:
            detected_lang = user_lang

        raw_text = (msg.get("text") or "").strip()
        text = raw_text.lower()
        if not raw_text:
            continue

        if detected_lang not in {"zh", "en"}:
            detected_lang = detect_lang_from_text(raw_text)

        if text in yes_tokens or raw_text in yes_tokens:
            decision = "yes"
        elif text in no_tokens or raw_text in no_tokens:
            decision = "no"

    if new_offset != offset:
        write_offset(p, new_offset)
    return decision, new_offset, detected_lang
