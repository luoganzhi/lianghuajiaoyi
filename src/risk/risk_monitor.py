from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import numpy as np
import logging

class RiskMonitor:
    def __init__(self,
                 capital_threshold: float,
                 daily_loss_limit: float,
                 max_positions: int = 5,
                 volatility_threshold: float = 0.03,
                 alert_callback: Optional[Callable] = None):
        """
        风险监控器
        
        Args:
            capital_threshold: 资金预警阈值
            daily_loss_limit: 每日最大亏损限制
            max_positions: 最大同时持仓数
            volatility_threshold: 波动率预警阈值
            alert_callback: 预警回调函数
        """
        self.capital_threshold = capital_threshold
        self.daily_loss_limit = daily_loss_limit
        self.max_positions = max_positions
        self.volatility_threshold = volatility_threshold
        self.alert_callback = alert_callback or self._default_alert
        
        self.initial_capital = 0.0
        self.current_capital = 0.0
        self.daily_pnl = 0.0
        self.positions: Dict[str, Dict] = {}
        self.price_history: Dict[str, List[float]] = {}
        self.alerts: List[Dict] = []
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='risk_monitor.log'
        )
        self.logger = logging.getLogger(__name__)
        
    def _default_alert(self, alert_type: str, message: str):
        """默认预警处理"""
        alert = {
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now()
        }
        self.alerts.append(alert)
        self.logger.warning(f"{alert_type}: {message}")
        
    def update_capital(self, current_capital: float):
        """更新资金状态"""
        if self.initial_capital == 0:
            self.initial_capital = current_capital
            
        self.current_capital = current_capital
        capital_change = (current_capital - self.initial_capital) / self.initial_capital
        
        # 检查资金损失是否超过阈值
        if capital_change < -self.capital_threshold:
            self.alert_callback(
                "CAPITAL_ALERT",
                f"Capital drawdown ({capital_change:.2%}) exceeded threshold ({self.capital_threshold:.2%})"
            )
            
    def update_daily_pnl(self, pnl_change: float):
        """更新每日盈亏"""
        self.daily_pnl += pnl_change
        
        # 检查每日亏损是否超过限制
        if self.daily_pnl < -self.daily_loss_limit:
            self.alert_callback(
                "DAILY_LOSS_ALERT",
                f"Daily loss ({self.daily_pnl:.2f}) exceeded limit ({self.daily_loss_limit:.2f})"
            )
            
    def update_position(self,
                       symbol: str,
                       size: float,
                       entry_price: float,
                       current_price: float):
        """更新持仓状态"""
        # 检查持仓数量是否超过限制
        if len(self.positions) >= self.max_positions and symbol not in self.positions:
            self.alert_callback(
                "POSITION_LIMIT_ALERT",
                f"Number of positions ({len(self.positions)}) reached maximum ({self.max_positions})"
            )
            return False
            
        self.positions[symbol] = {
            "size": size,
            "entry_price": entry_price,
            "current_price": current_price,
            "unrealized_pnl": (current_price - entry_price) * size
        }
        
        return True
        
    def update_price(self, symbol: str, price: float):
        """更新价格历史"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            
        self.price_history[symbol].append(price)
        
        # 保持最近100个价格点
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol].pop(0)
            
        # 计算波动率
        if len(self.price_history[symbol]) >= 20:
            returns = np.diff(np.log(self.price_history[symbol]))
            volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
            
            if volatility > self.volatility_threshold:
                self.alert_callback(
                    "VOLATILITY_ALERT",
                    f"High volatility detected for {symbol} ({volatility:.2%})"
                )
                
    def check_correlation(self, price_data: Dict[str, List[float]], threshold: float = 0.8):
        """检查持仓之间的相关性"""
        symbols = list(price_data.keys())
        n = len(symbols)
        
        if n < 2:
            return
            
        for i in range(n):
            for j in range(i + 1, n):
                if len(price_data[symbols[i]]) != len(price_data[symbols[j]]):
                    continue
                    
                corr = np.corrcoef(price_data[symbols[i]], price_data[symbols[j]])[0, 1]
                
                if abs(corr) > threshold:
                    self.alert_callback(
                        "CORRELATION_ALERT",
                        f"High correlation ({corr:.2f}) detected between {symbols[i]} and {symbols[j]}"
                    )
                    
    def get_monitoring_metrics(self) -> Dict:
        """获取监控指标"""
        # 计算回撤
        drawdown = 0.0
        if self.initial_capital > 0:
            drawdown = (self.initial_capital - self.current_capital) / self.initial_capital
        
        return {
            "current_capital": self.current_capital,
            "initial_capital": self.initial_capital,
            "drawdown": drawdown,
            "daily_pnl": self.daily_pnl,
            "position_count": len(self.positions),
            "positions": self.positions.copy(),
            "recent_alerts": self.alerts[-10:],  # 最近10条预警
            "total_exposure": sum(abs(p["size"] * p["current_price"]) for p in self.positions.values())
        }
        
    def reset_daily_metrics(self):
        """重置每日指标"""
        self.daily_pnl = 0.0
        # 保留最近24小时的预警
        cutoff_time = datetime.now() - timedelta(days=1)
        self.alerts = [a for a in self.alerts if a["timestamp"] >= cutoff_time] 