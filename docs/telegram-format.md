# Telegram Message Format

## Message types

## 1) Startup snapshot

Sent when service starts (or forced prompt), includes:

- Web panel URL
- monitored wallets
- wallet snapshot block (score/win-rate/hold-time/drawdown/open positions)
- initial-follow prompt when applicable

Chinese example:

```text
🚀 Copytrade 服务已启动
🌐 Web 面板：http://127.0.0.1:8899
👛 监控钱包：0x...

📌 当前快照
- 0x...
score=78 wr=0.63 rwr=0.70 hold=95.5m dd=12.3% open_pos=2
  - BTC long sz=0.01 entry=62000 upnl=14.2

❓ 请回复 YES / NO：是否立即执行初次跟单？
```

No-open-position variant ends with:

```text
ℹ️ 当前没有可跟随持仓，已跳过初次跟单询问。
```

## 2) Decision acknowledgement

When operator replies `YES/NO` for initial follow:

```text
已收到你的决策：YES。将允许初次跟单流程。
```

## 3) Initial follow execution logs

Per startup position:

- dry-run: `[INITIAL-DRYRUN] ...`
- live sent: `[INITIAL-FOLLOW] ... resp=...`
- live failed: `[INITIAL-FAILED] ... error=...`
- blocked by kill switch: `[INITIAL-SKIP] ... kill_switch=true`

## 4) Per-event decision message (core)

Template shape:

```text
📍 标的：<symbol> <side>
👛 钱包：<wallet>
⚙️ 模式：<mode>

<自然语言风控解释块>

🧾 执行回执：<order_or_null>
```

Rationale block currently includes:

- decision (`FOLLOW` / `SKIP` / `CLOSE`)
- score vs threshold
- wallet profile metrics
- sizing multiplier
- per-trade and total exposure checks
- kill switch state
- close trigger note (`source_close` / `TP` / `SL` / `Trailing TP retrace ...`)
- watermark context when copied position exists (`peak/current/retrace`)
- explicit failure reasons when skipped

## Formatting principles

- Prioritize readability on mobile.
- Include explicit skip reasons.
- Keep decision and risk checks on separate lines.
- Do not leak secrets (token/private key) into Telegram output.
