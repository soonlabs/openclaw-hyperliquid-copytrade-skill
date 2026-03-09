# Runbook

## Prerequisites

- Python 3 available (recommended: `.venv-hl`).
- Workspace `.env` contains required variables.
- Telegram bot can send messages to target chat.

## Required env

Minimum required values:

- `TARGET_WALLETS`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `HL_WALLET_PRIVATE_KEY`

Optional with defaults:

- `MODE` (`dry-run` by default)
- `MAX_RISK_PER_TRADE_PCT` (default `10`)
- `MAX_TOTAL_EXPOSURE_PCT` (default `60`)
- `SCORE_THRESHOLD` (default `70`)
- `EVENT_GRANULARITY` (`order` by default; use `fill` for per-fill mode)
- `DECISION_DEDUP_WINDOW_SECONDS` (default `0`; only used when `EVENT_GRANULARITY=fill`)

For `MODE=live`:

- `LIVE_EXECUTOR_URL` is required by runner.

Trailing TP options:

- `AUTO_TP_PCT` (trailing activation threshold when enabled)
- `AUTO_SL_PCT`
- `TRAILING_TP_ENABLE` (`true`/`false`)
- `TRAILING_TP_CALLBACK_PCT` (> 0)

## One-click service operations

From workspace root:

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py start
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py status
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py stop
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py restart
```

### What `start` launches

- `live_executor_service_stdlib.py` (executor)
- `status_web.py` (local dashboard)
- `runner.py` (main decision loop)

### URLs / logs / pid files

- Web status: `http://127.0.0.1:8899` (default from `STATUS_WEB_URL`)
- Logs:
  - `skills/openclaw-hyperliquid-copytrade/logs/executor.log`
  - `skills/openclaw-hyperliquid-copytrade/logs/status_web.log`
  - `skills/openclaw-hyperliquid-copytrade/logs/runner.log`
- PID file: `skills/openclaw-hyperliquid-copytrade/services-pids.json`

## Common failures and fixes

### 1) `Missing required env: ...`

Cause: required `.env` key missing.

Fix: add missing variable in workspace `.env` and restart services.

---

### 2) `MODE=live requires LIVE_EXECUTOR_URL`

Cause: live mode enabled without executor endpoint.

Fix:

- either set `LIVE_EXECUTOR_URL`, or
- switch back to `MODE=dry-run`.

---

### 3) Telegram send fails (`curl --fail` / non-OK response)

Cause: invalid token/chat id, bot not in chat, or bot lacks permissions.

Fix checklist:

- verify bot token from BotFather
- verify chat id via `getUpdates`
- make sure bot received at least one user message
- for groups, ensure bot is added and allowed to post

---

### 4) `status` shows dead processes or stale PID file

Cause: process died unexpectedly.

Fix:

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py stop
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py start
```

Then inspect `logs/*.log`.

---

### 5) No new decisions for long time

Cause options:

- source wallet has no new fills
- `SCORE_THRESHOLD` too strict
- `KILL_SWITCH=true` forcing skips

Fix:

- check `wallet-analytics.json` and runner logs
- lower threshold only after validation
- keep dry-run while tuning

---

### 6) `TRAILING_TP_CALLBACK_PCT must be > 0`

Cause: invalid callback config.

Fix:

- set a positive number (example: `TRAILING_TP_CALLBACK_PCT=1`)
- restart services

## Verification notes (2026-02-27)

- Runner now persists trailing watermark fields in `state.json` per copied position.
- Telegram close rationale includes trailing retrace details when triggered.
- Validation command used: `python3 -m py_compile scripts/*.py`.

## Replay backtest for trailing TP

Use a local replay to validate price paths quickly:

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/backtest_trailing_tp.py \
  --side buy --entry 100 --prices 102,106,110,108 \
  --auto-tp-pct 6 --auto-sl-pct 3 --trailing-enable --trailing-callback-pct 1
```

The output JSON includes per-step watermarks and first trigger (if any).

Recommended automated checks:

```bash
python3 -m unittest skills/openclaw-hyperliquid-copytrade/tests/test_trailing_tp.py -v
python3 -m unittest skills/openclaw-hyperliquid-copytrade/tests/test_backtest_trailing_tp.py -v
```

## Overnight safe profile

Suggested overnight profile:

- `MODE=dry-run`
- `KILL_SWITCH=true`
- `HL_REAL_EXECUTION=false`

This preserves monitoring and Telegram visibility with zero live execution.
