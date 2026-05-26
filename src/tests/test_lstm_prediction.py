import unittest
import numpy as np
import pandas as pd
import tempfile
import tensorflow as tf
from src.strategies.lstm_strategy import LSTMStrategy

class TestLSTMPrediction(unittest.TestCase):
    
    def setUp(self):
        """测试前的准备工作"""
        tf.keras.backend.clear_session()
        np.random.seed(42)
        tf.random.set_seed(42)
        self.model_dir = tempfile.TemporaryDirectory()

        # 生成模拟的正弦波数据，这样我们可以预测明确的模式
        self.sequence_length = 24
        self.prediction_length = 6
        
        # 生成时间序列数据（正弦波+趋势+噪声）
        t = np.linspace(0, 8*np.pi, 1000)
        trend = 0.1 * t
        seasonal = 10 * np.sin(t)
        noise = np.random.normal(0, 1, 1000)
        prices = trend + seasonal + noise + 100
        
        dates = pd.date_range(start='2023-01-01', end='2023-01-01 23:59:00', periods=1000)
        
        self.data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 0.1, 1000),
            'high': prices + np.random.normal(0.5, 0.1, 1000),
            'low': prices + np.random.normal(-0.5, 0.1, 1000),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 1000)
        })
        
        # 初始化策略
        self.strategy = LSTMStrategy(
            sequence_length=self.sequence_length,
            prediction_length=self.prediction_length,
            model_path=self.model_dir.name,
            threshold=0.02
        )

    def tearDown(self):
        tf.keras.backend.clear_session()
        self.model_dir.cleanup()
    
    def test_data_preparation(self):
        """测试数据预处理功能"""
        X, y = self.strategy._prepare_data(self.data)
        
        # 验证输入数据形状
        self.assertEqual(X.shape[1], self.sequence_length)
        self.assertEqual(y.shape[1], self.prediction_length)
        
        # 验证数据标准化
        self.assertTrue(np.all(np.isfinite(X)))
        self.assertTrue(np.all(np.isfinite(y)))
        self.assertTrue(np.nanmin(X) >= -1e-8 and np.nanmax(X) <= 1 + 1e-8)
        self.assertTrue(np.nanmin(y) >= -1e-8 and np.nanmax(y) <= 1 + 1e-8)
    
    def test_model_training(self):
        """测试模型训练过程"""
        # 训练模型
        history = self.strategy.train(self.data, epochs=5, batch_size=32, verbose=0)
        
        # 验证模型是否已训练
        self.assertTrue(self.strategy.is_trained)
        self.assertIsNotNone(self.strategy.model)
        
        # 验证模型结构
        expected_input_shape = (None, self.sequence_length, self.strategy.n_features)
        actual_input_shape = self.strategy.model.input_shape
        self.assertEqual(expected_input_shape, actual_input_shape)
        
        expected_output_shape = (None, self.prediction_length)
        actual_output_shape = self.strategy.model.output_shape
        self.assertEqual(expected_output_shape, actual_output_shape)
    
    def test_prediction_accuracy(self):
        """测试预测准确性"""
        # 首先训练模型
        self.strategy.train(self.data[:800], epochs=10, batch_size=32, verbose=0)
        
        # 使用后200个数据点进行测试
        test_data = self.data[800:]
        
        # 进行预测
        predictions_list = []
        actual_values_list = []
        
        for i in range(0, len(test_data) - self.sequence_length - self.prediction_length, self.prediction_length):
            # 获取预测窗口
            window_data = test_data.iloc[i:i+self.sequence_length]
            actual_values = test_data.iloc[i+self.sequence_length:i+self.sequence_length+self.prediction_length]['close'].values
            
            # 预测
            predictions = self.strategy.predict(window_data)
            
            predictions_list.append(predictions)
            actual_values_list.append(actual_values)
        
        # 计算预测误差
        mse = np.mean([np.mean((pred - actual) ** 2) 
                      for pred, actual in zip(predictions_list, actual_values_list)])
        rmse = np.sqrt(mse)
        
        # 计算预测值与实际值的相关系数
        pred_flat = np.concatenate(predictions_list)
        actual_flat = np.concatenate(actual_values_list)
        correlation = np.corrcoef(pred_flat, actual_flat)[0, 1]
        
        print(f"\n预测性能指标:")
        print(f"RMSE: {rmse:.2f}")
        print(f"相关系数: {correlation:.2f}")
        
        # 验证预测结果的合理性
        self.assertLess(rmse, 20.0, "RMSE应该在合理范围内")
        self.assertGreater(correlation, 0.3, "预测值与实际值应该有正相关性")
    
    def test_signal_generation(self):
        """测试交易信号生成"""
        # 训练模型
        self.strategy.train(self.data[:800], epochs=5, batch_size=32, verbose=0)
        
        # 生成交易信号
        signals = []
        for i in range(800, len(self.data) - self.sequence_length, self.prediction_length):
            window_data = self.data.iloc[i:i+self.sequence_length]
            signal = self.strategy.generate_signal(window_data)
            signals.append(signal)
        
        # 验证信号值的合理性
        unique_signals = set(signals)
        self.assertTrue(unique_signals.issubset({-1, 0, 1}), "信号值应该是 -1, 0, 1 之一")
        
        # 验证信号的分布
        signal_counts = pd.Series(signals).value_counts()
        print("\n信号分布:")
        print(signal_counts)
        
        # 确保不是总是产生相同的信号
        self.assertGreater(len(signal_counts), 1, "应该产生不同的交易信号")
    
    def test_model_persistence(self):
        """测试模型的保存和加载"""
        # 训练并保存模型
        self.strategy.train(self.data, epochs=5, batch_size=32, verbose=0)
        
        # 记录预测结果
        original_predictions = self.strategy.predict(self.data[-self.sequence_length:])
        
        # 创建新的策略实例（会加载保存的模型）
        new_strategy = LSTMStrategy(
            sequence_length=self.sequence_length,
            prediction_length=self.prediction_length,
            model_path=self.model_dir.name,
            threshold=0.02
        )
        
        # 使用加载的模型预测
        loaded_predictions = new_strategy.predict(self.data[-self.sequence_length:])
        
        # 验证两次预测结果是否一致
        np.testing.assert_array_almost_equal(
            original_predictions, 
            loaded_predictions, 
            decimal=5, 
            err_msg="加载的模型预测结果应与原模型一致"
        )

if __name__ == '__main__':
    unittest.main()
