# Help Center

This is the central help entry for `openclaw-hyperliquid-copytrade`.

## What to read first

For first-time users:
- `docs/quickstart-onboarding.md`

For existing deployments:
- `docs/runbook.md` (operations)
- `docs/risk-policy.md` (risk controls)
- `docs/telegram-format.md` (message fields)
- `docs/architecture.md` (system design)

## One-command onboarding

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/first_run_onboarding.py --start
```

This command:
1. creates/updates workspace `.env`
2. applies defaults (`MODE=live`, `KILL_SWITCH=false`)
3. asks for required values step-by-step
4. starts executor + status web + runner

## Common ops commands

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py start
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py status
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py stop
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py restart
```

## FAQ

### Telegram not receiving messages
- Check `.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Ensure bot can post in target chat
- Check `skills/openclaw-hyperliquid-copytrade/logs/runner.log`

### Why all actions are SKIP
- `KILL_SWITCH=true`
- `SCORE_THRESHOLD` too high
- exposure caps already hit

### Does first startup place live orders immediately?
The runtime enters live decision flow by default (`MODE=live`, `KILL_SWITCH=false`).
If you want simulation-first behavior, switch to `MODE=dry-run` before start.

## Security reminders

- Never share private keys/tokens in chat.
- Keep secrets only in local `.env`.
- Run observation/validation before any production-scale live usage.
