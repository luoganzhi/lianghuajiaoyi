import pandas as pd
import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.strategies.lstm_strategy import LSTMStrategy
from src.data.data_loader import DataLoader  # 假设您有数据加载器

def train_lstm_model():
    """训练并保存LSTM模型"""
    # 配置参数
    model_params = {
        'sequence_length': 24,  # 使用24小时数据
        'prediction_length': 6,  # 预测未来6小时
        'model_path': 'models/lstm',  # 模型保存路径
        'threshold': 0.02  # 交易信号阈值
    }
    
    # 初始化策略
    strategy = LSTMStrategy(**model_params)
    
    # 加载训练数据
    # 这里使用示例数据，您需要替换为实际的数据加载逻辑
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='1h')
    data = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 102,
        'low': np.random.randn(len(dates)).cumsum() + 98,
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, len(dates))
    })
    
    # 训练模型
    print("开始训练模型...")
    strategy.train(
        data=data,
        epochs=50,
        batch_size=32
    )
    print(f"模型训练完成，已保存到 {model_params['model_path']}")

if __name__ == "__main__":
    train_lstm_model() 