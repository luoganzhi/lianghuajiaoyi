#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化合约策略回测脚本 - 测试ContractDailyTradingStrategy
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 直接导入策略
sys.path.insert(0, os.path.join(project_root, 'strategies'))
from contract_daily_trading_strategy import ContractDailyTradingStrategy

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        timestamps = pd.date_range(start=start_time, end=end_time, freq='15T')
    else:
        timestamps = pd.date_range(start=start_time, end=end_time, freq='H')
    
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

def simple_backtest(strategy, data, initial_cash=100000, leverage=50):
    """
    简单的回测实现
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
    
    # 模拟交易
    print("🔄 模拟交易执行...")
    
    # 初始化变量
    current_cash = initial_cash
    current_position = 0
    entry_price = 0
    entry_time = None
    trades = []
    equity_curve = [initial_cash]
    
    # 遍历每个时间点
    for i, (timestamp, row) in enumerate(data.iterrows()):
        signal = signals[i] if i < len(signals) else 0
        current_price = row['close']
        
        # 检查是否应该平仓
        if current_position != 0:
            # 检查止盈条件
            if current_position > 0:  # 做多
                profit_pct = (current_price - entry_price) / entry_price
                if profit_pct >= strategy.take_profit:
                    # 平仓
                    exit_value = current_position * current_price
                    fee = exit_value * 0.0005  # 0.05%手续费
                    pnl = exit_value - (current_position * entry_price) - fee
                    current_cash += exit_value - fee
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': timestamp,
                        'side': 'long',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'size': current_position,
                        'pnl': pnl,
                        'profit_pct': profit_pct * 100
                    })
                    
                    print(f"💰 做多止盈: 入场 {entry_price:.2f}, 出场 {current_price:.2f}, 盈利 {pnl:.2f} USDT ({profit_pct*100:.2f}%)")
                    
                    current_position = 0
                    entry_price = 0
                    entry_time = None
            
            elif current_position < 0:  # 做空
                profit_pct = (entry_price - current_price) / entry_price
                if profit_pct >= strategy.take_profit:
                    # 平仓
                    exit_value = abs(current_position) * current_price
                    fee = exit_value * 0.0005  # 0.05%手续费
                    pnl = (entry_price - current_price) * abs(current_position) - fee
                    current_cash += pnl
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': timestamp,
                        'side': 'short',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'size': abs(current_position),
                        'pnl': pnl,
                        'profit_pct': profit_pct * 100
                    })
                    
                    print(f"💰 做空止盈: 入场 {entry_price:.2f}, 出场 {current_price:.2f}, 盈利 {pnl:.2f} USDT ({profit_pct*100:.2f}%)")
                    
                    current_position = 0
                    entry_price = 0
                    entry_time = None
        
        # 检查开仓信号
        if current_position == 0 and signal != 0:
            if signal == 1:  # 做多信号
                # 计算可用保证金
                available_margin = current_cash * leverage
                position_size = available_margin / current_price
                
                # 开仓
                current_position = position_size
                entry_price = current_price
                entry_time = timestamp
                
                print(f"📈 做多开仓: 价格 {current_price:.2f}, 数量 {position_size:.4f}")
                
            elif signal == -1:  # 做空信号
                # 计算可用保证金
                available_margin = current_cash * leverage
                position_size = available_margin / current_price
                
                # 开仓
                current_position = -position_size
                entry_price = current_price
                entry_time = timestamp
                
                print(f"📉 做空开仓: 价格 {current_price:.2f}, 数量 {position_size:.4f}")
        
        # 记录权益
        if current_position != 0:
            # 计算当前持仓价值
            if current_position > 0:  # 做多
                position_value = current_position * current_price
                unrealized_pnl = position_value - (current_position * entry_price)
            else:  # 做空
                position_value = abs(current_position) * current_price
                unrealized_pnl = (entry_price - current_price) * abs(current_position)
            
            current_equity = current_cash + unrealized_pnl
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
        
        # 显示详细交易记录
        print(f"\n📝 详细交易记录:")
        for i, trade in enumerate(trades, 1):
            print(f"  交易 {i}: {trade['side'].upper()} | "
                  f"入场: {trade['entry_price']:.2f} | "
                  f"出场: {trade['exit_price']:.2f} | "
                  f"盈利: {trade['pnl']:.2f} USDT ({trade['profit_pct']:.2f}%)")
    
    # 策略信息
    print(f"\n🎯 策略配置:")
    print(f"  策略类型: ContractDailyTradingStrategy")
    print(f"  杠杆倍数: 50x")
    print(f"  止盈设置: 50%")
    print(f"  止损设置: 无止损")
    print(f"  保证金模式: 逐仓")
    print(f"  K线间隔: 15分钟")

def main():
    """
    主函数
    """
    print("🚀 合约策略回测系统")
    print("="*50)
    
    # 策略参数
    strategy_params = {
        'take_profit': 0.50,           # 50%止盈
        'rsi_period': 14,              # RSI周期
        'rsi_oversold': 30.0,          # RSI超卖阈值
        'rsi_overbought': 70.0,        # RSI超买阈值
        'ma_short': 5,                 # 短期MA
        'ma_long': 20,                 # 长期MA
        'min_volume_ratio': 1.5,       # 最小成交量比例
        'price_pullback': 0.01,        # 价格回调比例
        'start_hour': 0,               # 开始交易时间
        'end_hour': 24,                # 结束交易时间
        'kline_interval': '15m'        # K线间隔
    }
    
    # 回测参数
    backtest_params = {
        'days': 30,                    # 回测天数
        'initial_cash': 100000,        # 初始资金
        'leverage': 50                 # 杠杆倍数
    }
    
    try:
        # 1. 创建策略
        print("🔧 创建合约交易策略...")
        strategy = ContractDailyTradingStrategy(**strategy_params)
        print("✅ 策略创建成功")
        
        # 2. 获取测试数据
        data = create_mock_data(
            days=backtest_params['days'],
            interval=strategy_params['kline_interval']
        )
        
        # 3. 运行回测
        results = simple_backtest(
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
