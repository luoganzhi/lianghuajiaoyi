import logging

from src.config.config import CONTRACT_CONFIG
from src.trading.futures_helpers import get_futures_position, set_take_profit_order


def check_startup_position(account, symbol, leverage):
    """程序启动时检查并恢复合约持仓状态。"""
    in_position = False
    current_position = None

    print("\n🔍 程序启动时检查持仓状态...")
    logging.info("🔍 程序启动时检查持仓状态...")
    try:
        initial_position = get_futures_position(account, symbol)
        if initial_position and initial_position['size'] != 0:
            print(f"⚠️ 检测到现有持仓: {initial_position['size']:.4f}张 | 盈亏: {initial_position['unrealized_pnl']:.2f}USDT")

            logging.info("⚠️ 程序启动时检测到现有持仓:")
            logging.info(f"  - 持仓数量: {initial_position['size']:.4f} 张")
            logging.info(f"  - 入场价格: {initial_position['entry_price']:.2f} USDT")
            logging.info(f"  - 未实现盈亏: {initial_position['unrealized_pnl']:.2f} USDT")
            logging.info(f"  - 持仓方向: {'做多' if initial_position['size'] > 0 else '做空'}")
            logging.info(f"  - 杠杆倍数: {initial_position.get('leverage', 'N/A')}")
            logging.info(f"  - 保证金模式: {initial_position.get('margin_mode', 'N/A')}")

            in_position = True
            current_position = initial_position

            _set_startup_take_profit(account, symbol, initial_position, leverage)
        else:
            print("✅ 无现有持仓")
    except Exception as exc:
        print(f"⚠️ 启动时持仓检查失败: {str(exc)}")
        print("⚠️ 为了安全起见，程序将继续运行但会严格检查持仓状态")

    print(f"📊 初始状态: {'有持仓' if in_position else '无持仓'}")
    print("-" * 50)
    return in_position, current_position


def _set_startup_take_profit(account, symbol, initial_position, leverage):
    try:
        actual_entry_price = initial_position['entry_price']
        actual_position_size = initial_position['size']

        print("🔍 调试持仓方向判断:")
        print(f"  - 原始持仓数量: {initial_position.get('size', 'N/A')}")
        print(f"  - 转换后持仓数量: {actual_position_size}")
        print(f"  - 持仓数量类型: {type(actual_position_size)}")
        print(f"  - 持仓数量 > 0: {actual_position_size > 0}")

        margin_take_profit_pct = CONTRACT_CONFIG['take_profit_pct']
        price_take_profit_pct = margin_take_profit_pct / leverage

        position_type = initial_position.get('position_type', 'unknown')
        print(f"  - 持仓类型: {position_type}")

        if position_type == 'long':
            actual_take_profit_price = actual_entry_price * (1 + price_take_profit_pct)
            startup_entry_side = 'buy'
            print("  - 判断结果: 做多持仓")
        elif position_type == 'short':
            actual_take_profit_price = actual_entry_price * (1 - price_take_profit_pct)
            startup_entry_side = 'sell'
            print("  - 判断结果: 做空持仓")
        else:
            if actual_position_size > 0:
                actual_take_profit_price = actual_entry_price * (1 + price_take_profit_pct)
                startup_entry_side = 'buy'
                print("  - 备用判断结果: 做多持仓")
            else:
                actual_take_profit_price = actual_entry_price * (1 - price_take_profit_pct)
                startup_entry_side = 'sell'
                print("  - 备用判断结果: 做空持仓")

        print(f"  - 设置的开仓方向: {startup_entry_side}")

        tp_order = set_take_profit_order(account, symbol, position_type, actual_position_size, actual_take_profit_price)
        if tp_order:
            print(f"✅ 止盈设置: {actual_take_profit_price:.2f}")

    except Exception as exc:
        print(f"⚠️ 止盈设置失败: {str(exc)}")
