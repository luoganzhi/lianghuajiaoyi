#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试每日交易策略集成
"""

import sys
import os
import pandas as pd
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_strategy_import():
    """测试策略导入"""
    try:
        from src.strategies.daily_trading_strategy import DailyTradingStrategy
        print("✅ DailyTradingStrategy导入成功")
        return True
    except Exception as e:
        print(f"❌ DailyTradingStrategy导入失败: {e}")
        return False

def test_strategy_initialization():
    """测试策略初始化"""
    try:
        from src.strategies.daily_trading_strategy import DailyTradingStrategy
        
        strategy = DailyTradingStrategy(
            take_profit=0.01,
            stop_loss=0.005,
            rsi_period=21,
            ma_short=5,
            ma_long=20,
            use_dynamic_stop=False,
            use_macd=False
        )
        
        print("✅ 策略初始化成功")
        print(f"   止盈: {strategy.take_profit * 100:.1f}%")
        print(f"   止损: {strategy.stop_loss * 100:.1f}%")
        print(f"   RSI周期: {strategy.rsi_period}")
        print(f"   MA设置: {strategy.ma_short}/{strategy.ma_long}")
        return True
    except Exception as e:
        print(f"❌ 策略初始化失败: {e}")
        return False

def test_strategy_signal_generation():
    """测试信号生成"""
    try:
        from src.strategies.daily_trading_strategy import DailyTradingStrategy
        
        strategy = DailyTradingStrategy()
        
        # 创建模拟数据
        dates = pd.date_range(start='2025-01-01', periods=100, freq='1H')
        data = pd.DataFrame({
            'open': [100 + i * 0.1 for i in range(100)],
            'high': [101 + i * 0.1 for i in range(100)],
            'low': [99 + i * 0.1 for i in range(100)],
            'close': [100.5 + i * 0.1 for i in range(100)],
            'volume': [1000 + i * 10 for i in range(100)]
        }, index=dates)
        
        signal = strategy.generate_signal(data)
        print(f"✅ 信号生成成功: {signal}")
        return True
    except Exception as e:
        print(f"❌ 信号生成失败: {e}")
        return False

def test_main_integration():
    """测试main.py集成"""
    try:
        from src.main import main
        print("✅ main.py集成成功")
        return True
    except Exception as e:
        print(f"❌ main.py集成失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("🧪 开始测试每日交易策略集成...")
    print("=" * 50)
    
    tests = [
        ("策略导入", test_strategy_import),
        ("策略初始化", test_strategy_initialization),
        ("信号生成", test_strategy_signal_generation),
        ("main.py集成", test_main_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 测试: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name}测试失败")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！策略集成成功！")
        print("\n🚀 现在可以运行策略了:")
        print("   python run_daily_strategy.py")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")

if __name__ == "__main__":
    main()
