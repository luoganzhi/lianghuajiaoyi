import logging
from datetime import datetime

from src.config.config import CONTRACT_CONFIG


def update_futures_monitor(trade_monitor, symbol, in_position, current_position, price, strategy, leverage, capital):
    """更新交易监控持仓和系统指标。"""
    if in_position and current_position:
        actual_leverage = current_position.get('leverage', leverage)
        if actual_leverage != leverage:
            logging.info(f"⚠️ 杠杆不匹配 - 设置: {leverage}x, 实际: {actual_leverage}x")

        trade_monitor.update_position(symbol, {
            "size": current_position['size'],
            "entry_price": current_position['entry_price'],
            "current_price": price,
            "unrealized_pnl": current_position['unrealized_pnl'],
            "position_type": strategy.position_type,
            "leverage": actual_leverage,
            "margin_mode": strategy.margin_mode
        })
    else:
        trade_monitor.update_position(symbol, {})

    trade_monitor.update_system_metrics({
        "current_capital": capital,
        "initial_capital": capital,
        "drawdown": 0.0,
        "daily_pnl": 0.0,
        "position_count": 1 if in_position else 0,
        "positions": trade_monitor.positions,
        "recent_alerts": [],
        "total_exposure": current_position['size'] * price if in_position and current_position else 0
    })


def log_periodic_runner_state(loop_count, in_position, current_position, price, strategy):
    """定期记录程序状态到日志。"""
    if loop_count % 100 != 0:
        return

    logging.info(f"📊 程序运行状态记录 (循环 {loop_count}):")
    logging.info(f"  - 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"  - 持仓状态: {'有持仓' if in_position else '无持仓'}")
    logging.info(f"  - 当前价格: {price:.2f} USDT")
    if in_position and current_position:
        logging.info(f"  - 持仓详情: {current_position['size']:.4f}张 @ {current_position['entry_price']:.2f} USDT")
        logging.info(f"  - 未实现盈亏: {current_position['unrealized_pnl']:.2f} USDT")
        margin_used = CONTRACT_CONFIG["fixed_margin"]
        pnl_pct = (current_position['unrealized_pnl'] / margin_used) * 100
        logging.info(f"  - 保证金收益率: {pnl_pct:.2f}%")
    logging.info(f"  - 策略状态: {strategy.__class__.__name__}")
    logging.info(f"  - 调试模式: {strategy.debug_mode}")


def display_compact_loop_status(loop_count, in_position, current_position):
    """定期输出简短运行状态。"""
    if loop_count % 30 != 0:
        return

    if in_position and current_position:
        print(f"📊 {datetime.now().strftime('%H:%M:%S')} | 持仓: {current_position['size']:.4f}张 | 盈亏: {current_position['unrealized_pnl']:.2f}USDT")
    else:
        print(f"📊 {datetime.now().strftime('%H:%M:%S')} | 无持仓")
