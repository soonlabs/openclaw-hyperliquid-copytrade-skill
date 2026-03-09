# 首次下载 Skill：一键接入指南

目标：让第一次下载本 skill 的用户在 3 分钟内跑起来（安全默认：仅 dry-run）。

## 前置要求

- 已安装 Python 3
- 当前目录位于 OpenClaw workspace 根目录
- Telegram 已创建 bot（拿到 Token）

## 一键命令

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/first_run_onboarding.py --start
```

执行后你会被引导输入：
- `TARGET_WALLETS`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

然后自动：
- 写入/更新 `.env`
- 应用安全默认值
- 启动服务

## 验证是否接入成功

1. 终端看到 `services started` 或 `running(pid)`
2. 打开 `http://127.0.0.1:8899` 看状态页
3. Telegram 收到启动快照消息

## 常见失败处理

### 1) 缺少必填配置
再次运行向导：
```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/first_run_onboarding.py
```

### 2) 服务启动失败
查看日志：
- `skills/openclaw-hyperliquid-copytrade/logs/runner.log`
- `skills/openclaw-hyperliquid-copytrade/logs/executor.log`
- `skills/openclaw-hyperliquid-copytrade/logs/status_web.log`

### 3) Telegram 无消息
确认 bot token/chat id 正确，且 bot 已在目标聊天中发过/收过消息。

## 下一步（推荐）

- 先保持 dry-run 观察一天
- 校验 SKIP/FOLLOW 原因是否符合预期
- 再决定是否切换 live
