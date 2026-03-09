#!/usr/bin/env python3
import json
import os
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HOST = os.getenv("STATUS_WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("STATUS_WEB_PORT", "8899"))
BASE = Path(os.getenv("STATUS_BASE_DIR", "./skills/openclaw-hyperliquid-copytrade"))
STATE_FILE = BASE / "state.json"
RUNTIME_FILE = BASE / "runtime-status.json"
WALLET_ANALYTICS_FILE = BASE / "wallet-analytics.json"


def _load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _fmt_ts_seconds(ts):
    if not ts:
        return "n/a"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


def _fmt_ts_millis(ts):
    if not ts:
        return "n/a"
    try:
        return datetime.fromtimestamp(int(ts) / 1000).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    except Exception:
        return str(ts)


def render_html() -> str:
    state = _load_json(STATE_FILE, {})
    runtime = _load_json(RUNTIME_FILE, {})
    analytics = _load_json(WALLET_ANALYTICS_FILE, {})
    processed = len(state.get("processed_event_ids", []))
    exp = state.get("current_exposure_pct", 0)
    cursor = state.get("last_cursor_ms")
    now = int(time.time())
    wallet_cards = []
    for w, info in (analytics.get("wallets", {}) or {}).items():
        if isinstance(info, dict) and "error" in info:
            wallet_cards.append(f"<div><code>{w}</code> error={info['error']}</div>")
        else:
            pos_lines = []
            for p in (info.get("open_positions") or [])[:8]:
                pos_lines.append(
                    f"<li>{p.get('coin')} {p.get('side')} sz={p.get('size')} entry={p.get('entry_px')} upnl={p.get('unrealized_pnl')}</li>"
                )
            pos_html = "<ul>" + "".join(pos_lines) + "</ul>" if pos_lines else "<div>positions: none</div>"
            wallet_cards.append(
                "<div style='margin-bottom:10px;padding:8px;border:1px dashed #ddd;border-radius:8px'>"
                f"<div><code>{w}</code> "
                f"score=<code>{info.get('score','n/a')}</code> "
                f"wr=<code>{info.get('win_rate','n/a')}</code> "
                f"rwr=<code>{info.get('recent_win_rate','n/a')}</code> "
                f"hold=<code>{info.get('avg_hold_minutes','n/a')}m</code> "
                f"dd=<code>{info.get('max_drawdown_pct','n/a')}%</code> "
                f"open_pos=<code>{info.get('open_position_count','n/a')}</code></div>"
                f"{pos_html}"
                "</div>"
            )
    wallet_html = "".join(wallet_cards) if wallet_cards else "<div>n/a</div>"

    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Copytrade Status</title>
<meta http-equiv='refresh' content='1'>
<style>body{{font-family:system-ui;max-width:900px;margin:24px auto;padding:0 12px}} .card{{border:1px solid #ddd;border-radius:10px;padding:14px;margin:10px 0}} code{{background:#f6f6f6;padding:2px 6px;border-radius:6px}}</style>
</head><body>
<h2>Hyperliquid Copytrade 状态面板</h2>
<div class='card'><b>现在时间:</b> {_fmt_ts_seconds(now)} ({now})</div>
<div class='card'>
  <h3>Runner Runtime</h3>
  <div>status: <code>{runtime.get('status','unknown')}</code></div>
  <div>mode: <code>{runtime.get('mode','n/a')}</code></div>
  <div>kill_switch: <code>{runtime.get('kill_switch','n/a')}</code></div>
  <div>wallets: <code>{', '.join(runtime.get('wallets',[]))}</code></div>
  <div>threshold: <code>{runtime.get('threshold','n/a')}</code></div>
  <div>poll_seconds: <code>{runtime.get('poll_seconds','n/a')}</code></div>
  <div>last_cycle_new_events: <code>{runtime.get('last_cycle_new_events','n/a')}</code></div>
  <div>last_cycle_ts: <code>{_fmt_ts_seconds(runtime.get('last_cycle_ts'))}</code></div>
  <div>initial_follow_decision: <code>{runtime.get('initial_follow_decision','n/a')}</code></div>
  <div>initial_follow_done: <code>{runtime.get('initial_follow_done','n/a')}</code></div>
  <div>detected_lang: <code>{runtime.get('detected_lang','n/a')}</code></div>
</div>
<div class='card'>
  <h3>State</h3>
  <div>processed_event_ids: <code>{processed}</code></div>
  <div>current_exposure_pct: <code>{exp}</code></div>
  <div>last_cursor_ms: <code>{_fmt_ts_millis(cursor)}</code></div>
</div>
<div class='card'>
  <h3>Wallet Analytics</h3>
  <div>updated_at: <code>{_fmt_ts_seconds(analytics.get('updated_at'))}</code></div>
  <div>threshold: <code>{analytics.get('threshold','n/a')}</code></div>
  {wallet_html}
</div>
<div class='card'>
  <h3>Files</h3>
  <div>{STATE_FILE}</div>
  <div>{RUNTIME_FILE}</div>
  <div>{WALLET_ANALYTICS_FILE}</div>
</div>
</body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ["/", "/status"]:
            self.send_response(404)
            self.end_headers()
            return
        html = render_html().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    print(f"[status-web] http://{HOST}:{PORT}")
    HTTPServer((HOST, PORT), H).serve_forever()
