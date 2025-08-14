#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合约策略回测脚本 - 测试ContractDailyTradingStrategy
支持高杠杆、双向交易、逐仓模式等合约特性
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import ccxt

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 直接导入策略，避免复杂的模块导入
sys.path.insert(0, os.path.join(project_root, 'strategies'))
from contract_daily_trading_strategy import ContractDailyTradingStrategy

# 导入真实数据获取模块
from data.market_data import MarketDataFetcher

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_test_data(symbol="BTC-USDT", days=30, interval="15m"):
    """
    获取真实测试数据
    """
    try:
        print(f"📊 获取 {symbol} 的 {days} 天 {interval} K线数据...")
        
        # 使用成功的代理配置
        proxy = 'http://127.0.0.1:7890'
        print(f"🔧 使用代理配置: {proxy}")
        
        # 创建市场数据获取器
        market_data = MarketDataFetcher('okx', proxy=proxy)
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        print(f"📅 请求数据时间范围: {start_time} 到 {end_time}")
        
        # 获取历史数据
        data = market_data.get_historical_ohlcv(
            symbol=symbol,
            timeframe=interval,
            start_date=start_time,
            end_date=end_time
        )
        
        if data is None or len(data) == 0:
            raise Exception("API返回空数据")
        
        print(f"✅ 成功获取 {len(data)} 条K线数据")
        print(f"📅 数据时间范围: {data.index[0]} 到 {data.index[-1]}")
        
        # 显示数据样本
        print(f"📊 数据样本:")
        print(data.head())
        print(f"📊 数据统计:")
        print(f"  开盘价范围: {data['open'].min():.2f} - {data['open'].max():.2f}")
        print(f"  收盘价范围: {data['close'].min():.2f} - {data['close'].max():.2f}")
        print(f"  成交量范围: {data['volume'].min():.2f} - {data['volume'].max():.2f}")
        
        return data
        
    except Exception as e:
        print(f"❌ 获取市场数据失败: {e}")
        raise Exception(f"无法获取真实市场数据: {e}")

def create_mock_data(days=30, interval="15m"):
    """
    创建模拟数据用于回测
    """
    print("🔧 创建模拟数据...")
    
    # 计算K线数量
    if interval == "15m":
        klines_per_day = 96  # 24小时 * 4 (15分钟)
    elif interval == "1h":
        klines_per_day = 24
    else:
        klines_per_day = 96
    
    total_klines = days * klines_per_day
    
    # 生成时间序列
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=total_klines * 15 if interval == "15m" else total_klines * 60)
    
    if interval == "15m":
        timestamps = pd.date_range(start=start_time, end=end_time, freq='15min')
    else:
        timestamps = pd.date_range(start=start_time, end=end_time, freq='H')
    
    # 确保时间戳数量正确
    timestamps = timestamps[:total_klines]
    
    # 生成价格数据（模拟BTC价格走势）
    np.random.seed(42)  # 固定随机种子，确保结果可重现
    
    # 基础价格
    base_price = 120000
    
    # 生成价格序列（带趋势和波动）
    price_changes = np.random.normal(0, 0.02, total_klines)  # 2%的标准差
    trend = np.linspace(0, 0.1, total_klines)  # 轻微上涨趋势
    
    prices = [base_price]
    for i in range(1, total_klines):
        new_price = prices[-1] * (1 + price_changes[i] + trend[i] * 0.001)
        prices.append(max(new_price, base_price * 0.8))  # 防止价格过低
    
    # 生成OHLCV数据
    data = []
    for i, (timestamp, price) in enumerate(zip(timestamps, prices)):
        # 生成OHLC
        volatility = price * 0.01  # 1%的波动
        high = price + np.random.uniform(0, volatility)
        low = price - np.random.uniform(0, volatility)
        open_price = price + np.random.uniform(-volatility/2, volatility/2)
        close_price = price
        
        # 生成成交量
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data, index=timestamps)
    print(f"✅ 模拟数据创建完成: {len(df)} 条K线")
    return df

