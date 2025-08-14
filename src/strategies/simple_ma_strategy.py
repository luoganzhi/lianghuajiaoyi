import pandas as pd
from .base_strategy import BaseStrategy

class SimpleMAStrategy(BaseStrategy):
    def __init__(self, short_window=5, long_window=20):
        super().__init__({'short_window': short_window, 'long_window': long_window})
        self.short_window = short_window
        self.long_window = long_window

    def generate_signal(self, df: pd.DataFrame) -> int:
        if len(df) < self.long_window:
            return 0
        short_ma = df['close'].rolling(window=self.short_window).mean().iloc[-1]
        long_ma = df['close'].rolling(window=self.long_window).mean().iloc[-1]
        prev_short_ma = df['close'].rolling(window=self.short_window).mean().iloc[-2]
        prev_long_ma = df['close'].rolling(window=self.long_window).mean().iloc[-2]
        if prev_short_ma < prev_long_ma and short_ma > long_ma:
            return 1
        elif prev_short_ma > prev_long_ma and short_ma < long_ma:
            return -1
        else:
            return 0

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: 包含行情数据的DataFrame
            
        Returns:
            包含信号的DataFrame（需包含'signal'列，1=买入，-1=卖出，0=空仓）
        """
        df = data.copy()
        
        # 计算移动平均线
        df['ma_short'] = df['close'].rolling(window=self.short_window).mean()
        df['ma_long'] = df['close'].rolling(window=self.long_window).mean()
        
        # 初始化信号列
        df['signal'] = 0
        
        # 生成交叉信号
        for i in range(self.long_window, len(df)):
            if (df['ma_short'].iloc[i-1] < df['ma_long'].iloc[i-1] and 
                df['ma_short'].iloc[i] > df['ma_long'].iloc[i]):
                df.loc[df.index[i], 'signal'] = 1  # 金叉买入
            elif (df['ma_short'].iloc[i-1] > df['ma_long'].iloc[i-1] and 
                  df['ma_short'].iloc[i] < df['ma_long'].iloc[i]):
                df.loc[df.index[i], 'signal'] = -1  # 死叉卖出
                
        return df 