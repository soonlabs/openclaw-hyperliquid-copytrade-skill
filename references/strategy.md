# Strategy Notes

## Decision score (0-100)

Weighted components:

- Win rate (35%)
- Risk-adjusted hold quality (20%)
- Max drawdown penalty (25%)
- Recency momentum (20%)

## Suggested formulas

- `win_component = clamp(win_rate, 0, 1) * 100`
- `hold_component = exp(-abs(avg_hold_min - target_hold_min)/target_hold_min) * 100`
- `dd_component = max(0, 100 - (max_drawdown_pct * 2))`
- `recency_component = clamp(recent_win_rate, 0, 1) * 100`

Final:

`score = 0.35*win + 0.20*hold + 0.25*dd + 0.20*recency`

## Execute only if

- `score >= SCORE_THRESHOLD`
- `risk_per_trade_pct <= MAX_RISK_PER_TRADE_PCT`
- `current_exposure_pct + proposed_exposure_pct <= MAX_TOTAL_EXPOSURE_PCT`

## Position sizing

Use confidence multiplier:

`size_multiplier = clamp((score - threshold) / (100 - threshold), 0.1, 1.0)`

Proposed notional:

`notional = capital_usd * (max_risk_pct/100) * size_multiplier`

## Telegram rationale template

- Action: FOLLOW / SKIP
- Wallet
- Symbol / side
- Score + threshold
- Risk checks: per-trade + total exposure
- Reason summary (one sentence)
