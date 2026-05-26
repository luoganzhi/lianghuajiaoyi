import sys
import os
import time
import logging
from datetime import datetime

try:
    from src.runtime.app_runtime import bootstrap_project_path, clear_previous_data, setup_logging
except ModuleNotFoundError:
    from runtime.app_runtime import bootstrap_project_path, clear_previous_data, setup_logging


project_root = bootstrap_project_path()

from src.config.config import CONTRACT_CONFIG, IS_SIMULATED, MONITOR_CONFIG, PROXY, RISK_CONFIG
from src.data.market_data import MarketDataFetcher
from src.execution.okx_executor import OKXExecutor
from src.risk.risk_manager import RiskManager
from src.risk.risk_monitor import RiskMonitor
from src.monitor.trade_monitor import TradeMonitor
from src.risk.position_manager import PositionManager
from src.risk.stop_manager import StopManager
from src.strategies.daily_trading_strategy import DailyTradingStrategy
from src.strategies.contract_daily_trading_strategy import ContractDailyTradingStrategy
from src.trading.environment import get_trading_credentials, validate_trading_environment
# from src.monitor.report_generator import ReportGenerator  # 暂时注释掉，合约交易不需要

# 初始化日志（在所有模块导入后）
setup_logging()

from src.trading.futures_helpers import (
    execute_futures_trade,
    check_existing_take_profit_orders,
    set_take_profit_order,
    get_futures_position,
    calculate_futures_position_size,
    close_futures_position,
    _close_position,
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
        # 初始化组件
        print("正在初始化交易组件...")
        api_key, api_secret, api_password = get_trading_credentials()
        
        # 尝试不同的代理配置
        proxy_configs = [
            "http://127.0.0.1:7890",  # 备用代理1
        ]
        
        market_data = None
        account = None
        
        # 尝试初始化市场数据获取器
        for proxy in proxy_configs:
            try:
                print(f"尝试使用代理: {proxy or '无代理'}")
                market_data = MarketDataFetcher(
                    exchange_id='okx',
                    api_key=api_key,
                    secret=api_secret,
                    proxy=proxy
                )
                
                # 测试连接
                test_ticker = market_data.get_ticker('BTC/USDT')
                if test_ticker:
                    print(f"✅ 市场数据连接成功 (代理: {proxy or '无代理'})")
                    break
            except Exception as e:
                print(f"❌ 代理 {proxy or '无代理'} 连接失败: {str(e)[:100]}")
                continue
        
        if not market_data:
            print("❌ 所有代理都无法连接，请检查网络设置")
            return
        
        # 尝试初始化交易执行器
        for proxy in proxy_configs:
            try:
                account = OKXExecutor(
                    api_key=api_key,
                    api_secret=api_secret,
                    api_password=api_password,
                    proxy=proxy,
                    is_simulated=IS_SIMULATED
                )
                
                # 测试账户连接
                test_balance = account.get_balance("USDT")
                if test_balance is not None:
                    print(f"✅ 交易账户连接成功 (代理: {proxy or '无代理'})")
                    break
            except Exception as e:
                print(f"❌ 代理 {proxy or '无代理'} 账户连接失败: {str(e)[:100]}")
                continue
        
        if not account:
            print("❌ 所有代理都无法连接交易账户，请检查API配置")
            return
        
        trade_monitor = TradeMonitor()
        # 使用新的合约交易策略，从配置文件读取K线周期和调试模式
        kline_interval = CONTRACT_CONFIG.get('kline_interval', '1m')  # 默认1分钟
        debug_mode = CONTRACT_CONFIG.get('debug_mode', False)
        strategy = ContractDailyTradingStrategy(debug_mode=debug_mode, kline_interval=kline_interval)
        
        # 🎯 启用高精度模式 - 25%保证金止盈
        # strategy.enable_high_precision_mode()
        
        # 记录策略初始化详情
        logging.info(f"📊 策略初始化完成:")
        logging.info(f"  - 策略类型: {strategy.__class__.__name__}")
        logging.info(f"  - 策略模式: {strategy.get_strategy_mode()}")
        logging.info(f"  - 调试模式: {strategy.debug_mode}")
        logging.info(f"  - 止盈比例: {strategy.take_profit*100:.3f}%")
        logging.info(f"  - 杠杆倍数: {strategy.leverage}x")
        logging.info(f"  - 保证金模式: {strategy.margin_mode}")
        logging.info(f"  - K线间隔: {strategy.kline_interval}")
        
        print("✅ 所有组件初始化成功！")
        
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
    
    # 打印策略配置
    print("=" * 50)
    print("🚀 合约每日交易策略 - 高杠杆版本")
    print("=" * 50)
    print(f"策略类型: {strategy.__class__.__name__}")
    print(f"策略模式: {strategy.get_strategy_mode()}")
    print(f"止盈设置: {strategy.take_profit * 100:.3f}% (基于保证金)")
    print(f"止损设置: 无止损 (强制平仓: -100%保证金)")
    print(f"杠杆倍数: {leverage}x")
    print(f"保证金模式: {strategy.margin_mode}")
    print(f"交易时间: {strategy.start_hour}:00-{strategy.end_hour}:00")
    print(f"K线间隔: {strategy.kline_interval}")
    print(f"固定保证金: {CONTRACT_CONFIG['fixed_margin']} USDT")
    print(f"调试模式: {'🔧 已启用' if strategy.debug_mode else '📊 生产模式'}")
    if strategy.debug_mode:
        print(f"🔧 调试参数调整:")
        print(f"  RSI超卖阈值: 30.0 → {strategy.rsi_oversold}")
        print(f"  RSI超买阈值: 70.0 → {strategy.rsi_overbought}")
        print(f"  最小成交量比例: 1.5 → {strategy.min_volume_ratio}")
        print(f"  价格回调比例: 1.0% → {strategy.price_pullback*100:.1f}%")
        print(f"  短期MA: 5 → {strategy.ma_short}")
        print(f"  长期MA: 20 → {strategy.ma_long}")
        print(f"  K线间隔: 15m → {strategy.kline_interval}")
    print("=" * 50)
    
    # 合约交易状态管理
    in_position = False
    current_position = None
    
    # 信号去重和开仓锁机制
    last_signal = 0  # 上次信号
    last_signal_time = 0  # 上次信号时间
    signal_cooldown = 10  # 信号冷却时间（秒）
    trading_lock = False  # 开仓锁
    last_trade_time = 0  # 上次开仓时间
    trade_cooldown = 30  # 开仓冷却时间（秒）
    
    # 🔍 程序启动时立即检查持仓状态
    print(f"\n🔍 程序启动时检查持仓状态...")
    logging.info(f"🔍 程序启动时检查持仓状态...")
    try:
        initial_position = get_futures_position(account, symbol)
        if initial_position and initial_position['size'] != 0:
            print(f"⚠️ 检测到现有持仓: {initial_position['size']:.4f}张 | 盈亏: {initial_position['unrealized_pnl']:.2f}USDT")
            
            # 记录启动时持仓详情
            logging.info(f"⚠️ 程序启动时检测到现有持仓:")
            logging.info(f"  - 持仓数量: {initial_position['size']:.4f} 张")
            logging.info(f"  - 入场价格: {initial_position['entry_price']:.2f} USDT")
            logging.info(f"  - 未实现盈亏: {initial_position['unrealized_pnl']:.2f} USDT")
            logging.info(f"  - 持仓方向: {'做多' if initial_position['size'] > 0 else '做空'}")
            logging.info(f"  - 杠杆倍数: {initial_position.get('leverage', 'N/A')}")
            logging.info(f"  - 保证金模式: {initial_position.get('margin_mode', 'N/A')}")
            
            # 立即设置持仓状态，防止开新仓
            in_position = True
            current_position = initial_position
            
            # 检查是否需要设置止盈单
            try:
                # 计算止盈价格
                actual_entry_price = initial_position['entry_price']
                actual_position_size = initial_position['size']
                position_type = initial_position.get('posSide', 'long')
                
                # 添加调试信息
                print(f"🔍 调试持仓方向判断:")
                print(f"  - 原始持仓数量: {initial_position.get('size', 'N/A')}")
                print(f"  - 转换后持仓数量: {actual_position_size}")
                print(f"  - 持仓数量类型: {type(actual_position_size)}")
                print(f"  - 持仓数量 > 0: {actual_position_size > 0}")
                
                margin_take_profit_pct = CONTRACT_CONFIG['take_profit_pct']  # 保证金止盈比例：10%
                price_take_profit_pct = margin_take_profit_pct / leverage  # 价格止盈比例
                
                # 根据持仓类型判断开仓方向
                position_type = initial_position.get('position_type', 'unknown')
                print(f"  - 持仓类型: {position_type}")
                
                if position_type == 'long':  # 做多持仓
                    actual_take_profit_price = actual_entry_price * (1 + price_take_profit_pct)
                    startup_entry_side = 'buy'  # 做多开仓方向
                    print(f"  - 判断结果: 做多持仓")
                elif position_type == 'short':  # 做空持仓
                    actual_take_profit_price = actual_entry_price * (1 - price_take_profit_pct)
                    startup_entry_side = 'sell'  # 做空开仓方向
                    print(f"  - 判断结果: 做空持仓")
                else:  # 未知持仓类型，根据持仓数量判断（备用方案）
                    if actual_position_size > 0:  # 做多持仓
                        actual_take_profit_price = actual_entry_price * (1 + price_take_profit_pct)
                        startup_entry_side = 'buy'  # 做多开仓方向
                        print(f"  - 备用判断结果: 做多持仓")
                    else:  # 做空持仓
                        actual_take_profit_price = actual_entry_price * (1 - price_take_profit_pct)
                        startup_entry_side = 'sell'  # 做空开仓方向
                        print(f"  - 备用判断结果: 做空持仓")
                
                print(f"  - 设置的开仓方向: {startup_entry_side}")
                
                # 传递持仓类型而不是开仓方向
                tp_order = set_take_profit_order(account, symbol, position_type, actual_position_size, actual_take_profit_price)
                if tp_order:
                    print(f"✅ 止盈设置: {actual_take_profit_price:.2f}")
                    
            except Exception as tp_e:
                print(f"⚠️ 止盈设置失败: {str(tp_e)}")
        else:
            print(f"✅ 无现有持仓")
    except Exception as e:
        print(f"⚠️ 启动时持仓检查失败: {str(e)}")
        print(f"⚠️ 为了安全起见，程序将继续运行但会严格检查持仓状态")
    
    print(f"📊 初始状态: {'有持仓' if in_position else '无持仓'}")
    print("-" * 50)
    
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
                        print(f"\n📊 合约交易状态 - {datetime.now().strftime('%H:%M:%S')}")
                        print(f"{'='*50}")
                        print(f"💰 当前价格: {price:.2f} USDT")
                        print(f"🎯 交易信号: 无 (有持仓，不允许开新仓)")
                        print(f"📈 持仓状态: 有持仓")
                        
                        if current_position:
                            # 基于保证金计算收益率
                            margin_used = CONTRACT_CONFIG["fixed_margin"]  # 固定保证金
                            pnl_pct_vs_margin = (current_position['unrealized_pnl'] / margin_used) * 100
                            position_type = strategy.position_type or 'unknown'
                            print(f"\n📊 持仓详情:")
                            print(f"  持仓类型: {position_type.upper()} ({'做多' if position_type == 'long' else '做空'})")
                            print(f"  合约数量: {current_position['size']:.4f} 张")
                            print(f"  入场价格: {current_position['entry_price']:.2f} USDT")
                            print(f"  未实现盈亏: {current_position['unrealized_pnl']:.2f} USDT")
                            print(f"  保证金收益率: {pnl_pct_vs_margin:.2f}%")
                            print(f"  杠杆倍数: {leverage}x")
                            print(f"  保证金: {margin_used:.2f} USDT (固定)")
                        
                        print(f"📅 当前状态: 有持仓 (不可开新仓)")
                        print(f"🎯 策略状态:")
                        print(f"  止盈设置: {strategy.take_profit * 100:.1f}% (基于保证金)")
                        print(f"  止损设置: 无止损 (强制平仓: -100%保证金)")
                        print(f"  交易时间: {strategy.start_hour}:00-{strategy.end_hour}:00")
                        print(f"  保证金: {CONTRACT_CONFIG['fixed_margin']} USDT (固定)")
                        print(f"  调试模式: {'🔧 已启用' if strategy.debug_mode else '📊 生产模式'}")
                        if strategy.debug_mode:
                            print(f"  🔧 调试参数:")
                            print(f"    RSI超卖: {strategy.rsi_oversold} (原: 30.0)")
                            print(f"    RSI超买: {strategy.rsi_overbought} (原: 70.0)")
                            print(f"    成交量比例: {strategy.min_volume_ratio} (原: 1.5)")
                            print(f"    价格回调: {strategy.price_pullback*100:.1f}% (原: 1.0%)")
                            print(f"    短期MA: {strategy.ma_short} (原: 5)")
                            print(f"    长期MA: {strategy.ma_long} (原: 20)")
                            print(f"    K线间隔: {strategy.kline_interval} (原: 15m)")
                        print("-" * 50)
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
                # 有信号时显示详细信息
                print(f"\n{'='*60}")
                print(f"🎯 合约交易信号触发 - {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'='*60}")
                print(f"💰 当前价格: {price:.2f} USDT")
                print(f"🎯 信号类型: {'🟢 做多信号' if signal == 1 else '🔴 做空信号'}")
                print(f"📈 持仓状态: {'有持仓' if in_position else '无持仓'}")
                
                # 如果有持仓，显示详细盈亏信息
                if current_position:
                    # 基于保证金计算收益率
                    margin_used = CONTRACT_CONFIG["fixed_margin"]  # 固定保证金
                    pnl_pct_vs_margin = (current_position['unrealized_pnl'] / margin_used) * 100
                    position_type = strategy.position_type or 'unknown'
                    print(f"\n📊 当前持仓详情:")
                    print(f"  持仓类型: {position_type.upper()} ({'做多' if position_type == 'long' else '做空'})")
                    print(f"  合约数量: {current_position['size']:.4f} 张")
                    print(f"  入场价格: {current_position['entry_price']:.2f} USDT")
                    print(f"  未实现盈亏: {current_position['unrealized_pnl']:.2f} USDT")
                    print(f"  保证金收益率: {pnl_pct_vs_margin:.2f}%")
                    print(f"  杠杆倍数: {current_position['leverage']}x")
                    print(f"  保证金: {margin_used:.2f} USDT (固定)")
                print(f"{'='*60}")
            else:
                # 无信号时显示完整状态（每3次循环显示一次）
                if not hasattr(futures_trading_main, 'loop_count'):
                    futures_trading_main.loop_count = 0
                futures_trading_main.loop_count += 1
                
                if futures_trading_main.loop_count % 3 == 0:  # 每3次循环显示一次状态（约3秒显示一次）
                    print(f"\n📊 合约交易状态 - {datetime.now().strftime('%H:%M:%S')}")
                    print(f"{'='*50}")
                    print(f"💰 当前价格: {price:.2f} USDT")
                    print(f"🎯 交易信号: 无")
                    print(f"📈 持仓状态: {'有持仓' if in_position else '无持仓'}")
                    
                    if in_position and current_position:
                        # 基于保证金计算收益率
                        margin_used = CONTRACT_CONFIG["fixed_margin"]  # 固定保证金
                        pnl_pct_vs_margin = (current_position['unrealized_pnl'] / margin_used) * 100
                        position_type = strategy.position_type or 'unknown'
                        print(f"\n📊 持仓详情:")
                        print(f"  持仓类型: {position_type.upper()} ({'做多' if position_type == 'long' else '做空'})")
                        print(f"  合约数量: {current_position['size']:.4f} 张")
                        print(f"  入场价格: {current_position['entry_price']:.2f} USDT")
                        print(f"  未实现盈亏: {current_position['unrealized_pnl']:.2f} USDT")
                        print(f"  保证金收益率: {pnl_pct_vs_margin:.2f}%")
                        print(f"  杠杆倍数: {leverage}x")  # 使用实际设置的杠杆倍数
                        print(f"  保证金: {margin_used:.2f} USDT (固定)")
                    else:
                        print(f"\n📊 无持仓")
                        print(f"  可用资金: {capital:.2f} USDT")
                        print(f"  杠杆倍数: {leverage}x")
                    
                    # 检查当前交易状态
                    if in_position:
                        print(f"📅 当前状态: 有持仓 (不可开新仓)")
                    else:
                        print(f"📅 当前状态: 无持仓 (可开新仓)")
                    
                    # 显示策略状态
                    print(f"🎯 策略状态:")
                    print(f"  止盈设置: {strategy.take_profit * 100:.1f}% (基于保证金)")
                    print(f"  止损设置: 无止损 (强制平仓: -100%保证金)")
                    print(f"  交易时间: {strategy.start_hour}:00-{strategy.end_hour}:00")
                    print(f"  保证金: {CONTRACT_CONFIG['fixed_margin']} USDT (固定)")
                    print(f"  调试模式: {'🔧 已启用' if strategy.debug_mode else '📊 生产模式'}")
                    if strategy.debug_mode:
                        print(f"  🔧 调试参数:")
                        print(f"    RSI超卖: {strategy.rsi_oversold} (原: 30.0)")
                        print(f"    RSI超买: {strategy.rsi_overbought} (原: 70.0)")
                        print(f"    成交量比例: {strategy.min_volume_ratio} (原: 1.5)")
                        print(f"    价格回调: {strategy.price_pullback*100:.1f}% (原: 1.0%)")
                        print(f"    短期MA: {strategy.ma_short} (原: 5)")
                        print(f"    长期MA: {strategy.ma_long} (原: 20)")
                        print(f"    K线间隔: {strategy.kline_interval} (原: 15m)")
                    print("-" * 50)
            
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
                
            if signal == 1 and not in_position:  # 做多信号
                print(f"\n🚀 执行合约做多开仓...")
                
                # 记录开仓原因和策略信息
                logging.info(f"🎯 开仓信号触发 - 做多开仓")
                logging.info(f"📊 开仓原因分析:")
                logging.info(f"  - 策略信号: {signal}")
                logging.info(f"  - 当前价格: {price:.2f} USDT")
                logging.info(f"  - 策略类型: {strategy.__class__.__name__}")
                logging.info(f"  - 调试模式: {strategy.debug_mode}")
                
                # 基于保证金计算合约开仓数量
                position_size = calculate_futures_position_size()
                position_value = position_size * price
                
                # 计算止盈价格
                margin_take_profit_pct = CONTRACT_CONFIG['take_profit_pct']  # 保证金止盈比例：10%
                price_take_profit_pct = margin_take_profit_pct / leverage  # 价格止盈比例：10% ÷ 50 = 0.2%
                take_profit_price = price * (1 + price_take_profit_pct)  # 做多触发价格
                
                print(f"📊 开仓详情: {position_size:.4f}张 | 价格: {price:.2f} | 止盈: {take_profit_price:.2f} | 保证金: {CONTRACT_CONFIG['fixed_margin']}USDT")
                
                # 记录开仓参数
                logging.info(f"📊 开仓参数详情:")
                logging.info(f"  - 合约数量: {position_size:.4f} 张")
                logging.info(f"  - 开仓价格: {price:.2f} USDT")
                logging.info(f"  - 止盈价格: {take_profit_price:.2f} USDT")
                logging.info(f"  - 杠杆倍数: {leverage}x")
                logging.info(f"  - 保证金: {CONTRACT_CONFIG['fixed_margin']} USDT")
                logging.info(f"  - 保证金止盈比例: {margin_take_profit_pct*100:.1f}%")
                logging.info(f"  - 价格止盈比例: {price_take_profit_pct*100:.3f}%")
                
                # 执行做多开仓
                try:
                    print(f"🔄 正在执行做多开仓订单...")
                    logging.info(f"🔄 开始执行合约做多开仓 - 价格: {price:.2f}, 数量: {position_size:.4f}, 杠杆: {leverage}x")
                    
                    order = execute_futures_trade(account, symbol, 'buy', position_size, leverage, "market", None)
                    if order:
                        print(f"✅ 开仓成功! 订单ID: {order.get('id', 'N/A')}")
                        
                        # 立即更新持仓状态，防止重复开仓
                        in_position = True
                        
                        # 激活开仓锁，防止重复开仓
                        trading_lock = True
                        last_trade_time = time.time()
                        print(f"🔒 开仓锁已激活，冷却时间: {trade_cooldown}秒")
                        
                        # 立即获取持仓信息，获取实际入场价格并重新设定止盈
                        time.sleep(2)  # 等待2秒让订单完全生效
                        try:
                            current_position = get_futures_position(account, symbol)
                            if current_position:
                                actual_entry_price = current_position['entry_price']
                                actual_position_size = current_position['size']
                                position_type = current_position.get('posSide', 'long')  # 获取持仓方向
                                
                                # 根据持仓数量计算止盈价格
                                if actual_position_size > 0:  # 做多持仓
                                    # 做多：价格上涨时盈利，止盈价格高于开仓价格
                                    actual_take_profit_price = actual_entry_price * (1 + price_take_profit_pct)
                                else:  # 做空持仓
                                    # 做空：价格下跌时盈利，止盈价格低于开仓价格
                                    actual_take_profit_price = actual_entry_price * (1 - price_take_profit_pct)
                                
                                # 根据持仓方向设置止盈订单
                                try:
                                    # 根据持仓数量判断持仓类型
                                    position_type = 'long' if actual_position_size > 0 else 'short'
                                    tp_order = set_take_profit_order(account, symbol, position_type, actual_position_size, actual_take_profit_price)
                                    if tp_order:
                                        print(f"✅ 止盈设置: {actual_take_profit_price:.2f}")
                                    else:
                                        print(f"⚠️ 止盈设置失败")
                                except Exception as tp_e:
                                    print(f"⚠️ 止盈设置失败: {str(tp_e)}")
                                
                                if abs(price - actual_entry_price) > 10:
                                    print(f"⚠️ 开仓价格与实际入场价格差异较大!")
                                else:
                                    print(f"✅ 开仓价格与实际入场价格一致")
                            else:
                                print(f"⚠️ 无法获取持仓信息")
                        except Exception as e:
                            print(f"⚠️ 获取持仓信息失败: {str(e)}")
                        
                        # 更新策略状态 - 使用实际入场价格
                        actual_entry_price_for_strategy = current_position['entry_price'] if current_position else price
                        strategy.on_position_entry('buy', actual_entry_price_for_strategy, position_size, datetime.now())
                        
                        # 记录交易
                        trade_data = {
                            "timestamp": datetime.now(),
                            "symbol": symbol,
                            "side": "buy",
                            "size": position_size,
                            "price": actual_entry_price_for_strategy,
                            "value": position_value,
                            "type": "futures_long_entry",
                            "leverage": leverage,
                            "order_id": order.get("id", ""),
                            "status": order.get("status", "")
                        }
                        trade_monitor.record_trade(trade_data)
                        
                        # 更新持仓状态
                        in_position = True
                        print(f"✅ 已更新持仓状态")
                        logging.info(f"✅ 已更新持仓状态")
                    else:
                        print("❌ 开仓失败")
                        
                except Exception as e:
                    print(f"❌ 开仓失败: {str(e)}")
                    continue
                    
            elif signal == -1 and not in_position:  # 做空信号
                print(f"\n🔴 执行合约做空开仓...")
                
                # 记录开仓原因和策略信息
                logging.info(f"🎯 开仓信号触发 - 做空开仓")
                logging.info(f"📊 开仓原因分析:")
                logging.info(f"  - 策略信号: {signal}")
                logging.info(f"  - 当前价格: {price:.2f} USDT")
                logging.info(f"  - 策略类型: {strategy.__class__.__name__}")
                logging.info(f"  - 调试模式: {strategy.debug_mode}")
                
                # 基于保证金计算合约开仓数量
                position_size = calculate_futures_position_size()
                position_value = position_size * price
                
                # 计算止盈价格
                margin_take_profit_pct = CONTRACT_CONFIG['take_profit_pct']  # 保证金止盈比例：10%
                price_take_profit_pct = margin_take_profit_pct / leverage  # 价格止盈比例：10% ÷ 50 = 0.2%
                take_profit_price = price * (1 - price_take_profit_pct)  # 做空触发价格
                
                print(f"📊 开仓详情: {position_size:.4f}张 | 价格: {price:.2f} | 止盈: {take_profit_price:.2f} | 保证金: {CONTRACT_CONFIG['fixed_margin']}USDT")
                
                # 记录开仓参数
                logging.info(f"📊 开仓参数详情:")
                logging.info(f"  - 合约数量: {position_size:.4f} 张")
                logging.info(f"  - 开仓价格: {price:.2f} USDT")
                logging.info(f"  - 止盈价格: {take_profit_price:.2f} USDT")
                logging.info(f"  - 杠杆倍数: {leverage}x")
                logging.info(f"  - 保证金: {CONTRACT_CONFIG['fixed_margin']} USDT")
                logging.info(f"  - 保证金止盈比例: {margin_take_profit_pct*100:.1f}%")
                logging.info(f"  - 价格止盈比例: {price_take_profit_pct*100:.3f}%")
                
                # 执行做空开仓
                try:
                    print(f"🔄 正在执行做空开仓订单...")
                    logging.info(f"🔄 开始执行合约做空开仓 - 价格: {price:.2f}, 数量: {position_size:.4f}, 杠杆: {leverage}x")
                    
                    order = execute_futures_trade(account, symbol, 'sell', position_size, leverage, "market", None)
                    if order:
                        print(f"✅ 开仓成功! 订单ID: {order.get('id', 'N/A')}")
                        
                        # 立即更新持仓状态，防止重复开仓
                        in_position = True
                        
                        # 激活开仓锁，防止重复开仓
                        trading_lock = True
                        last_trade_time = time.time()
                        print(f"🔒 开仓锁已激活，冷却时间: {trade_cooldown}秒")
                        
                        # 立即获取持仓信息，获取实际入场价格并重新设定止盈
                        time.sleep(2)  # 等待2秒让订单完全生效
                        try:
                            current_position = get_futures_position(account, symbol)
                            if current_position:
                                actual_entry_price = current_position['entry_price']
                                actual_position_size = current_position['size']
                                position_type = current_position.get('posSide', 'short')  # 获取持仓方向
                                
                                # 根据持仓数量计算止盈价格
                                if actual_position_size > 0:  # 做多持仓
                                    # 做多：价格上涨时盈利，止盈价格高于开仓价格
                                    actual_take_profit_price = actual_entry_price * (1 + price_take_profit_pct)
                                else:  # 做空持仓
                                    # 做空：价格下跌时盈利，止盈价格低于开仓价格
                                    actual_take_profit_price = actual_entry_price * (1 - price_take_profit_pct)
                                
                                # 根据持仓方向设置止盈订单
                                try:
                                    # 根据持仓数量判断持仓类型
                                    position_type = 'long' if actual_position_size > 0 else 'short'
                                    tp_order = set_take_profit_order(account, symbol, position_type, actual_position_size, actual_take_profit_price)
                                    if tp_order:
                                        print(f"✅ 止盈设置: {actual_take_profit_price:.2f}")
                                    else:
                                        print(f"⚠️ 止盈设置失败")
                                except Exception as tp_e:
                                    print(f"⚠️ 止盈设置失败: {str(tp_e)}")
                                
                                if abs(price - actual_entry_price) > 10:
                                    print(f"⚠️ 开仓价格与实际入场价格差异较大!")
                                else:
                                    print(f"✅ 开仓价格与实际入场价格一致")
                            else:
                                print(f"⚠️ 无法获取持仓信息")
                        except Exception as e:
                            print(f"⚠️ 获取持仓信息失败: {str(e)}")
                        
                        # 更新策略状态 - 使用实际入场价格
                        actual_entry_price_for_strategy = current_position['entry_price'] if current_position else price
                        strategy.on_position_entry('sell', actual_entry_price_for_strategy, position_size, datetime.now())
                        
                        # 记录交易
                        trade_data = {
                            "timestamp": datetime.now(),
                            "symbol": symbol,
                            "side": "sell",
                            "size": position_size,
                            "price": actual_entry_price_for_strategy,
                            "value": position_value,
                            "type": "futures_short_entry",
                            "leverage": leverage,
                            "order_id": order.get("id", ""),
                            "status": order.get("status", "")
                        }
                        trade_monitor.record_trade(trade_data)
                        
                        # 更新持仓状态
                        in_position = True
                        print(f"✅ 已更新持仓状态")
                        logging.info(f"✅ 已更新持仓状态")
                    else:
                        print("❌ 开仓失败")
                        
                except Exception as e:
                    print(f"❌ 开仓失败: {str(e)}")
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

# 原有的现货交易主程序保持不变
def main():
    print("🚀 启动现货交易模式...")
    if not validate_trading_environment():
        return
    
    # 清理之前的数据
    clear_previous_data()
    
    # 重新配置日志（清理后重新设置）
    setup_logging()
    
    # 1. 选择API信息
    api_key, api_secret, api_password = get_trading_credentials()

    # 2. 初始化API对象
    market_data = MarketDataFetcher(exchange_id='okx', proxy=PROXY)
    account = OKXExecutor(api_key, api_secret, api_password, proxy=PROXY, is_simulated=IS_SIMULATED)
    risk_manager = RiskManager()
    position_manager = PositionManager(market_data, account)
    stop_manager = StopManager()
    trade_monitor = TradeMonitor(log_dir="logs", report_dir="reports")
    risk_monitor = RiskMonitor(
        capital_threshold=RISK_CONFIG['risk_limits']['max_drawdown'],    # 资金预警阈值
        daily_loss_limit=RISK_CONFIG['risk_limits']['daily_loss'],      # 每日最大亏损限制
        max_positions=RISK_CONFIG['risk_limits']['max_positions'],       # 最大同时持仓数
        volatility_threshold=0.03                                        # 波动率预警阈值
    )

    # 3. 初始化策略
    # 使用每日交易策略（50%胜率版本）
    strategy = DailyTradingStrategy(
        take_profit=0.01,      # 1.0%止盈
        stop_loss=0.005,       # 0.5%止损
        rsi_period=21,         # RSI周期
        rsi_oversold=30.0,     # RSI超卖阈值
        ma_short=5,            # 短期MA
        ma_long=20,            # 长期MA
        start_hour=0,          # 开始交易时间（0点）
        end_hour=24,           # 结束交易时间（24点）
        min_volume_ratio=1.2,  # 最小成交量比率
        price_pullback=0.01,   # 价格回调阈值
        
        # 优化参数（保持关闭状态）
        atr_period=14,         # ATR周期
        atr_multiplier=1.5,    # ATR倍数
        use_dynamic_stop=False, # 关闭动态止损
        use_macd=False,        # 关闭MACD确认
        avoid_hours=[],        # 不避开任何时段
        best_hours=[],         # 不限制最佳时段
    )

    # 4. 主循环
    symbol = "BTC-USDT"
    interval = 10  # 10秒
    capital = float(account.get_balance("USDT"))
    print(f"初始资金: {capital} USDT")
    
    # 打印策略配置
    print("=" * 50)
    print("🚀 每日交易策略启动")
    print("=" * 50)
    print(f"策略类型: DailyTradingStrategy")
    print(f"止盈设置: {strategy.take_profit * 100:.1f}%")
    print(f"止损设置: 0.5%")
    print(f"RSI周期: {strategy.rsi_period}")
    print(f"MA设置: {strategy.ma_short}/{strategy.ma_long}")
    print(f"交易时间: {strategy.start_hour}:00-{strategy.end_hour}:00")
    print(f"每日交易限制: 1次")
    print("=" * 50)
    
    # 交易状态管理
    in_position = False  # 是否持有仓位
    MIN_POSITION_SIZE = 0.00001  # 最小持仓数量阈值（BTC）
    MIN_ORDER_VALUE = 5  # 最小下单价值阈值（USDT）

    while True:
        try:
            # 每日重置交易状态
            current_date = datetime.now().strftime('%Y-%m-%d')
            if hasattr(strategy, 'daily_traded') and current_date not in strategy.daily_traded:
                print(f"🔄 新的一天开始: {current_date}")
            
            # 更新市场数据
            price = float(market_data.get_ticker(symbol)['last'])
            
            # 获取持仓信息（静默获取，不打印）
            try:
                btc_balance = account.get_balance("BTC")
                usdt_balance = account.get_balance("USDT")
                if btc_balance >= MIN_POSITION_SIZE:
                    in_position = True
                else:
                    in_position = False
            except Exception as e:
                print(f"❌ 获取账户信息失败: {str(e)}")
                continue

            # 获取策略信号
            # 现货交易对格式转换，用于获取K线数据
            if symbol.endswith('-SWAP'):
                ohlcv_symbol = symbol.replace('-SWAP', '')
            else:
                ohlcv_symbol = symbol
            
            ohlcv_data = market_data.get_ohlcv(ohlcv_symbol, timeframe=CONTRACT_CONFIG.get('kline_interval', '1m'))
            signal = strategy.generate_signal(ohlcv_data)
            
            # 只在有信号时打印详细信息
            if signal != 0:
                print(f"\n{'='*50}")
                print(f"🎯 交易信号触发 - {datetime.now().strftime('%H:%M:%S')}")
                print(f"当前价格: {price:.2f}")
                print(f"信号类型: {'🟢 买入' if signal == 1 else '🔴 卖出'}")
                print(f"策略持仓: {'有持仓' if hasattr(strategy, 'current_position') and strategy.current_position > 0 else '无持仓'}")
                
                # 如果有持仓，显示盈亏信息
                if hasattr(strategy, 'current_position') and strategy.current_position > 0 and hasattr(strategy, 'entry_price'):
                    pnl_pct = ((price - strategy.entry_price) / strategy.entry_price * 100)
                    print(f"入场价格: {strategy.entry_price:.2f}")
                    print(f"当前盈亏: {pnl_pct:.2f}%")
                print(f"{'='*50}")
            else:
                # 无信号时只显示简单状态（每10次循环显示一次）
                if not hasattr(main, 'loop_count'):
                    main.loop_count = 0
                main.loop_count += 1
                
                if main.loop_count % 10 == 0:  # 每10次循环显示一次状态
                    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - 价格: {price:.2f} | 信号: 无 | 持仓: {'是' if in_position else '否'}")

            # 风控与下单逻辑
            # 检查是否已经交易过今天
            today = datetime.now().strftime('%Y-%m-%d')
            if hasattr(strategy, 'daily_traded') and strategy.daily_traded.get(today, False):
                print(f"ℹ️ 今日已交易，跳过交易机会")
                
            elif signal == 1 and not in_position:  # 买入信号且当前无仓位
                print(f"\n🚀 执行买入交易...")
                
                stop_loss = price * 0.98
                position_size = position_manager.calculate_position_size(symbol, stop_loss) * 0.5
                position_value = position_size * price
                
                # 检查下单价值是否满足最小要求
                if position_value < MIN_ORDER_VALUE:
                    print(f"⚠️ 下单价值 {position_value:.2f} USDT 小于最小要求 {MIN_ORDER_VALUE} USDT")
                    continue
                
                position_ratio = position_value / capital
                
                if position_ratio > MONITOR_CONFIG['alert_thresholds']['position_limit']:
                    print(f"⚠️ 仓位比例 {position_ratio*100:.2f}% 超过限制")
                    continue
                    
                print(f"📊 交易详情:")
                print(f"  开仓数量: {position_size:.6f} BTC")
                print(f"  交易价值: {position_value:.2f} USDT")
                print(f"  仓位比例: {position_ratio*100:.2f}%")
                
                if position_size >= MIN_POSITION_SIZE and risk_manager.check_position_limit(symbol, position_size, capital):
                    try:
                        order = account.place_order(symbol, order_type="market", side="buy", amount=position_size)
                        print(f"✅ 买入成功! 订单ID: {order.get('id', 'N/A')}")
                        in_position = True
                    
                        # 记录交易
                        trade_data = {
                            "timestamp": datetime.now(),
                            "symbol": symbol,
                            "side": "buy",
                            "size": position_size,
                            "price": price,
                            "value": position_value,
                            "type": "entry",
                            "order_id": order.get("id", ""),
                            "status": order.get("status", "")
                        }
                        trade_monitor.record_trade(trade_data)
                        
                        # 标记今日已交易
                        if hasattr(strategy, 'daily_traded'):
                            strategy.daily_traded[today] = True
                            print(f"✅ 已标记今日 {today} 为已交易")
                        
                    except Exception as e:
                        print(f"❌ 买入失败: {str(e)}")
                        continue
                else:
                    print("❌ 风控未通过，无法买入")
                    
            elif signal == -1 and in_position:  # 卖出信号且当前有仓位
                print(f"\n🔴 执行卖出交易...")
                
                # 获取BTC余额
                btc_balance = account.get_balance("BTC")
                
                if btc_balance >= MIN_POSITION_SIZE:  # 使用最小持仓阈值判断
                    try:
                        order = account.place_order(symbol, order_type="market", side="sell", amount=btc_balance)
                        print(f"✅ 卖出成功! 订单ID: {order.get('id', 'N/A')}")
                        print(f"📊 卖出详情:")
                        print(f"  卖出数量: {btc_balance:.6f} BTC")
                        print(f"  卖出价格: {price:.2f} USDT")
                        print(f"  交易价值: {btc_balance * price:.2f} USDT")
                        in_position = False
                    
                    # 记录交易
                        trade_data = {
                        "timestamp": datetime.now(),
                        "symbol": symbol,
                        "side": "sell",
                            "size": btc_balance,
                        "price": price,
                            "value": btc_balance * price,
                            "type": "exit",
                            "order_id": order.get("id", ""),
                            "status": order.get("status", "")
                        }
                        trade_monitor.record_trade(trade_data)
                        
                    except Exception as e:
                        print(f"❌ 卖出失败: {str(e)}")
                        continue
                else:
                    print("ℹ️ BTC余额小于最小交易数量")
                    
            # 止损止盈监控
            position_info = account.get_position(symbol)
            size = float(position_info["contracts"]) if position_info and position_info.get("contracts", 0) > 0 else 0
            if size > 0:
                entry_price = float(position_info["entryPrice"])
                current_price = price
                stop_result = stop_manager.update_stops(symbol, current_price)
                
                if stop_result["stop_loss_triggered"] or stop_result["take_profit_triggered"]:
                    stop_type = "止损" if stop_result["stop_loss_triggered"] else "止盈"
                    print(f"\n🚨 {stop_type}触发!")
                    
                    try:
                        order = account.place_order(symbol, order_type="market", side="sell", amount=size)
                        print(f"✅ {stop_type}执行成功! 订单ID: {order.get('id', 'N/A')}")
                    
                        # 计算收益
                        profit = (current_price - entry_price) * size
                        profit_pct = (profit / (entry_price * size)) * 100
                        
                        print(f"📊 {stop_type}详情:")
                        print(f"  卖出数量: {size:.6f} BTC")
                        print(f"  入场价格: {entry_price:.2f} USDT")
                        print(f"  卖出价格: {current_price:.2f} USDT")
                        print(f"  盈亏金额: {profit:.2f} USDT")
                        print(f"  盈亏比例: {profit_pct:.2f}% (基于交易价值)")
                    
                    # 记录交易
                        trade_data = {
                        "timestamp": datetime.now(),
                        "symbol": symbol,
                        "side": "sell",
                        "size": size,
                        "price": current_price,
                            "value": size * current_price,
                        "profit": profit if profit > 0 else 0,
                        "loss": abs(profit) if profit < 0 else 0,
                            "type": "stop" if stop_result["stop_loss_triggered"] else "take_profit",
                            "order_id": order.get("id", ""),
                            "status": order.get("status", "")
                        }
                        trade_monitor.record_trade(trade_data)
                        
                        # 移除止损止盈
                        stop_manager.remove_stops(symbol)
                        
                        # 清空持仓监控
                        trade_monitor.update_position(symbol, {})
                        
                    except Exception as e:
                        print(f"❌ {stop_type}执行失败: {str(e)}")
                        continue
            
            # 更新持仓监控
                position_data = {
                    "size": size,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "unrealized_pnl": (current_price - entry_price) * size
                }
                trade_monitor.update_position(symbol, position_data)
            
            # 更新系统指标
            initial_capital = float(account.get_balance("USDT"))
            metrics = {
                "current_capital": capital,
                "initial_capital": initial_capital,
                "drawdown": (initial_capital - capital) / initial_capital if initial_capital > 0 else 0,
                "daily_pnl": risk_monitor.daily_pnl,
                "position_count": len(trade_monitor.positions),
                "positions": trade_monitor.positions,
                "recent_alerts": risk_monitor.alerts[-10:] if risk_monitor.alerts else [],
                "total_exposure": sum(pos.get("value", 0) for pos in trade_monitor.positions.values())
            }
            trade_monitor.update_system_metrics(metrics)
            
            # 打印中文系统状态和交易信号
            if main.loop_count % 10 == 0:  # 每10次循环显示一次
                print(f"\n📊 系统状态 - {datetime.now().strftime('%H:%M:%S')}")
                print(f"💰 当前资金: {capital:.2f} USDT")
                print(f"📈 初始资金: {initial_capital:.2f} USDT")
                print(f"📉 回撤比例: {((initial_capital - capital) / initial_capital * 100):.2f}%" if initial_capital > 0 else "📉 回撤比例: 0.00%")
                print(f"📅 当日盈亏: {risk_monitor.daily_pnl:.2f} USDT")
                print(f"📊 持仓数量: {len(trade_monitor.positions)}")
                print(f"💼 总敞口: {sum(pos.get('value', 0) for pos in trade_monitor.positions.values()):.2f} USDT")
                
                # 显示当前交易信号状态
                if hasattr(strategy, 'current_position') and strategy.current_position > 0:
                    if hasattr(strategy, 'entry_price'):
                        current_pnl = ((price - strategy.entry_price) / strategy.entry_price * 100)
                        print(f"🎯 当前持仓: 有")
                        print(f"📍 入场价格: {strategy.entry_price:.2f} USDT")
                        print(f"📊 当前盈亏: {current_pnl:.2f}%")
                        print(f"🎯 止盈目标: {strategy.take_profit * 100:.1f}%")
                        print(f"🛑 止损线: 0.5%")
                else:
                    print(f"🎯 当前持仓: 无")
                    print(f"🔍 等待买入信号...")
                
                print("-" * 50)
            
            time.sleep(interval)
        except Exception as e:
            print(f"❌ 主循环异常: {e}")
            time.sleep(10)
            continue

if __name__ == "__main__":
    # main() 
    futures_trading_main()
