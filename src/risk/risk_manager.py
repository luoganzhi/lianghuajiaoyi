from typing import Dict, Optional, List
import numpy as np
from datetime import datetime
from data.market_data import MarketDataFetcher
from config.config import PROXY, IS_SIMULATED, SIM_API_KEY, SIM_API_SECRET, SIM_API_PASSWORD, REAL_API_KEY, REAL_API_SECRET, REAL_API_PASSWORD, RISK_CONFIG
from execution.okx_executor import OKXExecutor
from risk.position_manager import PositionManager

class RiskManager:
    def __init__(self):
        """
        风险管理器 - 使用统一的风控配置
        """
        # 从RISK_CONFIG获取配置
        self.max_position_size = RISK_CONFIG['position']['max_size']
        self.max_drawdown = RISK_CONFIG['risk_limits']['max_drawdown']
        self.stop_loss_pct = RISK_CONFIG['stop_loss']['fixed_pct']
        self.take_profit_pct = RISK_CONFIG['take_profit']['fixed_pct']
        self.max_daily_trades = RISK_CONFIG['risk_limits']['max_daily_trades']
        
        # 交易状态跟踪
        self.daily_trades_count = 0
        self.last_trade_date = None
        self.current_drawdown = 0
        self.peak_value = 0
        self.positions: Dict[str, float] = {}  # 当前持仓
        
        # 初始化市场数据获取器
        self.market_data = MarketDataFetcher(
            exchange_id='okx',
            proxy=PROXY
        )
        
    def get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            ticker = self.market_data.get_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            print(f"获取价格失败: {str(e)}")
            return 0.0
    
    def check_position_limit(self, symbol: str, size: float, total_capital: float) -> bool:
        """检查是否超过最大仓位限制"""
        current_price = self.get_current_price(symbol)
        if current_price <= 0:
            return False
        position_ratio = (size * current_price) / total_capital
        return position_ratio <= self.max_position_size
    
    def check_drawdown_limit(self, current_value: float) -> bool:
        """检查是否超过最大回撤限制"""
        self.peak_value = max(self.peak_value, current_value)
        self.current_drawdown = (self.peak_value - current_value) / self.peak_value
        return self.current_drawdown <= self.max_drawdown
    
    def should_stop_loss(self, symbol: str, entry_price: float, current_price: float) -> bool:
        """检查是否应该止损"""
        if entry_price is None:
            return False
        return (entry_price - current_price) / entry_price >= self.stop_loss_pct
    
    def should_take_profit(self, symbol: str, entry_price: float, current_price: float) -> bool:
        """检查是否应该止盈"""
        if entry_price is None:
            return False
        return (current_price - entry_price) / entry_price >= self.take_profit_pct
    
    def can_place_trade(self) -> bool:
        """检查是否可以进行新的交易"""
        current_date = datetime.now().date()
        
        # 重置每日交易计数
        if self.last_trade_date != current_date:
            self.daily_trades_count = 0
            self.last_trade_date = current_date
            
        return self.daily_trades_count < self.max_daily_trades
    
    def update_trade_count(self):
        """更新交易次数"""
        self.daily_trades_count += 1
    
    def get_position_size(self, symbol: str) -> float:
        """获取当前持仓大小"""
        return self.positions.get(symbol, 0)
    
    def update_position(self, symbol: str, size: float):
        """更新持仓信息"""
        self.positions[symbol] = size
    
    def get_risk_metrics(self) -> Dict:
        """获取风险指标"""
        return {
            "current_drawdown": self.current_drawdown,
            "daily_trades": self.daily_trades_count,
            "positions": self.positions.copy()
        }
    
    def validate_trade(self, 
                      symbol: str, 
                      size: float, 
                      total_capital: float,
                      entry_price: Optional[float] = None) -> Dict[str, bool]:
        """验证交易是否满足所有风控条件"""
        return {
            "position_valid": self.check_position_limit(symbol, size, total_capital),
            "drawdown_valid": self.check_drawdown_limit(total_capital),
            "can_trade": self.can_place_trade()
        }

class PositionManager:
    def __init__(self, market_data_fetcher, account_manager, max_leverage=1.0, position_sizing_method="fixed_fraction", risk_per_trade=0.02):
        self.market_data = market_data_fetcher
        self.account = account_manager

    def calculate_position_size(self, symbol, risk_per_trade):
        price = self.market_data.get_ticker(symbol)['last']
        capital = self.account.get_total_capital()
        # ...后续逻辑 

def main():
    # 根据环境选择API信息
    if IS_SIMULATED:
        api_key = SIM_API_KEY
        api_secret = SIM_API_SECRET
        api_password = SIM_API_PASSWORD
    else:
        api_key = REAL_API_KEY
        api_secret = REAL_API_SECRET
        api_password = REAL_API_PASSWORD

    # 初始化行情和账户模块
    market_data = MarketDataFetcher(exchange_id='okx', proxy=PROXY)
    account = OKXExecutor(api_key, api_secret, api_password, proxy=PROXY, is_simulated=IS_SIMULATED)
    position_manager = PositionManager(
        market_data_fetcher=market_data,
        account_manager=account,
        max_leverage=1.0,
        position_sizing_method="fixed_fraction",
        risk_per_trade=0.02
    )

    symbol = "BTC-USDT"
    entry_price = float(market_data.get_ticker(symbol)['last'])
    stop_loss = entry_price * 0.98  # 2%止损

    # 计算建议仓位
    position_size = position_manager.calculate_position_size(symbol, stop_loss)
    print(f"建议仓位大小: {position_size:.4f} BTC")

    # 添加持仓
    position_manager.add_position(symbol, position_size, entry_price, stop_loss, take_profit=entry_price*1.05)
    print("已添加持仓。")

    # 更新持仓盈亏
    position_manager.update_position(symbol)
    metrics = position_manager.get_position_metrics()
    print(f"持仓指标: {metrics}")

    # 平仓
    realized_pnl = position_manager.close_position(symbol)
    print(f"平仓实现盈亏: {realized_pnl}")

def test_position_manager():
    print("\n测试仓位管理器...")

    # 初始化仓位管理器（用真实行情和账户模块）
    position_manager = PositionManager(
        market_data_fetcher=market_data,
        account_manager=account,
        max_leverage=1.0,
        position_sizing_method="fixed_fraction",
        risk_per_trade=0.02
    )

    symbol = "BTC-USDT"
    entry_price = float(market_data.get_ticker(symbol)['last'])
    stop_loss = entry_price * 0.98  # 2%止损

    # 计算建议仓位
    position_size = position_manager.calculate_position_size(symbol, stop_loss)
    print(f"建议仓位大小: {position_size:.4f} BTC")

    # 添加持仓
    position_manager.add_position(symbol, position_size, entry_price, stop_loss, take_profit=entry_price*1.05)
    print("已添加持仓。")

    # 更新持仓盈亏
    position_manager.update_position(symbol)
    metrics = position_manager.get_position_metrics()
    print(f"持仓指标: {metrics}")

    # 平仓
    realized_pnl = position_manager.close_position(symbol)
    print(f"平仓实现盈亏: {realized_pnl}")

if __name__ == "__main__":
    main() 