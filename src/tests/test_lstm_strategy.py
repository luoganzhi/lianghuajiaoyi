import unittest
import pandas as pd
import numpy as np
import tempfile
import tensorflow as tf
from src.strategies.lstm_strategy import LSTMStrategy

class TestLSTMStrategy(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        tf.keras.backend.clear_session()
        self.model_dir = tempfile.TemporaryDirectory()

        # 创建模拟的历史数据
        dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='1H')
        np.random.seed(42)
        
        # 生成模拟价格数据
        prices = np.random.randn(len(dates)).cumsum() + 100
        self.test_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.randn(len(dates)) * 0.1,
            'high': prices + np.random.randn(len(dates)) * 0.2,
            'low': prices - np.random.randn(len(dates)) * 0.2,
            'close': prices,
            'volume': np.random.randint(1000, 10000, len(dates))
        })
        
        # 初始化策略
        self.strategy = LSTMStrategy(
            sequence_length=24,  # 使用24小时数据
            prediction_length=6,  # 预测未来6小时
            model_path=self.model_dir.name,
            threshold=0.02
        )

    def tearDown(self):
        tf.keras.backend.clear_session()
        self.model_dir.cleanup()

    def test_model_training(self):
        """测试模型训练"""
        # 训练模型
        self.strategy.train(
            self.test_data,
            epochs=2,  # 测试时使用较少的epochs
            batch_size=32,
            verbose=0
        )
        
        self.assertTrue(self.strategy.is_trained)
        self.assertIsNotNone(self.strategy.model)

    def test_prediction(self):
        """测试预测功能"""
        # 确保模型已训练
        if not self.strategy.is_trained:
            self.strategy.train(self.test_data, epochs=2, verbose=0)
            
        # 获取预测结果
        predictions = self.strategy.predict(self.test_data)
        
        # 验证预测结果
        self.assertEqual(len(predictions), self.strategy.prediction_length)
        self.assertTrue(np.all(np.isfinite(predictions)))

    def test_signal_generation(self):
        """测试信号生成"""
        # 确保模型已训练
        if not self.strategy.is_trained:
            self.strategy.train(self.test_data, epochs=2, verbose=0)
            
        # 测试信号生成
        signal_data = self.test_data.tail(self.strategy.sequence_length + 1)
        signal = self.strategy.generate_signal(signal_data)
        
        # 验证信号值是否有效
        self.assertIn(signal, [-1, 0, 1])

    def test_model_update(self):
        """测试模型更新"""
        # 首先训练模型
        self.strategy.train(self.test_data[:1000], epochs=2, verbose=0)
        
        # 测试增量更新
        self.strategy.update_model(self.test_data[1000:1100], retrain=False)
        
        # 测试完全重训练
        self.strategy.update_model(self.test_data[1100:1200], retrain=True)

    def test_strategy_performance(self):
        """测试策略性能"""
        # 训练模型
        train_data = self.test_data[:5000]  # 使用前5000条数据训练
        test_data = self.test_data[5000:]   # 使用剩余数据测试
        
        self.strategy.train(train_data, epochs=2, verbose=0)
        
        # 模拟交易
        position = 0
        trades = []
        initial_balance = 10000
        current_balance = initial_balance
        
        max_windows = min(240, len(test_data) - self.strategy.sequence_length)
        for i in range(0, max_windows, self.strategy.prediction_length):
            window_data = test_data.iloc[i:i+self.strategy.sequence_length]
            signal = self.strategy.generate_signal(window_data)
            
            current_price = window_data['close'].iloc[-1]
            
            # 模拟交易执行
            if signal == 1 and position == 0:  # 买入信号
                position = 1
                trades.append({
                    'type': 'buy',
                    'price': current_price,
                    'timestamp': window_data.index[-1]
                })
            elif signal == -1 and position == 1:  # 卖出信号
                position = 0
                trades.append({
                    'type': 'sell',
                    'price': current_price,
                    'timestamp': window_data.index[-1]
                })
        
        # 计算收益率
        if trades:
            returns = []
            for i in range(0, len(trades)-1, 2):
                if i+1 < len(trades):
                    returns.append(
                        (trades[i+1]['price'] - trades[i]['price']) / trades[i]['price']
                    )
            
            total_return = np.prod([1 + r for r in returns]) - 1
            self.assertIsInstance(total_return, float)

if __name__ == '__main__':
    unittest.main()
