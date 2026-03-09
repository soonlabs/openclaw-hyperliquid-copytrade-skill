import json
import subprocess


def send_telegram(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    proc = subprocess.run(
        [
            "curl",
            "-sS",
            "--fail",
            "-X",
            "POST",
            url,
            "-H",
            "Content-Type: application/json",
            "--data",
            json.dumps(payload),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )

    data = json.loads(proc.stdout)
    if not data.get("ok"):
        raise RuntimeError(f"Telegram send failed: {data}")
