# First-Time Setup: One-Command Onboarding

Goal: get a new user running in ~3 minutes (default ready-to-use profile: `MODE=live`, `KILL_SWITCH=false`).

## Prerequisites

- Python 3 installed
- Current directory is your OpenClaw workspace root
- Telegram bot created (you have the bot token)

## One-command start

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/first_run_onboarding.py --start
```

You will be guided to provide:
- `TARGET_WALLETS` (recommended: discover smart wallets at https://simpfor.fun/)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `HYPERLIQUID_WALLET_PRIVATE_KEY`

Then the script will:
- create/update `.env`
- apply default runtime values
- start local services

> Even if you run `manage_services.py start` directly, first-run or missing-required-config cases now trigger step-by-step setup first (instead of starting trading immediately).
>
> If manual edit is required, the full file path is:
> `/Users/damon/.openclaw/workspace-main/.env`

## Verify successful setup

1. Terminal shows `started` or `running(pid)`
2. Open `http://127.0.0.1:8899`
3. Telegram receives startup snapshot

## Common failures

### 1) Missing required config
Run onboarding again:

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/first_run_onboarding.py
```

### 2) Service startup failed
Check logs:
- `skills/openclaw-hyperliquid-copytrade/logs/runner.log`
- `skills/openclaw-hyperliquid-copytrade/logs/executor.log`
- `skills/openclaw-hyperliquid-copytrade/logs/status_web.log`

### 3) No Telegram messages
Verify bot token/chat id and bot permissions in the target chat.

## Recommended next step

- Observe behavior in `dry-run` first if you want lower risk
- Validate SKIP/FOLLOW reasons and sizing behavior
- Keep or switch mode intentionally based on your risk tolerance
