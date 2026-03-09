#!/usr/bin/env python3
"""One-click onboarding for first-time users of openclaw-hyperliquid-copytrade."""

from __future__ import annotations

import argparse
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
    "HL_WALLET_PRIVATE_KEY",
]

SAFETY_DEFAULTS = {
    "MODE": "dry-run",
    "MAX_RISK_PER_TRADE_PCT": "10",
    "MAX_TOTAL_EXPOSURE_PCT": "60",
    "KILL_SWITCH": "true",
    "HL_REAL_EXECUTION": "false",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="First-run onboarding wizard")
    parser.add_argument("--start", action="store_true", help="Start services after env setup")
    parser.add_argument("--no-input", action="store_true", help="Do not prompt interactively")
    args = parser.parse_args()

    print("🦞 Hyperliquid Copytrade 首次接入向导")
    print(f"Workspace: {WORKSPACE_ROOT}")

    data = ensure_env()
    apply_defaults(data)

    if not args.no_input:
        ask_if_needed(data, "TARGET_WALLETS", "请输入跟单目标钱包地址（逗号分隔多个）: ")
        ask_if_needed(data, "TELEGRAM_BOT_TOKEN", "请输入 Telegram Bot Token: ")
        ask_if_needed(data, "TELEGRAM_CHAT_ID", "请输入 Telegram Chat ID: ")
        ask_if_needed(data, "HL_WALLET_PRIVATE_KEY", "请输入 Hyperliquid 私钥（仅本地 .env 保存，不会上传）: ")

    missing = validate_required(data)
    write_env(ENV_FILE, data)

    if missing:
        print("\n❌ 以下配置仍缺失，请补充后重试：")
        for m in missing:
            print(f"- {m}")
        print(f"\n已写入模板到: {ENV_FILE}")
        return 1

    print("\n✅ .env 已就绪（默认安全模式：dry-run + kill-switch=true）")
    print(f"- Web 面板: {data.get('STATUS_WEB_URL', 'http://127.0.0.1:8899')}")

    if args.start:
        print("\n🚀 正在启动服务...")
        rc = run_manage("start")
        if rc != 0:
            print("❌ 启动失败，请检查 logs/*.log")
            return rc
        print("✅ 服务已启动")
        run_manage("status")
        print("\n下一步：去 Telegram 回复 YES/NO 完成首次跟单决策。")
    else:
        print("\n你可以运行以下命令一键启动：")
        print("python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py start")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
