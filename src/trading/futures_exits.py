import logging
from dataclasses import dataclass

from src.config.config import CONTRACT_CONFIG
from src.trading.futures_helpers import close_futures_position


@dataclass
class FuturesExitResult:
    closed: bool = False
    current_position: dict = None


def handle_futures_exit(account, symbol, current_position, price, strategy, leverage):
    """检查并执行止盈或强制平仓。"""
    if not current_position or current_position['size'] == 0:
        return FuturesExitResult(current_position=current_position)

    entry_price = current_position['entry_price']
    margin_used = CONTRACT_CONFIG["fixed_margin"]
    current_pnl_pct_vs_margin = current_position['unrealized_pnl'] / margin_used

    if current_pnl_pct_vs_margin >= strategy.take_profit:
        print(f"🎯 止盈触发! 收益率: {current_pnl_pct_vs_margin*100:.2f}% | 盈亏: {current_position['unrealized_pnl']:.2f}USDT")
        _log_exit_reason("🎯", "止盈平仓", entry_price, price, current_position, current_pnl_pct_vs_margin, strategy, leverage, margin_used)
        return _close_position(account, symbol, current_position, "止盈平仓")

    if current_pnl_pct_vs_margin <= -1.0:
        print(f"🛑 强制平仓! 亏损: {current_pnl_pct_vs_margin*100:.2f}% | 盈亏: {current_position['unrealized_pnl']:.2f}USDT")
        _log_exit_reason("🛑", "强制平仓", entry_price, price, current_position, current_pnl_pct_vs_margin, strategy, leverage, margin_used)
        return _close_position(account, symbol, current_position, "强制平仓")

    return FuturesExitResult(current_position=current_position)


def _log_exit_reason(icon, exit_type, entry_price, price, current_position, pnl_pct, strategy, leverage, margin_used):
    logging.info(f"{icon} {exit_type}触发")
    logging.info(f"📊 {exit_type}原因分析:")
    logging.info(f"  - 平仓类型: {exit_type}")
    logging.info(f"  - 入场价格: {entry_price:.2f} USDT")
    logging.info(f"  - 当前价格: {price:.2f} USDT")
    logging.info(f"  - 持仓数量: {current_position['size']:.4f} 张")
    logging.info(f"  - 未实现盈亏: {current_position['unrealized_pnl']:.2f} USDT")
    if exit_type == "止盈平仓":
        logging.info(f"  - 保证金收益率: {pnl_pct*100:.2f}%")
        logging.info(f"  - 止盈阈值: {strategy.take_profit*100:.1f}%")
    else:
        logging.info(f"  - 保证金亏损率: {pnl_pct*100:.2f}%")
        logging.info("  - 强制平仓阈值: -100%")
    logging.info(f"  - 杠杆倍数: {leverage}x")
    logging.info(f"  - 保证金: {margin_used:.2f} USDT")
    if exit_type == "强制平仓":
        logging.info("  - 风险等级: 极高 (亏损超过保证金)")


def _close_position(account, symbol, current_position, exit_type):
    try:
        close_futures_position(account, symbol, current_position)
        logging.info(f"✅ {exit_type}执行成功")
        return FuturesExitResult(closed=True, current_position=None)
    except Exception as exc:
        print(f"❌ {exit_type}失败: {str(exc)}")
        logging.error(f"❌ {exit_type}执行失败: {str(exc)}")
        return FuturesExitResult(current_position=current_position)
