import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from src.strategies.mean_reversion_strategy import MeanReversionStrategy
from src.strategies.ma_curve_strategy import MACurveStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.composite_strategy import CompositeStrategy
from src.strategies.trend_following_strategy import TrendFollowingStrategy
from src.strategies.grid_trading_strategy import GridTradingStrategy
from src.strategies.profit_filter_strategy import ProfitFilterStrategy
from src.strategies.daily_trading_strategy import DailyTradingStrategy
from src.data.market_data import MarketDataFetcher
from src.data.data_processor import DataProcessor
from src.strategies.simple_ma_strategy import SimpleMAStrategy
from src.backtest.simple_backtester import SimpleBacktester
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_trade_details(trades):
    """打印详细的交易记录"""
    if not trades:
        logger.info("没有交易记录")
        return
    
    logger.info(f"\n=== 详细交易记录 (共{len(trades)}笔) ===")
    
    # 按时间排序
    sorted_trades = sorted(trades, key=lambda x: x['timestamp'])
    
    total_pnl = 0
    winning_trades = 0
    losing_trades = 0
    
    for i, trade in enumerate(sorted_trades):
        timestamp = trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        trade_type = trade['type']
        price = trade['price']
        size = trade['size']
        value = trade['value']
        fee = trade['fee']
        equity = trade['equity']
        
        print(f"\n交易 #{i+1}:")
        print(f"  时间: {timestamp}")
        print(f"  类型: {trade_type.upper()}")
        print(f"  价格: {price:.2f}")
        print(f"  数量: {size:.6f}")
        print(f"  价值: {value:.2f}")
        print(f"  手续费: {fee:.2f}")
        print(f"  账户权益: {equity:.2f}")
        
        # 如果是卖出交易，显示盈亏信息
        if trade_type == 'sell' and 'pnl' in trade:
            pnl = trade['pnl']
            pnl_pct = trade['pnl_pct']
            buy_price = trade.get('buy_price', 'N/A')
            buy_time = trade.get('buy_timestamp', 'N/A')
            if isinstance(buy_time, pd.Timestamp):
                buy_time = buy_time.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"  买入价格: {buy_price}")
            print(f"  买入时间: {buy_time}")
            print(f"  盈亏: {pnl:.2f} ({pnl_pct:+.2f}%)")
            
            total_pnl += pnl
            if pnl > 0:
                winning_trades += 1
            elif pnl < 0:
                losing_trades += 1
    
    # 打印交易统计
    logger.info(f"\n=== 交易统计 ===")
    logger.info(f"总交易次数: {len(trades)}")
    logger.info(f"总盈亏: {total_pnl:.2f}")
    logger.info(f"盈利交易: {winning_trades}次")
    logger.info(f"亏损交易: {losing_trades}次")
    
    # 计算并显示盈利率
    if winning_trades + losing_trades > 0:
        win_rate = winning_trades / (winning_trades + losing_trades) * 100
        logger.info(f"胜率: {win_rate:.1f}%")
        
        # 计算平均盈亏
        if winning_trades > 0:
            avg_profit = sum(t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0) / winning_trades
            logger.info(f"平均盈利: {avg_profit:.2f}")
        if losing_trades > 0:
            avg_loss = sum(abs(t.get('pnl', 0)) for t in trades if t.get('pnl', 0) < 0) / losing_trades
            logger.info(f"平均亏损: {avg_loss:.2f}")
        
        # 计算盈亏比
        if losing_trades > 0 and winning_trades > 0:
            profit_loss_ratio = avg_profit / avg_loss if 'avg_profit' in locals() and 'avg_loss' in locals() else 0
            logger.info(f"盈亏比: {profit_loss_ratio:.2f}")
        
        # 计算总盈利率（相对于初始资金）
        if trades and 'equity' in trades[0]:
            initial_equity = trades[0]['equity'] + trades[0].get('pnl', 0)  # 第一笔交易前的权益
            if initial_equity > 0:
                total_return_rate = (total_pnl / initial_equity) * 100
                logger.info(f"总盈利率: {total_return_rate:.2f}%")

