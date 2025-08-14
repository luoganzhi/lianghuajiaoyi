import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    def __init__(
        self,
        rsi_period: int = 14,
        oversold_threshold: float = 30.0,
        overbought_threshold: float = 70.0,
        confirm_window: int = 1,
        use_divergence: bool = False,
        divergence_lookback: int = 5,
    ):
        super().__init__(
            {
                "rsi_period": rsi_period,
                "oversold_threshold": oversold_threshold,
                "overbought_threshold": overbought_threshold,
                "confirm_window": confirm_window,
                "use_divergence": use_divergence,
                "divergence_lookback": divergence_lookback,
            }
        )
        self.rsi_period = rsi_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.confirm_window = confirm_window
        self.use_divergence = use_divergence
        self.divergence_lookback = divergence_lookback

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _detect_divergence(self, df: pd.DataFrame) -> tuple:
        """检测RSI背离"""
        if not self.use_divergence or len(df) < self.divergence_lookback * 2:
            return False, False
        
        # 获取最近的价格和RSI数据
        recent_prices = df['close'].tail(self.divergence_lookback)
        recent_rsi = df['rsi'].tail(self.divergence_lookback)
        
        # 检测价格和RSI的趋势
        price_trend = recent_prices.iloc[-1] - recent_prices.iloc[0]
        rsi_trend = recent_rsi.iloc[-1] - recent_rsi.iloc[0]
        
        # 看涨背离：价格下跌但RSI上升
        bullish_divergence = price_trend < 0 and rsi_trend > 0
        
        # 看跌背离：价格上涨但RSI下降
        bearish_divergence = price_trend > 0 and rsi_trend < 0
        
        return bullish_divergence, bearish_divergence

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据，计算RSI和相关指标"""
        data = df.copy()
        
        # 计算RSI
        data['rsi'] = self._calculate_rsi(data['close'], self.rsi_period)
        
        # 计算RSI的变化率
        data['rsi_change'] = data['rsi'].diff()
        
        # 计算RSI的移动平均
        data['rsi_ma'] = data['rsi'].rolling(window=5).mean()
        
        # 标记超买超卖区域
        data['oversold'] = (data['rsi'] < self.oversold_threshold).astype(int)
        data['overbought'] = (data['rsi'] > self.overbought_threshold).astype(int)
        
        # 计算RSI的斜率
        data['rsi_slope'] = data['rsi'].diff(3)
        
        return data

    def generate_signal(self, df: pd.DataFrame) -> int:
        """生成单个信号"""
        data = self._prepare(df)
        
        if len(data) < self.rsi_period + 5:
            return 0
        
        recent = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 检测背离
        bullish_div, bearish_div = self._detect_divergence(data)
        
        # 买入信号条件
        buy_conditions = [
            # 条件1: RSI从超卖区域反弹
            prev['oversold'] == 1 and recent['oversold'] == 0,
            # 条件2: RSI上升且价格也上升
            recent['rsi_change'] > 0 and recent['close'] > prev['close'],
            # 条件3: RSI斜率向上
            recent['rsi_slope'] > 0,
            # 条件4: 看涨背离（如果启用）
            not self.use_divergence or bullish_div
        ]
        
        # 卖出信号条件
        sell_conditions = [
            # 条件1: RSI从超买区域回落
            prev['overbought'] == 1 and recent['overbought'] == 0,
            # 条件2: RSI下降且价格也下降
            recent['rsi_change'] < 0 and recent['close'] < prev['close'],
            # 条件3: RSI斜率向下
            recent['rsi_slope'] < 0,
            # 条件4: 看跌背离（如果启用）
            not self.use_divergence or bearish_div
        ]
        
        # 生成信号
        if sum(buy_conditions) >= 2:  # 至少满足2个买入条件
            return 1
        elif sum(sell_conditions) >= 2:  # 至少满足2个卖出条件
            return -1
        
        return 0

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成完整的信号序列"""
        df = self._prepare(data)
        df['signal'] = 0
        
        if len(df) < self.rsi_period + 5:
            return df
        
        # 生成信号
        for i in range(self.rsi_period + 5, len(df)):
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
            "name": "RSI Strategy",
            "description": "基于RSI超买超卖和背离的交易策略",
            "parameters": {
                "rsi_period": f"RSI计算周期: {self.rsi_period}",
                "oversold_threshold": f"超卖阈值: {self.oversold_threshold}",
                "overbought_threshold": f"超买阈值: {self.overbought_threshold}",
                "confirm_window": f"确认窗口: {self.confirm_window}",
                "use_divergence": f"使用背离: {self.use_divergence}",
                "divergence_lookback": f"背离检测周期: {self.divergence_lookback}"
            }
        }
