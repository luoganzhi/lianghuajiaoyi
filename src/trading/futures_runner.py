import sys
import os
import time
import logging
from datetime import datetime

from src.config.config import CONTRACT_CONFIG
from src.runtime.app_runtime import clear_previous_data, setup_logging
from src.trading.environment import validate_trading_environment
# from src.monitor.report_generator import ReportGenerator  # 暂时注释掉，合约交易不需要

from src.trading.futures_helpers import (
    check_existing_take_profit_orders,
    set_take_profit_order,
    get_futures_position,
    close_futures_position,
    _close_position,
)
from src.trading.futures_entries import open_futures_position
from src.trading.futures_setup import initialize_futures_components, print_futures_strategy_config
from src.trading.futures_startup import check_startup_position
from src.trading.futures_status import (
    display_no_signal_status,
    display_position_monitor_status,
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
    last_signal_check = 0  # 上次信号检查时间
    signal_check_interval = 1  # 无持仓时信号检查间隔（秒）
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
                # 有持仓时：主要监控持仓状态，不允许开新仓
                if current_time - last_position_check >= position_check_interval:
                    # 获取最新价格（用于计算盈亏）
                    try:
                        ticker_data = market_data.get_ticker(symbol)
                        if ticker_data and 'last' in ticker_data:
                            price = float(ticker_data['last'])
                        else:
                            price = current_position['entry_price'] if current_position else 0
                    except Exception as e:
                        price = current_position['entry_price'] if current_position else 0
                    
                    # 更新持仓信息
                    try:
                        current_position = get_futures_position(account, symbol, strategy)
                        
                        # 只有在成功获取到持仓信息时才更新状态
                        if current_position is not None:
                            previous_in_position = in_position
                            
                            # 检查持仓数量是否为0
                            if float(current_position.get('size', 0)) == 0:
                                # 持仓数量为0，更新为无持仓状态
                                in_position = False
                                if previous_in_position:
                                    logging.info(f"📊 持仓状态变化: 有持仓 -> 无持仓 (持仓数量为0)")
                            else:
                                # 持仓数量不为0，更新为有持仓状态
                                in_position = True
                                if not previous_in_position:
                                    logging.info(f"📊 持仓状态变化: 无持仓 -> 有持仓")
                            
                            # 记录持仓状态变化
                            if previous_in_position != in_position:
                                logging.info(f"📊 持仓状态变化:")
                                logging.info(f"  - 之前状态: {'有持仓' if previous_in_position else '无持仓'}")
                                logging.info(f"  - 当前状态: {'有持仓' if in_position else '无持仓'}")
                                logging.info(f"  - 变化时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                if in_position:
                                    logging.info(f"  - 持仓详情: {current_position['size']:.4f}张 @ {current_position['entry_price']:.2f} USDT")
                                else:
                                    logging.info(f"  - 持仓详情: 无持仓 (数量为0)")
                        else:
                            # 如果查询失败，保持原有状态不变
                            logging.warning(f"⚠️ 持仓查询失败，保持原有状态: {'有持仓' if in_position else '无持仓'}")
                            # 不更新 in_position，保持原样
                        
                        # 只有在成功查询到无持仓时才判断为强平
                        if current_position is None and in_position:
                            print(f"⚠️ 检测到持仓状态变化: 有持仓 -> 无持仓")
                            print(f"🔍 正在验证是否真的被强平...")
                            logging.warning(f"⚠️ 检测到持仓状态变化: 有持仓 -> 无持仓")
                            
                            # 再次尝试获取持仓信息进行验证
                            try:
                                verification_position = get_futures_position(account, symbol, strategy)
                                if verification_position and float(verification_position.get('size', 0)) != 0:
                                    print(f"✅ 验证结果: 持仓仍然存在，不是强平")
                                    logging.info(f"✅ 验证结果: 持仓仍然存在，不是强平")
                                    # 恢复状态
                                    in_position = True
                                    current_position = verification_position
                                else:
                                    print(f"⚠️ 验证结果: 确认仓位被强平")
                                    logging.warning(f"⚠️ 验证结果: 确认仓位被强平")
                                    # 只有在确认无持仓时才更新状态
                                    in_position = False
                            except Exception as verify_e:
                                print(f"⚠️ 验证持仓时出错: {str(verify_e)}")
                                logging.warning(f"⚠️ 验证持仓时出错: {str(verify_e)}")
                                # 验证失败时保持原有状态
                                print(f"🔄 验证失败，保持原有持仓状态: {'有持仓' if in_position else '无持仓'}")
                        
                        # 如果有持仓，检查是否需要设置止盈单
                        if current_position and current_position['size'] != 0:
                            try:
                                actual_entry_price = current_position['entry_price']
                                actual_position_size = current_position['size']
                                
                                # 直接使用持仓查询响应中的position_type字段
                                position_type = current_position.get('position_type', 'unknown')
                                print(f"🔍 持仓信息: size={actual_position_size}, position_type={position_type}")
                                
                                # 计算止盈价格
                                margin_take_profit_pct = CONTRACT_CONFIG['take_profit_pct']  # 保证金止盈比例：10%
                                price_take_profit_pct = margin_take_profit_pct / leverage  # 价格止盈比例
                                
                                # 根据持仓类型计算止盈价格
                                if position_type == 'long':  # 做多持仓
                                    actual_take_profit_price = actual_entry_price * (1 + price_take_profit_pct)
                                elif position_type == 'short':  # 做空持仓
                                    actual_take_profit_price = actual_entry_price * (1 - price_take_profit_pct)
                                else:
                                    print(f"❌ 未知的持仓类型: {position_type}")
                                    continue
                                
                                # 先检查是否已经存在止盈单
                                has_existing_tp = check_existing_take_profit_orders(account, symbol)
                                
                                if not has_existing_tp:
                                    # 如果没有现有止盈单，尝试设置新的止盈单
                                    print(f"🔧 尝试设置止盈单: {actual_take_profit_price:.2f} USDT")
                                    print(f"🔍 使用持仓类型: {position_type}")
                                    tp_order = set_take_profit_order(account, symbol, position_type, actual_position_size, actual_take_profit_price)
                                    if tp_order:
                                        print(f"✅ 止盈单设置成功: {actual_take_profit_price:.2f} USDT")
                                    else:
                                        print(f"⚠️ 止盈单设置失败")
                                else:
                                    print(f"ℹ️ 已存在止盈单，无需重复设置")
                                    
                            except Exception as tp_e:
                                print(f"⚠️ 止盈单检查/设置异常: {str(tp_e)}")
                                # 如果是方向错误，说明可能已经存在止盈单
                                if "reduce-only order can't be in the same trading direction" in str(tp_e):
                                    print(f"ℹ️ 检测到止盈单可能已存在")
                                else:
                                    print(f"⚠️ 止盈单设置失败，需要手动检查")
                        
                        last_position_check = current_time
                    except Exception as e:
                        logging.warning(f"⚠️ 持仓检查失败: {str(e)[:100]}")
                        time.sleep(1)
                        continue
                    
                    # 定期显示状态（每30秒）
                    if current_time - last_status_display >= status_display_interval:
                        display_position_monitor_status(price, current_position, strategy, leverage)
                        last_status_display = current_time
                    
                    # 有持仓时绝对不允许生成新信号
                    signal = 0
                    print(f"ℹ️ 有持仓状态，跳过信号生成 (in_position={in_position})")
                    logging.info(f"ℹ️ 有持仓状态，跳过信号生成 (in_position={in_position})")
                    
                else:
                    # 未到检查时间，跳过本次循环
                    time.sleep(1)
                    continue
                    
            else:
                # 无持仓时：持续获取信号，允许开新仓
                # 更新市场数据
                try:
                    ticker_data = market_data.get_ticker(symbol)
                    if not ticker_data or 'last' not in ticker_data:
                        warning_msg = "⚠️ 获取行情数据失败，跳过本次循环"
                        print(warning_msg)
                        logging.warning(f"⚠️ 获取行情数据失败 - 数据为空或格式错误")
                        time.sleep(interval)
                        continue
                    price = float(ticker_data['last'])
                except Exception as e:
                    error_msg = f"⚠️ 获取行情数据失败: {str(e)[:100]}，跳过本次循环"
                    print(error_msg)
                    logging.error(f"⚠️ 获取行情数据异常 - 错误: {str(e)}")
                    time.sleep(interval)
                    continue
                
                # 获取合约持仓信息
                try:
                    current_position = get_futures_position(account, symbol, strategy)
                    previous_in_position = in_position
                    in_position = current_position is not None
                    
                    # 检测仓位是否被强平
                    if previous_in_position and not in_position:
                        print(f"⚠️ 检测到仓位被强平")
                        # 重置策略状态
                        strategy.on_position_exit('unknown', price, 0, 0)
                        print(f"✅ 仓位强平处理完成")
                        print(f"🔍 策略持仓状态: {strategy.current_position}")
                    
                except Exception as e:
                    error_msg = f"⚠️ 获取合约持仓失败: {str(e)[:100]}，跳过本次循环"
                    print(error_msg)
                    logging.error(f"⚠️ 获取合约持仓异常 - 错误: {str(e)}")
                    time.sleep(interval)
                    continue

                # 获取策略信号
                # 合约交易对格式转换，用于获取K线数据
                if symbol.endswith('-SWAP'):
                    ohlcv_symbol = symbol.replace('-SWAP', '')
                else:
                    ohlcv_symbol = symbol
                
                ohlcv_data = market_data.get_ohlcv(ohlcv_symbol, timeframe=CONTRACT_CONFIG.get('kline_interval', '1m'))
                raw_signal = strategy.generate_signal(ohlcv_data)
                
                # 记录策略信号生成详情
                logging.info(f"🔍 策略信号生成详情:")
                logging.info(f"  - 原始信号: {raw_signal}")
                logging.info(f"  - 信号类型: {'做多' if raw_signal == 1 else '做空' if raw_signal == -1 else '平仓' if raw_signal == 0 else '未知'}")
                logging.info(f"  - 当前价格: {price:.2f} USDT")
                logging.info(f"  - 策略类型: {strategy.__class__.__name__}")
                logging.info(f"  - 调试模式: {strategy.debug_mode}")
                logging.info(f"  - 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 禁用信号0（平仓信号），只允许开仓信号
                if raw_signal == 0:
                    signal = 0  # 保持为0，但不执行平仓
                    print(f"ℹ️ 策略生成平仓信号，已禁用 (raw_signal={raw_signal})")
                    logging.info(f"ℹ️ 策略生成平仓信号，已禁用 (raw_signal={raw_signal})")
                else:
                    signal = raw_signal  # 允许开仓信号
                    logging.info(f"✅ 策略信号有效，允许执行: {signal}")
                
                # 信号去重机制
                current_time = time.time()
                if signal != 0:
                    # 检查是否是重复信号
                    if (signal == last_signal and 
                        current_time - last_signal_time < signal_cooldown):
                        print(f"⚠️ 重复信号被忽略: {signal} (冷却中)")
                        signal = 0  # 忽略重复信号
                    else:
                        # 更新信号记录
                        last_signal = signal
                        last_signal_time = current_time
                
                # 添加调试信息：显示策略计算过程
                if len(ohlcv_data) > 0:
                    current_price = ohlcv_data['close'].iloc[-1]
                    print(f"🔍 策略计算: 价格={current_price:.2f}, 信号={signal}, 时间={datetime.now().strftime('%H:%M:%S')}")
            
            # 记录信号生成日志
            if signal != 0:
                signal_type = "做多" if signal == 1 else "做空"
                logging.info(f"🎯 合约交易信号生成 - 类型: {signal_type}, 价格: {price:.2f}, 时间: {datetime.now().strftime('%H:%M:%S')}")
            elif loop_count % 100 == 0:  # 每100次循环记录一次无信号状态
                logging.debug(f"📊 合约交易无信号 - 价格: {price:.2f}, 时间: {datetime.now().strftime('%H:%M:%S')}")
            
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
            
            # 合约交易逻辑
            today = datetime.now().strftime('%Y-%m-%d')
            
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
                    
            # 注释掉信号为0时的平仓逻辑，只保留止盈和强制平仓
            # elif signal == 0 and in_position:  # 检查是否应该平仓
            #     # 检查止盈条件
            #     if current_position and current_position['size'] != 0:
            #         entry_price = current_position['entry_price']
            #         position_type = strategy.position_type
            #         
            #         # 根据持仓数量判断方向
            #         if current_position['size'] > 0:  # 做多持仓
            #             # 做多止盈检查
            #             profit_pct = (price - entry_price) / entry_price
            #             if profit_pct >= strategy.take_profit:
            #                 print(f"🎯 止盈触发! 盈利: {profit_pct*100:.2f}%")
            #                 if _close_position(account, symbol, current_position, price, 'long'):
            #                     # 更新策略状态
            #                     strategy.on_position_exit('sell', price, current_position['size'], profit_pct)
            #                     # 重置持仓状态
            #                     in_position = False
            #                     current_position = None
            #                 continue
            #         else:  # 做空持仓
            #             # 做空止盈检查
            #             profit_pct = (entry_price - price) / entry_price
            #             if profit_pct >= strategy.take_profit:
            #                 print(f"🎯 止盈触发! 盈利: {profit_pct*100:.2f}%")
            #                 if _close_position(account, symbol, current_position, price, 'short'):
            #                     # 更新策略状态
            #                     strategy.on_position_exit('buy', price, current_position['size'], profit_pct)
            #                     # 重置持仓状态
            #                     in_position = False
            #                     current_position = None
            #                 continue
            
            # 合约止盈和强制平仓监控
            if current_position and current_position['size'] != 0:
                entry_price = current_position['entry_price']
                # 基于保证金计算收益率：未实现盈亏 / 保证金
                margin_used = CONTRACT_CONFIG["fixed_margin"]  # 使用配置中的保证金
                current_pnl_pct_vs_margin = (current_position['unrealized_pnl'] / margin_used)
                
                # 检查止盈（基于保证金）
                if current_pnl_pct_vs_margin >= strategy.take_profit:
                    print(f"🎯 止盈触发! 收益率: {current_pnl_pct_vs_margin*100:.2f}% | 盈亏: {current_position['unrealized_pnl']:.2f}USDT")
                    
                    # 记录止盈平仓原因
                    logging.info(f"🎯 止盈平仓触发")
                    logging.info(f"📊 止盈平仓原因分析:")
                    logging.info(f"  - 平仓类型: 止盈平仓")
                    logging.info(f"  - 入场价格: {entry_price:.2f} USDT")
                    logging.info(f"  - 当前价格: {price:.2f} USDT")
                    logging.info(f"  - 持仓数量: {current_position['size']:.4f} 张")
                    logging.info(f"  - 未实现盈亏: {current_position['unrealized_pnl']:.2f} USDT")
                    logging.info(f"  - 保证金收益率: {current_pnl_pct_vs_margin*100:.2f}%")
                    logging.info(f"  - 止盈阈值: {strategy.take_profit*100:.1f}%")
                    logging.info(f"  - 杠杆倍数: {leverage}x")
                    logging.info(f"  - 保证金: {margin_used:.2f} USDT")
                    
                    # 执行平仓
                    try:
                        close_futures_position(account, symbol, current_position)
                        in_position = False
                        current_position = None
                        logging.info(f"✅ 止盈平仓执行成功")
                    except Exception as e:
                        print(f"❌ 止盈平仓失败: {str(e)}")
                        logging.error(f"❌ 止盈平仓执行失败: {str(e)}")
                    
                # 强制平仓：亏损超过保证金时强制平仓
                elif current_pnl_pct_vs_margin <= -1.0:  # 亏损100%保证金
                    print(f"🛑 强制平仓! 亏损: {current_pnl_pct_vs_margin*100:.2f}% | 盈亏: {current_position['unrealized_pnl']:.2f}USDT")
                    
                    # 记录强制平仓原因
                    logging.info(f"🛑 强制平仓触发")
                    logging.info(f"📊 强制平仓原因分析:")
                    logging.info(f"  - 平仓类型: 强制平仓")
                    logging.info(f"  - 入场价格: {entry_price:.2f} USDT")
                    logging.info(f"  - 当前价格: {price:.2f} USDT")
                    logging.info(f"  - 持仓数量: {current_position['size']:.4f} 张")
                    logging.info(f"  - 未实现盈亏: {current_position['unrealized_pnl']:.2f} USDT")
                    logging.info(f"  - 保证金亏损率: {current_pnl_pct_vs_margin*100:.2f}%")
                    logging.info(f"  - 强制平仓阈值: -100%")
                    logging.info(f"  - 杠杆倍数: {leverage}x")
                    logging.info(f"  - 保证金: {margin_used:.2f} USDT")
                    logging.info(f"  - 风险等级: 极高 (亏损超过保证金)")
                    
                    # 执行强制平仓
                    try:
                        close_futures_position(account, symbol, current_position)
                        in_position = False
                        current_position = None
                        logging.info(f"✅ 强制平仓执行成功")
                    except Exception as e:
                        print(f"❌ 强制平仓失败: {str(e)}")
                        logging.error(f"❌ 强制平仓执行失败: {str(e)}")
            
            # 更新持仓监控（减少重复调用）
            if loop_count % 5 == 0:  # 每5次循环更新一次，减少重复
                if in_position and current_position:
                    # 调试：显示实际杠杆信息
                    actual_leverage = current_position.get('leverage', leverage)
                    if actual_leverage != leverage:
                        logging.info(f"⚠️ 杠杆不匹配 - 设置: {leverage}x, 实际: {actual_leverage}x")
                    
                    position_data = {
                        "size": current_position['size'],
                        "entry_price": current_position['entry_price'],
                        "current_price": price,
                        "unrealized_pnl": current_position['unrealized_pnl'],
                        "position_type": strategy.position_type,
                        "leverage": actual_leverage,  # 使用实际杠杆倍数
                        "margin_mode": strategy.margin_mode
                    }
                    trade_monitor.update_position(symbol, position_data)
                else:
                    # 清空持仓监控
                    trade_monitor.update_position(symbol, {})
                
                # 更新系统指标
                metrics = {
                    "current_capital": capital,
                    "initial_capital": capital,  # 这里可以设置为初始资金
                    "drawdown": 0.0,  # 暂时设为0，可以根据需要计算
                    "daily_pnl": 0.0,  # 暂时设为0，可以根据需要计算
                    "position_count": 1 if in_position else 0,
                    "positions": trade_monitor.positions,
                    "recent_alerts": [],
                    "total_exposure": current_position['size'] * price if in_position and current_position else 0
                }
                trade_monitor.update_system_metrics(metrics)
            
            # 更新循环计数
            loop_count += 1
            
            # 定期记录程序状态到日志
            if loop_count % 100 == 0:  # 每100次循环记录一次详细状态
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
            
            if loop_count % 30 == 0:  # 每30次循环显示一次状态（1秒间隔下约30秒显示一次）
                if in_position and current_position:
                    print(f"📊 {datetime.now().strftime('%H:%M:%S')} | 持仓: {current_position['size']:.4f}张 | 盈亏: {current_position['unrealized_pnl']:.2f}USDT")
                else:
                    print(f"📊 {datetime.now().strftime('%H:%M:%S')} | 无持仓")
            
            time.sleep(interval)
            
        except Exception as e:
            error_msg = f"❌ 合约交易主循环异常: {str(e)[:200]}"
            print(error_msg)
            logging.error(f"❌ 合约交易主循环异常 - 错误: {str(e)}")
            print("等待10秒后重试...")
            time.sleep(10)
            continue