def get_historical_data(fetcher, symbol, timeframe, days):
    """分页获取历史数据"""
    all_data = []
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    current_time = end_time
    
    while current_time > start_time:
        try:
            # 获取一批数据
            batch_data = fetcher.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=int((current_time - timedelta(days=5)).timestamp() * 1000),
                limit=100
            )
            
            if not batch_data or len(batch_data) == 0:
                break
                
            all_data.extend(batch_data)
            
            # 更新时间到最早的数据时间
            if batch_data and len(batch_data) > 0:
                earliest_time = pd.to_datetime(batch_data[0]['timestamp'], unit='ms')
                current_time = earliest_time
                
                logger.info(f"已获取 {len(all_data)} 条数据，当前时间: {current_time}")
            else:
                break
            
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            break
    
    # 去重并按时间排序
    if all_data:
        df = pd.DataFrame(all_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        # 过滤时间范围
        df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
        
        return df.to_dict('records')
    else:
        return []

def get_full_historical_data(fetcher, symbol, timeframe, days):
    """获取完整的历史数据，支持分页"""
    all_data = []
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    logger.info(f"开始获取 {days} 天的历史数据...")
    logger.info(f"目标时间范围: {start_time} 到 {end_time}")
    
    # 从最新数据开始，逐步向前获取
    current_end = end_time
    batch_count = 0
    
    while current_end > start_time and batch_count < 20:  # 限制最大批次防止无限循环
        try:
            batch_count += 1
            logger.info(f"第 {batch_count} 批次获取数据...")
            
            # 计算本次请求的开始时间（向前7天，确保有足够重叠）
            batch_start = current_end - timedelta(days=7)
            
            # 获取一批数据
            batch_df = fetcher.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=int(batch_start.timestamp() * 1000),
                limit=100
            )
            
            # 检查数据是否为空
            if batch_df.empty:
                logger.info("没有更多数据，停止获取")
                break
            
            # 转换为字典列表并添加到总数据中
            batch_data = batch_df.to_dict('records')
            all_data.extend(batch_data)
            
            # 更新时间到最早的数据时间
            if len(batch_data) > 0:
                earliest_time = batch_df.index.min()
                # 确保earliest_time是datetime对象
                if isinstance(earliest_time, (int, float)):
                    earliest_time = pd.to_datetime(earliest_time, unit='ms')
                current_end = earliest_time
                
                logger.info(f"已获取 {len(all_data)} 条数据，当前最早时间: {earliest_time}")
                
                # 如果已经获取到足够早的数据，停止
                if earliest_time <= start_time:
                    logger.info("已获取到目标时间范围的数据")
                    break
                    
                # 如果时间没有向前推进，说明没有更多历史数据
                if batch_count > 1 and len(batch_data) < 100:
                    logger.info("数据量不足100条，可能已到达历史数据边界")
                    break
            else:
                logger.info("批次数据为空，停止获取")
                break
                
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            break
    
    # 处理数据
    if all_data and len(all_data) > 0:
        try:
            df = pd.DataFrame(all_data)
            # 确保timestamp列是datetime类型
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # 去重并按时间排序
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
            
            # 过滤到目标时间范围
            df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
            
            logger.info(f"最终获取到 {len(df)} 条数据")
            if len(df) > 0:
                logger.info(f"实际时间范围: {df['timestamp'].min()} 到 {df['timestamp'].max()}")
                actual_days = (df['timestamp'].max() - df['timestamp'].min()).days
                logger.info(f"实际覆盖天数: {actual_days} 天")
            
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"处理数据失败: {e}")
            return []
    else:
        logger.warning("没有获取到任何数据")
        return []

