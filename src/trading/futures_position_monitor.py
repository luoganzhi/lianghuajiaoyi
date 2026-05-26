import logging
import time
from dataclasses import dataclass
from datetime import datetime

from src.config.config import CONTRACT_CONFIG
from src.trading.futures_helpers import (
    check_existing_take_profit_orders,
    get_futures_position,
    set_take_profit_order,
)
from src.trading.futures_status import display_position_monitor_status


@dataclass
class FuturesPositionMonitorResult:
    price: float = 0
    current_position: dict = None
    in_position: bool = True
    last_position_check: float = 0
    last_status_display: float = 0
    signal: int = 0
    skip_cycle: bool = False


def monitor_open_position(
    market_data,
    account,
    symbol,
    strategy,
    current_position,
    in_position,
    leverage,
    current_time,
    last_position_check,
    position_check_interval,
    last_status_display,
    status_display_interval,
):
    """有持仓时监控仓位、补止盈并禁止新开仓信号。"""
    if current_time - last_position_check < position_check_interval:
        time.sleep(1)
        return FuturesPositionMonitorResult(
            current_position=current_position,
            in_position=in_position,
            last_position_check=last_position_check,
            last_status_display=last_status_display,
            skip_cycle=True,
        )

    price = _get_monitor_price(market_data, symbol, current_position)

    try:
        current_position, in_position = _sync_open_position(account, symbol, strategy, current_position, in_position)

        ensure_result = _ensure_take_profit_order(account, symbol, current_position, leverage)
        if ensure_result.skip_cycle:
            return FuturesPositionMonitorResult(
                price=price,
                current_position=current_position,
                in_position=in_position,
                last_position_check=last_position_check,
                last_status_display=last_status_display,
                skip_cycle=True,
            )

        last_position_check = current_time
    except Exception as exc:
        logging.warning(f"⚠️ 持仓检查失败: {str(exc)[:100]}")
        time.sleep(1)
        return FuturesPositionMonitorResult(
            price=price,
            current_position=current_position,
            in_position=in_position,
            last_position_check=last_position_check,
            last_status_display=last_status_display,
            skip_cycle=True,
        )

    if current_time - last_status_display >= status_display_interval:
        display_position_monitor_status(price, current_position, strategy, leverage)
        last_status_display = current_time

    print(f"ℹ️ 有持仓状态，跳过信号生成 (in_position={in_position})")
    logging.info(f"ℹ️ 有持仓状态，跳过信号生成 (in_position={in_position})")

    return FuturesPositionMonitorResult(
        price=price,
        current_position=current_position,
        in_position=in_position,
        last_position_check=last_position_check,
        last_status_display=last_status_display,
        signal=0,
    )


def _get_monitor_price(market_data, symbol, current_position):
    try:
        ticker_data = market_data.get_ticker(symbol)
        if ticker_data and 'last' in ticker_data:
            return float(ticker_data['last'])
        return current_position['entry_price'] if current_position else 0
    except Exception:
        return current_position['entry_price'] if current_position else 0


def _sync_open_position(account, symbol, strategy, current_position, in_position):
    current_position = get_futures_position(account, symbol, strategy)

    if current_position is not None:
        previous_in_position = in_position
        if float(current_position.get('size', 0)) == 0:
            in_position = False
            if previous_in_position:
                logging.info("📊 持仓状态变化: 有持仓 -> 无持仓 (持仓数量为0)")
        else:
            in_position = True
            if not previous_in_position:
                logging.info("📊 持仓状态变化: 无持仓 -> 有持仓")

        if previous_in_position != in_position:
            _log_position_state_change(previous_in_position, in_position, current_position)
    else:
        logging.warning(f"⚠️ 持仓查询失败，保持原有状态: {'有持仓' if in_position else '无持仓'}")

    if current_position is None and in_position:
        current_position, in_position = _verify_possible_liquidation(account, symbol, strategy, in_position)

    return current_position, in_position


def _log_position_state_change(previous_in_position, in_position, current_position):
    logging.info("📊 持仓状态变化:")
    logging.info(f"  - 之前状态: {'有持仓' if previous_in_position else '无持仓'}")
    logging.info(f"  - 当前状态: {'有持仓' if in_position else '无持仓'}")
    logging.info(f"  - 变化时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if in_position:
        logging.info(f"  - 持仓详情: {current_position['size']:.4f}张 @ {current_position['entry_price']:.2f} USDT")
    else:
        logging.info("  - 持仓详情: 无持仓 (数量为0)")


def _verify_possible_liquidation(account, symbol, strategy, in_position):
    print("⚠️ 检测到持仓状态变化: 有持仓 -> 无持仓")
    print("🔍 正在验证是否真的被强平...")
    logging.warning("⚠️ 检测到持仓状态变化: 有持仓 -> 无持仓")

    try:
        verification_position = get_futures_position(account, symbol, strategy)
        if verification_position and float(verification_position.get('size', 0)) != 0:
            print("✅ 验证结果: 持仓仍然存在，不是强平")
            logging.info("✅ 验证结果: 持仓仍然存在，不是强平")
            return verification_position, True

        print("⚠️ 验证结果: 确认仓位被强平")
        logging.warning("⚠️ 验证结果: 确认仓位被强平")
        return None, False
    except Exception as exc:
        print(f"⚠️ 验证持仓时出错: {str(exc)}")
        logging.warning(f"⚠️ 验证持仓时出错: {str(exc)}")
        print(f"🔄 验证失败，保持原有持仓状态: {'有持仓' if in_position else '无持仓'}")
        return None, in_position


@dataclass
class TakeProfitEnsureResult:
    skip_cycle: bool = False


def _ensure_take_profit_order(account, symbol, current_position, leverage):
    if not current_position or current_position['size'] == 0:
        return TakeProfitEnsureResult()

    try:
        actual_entry_price = current_position['entry_price']
        actual_position_size = current_position['size']
        position_type = current_position.get('position_type', 'unknown')
        print(f"🔍 持仓信息: size={actual_position_size}, position_type={position_type}")

        margin_take_profit_pct = CONTRACT_CONFIG['take_profit_pct']
        price_take_profit_pct = margin_take_profit_pct / leverage

        if position_type == 'long':
            actual_take_profit_price = actual_entry_price * (1 + price_take_profit_pct)
        elif position_type == 'short':
            actual_take_profit_price = actual_entry_price * (1 - price_take_profit_pct)
        else:
            print(f"❌ 未知的持仓类型: {position_type}")
            return TakeProfitEnsureResult(skip_cycle=True)

        has_existing_tp = check_existing_take_profit_orders(account, symbol)
        if not has_existing_tp:
            print(f"🔧 尝试设置止盈单: {actual_take_profit_price:.2f} USDT")
            print(f"🔍 使用持仓类型: {position_type}")
            tp_order = set_take_profit_order(account, symbol, position_type, actual_position_size, actual_take_profit_price)
            if tp_order:
                print(f"✅ 止盈单设置成功: {actual_take_profit_price:.2f} USDT")
            else:
                print("⚠️ 止盈单设置失败")
        else:
            print("ℹ️ 已存在止盈单，无需重复设置")
    except Exception as exc:
        print(f"⚠️ 止盈单检查/设置异常: {str(exc)}")
        if "reduce-only order can't be in the same trading direction" in str(exc):
            print("ℹ️ 检测到止盈单可能已存在")
        else:
            print("⚠️ 止盈单设置失败，需要手动检查")

    return TakeProfitEnsureResult()
