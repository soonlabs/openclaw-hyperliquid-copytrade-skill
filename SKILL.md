---
name: openclaw-hyperliquid-copytrade
description: Monitor target Hyperliquid wallets, score copy-trade decisions using historical performance/risk signals, execute proportional orders with strict risk caps, and broadcast per-trade rationale to Telegram. Use when building or operating AI-assisted follow-trading workflows with dry-run/live modes, score thresholds, and explainable decision logs.
---

# OpenClaw Hyperliquid Copytrade

Build and run a copy-trading pipeline with explainable decisions and live wallet position visibility.

## Inputs Required

Minimum required values:

- `TARGET_WALLETS` (comma-separated, recommended: discover smart wallets at https://simpfor.fun/)
- `TELEGRAM_BOT_TOKEN` (bot token from @BotFather in Telegram)
- `TELEGRAM_CHAT_ID` (Telegram chat/group ID for receiving copy-trade notifications)
- `HYPERLIQUID_WALLET_PRIVATE_KEY` (your Hyperliquid wallet private key for order execution)

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
2. Apply ready-to-use defaults (`MODE=live`, `KILL_SWITCH=false`, `HL_REAL_EXECUTION=true`)
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

Use the template matching the user's language (Chinese input → Chinese template; English input → English template).

**Chinese template:**

```text
启动被拦截了（配置未完成）：

缺少以下必填项：
- TARGET_WALLETS (要跟单的钱包地址，逗号分隔，推荐在 https://simpfor.fun 发现聪明钱)
- TELEGRAM_BOT_TOKEN (Telegram 机器人 token，从 @BotFather 获取)
- TELEGRAM_CHAT_ID (Telegram 会话/群组 ID，用于接收跟单通知)
- HYPERLIQUID_WALLET_PRIVATE_KEY (你的 Hyperliquid 钱包私钥，用于下单)

你把这 4 项发我，我就继续帮你完成并启动。
```

**English template:**

```text
Start blocked (config incomplete):

Missing required fields:
- TARGET_WALLETS (comma-separated wallet addresses to copy, discover smart wallets at https://simpfor.fun)
- TELEGRAM_BOT_TOKEN (bot token from @BotFather in Telegram)
- TELEGRAM_CHAT_ID (Telegram chat/group ID for receiving copy-trade notifications)
- HYPERLIQUID_WALLET_PRIVATE_KEY (your Hyperliquid wallet private key for order execution)

Send me these 4 values and I'll complete setup and start.
```

Notes:
- Keep wording stable across sessions (avoid stylistic drift).
- If some fields are already present, list only missing fields.

## Live Mode Notes

Default startup is real trading (`MODE=live`, `HL_REAL_EXECUTION=true`). Built-in risk controls protect against overexposure:

- Per-trade cap: `MAX_RISK_PER_TRADE_PCT` (default 10%)
- Total exposure cap: `MAX_TOTAL_EXPOSURE_PCT` (default 60%)
- Score threshold: skip execution when score < `SCORE_THRESHOLD`
- Kill switch: set `KILL_SWITCH=true` to halt all execution immediately

To switch to simulation mode, set `MODE=dry-run` or `HL_REAL_EXECUTION=false`.

## Extend

- Replace `fetch_wallet_event_stub()` in `runner.py` with Hyperliquid websocket/event feed.
- Replace `build_order_stub()` with actual Hyperliquid order payload.
- Add wallet-level weighting and blacklist/whitelist filters.
- Add post-trade analytics to update wallet confidence over time.

How to get tg bot 的chat id?                                                                                                                                    
                                                                                                                                                        
### 方法 A（最简单）                                                                                                                                       
                                                                                                                                                        
1. 给你的 bot 发一条消息（私聊或群里 @它）。                                                                                                               
2. 浏览器打开：                                                                                                                                            
https://api.telegram.org/bot<你的BOT_TOKEN>/getUpdates                                                                                                     
3. 在返回 JSON 里找：                                                                                                                                      
- 私聊：message.chat.id（通常是正数）                                                                                                                      
- 群组：message.chat.id（通常是负数，如 -100...）          