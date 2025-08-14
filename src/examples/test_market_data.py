import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.market_data import MarketDataFetcher
from config.config import TRADING_CONFIG
import pandas as pd
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_market_data():
    try:
        # 初始化数据获取器（不带API Key）
        exchange_id = 'okx'  # 使用欧易（OKX）
        
        # 配置代理（如果有的话）
        proxy = 'http://127.0.0.1:7890'  # 根据实际情况修改代理地址
        
        # 尝试不带API Key访问
        fetcher = MarketDataFetcher(
            exchange_id=exchange_id,
            proxy=proxy  # 添加代理支持
        )
        
        # 测试1: 获取当前行情
        symbol = 'BTC-USDT'  # 使用OKX的币对格式
        logger.info(f"测试1: 获取{symbol}当前行情")
        ticker = fetcher.get_ticker(symbol)
        logger.info(f"最新价格: {ticker['last']}")
        logger.info(f"24小时成交量: {ticker['quoteVolume']}")
        
        # 测试2: 获取K线数据
        logger.info("\n测试2: 获取K线数据")
        timeframe = '1m'  # 1分钟K线
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        ohlcv = fetcher.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=int(start_time.timestamp() * 1000)
        )
        logger.info(f"获取到 {len(ohlcv)} 条K线数据")
        logger.info("最近5条K线数据:")
        logger.info(ohlcv.tail())
        
        # 测试3: 获取订单簿数据
        logger.info("\n测试3: 获取订单簿数据")
        order_book = fetcher.get_order_book(symbol, limit=5)
        logger.info("买单前5档:")
        for bid in order_book['bids'][:5]:
            logger.info(f"价格: {bid[0]}, 数量: {bid[1]}")
        logger.info("\n卖单前5档:")
        for ask in order_book['asks'][:5]:
            logger.info(f"价格: {ask[0]}, 数量: {ask[1]}")
            
        # 测试4: 获取最近成交记录
        logger.info("\n测试4: 获取最近成交记录")
        trades = fetcher.get_trades(symbol, limit=5)
        logger.info(f"获取到 {len(trades)} 条成交记录")
        for trade in trades:
            logger.info(f"价格: {trade['price']}, 数量: {trade['amount']}, 方向: {trade['side']}")
            
        logger.info("\n所有测试完成！数据获取模块功能正常。")
        return True
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        print("详细错误信息:", e.args)  # 打印详细错误信息
        return False

if __name__ == "__main__":
    test_market_data() 