def compare_backtest_periods():
    """对比不同时间周期的回测结果"""
    try:
        exchange_id = 'okx'
        proxy = 'http://127.0.0.1:7890'
        fetcher = MarketDataFetcher(exchange_id=exchange_id, proxy=proxy)
        symbol = 'BTC-USDT'
        timeframe = '1h'
        end_time = datetime.now()
        
        periods = [7, 30]
        
        for days in periods:
            logger.info(f"\n=== 测试 {days} 天回测 ===")
            
            # 获取数据
            start_time = end_time - timedelta(days=days)
            ohlcv = fetcher.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=int(start_time.timestamp() * 1000)
            )
            
            # 数据处理
            processor = DataProcessor()
            processed_data = processor.process_ohlcv(ohlcv)
            logger.info(f"获取到{len(processed_data)}条K线数据")
            logger.info(f"数据时间范围: {processed_data.index[0]} 到 {processed_data.index[-1]}")
            
            # 策略信号生成
            strategy = MACurveStrategy(ma_window=20, slope_lookback=3, slope_threshold=0.0, confirm_window=1)
            signals = strategy.generate_signals(processed_data)
            
            # 检查信号数量
            signal_count = len(signals[signals['signal'] != 0])
            logger.info(f"生成信号数量: {signal_count}")
            
            # 显示前几个信号的时间
            if signal_count > 0:
                signal_times = signals[signals['signal'] != 0].index[:5]
                logger.info(f"前5个信号时间: {list(signal_times)}")
            
            # 回测
            backtester = SimpleBacktester(initial_cash=100000, fee=0.001)
            result = backtester.run_backtest(processed_data, signals)
            
            logger.info(f"总收益率: {result['total_return']*100:.2f}%")
            logger.info(f"交易次数: {len(result['trades'])}")
            
        # 解释结果
        logger.info(f"\n=== 分析结果 ===")
        logger.info("为什么30天回测交易次数反而更少？")
        logger.info("1. 交易所API限制：单次请求最多返回100条K线数据")
        logger.info("2. 7天回测：获取最近7天的数据（2025-08-05到2025-08-09）")
        logger.info("3. 30天回测：获取30天前的数据（2025-07-13到2025-07-17）")
        logger.info("4. 市场波动性：最近7天的市场波动更大，产生更多交易信号")
        logger.info("5. 策略敏感性：MA策略在不同市场条件下表现不同")
            
        return True
    except Exception as e:
        logger.error(f"对比测试失败: {e}")
        return False

def test_backtest():
    try:
        # 获取行情数据
        exchange_id = 'okx'
        proxy = 'http://127.0.0.1:7890'
        fetcher = MarketDataFetcher(exchange_id=exchange_id, proxy=proxy)
        symbol = 'BTC-USDT'
        timeframe = '1h'  # 改为1小时K线
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)  # 改为7天数据
        logger.info(f"获取{symbol}的{timeframe}K线数据")
        ohlcv = fetcher.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=int(start_time.timestamp() * 1000)
        )
        # 数据处理
        processor = DataProcessor()
        processed_data = processor.process_ohlcv(ohlcv)
        logger.info(f"获取到{len(processed_data)}条K线数据")
        
        # 策略信号生成
        # strategy = SimpleMAStrategy(short_window=5, long_window=20)
        # strategy = MeanReversionStrategy(window=20, num_std=2)
        strategy = MACurveStrategy(ma_window=20, slope_lookback=3, slope_threshold=0.0, confirm_window=1)  # 调整参数
        signals = strategy.generate_signals(processed_data)
        
        # 检查信号数量
        signal_count = len(signals[signals['signal'] != 0])
        logger.info(f"生成信号数量: {signal_count}")
        
        # 回测
        backtester = SimpleBacktester(initial_cash=100000, fee=0.001)
        result = backtester.run_backtest(processed_data, signals)
        logger.info(f"总收益率: {result['total_return']*100:.2f}%")
        logger.info(f"最大回撤: {result['max_drawdown']*100:.2f}%")
        logger.info(f"夏普比率: {result['sharpe']:.2f}")
        logger.info(f"策略评分: {result['score']:.2f} / 100  (构成: {result['score_components']})")
        logger.info("资金曲线最后5行:")
        print(result['equity_curve'].tail())
        
        # 打印详细交易记录
        print_trade_details(result['trades'])
        
        logger.info("\n回测模块测试完成！")
        return True
    except Exception as e:
        logger.error(f"回测失败: {e}")
        return False

