import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.market_data import MarketDataFetcher
from src.data.data_processor import DataProcessor
from src.strategies.simple_ma_strategy import SimpleMAStrategy
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_strategy():
    try:
        # 获取行情数据
        exchange_id = 'okx'
        proxy = 'http://127.0.0.1:7890'
        fetcher = MarketDataFetcher(exchange_id=exchange_id, proxy=proxy)
        symbol = 'BTC-USDT'
        timeframe = '1h'
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)  # 获取30天的数据
        logger.info(f"获取{symbol}的{timeframe}K线数据")
        ohlcv = fetcher.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=int(start_time.timestamp() * 1000)
        )
        # 数据处理
        processor = DataProcessor()
        processed_data = processor.process_ohlcv(ohlcv)
        # 策略信号生成
        strategy = SimpleMAStrategy(short_window=5, long_window=20)
        signals = strategy.generate_signals(processed_data)
        logger.info(f'总数据量: {signals.shape[0]}')
        logger.info(signals[['timestamp', 'close', 'ma_short', 'ma_long', 'signal']].head(25).to_string())  # 打印前25行
        logger.info(signals[['timestamp', 'close', 'ma_short', 'ma_long', 'signal']].tail(25).to_string())  # 打印后25行
        logger.info('\n' + '='*40 + '\n非零信号:')
        nonzero_signals = signals[signals['signal'] != 0][['timestamp', 'close', 'ma_short', 'ma_long', 'signal']]
        if not nonzero_signals.empty:
            print('\n' + nonzero_signals.to_string(index=False))
        else:
            print('\n无交叉信号')
        logger.info("\n策略模块测试完成！")
        return True
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        if hasattr(e, 'args'):
            logger.error(f"详细错误信息: {e.args}")
        return False

if __name__ == "__main__":
    test_strategy() 