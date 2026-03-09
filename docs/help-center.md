# Help Center（使用帮助）

本文件是 `openclaw-hyperliquid-copytrade` 的统一帮助入口。

## 1) 我应该先看什么？

首次安装用户：
- 先看 `docs/quickstart-onboarding.md`
- 然后执行一键接入命令（会引导你填 `.env`）

已有环境用户：
- 日常运维看 `docs/runbook.md`
- 风控策略看 `docs/risk-policy.md`
- Telegram 消息字段看 `docs/telegram-format.md`
- 架构理解看 `docs/architecture.md`

## 2) 一键接入（首次用户推荐）

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/first_run_onboarding.py --start
```

该命令会：
1. 自动生成/补齐 workspace 根目录 `.env`
2. 强制安全默认值（`MODE=dry-run` + `KILL_SWITCH=true`）
3. 引导填写必要字段（钱包/TG Token/TG Chat ID）
4. 自动启动 executor + status_web + runner

## 3) 常用运维命令

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py start
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py status
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py stop
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py restart
```

## 4) 常见问题

### Q1: Telegram 没有收到消息
- 检查 `.env` 中 `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`
- 确保 bot 在目标聊天中可发言
- 查看 `skills/openclaw-hyperliquid-copytrade/logs/runner.log`

### Q2: 为什么一直 SKIP？
常见原因：
- `KILL_SWITCH=true`
- `SCORE_THRESHOLD` 过高
- 暴露上限命中（单笔或总暴露）

### Q3: 初次启动是否会马上实盘下单？
不会。默认会设置：
- `MODE=dry-run`
- `KILL_SWITCH=true`
- `HL_REAL_EXECUTION=false`

## 5) 安全提醒

- 不要在聊天中发送私钥/token。
- 私密配置只保存在本地 `.env`。
- 上实盘前至少跑 24h dry-run 并人工验收日志。
