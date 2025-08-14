from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Optional, Union, List

class BaseExecutor(ABC):
    """交易执行基类，定义基本接口"""
    
    def __init__(self, exchange_id: str, api_key: str = None, api_secret: str = None, proxy: str = None):
        """
        初始化交易执行器
        Args:
            exchange_id: 交易所ID
            api_key: API密钥
            api_secret: API密钥对应的密钥
            proxy: 代理服务器地址
        """
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.proxy = proxy
        self.positions = {}  # 当前持仓
        self.orders = {}     # 当前订单
        
    @abstractmethod
    def place_order(self, symbol: str, order_type: str, side: str, 
                   amount: float, price: Optional[float] = None) -> Dict:
        """
        下单
        Args:
            symbol: 交易对
            order_type: 订单类型（limit/market）
            side: 买卖方向（buy/sell）
            amount: 数量
            price: 价格（市价单可为None）
        Returns:
            订单信息字典
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        撤单
        Args:
            order_id: 订单ID
            symbol: 交易对
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        查询订单
        Args:
            order_id: 订单ID
            symbol: 交易对
        Returns:
            订单信息字典
        """
        pass
    
    @abstractmethod
    def get_orders(self, symbol: str, status: str = None) -> List[Dict]:
        """
        查询订单列表
        Args:
            symbol: 交易对
            status: 订单状态（open/closed）
        Returns:
            订单信息列表
        """
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Dict:
        """
        查询持仓
        Args:
            symbol: 交易对
        Returns:
            持仓信息字典
        """
        pass
    
    @abstractmethod
    def get_balance(self, currency: str = None) -> Union[Dict, float]:
        """
        查询余额
        Args:
            currency: 币种，None表示查询所有
        Returns:
            余额信息字典或具体数值
        """
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict:
        """
        获取最新行情
        Args:
            symbol: 交易对
        Returns:
            行情信息字典
        """
        pass
    
    def update_positions(self):
        """更新持仓信息"""
        pass
    
    def update_orders(self):
        """更新订单信息"""
        pass 