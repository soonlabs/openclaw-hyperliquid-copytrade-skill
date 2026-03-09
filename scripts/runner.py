#!/usr/bin/env python3
import os
import time
import json
from statistics import mean
from typing import Dict, List

from hyperliquid_api import extract_open_positions, fetch_user_fills_by_time, normalize_fill_to_event
from live_exec import execute_live_order
from score import WalletStats, score_wallet, size_multiplier
from state import load_state, save_state
from telegram import send_telegram
from telegram_control import poll_yes_no_decision


def load_env_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def get_required(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise ValueError(f"Missing required env: {name}")
    return val


def _realized_metrics_from_rows(rows: List[Dict]) -> Dict:
    pnls = [float(x.get("closedPnl", 0) or 0) for x in rows]
    non_zero = [x for x in pnls if abs(x) > 1e-12]
    realized_trade_count = len(non_zero)
    realized_pnl_sum = sum(non_zero) if non_zero else 0.0
    if non_zero:
        wins = sum(1 for x in non_zero if x > 0)
        realized_win_rate = wins / len(non_zero)
    else:
        realized_win_rate = None
    return {
        "pnls": pnls,
        "non_zero": non_zero,
        "realized_trade_count": realized_trade_count,
        "realized_pnl_sum": realized_pnl_sum,
        "realized_win_rate": realized_win_rate,
    }


def estimate_wallet_stats(wallet: str, lookback_ms: int) -> WalletStats:
    rows = fetch_user_fills_by_time(wallet, lookback_ms)
    if not rows:
        return WalletStats(win_rate=0.5, avg_hold_minutes=120.0, max_drawdown_pct=20.0, recent_win_rate=0.5)

    metrics = _realized_metrics_from_rows(rows)
    pnls = metrics["pnls"]
    non_zero = metrics["non_zero"]
    if non_zero:
        win_rate = float(metrics["realized_win_rate"])
    else:
        win_rate = 0.5

    # Approximation: mean time gap between fills as hold-time proxy.
    times = [int(x.get("time", 0)) for x in rows if x.get("time")]
    times.sort()
    gaps = [max(0, (times[i] - times[i - 1]) / 60000.0) for i in range(1, len(times))]
    avg_hold_minutes = mean(gaps[-100:]) if gaps else 120.0

    # Simple equity curve from realized pnl only.
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        equity += p
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)

    # Normalize to a percentage-like value for score function.
    gross = sum(abs(x) for x in pnls) or 1.0
    max_drawdown_pct = min(100.0, (max_dd / gross) * 100.0)

    recent = non_zero[-30:] if len(non_zero) >= 1 else []
    if recent:
        recent_win_rate = sum(1 for x in recent if x > 0) / len(recent)
    else:
        recent_win_rate = win_rate

    return WalletStats(
        win_rate=win_rate,
        avg_hold_minutes=avg_hold_minutes,
        max_drawdown_pct=max_drawdown_pct,
        recent_win_rate=recent_win_rate,
    )


def build_order_stub(event: Dict, notional_usd: float) -> Dict:
    return {
        "symbol": event["symbol"],
        "side": event["side"],
        "notional_usd": round(notional_usd, 2),
        "source_event": event["event_id"],
    }


