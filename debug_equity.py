import pandas as pd
import numpy as np

def debug_equity_calculation():
    """调试权益计算"""
    
    # 模拟数据
    initial_cash = 100000
    fee = 0.001
    
    # 交易记录
    trades = [
        {'type': 'buy', 'price': 118353.10, 'size': 1, 'timestamp': '2025-07-23 04:00:00'},
        {'type': 'sell', 'price': 118528.10, 'size': 1, 'timestamp': '2025-07-23 08:00:00'},
        {'type': 'buy', 'price': 118959.90, 'size': 1, 'timestamp': '2025-07-27 16:00:00'},
        {'type': 'sell', 'price': 119439.30, 'size': 1, 'timestamp': '2025-07-27 20:00:00'},
        {'type': 'buy', 'price': 112931.80, 'size': 1, 'timestamp': '2025-08-05 12:00:00'},
        {'type': 'sell', 'price': 113628.00, 'size': 1, 'timestamp': '2025-08-05 16:00:00'},
    ]
    
    # 计算交易盈亏
    total_pnl = 0
    current_cash = initial_cash
    
    for i in range(0, len(trades), 2):
        if i + 1 < len(trades):
            buy_trade = trades[i]
            sell_trade = trades[i + 1]
            
            # 买入
            buy_value = buy_trade['price'] * buy_trade['size']
            buy_fee = buy_value * fee
            current_cash -= buy_value + buy_fee
            
            # 卖出
            sell_value = sell_trade['price'] * sell_trade['size']
            sell_fee = sell_value * fee
            current_cash += sell_value - sell_fee
            
            # 计算这笔交易的盈亏
            pnl = sell_value - buy_value - buy_fee - sell_fee
            total_pnl += pnl
            
            print(f"交易 {i//2 + 1}: 买入 {buy_trade['price']:.2f}, 卖出 {sell_trade['price']:.2f}")
            print(f"  盈亏: {pnl:.2f}, 当前现金: {current_cash:.2f}")
    
    print(f"\n总盈亏: {total_pnl:.2f}")
    print(f"最终现金: {current_cash:.2f}")
    print(f"收益率: {(current_cash - initial_cash) / initial_cash * 100:.2f}%")

if __name__ == "__main__":
    debug_equity_calculation()