def test_30_days_backtest_quick():
    """快速测试30天回测（使用日线数据）"""
    try:
        exchange_id = 'okx'
        proxy = 'http://127.0.0.1:7890'
        fetcher = MarketDataFetcher(exchange_id=exchange_id, proxy=proxy)
        symbol = 'BTC-USDT'
        timeframe = '1d'  # 使用日线数据，快速获取
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        logger.info(f"开始快速30天回测...")
        logger.info(f"时间范围: {start_time} 到 {end_time}")
        logger.info(f"使用 {timeframe} K线数据")
        
        # 直接使用单次请求获取数据
        ohlcv_df = fetcher.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=int(start_time.timestamp() * 1000),
            limit=100
        )
        
        if ohlcv_df.empty:
            logger.error("无法获取历史数据")
            return False
        
        logger.info(f"成功获取 {len(ohlcv_df)} 条历史数据")
        logger.info(f"数据时间范围: {ohlcv_df.index.min()} 到 {ohlcv_df.index.max()}")
        
        # 数据处理
        processor = DataProcessor()
        processed_data = processor.process_ohlcv(ohlcv_df)
        logger.info(f"处理后的数据: {len(processed_data)} 条")
        
        # 策略信号生成 - 调整参数以适应日线数据
        strategy = MACurveStrategy(ma_window=5, slope_lookback=2, slope_threshold=0.0, confirm_window=1)
        signals = strategy.generate_signals(processed_data)
        
        # 检查信号数量
        signal_count = len(signals[signals['signal'] != 0])
        logger.info(f"生成信号数量: {signal_count}")
        
        # 回测
        backtester = SimpleBacktester(initial_cash=100000, fee=0.001)
        result = backtester.run_backtest(processed_data, signals)
        
        logger.info(f"总收益率: {result['total_return']*100:.2f}%")
        logger.info(f"最大回撤: {result['max_drawdown']*100:.2f}%")
        logger.info(f"夏普比率: {result['sharpe']:.2f}")
        logger.info(f"交易次数: {len(result['trades'])}")
        
        # 打印详细交易记录
        print_trade_details(result['trades'])
        
        return True
    except Exception as e:
        logger.error(f"快速30天回测失败: {e}")
        return False

def test_30_days_backtest():
    """测试真正的30天回测"""
    try:
        exchange_id = 'okx'
        proxy = 'http://127.0.0.1:7890'
        fetcher = MarketDataFetcher(exchange_id=exchange_id, proxy=proxy)
        symbol = 'BTC-USDT'
        timeframe = '4h'  # 使用4小时K线，减少数据量
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        logger.info(f"开始获取30天历史数据...")
        logger.info(f"时间范围: {start_time} 到 {end_time}")
        logger.info(f"使用 {timeframe} K线数据")
        
        # 使用专门的历史数据获取方法
        ohlcv_df = fetcher.get_historical_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_time,
            end_date=end_time,
            batch_size=100
        )
        
        if ohlcv_df.empty:
            logger.error("无法获取历史数据")
            return False
        
        logger.info(f"成功获取 {len(ohlcv_df)} 条历史数据")
        logger.info(f"数据时间范围: {ohlcv_df['timestamp'].min()} 到 {ohlcv_df['timestamp'].max()}")
        
        # 数据处理
        processor = DataProcessor()
        processed_data = processor.process_ohlcv(ohlcv_df)
        logger.info(f"处理后的数据: {len(processed_data)} 条")
        
        # 策略信号生成 - 调整参数以适应4小时K线
        strategy = MACurveStrategy(ma_window=10, slope_lookback=2, slope_threshold=0.0, confirm_window=1)
        signals = strategy.generate_signals(processed_data)
        
        # 检查信号数量
        signal_count = len(signals[signals['signal'] != 0])
        logger.info(f"生成信号数量: {signal_count}")
        
        # 回测
        backtester = SimpleBacktester(initial_cash=100000, fee=0.001)
        result = backtester.run_backtest(processed_data, signals)
        
        logger.info(f"总收益率: {result['total_return']*100:.2f}%")
        logger.info(f"最大回撤: {result['max_drawdown']*100:.2f}%")
        logger.info(f"夏普比率: {result['sharpe']:.2f}")
        logger.info(f"交易次数: {len(result['trades'])}")
        
        # 打印详细交易记录
        print_trade_details(result['trades'])
        
        return True
    except Exception as e:
        logger.error(f"30天回测失败: {e}")
        return False

