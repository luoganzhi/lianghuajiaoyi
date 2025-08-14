import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.market_data import MarketDataFetcher
from src.data.data_processor import DataProcessor
from src.strategies.simple_ma_strategy import SimpleMAStrategy
from src.backtest.simple_backtester import SimpleBacktester
from src.visualization.backtest_visualizer import BacktestVisualizer
import pandas as pd
from datetime import datetime, timedelta
import logging
import traceback
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_visualization():
    try:
        print("到达：准备获取行情数据")
        exchange_id = 'okx'
        proxy = 'http://127.0.0.1:7890'
        fetcher = MarketDataFetcher(exchange_id=exchange_id, proxy=proxy)
        symbol = 'BTC-USDT'
        timeframe = '1h'
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        logger.info(f"获取{symbol}的{timeframe}K线数据")
        ohlcv = fetcher.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=int(start_time.timestamp() * 1000)
        )
        print("到达：获取K线数据，ohlcv前5行：")
        print(ohlcv.head())
        
        processor = DataProcessor()
        processed_data = processor.process_ohlcv(ohlcv)
        print("到达：数据处理，processed_data前5行：")
        print(processed_data.head())
        
        strategy = SimpleMAStrategy(short_window=5, long_window=20)
        signals = strategy.generate_signals(processed_data)
        print("到达：生成信号，signals前5行：")
        print(signals.head())
        
        backtester = SimpleBacktester(initial_cash=100000, fee=0.001)
        result = backtester.run_backtest(processed_data, signals)
        print("到达：回测，result内容：")
        print(result)
        
        visualizer = BacktestVisualizer()
        print("到达：准备可视化 plot_all")
        visualizer.plot_all(result)
        print("plot_all已执行")
        
        logger.info("可视化模块测试完成！")
        return True
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        if hasattr(e, 'args'):
            logger.error(f"详细错误信息: {e.args}")
        traceback.print_exc()
        return False

def plot_monthly_returns(self, strategy_returns: pd.Series, title: str = "Monthly Returns"):
    # 确保索引是datetime类型
    if not isinstance(strategy_returns.index, pd.DatetimeIndex):
        strategy_returns.index = pd.to_datetime(strategy_returns.index)
    # 数据有效性检查
    if len(strategy_returns) == 0 or strategy_returns.abs().sum() == 0:
        print("无有效策略收益数据，跳过月度收益图。")
        return
    monthly_returns = strategy_returns.resample('ME').apply(
        lambda x: (1 + x).prod() - 1
    )
    monthly_returns_matrix = monthly_returns.to_frame()
    monthly_returns_matrix['year'] = monthly_returns_matrix.index.year
    monthly_returns_matrix['month'] = monthly_returns_matrix.index.month
    # 这里修正
    value_col = monthly_returns_matrix.columns[0]
    monthly_returns_pivot = monthly_returns_matrix.pivot(
        index='year', columns='month', values=value_col
    )
    plt.figure(figsize=(12, 8))
    sns.heatmap(monthly_returns_pivot, annot=True, fmt='.2%', cmap='RdYlGn',
               center=0, cbar_kws={'label': 'Return'})
    plt.title(title)
    plt.xlabel('Month')
    plt.ylabel('Year')
    plt.show()

if __name__ == "__main__":
    test_visualization() 