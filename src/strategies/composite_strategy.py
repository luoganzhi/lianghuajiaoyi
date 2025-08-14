import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class CompositeStrategy(BaseStrategy):
    def __init__(
        self,
        # MA参数
        ma_short: int = 10,
        ma_long: int = 30,
        ma_trend: int = 50,
        
        # RSI参数
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        
        # 布林带参数
        boll_period: int = 20,
        boll_std: float = 2.0,
        
        # 量价参数
        volume_ma_period: int = 20,
        volume_threshold: float = 1.5,
        
        # 综合权重
        ma_weight: float = 0.3,
        rsi_weight: float = 0.25,
        boll_weight: float = 0.25,
        volume_weight: float = 0.2,
        
        # 信号确认
        confirm_window: int = 2,
        min_score: float = 0.6,
    ):
        super().__init__(
            {
                "ma_short": ma_short,
                "ma_long": ma_long,
                "ma_trend": ma_trend,
                "rsi_period": rsi_period,
                "rsi_oversold": rsi_oversold,
                "rsi_overbought": rsi_overbought,
                "boll_period": boll_period,
                "boll_std": boll_std,
                "volume_ma_period": volume_ma_period,
                "volume_threshold": volume_threshold,
                "ma_weight": ma_weight,
                "rsi_weight": rsi_weight,
                "boll_weight": boll_weight,
                "volume_weight": volume_weight,
                "confirm_window": confirm_window,
                "min_score": min_score,
            }
        )
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.ma_trend = ma_trend
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.boll_period = boll_period
        self.boll_std = boll_std
        self.volume_ma_period = volume_ma_period
        self.volume_threshold = volume_threshold
        self.ma_weight = ma_weight
        self.rsi_weight = rsi_weight
        self.boll_weight = boll_weight
        self.volume_weight = volume_weight
        self.confirm_window = confirm_window
        self.min_score = min_score

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std: float = 2.0) -> tuple:
        """计算布林带"""
        ma = prices.rolling(window=period).mean()
        std_dev = prices.rolling(window=period).std()
        upper_band = ma + (std_dev * std)
        lower_band = ma - (std_dev * std)
        return upper_band, ma, lower_band

    def _calculate_volume_indicators(self, volume: pd.Series, close: pd.Series, period: int = 20) -> tuple:
        """计算量价指标"""
        # 成交量移动平均
        volume_ma = volume.rolling(window=period).mean()
        
        # 量价关系
        volume_ratio = volume / volume_ma
        
        # 价格变化率
        price_change = close.pct_change()
        
        # 量价背离检测
        volume_price_divergence = np.where(
            (price_change > 0) & (volume_ratio < 1.0), -1,  # 价升量缩
            np.where((price_change < 0) & (volume_ratio > 1.0), 1, 0)  # 价跌量增
        )
        
        return volume_ma, volume_ratio, volume_price_divergence

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据，计算所有技术指标"""
        data = df.copy()
        
        # 1. 移动平均线
        data['ma_short'] = data['close'].rolling(window=self.ma_short).mean()
        data['ma_long'] = data['close'].rolling(window=self.ma_long).mean()
        data['ma_trend'] = data['close'].rolling(window=self.ma_trend).mean()
        
        # MA信号
        data['ma_signal'] = np.where(
            (data['close'] > data['ma_short']) & 
            (data['ma_short'] > data['ma_long']) & 
            (data['ma_long'] > data['ma_trend']), 1,  # 多头排列
            np.where(
                (data['close'] < data['ma_short']) & 
                (data['ma_short'] < data['ma_long']) & 
                (data['ma_long'] < data['ma_trend']), -1,  # 空头排列
                0  # 中性
            )
        )
        
        # 2. RSI指标
        data['rsi'] = self._calculate_rsi(data['close'], self.rsi_period)
        data['rsi_signal'] = np.where(
            data['rsi'] < self.rsi_oversold, 1,  # 超卖
            np.where(data['rsi'] > self.rsi_overbought, -1, 0)  # 超买
        )
        
        # 3. 布林带
        upper, middle, lower = self._calculate_bollinger_bands(
            data['close'], self.boll_period, self.boll_std
        )
        data['boll_upper'] = upper
        data['boll_middle'] = middle
        data['boll_lower'] = lower
        
        # 布林带信号
        data['boll_signal'] = np.where(
            data['close'] < data['boll_lower'], 1,  # 价格触及下轨
            np.where(data['close'] > data['boll_upper'], -1, 0)  # 价格触及上轨
        )
        
        # 4. 量价指标
        volume_ma, volume_ratio, volume_divergence = self._calculate_volume_indicators(
            data['volume'], data['close'], self.volume_ma_period
        )
        data['volume_ma'] = volume_ma
        data['volume_ratio'] = volume_ratio
        data['volume_divergence'] = volume_divergence
        
        # 量价信号
        data['volume_signal'] = np.where(
            (data['volume_ratio'] > self.volume_threshold) & 
            (data['close'] > data['close'].shift(1)), 1,  # 放量上涨
            np.where(
                (data['volume_ratio'] > self.volume_threshold) & 
                (data['close'] < data['close'].shift(1)), -1,  # 放量下跌
                0
            )
        )
        
        return data

    def _calculate_composite_score(self, row: pd.Series) -> float:
        """计算综合评分"""
        scores = []
        
        # MA评分 (0-1)
        if row['ma_signal'] == 1:
            ma_score = 1.0
        elif row['ma_signal'] == -1:
            ma_score = 0.0
        else:
            ma_score = 0.5
        scores.append(ma_score * self.ma_weight)
        
        # RSI评分 (0-1)
        if row['rsi_signal'] == 1:
            rsi_score = 1.0
        elif row['rsi_signal'] == -1:
            rsi_score = 0.0
        else:
            # RSI在中间区域，根据位置给分
            rsi_score = 1.0 - abs(row['rsi'] - 50) / 50
        scores.append(rsi_score * self.rsi_weight)
        
        # 布林带评分 (0-1)
        if row['boll_signal'] == 1:
            boll_score = 1.0
        elif row['boll_signal'] == -1:
            boll_score = 0.0
        else:
            # 价格在布林带中间，根据位置给分
            band_width = row['boll_upper'] - row['boll_lower']
            if band_width > 0:
                position = (row['close'] - row['boll_lower']) / band_width
                boll_score = 1.0 - abs(position - 0.5) * 2  # 越接近中间分数越高
            else:
                boll_score = 0.5
        scores.append(boll_score * self.boll_weight)
        
        # 量价评分 (0-1)
        if row['volume_signal'] == 1:
            volume_score = 1.0
        elif row['volume_signal'] == -1:
            volume_score = 0.0
        else:
            # 根据成交量比率给分
            volume_score = min(row['volume_ratio'] / self.volume_threshold, 1.0)
        scores.append(volume_score * self.volume_weight)
        
        return sum(scores)

    def generate_signal(self, df: pd.DataFrame) -> int:
        """生成单个信号"""
        data = self._prepare(df)
        
        if len(data) < max(self.ma_trend, self.rsi_period, self.boll_period, self.volume_ma_period) + 5:
            return 0
        
        recent = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 计算综合评分
        current_score = self._calculate_composite_score(recent)
        prev_score = self._calculate_composite_score(prev)
        
        # 生成信号
        if current_score > self.min_score and current_score > prev_score:
            return 1  # 买入信号
        elif current_score < (1 - self.min_score) and current_score < prev_score:
            return -1  # 卖出信号
        
        return 0

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成完整的信号序列"""
        df = self._prepare(data)
        df['signal'] = 0
        df['composite_score'] = 0.0
        
        min_periods = max(self.ma_trend, self.rsi_period, self.boll_period, self.volume_ma_period) + 5
        
        if len(df) < min_periods:
            return df
        
        # 计算综合评分
        for i in range(min_periods, len(df)):
            df_subset = df.iloc[:i+1]
            score = self._calculate_composite_score(df_subset.iloc[-1])
            df.iloc[i, df.columns.get_loc('composite_score')] = score
        
        # 生成信号
        for i in range(min_periods, len(df)):
            current_score = df.iloc[i]['composite_score']
            prev_score = df.iloc[i-1]['composite_score']
            
            if current_score > self.min_score and current_score > prev_score:
                df.iloc[i, df.columns.get_loc('signal')] = 1
            elif current_score < (1 - self.min_score) and current_score < prev_score:
                df.iloc[i, df.columns.get_loc('signal')] = -1
        
        # 应用确认窗口
        if self.confirm_window > 1:
            df['signal'] = (
                df['signal'].rolling(self.confirm_window).apply(
                    lambda x: 1 if (x == 1).sum() >= self.confirm_window else 
                             (-1 if (x == -1).sum() >= self.confirm_window else 0), 
                    raw=False
                )
            ).fillna(0)
        
        return df

    def get_strategy_info(self) -> dict:
        """获取策略信息"""
        return {
            "name": "Composite Strategy",
            "description": "综合MA、RSI、布林带和量价关系的多指标策略",
            "parameters": {
                "ma_short": f"短期MA: {self.ma_short}",
                "ma_long": f"长期MA: {self.ma_long}",
                "ma_trend": f"趋势MA: {self.ma_trend}",
                "rsi_period": f"RSI周期: {self.rsi_period}",
                "rsi_oversold": f"RSI超卖: {self.rsi_oversold}",
                "rsi_overbought": f"RSI超买: {self.rsi_overbought}",
                "boll_period": f"布林带周期: {self.boll_period}",
                "boll_std": f"布林带标准差: {self.boll_std}",
                "volume_ma_period": f"成交量MA周期: {self.volume_ma_period}",
                "volume_threshold": f"成交量阈值: {self.volume_threshold}",
                "ma_weight": f"MA权重: {self.ma_weight}",
                "rsi_weight": f"RSI权重: {self.rsi_weight}",
                "boll_weight": f"布林带权重: {self.boll_weight}",
                "volume_weight": f"量价权重: {self.volume_weight}",
                "confirm_window": f"确认窗口: {self.confirm_window}",
                "min_score": f"最小评分: {self.min_score}"
            }
        }
