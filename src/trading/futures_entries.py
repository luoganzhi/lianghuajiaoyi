import logging
import time
from dataclasses import dataclass
from datetime import datetime

from src.config.config import CONTRACT_CONFIG
from src.trading.futures_helpers import (
    calculate_futures_position_size,
    execute_futures_trade,
    get_futures_position,
    set_take_profit_order,
)


@dataclass
class FuturesEntryResult:
    opened: bool = False
    current_position: dict = None
    trading_lock: bool = False
    last_trade_time: float = 0
    skip_cycle: bool = False


def open_futures_position(account, symbol, signal, price, leverage, strategy, trade_monitor, trade_cooldown):
    """根据交易信号执行合约开仓。"""
    if signal == 1:
        side = 'buy'
        direction_name = '做多'
        signal_name = '做多开仓'
        entry_type = 'futures_long_entry'
        take_profit_price_multiplier = 1
    elif signal == -1:
        side = 'sell'
        direction_name = '做空'
        signal_name = '做空开仓'
        entry_type = 'futures_short_entry'
        take_profit_price_multiplier = -1
    else:
        return FuturesEntryResult()

    print(f"\n{'🚀' if signal == 1 else '🔴'} 执行合约{direction_name}开仓...")
    _log_entry_signal(signal, price, strategy, signal_name)

    position_size = calculate_futures_position_size()
    position_value = position_size * price
    margin_take_profit_pct = CONTRACT_CONFIG['take_profit_pct']
    price_take_profit_pct = margin_take_profit_pct / leverage
    take_profit_price = price * (1 + take_profit_price_multiplier * price_take_profit_pct)

    print(f"📊 开仓详情: {position_size:.4f}张 | 价格: {price:.2f} | 止盈: {take_profit_price:.2f} | 保证金: {CONTRACT_CONFIG['fixed_margin']}USDT")
    _log_entry_parameters(position_size, price, take_profit_price, leverage, margin_take_profit_pct, price_take_profit_pct)

    try:
        print(f"🔄 正在执行{direction_name}开仓订单...")
        logging.info(f"🔄 开始执行合约{direction_name}开仓 - 价格: {price:.2f}, 数量: {position_size:.4f}, 杠杆: {leverage}x")

        order = execute_futures_trade(account, symbol, side, position_size, leverage, "market", None)
        if not order:
            print("❌ 开仓失败")
            return FuturesEntryResult()

        print(f"✅ 开仓成功! 订单ID: {order.get('id', 'N/A')}")
        last_trade_time = time.time()
        print(f"🔒 开仓锁已激活，冷却时间: {trade_cooldown}秒")

        current_position = _refresh_position_after_entry(
            account,
            symbol,
            price,
            price_take_profit_pct,
        )

        actual_entry_price = current_position['entry_price'] if current_position else price
        strategy.on_position_entry(side, actual_entry_price, position_size, datetime.now())

        trade_monitor.record_trade({
            "timestamp": datetime.now(),
            "symbol": symbol,
            "side": side,
            "size": position_size,
            "price": actual_entry_price,
            "value": position_value,
            "type": entry_type,
            "leverage": leverage,
            "order_id": order.get("id", ""),
            "status": order.get("status", "")
        })

        print("✅ 已更新持仓状态")
        logging.info("✅ 已更新持仓状态")
        return FuturesEntryResult(
            opened=True,
            current_position=current_position,
            trading_lock=True,
            last_trade_time=last_trade_time,
        )

    except Exception as exc:
        print(f"❌ 开仓失败: {str(exc)}")
        return FuturesEntryResult(skip_cycle=True)


def _log_entry_signal(signal, price, strategy, signal_name):
    logging.info(f"🎯 开仓信号触发 - {signal_name}")
    logging.info("📊 开仓原因分析:")
    logging.info(f"  - 策略信号: {signal}")
    logging.info(f"  - 当前价格: {price:.2f} USDT")
    logging.info(f"  - 策略类型: {strategy.__class__.__name__}")
    logging.info(f"  - 调试模式: {strategy.debug_mode}")


def _log_entry_parameters(position_size, price, take_profit_price, leverage, margin_take_profit_pct, price_take_profit_pct):
    logging.info("📊 开仓参数详情:")
    logging.info(f"  - 合约数量: {position_size:.4f} 张")
    logging.info(f"  - 开仓价格: {price:.2f} USDT")
    logging.info(f"  - 止盈价格: {take_profit_price:.2f} USDT")
    logging.info(f"  - 杠杆倍数: {leverage}x")
    logging.info(f"  - 保证金: {CONTRACT_CONFIG['fixed_margin']} USDT")
    logging.info(f"  - 保证金止盈比例: {margin_take_profit_pct*100:.1f}%")
    logging.info(f"  - 价格止盈比例: {price_take_profit_pct*100:.3f}%")


def _refresh_position_after_entry(account, symbol, price, price_take_profit_pct):
    time.sleep(2)
    try:
        current_position = get_futures_position(account, symbol)
        if not current_position:
            print("⚠️ 无法获取持仓信息")
            return None

        actual_entry_price = current_position['entry_price']
        actual_position_size = current_position['size']

        if actual_position_size > 0:
            actual_take_profit_price = actual_entry_price * (1 + price_take_profit_pct)
        else:
            actual_take_profit_price = actual_entry_price * (1 - price_take_profit_pct)

        try:
            position_type = 'long' if actual_position_size > 0 else 'short'
            tp_order = set_take_profit_order(account, symbol, position_type, actual_position_size, actual_take_profit_price)
            if tp_order:
                print(f"✅ 止盈设置: {actual_take_profit_price:.2f}")
            else:
                print("⚠️ 止盈设置失败")
        except Exception as exc:
            print(f"⚠️ 止盈设置失败: {str(exc)}")

        if abs(price - actual_entry_price) > 10:
            print("⚠️ 开仓价格与实际入场价格差异较大!")
        else:
            print("✅ 开仓价格与实际入场价格一致")

        return current_position
    except Exception as exc:
        print(f"⚠️ 获取持仓信息失败: {str(exc)}")
        return None
