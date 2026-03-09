#!/usr/bin/env python3
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
PID_FILE = ROOT / "services-pids.json"
LOG_DIR = ROOT / "logs"
STATE_FILE = ROOT / "state.json"


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


def _load_workspace_env() -> dict:
    env = os.environ.copy()
    env_path = ROOT.parent.parent / ".env"
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        env[k.strip()] = v.strip()
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
