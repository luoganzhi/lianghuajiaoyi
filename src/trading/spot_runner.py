import time
from datetime import datetime

from src.config.config import CONTRACT_CONFIG, IS_SIMULATED, MONITOR_CONFIG, PROXY, RISK_CONFIG
from src.data.market_data import MarketDataFetcher
from src.execution.okx_executor import OKXExecutor
from src.monitor.trade_monitor import TradeMonitor
from src.risk.position_manager import PositionManager
from src.risk.risk_manager import RiskManager
from src.risk.risk_monitor import RiskMonitor
from src.risk.stop_manager import StopManager
from src.runtime.app_runtime import clear_previous_data, setup_logging
from src.strategies.daily_trading_strategy import DailyTradingStrategy
from src.trading.environment import get_trading_credentials, validate_trading_environment


def spot_trading_main():
    """现货交易主程序。"""
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
    print("策略类型: DailyTradingStrategy")
    print(f"止盈设置: {strategy.take_profit * 100:.1f}%")
    print("止损设置: 0.5%")
    print(f"RSI周期: {strategy.rsi_period}")
    print(f"MA设置: {strategy.ma_short}/{strategy.ma_long}")
    print(f"交易时间: {strategy.start_hour}:00-{strategy.end_hour}:00")
    print("每日交易限制: 1次")
    print("=" * 50)

    # 交易状态管理
    in_position = False  # 是否持有仓位
    min_position_size = 0.00001  # 最小持仓数量阈值（BTC）
    min_order_value = 5  # 最小下单价值阈值（USDT）
    spot_trading_main.loop_count = 0

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
                account.get_balance("USDT")
                if btc_balance >= min_position_size:
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
                if not hasattr(spot_trading_main, 'loop_count'):
                    spot_trading_main.loop_count = 0
                spot_trading_main.loop_count += 1

                if spot_trading_main.loop_count % 10 == 0:  # 每10次循环显示一次状态
                    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - 价格: {price:.2f} | 信号: 无 | 持仓: {'是' if in_position else '否'}")

            # 风控与下单逻辑
            # 检查是否已经交易过今天
            today = datetime.now().strftime('%Y-%m-%d')
            if hasattr(strategy, 'daily_traded') and strategy.daily_traded.get(today, False):
                print("ℹ️ 今日已交易，跳过交易机会")

            elif signal == 1 and not in_position:  # 买入信号且当前无仓位
                print("\n🚀 执行买入交易...")

                stop_loss = price * 0.98
                position_size = position_manager.calculate_position_size(symbol, stop_loss) * 0.5
                position_value = position_size * price

                # 检查下单价值是否满足最小要求
                if position_value < min_order_value:
                    print(f"⚠️ 下单价值 {position_value:.2f} USDT 小于最小要求 {min_order_value} USDT")
                    continue

                position_ratio = position_value / capital

                if position_ratio > MONITOR_CONFIG['alert_thresholds']['position_limit']:
                    print(f"⚠️ 仓位比例 {position_ratio*100:.2f}% 超过限制")
                    continue

                print("📊 交易详情:")
                print(f"  开仓数量: {position_size:.6f} BTC")
                print(f"  交易价值: {position_value:.2f} USDT")
                print(f"  仓位比例: {position_ratio*100:.2f}%")

                if position_size >= min_position_size and risk_manager.check_position_limit(symbol, position_size, capital):
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
                print("\n🔴 执行卖出交易...")

                # 获取BTC余额
                btc_balance = account.get_balance("BTC")

                if btc_balance >= min_position_size:  # 使用最小持仓阈值判断
                    try:
                        order = account.place_order(symbol, order_type="market", side="sell", amount=btc_balance)
                        print(f"✅ 卖出成功! 订单ID: {order.get('id', 'N/A')}")
                        print("📊 卖出详情:")
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
            if spot_trading_main.loop_count % 10 == 0:  # 每10次循环显示一次
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
                        print("🎯 当前持仓: 有")
                        print(f"📍 入场价格: {strategy.entry_price:.2f} USDT")
                        print(f"📊 当前盈亏: {current_pnl:.2f}%")
                        print(f"🎯 止盈目标: {strategy.take_profit * 100:.1f}%")
                        print("🛑 止损线: 0.5%")
                else:
                    print("🎯 当前持仓: 无")
                    print("🔍 等待买入信号...")

                print("-" * 50)

            time.sleep(interval)
        except Exception as e:
            print(f"❌ 主循环异常: {e}")
            time.sleep(10)
            continue