def write_runtime_status(path: str, payload: Dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[warn] failed to write runtime status: {e}")


def write_wallet_analytics(path: str, payload: Dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[warn] failed to write wallet analytics: {e}")


def _render_startup_message(lang: str, status_web_url: str, wallets: List[str], summary: str, ask_initial: bool) -> str:
    if lang == "zh":
        base = (
            "🚀 Copytrade 服务已启动\n"
            f"🌐 Web 面板：{status_web_url}\n"
            f"👛 监控钱包：{', '.join(wallets)}\n"
            f"\n📌 当前快照\n{summary}\n"
        )
        if ask_initial:
            base += "\n❓ 请回复 YES / NO：是否立即执行初次跟单？"
        else:
            base += "\nℹ️ 当前没有可跟随持仓，已跳过初次跟单询问。"
        return base

    base = (
        "🚀 Copytrade services started\n"
        f"🌐 Web: {status_web_url}\n"
        f"👛 Monitoring wallet(s): {', '.join(wallets)}\n"
        f"\n📌 Snapshot\n{summary}\n"
    )
    if ask_initial:
        base += "\n❓ Reply YES / NO: execute initial follow now?"
    else:
        base += "\nℹ️ No open positions found, skipping initial follow prompt."
    return base


def _render_decision_ack(lang: str, decision: str) -> str:
    if lang == "zh":
        return f"已收到你的决策：{decision.upper()}。{'将允许初次跟单流程。' if decision == 'yes' else '将跳过初次跟单流程。'}"
    return f"Received decision: {decision.upper()}. {'Will allow initial follow flow.' if decision == 'yes' else 'Will skip initial follow flow.'}"


def _render_missing_wallets_prompt(lang: str) -> str:
    if lang == "zh":
        return (
            "⚠️ 目前还没有配置跟单地址，已暂停启动跟单流程。\n"
            "\n"
            "你可以先到 https://simpfor.fun/ 发现并筛选要跟随的钱包地址。\n"
            "\n"
            "推荐直接在对话里把地址发给我（支持多个，逗号分隔），我会按对话继续帮你完成配置并重启服务。\n"
            "\n"
            "如果你必须手动修改文件，请编辑：/Users/damon/.openclaw/workspace-main/.env\n"
            "并设置 TARGET_WALLETS=<地址1,地址2>，保存后重启服务。"
        )
    return (
        "⚠️ No target wallets configured, so copy-trading startup is paused.\n"
        "\n"
        "You can discover candidate wallets at https://simpfor.fun/.\n"
        "\n"
        "Preferred: send wallet address(es) directly in chat (comma-separated), and I will continue with guided setup + restart.\n"
        "\n"
        "If manual edit is required, update: /Users/damon/.openclaw/workspace-main/.env\n"
        "Set TARGET_WALLETS=<addr1,addr2>, then restart services."
    )


def _render_initial_follow_msg(lang: str, total_positions: int) -> str:
    if lang == "zh":
        return f"🟢 收到 YES。检测到当前持仓 {total_positions} 个，正在执行初次跟单流程。"
    return f"🟢 Initial follow requested (YES). Detected {total_positions} open positions. Executing initial follow flow."


def _render_reason_natural(action: str, score: float, threshold: float, stats: WalletStats, mult: float,
                           current_exposure: float, proposed_exposure: float, total_cap_pct: float,
                           risk_pct: float, score_ok: bool, risk_ok: bool, exposure_ok: bool,
                           kill_switch: bool, fail_reasons: List[str], close_note: str) -> str:
    action_emoji = {"FOLLOW": "✅", "SKIP": "⏸️", "CLOSE": "🔻"}.get(action, "ℹ️")
    lines = [
        f"{action_emoji} 决策：{action}",
        f"🧠 评分：{score} / 阈值 {threshold}（{'通过' if score_ok else '未通过'}）",
        f"📊 钱包画像：胜率 {stats.win_rate:.2f}｜近期胜率 {stats.recent_win_rate:.2f}｜平均持仓 {stats.avg_hold_minutes:.1f}m｜回撤 {stats.max_drawdown_pct:.1f}%",
        f"⚖️ 仓位倍率：{mult:.3f}",
        f"🛡️ 单笔仓位上限检查：这笔 {proposed_exposure:.2f}% <= 上限 {risk_pct:.2f}%（{'通过' if risk_ok else '未通过'}）",
        f"🧮 总仓位上限检查：当前 {current_exposure:.2f}% + 这笔 {proposed_exposure:.2f}% <= 总上限 {total_cap_pct:.2f}%（{'通过' if exposure_ok else '未通过'}）",
        f"🔒 Kill Switch：{'开启' if kill_switch else '关闭'}",
    ]
    if close_note:
        lines.append(f"🔁 平仓触发：{close_note}")
    if fail_reasons:
        lines.append(f"🚫 未执行原因：{'、'.join(fail_reasons)}")
    else:
        lines.append("🎯 执行条件满足")
    return "\n".join(lines)


def _wallet_snapshot_lines(info: Dict) -> List[str]:
    lines = [
        f"score={info.get('score','n/a')} wr={info.get('win_rate','n/a')} rwr={info.get('recent_win_rate','n/a')} hold={info.get('avg_hold_minutes','n/a')}m dd={info.get('max_drawdown_pct','n/a')}% open_pos={info.get('open_position_count','n/a')}"
    ]
    for p in (info.get("open_positions") or [])[:8]:
        lines.append(
            f"  - {p.get('coin')} {p.get('side')} sz={p.get('size')} entry={p.get('entry_px')} upnl={p.get('unrealized_pnl')}"
        )
    return lines


def _calc_pnl_pct(entry: float, price: float, side: str) -> float:
    if side == "buy":
        return ((price - entry) / entry) * 100.0
    return ((entry - price) / entry) * 100.0


def _normalize_copied_position(copied: Dict) -> Dict | None:
    if not isinstance(copied, dict):
        return None
    try:
        entry = float(copied.get("entry_price"))
        high_px = float(copied.get("high_watermark_price", entry))
        low_px = float(copied.get("low_watermark_price", entry))
    except (TypeError, ValueError):
        return None

    copied["high_watermark_price"] = max(high_px, entry)
    copied["low_watermark_price"] = min(low_px, entry)
    side_cp = str(copied.get("side", "buy"))
    favorable_px = copied["high_watermark_price"] if side_cp == "buy" else copied["low_watermark_price"]
    favorable_pnl = _calc_pnl_pct(entry, favorable_px, side_cp)
    try:
        watermark_pnl = float(copied.get("watermark_pnl_pct", favorable_pnl))
    except (TypeError, ValueError):
        watermark_pnl = favorable_pnl
    copied["watermark_price"] = favorable_px
    copied["watermark_pnl_pct"] = max(watermark_pnl, favorable_pnl)
    return copied


def _collapse_events_by_order(events: List[Dict], processed_order_keys: set[str]) -> List[Dict]:
    by_order: Dict[str, Dict] = {}
    for ev in events:
        rf = ev.get("raw_fill") or {}
        oid = str(rf.get("oid", "na"))
        order_key = f"{ev.get('wallet')}:{ev.get('symbol')}:{ev.get('side')}:{oid}"
        ev["_order_key"] = order_key
        prev = by_order.get(order_key)
        if prev is None or int(ev.get("timestamp", 0)) >= int(prev.get("timestamp", 0)):
            by_order[order_key] = ev
    collapsed = sorted(by_order.values(), key=lambda x: x.get("timestamp", 0))
    return [ev for ev in collapsed if ev.get("_order_key") not in processed_order_keys]


def _evaluate_execution_gates(
    *,
    score: float,
    threshold: float,
    proposed_exposure: float,
    current_exposure: float,
    risk_pct: float,
    total_cap_pct: float,
    kill_switch: bool,
) -> Dict:
    score_ok = score >= threshold
    risk_ok = proposed_exposure <= risk_pct
    exposure_ok = (current_exposure + proposed_exposure) <= total_cap_pct
    can_execute = (not kill_switch) and score_ok and risk_ok and exposure_ok
    fail_reasons: List[str] = []
    if kill_switch:
        fail_reasons.append("kill_switch=true")
    if not score_ok:
        fail_reasons.append(f"score<{threshold}")
    if not risk_ok:
        fail_reasons.append(f"proposed_exposure>{risk_pct}%")
    if not exposure_ok:
        fail_reasons.append(f"total_exposure>{total_cap_pct}%")
    return {
        "score_ok": score_ok,
        "risk_ok": risk_ok,
        "exposure_ok": exposure_ok,
        "can_execute": can_execute,
        "fail_reasons": fail_reasons,
    }


def _apply_follow_exposure(current_exposure: float, proposed_exposure: float) -> float:
    return max(0.0, float(current_exposure) + max(0.0, float(proposed_exposure)))


def _apply_close_exposure(current_exposure: float, copied: Dict, notional: float, capital_usd: float) -> float:
    released_exposure = float(copied.get("exposure_pct", (notional / max(1e-9, capital_usd)) * 100.0) or 0.0)
    return max(0.0, float(current_exposure) - max(0.0, released_exposure))


def _evaluate_tp_sl_trigger(
    copied: Dict,
    price: float,
    auto_tp_pct: float,
    auto_sl_pct: float,
    trailing_tp_enable: bool,
    trailing_tp_callback_pct: float,
) -> tuple[str | None, str]:
    entry = float(copied.get("entry_price"))
    side_cp = str(copied.get("side", "buy"))
    px = float(price)
    pnl_pct = _calc_pnl_pct(entry, px, side_cp)

    high_px = max(float(copied.get("high_watermark_price", entry)), px)
    low_px = min(float(copied.get("low_watermark_price", entry)), px)
    copied["high_watermark_price"] = round(high_px, 8)
    copied["low_watermark_price"] = round(low_px, 8)

    favorable_px = high_px if side_cp == "buy" else low_px
    favorable_pnl_pct = _calc_pnl_pct(entry, favorable_px, side_cp)
    watermark_pnl_pct = max(float(copied.get("watermark_pnl_pct", 0.0)), favorable_pnl_pct)
    copied["watermark_price"] = round(favorable_px, 8)
    copied["watermark_pnl_pct"] = round(watermark_pnl_pct, 6)

    retrace_pct = max(0.0, watermark_pnl_pct - pnl_pct)
    watermark_note = f"peak={watermark_pnl_pct:.2f}% current={pnl_pct:.2f}% retrace={retrace_pct:.2f}%"

    tp_sl_trigger = None
    if pnl_pct <= -auto_sl_pct:
        tp_sl_trigger = f"SL hit {pnl_pct:.2f}% <= -{auto_sl_pct:.2f}%"
    elif trailing_tp_enable:
        if watermark_pnl_pct >= auto_tp_pct and retrace_pct >= trailing_tp_callback_pct:
            tp_sl_trigger = (
                f"Trailing TP retrace {retrace_pct:.2f}% >= {trailing_tp_callback_pct:.2f}% "
                f"(peak {watermark_pnl_pct:.2f}% -> now {pnl_pct:.2f}%)"
            )
    elif pnl_pct >= auto_tp_pct:
        tp_sl_trigger = f"TP hit {pnl_pct:.2f}% >= {auto_tp_pct:.2f}%"

    return tp_sl_trigger, watermark_note


def main() -> None:
    load_env_file()

    tg_lang = os.getenv("TG_LANG", "auto").strip().lower()
    lang = "zh" if tg_lang in {"auto", "zh"} else "en"

    target_wallets_raw = os.getenv("TARGET_WALLETS", "")
    wallets = [w.strip().replace(" ", "") for w in target_wallets_raw.split(",") if w.strip()]
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not wallets:
        msg = _render_missing_wallets_prompt(lang)
        print(msg)
        if bot_token and chat_id:
            try:
                send_telegram(bot_token, chat_id, msg)
            except Exception as e:
                print(f"telegram missing-wallet prompt error: {e}")
        return

    mode = os.getenv("MODE", "dry-run")
    kill_switch = os.getenv("KILL_SWITCH", "false").lower() in {"1", "true", "yes", "on"}
    max_events_per_cycle = int(os.getenv("MAX_EVENTS_PER_CYCLE", "20"))
    risk_pct = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "10"))
    total_cap_pct = float(os.getenv("MAX_TOTAL_EXPOSURE_PCT", "60"))
    auto_tp_pct = float(os.getenv("AUTO_TP_PCT", "6"))
    auto_sl_pct = float(os.getenv("AUTO_SL_PCT", "3"))
    trailing_tp_enable = os.getenv("TRAILING_TP_ENABLE", "false").lower() in {"1", "true", "yes", "on"}
    trailing_tp_callback_pct = float(os.getenv("TRAILING_TP_CALLBACK_PCT", "1"))
    threshold = float(os.getenv("SCORE_THRESHOLD", "70"))
    if not bot_token:
        raise ValueError("Missing required env: TELEGRAM_BOT_TOKEN")
    if not chat_id:
        raise ValueError("Missing required env: TELEGRAM_CHAT_ID")
    poll_seconds = int(os.getenv("POLL_SECONDS", "5"))
    capital_usd = float(os.getenv("CAPITAL_USD", "1000"))
    state_file = os.getenv("STATE_FILE", "./skills/openclaw-hyperliquid-copytrade/state.json")
    stats_lookback_hours = int(os.getenv("STATS_LOOKBACK_HOURS", "168"))
    live_executor_url = os.getenv("LIVE_EXECUTOR_URL", "").strip()
    live_executor_bearer = os.getenv("LIVE_EXECUTOR_BEARER", "").strip() or None
    runtime_status_file = os.getenv(
        "RUNTIME_STATUS_FILE", "./skills/openclaw-hyperliquid-copytrade/runtime-status.json"
    )
    status_web_url = os.getenv("STATUS_WEB_URL", "http://127.0.0.1:8899")
    require_initial_decision = os.getenv("REQUIRE_INITIAL_DECISION", "true").lower() in {"1", "true", "yes", "on"}
    tg_offset_file = os.getenv("TG_OFFSET_FILE", "./skills/openclaw-hyperliquid-copytrade/tg-offset.json")
    wallet_analytics_file = os.getenv(
        "WALLET_ANALYTICS_FILE", "./skills/openclaw-hyperliquid-copytrade/wallet-analytics.json"
    )
    event_granularity = os.getenv("EVENT_GRANULARITY", "order").strip().lower()  # order|fill
    dedup_window_seconds = int(os.getenv("DECISION_DEDUP_WINDOW_SECONDS", "0"))

    now_ms = int(time.time() * 1000)
    default_cursor = now_ms - 15 * 60 * 1000

    state = load_state(state_file)
    processed = set(state.get("processed_event_ids", []))
    current_exposure = float(state.get("current_exposure_pct", 0.0))
    last_cursor_ms = int(state.get("last_cursor_ms", default_cursor))
    initial_follow_decision = state.get("initial_follow_decision", "pending")
    initial_follow_done = bool(state.get("initial_follow_done", False))
    startup_prompt_sent = bool(state.get("startup_prompt_sent", False))
    force_startup_prompt = os.getenv("FORCE_STARTUP_PROMPT", "false").lower() in {"1", "true", "yes", "on"}
    copied_positions = state.get("copied_positions", {})  # symbol -> {side, entry_price, notional}
    detected_lang = state.get("detected_lang", "zh" if tg_lang == "auto" else tg_lang)
    recent_decision_keys = state.get("recent_decision_keys", {})
    processed_order_keys = set(state.get("processed_order_keys", []))
    for symbol, copied in list(copied_positions.items()):
        normalized = _normalize_copied_position(copied)
        if normalized is None:
            copied_positions.pop(symbol, None)
            continue
        if normalized.get("exposure_pct") is None:
            try:
                inferred = (float(normalized.get("notional", 0) or 0) / max(1e-9, capital_usd)) * 100.0
                normalized["exposure_pct"] = round(max(0.0, inferred), 4)
            except Exception:
                normalized["exposure_pct"] = 0.0
        copied_positions[symbol] = normalized

    if mode == "live" and not live_executor_url:
        raise ValueError("MODE=live requires LIVE_EXECUTOR_URL")
    if trailing_tp_callback_pct <= 0:
        raise ValueError("TRAILING_TP_CALLBACK_PCT must be > 0")

    print(
        f"[copytrade] started mode={mode} wallets={len(wallets)} "
        f"threshold={threshold} kill_switch={kill_switch} trailing_tp={trailing_tp_enable} "
        f"trailing_callback={trailing_tp_callback_pct}"
    )

    write_runtime_status(
        runtime_status_file,
        {
            "started_at": int(time.time()),
            "mode": mode,
            "kill_switch": kill_switch,
            "wallets": wallets,
            "threshold": threshold,
            "trailing_tp_enable": trailing_tp_enable,
            "trailing_tp_callback_pct": trailing_tp_callback_pct,
            "poll_seconds": poll_seconds,
            "event_granularity": event_granularity,
            "status": "running",
            "processed_event_count": len(processed),
            "current_exposure_pct": current_exposure,
            "last_cycle_ts": int(time.time()),
            "last_cycle_new_events": 0,
            "initial_follow_decision": initial_follow_decision,
            "detected_lang": detected_lang,
        },
    )

    startup_lookback_start_ms = int(time.time() * 1000) - stats_lookback_hours * 3600 * 1000
    startup_stats = {}
    for wallet in wallets:
        try:
            rows = fetch_user_fills_by_time(wallet, startup_lookback_start_ms)
            realized_metrics = _realized_metrics_from_rows(rows)
            s = estimate_wallet_stats(wallet, startup_lookback_start_ms)
            startup_score = score_wallet(s)
            positions = extract_open_positions(wallet)
            startup_stats[wallet] = {
                "win_rate": round(s.win_rate, 4),
                "recent_win_rate": round(s.recent_win_rate, 4),
                "avg_hold_minutes": round(s.avg_hold_minutes, 2),
                "max_drawdown_pct": round(s.max_drawdown_pct, 2),
                "score": startup_score,
                "realized_trade_count": realized_metrics["realized_trade_count"],
                "realized_pnl_sum": round(realized_metrics["realized_pnl_sum"], 6),
                "realized_win_rate": (
                    None
                    if realized_metrics["realized_win_rate"] is None
                    else round(float(realized_metrics["realized_win_rate"]), 4)
                ),
                "open_positions": positions,
                "open_position_count": len(positions),
                "open_unrealized_pnl_sum": round(sum(float(p.get("unrealized_pnl", 0) or 0) for p in positions), 6),
            }
        except Exception as e:
            startup_stats[wallet] = {"error": str(e)}

    write_wallet_analytics(
        wallet_analytics_file,
        {
            "updated_at": int(time.time()),
            "wallets": startup_stats,
            "threshold": threshold,
            "mode": mode,
        },
    )

    total_open_positions = sum((startup_stats.get(w, {}) or {}).get("open_position_count", 0) for w in wallets)
    ask_initial = require_initial_decision and total_open_positions > 0

    if require_initial_decision and (force_startup_prompt or not startup_prompt_sent):
        lines = []
        for w, info in startup_stats.items():
            if "error" in info:
                lines.append(f"- {w}: stats error")
            else:
                lines.append(f"- {w}")
                lines.extend(_wallet_snapshot_lines(info))
        summary = "\n".join(lines)
        msg = _render_startup_message(detected_lang, status_web_url, wallets, summary, ask_initial)
        try:
            send_telegram(bot_token, chat_id, msg)
            startup_prompt_sent = True
            state["startup_prompt_sent"] = True
            if not ask_initial:
                state["initial_follow_decision"] = "skipped_no_open_positions"
                state["initial_follow_done"] = True
            save_state(state_file, state)
        except Exception as e:
            print(f"telegram startup prompt error: {e}")

    while True:
        if ask_initial and initial_follow_decision == "pending":
            try:
                decision, _, lang_guess = poll_yes_no_decision(bot_token, chat_id, tg_offset_file)
                if tg_lang == "auto" and lang_guess in {"zh", "en"}:
                    detected_lang = lang_guess
                    state["detected_lang"] = detected_lang
                if decision in {"yes", "no"}:
                    initial_follow_decision = decision
                    state["initial_follow_decision"] = decision
                    save_state(state_file, state)
                    send_telegram(bot_token, chat_id, _render_decision_ack(detected_lang, decision))
            except Exception as e:
                print(f"telegram decision poll error: {e}")

        if ask_initial and initial_follow_decision == "yes" and not initial_follow_done:
            try:
                all_positions = []
                for w in wallets:
                    all_positions.extend((startup_stats.get(w, {}) or {}).get("open_positions", []))

                total_positions = len(all_positions)
                send_telegram(bot_token, chat_id, _render_initial_follow_msg(detected_lang, total_positions))

                if total_positions == 0:
                    send_telegram(bot_token, chat_id, "No open positions found for initial follow.")
                else:
                    # Proportional sizing by source wallet position value share.
                    abs_values = [abs(float(p.get("position_value", 0) or 0)) for p in all_positions]
                    total_abs_value = sum(abs_values)
                    max_initial_notional = capital_usd * (risk_pct / 100.0) * max(1, total_positions)

                    for p in all_positions:
                        pv = abs(float(p.get("position_value", 0) or 0))
                        share = (pv / total_abs_value) if total_abs_value > 0 else (1.0 / total_positions)
                        notional = max_initial_notional * share
                        intent_event = {
                            "event_id": f"initial-follow:{p.get('wallet')}:{p.get('coin')}:{int(time.time())}",
                            "wallet": p.get("wallet"),
                            "symbol": p.get("coin"),
                            "side": "buy" if p.get("side") == "long" else "sell",
                            "size": p.get("size"),
                            "price": p.get("entry_px"),
                            "timestamp": int(time.time()),
                        }

                        if kill_switch:
                            send_telegram(
                                bot_token,
                                chat_id,
                                f"[INITIAL-SKIP] {p.get('coin')} {p.get('side')} kill_switch=true",
                            )
                            continue

                        if mode == "live":
                            try:
                                live_resp = execute_live_order(
                                    intent_event,
                                    notional,
                                    executor_url=live_executor_url,
                                    executor_bearer=live_executor_bearer,
                                )
                                send_telegram(
                                    bot_token,
                                    chat_id,
                                    f"[INITIAL-FOLLOW] {p.get('coin')} {p.get('side')} notional={round(notional,2)} share={round(share,4)} resp={live_resp}",
                                )
                            except Exception as e:
                                send_telegram(
                                    bot_token,
                                    chat_id,
                                    f"[INITIAL-FAILED] {p.get('coin')} {p.get('side')} error={e}",
                                )
                        else:
                            send_telegram(
                                bot_token,
                                chat_id,
                                f"[INITIAL-DRYRUN] {p.get('coin')} {p.get('side')} notional={round(notional,2)} share={round(share,4)}",
                            )

                initial_follow_done = True
                state["initial_follow_done"] = True
                save_state(state_file, state)
            except Exception as e:
                print(f"telegram initial-follow ack error: {e}")

        start_ms = max(0, last_cursor_ms - 3000)
        latest_seen_ms = last_cursor_ms
        new_events: List[Dict] = []

        for wallet in wallets:
            try:
                fills = fetch_user_fills_by_time(wallet, start_ms)
            except Exception as e:
                print(f"[warn] fetch fills failed wallet={wallet}: {e}")
                continue

            for fill in fills:
                event = normalize_fill_to_event(fill, wallet)
                eid = event["event_id"]
                if eid in processed:
                    continue
                new_events.append(event)
                raw_ms = int(fill.get("time", 0) or 0)
                latest_seen_ms = max(latest_seen_ms, raw_ms)

        new_events.sort(key=lambda x: x.get("timestamp", 0))
        if len(new_events) > max_events_per_cycle:
            new_events = new_events[-max_events_per_cycle:]

        # Optional order-level aggregation: keep one decision per order (oid) instead of per fill.
        if event_granularity == "order":
            new_events = _collapse_events_by_order(new_events, processed_order_keys)

        if not new_events:
            state["last_cursor_ms"] = latest_seen_ms
            state["copied_positions"] = copied_positions
            cutoff_ts = int(time.time()) - max(60, dedup_window_seconds * 10)
            recent_decision_keys = {
                k: int(v) for k, v in recent_decision_keys.items() if int(v or 0) >= cutoff_ts
            }
            state["recent_decision_keys"] = recent_decision_keys
            state["processed_order_keys"] = list(processed_order_keys)[-20000:]
            save_state(state_file, state)
            write_runtime_status(
                runtime_status_file,
                {
                    "started_at": int(time.time()),
                    "mode": mode,
                    "kill_switch": kill_switch,
                    "wallets": wallets,
                    "threshold": threshold,
                    "trailing_tp_enable": trailing_tp_enable,
                    "trailing_tp_callback_pct": trailing_tp_callback_pct,
                    "poll_seconds": poll_seconds,
                    "event_granularity": event_granularity,
                    "status": "running",
                    "processed_event_count": len(processed),
                    "current_exposure_pct": round(current_exposure, 4),
                    "last_cycle_ts": int(time.time()),
                    "last_cycle_new_events": 0,
                    "initial_follow_decision": initial_follow_decision,
                    "initial_follow_done": initial_follow_done,
                    "detected_lang": detected_lang,
                },
            )
            time.sleep(poll_seconds)
            continue

        stats_cache: Dict[str, WalletStats] = {}
        lookback_start_ms = int(time.time() * 1000) - stats_lookback_hours * 3600 * 1000

        # Refresh analytics snapshot for all monitored wallets.
        analytics_payload = {"updated_at": int(time.time()), "wallets": {}, "threshold": threshold, "mode": mode}
        for w in wallets:
            try:
                rows = fetch_user_fills_by_time(w, lookback_start_ms)
                realized_metrics = _realized_metrics_from_rows(rows)
                ws = estimate_wallet_stats(w, lookback_start_ms)
                positions = extract_open_positions(w)
                analytics_payload["wallets"][w] = {
                    "win_rate": round(ws.win_rate, 4),
                    "recent_win_rate": round(ws.recent_win_rate, 4),
                    "avg_hold_minutes": round(ws.avg_hold_minutes, 2),
                    "max_drawdown_pct": round(ws.max_drawdown_pct, 2),
                    "score": score_wallet(ws),
                    "realized_trade_count": realized_metrics["realized_trade_count"],
                    "realized_pnl_sum": round(realized_metrics["realized_pnl_sum"], 6),
                    "realized_win_rate": (
                        None
                        if realized_metrics["realized_win_rate"] is None
                        else round(float(realized_metrics["realized_win_rate"]), 4)
                    ),
                    "open_positions": positions,
                    "open_position_count": len(positions),
                    "open_unrealized_pnl_sum": round(sum(float(p.get("unrealized_pnl", 0) or 0) for p in positions), 6),
                }
            except Exception as e:
                analytics_payload["wallets"][w] = {"error": str(e)}
        write_wallet_analytics(wallet_analytics_file, analytics_payload)

        for event in new_events:
            eid = event["event_id"]
            wallet = event["wallet"]

            event_ts = int(event.get("timestamp", int(time.time())))
            dedup_key = f"{wallet}:{event.get('symbol')}:{event.get('side')}"
            last_seen_ts = int(recent_decision_keys.get(dedup_key, 0) or 0)
            if event_granularity == "fill" and dedup_window_seconds > 0 and last_seen_ts and (event_ts - last_seen_ts) <= dedup_window_seconds:
                processed.add(eid)
                continue

            if wallet not in stats_cache:
                stats_cache[wallet] = estimate_wallet_stats(wallet, lookback_start_ms)

            stats = stats_cache[wallet]
            score = score_wallet(stats)
            mult = size_multiplier(score, threshold)
            proposed_exposure = risk_pct * mult

            symbol = str(event.get("symbol"))
            src_dir = str((event.get("raw_fill") or {}).get("dir", ""))
            is_source_close = "close" in src_dir.lower()
            copied = copied_positions.get(symbol)

            # Auto risk close checks for existing copied position.
            tp_sl_trigger = None
            watermark_note = ""
            if copied and copied.get("entry_price") and event.get("price"):
                tp_sl_trigger, watermark_note = _evaluate_tp_sl_trigger(
                    copied=copied,
                    price=float(event.get("price")),
                    auto_tp_pct=auto_tp_pct,
                    auto_sl_pct=auto_sl_pct,
                    trailing_tp_enable=trailing_tp_enable,
                    trailing_tp_callback_pct=trailing_tp_callback_pct,
                )

            should_close = bool(copied and (is_source_close or tp_sl_trigger))

            gates = _evaluate_execution_gates(
                score=score,
                threshold=threshold,
                proposed_exposure=proposed_exposure,
                current_exposure=current_exposure,
                risk_pct=risk_pct,
                total_cap_pct=total_cap_pct,
                kill_switch=kill_switch,
            )
            score_ok = gates["score_ok"]
            risk_ok = gates["risk_ok"]
            exposure_ok = gates["exposure_ok"]
            can_execute = gates["can_execute"]

            action = "CLOSE" if should_close else ("FOLLOW" if can_execute else "SKIP")
            fail_reasons = gates["fail_reasons"]

            close_note = f"source_close={is_source_close}, tp_sl={tp_sl_trigger}"
            if watermark_note:
                close_note = f"{close_note}, {watermark_note}"
            reason = _render_reason_natural(
                action=action,
                score=score,
                threshold=threshold,
                stats=stats,
                mult=mult,
                current_exposure=current_exposure,
                proposed_exposure=proposed_exposure,
                total_cap_pct=total_cap_pct,
                risk_pct=risk_pct,
                score_ok=score_ok,
                risk_ok=risk_ok,
                exposure_ok=exposure_ok,
                kill_switch=kill_switch,
                fail_reasons=fail_reasons,
                close_note=close_note,
            )

            if should_close:
                notional = float(copied.get("notional", capital_usd * (risk_pct / 100.0)))
                close_side = "sell" if copied.get("side") == "buy" else "buy"
                close_event = dict(event)
                close_event["side"] = close_side
                order = build_order_stub(close_event, notional)
                order["close_reason"] = "source_close" if is_source_close else tp_sl_trigger
                if mode == "live" and not kill_switch:
                    try:
                        live_resp = execute_live_order(
                            close_event,
                            notional,
                            executor_url=live_executor_url,
                            executor_bearer=live_executor_bearer,
                        )
                        order["live_status"] = "SENT"
                        order["live_response"] = live_resp
                    except Exception as e:
                        order["live_status"] = "FAILED"
                        order["live_error"] = str(e)
                current_exposure = _apply_close_exposure(
                    current_exposure=current_exposure,
                    copied=copied,
                    notional=notional,
                    capital_usd=capital_usd,
                )
                copied_positions.pop(symbol, None)
            elif can_execute:
                notional = capital_usd * (risk_pct / 100.0) * mult
                order = build_order_stub(event, notional)
                if mode == "live":
                    try:
                        live_resp = execute_live_order(
                            event,
                            notional,
                            executor_url=live_executor_url,
                            executor_bearer=live_executor_bearer,
                        )
                        order["live_status"] = "SENT"
                        order["live_response"] = live_resp
                    except Exception as e:
                        order["live_status"] = "FAILED"
                        order["live_error"] = str(e)
                current_exposure = _apply_follow_exposure(current_exposure, proposed_exposure)
                copied_positions[symbol] = {
                    "side": event.get("side"),
                    "entry_price": event.get("price"),
                    "notional": round(notional, 2),
                    "exposure_pct": round(proposed_exposure, 4),
                    "high_watermark_price": event.get("price"),
                    "low_watermark_price": event.get("price"),
                    "watermark_price": event.get("price"),
                    "watermark_pnl_pct": 0.0,
                }
            else:
                order = None

            msg = (
                f"📍 标的：{event['symbol']} {event['side']}\n"
                f"👛 钱包：{wallet}\n"
                f"⚙️ 模式：{mode}\n"
                f"\n{reason}\n"
                f"\n🧾 执行回执：{order}"
            )
            try:
                send_telegram(bot_token, chat_id, msg)
            except Exception as e:
                print(f"telegram error: {e}")

            recent_decision_keys[dedup_key] = event_ts
            if event_granularity == "order":
                processed_order_keys.add(event.get("_order_key", f"{wallet}:{event.get('symbol')}:{event.get('side')}:{eid}"))
            processed.add(eid)

        state["processed_event_ids"] = list(processed)[-10000:]
        state["current_exposure_pct"] = round(current_exposure, 4)
        state["last_cursor_ms"] = latest_seen_ms
        state["copied_positions"] = copied_positions
        cutoff_ts = int(time.time()) - max(60, dedup_window_seconds * 10)
        recent_decision_keys = {
            k: int(v) for k, v in recent_decision_keys.items() if int(v or 0) >= cutoff_ts
        }
        state["recent_decision_keys"] = recent_decision_keys
        state["processed_order_keys"] = list(processed_order_keys)[-20000:]
        save_state(state_file, state)
        write_runtime_status(
            runtime_status_file,
            {
                "started_at": int(time.time()),
                "mode": mode,
                "kill_switch": kill_switch,
                "wallets": wallets,
                "threshold": threshold,
                "trailing_tp_enable": trailing_tp_enable,
                "trailing_tp_callback_pct": trailing_tp_callback_pct,
                "poll_seconds": poll_seconds,
                "event_granularity": event_granularity,
                "status": "running",
                "processed_event_count": len(processed),
                "current_exposure_pct": round(current_exposure, 4),
                "last_cycle_ts": int(time.time()),
                "last_cycle_new_events": len(new_events),
                "initial_follow_decision": initial_follow_decision,
                "initial_follow_done": initial_follow_done,
                "detected_lang": detected_lang,
            },
        )

        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
