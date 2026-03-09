# Risk Policy

## Purpose

Define guardrails for copy-trading decisions so that follow sizing and close behavior remain bounded and explainable.

## Core controls

- Per-trade risk cap: `MAX_RISK_PER_TRADE_PCT`
- Total exposure cap: `MAX_TOTAL_EXPOSURE_PCT`
- Score gate: `SCORE_THRESHOLD`
- Global kill switch: `KILL_SWITCH`

A trade is executable only when all gates pass (and not kill-switched).

## Decision gates

For each event, runner computes:

- `score = score_wallet(stats)`
- `mult = size_multiplier(score, threshold)`
- `proposed_exposure_pct = MAX_RISK_PER_TRADE_PCT * mult`

Execution gates:

1. `score >= SCORE_THRESHOLD`
2. `proposed_exposure_pct <= MAX_RISK_PER_TRADE_PCT`
3. `current_exposure_pct + proposed_exposure_pct <= MAX_TOTAL_EXPOSURE_PCT`
4. `KILL_SWITCH` must be false

If any gate fails, action is `SKIP` with explicit reasons in Telegram message.

## Initial-follow policy

At startup, if `REQUIRE_INITIAL_DECISION=true` and open positions exist:

- System asks operator to reply `YES/NO`.
- `YES`: perform initial follow from current source open positions.
- `NO`: skip initial follow.

Sizing for initial follow is proportional to source position value share, bounded by risk budget.

## Close policy

When a copied position exists, close can be triggered by:

1. Source close mirror (`dir` indicates close)
2. Trailing take-profit retrace after TP activation:
   - enable with `TRAILING_TP_ENABLE=true`
   - activate trailing only after profit reaches `AUTO_TP_PCT`
   - close when retrace from position watermark exceeds `TRAILING_TP_CALLBACK_PCT`
3. Auto take-profit (`AUTO_TP_PCT`) when trailing is disabled
4. Auto stop-loss (`AUTO_SL_PCT`)

Runner persists per-position watermark state (`high_watermark_price`, `low_watermark_price`, `watermark_pnl_pct`) in `state.json` so trailing logic survives restarts.

Close-side is opposite of copied side. Close reason (including trailing retrace details) is included in execution receipt.

## Mode policy

- `MODE=dry-run`: no live order submission; still emits full rationale and receipts.
- `MODE=live`: requires executor URL and should only be enabled after dry-run stability checks.

## Recommended operational posture

### Default / ready-to-use

- `MODE=live`
- `KILL_SWITCH=false`
- `HL_REAL_EXECUTION=true`

### Safety override

If you want simulation-first behavior, set `HL_REAL_EXECUTION=false` or `MODE=dry-run` manually before start.
- no duplicate execution behavior
- exposure math verified under stress
- stop/restart tested
- Telegram rationale quality accepted
