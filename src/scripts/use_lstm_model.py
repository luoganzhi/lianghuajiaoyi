import pandas as pd
import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.strategies.lstm_strategy import LSTMStrategy

def use_lstm_model():
    """使用已训练的LSTM模型进行预测"""
    # 配置参数 - 需要与训练时使用的参数一致
    model_params = {
        'sequence_length': 24,
        'prediction_length': 6,
        'model_path': 'models/lstm',
        'threshold': 0.02
    }
    
    # 初始化策略 - 会自动加载已保存的模型
    strategy = LSTMStrategy(**model_params)
    
    if not strategy.is_trained:
        print("错误：未找到已训练的模型！请先运行 train_lstm_model.py 训练模型。")
        return
        
    # 准备测试数据
    # 这里使用示例数据，您需要替换为实际的市场数据
    dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='1h')
    test_data = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 102,
        'low': np.random.randn(len(dates)).cumsum() + 98,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, len(dates))
    })
    
    # 使用模型进行预测
    try:
        predictions = strategy.predict(test_data)
        print("\n预测结果:")
        print(f"未来 {len(predictions)} 个时间段的价格预测:")
        for i, price in enumerate(predictions, 1):
            print(f"T+{i}: {price:.2f}")
            
        # 获取交易信号
        signal = strategy.generate_signal(test_data)
        signal_map = {1: "买入", -1: "卖出", 0: "持仓不变"}
        print(f"\n交易信号: {signal_map[signal]}")
        
    except Exception as e:
        print(f"预测过程中出错: {e}")

if __name__ == "__main__":
    use_lstm_model() 