from abc import ABC, abstractmethod
import pandas as pd

class BaseBacktester(ABC):  # ABC是Python的抽象基类(Abstract Base Class)，用于定义接口规范
                            # 继承ABC的好处:
                            # 1. 强制子类必须实现抽象方法(@abstractmethod装饰的方法)
                            # 2. 提供统一的接口规范，确保所有回测器都实现run_backtest方法
                            # 3. 提高代码的可维护性和可扩展性
    def __init__(self, initial_cash=100000):
        """
        初始化回测器
        Args:
            initial_cash (float): 初始资金，默认为100000
        """
        self.initial_cash = initial_cash
    @abstractmethod
    def run_backtest(self, data: pd.DataFrame, signals: pd.DataFrame) -> dict:
        """
        执行回测
        Args:
            data: 行情数据
            signals: 策略信号
        Returns:
            回测结果字典
        """
        pass
