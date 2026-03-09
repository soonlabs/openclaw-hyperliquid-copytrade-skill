# Hyperliquid Integration Notes

This skill now reads real source-wallet fills via Hyperliquid `/info` (`userFillsByTime`) in polling mode.

## Event source

Current implementation:

- Poll `/info` with `type=userFillsByTime`
- Normalize each fill into a copytrade event
- Deduplicate with persisted `processed_event_ids`

Optional upgrade:

- Replace polling with websocket `userFills` subscriptions for lower latency

Expected normalized event shape:

```json
{
  "event_id": "unique-source-id",
  "wallet": "0x...",
  "symbol": "BTC",
  "side": "buy",
  "size": 0.1,
  "price": 70000,
  "timestamp": 1730000000
}
```

## Historical analytics

For each source wallet, compute:

- win_rate
- avg_hold_minutes
- max_drawdown_pct
- recent_win_rate

Return this object to `score_wallet()`.

## Order execution

Current live path forwards order intents to an external signer/executor via `LIVE_EXECUTOR_URL`.

The runner sends:

- symbol
- side
- notional_usd
- source_event_id
- source_wallet
- source_price / size / timestamp

Your executor service is responsible for:

- wallet key management
- Hyperliquid signed `/exchange` requests
- retries / idempotency / final status

Starter services included:

1) `scripts/live_executor_service.py` (FastAPI)
2) `scripts/live_executor_service_stdlib.py` (no external dependencies)

Both expose:

- `GET /health`
- `POST /execute`
- optional bearer auth via `EXECUTOR_BEARER`

Run locally (dependency-free path):

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/live_executor_service_stdlib.py
```

Real execution mode (signed market orders):

- set `HL_REAL_EXECUTION=true`
- set `HL_WALLET_PRIVATE_KEY` (keep only in local `.env`)
- keep `HL_API_URL=https://api.hyperliquid.xyz`
- optional: tune `HL_MARKET_SLIPPAGE`

One-click service control:

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py start
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py status
python3 skills/openclaw-hyperliquid-copytrade/scripts/manage_services.py stop
```

Startup Telegram flow:

- Runner sends startup message with web URL and monitored wallet list.
- It asks for `YES` / `NO` (also supports `是/否/好/不要`) to decide initial-follow flow.
- Telegram language can be forced by `TG_LANG=zh|en`, or auto-detected with `TG_LANG=auto`.
- Auto mode prioritizes Telegram `from.language_code` (e.g. `zh-CN`, `en-US`), then falls back to text detection.
- Decision is read via Telegram `getUpdates` and persisted in state.
- On `YES`, runner executes initial-follow intents from current open positions (live mode calls executor; dry-run sends simulation messages).
- Initial-follow notional is split proportionally by each source position's absolute `position_value` share.
- Auto-close supports: (1) source close mirror, (2) local TP/SL (`AUTO_TP_PCT`, `AUTO_SL_PCT`), (3) optional trailing TP retrace (`TRAILING_TP_ENABLE`, `TRAILING_TP_CALLBACK_PCT`) with persisted per-position watermark state.

Status web (optional):

```bash
python3 skills/openclaw-hyperliquid-copytrade/scripts/status_web.py
# open http://127.0.0.1:8899
```

Then set in `.env`:

```env
LIVE_EXECUTOR_URL=http://127.0.0.1:8787/execute
LIVE_EXECUTOR_BEARER=your_shared_secret
```

Mandatory safeguards:

- Per-trade cap
- Total exposure cap
- Symbol allowlist/blocklist
- Kill switch env var (`KILL_SWITCH=true`)

## Reliability checklist

- Reconnect websocket automatically
- Persist processed event ids
- Use monotonic timestamps for backoff
- Send alert when stream is stale > 60s