def run_contract_backtest(strategy, data, initial_cash=100000, leverage=50):
    """
    运行合约策略回测 - 简化版本
    """
    print(f"\n🚀 开始合约策略回测...")
    print(f"💰 初始资金: {initial_cash:,.2f} USDT")
    print(f"⚡ 杠杆倍数: {leverage}x")
    print(f"📊 数据量: {len(data)} 条K线")
    
    # 生成交易信号
    print("🎯 生成交易信号...")
    signals = strategy.generate_signals(data)
    
    # 统计信号
    buy_signals = sum(1 for s in signals if s == 1)
    sell_signals = sum(1 for s in signals if s == -1)
    total_signals = buy_signals + sell_signals
    
    print(f"📈 买入信号: {buy_signals}")
    print(f"📉 卖出信号: {sell_signals}")
    print(f"🎯 总信号数: {total_signals}")
    
    if total_signals == 0:
        print("❌ 没有生成任何交易信号，无法进行回测")
        return None
    
    # 简化回测逻辑
    print("🔄 运行简化回测...")
    
    # 模拟交易
    current_cash = initial_cash
    current_position = 0
    entry_price = 0
    trades = []
    equity_curve = [initial_cash]
    
    # 遍历每个时间点
    for i, (timestamp, row) in enumerate(data.iterrows()):
        signal = signals[i] if i < len(signals) else 0
        current_price = row['close']
        
        # 检查是否应该平仓
        if current_position != 0:
            # 检查止盈条件 - 基于保证金计算收益率
            if current_position > 0:  # 做多
                # 计算未实现盈亏
                unrealized_pnl = (current_price - entry_price) * current_position
                # 基于保证金计算收益率
                profit_pct = unrealized_pnl / 100  # 100 USDT保证金
                if profit_pct >= strategy.take_profit:
                    # 平仓
                    exit_value = current_position * current_price
                    fee = exit_value * 0.0005  # 0.05%手续费
                    pnl = exit_value - (current_position * entry_price) - fee
                    # 返还保证金 + 盈亏
                    current_cash += 100 + pnl
                    
                    trades.append({
                        'entry_time': entry_price,
                        'exit_time': current_price,
                        'side': 'long',
                        'pnl': pnl,
                        'profit_pct': profit_pct * 100
                    })
                    
                    print(f"💰 做多止盈: 入场 {entry_price:.2f}, 出场 {current_price:.2f}, 盈利 {pnl:.2f} USDT ({profit_pct*100:.2f}%)")
                    
                    current_position = 0
                    entry_price = 0
                    
            elif current_position < 0:  # 做空
                # 计算未实现盈亏
                unrealized_pnl = (entry_price - current_price) * abs(current_position)
                # 基于保证金计算收益率
                profit_pct = unrealized_pnl / 100  # 100 USDT保证金
                if profit_pct >= strategy.take_profit:
                    # 平仓
                    exit_value = abs(current_position) * current_price
                    fee = exit_value * 0.0005  # 0.05%手续费
                    pnl = (entry_price - current_price) * abs(current_position) - fee
                    # 返还保证金 + 盈亏
                    current_cash += 100 + pnl
                    
                    trades.append({
                        'entry_time': entry_price,
                        'exit_time': current_price,
                        'side': 'short',
                        'pnl': pnl,
                        'profit_pct': profit_pct * 100
                    })
                    
                    print(f"💰 做空止盈: 入场 {entry_price:.2f}, 出场 {current_price:.2f}, 盈利 {pnl:.2f} USDT ({profit_pct*100:.2f}%)")
                    
                    current_position = 0
                    entry_price = 0
        
        # 检查开仓信号
        if current_position == 0 and signal != 0:
            # 固定每次交易使用100 USDT
            trade_amount = 100  # 每次交易100 USDT
            
            # 检查是否有足够资金开仓
            if current_cash < trade_amount:
                print(f"⚠️ 资金不足，无法开仓，当前资金: {current_cash:.2f} USDT")
                continue
            
            if signal == 1:  # 做多信号
                # 计算可用保证金（杠杆计算修正）
                # 50倍杠杆意味着用100 USDT可以控制5000 USDT的仓位
                position_size = (trade_amount * leverage) / current_price
                
                # 开仓 - 扣除保证金
                current_cash -= trade_amount
                current_position = position_size
                entry_price = current_price
                print(f"📈 做多开仓: 价格 {current_price:.2f}, 数量 {position_size:.4f}, 使用资金 {trade_amount:.2f} USDT, 剩余资金: {current_cash:.2f} USDT")
                
            elif signal == -1:  # 做空信号
                # 计算可用保证金（杠杆计算修正）
                position_size = (trade_amount * leverage) / current_price
                
                # 开仓 - 扣除保证金
                current_cash -= trade_amount
                current_position = -position_size
                entry_price = current_price
                print(f"📉 做空开仓: 价格 {current_price:.2f}, 数量 {position_size:.4f}, 使用资金 {trade_amount:.2f} USDT, 剩余资金: {current_cash:.2f} USDT")
        
        # 记录权益
        if current_position != 0:
            # 计算当前持仓价值
            if current_position > 0:  # 做多
                position_value = current_position * current_price
                unrealized_pnl = position_value - (current_position * entry_price)
            else:  # 做空
                position_value = abs(current_position) * current_price
                unrealized_pnl = (entry_price - current_price) * abs(current_position)
            
            # 基于保证金计算收益率
            margin_used = 100  # 每次交易使用100 USDT保证金
            profit_pct_vs_margin = unrealized_pnl / margin_used
            
            # 检查保证金是否充足（强制平仓机制）
            if unrealized_pnl < -margin_used:  # 亏损超过保证金
                # 强制平仓
                if current_position > 0:  # 做多
                    exit_value = current_position * current_price
                    fee = exit_value * 0.0005
                    pnl = exit_value - (current_position * entry_price) - fee
                else:  # 做空
                    exit_value = abs(current_position) * current_price
                    fee = exit_value * 0.0005
                    pnl = (entry_price - current_price) * abs(current_position) - fee
                
                # 返还保证金 + 盈亏
                current_cash += margin_used + pnl
                
                trades.append({
                    'entry_time': entry_price,
                    'exit_time': current_price,
                    'side': 'long' if current_position > 0 else 'short',
                    'pnl': pnl,
                    'profit_pct': (pnl / (margin_used * leverage)) * 100,
                    'exit_reason': 'margin_call'
                })
                
                print(f"🚨 强制平仓: 入场 {entry_price:.2f}, 出场 {current_price:.2f}, 亏损 {pnl:.2f} USDT (保证金不足)")
                
                current_position = 0
                entry_price = 0
                unrealized_pnl = 0
            
            # 权益 = 现金 + 未实现盈亏（修正：强制平仓后unrealized_pnl=0）
            current_equity = current_cash + unrealized_pnl
            
            # 调试信息
            if i % 100 == 0:  # 每100个周期打印一次
                print(f"📊 第{i}周期: 价格={current_price:.2f}, 持仓={current_position:.4f}, 未实现盈亏={unrealized_pnl:.2f}, 保证金收益率={profit_pct_vs_margin*100:.2f}%, 权益={current_equity:.2f}")
        else:
            current_equity = current_cash
        
        equity_curve.append(current_equity)
    
    # 计算最终结果
    final_equity = equity_curve[-1]
    total_return = (final_equity - initial_cash) / initial_cash
    
    # 计算最大回撤
    peak = initial_cash
    max_drawdown = 0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        drawdown = (peak - equity) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return {
        'initial_cash': initial_cash,
        'final_equity': final_equity,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'trades': trades,
        'equity_curve': equity_curve
    }

