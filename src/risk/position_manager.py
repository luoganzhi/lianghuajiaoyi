from typing import Dict, Optional
import numpy as np

class PositionManager:
    def __init__(self,
                 market_data_fetcher,   # 实时行情获取器，如MarketDataFetcher
                 account_manager,      # 账户管理器，如OKXExecutor
                 max_leverage: float = 1.0,
                 position_sizing_method: str = "fixed_fraction",
                 risk_per_trade: float = 0.02):
        """
        仓位管理器
        Args:
            market_data_fetcher: 实时行情获取器实例
            account_manager: 账户管理器实例
            max_leverage: 最大杠杆倍数
            position_sizing_method: 仓位计算方法 ('fixed_fraction', 'kelly', 'fixed_amount')
            risk_per_trade: 每笔交易风险比例
        """
        self.market_data = market_data_fetcher
        self.account = account_manager
        self.max_leverage = max_leverage
        self.position_sizing_method = position_sizing_method
        self.risk_per_trade = risk_per_trade
        self.positions: Dict[str, Dict] = {}  # 记录所有持仓信息

    def calculate_position_size(self,
                              symbol: str,
                              stop_loss: float,
                              win_rate: Optional[float] = None,
                              profit_loss_ratio: Optional[float] = None) -> float:
        """
        计算建议持仓大小，全部用真实行情和账户数据
        Args:
            symbol: 交易对
            stop_loss: 止损价格
            win_rate: 胜率（用于Kelly公式）
            profit_loss_ratio: 盈亏比（用于Kelly公式）
        """
        entry_price = float(self.market_data.get_ticker(symbol)['last'])
        current_capital = float(self.account.get_balance("USDT"))  # 假设USDT为主币种
        risk_amount = current_capital * self.risk_per_trade
        position_size = 0.0

        if self.position_sizing_method == "fixed_fraction":
            risk_per_unit = abs(entry_price - stop_loss)
            position_size = risk_amount / risk_per_unit
        elif self.position_sizing_method == "kelly" and win_rate and profit_loss_ratio:
            kelly_fraction = win_rate - ((1 - win_rate) / profit_loss_ratio)
            kelly_fraction = max(0, min(kelly_fraction, 0.5))
            position_size = (current_capital * kelly_fraction) / entry_price
        elif self.position_sizing_method == "fixed_amount":
            position_size = risk_amount / entry_price

        max_position = current_capital * self.max_leverage / entry_price
        position_size = min(position_size, max_position)
        return position_size

    def add_position(self,
                    symbol: str,
                    size: float,
                    entry_price: float,
                    stop_loss: float,
                    take_profit: Optional[float] = None):
        """添加新持仓"""
        self.positions[symbol] = {
            "size": size,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "unrealized_pnl": 0.0
        }

    def update_position(self,
                       symbol: str):
        """更新持仓盈亏，自动获取最新价格"""
        if symbol in self.positions:
            position = self.positions[symbol]
            current_price = float(self.market_data.get_ticker(symbol)['last'])
            position["unrealized_pnl"] = (current_price - position["entry_price"]) * position["size"]
            position["current_price"] = current_price

    def close_position(self, symbol: str):
        """平仓并计算实现盈亏，自动获取最新价格"""
        if symbol in self.positions:
            position = self.positions[symbol]
            exit_price = float(self.market_data.get_ticker(symbol)['last'])
            realized_pnl = (exit_price - position["entry_price"]) * position["size"]
            # 这里不再维护current_capital，建议由账户模块统一管理资金
            del self.positions[symbol]
            return realized_pnl
        return 0.0

    def get_total_exposure(self) -> float:
        """计算总持仓风险敞口，全部用最新价格"""
        total_exposure = 0.0
        for symbol, position in self.positions.items():
            current_price = float(self.market_data.get_ticker(symbol)['last'])
            total_exposure += abs(position["size"] * current_price)
        return total_exposure

    def get_position_metrics(self) -> Dict:
        """获取持仓相关指标，全部用最新数据"""
        current_capital = float(self.account.get_balance("USDT"))
        total_exposure = self.get_total_exposure()
        return {
            "total_capital": current_capital,
            "total_exposure": total_exposure,
            "leverage": total_exposure / current_capital if current_capital > 0 else 0,
            "positions": self.positions.copy()
        }