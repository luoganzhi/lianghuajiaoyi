import ccxt
import pandas as pd
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime
import requests
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import SIM_API_KEY

logger = logging.getLogger(__name__)

class MarketDataFetcher:
    def __init__(self, exchange_id: str, api_key: str = None, secret: str = None, proxy: str = None):
        """
        初始化市场数据获取器
        
        Args:
            exchange_id: 交易所ID（如'binance', 'okx'等）
            api_key: API密钥（可选）
            secret: API密钥对应的密钥（可选）
            proxy: 代理服务器地址（可选，如'http://127.0.0.1:7890'）
        """
        self.exchange_id = exchange_id
        
        # 配置代理
        exchange_config = {
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000
            }
        }
        
        # 添加代理配置
        if proxy:
            exchange_config['proxies'] = {
                'http': proxy,
                'https': proxy
            }
        
        # 创建交易所实例
        self.exchange = getattr(ccxt, exchange_id)(exchange_config)

        # 设置OKX特定的配置
        if exchange_id == 'okx':
            # 根据API密钥判断是否为模拟盘
            if api_key == SIM_API_KEY:
                self.exchange.sandbox = True  # 启用模拟盘
                print(f"🔧 OKX模拟盘已启用")
            else:
                self.exchange.sandbox = False  # 实盘模式
                print(f"🔧 OKX实盘模式")
            
            # 移除强制设置为现货模式，让CCXT根据symbol自动判断
            self.exchange.options['adjustForTimeDifference'] = True
            self.exchange.options['recvWindow'] = 60000

    def _retry_on_error(self, func, *args, max_retries=3, **kwargs):
        """
        错误重试装饰器
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            max_retries: 最大重试次数
            **kwargs: 函数关键字参数
        """
        for i in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i == max_retries - 1:
                    raise
                logger.warning(f"第{i+1}次尝试失败: {str(e)}，等待后重试...")
                time.sleep(2 ** i)  # 指数退避

    def get_ticker(self, symbol: str) -> Dict:
        """
        获取指定交易对的当前行情
        
        Args:
            symbol: 交易对符号（如'BTC/USDT'）
            
        Returns:
            包含行情信息的字典
        """
        try:
            # 直接使用OKX API获取ticker数据
            import requests
            
            # 构建请求参数
            params = {
                'instId': symbol
            }
            
            # 如果是模拟盘，添加模拟盘标识
            if self.exchange.sandbox:
                params['simulated'] = '1'
                logger.info(f"🔧 使用模拟盘参数获取ticker: {params}")
            else:
                logger.info(f"🔧 使用实盘参数获取ticker: {params}")
            
            # 发送请求（带重试机制）
            url = "https://www.okx.com/api/v5/market/ticker"
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, params=params, timeout=15)
                    
                    if response.status_code != 200:
                        raise Exception(f"API请求失败: {response.status_code}")
                    
                    data = response.json()
                    if data.get('code') != '0':
                        raise Exception(f"API返回错误: {data.get('msg', 'Unknown error')}")
                    
                    # 成功获取数据，跳出重试循环
                    break
                    
                except (requests.exceptions.RequestException, Exception) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Ticker数据获取失败 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        # 最后一次尝试失败，抛出异常
                        raise Exception(f"Ticker数据获取失败 (已重试{max_retries}次): {str(e)}")
            
            # 处理ticker数据
            ticker_data = data.get('data', [])
            if not ticker_data:
                raise Exception("无ticker数据")
            
            ticker = ticker_data[0]
            
            return {
                'symbol': ticker.get('instId', symbol),
                'last': float(ticker.get('last', 0)),
                'bid': float(ticker.get('bidPx', 0)),
                'ask': float(ticker.get('askPx', 0)),
                'high': float(ticker.get('high24h', 0)),
                'low': float(ticker.get('low24h', 0)),
                'volume': float(ticker.get('vol24h', 0)),
                'quoteVolume': float(ticker.get('volCcy24h', 0)),
                'timestamp': int(ticker.get('ts', 0))
            }
        except Exception as e:
            logger.error(f"获取行情数据失败: {str(e)}")
            if hasattr(e, 'args'):
                logger.error(f"详细错误信息: {e.args}")
            raise

    def get_ohlcv(self, symbol: str, timeframe: str = '1m', 
                  since: Optional[int] = None, limit: Optional[int] = None) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 交易对符号
            timeframe: K线周期（如'1m', '5m', '1h', '1d'等）
            since: 开始时间戳（毫秒）
            limit: 获取的K线数量
            
        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            # 直接使用OKX API获取K线数据
            import requests
            
            # 转换timeframe格式
            timeframe_map = {
                '1m': '1m',
                '5m': '5m', 
                '15m': '15m',
                '1h': '1H',
                '4h': '4H',
                '1d': '1D'
            }
            bar = timeframe_map.get(timeframe, '1m')
            
            # 构建请求参数
            params = {
                'instId': symbol,
                'bar': bar,
                'limit': str(limit) if limit else '100'
            }
            
            # 如果是模拟盘，添加模拟盘标识
            if self.exchange.sandbox:
                params['simulated'] = '1'
                logger.info(f"🔧 使用模拟盘参数获取K线: {params}")
            else:
                logger.info(f"🔧 使用实盘参数获取K线: {params}")
            
            # 发送请求（带重试机制）
            url = "https://www.okx.com/api/v5/market/candles"
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, params=params, timeout=15)
                    
                    if response.status_code != 200:
                        raise Exception(f"API请求失败: {response.status_code}")
                    
                    data = response.json()
                    if data.get('code') != '0':
                        raise Exception(f"API返回错误: {data.get('msg', 'Unknown error')}")
                    
                    # 成功获取数据，跳出重试循环
                    break
                    
                except (requests.exceptions.RequestException, Exception) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"K线数据获取失败 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                    else:
                        # 最后一次尝试失败，抛出异常
                        raise Exception(f"K线数据获取失败 (已重试{max_retries}次): {str(e)}")
            
            # 处理K线数据
            ohlcv_data = data.get('data', [])
            if not ohlcv_data:
                raise Exception("无K线数据")
            
            # 转换为DataFrame
            df_data = []
            for candle in ohlcv_data:
                # OKX K线数据格式: [timestamp, open, high, low, close, volume, currency_volume]
                df_data.append({
                    'timestamp': int(candle[0]),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            df = pd.DataFrame(df_data)
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Shanghai')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {str(e)}")
            if hasattr(e, 'args'):
                logger.error(f"详细错误信息: {e.args}")
            raise

    def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """
        获取订单簿数据
        
        Args:
            symbol: 交易对符号
            limit: 获取的订单数量
            
        Returns:
            包含订单簿数据的字典
        """
        try:
            order_book = self._retry_on_error(self.exchange.fetch_order_book, symbol, limit)
            return {
                # bids: 买单列表，每个元素为[价格, 数量]的数组，按价格从高到低排序
                # asks: 卖单列表，每个元素为[价格, 数量]的数组，按价格从低到高排序
                'bids': order_book['bids'],  # 买单列表
                'asks': order_book['asks'],  # 卖单列表
                'timestamp': order_book['timestamp']
            }
        except Exception as e:
            logger.error(f"获取订单簿数据失败: {str(e)}")
            if hasattr(e, 'args'):
                logger.error(f"详细错误信息: {e.args}")
            raise

    def get_trades(self, symbol: str, limit: int = 50) -> List[Dict]:
        """
        获取最近成交记录
        
        Args:
            symbol: 交易对符号
            limit: 获取的成交记录数量
            
        Returns:
            成交记录列表
        """
        try:
            trades = self._retry_on_error(self.exchange.fetch_trades, symbol, limit=limit)
            return [{
                'id': trade['id'],          # 交易ID，唯一标识符
                'timestamp': trade['timestamp'],  # 交易时间戳（毫秒）
                'price': trade['price'],    # 成交价格
                'amount': trade['amount'],  # 成交数量
                'side': trade['side'],      # 交易方向（buy/sell）
                'cost': trade['cost']       # 成交金额（price * amount）
            } for trade in trades]
        except Exception as e:
            logger.error(f"获取成交记录失败: {str(e)}")
            if hasattr(e, 'args'):
                logger.error(f"详细错误信息: {e.args}")
            raise

    def get_historical_ohlcv(self, symbol: str, timeframe: str,
                           start_date: datetime, end_date: datetime,
                           batch_size: int = 100) -> pd.DataFrame:
        """
        获取指定时间范围的所有历史K线数据
        OHLCV代表:
        - Open: 开盘价
        - High: 最高价  
        - Low: 最低价
        - Close: 收盘价
        - Volume: 交易量
        
        Args:
            symbol: 交易对符号
            timeframe: K线周期
            start_date: 开始时间
            end_date: 结束时间
            batch_size: 每次请求的数据量
            
        Returns:
            包含所有历史数据的DataFrame
        """
        all_data = []
        current_date = start_date
        
        # 计算预期的数据点数量
        time_delta = end_date - start_date
        expected_points = time_delta.total_seconds() / self._get_timeframe_seconds(timeframe)
        estimated_batches = int(expected_points / batch_size) + 1
        
        # 设置最大批次限制，防止无限循环
        max_batches = min(estimated_batches * 2, 50)  # 最多50批次或预估值的2倍
        
        logger.info(f"开始获取历史数据，预计需要 {estimated_batches} 批次，最大限制 {max_batches} 批次")
        batch_num = 0
        
        while current_date < end_date and batch_num < max_batches:
            try:
                batch_num += 1
                logger.info(f"正在获取第 {batch_num}/{max_batches} 批数据...")
                
                # 获取一批数据
                batch = self._retry_on_error(
                    self.exchange.fetch_ohlcv,
                    symbol,
                    timeframe,
                    int(current_date.timestamp() * 1000),
                    batch_size
                )
                
                if not batch:
                    logger.info("没有更多数据，停止获取")
                    break
                    
                # 转换为DataFrame
                df_batch = pd.DataFrame(
                    batch,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df_batch['timestamp'] = pd.to_datetime(df_batch['timestamp'], unit='ms')
                
                all_data.append(df_batch)
                
                # 更新下一批数据的开始时间
                last_timestamp = df_batch['timestamp'].iloc[-1]
                
                # 检查时间是否向前推进
                if last_timestamp <= current_date:
                    logger.info("时间没有向前推进，可能已到达数据边界")
                    break
                    
                current_date = last_timestamp
                
                # 添加延时以避免触发频率限制
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"获取历史数据失败: {str(e)}")
                if hasattr(e, 'args'):
                    logger.error(f"详细错误信息: {e.args}")
                raise
        
        if batch_num >= max_batches:
            logger.warning(f"达到最大批次限制 {max_batches}，可能数据获取不完整")
        
        if not all_data:
            return pd.DataFrame()
            
        # 合并所有数据
        df = pd.concat(all_data, ignore_index=True)
        
        # 去除重复数据并按时间排序
        df = df.drop_duplicates(subset=['timestamp'])
        df = df.sort_values('timestamp')
        
        # 只保留指定时间范围内的数据
        df = df[
            (df['timestamp'] >= pd.Timestamp(start_date)) &
            (df['timestamp'] <= pd.Timestamp(end_date))
        ]
        
        logger.info(f"成功获取 {len(df)} 条历史数据")
        return df

    def _get_timeframe_seconds(self, timeframe: str) -> int:
        """
        将时间周期转换为秒数
        
        Args:
            timeframe: 时间周期字符串（如'1m', '1h', '1d'）
            
        Returns:
            对应的秒数
        """
        unit = timeframe[-1]
        number = int(timeframe[:-1])
        
        if unit == 'm':
            return number * 60
        elif unit == 'h':
            return number * 3600
        elif unit == 'd':
            return number * 86400
        else:
            raise ValueError(f"不支持的时间周期单位: {unit}") 