from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.config.config import PROXY
from src.data.market_data import MarketDataFetcher
from src.trading.symbols import normalize_spot_symbol


def load_backtest_data(
    data_source,
    symbol,
    timeframe,
    days,
    start_date=None,
    end_date=None,
    exchange_id='okx',
):
    """Load OHLCV data for backtesting."""
    if data_source == 'mock':
        return create_mock_ohlcv(days=days, timeframe=timeframe)

    if data_source == 'okx':
        end = _parse_date(end_date) if end_date else datetime.now()
        start = _parse_date(start_date) if start_date else end - timedelta(days=days)
        fetcher = MarketDataFetcher(exchange_id=exchange_id, proxy=PROXY)
        data_symbol = normalize_spot_symbol(symbol)
        data = fetcher.get_historical_ohlcv(data_symbol, timeframe, start, end)
        if data.empty:
            raise ValueError("OKX 没有返回历史K线数据")
        return data

    raise ValueError(f"不支持的数据源: {data_source}. 支持: mock, okx")


def create_mock_ohlcv(days=30, timeframe='1m', base_price=70000.0):
    seconds = _timeframe_seconds(timeframe)
    periods = max(int(days * 86400 / seconds), 100)
    end_time = datetime.now()
    timestamps = pd.date_range(end=end_time, periods=periods, freq=pd.to_timedelta(seconds, unit='s'))

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.003, periods)
    trend = np.linspace(0, 0.08, periods) / periods
    close = [base_price]
    for idx in range(1, periods):
        close.append(max(close[-1] * (1 + returns[idx] + trend[idx]), base_price * 0.2))

    close = np.array(close)
    spread = close * rng.uniform(0.0005, 0.004, periods)
    open_price = close * (1 + rng.normal(0, 0.001, periods))
    high = np.maximum(open_price, close) + spread
    low = np.minimum(open_price, close) - spread
    volume = rng.uniform(100, 1000, periods)

    return pd.DataFrame(
        {
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
        },
        index=timestamps,
    )


def _parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d')


def _timeframe_seconds(timeframe):
    unit = timeframe[-1]
    number = int(timeframe[:-1])
    if unit == 'm':
        return number * 60
    if unit == 'h':
        return number * 3600
    if unit == 'd':
        return number * 86400
    raise ValueError(f"不支持的时间周期: {timeframe}")
