import sys
import os
import time
import logging
from datetime import datetime

from src.runtime.app_runtime import clear_previous_data, setup_logging
from src.trading.environment import validate_trading_environment
# from src.monitor.report_generator import ReportGenerator  # 暂时注释掉，合约交易不需要

from src.trading.futures_helpers import get_futures_position
from src.trading.futures_entries import open_futures_position
from src.trading.futures_exits import handle_futures_exit
from src.trading.futures_monitoring import (
    display_compact_loop_status,
    log_periodic_runner_state,
    update_futures_monitor,
)
from src.trading.futures_position_monitor import monitor_open_position
from src.trading.futures_setup import initialize_futures_components, print_futures_strategy_config
from src.trading.futures_signals import generate_no_position_signal, log_generated_signal
from src.trading.futures_startup import check_startup_position
from src.trading.futures_status import (
    display_no_signal_status,
    display_signal_trigger,
)


def futures_trading_main():
    """
    合约交易主程序
    """
    print("🚀 启动合约交易模式...")
    if not validate_trading_environment():
        return
    
    # 记录程序启动
    logging.info(f"🚀 合约交易程序启动")
    logging.info(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"🐍 Python版本: {sys.version}")
    logging.info(f"📁 工作目录: {os.getcwd()}")
    
    # 清理之前的数据
    clear_previous_data()
    
    # 重新配置日志（清理后重新设置）
    setup_logging()
    
    # 初始化循环计数器
    loop_count = 0
    
    try:
        components = initialize_futures_components()
        if components is None:
            return

        market_data = components.market_data
        account = components.account
        trade_monitor = components.trade_monitor
        strategy = components.strategy

    except Exception as e:
        print(f"❌ 组件初始化失败: {e}")
        print("请检查网络连接和API配置")
        return
    
    # 合约交易参数
    symbol = "BTC-USDT-SWAP"  # 永续合约
    leverage = strategy.leverage  # 从策略获取杠杆倍数（50x）
    interval = 3   # 3秒（防止重复信号）
    capital = float(account.get_balance("USDT"))
    
    print(f"初始资金: {capital} USDT")
    print(f"杠杆倍数: {leverage}x")
    print(f"交易对: {symbol}")
    print(f"保证金模式: {strategy.margin_mode}")
    
    print_futures_strategy_config(strategy, leverage)
    
    # 信号去重和开仓锁机制
    last_signal = 0  # 上次信号
    last_signal_time = 0  # 上次信号时间
    signal_cooldown = 10  # 信号冷却时间（秒）
    trading_lock = False  # 开仓锁
    last_trade_time = 0  # 上次开仓时间
    trade_cooldown = 30  # 开仓冷却时间（秒）

    in_position, current_position = check_startup_position(account, symbol, leverage)
    
    # 优化请求频率的变量
    position_check_interval = 30  # 有持仓时持仓检查间隔（秒）
    last_position_check = 0  # 上次持仓检查时间
    last_status_display = 0  # 上次状态显示时间
    status_display_interval = 30  # 状态显示间隔（秒）
    
    # 添加调试模式切换功能
    def toggle_debug_mode():
        """切换调试模式"""
        if strategy.debug_mode:
            strategy.restore_original_params()
            print(f"\n🔧 已切换到生产模式 - 使用原始参数配置")
        else:
            strategy._enable_debug_mode()
            print(f"\n🔧 已切换到调试模式 - 信号生成条件已降低")
    
    print(f"📊 当前模式: {'🔧 调试模式' if strategy.debug_mode else '📊 生产模式'}")
    
    while True:
        try:
            current_time = time.time()
            
            # 每日重置交易状态
            current_date = datetime.now().strftime('%Y-%m-%d')
            if hasattr(strategy, 'daily_traded') and current_date not in strategy.daily_traded:
                print(f"🔄 新的一天: {current_date}")
            
            # 根据持仓状态调整请求频率
            if in_position:
                monitor_result = monitor_open_position(
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
                )
                if monitor_result.skip_cycle:
                    current_position = monitor_result.current_position
                    in_position = monitor_result.in_position
                    last_position_check = monitor_result.last_position_check
                    last_status_display = monitor_result.last_status_display
                    continue

                price = monitor_result.price
                current_position = monitor_result.current_position
                in_position = monitor_result.in_position
                last_position_check = monitor_result.last_position_check
                last_status_display = monitor_result.last_status_display
                signal = monitor_result.signal
            else:
                signal_result = generate_no_position_signal(
                    market_data,
                    account,
                    symbol,
                    strategy,
                    in_position,
                    last_signal,
                    last_signal_time,
                    signal_cooldown,
                    interval,
                )
                if signal_result.skip_cycle:
                    continue

                price = signal_result.price
                current_position = signal_result.current_position
                in_position = signal_result.in_position
                signal = signal_result.signal
                last_signal = signal_result.last_signal
                last_signal_time = signal_result.last_signal_time
            
            log_generated_signal(signal, price, loop_count)
            
            # 状态显示逻辑 - 像现货交易一样清晰显示
            if signal != 0:
                display_signal_trigger(signal, price, in_position, current_position, strategy)
            else:
                # 无信号时显示完整状态（每3次循环显示一次）
                if not hasattr(futures_trading_main, 'loop_count'):
                    futures_trading_main.loop_count = 0
                futures_trading_main.loop_count += 1
                
                if futures_trading_main.loop_count % 3 == 0:  # 每3次循环显示一次状态（约3秒显示一次）
                    display_no_signal_status(price, in_position, current_position, strategy, leverage, capital)
            
            # 确保价格变量可用（用于合约交易）
            if 'price' not in locals():
                try:
                    ticker_data = market_data.get_ticker(symbol)
                    if ticker_data and 'last' in ticker_data:
                        price = float(ticker_data['last'])
                    else:
                        print("⚠️ 无法获取价格数据，跳过本次循环")
                        time.sleep(interval)
                        continue
                except Exception as e:
                    print(f"⚠️ 获取价格数据失败: {str(e)}，跳过本次循环")
                    time.sleep(interval)
                    continue
            
            # 🔒 严格检查持仓状态（有持仓时绝对不允许开新仓）
            if in_position:
                if signal != 0:
                    info_msg = f"ℹ️ 已有持仓，跳过交易机会 (in_position={in_position})"
                    print(info_msg)
                    logging.info(f"ℹ️ 已有持仓，跳过交易机会 (in_position={in_position})")
                continue
            
            # 🔒 开仓锁检查（防止重复开仓）
            current_time = time.time()
            if trading_lock:
                if current_time - last_trade_time < trade_cooldown:
                    remaining_time = trade_cooldown - (current_time - last_trade_time)
                    print(f"🔒 开仓锁激活中，剩余冷却时间: {remaining_time:.1f}秒")
                    continue
                else:
                    trading_lock = False  # 解锁
                    print(f"🔓 开仓锁已解除")
            
            # 🔍 严格检查：每次开仓前都必须查询实际持仓状态
            try:
                actual_position = get_futures_position(account, symbol)
                if actual_position and actual_position['size'] != 0:
                    print(f"⚠️ 已有持仓: {actual_position['size']:.4f}张 | 盈亏: {actual_position['unrealized_pnl']:.2f}USDT")
                    in_position = True  # 更新状态
                    current_position = actual_position
                    continue
            except Exception as e:
                print(f"⚠️ 持仓查询失败，跳过开仓")
                continue
                
            if signal in (1, -1) and not in_position:
                entry_result = open_futures_position(
                    account,
                    symbol,
                    signal,
                    price,
                    leverage,
                    strategy,
                    trade_monitor,
                    trade_cooldown,
                )
                if entry_result.opened:
                    in_position = True
                    current_position = entry_result.current_position
                    trading_lock = entry_result.trading_lock
                    last_trade_time = entry_result.last_trade_time
                if entry_result.skip_cycle:
                    continue
            exit_result = handle_futures_exit(account, symbol, current_position, price, strategy, leverage)
            if exit_result.closed:
                in_position = False
            current_position = exit_result.current_position
            
            # 更新持仓监控（减少重复调用）
            if loop_count % 5 == 0:
                update_futures_monitor(trade_monitor, symbol, in_position, current_position, price, strategy, leverage, capital)
            
            # 更新循环计数
            loop_count += 1
            log_periodic_runner_state(loop_count, in_position, current_position, price, strategy)
            display_compact_loop_status(loop_count, in_position, current_position)
            
            time.sleep(interval)
            
        except Exception as e:
            error_msg = f"❌ 合约交易主循环异常: {str(e)[:200]}"
            print(error_msg)
            logging.error(f"❌ 合约交易主循环异常 - 错误: {str(e)}")
            print("等待10秒后重试...")
            time.sleep(10)
            continue
