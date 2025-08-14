from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, params: dict = None):
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        根据输入数据生成买卖信号
        Args:
            data: 包含行情和特征的DataFrame
        Returns:
            包含信号的DataFrame（需包含'signal'列，1=买入，-1=卖出，0=空仓）
        """
        pass 