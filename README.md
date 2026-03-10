# OpenClaw Hyperliquid Copytrade Skill

[English](#english) | [中文](#中文)

---

## English

An OpenClaw skill for **Hyperliquid copy trading**:
- Monitors target wallet fills
- Scores opportunities with risk checks
- Executes proportional actions (dry-run/live)
- Sends decision/execution logs to Telegram

### 1) Fastest prompt for assistant-driven startup (recommended)

In Telegram/OpenClaw chat, send:

```text
Start one-click copytrade
```

For one-shot setup + launch, send:

```text
Start one-click copytrade. Write these into .env and launch:
TARGET_WALLETS=your_wallets
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

> Security tip: do **not** send private keys in chat. Set `HYPERLIQUID_WALLET_PRIVATE_KEY` locally in your terminal.

### 2) Quick start (CLI)

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/first_run_onboarding.py --start
```

This will:
1. Initialize/update `.env`
2. Apply defaults
3. Prompt required fields interactively
4. Start services (executor / status_web / runner)

### 3) Required config

- `TARGET_WALLETS` (comma-separated; discover candidate smart wallets at https://simpfor.fun/)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `HYPERLIQUID_WALLET_PRIVATE_KEY`

### 4) Common commands

Start:
```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py start
```

Stop:
```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py stop
```

Status:
```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py status
```

### 5) Mode notes

- `MODE=live`: live monitoring/execution path (still governed by safety switches)
- `MODE=dry-run`: simulation only
- `HL_REAL_EXECUTION=false`: safer guardrail (no real order placement)

---

## 中文

一个用于 **Hyperliquid 跟单** 的 OpenClaw Skill：
- 监听目标钱包成交
- 进行评分与风控
- 按比例执行（可 dry-run / live）
- 将决策与执行结果推送到 Telegram

### 1) 给 AI 助手的“最快启动 Prompt”（推荐）

如果你在 Telegram / OpenClaw 对话里操作，直接发：

```text
启动一键跟单，走初次跟单流程
```

如果你希望它一次性就补齐配置并开跑，发：

```text
启动一键跟单。按以下配置写入 .env 并启动：
TARGET_WALLETS=你的地址
TELEGRAM_BOT_TOKEN=你的token
TELEGRAM_CHAT_ID=你的chat_id
```

> 安全建议：私钥不要在聊天里发送。可在本机终端手动写入 `HYPERLIQUID_WALLET_PRIVATE_KEY`。

### 2) 快速启动（命令行）

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/first_run_onboarding.py --start
```

它会自动：
1. 初始化/更新 `.env`
2. 应用默认参数
3. 交互式补齐必填项
4. 启动服务（executor / status_web / runner）

### 3) 必填配置

- `TARGET_WALLETS`（可多个，逗号分隔，推荐先去 https://simpfor.fun/ 发现聪明钱）
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `HYPERLIQUID_WALLET_PRIVATE_KEY`

### 4) 常用操作

启动：
```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py start
```

停止：
```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py stop
```

状态：
```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py status
```

### 5) 模式说明

- `MODE=live`：实时模式（仍受其它安全开关约束）
- `MODE=dry-run`：仅模拟，不真实执行
- `HL_REAL_EXECUTION=false`：即使 live，也不真实下单（更安全）
