# Architecture

## Overview

`openclaw-hyperliquid-copytrade` is a local copy-trading pipeline with explainable decisions and Telegram-first visibility.

Flow:

1. `runner.py` polls source wallet fills from Hyperliquid (`/info`-style data via `hyperliquid_api.py`).
2. Runner computes wallet stats and score (`score.py`).
3. Runner applies risk constraints and decides `FOLLOW` / `SKIP` / `CLOSE`.
4. Decision is sent to Telegram (`telegram.py`) with a human-readable rationale.
5. If execution is enabled, runner calls executor endpoint through `live_exec.py`.
6. Runtime snapshots are persisted (`state.py`, `runtime-status.json`, `wallet-analytics.json`) and shown in `status_web.py`.

## Components

- `scripts/runner.py`
  - Main loop and decision engine.
  - Startup Telegram snapshot and initial YES/NO follow flow.
  - Risk checks, TP/SL auto-close, source close mirror.
- `scripts/hyperliquid_api.py`
  - Hyperliquid data fetch + fill normalization.
- `scripts/score.py`
  - Wallet scoring and size multiplier logic.
- `scripts/live_exec.py`
  - Client bridge to execution service.
- `scripts/live_executor_service_stdlib.py`
  - Dependency-light local execution endpoint (`/execute`).
- `scripts/telegram.py`
  - Telegram send wrapper.
- `scripts/telegram_control.py`
  - Polls incoming YES/NO replies and language hint.
- `scripts/status_web.py`
  - Local dashboard for runtime status and wallet analytics.
- `scripts/manage_services.py`
  - One-click `start|stop|status|restart` process control.

## Runtime files

- `state.json`: processed event IDs, exposure, startup prompt flags, copied positions.
- `runtime-status.json`: heartbeat snapshot for dashboard.
- `wallet-analytics.json`: per-wallet score/stats and open-position snapshot.
- `services-pids.json`: process PIDs for service management.
- `logs/*.log`: executor, status web, runner logs.

## Decision lifecycle

For each new normalized fill event:

1. Load (or refresh) wallet stats over `STATS_LOOKBACK_HOURS`.
2. Compute `score` and `size_multiplier`.
3. Calculate proposed exposure.
4. Evaluate gates:
   - score threshold
   - per-trade exposure cap
   - total exposure cap
   - kill switch
5. If copied position exists, evaluate close triggers:
   - source close event
   - TP/SL thresholds
6. Emit Telegram rationale and execution receipt.
7. Persist state and runtime snapshot.

## Default runtime profile

Ready-to-use defaults:

- `MODE=live`
- `KILL_SWITCH=false`
- `HL_REAL_EXECUTION=true`

This enables live decision/execution flow with real order placement at startup. If you want simulation-first behavior, switch to `MODE=dry-run` or `HL_REAL_EXECUTION=false` manually.
