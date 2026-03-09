#!/usr/bin/env python3
"""One-click onboarding for first-time users of openclaw-hyperliquid-copytrade."""

from __future__ import annotations

import argparse
import locale
import os
import subprocess
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = SKILL_ROOT.parent.parent
ENV_EXAMPLE = SKILL_ROOT / "references" / "env.example"
ENV_FILE = WORKSPACE_ROOT / ".env"
MANAGE = SKILL_ROOT / "scripts" / "manage_services.py"

REQUIRED = [
    "TARGET_WALLETS",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "HYPERLIQUID_WALLET_PRIVATE_KEY",
]

SAFETY_DEFAULTS = {
    "MODE": "live",
    "MAX_RISK_PER_TRADE_PCT": "10",
    "MAX_TOTAL_EXPOSURE_PCT": "60",
    "KILL_SWITCH": "false",
    "HL_REAL_EXECUTION": "false",
    "LIVE_EXECUTOR_URL": "http://127.0.0.1:8787/execute",
    "STATUS_WEB_URL": "http://127.0.0.1:8899",
    "TG_LANG": "auto",
}


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def write_env(path: Path, data: dict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in data.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return parse_env(ENV_FILE)


def ask_if_needed(data: dict[str, str], key: str, prompt: str) -> None:
    current = data.get(key, "")
    if current and current not in {"replace_me", ""}:
        return
    value = input(prompt).strip()
    if value:
        data[key] = value


def apply_defaults(data: dict[str, str]) -> None:
    # Backward compatibility: older setup used HL_WALLET_PRIVATE_KEY
    if not data.get("HYPERLIQUID_WALLET_PRIVATE_KEY") and data.get("HL_WALLET_PRIVATE_KEY"):
        data["HYPERLIQUID_WALLET_PRIVATE_KEY"] = data["HL_WALLET_PRIVATE_KEY"]

    for k, v in SAFETY_DEFAULTS.items():
        data[k] = v


def validate_required(data: dict[str, str]) -> list[str]:
    missing = []
    for k in REQUIRED:
        v = data.get(k, "").strip()
        if not v or v == "replace_me":
            missing.append(k)
    return missing


def run_manage(action: str) -> int:
    cmd = ["python3", str(MANAGE), action]
    return subprocess.call(cmd, cwd=str(WORKSPACE_ROOT))


def detect_lang() -> str:
    tg_lang = os.getenv("TG_LANG", "auto").strip().lower()
    if tg_lang in {"zh", "zh-cn", "zh-hans", "zh-tw", "zh-hant"}:
        return "zh"
    if tg_lang in {"en", "en-us", "en-gb"}:
        return "en"

    loc = (os.getenv("LANG") or (locale.getdefaultlocale()[0] or "") or "").lower()
    if loc.startswith("zh"):
        return "zh"
    return "en"


def t(lang: str, en: str, zh: str) -> str:
    return zh if lang == "zh" else en


def main() -> int:
    parser = argparse.ArgumentParser(description="First-run onboarding wizard")
    parser.add_argument("--start", action="store_true", help="Start services after env setup")
    parser.add_argument("--no-input", action="store_true", help="Do not prompt interactively")
    args = parser.parse_args()

    lang = detect_lang()

    print(t(lang, "🦞 Hyperliquid Copytrade first-run onboarding", "🦞 Hyperliquid Copytrade 首次接入向导"))
    print(f"Workspace: {WORKSPACE_ROOT}")

    data = ensure_env()
    apply_defaults(data)

    if not args.no_input:
        ask_if_needed(
            data,
            "TARGET_WALLETS",
            t(lang, "Enter target wallet address(es), comma-separated (discover smart wallets at https://simpfor.fun/): ", "请输入跟单目标钱包地址（逗号分隔多个，推荐在 https://simpfor.fun/ 发现聪明钱）: "),
        )
        ask_if_needed(
            data,
            "TELEGRAM_BOT_TOKEN",
            t(lang, "Enter Telegram Bot Token: ", "请输入 Telegram Bot Token: "),
        )
        ask_if_needed(
            data,
            "TELEGRAM_CHAT_ID",
            t(lang, "Enter Telegram Chat ID: ", "请输入 Telegram Chat ID: "),
        )
        ask_if_needed(
            data,
            "HYPERLIQUID_WALLET_PRIVATE_KEY",
            t(
                lang,
                "Enter Hyperliquid wallet private key (saved locally in .env only): ",
                "请输入 Hyperliquid 钱包私钥（仅本地 .env 保存，不会上传）: ",
            ),
        )

    missing = validate_required(data)
    write_env(ENV_FILE, data)

    if missing:
        print(t(lang, "\n❌ Missing required configuration:", "\n❌ 以下配置仍缺失，请补充后重试："))
        for m in missing:
            print(f"- {m}")
        print(t(lang, f"\nTemplate/config saved to: {ENV_FILE}", f"\n已写入模板到: {ENV_FILE}"))
        return 1

    print(
        t(
            lang,
            "\n✅ .env is ready (default ready-to-use: MODE=live + KILL_SWITCH=false)",
            "\n✅ .env 已就绪（默认开箱即用：MODE=live + KILL_SWITCH=false）",
        )
    )
    print(t(lang, f"- Web dashboard: {data.get('STATUS_WEB_URL', 'http://127.0.0.1:8899')}", f"- Web 面板: {data.get('STATUS_WEB_URL', 'http://127.0.0.1:8899')}"))

    if args.start:
        print(t(lang, "\n🚀 Starting services...", "\n🚀 正在启动服务..."))
        rc = run_manage("start")
        if rc != 0:
            print(t(lang, "❌ Startup failed. Check logs/*.log", "❌ 启动失败，请检查 logs/*.log"))
            return rc
        print(t(lang, "✅ Services started", "✅ 服务已启动"))
        run_manage("status")
        print(
            t(
                lang,
                "\nNext: reply YES/NO in Telegram to finish initial follow decision.",
                "\n下一步：去 Telegram 回复 YES/NO 完成首次跟单决策。",
            )
        )
    else:
        print(t(lang, "\nRun the command below to start services:", "\n你可以运行以下命令一键启动："))
        print("python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py start")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