def print_backtest_results(results):
    """
    打印回测结果
    """
    if results is None:
        return
    
    print("\n" + "="*60)
    print("📊 合约策略回测结果")
    print("="*60)
    
    # 基本指标
    print(f"💰 初始资金: {results['initial_cash']:,.2f} USDT")
    print(f"📈 最终资金: {results['final_equity']:,.2f} USDT")
    print(f"🎯 总收益率: {results['total_return']*100:.2f}%")
    print(f"📉 最大回撤: {results['max_drawdown']*100:.2f}%")
    
    # 交易统计
    trades = results['trades']
    if trades:
        print(f"\n📋 交易统计:")
        print(f"  总交易次数: {len(trades)}")
        
        # 计算盈亏
        profits = [t['pnl'] for t in trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in trades if t['pnl'] < 0]
        
        if profits:
            avg_profit = np.mean(profits)
            print(f"  盈利交易: {len(profits)} 次")
            print(f"  平均盈利: {avg_profit:.2f} USDT")
        
        if losses:
            avg_loss = np.mean(losses)
            print(f"  亏损交易: {len(losses)} 次")
            print(f"  平均亏损: {avg_loss:.2f} USDT")
        
        if profits and losses:
            win_rate = len(profits) / len(trades) * 100
            profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
            print(f"  胜率: {win_rate:.1f}%")
            print(f"  盈亏比: {profit_loss_ratio:.2f}")
        
        # 计算总盈亏
        total_profit = sum(profits) if profits else 0
        total_loss = sum(losses) if losses else 0
        net_pnl = total_profit + total_loss
        
        print(f"  总盈利: {total_profit:.2f} USDT")
        print(f"  总亏损: {total_loss:.2f} USDT")
        print(f"  净盈亏: {net_pnl:.2f} USDT")
        
        # 显示详细交易记录
        print(f"\n📝 详细交易记录:")
        for i, trade in enumerate(trades, 1):
            print(f"  交易 {i}: {trade['side'].upper()} | "
                  f"入场: {trade['entry_time']:.2f} | "
                  f"出场: {trade['exit_time']:.2f} | "
                  f"盈利: {trade['pnl']:.2f} USDT ({trade['profit_pct']:.2f}%)")
    else:
        print(f"\n📋 交易统计: 无交易记录")
    
    # 策略信息
    print(f"\n🎯 策略配置:")
    print(f"  策略类型: ContractDailyTradingStrategy")
    print(f"  杠杆倍数: 50x")
    print(f"  单次交易资金: 100 USDT")
    print(f"  止盈设置: 5%")
    print(f"  止损设置: 无止损")
    print(f"  保证金模式: 逐仓")
    print(f"  K线间隔: 15分钟")

