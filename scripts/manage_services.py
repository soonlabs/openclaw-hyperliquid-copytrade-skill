#!/usr/bin/env python3
import json
import locale
import os
import signal
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
WORKSPACE_ROOT = ROOT.parent.parent
PID_FILE = ROOT / "services-pids.json"
LOG_DIR = ROOT / "logs"
STATE_FILE = ROOT / "state.json"
ENV_FILE = WORKSPACE_ROOT / ".env"
ENV_EXAMPLE = ROOT / "references" / "env.example"

REQUIRED_KEYS = [
    "TARGET_WALLETS",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "HYPERLIQUID_WALLET_PRIVATE_KEY",
]


def _detect_lang() -> str:
    tg_lang = os.getenv("TG_LANG", "auto").strip().lower()
    if tg_lang in {"zh", "zh-cn", "zh-hans", "zh-tw", "zh-hant"}:
        return "zh"
    if tg_lang in {"en", "en-us", "en-gb"}:
        return "en"

    loc = (os.getenv("LANG") or (locale.getdefaultlocale()[0] or "") or "").lower()
    if loc.startswith("zh"):
        return "zh"
    return "en"


def _t(lang: str, en: str, zh: str) -> str:
    return zh if lang == "zh" else en


def _prepare_startup_state():
    if not STATE_FILE.exists():
        return
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    state["startup_prompt_sent"] = False
    state["initial_follow_decision"] = "pending"
    state["initial_follow_done"] = False
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_env(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def _write_env(path: Path, data: dict) -> None:
    lines = [f"{k}={v}" for k, v in data.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _missing_required_keys(data: dict) -> list[str]:
    missing = []
    for k in REQUIRED_KEYS:
        v = str(data.get(k, "")).strip()
        if not v or v == "replace_me":
            missing.append(k)
    return missing


def _ensure_required_config_interactive() -> bool:
    lang = _detect_lang()

    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    data = _parse_env(ENV_FILE)
    missing = _missing_required_keys(data)
    if not missing:
        return True

    if not sys.stdin.isatty():
        if lang == "zh":
            print("启动被拦截了（配置未完成）：\n")
            print("缺少以下必填项：")
            if "TARGET_WALLETS" in missing:
                print("- TARGET_WALLETS (要跟单的钱包地址，逗号分隔，推荐在 simpfor.fun 发现聪明钱)")
            if "TELEGRAM_BOT_TOKEN" in missing:
                print("- TELEGRAM_BOT_TOKEN (Telegram 机器人 token，从 @BotFather 获取)")
            if "TELEGRAM_CHAT_ID" in missing:
                print("- TELEGRAM_CHAT_ID (Telegram 会话/群组 ID，用于接收跟单通知)")
            if "HYPERLIQUID_WALLET_PRIVATE_KEY" in missing:
                print("- HYPERLIQUID_WALLET_PRIVATE_KEY (你的 Hyperliquid 钱包私钥，用于下单)")
            print("\n你把这 4 项发我，我就继续帮你完成并启动。")
        else:
            print("Start blocked (config incomplete):\n")
            print("Missing required fields:")
            if "TARGET_WALLETS" in missing:
                print("- TARGET_WALLETS (comma-separated wallet addresses to copy, discover smart wallets at simpfor.fun)")
            if "TELEGRAM_BOT_TOKEN" in missing:
                print("- TELEGRAM_BOT_TOKEN (bot token from @BotFather in Telegram)")
            if "TELEGRAM_CHAT_ID" in missing:
                print("- TELEGRAM_CHAT_ID (Telegram chat/group ID for receiving copy-trade notifications)")
            if "HYPERLIQUID_WALLET_PRIVATE_KEY" in missing:
                print("- HYPERLIQUID_WALLET_PRIVATE_KEY (your Hyperliquid wallet private key for order execution)")
            print("\nSend me these 4 values and I'll complete setup and start.")
        return False

    print(_t(lang, "⚠️ First run or incomplete config detected. Let's collect required fields step-by-step:", "⚠️ 检测到首次启动或配置不完整，先进行分步骤配置："))
    print(_t(lang, f"Config file: {ENV_FILE}", f"配置文件：{ENV_FILE}"))

    prompts = {
        "TARGET_WALLETS": _t(lang, "1/4 Enter target wallet address(es), comma-separated (discover smart wallets at https://simpfor.fun/): ", "1/4 请输入跟单目标钱包地址（多个用逗号分隔，推荐在 https://simpfor.fun/ 发现聪明钱）: "),
        "TELEGRAM_BOT_TOKEN": _t(lang, "2/4 Enter Telegram Bot Token: ", "2/4 请输入 Telegram Bot Token: "),
        "TELEGRAM_CHAT_ID": _t(lang, "3/4 Enter Telegram Chat ID: ", "3/4 请输入 Telegram Chat ID: "),
        "HYPERLIQUID_WALLET_PRIVATE_KEY": _t(lang, "4/4 Enter Hyperliquid wallet private key (saved locally in .env only): ", "4/4 请输入 Hyperliquid 钱包私钥（仅写入本地 .env）: "),
    }
    for key in REQUIRED_KEYS:
        if key not in missing:
            continue
        val = input(prompts[key]).strip()
        if val:
            data[key] = val

    still_missing = _missing_required_keys(data)
    _write_env(ENV_FILE, data)

    if still_missing:
        print(_t(lang, "\n❌ Configuration is still incomplete. Input has been saved. Please fill remaining fields and retry:", "\n❌ 配置仍不完整，已保存当前输入。请补齐后再启动："))
        for key in still_missing:
            print(f"- {key}")
        print(_t(lang, f"Edit file: {ENV_FILE}", f"编辑文件：{ENV_FILE}"))
        return False

    print(_t(lang, "\n✅ Required configuration is complete. Continuing startup...", "\n✅ 必要配置已完成，正在继续启动服务…"))
    return True


def _load_workspace_env() -> dict:
    env = os.environ.copy()
    for k, v in _parse_env(ENV_FILE).items():
        env[k] = v
    return env


def _start(name: str, cmd: list[str]):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out = open(LOG_DIR / f"{name}.log", "a", encoding="utf-8")
    p = subprocess.Popen(cmd, stdout=out, stderr=out, cwd=str(ROOT.parent.parent), env=_load_workspace_env())
    return p.pid


def _resolve_python() -> str:
    venv_py = ROOT.parent.parent / ".venv-hl" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def start_all():
    if not _ensure_required_config_interactive():
        raise SystemExit(1)

    _prepare_startup_state()
    py = _resolve_python()
    pids = {}
    pids["executor"] = _start("executor", [py, str(BASE / "live_executor_service_stdlib.py")])
    pids["status_web"] = _start("status_web", [py, str(BASE / "status_web.py")])
    pids["runner"] = _start("runner", [py, "-u", str(BASE / "runner.py")])
    PID_FILE.write_text(json.dumps(pids, indent=2), encoding="utf-8")
    print("started", pids)


def stop_all():
    if not PID_FILE.exists():
        print("no pid file")
        return
    pids = json.loads(PID_FILE.read_text(encoding="utf-8"))
    for _, pid in pids.items():
        try:
            os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
    PID_FILE.unlink(missing_ok=True)
    print("stopped", pids)


def status_all():
    if not PID_FILE.exists():
        print("stopped")
        return
    pids = json.loads(PID_FILE.read_text(encoding="utf-8"))
    status = {}
    for name, pid in pids.items():
        try:
            os.kill(int(pid), 0)
            status[name] = f"running({pid})"
        except ProcessLookupError:
            status[name] = f"dead({pid})"
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in {"start", "stop", "status", "restart"}:
        print("Usage: python manage_services.py <start|stop|status|restart>")
        raise SystemExit(1)
    action = sys.argv[1]
    if action == "start":
        start_all()
    elif action == "stop":
        stop_all()
    elif action == "status":
        status_all()
    elif action == "restart":
        stop_all()
        start_all()
