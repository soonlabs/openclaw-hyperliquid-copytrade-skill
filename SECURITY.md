# SECURITY.md

## Security Principles

- Never commit secrets to git.
- Keep all credentials in local `.env` only.
- Treat `HL_WALLET_PRIVATE_KEY` as the highest-risk secret.
- Default to safe mode for first run:
  - `MODE=dry-run`
  - `KILL_SWITCH=true`
  - `HL_REAL_EXECUTION=false`

## Must-NOT-Commit Files

- `.env`
- `skills/openclaw-hyperliquid-copytrade/logs/*`
- `skills/openclaw-hyperliquid-copytrade/state.json`
- `skills/openclaw-hyperliquid-copytrade/runtime-status.json`
- `skills/openclaw-hyperliquid-copytrade/services-pids.json`
- `skills/openclaw-hyperliquid-copytrade/tg-offset.json`
- `skills/openclaw-hyperliquid-copytrade/wallet-analytics.json`

## Release Gate (required before open source release)

Run preflight scanner:

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/security_preflight.py
```

If any finding appears, fix it before publish.

## Incident Response (if secret leaked)

1. Rotate Telegram bot token immediately.
2. Rotate Hyperliquid private key immediately.
3. Invalidate shared bearer secrets (`LIVE_EXECUTOR_BEARER`) if used.
4. Rewrite git history if needed before public release.
5. Re-run preflight scanner and confirm clean result.
