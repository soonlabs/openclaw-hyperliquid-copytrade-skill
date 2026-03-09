# Telegram Message Format

## Message types

## 1) Startup snapshot

Sent on service startup (or forced startup prompt). Includes:

- web dashboard URL
- monitored wallets
- wallet snapshot block (score / win-rate / hold-time / drawdown / open positions)
- initial-follow prompt when applicable

Example:

```text
🚀 Copytrade services started
🌐 Web: http://127.0.0.1:8899
👛 Monitoring wallet(s): 0x...

📌 Snapshot
- 0x...
score=78 wr=0.63 rwr=0.70 hold=95.5m dd=12.3% open_pos=2
  - BTC long sz=0.01 entry=62000 upnl=14.2

❓ Reply YES / NO: execute initial follow now?
```

No-open-position variant ends with:

```text
ℹ️ No open positions found, skipping initial follow prompt.
```

## 2) Decision acknowledgement

When operator replies `YES/NO` for initial follow:

```text
Received decision: YES. Will allow initial follow flow.
```

## 3) Initial-follow execution logs

Per startup position:

- dry-run: `[INITIAL-DRYRUN] ...`
- live sent: `[INITIAL-FOLLOW] ... resp=...`
- live failed: `[INITIAL-FAILED] ... error=...`
- blocked by kill switch: `[INITIAL-SKIP] ... kill_switch=true`

## 4) Per-event decision message (core)

Template shape:

```text
📍 Symbol: <symbol> <side>
👛 Wallet: <wallet>
⚙️ Mode: <mode>

<natural-language risk rationale block>

🧾 Execution receipt: <order_or_null>
```

Rationale block includes:

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

- Keep messages mobile-readable.
- Always include explicit skip reasons.
- Keep decision and risk checks on separate lines.
- Never leak secrets (token/private key) into Telegram output.
