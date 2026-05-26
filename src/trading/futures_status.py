from datetime import datetime

from src.config.config import CONTRACT_CONFIG


def display_position_monitor_status(price, current_position, strategy, leverage):
    """有持仓监控时的定期状态输出。"""
    print(f"\n📊 合约交易状态 - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*50}")
    print(f"💰 当前价格: {price:.2f} USDT")
    print("🎯 交易信号: 无 (有持仓，不允许开新仓)")
    print("📈 持仓状态: 有持仓")

    if current_position:
        print_position_details(current_position, strategy, leverage)

    print("📅 当前状态: 有持仓 (不可开新仓)")
    print_strategy_status(strategy)
    print("-" * 50)


def display_signal_trigger(signal, price, in_position, current_position, strategy):
    """有交易信号时的状态输出。"""
    print(f"\n{'='*60}")
    print(f"🎯 合约交易信号触发 - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    print(f"💰 当前价格: {price:.2f} USDT")
    print(f"🎯 信号类型: {'🟢 做多信号' if signal == 1 else '🔴 做空信号'}")
    print(f"📈 持仓状态: {'有持仓' if in_position else '无持仓'}")

    if current_position:
        print_position_details(
            current_position,
            strategy,
            current_position['leverage'],
            heading="当前持仓详情"
        )

    print(f"{'='*60}")


def display_no_signal_status(price, in_position, current_position, strategy, leverage, capital):
    """无交易信号时的定期状态输出。"""
    print(f"\n📊 合约交易状态 - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*50}")
    print(f"💰 当前价格: {price:.2f} USDT")
    print("🎯 交易信号: 无")
    print(f"📈 持仓状态: {'有持仓' if in_position else '无持仓'}")

    if in_position and current_position:
        print_position_details(current_position, strategy, leverage)
    else:
        print("\n📊 无持仓")
        print(f"  可用资金: {capital:.2f} USDT")
        print(f"  杠杆倍数: {leverage}x")

    if in_position:
        print("📅 当前状态: 有持仓 (不可开新仓)")
    else:
        print("📅 当前状态: 无持仓 (可开新仓)")

    print_strategy_status(strategy)
    print("-" * 50)


def print_position_details(current_position, strategy, leverage, heading="持仓详情"):
    margin_used = CONTRACT_CONFIG["fixed_margin"]
    pnl_pct_vs_margin = (current_position['unrealized_pnl'] / margin_used) * 100
    position_type = strategy.position_type or 'unknown'

    print(f"\n📊 {heading}:")
    print(f"  持仓类型: {position_type.upper()} ({'做多' if position_type == 'long' else '做空'})")
    print(f"  合约数量: {current_position['size']:.4f} 张")
    print(f"  入场价格: {current_position['entry_price']:.2f} USDT")
    print(f"  未实现盈亏: {current_position['unrealized_pnl']:.2f} USDT")
    print(f"  保证金收益率: {pnl_pct_vs_margin:.2f}%")
    print(f"  杠杆倍数: {leverage}x")
    print(f"  保证金: {margin_used:.2f} USDT (固定)")


def print_strategy_status(strategy):
    print("🎯 策略状态:")
    print(f"  止盈设置: {strategy.take_profit * 100:.1f}% (基于保证金)")
    print("  止损设置: 无止损 (强制平仓: -100%保证金)")
    print(f"  交易时间: {strategy.start_hour}:00-{strategy.end_hour}:00")
    print(f"  保证金: {CONTRACT_CONFIG['fixed_margin']} USDT (固定)")
    print(f"  调试模式: {'🔧 已启用' if strategy.debug_mode else '📊 生产模式'}")
    if strategy.debug_mode:
        print("  🔧 调试参数:")
        print(f"    RSI超卖: {strategy.rsi_oversold} (原: 30.0)")
        print(f"    RSI超买: {strategy.rsi_overbought} (原: 70.0)")
        print(f"    成交量比例: {strategy.min_volume_ratio} (原: 1.5)")
        print(f"    价格回调: {strategy.price_pullback*100:.1f}% (原: 1.0%)")
        print(f"    短期MA: {strategy.ma_short} (原: 5)")
        print(f"    长期MA: {strategy.ma_long} (原: 20)")
        print(f"    K线间隔: {strategy.kline_interval} (原: 15m)")
