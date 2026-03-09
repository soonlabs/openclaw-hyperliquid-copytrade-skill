from dataclasses import dataclass


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class WalletStats:
    win_rate: float
    avg_hold_minutes: float
    max_drawdown_pct: float
    recent_win_rate: float


def score_wallet(stats: WalletStats, target_hold_min: float = 120.0) -> float:
    win = clamp(stats.win_rate, 0.0, 1.0) * 100
    hold = pow(2.718281828, -abs(stats.avg_hold_minutes - target_hold_min) / max(target_hold_min, 1)) * 100
    dd = max(0.0, 100 - (stats.max_drawdown_pct * 2))
    recency = clamp(stats.recent_win_rate, 0.0, 1.0) * 100

    score = 0.35 * win + 0.20 * hold + 0.25 * dd + 0.20 * recency
    return round(clamp(score, 0.0, 100.0), 2)


def size_multiplier(score: float, threshold: float) -> float:
    if score < threshold:
        return 0.0
    if threshold >= 100:
        return 0.1
    raw = (score - threshold) / (100 - threshold)
    return round(clamp(raw, 0.1, 1.0), 4)
