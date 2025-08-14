import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class ProfitFilterStrategy(BaseStrategy):
    def __init__(
        self,
        # 基础策略参数
        ma_short: int = 10,
        ma_long: int = 30,
        
        # 盈利过滤参数
        min_profit_after_fee: float = 0.003,  # 扣除手续费后最小盈利0.3%
        fee_rate: float = 0.001,  # 手续费率0.1%
        
        # 信号确认
        confirm_window: int = 2,
        
        # 止损止盈
        stop_loss: float = 0.02,  # 2%止损
        take_profit: float = 0.05,  # 5%止盈
    ):
        super().__init__(
            {
                "ma_short": ma_short,
                "ma_long": ma_long,
                "min_profit_after_fee": min_profit_after_fee,
                "fee_rate": fee_rate,
                "confirm_window": confirm_window,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            }
        )
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.min_profit_after_fee = min_profit_after_fee
        self.fee_rate = fee_rate
        self.confirm_window = confirm_window
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    def _calculate_expected_profit(self, current_price: float, target_price: float) -> float:
        """计算预期盈利（扣除手续费）"""
        # 价格变化率
        price_change = (target_price - current_price) / current_price
        
        # 扣除手续费（买入+卖出）
        total_fee = self.fee_rate * 2  # 0.2%
        
        # 预期盈利
        expected_profit = price_change - total_fee
        
        return expected_profit

    def _estimate_target_price(self, df: pd.DataFrame, direction: int) -> float:
        """估算目标价格"""
        if direction == 1:  # 买入信号
            # 估算上涨目标价格（基于历史波动率）
            returns = df['close'].pct_change()
            volatility = returns.rolling(20).std().iloc[-1]
            target_price = df['close'].iloc[-1] * (1 + volatility * 2)  # 2倍标准差
        else:  # 卖出信号
            # 估算下跌目标价格
            returns = df['close'].pct_change()
            volatility = returns.rolling(20).std().iloc[-1]
            target_price = df['close'].iloc[-1] * (1 - volatility * 2)
        
        return target_price

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据"""
        data = df.copy()
        
        # 计算移动平均
        data['ma_short'] = data['close'].rolling(window=self.ma_short).mean()
        data['ma_long'] = data['close'].rolling(window=self.ma_long).mean()
        
        # 计算信号
        data['ma_signal'] = np.where(
            data['ma_short'] > data['ma_long'], 1, -1
        )
        
        # 计算信号变化
        data['signal_change'] = data['ma_signal'].diff()
        
        return data

    def generate_signal(self, df: pd.DataFrame) -> int:
        """生成信号"""
        data = self._prepare(df)
        
        if len(data) < self.ma_long + 5:
            return 0
        
        recent = data.iloc[-1]
        current_price = recent['close']
        
        # 检查信号变化
        if recent['signal_change'] > 0:  # 买入信号
            # 估算目标价格
            target_price = self._estimate_target_price(data, 1)
            
            # 计算预期盈利
            expected_profit = self._calculate_expected_profit(current_price, target_price)
            
            # 检查是否满足最小盈利要求
            if expected_profit >= self.min_profit_after_fee:
                return 1  # 满足盈利要求，执行买入
            else:
                return 0  # 不满足盈利要求，忽略信号
                
        elif recent['signal_change'] < 0:  # 卖出信号
            # 估算目标价格
            target_price = self._estimate_target_price(data, -1)
            
            # 计算预期盈利
            expected_profit = self._calculate_expected_profit(current_price, target_price)
            
            # 检查是否满足最小盈利要求
            if expected_profit >= self.min_profit_after_fee:
                return -1  # 满足盈利要求，执行卖出
            else:
                return 0  # 不满足盈利要求，忽略信号
        
        return 0

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成信号序列"""
        df = self._prepare(data)
        df['signal'] = 0
        df['expected_profit'] = 0.0
        
        min_periods = self.ma_long + 5
        
        if len(df) < min_periods:
            return df
        
        # 生成信号
        for i in range(min_periods, len(df)):
            df_subset = df.iloc[:i+1]
            signal = self.generate_signal(df_subset)
            df.iloc[i, df.columns.get_loc('signal')] = signal
            
            # 记录预期盈利
            if signal != 0:
                current_price = df.iloc[i]['close']
                if signal == 1:
                    target_price = self._estimate_target_price(df_subset, 1)
                else:
                    target_price = self._estimate_target_price(df_subset, -1)
                
                expected_profit = self._calculate_expected_profit(current_price, target_price)
                df.iloc[i, df.columns.get_loc('expected_profit')] = expected_profit
        
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
            "name": "Profit Filter Strategy",
            "description": "带有最小盈利要求的策略",
            "parameters": {
                "ma_short": f"短期MA: {self.ma_short}",
                "ma_long": f"长期MA: {self.ma_long}",
                "min_profit_after_fee": f"最小盈利要求: {self.min_profit_after_fee*100:.1f}%",
                "fee_rate": f"手续费率: {self.fee_rate*100:.1f}%",
                "confirm_window": f"确认窗口: {self.confirm_window}",
                "stop_loss": f"止损: {self.stop_loss*100:.1f}%",
                "take_profit": f"止盈: {self.take_profit*100:.1f}%"
            }
        }
