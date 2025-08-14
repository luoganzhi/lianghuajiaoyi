import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.market_data import MarketDataFetcher
from src.data.data_processor import DataProcessor
import pandas as pd
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_data_processor():
    try:
        # 初始化数据获取器和数据处理器
        exchange_id = 'okx'
        proxy = 'http://127.0.0.1:7890'  # 根据实际情况修改代理地址
        
        fetcher = MarketDataFetcher(
            exchange_id=exchange_id,
            proxy=proxy
        )
        
        processor = DataProcessor()
        
        # 获取测试数据
        symbol = 'BTC-USDT'
        timeframe = '1h'  # 1小时K线
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)  # 获取7天的数据
        
        logger.info(f"获取{symbol}的{timeframe}K线数据")
        ohlcv = fetcher.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=int(start_time.timestamp() * 1000)
        )
        
        # 测试1: 处理K线数据，添加技术指标
        logger.info("\n测试1: 处理K线数据，添加技术指标")
        processed_data = processor.process_ohlcv(ohlcv)
        logger.info(f"处理后的数据包含以下列: {processed_data.columns.tolist()}")
        logger.info("\n最近5条数据的部分指标:")
        display_columns = ['timestamp', 'close', 'returns', 'ma5', 'macd', 'atr', 'volume_ratio']
        logger.info(processed_data[display_columns].tail())
        
        # 测试2: 标准化数据
        logger.info("\n测试2: 标准化数据")
        columns_to_normalize = ['close', 'volume', 'returns']
        normalized_data = processor.normalize_data(processed_data, columns_to_normalize)
        logger.info("\n标准化后的数据:")
        logger.info(normalized_data[columns_to_normalize].tail())
        
        # 测试3: 移除异常值
        logger.info("\n测试3: 移除异常值")
        columns_to_check = ['returns', 'volume']
        cleaned_data = processor.remove_outliers(normalized_data, columns_to_check, method='zscore', threshold=3.0)
        logger.info(f"原始数据行数: {len(normalized_data)}")
        logger.info(f"清理后数据行数: {len(cleaned_data)}")
        
        logger.info("\n所有测试完成！数据处理模块功能正常。")
        return True
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        if hasattr(e, 'args'):
            logger.error(f"详细错误信息: {e.args}")
        return False

if __name__ == "__main__":
    test_data_processor() 