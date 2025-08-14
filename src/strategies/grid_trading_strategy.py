import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class GridTradingStrategy(BaseStrategy):
    def __init__(
        self,
        # 网格参数
        grid_levels: int = 5,  # 网格层数
        grid_spacing: float = 0.02,  # 网格间距 2%
        
        # 动态网格
        use_dynamic_grid: bool = True,
        volatility_period: int = 20,
        volatility_multiplier: float = 1.5,
        
        # 仓位管理
        base_position: float = 0.2,  # 基础仓位
        max_position: float = 0.8,   # 最大仓位
        
        # 风险控制
        max_drawdown: float = 0.1,   # 最大回撤 10%
        
        # 确认参数
        confirm_window: int = 2,
    ):
        super().__init__(
            {
                "grid_levels": grid_levels,
                "grid_spacing": grid_spacing,
                "use_dynamic_grid": use_dynamic_grid,
                "volatility_period": volatility_period,
                "volatility_multiplier": volatility_multiplier,
                "base_position": base_position,
                "max_position": max_position,
                "max_drawdown": max_drawdown,
                "confirm_window": confirm_window,
            }
        )
        self.grid_levels = grid_levels
        self.grid_spacing = grid_spacing
        self.use_dynamic_grid = use_dynamic_grid
        self.volatility_period = volatility_period
        self.volatility_multiplier = volatility_multiplier
        self.base_position = base_position
        self.max_position = max_position
        self.max_drawdown = max_drawdown
        self.confirm_window = confirm_window

    def _calculate_volatility(self, prices: pd.Series) -> pd.Series:
        """计算波动率"""
        returns = prices.pct_change()
        volatility = returns.rolling(window=self.volatility_period).std()
        return volatility

    def _calculate_grid_levels(self, price: float, volatility: float) -> list:
        """计算网格价格水平"""
        if self.use_dynamic_grid:
            # 动态网格间距
            dynamic_spacing = self.grid_spacing * volatility * self.volatility_multiplier
        else:
            dynamic_spacing = self.grid_spacing
        
        grid_prices = []
        for i in range(-self.grid_levels, self.grid_levels + 1):
            grid_price = price * (1 + i * dynamic_spacing)
            grid_prices.append(grid_price)
        
        return sorted(grid_prices)

    def _calculate_position_size(self, price: float, grid_prices: list, current_position: float) -> float:
        """计算仓位大小"""
        # 找到当前价格在网格中的位置
        grid_index = None
        for i, grid_price in enumerate(grid_prices):
            if price <= grid_price:
                grid_index = i
                break
        
        if grid_index is None:
            grid_index = len(grid_prices) - 1
        
        # 根据网格位置计算仓位
        position_ratio = grid_index / len(grid_prices)
        target_position = self.base_position + (self.max_position - self.base_position) * position_ratio
        
        return target_position

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据"""
        data = df.copy()
        
        # 计算波动率
        data['volatility'] = self._calculate_volatility(data['close'])
        
        # 计算移动平均作为网格中心
        data['grid_center'] = data['close'].rolling(window=20).mean()
        
        # 计算网格价格水平
        data['grid_prices'] = data.apply(
            lambda row: self._calculate_grid_levels(row['close'], row['volatility']), 
            axis=1
        )
        
        # 计算价格在网格中的位置
        data['grid_position'] = data.apply(
            lambda row: self._calculate_position_size(row['close'], row['grid_prices'], 0), 
            axis=1
        )
        
        return data

    def generate_signal(self, df: pd.DataFrame, current_position: float = 0) -> tuple:
        """生成信号和仓位"""
        data = self._prepare(df)
        
        if len(data) < self.volatility_period + 10:
            return 0, 0
        
        recent = data.iloc[-1]
        prev = data.iloc[-2]
        
        # 计算目标仓位
        target_position = recent['grid_position']
        
        # 计算仓位变化
        position_change = target_position - current_position
        
        # 生成信号
        if position_change > 0.1:  # 需要买入
            return 1, target_position
        elif position_change < -0.1:  # 需要卖出
            return -1, target_position
        else:
            return 0, current_position

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成信号序列"""
        df = self._prepare(data)
        df['signal'] = 0
        df['target_position'] = 0
        
        min_periods = self.volatility_period + 10
        
        if len(df) < min_periods:
            return df
        
        current_position = 0
        
        # 生成信号
        for i in range(min_periods, len(df)):
            df_subset = df.iloc[:i+1]
            signal, target_pos = self.generate_signal(df_subset, current_position)
            
            df.iloc[i, df.columns.get_loc('signal')] = signal
            df.iloc[i, df.columns.get_loc('target_position')] = target_pos
            
            if signal != 0:
                current_position = target_pos
        
        return df

    def get_strategy_info(self) -> dict:
        """获取策略信息"""
        return {
            "name": "Grid Trading Strategy",
            "description": "基于网格交易的震荡市场策略",
            "parameters": {
                "grid_levels": f"网格层数: {self.grid_levels}",
                "grid_spacing": f"网格间距: {self.grid_spacing}",
                "use_dynamic_grid": f"动态网格: {self.use_dynamic_grid}",
                "volatility_period": f"波动率周期: {self.volatility_period}",
                "volatility_multiplier": f"波动率倍数: {self.volatility_multiplier}",
                "base_position": f"基础仓位: {self.base_position}",
                "max_position": f"最大仓位: {self.max_position}",
                "max_drawdown": f"最大回撤: {self.max_drawdown}",
                "confirm_window": f"确认窗口: {self.confirm_window}"
            }
        }
