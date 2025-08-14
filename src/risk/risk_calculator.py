from typing import List, Dict, Optional
import numpy as np
from datetime import datetime, timedelta

class RiskCalculator:
    def __init__(self):
        """风险计算器"""
        self.trade_history: List[Dict] = []
        self.daily_pnl: Dict[str, float] = {}
        
    def add_trade(self,
                  symbol: str,
                  entry_price: float,
                  exit_price: float,
                  position_size: float,
                  entry_time: datetime,
                  exit_time: datetime,
                  trade_type: str):
        """
        添加交易记录
        
        Args:
            symbol: 交易对
            entry_price: 入场价格
            exit_price: 出场价格
            position_size: 交易数量
            entry_time: 入场时间
            exit_time: 出场时间
            trade_type: 交易类型 ('long' or 'short')
        """
        pnl = (exit_price - entry_price) * position_size
        if trade_type == 'short':
            pnl = -pnl
            
        trade = {
            "symbol": symbol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "position_size": position_size,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "trade_type": trade_type,
            "pnl": pnl
        }
        
        self.trade_history.append(trade)
        
        # 更新每日盈亏
        date_str = exit_time.strftime("%Y-%m-%d")
        self.daily_pnl[date_str] = self.daily_pnl.get(date_str, 0) + pnl
        
    def calculate_win_rate(self, lookback_days: Optional[int] = None) -> float:
        """计算胜率"""
        if not self.trade_history:
            return 0.0
            
        if lookback_days:
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            trades = [t for t in self.trade_history if t["exit_time"] >= cutoff_date]
        else:
            trades = self.trade_history
            
        if not trades:
            return 0.0
            
        winning_trades = sum(1 for t in trades if t["pnl"] > 0)
        return winning_trades / len(trades)
        
    def calculate_profit_factor(self, lookback_days: Optional[int] = None) -> float:
        """计算盈亏比"""
        if not self.trade_history:
            return 0.0
            
        if lookback_days:
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            trades = [t for t in self.trade_history if t["exit_time"] >= cutoff_date]
        else:
            trades = self.trade_history
            
        if not trades:
            return 0.0
            
        gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """计算夏普比率"""
        if not self.daily_pnl:
            return 0.0
            
        daily_returns = list(self.daily_pnl.values())
        avg_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)
        
        if std_return == 0:
            return 0.0
            
        daily_rf_rate = (1 + risk_free_rate) ** (1/252) - 1
        sharpe = (avg_return - daily_rf_rate) / std_return
        
        # 年化夏普比率
        return sharpe * np.sqrt(252)
        
    def calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.trade_history:
            return 0.0
            
        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0
        
        for trade in self.trade_history:
            cumulative_pnl += trade["pnl"]
            peak = max(peak, cumulative_pnl)
            drawdown = peak - cumulative_pnl
            max_drawdown = max(max_drawdown, drawdown)
            
        return max_drawdown
        
    def get_risk_metrics(self, lookback_days: Optional[int] = None) -> Dict:
        """获取风险指标"""
        return {
            "win_rate": self.calculate_win_rate(lookback_days),
            "profit_factor": self.calculate_profit_factor(lookback_days),
            "sharpe_ratio": self.calculate_sharpe_ratio(),
            "max_drawdown": self.calculate_max_drawdown(),
            "total_trades": len(self.trade_history),
            "total_pnl": sum(t["pnl"] for t in self.trade_history)
        }