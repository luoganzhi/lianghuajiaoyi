import pandas as pd
from .base_strategy import BaseStrategy

class MeanReversionStrategy(BaseStrategy):
    def __init__(self, window=20, num_std=2):
        super().__init__({'window': window, 'num_std': num_std})
        self.window = window
        self.num_std = num_std

    def generate_signal(self, df: pd.DataFrame) -> int:
        if len(df) < self.window:
            return 0
        ma = df['close'].rolling(window=self.window).mean().iloc[-1]
        std = df['close'].rolling(window=self.window).std().iloc[-1]
        upper = ma + self.num_std * std
        lower = ma - self.num_std * std
        price = df['close'].iloc[-1]
        if price < lower:
            return 1
        elif price > upper:
            return -1
        else:
            return 0

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df['ma'] = df['close'].rolling(window=self.window).mean()
        df['std'] = df['close'].rolling(window=self.window).std()
        df['upper'] = df['ma'] + self.num_std * df['std']
        df['lower'] = df['ma'] - self.num_std * df['std']
        df['signal'] = 0
        # 超卖做多，超买做空
        df.loc[df['close'] < df['lower'], 'signal'] = 1
        df.loc[df['close'] > df['upper'], 'signal'] = -1
        return df 