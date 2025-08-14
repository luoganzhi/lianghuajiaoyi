from typing import Dict, Optional, Tuple
import numpy as np

class StopManager:
    def __init__(self,
                 default_stop_loss_pct: float = 0.02,
                 default_take_profit_pct: float = 0.05,
                 trailing_stop_pct: Optional[float] = None,
                 time_stop_minutes: Optional[int] = None):
        """
        止损止盈管理器
        
        Args:
            default_stop_loss_pct: 默认止损百分比
            default_take_profit_pct: 默认止盈百分比
            trailing_stop_pct: 追踪止损百分比
            time_stop_minutes: 最大持仓时间（分钟）
        """
        self.default_stop_loss_pct = default_stop_loss_pct
        self.default_take_profit_pct = default_take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.time_stop_minutes = time_stop_minutes
        
        self.stops: Dict[str, Dict] = {}  # 记录所有止损止盈信息
        
    def calculate_stop_levels(self,
                            symbol: str,
                            entry_price: float,
                            atr: Optional[float] = None) -> Tuple[float, float]:
        """
        计算止损止盈价格
        
        Args:
            symbol: 交易对
            entry_price: 入场价格
            atr: Average True Range值（用于动态止损）
        """
        if atr is not None:
            # 使用ATR计算动态止损
            stop_loss = entry_price - (atr * 2)  # 2倍ATR止损
            take_profit = entry_price + (atr * 3)  # 3倍ATR止盈
        else:
            # 使用固定百分比
            stop_loss = entry_price * (1 - self.default_stop_loss_pct)
            take_profit = entry_price * (1 + self.default_take_profit_pct)
            
        return stop_loss, take_profit
    
    def add_stop_orders(self,
                       symbol: str,
                       entry_price: float,
                       position_size: float,
                       stop_loss: Optional[float] = None,
                       take_profit: Optional[float] = None):
        """添加止损止盈订单"""
        if stop_loss is None or take_profit is None:
            stop_loss, take_profit = self.calculate_stop_levels(symbol, entry_price)
            
        self.stops[symbol] = {
            "entry_price": entry_price,
            "position_size": position_size,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "highest_price": entry_price,
            "trailing_stop": None
        }
        
        if self.trailing_stop_pct:
            self.stops[symbol]["trailing_stop"] = entry_price * (1 - self.trailing_stop_pct)
    
    def update_stops(self, symbol: str, current_price: float) -> Dict[str, bool]:
        """
        更新并检查止损止盈条件
        
        Returns:
            Dict with stop_loss_triggered and take_profit_triggered flags
        """
        if symbol not in self.stops:
            return {"stop_loss_triggered": False, "take_profit_triggered": False}
            
        stop_info = self.stops[symbol]
        result = {
            "stop_loss_triggered": False,
            "take_profit_triggered": False
        }
        
        # 更新最高价格
        if current_price > stop_info["highest_price"]:
            stop_info["highest_price"] = current_price
            
            # 更新追踪止损
            if self.trailing_stop_pct:
                stop_info["trailing_stop"] = current_price * (1 - self.trailing_stop_pct)
        
        # 检查止损条件
        if stop_info["trailing_stop"] and current_price <= stop_info["trailing_stop"]:
            result["stop_loss_triggered"] = True
        elif current_price <= stop_info["stop_loss"]:
            result["stop_loss_triggered"] = True
            
        # 检查止盈条件
        if current_price >= stop_info["take_profit"]:
            result["take_profit_triggered"] = True
            
        return result
    
    def remove_stops(self, symbol: str):
        """移除止损止盈订单"""
        if symbol in self.stops:
            del self.stops[symbol]
    
    def get_stop_metrics(self, symbol: str) -> Dict:
        """获取止损止盈相关指标"""
        if symbol not in self.stops:
            return {}
            
        stop_info = self.stops[symbol]
        return {
            "current_stop_loss": stop_info["trailing_stop"] or stop_info["stop_loss"],
            "take_profit": stop_info["take_profit"],
            "highest_price": stop_info["highest_price"],
            "risk_reward_ratio": (stop_info["take_profit"] - stop_info["entry_price"]) / 
                               (stop_info["entry_price"] - stop_info["stop_loss"])
        } 