def test_okx_connection():
    """
    测试OKX连接
    """
    try:
        print("🔍 测试OKX API连接...")
        
        # 尝试不同的网络配置
        configs = [

            {'timeout': 30000, 'enableRateLimit': True, 'proxies': {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}},
        ]
        
        for i, config in enumerate(configs, 1):
            try:
                print(f"🔧 尝试配置 {i}: {config}")
                exchange = ccxt.okx(config)
                
                # 测试连接
                ticker = exchange.fetch_ticker('BTC/USDT')
                print(f"✅ OKX连接成功！当前BTC价格: {ticker['last']:.2f} USDT")
                print(f"🔧 使用配置: {config}")
                return True
                
            except Exception as e:
                print(f"❌ 配置 {i} 失败: {e}")
                if i < len(configs):
                    print("🔄 尝试下一个配置...")
                continue
        
        print("❌ 所有配置都失败了")
        return False
        
    except Exception as e:
        print(f"❌ OKX连接测试异常: {e}")
        return False

def main():
    """
    主函数
    """
    print("🚀 合约策略回测系统")
    print("="*50)
    
    # 策略参数
    strategy_params = {
        'take_profit': 0.50,           # 50%止盈（基于保证金，更容易触发）
        'rsi_period': 14,              # RSI周期
        'rsi_oversold': 25.0,          # RSI超卖阈值（降低，更容易触发）
        'rsi_overbought': 75.0,        # RSI超买阈值（提高，更容易触发）
        'ma_short': 5,                 # 短期MA
        'ma_long': 20,                 # 长期MA
        'min_volume_ratio': 1.2,       # 最小成交量比例（降低，更容易满足）
        'price_pullback': 0.005,       # 价格回调比例（降低，更容易满足）
        'start_hour': 0,               # 开始交易时间
        'end_hour': 24,                # 结束交易时间
        'kline_interval': '15m'        # K线间隔
    }
    
    # 回测参数
    backtest_params = {
        'days': 7,                     # 回测天数（改为7天，确保有足够数据）
        'initial_cash': 100000,        # 初始资金
        'leverage': 50                 # 杠杆倍数
    }
    
    try:
        # 0. 测试网络连接
        if not test_okx_connection():
            raise Exception("无法连接到OKX API，请检查网络配置")
        
        # 1. 创建策略
        print("🔧 创建合约交易策略...")
        strategy = ContractDailyTradingStrategy(**strategy_params)
        print("✅ 策略创建成功")
        
        # 2. 获取真实测试数据
        data = get_test_data(
            symbol="BTC-USDT",
            days=backtest_params['days'],
            interval=strategy_params['kline_interval']
        )
        
        # 3. 运行回测
        results = run_contract_backtest(
            strategy=strategy,
            data=data,
            initial_cash=backtest_params['initial_cash'],
            leverage=backtest_params['leverage']
        )
        
        # 4. 显示结果
        print_backtest_results(results)
        
        # 5. 保存结果
        if results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"contract_backtest_results_{timestamp}.csv"
            
            # 保存权益曲线
            equity_df = pd.DataFrame({
                'step': range(len(results['equity_curve'])),
                'equity': results['equity_curve']
            })
            equity_df.to_csv(filename, index=False)
            print(f"\n💾 权益曲线已保存到: {filename}")
        
    except Exception as e:
        print(f"❌ 回测过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
