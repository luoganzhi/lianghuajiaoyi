import pandas as pd
from .base_strategy import BaseStrategy


class MACurveStrategy(BaseStrategy):
    def __init__(
        self,
        ma_window: int = 50,
        slope_lookback: int = 5,
        slope_threshold: float = 0.0,
        confirm_window: int = 1,
    ):
        super().__init__(
            {
                "ma_window": ma_window,
                "slope_lookback": slope_lookback,
                "slope_threshold": slope_threshold,
                "confirm_window": confirm_window,
            }
        )
        self.ma_window = ma_window
        self.slope_lookback = slope_lookback
        self.slope_threshold = slope_threshold
        self.confirm_window = confirm_window

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        data["ma"] = data["close"].rolling(window=self.ma_window, min_periods=self.ma_window).mean()
        data["ma_slope"] = (data["ma"] - data["ma"].shift(self.slope_lookback)) / max(self.slope_lookback, 1)
        data["price_above_ma"] = (data["close"] > data["ma"]).astype(int)
        data["price_above_ma_prev"] = data["price_above_ma"].shift(1)
        return data

    def generate_signal(self, df: pd.DataFrame) -> int:
        data = self._prepare(df)
        if len(data) < max(self.ma_window, self.slope_lookback) + 2:
            return 0

        recent = data.iloc[-1]
        prev = data.iloc[-2]

        crossed_up = prev["price_above_ma"] == 0 and recent["price_above_ma"] == 1
        crossed_down = prev["price_above_ma"] == 1 and recent["price_above_ma"] == 0

        if crossed_up and recent["ma_slope"] > self.slope_threshold:
            return 1
        if crossed_down and recent["ma_slope"] < -self.slope_threshold:
            return -1
        return 0

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = self._prepare(data)
        df["signal"] = 0
        if len(df) < max(self.ma_window, self.slope_lookback) + 2:
            return df

        crosses_up = (df["price_above_ma_prev"] == 0) & (df["price_above_ma"] == 1) & (df["ma_slope"] > self.slope_threshold)
        crosses_down = (df["price_above_ma_prev"] == 1) & (df["price_above_ma"] == 0) & (df["ma_slope"] < -self.slope_threshold)

        df.loc[crosses_up, "signal"] = 1
        df.loc[crosses_down, "signal"] = -1

        if self.confirm_window > 1:
            df["signal"] = (
                df["signal"].rolling(self.confirm_window).apply(lambda x: 1 if (x == 1).sum() == self.confirm_window else (-1 if (x == -1).sum() == self.confirm_window else 0), raw=False)
            ).fillna(0)

        return df



