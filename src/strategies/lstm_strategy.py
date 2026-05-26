import numpy as np
import pandas as pd
from typing import List, Tuple, Dict
from datetime import datetime
import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import MinMaxScaler
import joblib
from pathlib import Path

class LSTMStrategy:
    def __init__(self,
                 sequence_length: int = 60,
                 prediction_length: int = 5,
                 model_path: str = "models",
                 threshold: float = 0.01):  # 降低阈值
        """
        基于LSTM的多特征价格预测策略
        
        Args:
            sequence_length: 用于预测的历史数据长度
            prediction_length: 预测未来的时间步长
            model_path: 模型保存路径
            threshold: 交易信号阈值（预测涨跌幅超过此值则产生信号）
        """
        self.sequence_length = sequence_length
        self.prediction_length = prediction_length
        self.threshold = threshold
        self.model_path = Path(model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化模型和缩放器字典
        self.model = None
        self.scalers = {}
        self.is_trained = False
        
        # 特征列表及其权重
        self.features_config = {
            'close': 1.0,
            'high': 0.8,
            'low': 0.8,
            'volume': 0.6,
            'ma5': 0.7,
            'ma10': 0.7,
            'rsi': 0.6,
            'macd': 0.8,
            'atr': 0.6
        }
        self.features = list(self.features_config.keys())
        self.n_features = len(self.features)
        
        # 加载已有模型（如果存在）
        self._load_model()

    def _build_feature_frame(self, data: pd.DataFrame) -> pd.DataFrame:
        """补齐模型需要的技术指标特征。"""
        data = data.copy()

        if 'timestamp' in data.columns:
            data = data.sort_values('timestamp')
        else:
            data = data.sort_index()

        data['ma5'] = data['close'].rolling(window=5).mean()
        data['ma10'] = data['close'].rolling(window=10).mean()
        data['rsi'] = self.calculate_rsi(data['close'])
        data['macd'] = self.calculate_macd(data['close'])
        data['atr'] = self.calculate_atr(data['high'], data['low'], data['close'])

        return data.replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(0)
        
    def _build_model(self) -> keras.Model:
        """构建增强的LSTM模型，使用注意力机制和残差连接"""
        input_layer = keras.layers.Input(shape=(self.sequence_length, self.n_features))
        
        # 第一个LSTM层带注意力机制
        lstm1 = keras.layers.LSTM(64, return_sequences=True)(input_layer)
        attention1 = keras.layers.Attention()([lstm1, lstm1])
        lstm1_output = keras.layers.Add()([lstm1, attention1])
        
        # 第二个LSTM层
        lstm2 = keras.layers.LSTM(32, return_sequences=False)(lstm1_output)
        
        # 全连接层
        dense1 = keras.layers.Dense(32, activation='relu')(lstm2)
        dropout1 = keras.layers.Dropout(0.2)(dense1)
        
        # 输出层
        output = keras.layers.Dense(self.prediction_length)(dropout1)
        
        model = keras.Model(inputs=input_layer, outputs=output)
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss=keras.losses.Huber(),
            metrics=['mae', 'mse']
        )
        
        return model
        
    def _prepare_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """准备训练数据，对每个特征单独进行标准化"""
        data = self._build_feature_frame(data)
        
        # 检查特征
        missing_features = [col for col in self.features if col not in data.columns]
        if missing_features:
            raise ValueError(f"缺少必要的特征: {missing_features}")
        
        # 对每个特征单独进行标准化
        scaled_features = []
        for feature in self.features:
            feature_data = data[feature].values.reshape(-1, 1)
            
            # 如果是训练模式或缩放器不存在，创建新的缩放器
            if not self.is_trained or feature not in self.scalers:
                self.scalers[feature] = MinMaxScaler()
                scaled_feature = self.scalers[feature].fit_transform(feature_data)
            else:
                scaled_feature = self.scalers[feature].transform(feature_data)
                
            scaled_features.append(scaled_feature)
        
        # 将所有标准化后的特征组合
        scaled_data = np.hstack(scaled_features)
        
        # 创建序列数据
        X, y = [], []
        for i in range(len(scaled_data) - self.sequence_length - self.prediction_length + 1):
            # 输入序列
            sequence = scaled_data[i:(i + self.sequence_length)]
            # 目标序列（只预测收盘价）
            target = scaled_data[(i + self.sequence_length):(i + self.sequence_length + self.prediction_length), 0]
            
            if len(sequence) == self.sequence_length and len(target) == self.prediction_length:
                X.append(sequence)
                y.append(target)
        
        X = np.array(X)
        y = np.array(y)
        
        # 打印数据形状以便调试
        print(f"输入数据形状: {X.shape}")
        print(f"目标数据形状: {y.shape}")
        
        return X, y
        
    def train(self, data: pd.DataFrame, epochs: int = 50, batch_size: int = 32, verbose: int = 1):
        """训练模型，增加了早停和学习率调整"""
        X, y = self._prepare_data(data)
        
        if not self.model:
            self.model = self._build_model()
        
        # 定义回调函数
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=5,
                restore_best_weights=True
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=3,
                min_lr=0.0001
            )
        ]
        
        # 训练模型
        history = self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2,
            callbacks=callbacks,
            shuffle=True,
            verbose=verbose
        )
        
        # 保存模型和缩放器
        self._save_model()
        self.is_trained = True
        
        return history
        
    def _save_model(self):
        """保存模型和所有特征的缩放器"""
        if self.model:
            # 使用.h5格式保存模型
            model_file = self.model_path / "lstm_model.h5"
            self.model.save(model_file)
            # 保存缩放器
            scalers_file = self.model_path / "scalers.pkl"
            joblib.dump(self.scalers, scalers_file)
            
    def _load_model(self):
        """加载模型和所有特征的缩放器"""
        model_file = self.model_path / "lstm_model.h5"
        scalers_file = self.model_path / "scalers.pkl"
        
        if model_file.exists() and scalers_file.exists():
            try:
                self.model = keras.models.load_model(model_file)
                self.scalers = joblib.load(scalers_file)
                self.is_trained = True
            except Exception as e:
                print(f"加载模型时出错: {e}")
                self.model = None
                self.is_trained = False
        
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """使用多特征进行预测"""
        if not self.is_trained:
            raise ValueError("模型未训练")

        X = self._prepare_features(data)
        
        # 预测
        scaled_pred = self.model.predict(X, verbose=0)
        
        # 将预测结果转换回价格（只转换收盘价）
        predictions = self.scalers['close'].inverse_transform(scaled_pred.reshape(-1, 1))
        
        return predictions.flatten()

    def _classify_signal(self, pred_close: float, current_data: pd.Series) -> int:
        """根据预测价格和当前指标生成交易信号。"""
        current_price = current_data['close']
        current_ma5 = current_data['ma5']
        current_ma10 = current_data['ma10']
        current_rsi = current_data['rsi']
        current_macd = current_data['macd']

        price_change = (pred_close - current_price) / current_price

        if (price_change > self.threshold * 0.5 and
            (current_ma5 > current_ma10 or current_rsi < 60) and
            current_macd > -0.001):
            return 1

        if (price_change < -self.threshold * 0.5 and
            (current_ma5 < current_ma10 or current_rsi > 40) and
            current_macd < 0.001):
            return -1

        return 0
        
    def calculate_rsi(self, data: pd.Series, periods: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
        
    def calculate_macd(self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
        """计算MACD指标"""
        exp1 = data.ewm(span=fast, adjust=False).mean()
        exp2 = data.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd - signal_line
        
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, periods: int = 14) -> pd.Series:
        """计算ATR指标"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=periods).mean()
        
    def generate_signals(self, data: pd.DataFrame) -> List[int]:
        """
        生成交易信号
        
        Args:
            data: 市场数据
            
        Returns:
            signals: 交易信号列表 (-1: 卖出, 0: 持仓, 1: 买入)
        """
        if not self.is_trained:
            return [0] * len(data)
            
        signals = []
        sequence_length = self.sequence_length
        
        data = self._build_feature_frame(data)
        
        # 记录预测结果
        predictions = []
        actual_prices = []
        
        for i in range(len(data)):
            if i < sequence_length:
                signals.append(0)
                continue
                
            try:
                # 准备输入数据
                sequence = data.iloc[i-sequence_length:i]
                
                # 预测
                pred_prices = self.predict(sequence)
                pred_close = pred_prices[0]  # 预测的收盘价
                
                # 当前价格和指标
                current_price = data.iloc[i]['close']
                current_ma5 = data.iloc[i]['ma5']
                current_ma10 = data.iloc[i]['ma10']
                current_rsi = data.iloc[i]['rsi']
                current_macd = data.iloc[i]['macd']
                
                # 记录预测和实际价格
                predictions.append(pred_close)
                actual_prices.append(current_price)
                
                price_change = (pred_close - current_price) / current_price
                signal = self._classify_signal(pred_close, data.iloc[i])
                    
                signals.append(signal)
                
                # 打印调试信息
                if i % 10 == 0:  # 每10个数据点打印一次
                    print(f"时间点 {i}:")
                    print(f"预测价格: {pred_close:.2f}")
                    print(f"当前价格: {current_price:.2f}")
                    print(f"价格变化: {price_change:.2%}")
                    print(f"MA5: {current_ma5:.2f}")
                    print(f"MA10: {current_ma10:.2f}")
                    print(f"RSI: {current_rsi:.2f}")
                    print(f"MACD: {current_macd:.2f}")
                    print(f"信号: {signal}")
                    print("-" * 50)
                    
            except Exception as e:
                print(f"生成信号时出错: {str(e)}")
                signals.append(0)
        
        # 计算预测准确度
        predictions = np.array(predictions)
        actual_prices = np.array(actual_prices)
        valid_indices = ~np.isnan(predictions)
        if np.any(valid_indices):
            mse = np.mean((predictions[valid_indices] - actual_prices[valid_indices]) ** 2)
            mae = np.mean(np.abs(predictions[valid_indices] - actual_prices[valid_indices]))
            print(f"\n预测评估:")
            print(f"MSE: {mse:.2f}")
            print(f"MAE: {mae:.2f}")
            print(f"预测数量: {len(predictions)}")
            print(f"有效预测数量: {np.sum(valid_indices)}")
            print(f"生成信号数量: {sum(1 for s in signals if s != 0)}")
        
        return signals

    def generate_signal(self, data: pd.DataFrame) -> int:
        """生成最新一个时间点的交易信号。"""
        if not self.is_trained:
            return 0

        data = self._build_feature_frame(data)
        if len(data) < self.sequence_length:
            return 0

        if len(data) > self.sequence_length:
            sequence = data.iloc[-self.sequence_length - 1:-1]
            current_data = data.iloc[-1]
        else:
            sequence = data.tail(self.sequence_length)
            current_data = sequence.iloc[-1]

        pred_close = self.predict(sequence)[0]
        return self._classify_signal(pred_close, current_data)
        
    def update_model(self, new_data: pd.DataFrame, retrain: bool = False, verbose: int = 0):
        """更新模型，支持增量学习和完全重训练"""
        if retrain:
            self.train(new_data, verbose=verbose)
        else:
            # 增量学习
            X, y = self._prepare_data(new_data)
            if len(X) > 0:
                self.model.fit(
                    X, y,
                    epochs=1,
                    batch_size=1,
                    verbose=0
                ) 
        
    def _prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """准备单个预测的特征数据"""
        data = self._build_feature_frame(data)

        if len(data) < self.sequence_length:
            raise ValueError(f"预测数据不足，至少需要 {self.sequence_length} 条数据")

        data = data.tail(self.sequence_length)
        
        # 标准化特征
        scaled_features = []
        for feature in self.features:
            feature_data = data[feature].values.reshape(-1, 1)
            if feature in self.scalers:
                scaled_feature = self.scalers[feature].transform(feature_data)
            else:
                raise ValueError(f"特征 {feature} 的缩放器未找到")
            scaled_features.append(scaled_feature)
        
        # 组合所有特征
        scaled_data = np.hstack(scaled_features)
        
        # 添加批次维度
        return scaled_data.reshape(1, self.sequence_length, self.n_features)