def flexible_backtest(days=30, timeframe='1d', strategy_params=None, strategy_type='macurve'):
    """
    灵活的回测函数，支持自定义时间范围
    
    Args:
        days (int): 回测天数，默认30天
        timeframe (str): K线周期，默认'1d'（日线）
        strategy_params (dict): 策略参数字典
        strategy_type (str): 策略类型，'macurve', 'simple_ma', 'mean_reversion'
    """
    try:
        exchange_id = 'okx'
        proxy = 'http://127.0.0.1:7890'
        fetcher = MarketDataFetcher(exchange_id=exchange_id, proxy=proxy)
        symbol = 'BTC-USDT'
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        logger.info(f"\n=== 开始 {days} 天回测 ===")
        logger.info(f"时间范围: {start_time.strftime('%Y-%m-%d')} 到 {end_time.strftime('%Y-%m-%d')}")
        logger.info(f"使用 {timeframe} K线数据")
        logger.info(f"策略类型: {strategy_type}")
        
        # 获取数据
        if timeframe == '1d' and days <= 100:
            # 日线数据且天数较少，直接获取
            ohlcv_df = fetcher.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=int(start_time.timestamp() * 1000),
                limit=100
            )
        else:
            # 其他情况使用历史数据获取方法
            ohlcv_df = fetcher.get_historical_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_time,
                end_date=end_time,
                batch_size=100
            )
        
        if ohlcv_df.empty:
            logger.error("无法获取历史数据")
            return False
        
        logger.info(f"成功获取 {len(ohlcv_df)} 条历史数据")
        if hasattr(ohlcv_df.index, 'min'):
            logger.info(f"数据时间范围: {ohlcv_df.index.min()} 到 {ohlcv_df.index.max()}")
        
        # 数据处理
        processor = DataProcessor()
        processed_data = processor.process_ohlcv(ohlcv_df)
        logger.info(f"处理后的数据: {len(processed_data)} 条")
        
        # 策略参数设置
        if strategy_params is None:
            # 根据时间周期设置默认参数
            if timeframe == '1d':
                strategy_params = {'ma_window': 5, 'slope_lookback': 2, 'slope_threshold': 0.0, 'confirm_window': 1}
            elif timeframe == '4h':
                strategy_params = {'ma_window': 10, 'slope_lookback': 2, 'slope_threshold': 0.0, 'confirm_window': 1}
            elif timeframe == '1h':
                strategy_params = {'ma_window': 20, 'slope_lookback': 3, 'slope_threshold': 0.0, 'confirm_window': 1}
            else:
                strategy_params = {'ma_window': 10, 'slope_lookback': 2, 'slope_threshold': 0.0, 'confirm_window': 1}
        
        logger.info(f"策略参数: {strategy_params}")
        
        # 策略信号生成
        if strategy_type == 'simple_ma':
            from src.strategies.simple_ma_strategy import SimpleMAStrategy
            strategy = SimpleMAStrategy(**strategy_params)
        elif strategy_type == 'mean_reversion':
            from src.strategies.mean_reversion_strategy import MeanReversionStrategy
            strategy = MeanReversionStrategy(**strategy_params)
        elif strategy_type == 'rsi':
            from src.strategies.rsi_strategy import RSIStrategy
            strategy = RSIStrategy(**strategy_params)
        elif strategy_type == 'composite':
            from src.strategies.composite_strategy import CompositeStrategy
            strategy = CompositeStrategy(**strategy_params)
        elif strategy_type == 'trend_following':
            from src.strategies.trend_following_strategy import TrendFollowingStrategy
            strategy = TrendFollowingStrategy(**strategy_params)
        elif strategy_type == 'grid_trading':
            from src.strategies.grid_trading_strategy import GridTradingStrategy
            strategy = GridTradingStrategy(**strategy_params)
        elif strategy_type == 'profit_filter':
            from src.strategies.profit_filter_strategy import ProfitFilterStrategy
            strategy = ProfitFilterStrategy(**strategy_params)
        elif strategy_type == 'daily_trading':
            from src.strategies.daily_trading_strategy import DailyTradingStrategy
            strategy = DailyTradingStrategy(**strategy_params)
        else:  # macurve
            strategy = MACurveStrategy(**strategy_params)
            
        signals = strategy.generate_signals(processed_data)
        
        # 检查信号数量
        signal_count = len(signals[signals['signal'] != 0])
        logger.info(f"生成信号数量: {signal_count}")
        
        # 回测
        backtester = SimpleBacktester(initial_cash=100000, fee=0.001)
        result = backtester.run_backtest(processed_data, signals)
        
        # 输出结果
        logger.info(f"=== 回测结果 ===")
        logger.info(f"总收益率: {result['total_return']*100:.2f}%")
        logger.info(f"最大回撤: {result['max_drawdown']*100:.2f}%")
        logger.info(f"夏普比率: {result['sharpe']:.2f}")
        logger.info(f"策略评分: {result['score']:.2f} / 100")
        logger.info(f"交易次数: {len(result['trades'])}")
        
        # 打印详细交易记录
        print_trade_details(result['trades'])
        
        return result
        
    except Exception as e:
        logger.error(f"回测失败: {e}")
        return False

