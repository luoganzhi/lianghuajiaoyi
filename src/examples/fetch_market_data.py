import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.market_data import MarketDataFetcher
from config.config import EXCHANGE_CONFIG, TRADING_CONFIG
import pandas as pd
from datetime import datetime, timedelta

def main():
    # 初始化数据获取器
    exchange_id = 'binance'
    config = EXCHANGE_CONFIG[exchange_id]
    fetcher = MarketDataFetcher(
        exchange_id=exchange_id,
        api_key=config['api_key'],
        secret=config['secret']
    )

    # 获取当前行情
    symbol = TRADING_CONFIG['default_symbol']
    ticker = fetcher.get_ticker(symbol)
    print(f"\n当前{symbol}行情:")
    print(f"最新价格: {ticker['last']}")
    print(f"24小时成交量: {ticker['quoteVolume']}")

    # 获取K线数据
    timeframe = TRADING_CONFIG['default_timeframe']
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    ohlcv = fetcher.get_ohlcv(
        symbol=symbol,
        timeframe=timeframe,
        since=int(start_time.timestamp() * 1000)
    )
    print(f"\n最近一小时的K线数据:")
    print(ohlcv.tail())

    # 获取订单簿数据
    order_book = fetcher.get_order_book(symbol, limit=5)
    print(f"\n订单簿数据 (前5档):")
    print("买单:")
    for bid in order_book['bids'][:5]:
        print(f"价格: {bid[0]}, 数量: {bid[1]}")
    print("\n卖单:")
    for ask in order_book['asks'][:5]:
        print(f"价格: {ask[0]}, 数量: {ask[1]}")

if __name__ == "__main__":
    main() 