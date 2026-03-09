---
name: openclaw-hyperliquid-copytrade
description: Monitor target Hyperliquid wallets, score copy-trade decisions using historical performance/risk signals, execute proportional orders with strict risk caps, and broadcast per-trade rationale to Telegram. Use when building or operating AI-assisted follow-trading workflows with dry-run/live modes, score thresholds, and explainable decision logs.
---

# OpenClaw Hyperliquid Copytrade

Build and run a copy-trading pipeline with explainable decisions and live wallet position visibility.

## Inputs Required

Minimum required values:

- `TARGET_WALLETS` (comma-separated, recommended: discover smart wallets at https://simpfor.fun/)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `HYPERLIQUID_WALLET_PRIVATE_KEY`

Optional (have defaults):

- `MODE` (`live` by default)
- `MAX_RISK_PER_TRADE_PCT` (default `10`)
- `MAX_TOTAL_EXPOSURE_PCT` (default `60`)
- `SCORE_THRESHOLD` (default `70`)

## Files

- `scripts/runner.py` — orchestration loop (real wallet fills polling via Hyperliquid `/info`)
- `scripts/score.py` — scoring model (win-rate, hold-time, drawdown, recency)
- `scripts/telegram.py` — Telegram notifications
- `scripts/live_exec.py` — live execution bridge to external signer service
- `scripts/live_executor_service.py` — minimal FastAPI executor endpoint (`/execute`)
- `scripts/live_executor_service_stdlib.py` — dependency-free executor endpoint (`/execute`)
- `scripts/status_web.py` — dependency-free status dashboard (`/`)
- `scripts/manage_services.py` — one-click start/stop/status for all local services
- `scripts/telegram_control.py` — reads Telegram YES/NO replies (including localized variants) for initial follow decision and language hints
- `scripts/state.py` — lightweight state persistence
- `references/strategy.md` — scoring + risk design notes
- `references/hyperliquid-integration.md` — integration points and TODOs

## Quick Start

### One-click onboarding (first-time users)

Run:

`python3 skills/openclaw-hyperliquid-copytrade/scripts/first_run_onboarding.py --start`

It will:

1. Create/update workspace `.env`
2. Apply ready-to-use defaults (`MODE=live`, `KILL_SWITCH=false`, `HL_REAL_EXECUTION=false`)
3. Prompt required values (`TARGET_WALLETS`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)
4. Start all local services

### Manual start

1. Create a `.env` file using `references/env.example`.
2. Run: `python3 skills/openclaw-hyperliquid-copytrade/scripts/runner.py`.
3. Verify Telegram receives live-mode decision logs / execution receipts.
4. If you need a safer simulation first, switch `MODE=dry-run` manually.

## Documentation

- `docs/help-center.md` — index + FAQs + common operations
- `docs/quickstart-onboarding.md` — first-download one-click integration guide
- `docs/runbook.md` — operations and troubleshooting
- `docs/risk-policy.md` — risk controls and live-mode policy
- `docs/telegram-format.md` — message structure and field meanings
- `docs/architecture.md` — runtime architecture and data flow
- `docs/open-source-checklist.md` — pre-release checklist for open-source publish
- `SECURITY.md` — security policy and release gate

## Operating Rules

- Enforce per-trade and total-exposure caps before any execution decision.
- Skip execution when score is below threshold.
- Always log and notify decision rationale.
- Keep idempotency keys per source event to avoid duplicate actions.
- Keep API keys/tokens out of git; use environment variables only.
- Keep `KILL_SWITCH=true` whenever testing risky changes.

## Chat UX Policy (OpenClaw prompt)

When the user asks to start copy-trading from chat (for example: "启动跟单" / "启动一键跟单") and required config is missing, respond with a consistent, friendly template instead of ad-hoc wording.

Use this Chinese template:

```text
启动被拦截了（配置未完成）：

缺少以下必填项：
- TARGET_WALLETS
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
- HYPERLIQUID_WALLET_PRIVATE_KEY

你把这 4 项发我，我就继续帮你完成并启动。
```

Notes:
- Keep wording stable across sessions (avoid stylistic drift).
- If some fields are already present, list only missing fields.
- For `TARGET_WALLETS`, you may append one short hint: `推荐在 https://simpfor.fun/ 发现聪明钱地址`.

## Live Mode Checklist

Switch to `live` only after:

- 24h+ dry-run stability with expected decisions
- Duplicate events correctly ignored
- Exposure caps verified in stress scenarios
- Manual kill switch tested

## Extend

- Replace `fetch_wallet_event_stub()` in `runner.py` with Hyperliquid websocket/event feed.
- Replace `build_order_stub()` with actual Hyperliquid order payload.
- Add wallet-level weighting and blacklist/whitelist filters.
- Add post-trade analytics to update wallet confidence over time.