def interactive_backtest():
    """交互式回测，让用户选择参数"""
    print("\n=== 交互式回测系统 ===")
    print("请选择回测参数：")
    
    # 选择回测天数
    print("\n1. 选择回测天数：")
    print("   a) 7天")
    print("   b) 14天") 
    print("   c) 30天")
    print("   d) 60天")
    print("   e) 自定义天数")
    
    days_choice = input("请输入选择 (a/b/c/d/e): ").lower()
    
    if days_choice == 'a':
        days = 7
    elif days_choice == 'b':
        days = 14
    elif days_choice == 'c':
        days = 30
    elif days_choice == 'd':
        days = 60
    elif days_choice == 'e':
        try:
            days = int(input("请输入自定义天数: "))
        except ValueError:
            print("输入无效，使用默认30天")
            days = 30
    else:
        print("输入无效，使用默认30天")
        days = 30
    
    # 选择K线周期
    print("\n2. 选择K线周期：")
    print("   a) 1小时 (1h)")
    print("   b) 4小时 (4h)")
    print("   c) 日线 (1d)")
    
    timeframe_choice = input("请输入选择 (a/b/c): ").lower()
    
    if timeframe_choice == 'a':
        timeframe = '1h'
    elif timeframe_choice == 'b':
        timeframe = '4h'
    elif timeframe_choice == 'c':
        timeframe = '1d'
    else:
        print("输入无效，使用默认日线")
        timeframe = '1d'
    
    # 选择策略
    print("\n3. 选择策略：")
    print("   a) MA曲线策略 (默认)")
    print("   b) 简单MA策略")
    print("   c) 均值回归策略")
    
    strategy_choice = input("请输入选择 (a/b/c): ").lower()
    
    if strategy_choice == 'b':
        # 使用简单MA策略
        strategy_type = 'simple_ma'
        if timeframe == '1d':
            strategy_params = {'short_window': 3, 'long_window': 10}
        elif timeframe == '4h':
            strategy_params = {'short_window': 5, 'long_window': 15}
        else:  # 1h
            strategy_params = {'short_window': 10, 'long_window': 30}
        logger.info("使用简单MA策略")
    elif strategy_choice == 'c':
        # 使用均值回归策略
        strategy_type = 'mean_reversion'
        if timeframe == '1d':
            strategy_params = {'window': 10, 'num_std': 2}
        elif timeframe == '4h':
            strategy_params = {'window': 15, 'num_std': 2}
        else:  # 1h
            strategy_params = {'window': 20, 'num_std': 2}
        logger.info("使用均值回归策略")
    else:
        # 使用MA曲线策略（默认）
        strategy_type = 'macurve'
        strategy_params = None  # 使用默认参数
        logger.info("使用MA曲线策略")
    
    print(f"\n开始回测：{days}天，{timeframe}K线，{strategy_type}策略")
    
    # 执行回测
    return flexible_backtest(days=days, timeframe=timeframe, strategy_params=strategy_params, strategy_type=strategy_type)

