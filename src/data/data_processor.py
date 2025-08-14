import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        """
        初始化数据处理器
        """
        self.logger = logging.getLogger(__name__)

    def process_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理K线数据，添加技术指标
        
        Args:
            df: 原始K线数据DataFrame，包含timestamp, open, high, low, close, volume列
            
        Returns:
            处理后的DataFrame，包含原始数据和技术指标
        """
        try:
            # 统一时间索引：确保按时间排序并将 timestamp 设为 DatetimeIndex
            df = df.sort_values('timestamp')
            if 'timestamp' in df.columns:
                # 常见交易所返回 ms 时间戳，这里优先按 ms 转换；若已是可解析字符串也能兼容
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
                except Exception:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                # 丢弃无法解析的时间
                df = df.dropna(subset=['timestamp'])
                df = df.set_index('timestamp')
            
            # 计算基本技术指标
            df = self._add_basic_indicators(df)
            
            # 计算趋势指标
            df = self._add_trend_indicators(df)
            
            # 计算波动率指标
            df = self._add_volatility_indicators(df)
            
            # 计算成交量指标
            df = self._add_volume_indicators(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"处理K线数据失败: {str(e)}")
            raise

    def _add_basic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加基本技术指标
        
        Args:
            df: 原始K线数据
            
        Returns:
            添加了基本技术指标的DataFrame
        """
        # 计算收益率
        df['returns'] = df['close'].pct_change()
        
        # 计算对数收益率
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # 计算价格变化
        df['price_change'] = df['close'] - df['open']
        
        # 计算价格变化百分比
        df['price_change_pct'] = df['price_change'] / df['open']
        
        return df

    def _add_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加趋势指标
        
        Args:
            df: 原始K线数据
            
        Returns:
            添加了趋势指标的DataFrame
        """
        # 计算移动平均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        
        # 计算指数移动平均线
        df['ema5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema10'] = df['close'].ewm(span=10, adjust=False).mean()
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        
        # 计算MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        return df

    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加波动率指标
        
        Args:
            df: 原始K线数据
            
        Returns:
            添加了波动率指标的DataFrame
        """
        # 计算真实波幅
        df['tr'] = pd.DataFrame({
            'hl': df['high'] - df['low'],
            'hc': abs(df['high'] - df['close'].shift(1)),
            'lc': abs(df['low'] - df['close'].shift(1))
        }).max(axis=1)
        
        # 计算ATR
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # 计算布林带
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        
        return df

    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加成交量指标
        
        Args:
            df: 原始K线数据
            
        Returns:
            添加了成交量指标的DataFrame
        """
        # 计算成交量移动平均
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        df['volume_ma10'] = df['volume'].rolling(window=10).mean()
        
        # 计算成交量变化
        df['volume_change'] = df['volume'].pct_change()
        
        # 计算成交量比率
        df['volume_ratio'] = df['volume'] / df['volume_ma5']
        
        return df

    def normalize_data(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        标准化数据
        
        Args:
            df: 原始数据
            columns: 需要标准化的列名列表
            
        Returns:
            标准化后的DataFrame
        """
        try:
            df_normalized = df.copy()
            for column in columns:
                if column in df.columns:
                    mean = df[column].mean()
                    std = df[column].std()
                    df_normalized[column] = (df[column] - mean) / std
            return df_normalized
        except Exception as e:
            self.logger.error(f"标准化数据失败: {str(e)}")
            raise

    def remove_outliers(self, df: pd.DataFrame, columns: List[str], 
                       method: str = 'zscore', threshold: float = 3.0) -> pd.DataFrame:
        """
        移除异常值
        
        Args:
            df: 原始数据
            columns: 需要处理的列名列表
            method: 异常值检测方法 ('zscore' 或 'iqr')
            threshold: 阈值
            
        Returns:
            移除异常值后的DataFrame
        """
        try:
            df_clean = df.copy()
            for column in columns:
                if column in df.columns:
                    if method == 'zscore':
                        z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
                        df_clean = df_clean[z_scores < threshold]
                    elif method == 'iqr':
                        Q1 = df[column].quantile(0.25)
                        Q3 = df[column].quantile(0.75)
                        IQR = Q3 - Q1
                        df_clean = df_clean[
                            (df[column] >= Q1 - threshold * IQR) & 
                            (df[column] <= Q3 + threshold * IQR)
                        ]
            return df_clean
        except Exception as e:
            self.logger.error(f"移除异常值失败: {str(e)}")
            raise 