import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from src.data.market_data import MarketDataFetcher
from src.data.data_processor import DataProcessor
from src.strategies.lstm_strategy import LSTMStrategy
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LSTMBacktester:
    def __init__(self,
                 exchange_id: str,
                 symbol: str,
                 timeframe: str,
                 start_date: str,
                 end_date: str,
                 sequence_length: int = 24,
                 prediction_length: int = 6,
                 initial_capital: float = 10000,
                 position_size: float = 1.0,
                 commission: float = 0.001,
                 model_path: str = 'models/lstm_backtest',
                 threshold: float = 0.02,
                 proxy: str = None,
                 use_cached_data: bool = True,
                 retrain_model: bool = False):
        """
        LSTM策略回测器
        
        Args:
            exchange_id: 交易所ID
            symbol: 交易对
            timeframe: 时间周期
            start_date: 回测开始日期 (YYYY-MM-DD)
            end_date: 回测结束日期 (YYYY-MM-DD)
            sequence_length: 序列长度
            prediction_length: 预测长度
            initial_capital: 初始资金
            position_size: 仓位大小（占总资金比例）
            commission: 手续费率
            model_path: 模型保存路径
            threshold: 交易信号阈值
            proxy: 代理服务器地址
            use_cached_data: 是否使用缓存的历史数据
            retrain_model: 是否重新训练模型
        """
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.commission = commission
        self.use_cached_data = use_cached_data
        self.retrain_model = retrain_model
        
        # 创建数据缓存目录
        self.data_cache_dir = Path('data/cache')
        self.data_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据获取器和处理器
        self.data_fetcher = MarketDataFetcher(exchange_id, proxy=proxy)
        self.data_processor = DataProcessor()
        
        # 初始化LSTM策略
        self.strategy = LSTMStrategy(
            sequence_length=sequence_length,
            prediction_length=prediction_length,
            model_path=model_path,
            threshold=threshold
        )
        
        # 回测结果
        self.results = {
            'trades': [],
            'equity_curve': [],
            'positions': []
        }
        
    def _get_cache_filename(self):
        """获取缓存文件名"""
        return self.data_cache_dir / f"{self.exchange_id}_{self.symbol}_{self.timeframe}_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.csv"
        
    def generate_mock_data(self):
        """生成模拟数据用于回测"""
        logger.info("生成模拟数据...")
        
        # 生成日期范围
        dates = pd.date_range(
            start=self.start_date,
            end=self.end_date,
            freq=self.timeframe
        )
        
        # 生成模拟价格数据（趋势+周期+噪声）
        t = np.linspace(0, 8*np.pi, len(dates))
        trend = 0.1 * t
        seasonal = 10 * np.sin(t)
        noise = np.random.normal(0, 1, len(dates))
        prices = trend + seasonal + noise + 100
        
        # 创建DataFrame
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 0.1, len(dates)),
            'high': prices + np.random.normal(0.5, 0.1, len(dates)),
            'low': prices + np.random.normal(-0.5, 0.1, len(dates)),
            'close': prices,
            'volume': np.random.randint(1000, 10000, len(dates))
        })
        
        # 处理数据
        self.data = self.data_processor.process_ohlcv(data)
        logger.info(f"生成了 {len(self.data)} 条模拟数据")
        
        return self.data
    
    def load_data(self):
        """加载历史数据"""
        logger.info("加载历史数据...")
        
        cache_file = self._get_cache_filename()
        
        if self.use_cached_data and cache_file.exists():
            logger.info("使用缓存的历史数据...")
            self.data = pd.read_csv(cache_file)
            self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
            return self.data
            
        try:
            # 使用新的方法获取历史数据
            data = self.data_fetcher.get_historical_ohlcv(
                self.symbol,
                self.timeframe,
                self.start_date,
                self.end_date
            )
            
            if len(data) > 0:
                # 处理数据
                self.data = self.data_processor.process_ohlcv(data)
                
                # 移除异常值
                price_columns = ['open', 'high', 'low', 'close']
                self.data = self.data_processor.remove_outliers(
                    self.data, 
                    columns=price_columns,
                    method='zscore',
                    threshold=3.0
                )
                
                # 处理缺失值
                self.data = self.data.dropna()
                
                # 保存到缓存
                self.data.to_csv(cache_file, index=False)
                logger.info(f"历史数据已缓存到 {cache_file}")
                
                logger.info(f"从交易所加载并处理了 {len(self.data)} 条历史数据")
                
                # 确保数据量足够
                min_data_points = self.strategy.sequence_length + self.strategy.prediction_length
                if len(self.data) < min_data_points:
                    raise ValueError(f"数据量不足，至少需要 {min_data_points} 条数据")
            else:
                raise Exception("未获取到历史数据")
            
        except Exception as e:
            logger.warning(f"无法从交易所获取数据: {str(e)}")
            logger.info("使用模拟数据进行回测...")
            self.data = self.generate_mock_data()
        
        return self.data
    
    def prepare_training_data(self):
        """准备训练数据（使用前80%的数据训练）"""
        if self.data is None or len(self.data) == 0:
            raise ValueError("请先加载数据")
            
        # 数据标准化
        feature_columns = [
            'close', 'returns', 'ma5', 'ma20', 'macd',
            'bb_upper', 'bb_lower', 'atr', 'volume_ratio'
        ]
        
        # 确保所有特征都存在
        missing_features = [col for col in feature_columns if col not in self.data.columns]
        if missing_features:
            raise ValueError(f"缺少必要的特征: {missing_features}")
            
        # 确保时间戳列是datetime类型
        if not isinstance(self.data['timestamp'].iloc[0], pd.Timestamp):
            self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
            
        # 处理缺失值
        self.data = self.data.dropna()
        
        # 划分训练集和测试集
        train_size = int(len(self.data) * 0.8)
        self.train_data = self.data[:train_size].copy()
        self.test_data = self.data[train_size:].copy()
        
        logger.info(f"训练数据大小: {len(self.train_data)}")
        logger.info(f"测试数据大小: {len(self.test_data)}")
        
        return self.train_data, self.test_data
    
    def run_backtest(self):
        """运行回测"""
        logger.info("开始回测...")
        
        # 加载数据
        self.load_data()
        
        # 划分训练集和测试集
        train_size = int(len(self.data) * 0.8)
        train_data = self.data[:train_size]
        test_data = self.data[train_size:]
        
        logger.info(f"训练数据大小: {len(train_data)}")
        logger.info(f"测试数据大小: {len(test_data)}")
        
        # 训练模型
        if self.retrain_model or not self.strategy.is_trained:
            logger.info("训练模型...")
            self.strategy.train(train_data, epochs=100, batch_size=32)
        
        # 生成交易信号
        logger.info("开始回测交易...")
        signals = self.strategy.generate_signals(test_data)
        
        # 初始化回测变量
        current_position = 0  # -1: 空仓, 0: 持仓, 1: 多仓
        entry_price = 0
        equity = self.initial_capital
        self.results['equity_curve'] = []
        self.results['trades'] = []
        self.results['positions'] = []
        
        # 遍历测试数据
        for i, (index, row) in enumerate(test_data.iterrows()):
            # 记录当前权益
            self.results['equity_curve'].append({
                'timestamp': index,
                'equity': equity
            })
            self.results['positions'].append(current_position)
            
            # 获取当前信号
            signal = signals[i]
            
            # 根据信号交易
            if signal != 0 and signal != current_position:
                # 平仓
                if current_position != 0:
                    profit = (row['close'] - entry_price) * current_position
                    equity += profit
                    
                    self.results['trades'].append({
                        'entry_time': entry_time,
                        'exit_time': index,
                        'entry_price': entry_price,
                        'exit_price': row['close'],
                        'position': current_position,
                        'profit': profit
                    })
                    
                    current_position = 0
                    
                # 开仓
                if signal != 0:
                    current_position = signal
                    entry_price = row['close']
                    entry_time = index
        
        # 最后一个交易日平仓
        if current_position != 0:
            last_price = test_data.iloc[-1]['close']
            profit = (last_price - entry_price) * current_position
            equity += profit
            
            self.results['trades'].append({
                'entry_time': entry_time,
                'exit_time': test_data.index[-1],
                'entry_price': entry_price,
                'exit_price': last_price,
                'position': current_position,
                'profit': profit
            })
            
        # 计算回测指标
        self.calculate_metrics()
        
        return self.results
    
    def calculate_metrics(self):
        """计算回测指标"""
        try:
            # 将列表转换为DataFrame
            equity_curve = pd.DataFrame(self.results['equity_curve'])
            trades = pd.DataFrame(self.results['trades'])
            
            if len(equity_curve) > 0:
                # 将时间戳转换为datetime对象
                equity_curve['timestamp'] = pd.to_datetime(equity_curve['timestamp'], unit='s')
                
                # 计算收益率
                total_return = (equity_curve['equity'].iloc[-1] - self.initial_capital) / self.initial_capital
                
                # 计算年化收益率
                days = (equity_curve['timestamp'].max() - equity_curve['timestamp'].min()).days
                if days > 0:
                    annual_return = (1 + total_return) ** (365 / days) - 1
                else:
                    annual_return = 0
                
                # 计算最大回撤
                equity_values = equity_curve['equity']
                cummax = equity_values.cummax()
                drawdown = (cummax - equity_values) / cummax
                max_drawdown = drawdown.max()
                
                # 计算夏普比率
                daily_returns = equity_values.pct_change().dropna()
                if len(daily_returns) > 0 and daily_returns.std() != 0:
                    sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
                else:
                    sharpe_ratio = 0
                
                # 计算交易统计
                total_trades = len(trades)
                if total_trades > 0:
                    # 计算盈利交易
                    profitable_trades = trades[trades['profit'] > 0].dropna()
                    winning_trades = len(profitable_trades)
                    win_rate = winning_trades / total_trades
                else:
                    winning_trades = 0
                    win_rate = 0
                
                # 打印结果
                logger.info("\n回测结果:")
                logger.info(f"总收益率: {total_return:.2%}")
                logger.info(f"年化收益率: {annual_return:.2%}")
                logger.info(f"最大回撤: {max_drawdown:.2%}")
                logger.info(f"夏普比率: {sharpe_ratio:.2f}")
                logger.info(f"总交易次数: {total_trades}")
                logger.info(f"胜率: {win_rate:.2%}")
                
                # 保存回测结果
                self.results['metrics'] = {
                    'total_return': total_return,
                    'annual_return': annual_return,
                    'max_drawdown': max_drawdown,
                    'sharpe_ratio': sharpe_ratio,
                    'total_trades': total_trades,
                    'win_rate': win_rate
                }
                
                # 绘制回测结果
                self.plot_results()
            else:
                logger.warning("没有足够的数据来计算指标")
                
        except Exception as e:
            logger.error(f"计算指标时出错: {str(e)}")
            raise
            
    def plot_results(self):
        """绘制回测结果图表"""
        try:
            # 将列表转换为DataFrame
            equity_curve = pd.DataFrame(self.results['equity_curve'])
            
            if len(equity_curve) > 0:
                # 创建子图
                fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8))
                
                # 绘制资金曲线
                ax1.plot(pd.to_datetime(equity_curve['timestamp']), equity_curve['equity'])
                ax1.set_title('投资组合价值')
                ax1.grid(True)
                
                # 绘制持仓
                ax2.plot(pd.to_datetime(equity_curve['timestamp']), self.results['positions'])
                ax2.set_title('持仓')
                ax2.grid(True)
                
                # 绘制回撤
                equity_values = equity_curve['equity']
                cummax = equity_values.cummax()
                drawdown = (cummax - equity_values) / cummax
                ax3.fill_between(pd.to_datetime(equity_curve['timestamp']), drawdown, color='red', alpha=0.3)
                ax3.set_title('回撤')
                ax3.grid(True)
                
                # 调整布局
                plt.tight_layout()
                plt.savefig('backtest_results.png')
                logger.info("\n回测图表已保存为 'backtest_results.png'")
                
            else:
                logger.warning("没有足够的数据来绘制图表")
                
        except Exception as e:
            logger.error(f"绘制图表时出错: {str(e)}")
            raise

