import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from src.data.market_data import MarketDataFetcher
from src.data.data_processor import DataProcessor
from src.strategies.lstm_strategy import LSTMStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveLSTMTrader:
    def __init__(self, 
                 exchange_id: str,
                 symbol: str,
                 timeframe: str = '1h',
                 sequence_length: int = 24,
                 prediction_length: int = 6,
                 model_path: str = 'models/lstm_live',
                 threshold: float = 0.02,
                 api_key: str = None,
                 secret: str = None,
                 proxy: str = None):
        """
        实时LSTM交易策略运行器
        
        Args:
            exchange_id: 交易所ID
            symbol: 交易对
            timeframe: 时间周期
            sequence_length: 序列长度
            prediction_length: 预测长度
            model_path: 模型保存路径
            threshold: 交易信号阈值
            api_key: API密钥
            secret: API密钥对应的密钥
            proxy: 代理服务器地址
        """
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.timeframe = timeframe
        
        # 初始化数据获取器和处理器
        self.data_fetcher = MarketDataFetcher(exchange_id, api_key, secret, proxy)
        self.data_processor = DataProcessor()
        
        # 初始化LSTM策略
        self.strategy = LSTMStrategy(
            sequence_length=sequence_length,
            prediction_length=prediction_length,
            model_path=model_path,
            threshold=threshold
        )
        
        # 存储最近的数据
        self.recent_data = None
        
    def initialize_data(self):
        """初始化历史数据"""
        # 获取足够的历史数据用于模型训练
        initial_data = self.data_fetcher.get_ohlcv(
            self.symbol,
            self.timeframe,
            limit=1000  # 获取1000根K线
        )
        
        # 处理数据
        self.recent_data = self.data_processor.process_ohlcv(initial_data)
        logger.info(f"获取到{len(self.recent_data)}条历史数据")
        
        return self.recent_data
    
    def train_initial_model(self):
        """训练初始模型"""
        if self.recent_data is None:
            self.initialize_data()
            
        logger.info("开始训练初始模型...")
        self.strategy.train(self.recent_data, epochs=50, batch_size=32)
        logger.info("初始模型训练完成")
    
    def update_data(self):
        """更新最新数据"""
        try:
            # 获取最新的K线数据
            new_data = self.data_fetcher.get_ohlcv(
                self.symbol,
                self.timeframe,
                limit=2  # 获取最新的2根K线
            )
            
            # 处理新数据
            new_data = self.data_processor.process_ohlcv(new_data)
            
            # 更新数据集
            self.recent_data = pd.concat([
                self.recent_data[:-1],  # 移除最后一根可能不完整的K线
                new_data
            ]).drop_duplicates(subset=['timestamp']).sort_values('timestamp')
            
            # 保持固定长度
            self.recent_data = self.recent_data.tail(1000)
            
            return True
        except Exception as e:
            logger.error(f"更新数据失败: {str(e)}")
            return False
    
    def run(self, update_interval: int = 60):
        """
        运行实时交易策略
        
        Args:
            update_interval: 更新间隔（秒）
        """
        # 初始化
        if not self.strategy.is_trained:
            self.train_initial_model()
        
        logger.info(f"开始运行实时LSTM策略 - {self.symbol}")
        
        while True:
            try:
                # 更新数据
                if self.update_data():
                    # 获取最新的数据窗口
                    latest_window = self.recent_data.tail(self.strategy.sequence_length)
                    
                    # 生成交易信号
                    signal = self.strategy.generate_signal(latest_window)
                    
                    # 获取最新价格
                    current_price = latest_window.iloc[-1]['close']
                    
                    # 输出预测结果
                    logger.info(f"时间: {datetime.now()}")
                    logger.info(f"当前价格: {current_price}")
                    logger.info(f"交易信号: {signal}")
                    
                    # 每24小时更新一次模型
                    if datetime.now().hour == 0 and datetime.now().minute < 5:
                        logger.info("开始更新模型...")
                        self.strategy.train(self.recent_data, epochs=10, batch_size=32)
                        logger.info("模型更新完成")
                
                # 等待下一次更新
                time.sleep(update_interval)
                
            except KeyboardInterrupt:
                logger.info("策略运行结束")
                break
            except Exception as e:
                logger.error(f"策略运行出错: {str(e)}")
                time.sleep(update_interval)

def main():
    # 配置参数
    config = {
        'exchange_id': 'binance',  # 或 'okx'
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'sequence_length': 24,
        'prediction_length': 6,
        'model_path': 'models/lstm_live',
        'threshold': 0.02,
        'proxy': 'http://127.0.0.1:7890',  # 根据需要配置
        'api_key': None,  # 根据需要配置
        'secret': None,   # 根据需要配置
    }
    
    # 创建并运行策略
    try:
        logger.info("开始测试LSTM实时交易策略...")
        
        # 创建交易实例
        trader = LiveLSTMTrader(**config)
        
        # 测试数据初始化
        logger.info("测试数据初始化...")
        initial_data = trader.initialize_data()
        logger.info(f"初始数据形状: {initial_data.shape}")
        
        # 测试模型训练
        logger.info("测试模型训练...")
        trader.train_initial_model()
        
        # 测试实时更新
        logger.info("测试数据更新...")
        update_success = trader.update_data()
        logger.info(f"数据更新状态: {'成功' if update_success else '失败'}")
        
        # 测试信号生成
        logger.info("测试信号生成...")
        latest_window = trader.recent_data.tail(trader.strategy.sequence_length)
        signal = trader.strategy.generate_signal(latest_window)
        logger.info(f"生成的交易信号: {signal}")
        
        # 运行实时策略（测试5分钟）
        logger.info("测试实时运行（5分钟）...")
        trader.run(update_interval=60)
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        raise

if __name__ == '__main__':
    main() 