import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class TrendFollowingStrategy(BaseStrategy):
    def __init__(
        self,
        # 趋势判断参数
        trend_period: int = 50,
        trend_threshold: float = 0.02,  # 2%趋势阈值
        
        # 入场参数
        entry_period: int = 20,
        entry_threshold: float = 0.01,  # 1%入场阈值
        
        # 止损止盈
        stop_loss: float = 0.05,  # 5%止损
        take_profit: float = 0.15,  # 15%止盈
        
        # 仓位管理
        position_size: float = 0.8,  # 80%仓位
        
        # 确认窗口
        confirm_window: int = 3,
    ):
        super().__init__(
            {
                "trend_period": trend_period,
                "trend_threshold": trend_threshold,
                "entry_period": entry_period,
                "entry_threshold": entry_threshold,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "position_size": position_size,
                "confirm_window": confirm_window,
            }
        )
        self.trend_period = trend_period
        self.trend_threshold = trend_threshold
        self.entry_period = entry_period
        self.entry_threshold = entry_threshold
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.position_size = position_size
        self.confirm_window = confirm_window

    def _calculate_trend(self, prices: pd.Series) -> pd.Series:
        """计算趋势强度"""
        # 计算价格变化率
        price_change = prices.pct_change(self.trend_period)
        
        # 计算趋势强度（使用指数移动平均平滑）
        trend_strength = price_change.ewm(span=10).mean()
        
        return trend_strength

    def _calculate_volatility(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """计算波动率"""
        returns = prices.pct_change()
        volatility = returns.rolling(window=period).std()
        return volatility

    def _calculate_momentum(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """计算动量指标"""
        # 价格相对于移动平均的位置
        ma = prices.rolling(window=period).mean()
        momentum = (prices - ma) / ma
        return momentum

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据"""
        data = df.copy()
        
        # 1. 趋势强度
        data['trend_strength'] = self._calculate_trend(data['close'])
        
        # 2. 波动率
        data['volatility'] = self._calculate_volatility(data['close'], self.entry_period)
        
        # 3. 动量
        data['momentum'] = self._calculate_momentum(data['close'], self.entry_period)
        
        # 4. 价格位置
        data['price_position'] = (data['close'] - data['close'].rolling(50).min()) / \
                                (data['close'].rolling(50).max() - data['close'].rolling(50).min())
        
        # 5. 成交量确认
        data['volume_ma'] = data['volume'].rolling(window=20).mean()
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        
        return data

    def generate_signal(self, df: pd.DataFrame) -> int:
        """生成信号"""
        data = self._prepare(df)
        
        if len(data) < max(self.trend_period, self.entry_period) + 10:
            return 0
        
        recent = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 趋势判断
        trend_up = recent['trend_strength'] > self.trend_threshold
        trend_down = recent['trend_strength'] < -self.trend_threshold
        
        # 入场条件
        entry_up = (recent['momentum'] > self.entry_threshold and 
                   recent['price_position'] > 0.3 and
                   recent['volume_ratio'] > 1.2)
        
        entry_down = (recent['momentum'] < -self.entry_threshold and 
                     recent['price_position'] < 0.7 and
                     recent['volume_ratio'] > 1.2)
        
        # 生成信号
        if trend_up and entry_up:
            return 1  # 买入
        elif trend_down and entry_down:
            return -1  # 卖出
        
        return 0

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成信号序列"""
        df = self._prepare(data)
        df['signal'] = 0
        
        min_periods = max(self.trend_period, self.entry_period) + 10
        
        if len(df) < min_periods:
            return df
        
        # 生成信号
        for i in range(min_periods, len(df)):
            df_subset = df.iloc[:i+1]
            signal = self.generate_signal(df_subset)
            df.iloc[i, df.columns.get_loc('signal')] = signal
        
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
            "name": "Trend Following Strategy",
            "description": "基于趋势跟踪的长线交易策略",
            "parameters": {
                "trend_period": f"趋势周期: {self.trend_period}",
                "trend_threshold": f"趋势阈值: {self.trend_threshold}",
                "entry_period": f"入场周期: {self.entry_period}",
                "entry_threshold": f"入场阈值: {self.entry_threshold}",
                "stop_loss": f"止损: {self.stop_loss}",
                "take_profit": f"止盈: {self.take_profit}",
                "position_size": f"仓位: {self.position_size}",
                "confirm_window": f"确认窗口: {self.confirm_window}"
            }
        }