if __name__ == "__main__":
    print("=== 量化交易回测系统 ===")
    
    # ==========================================
    # 🚀 快速配置区域 - 修改这里的参数
    # ==========================================
    
    # 基本配置
    DAYS = 30                    # 回测天数
    TIMEFRAME = '1h'             # K线周期: '1h', '4h', '1d'
    STRATEGY_TYPE = 'daily_trading'    # 策略类型: 'daily_trading', 'profit_filter', 'trend_following', 'grid_trading', 'composite', 'rsi', 'macurve', 'simple_ma', 'mean_reversion'
    
    # 策略参数（根据策略类型自动设置）
    if STRATEGY_TYPE == 'simple_ma':
        STRATEGY_PARAMS = {'short_window': 5, 'long_window': 20}
    elif STRATEGY_TYPE == 'mean_reversion':
        STRATEGY_PARAMS = {'window': 20, 'num_std': 2}
    elif STRATEGY_TYPE == 'rsi':
        # RSI策略参数配置
        # 选择以下配置之一：
        
        # 配置1: 保守型（推荐）
        STRATEGY_PARAMS = {
            'rsi_period': 21,           # 更长的RSI周期，减少噪音
            'oversold_threshold': 25.0, # 更严格的超卖阈值
            'overbought_threshold': 75.0, # 更严格的超买阈值
            'confirm_window': 2,        # 2个周期确认
            'use_divergence': True,     # 启用背离检测
            'divergence_lookback': 5
        }
    elif STRATEGY_TYPE == 'composite':
        # 综合策略参数配置
        # 选择以下配置之一：
        
        # 配置1: 平衡型（推荐）
        STRATEGY_PARAMS = {
            # MA参数
            'ma_short': 10,
            'ma_long': 30,
            'ma_trend': 50,
            
            # RSI参数
            'rsi_period': 14,
            'rsi_oversold': 30.0,
            'rsi_overbought': 70.0,
            
            # 布林带参数
            'boll_period': 20,
            'boll_std': 2.0,
            
            # 量价参数
            'volume_ma_period': 20,
            'volume_threshold': 1.5,
            
            # 综合权重
            'ma_weight': 0.3,
            'rsi_weight': 0.25,
            'boll_weight': 0.25,
            'volume_weight': 0.2,
            
            # 信号确认
            'confirm_window': 2,
            'min_score': 0.6,
        }
        
        # 配置2: 平衡型
        # STRATEGY_PARAMS = {
        #     'rsi_period': 14,
        #     'oversold_threshold': 30.0,
        #     'overbought_threshold': 70.0,
        #     'confirm_window': 1,
        #     'use_divergence': False,
        #     'divergence_lookback': 5
        # }
        
        # 配置3: 激进型
        # STRATEGY_PARAMS = {
        #     'rsi_period': 7,
        #     'oversold_threshold': 35.0,
        #     'overbought_threshold': 65.0,
        #     'confirm_window': 1,
        #     'use_divergence': True,
        #     'divergence_lookback': 3
        #         }
    elif STRATEGY_TYPE == 'trend_following':
        # 趋势跟踪策略参数
        STRATEGY_PARAMS = {
            'trend_period': 50,
            'trend_threshold': 0.02,
            'entry_period': 20,
            'entry_threshold': 0.01,
            'stop_loss': 0.05,
            'take_profit': 0.15,
            'position_size': 0.8,
            'confirm_window': 3,
        }
    elif STRATEGY_TYPE == 'grid_trading':
        # 网格交易策略参数
        STRATEGY_PARAMS = {
            'grid_levels': 5,
            'grid_spacing': 0.02,
            'use_dynamic_grid': True,
            'volatility_period': 20,
            'volatility_multiplier': 1.5,
            'base_position': 0.2,
            'max_position': 0.8,
            'max_drawdown': 0.1,
            'confirm_window': 2,
        }
    elif STRATEGY_TYPE == 'profit_filter':
        # 盈利过滤策略参数
        STRATEGY_PARAMS = {
            'ma_short': 10,
            'ma_long': 30,
            'min_profit_after_fee': 0.001,  # 0.1%最小盈利（降低要求）
            'fee_rate': 0.001,  # 0.1%手续费
            'confirm_window': 1,  # 减少确认窗口
            'stop_loss': 0.02,  # 2%止损
            'take_profit': 0.05,  # 5%止盈
        }
    elif STRATEGY_TYPE == 'daily_trading':
        # 每日交易策略参数
        STRATEGY_PARAMS = {
            'take_profit': 0.01,  # 1.0%止盈（更保守，提高胜率）
            'stop_loss': 0.005,   # 0.5%止损（更保守，减少大亏损）
            'rsi_period': 21,     # RSI周期（更长周期，减少噪音）
            'rsi_oversold': 30.0, # RSI超卖阈值
            'ma_short': 5,        # 短期MA
            'ma_long': 20,        # 长期MA
            'start_hour': 0,      # 开始交易时间（0点）
            'end_hour': 24,       # 结束交易时间（24点）
            'min_volume_ratio': 1.2,  # 最小成交量比率（降低要求）
            'price_pullback': 0.01,   # 价格回调阈值
            
            # 新增优化参数（保持关闭状态）
            'atr_period': 14,        # ATR周期
            'atr_multiplier': 1.5,   # ATR倍数
            'use_dynamic_stop': False, # 关闭动态止损
            'use_macd': False,       # 关闭MACD确认
            'avoid_hours': [],       # 不避开任何时段
            'best_hours': [],        # 不限制最佳时段
        }
    else:  # macurve
        # MA曲线策略参数配置
        # 选择以下配置之一：
        
        # 配置1: 保守型
        # STRATEGY_PARAMS = {
        #     'ma_window': 20,        # 20个4h周期 = 80小时 ≈ 3.3天
        #     'slope_lookback': 5,    # 5个4h周期 = 20小时
        #     'slope_threshold': 0.2, # 斜率阈值，过滤噪音
        #     'confirm_window': 2     # 2个周期确认
        # }
        
        # 配置2: 平衡型（推荐）
        STRATEGY_PARAMS = {
            'ma_window': 15,        # 15个4h周期 = 60小时 ≈ 2.5天
            'slope_lookback': 3,    # 3个4h周期 = 12小时
            'slope_threshold': 0.1, # 较小的斜率阈值
            'confirm_window': 1     # 1个周期确认
        }
        
        # 配置3: 激进型
        # STRATEGY_PARAMS = {
        #     'ma_window': 10,        # 10个4h周期 = 40小时 ≈ 1.7天
        #     'slope_lookback': 2,    # 2个4h周期 = 8小时
        #     'slope_threshold': 0.0, # 无斜率过滤
        #     'confirm_window': 1     # 1个周期确认
        # }
        
        # 配置4: 超保守型
        # STRATEGY_PARAMS = {
        #     'ma_window': 30,        # 30个4h周期 = 120小时 ≈ 5天
        #     'slope_lookback': 10,   # 10个4h周期 = 40小时
        #     'slope_threshold': 0.5, # 较大的斜率阈值
        #     'confirm_window': 3     # 3个周期确认
        # }
    
    # ==========================================
    # 📊 常用配置示例（取消注释使用）
    # ==========================================
    
    # 短期高频回测
    # DAYS = 7; TIMEFRAME = '1h'; STRATEGY_TYPE = 'macurve'
    
    # 中期日线回测
    # DAYS = 14; TIMEFRAME = '1d'; STRATEGY_TYPE = 'simple_ma'
    
    # 长期回测
    # DAYS = 60; TIMEFRAME = '1d'; STRATEGY_TYPE = 'mean_reversion'
    
    # ==========================================
    
    print(f"开始回测：{DAYS}天，{TIMEFRAME}K线，{STRATEGY_TYPE}策略")
    
    # 执行回测
    result = flexible_backtest(
        days=DAYS, 
        timeframe=TIMEFRAME, 
        strategy_params=STRATEGY_PARAMS, 
        strategy_type=STRATEGY_TYPE
    )
    
    if result:
        print(f"\n✅ 回测完成！")
    else:
        print(f"\n❌ 回测失败！") 