def main():
    # 回测配置
    config = {
        'exchange_id': 'okx',
        'symbol': 'BTC/USDT',
        'timeframe': '4h',          # 改为4小时级别
        'start_date': '2023-10-01', # 缩短回测时间范围
        'end_date': '2023-12-31',
        'sequence_length': 12,      # 减少序列长度
        'prediction_length': 3,     # 减少预测长度
        'initial_capital': 10000,
        'position_size': 1.0,
        'commission': 0.001,
        'model_path': 'models/lstm_backtest',
        'threshold': 0.015,         # 调整阈值
        'proxy': 'http://127.0.0.1:7890',
        'use_cached_data': True,
        'retrain_model': True
    }
    
    try:
        # 创建模型目录
        Path(config['model_path']).mkdir(parents=True, exist_ok=True)
        
        # 创建回测器
        backtester = LSTMBacktester(**config)
        
        # 运行回测
        logger.info("开始运行回测...")
        results = backtester.run_backtest()
        
        # 计算和显示指标
        metrics = backtester.calculate_metrics()
        if metrics:
            logger.info("\n回测结果:")
            for key, value in metrics.items():
                logger.info(f"{key}: {value}")
            
            # 绘制图表
            backtester.plot_results()
            logger.info("\n回测图表已保存为 'backtest_results.png'")
        else:
            logger.warning("回测未产生有效结果")
        
    except Exception as e:
        logger.error(f"回测过程中出现错误: {str(e)}")
        raise

if __name__ == '__main__':
    main() 