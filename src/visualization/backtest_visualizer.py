import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import logging
import matplotlib as mpl

class BacktestVisualizer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
        plt.rcParams['axes.unicode_minus'] = False
        # 设置seaborn样式
        sns.set_style("whitegrid")

    def plot_equity_curve(self, equity_curve: pd.Series, title: str = "Equity Curve", total_return: float = None):
        """
        绘制资金曲线
        Args:
            equity_curve: 资金曲线数据
            title: 图表标题
            total_return: 总收益率
        """
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve.index, equity_curve.values, label='Equity')
        if total_return is not None:
            plt.title(f"{title} (总收益率: {total_return:.2%})")
        else:
            plt.title(title)
        plt.xlabel('Time')
        plt.ylabel('Equity')
        plt.legend()
        plt.grid(True)
        plt.show()

    def plot_drawdown(self, equity_curve: pd.Series, title: str = "Drawdown Analysis", max_drawdown: float = None):
        """
        绘制回撤曲线
        Args:
            equity_curve: 资金曲线数据
            title: 图表标题
            max_drawdown: 最大回撤
        """
        # 计算回撤
        rolling_max = equity_curve.expanding().max()
        drawdown = (equity_curve - rolling_max) / rolling_max * 100

        plt.figure(figsize=(12, 6))
        plt.plot(drawdown.index, drawdown.values, label='Drawdown %', color='red')
        if max_drawdown is not None:
            plt.title(f"{title} (最大回撤: {max_drawdown:.2%})")
        else:
            plt.title(title)
        plt.xlabel('Time')
        plt.ylabel('Drawdown (%)')
        plt.legend()
        plt.grid(True)
        plt.show()

    def plot_signals(self, data: pd.DataFrame, title: str = "Trading Signals"):
        """
        绘制K线和交易信号
        Args:
            data: 包含价格和信号的数据
            title: 图表标题
        """
        plt.figure(figsize=(12, 6))
        
        # 绘制K线
        plt.plot(data.index, data['close'], label='Close Price', color='blue', alpha=0.5)
        
        # 绘制买入信号
        buy_signals = data[data['signal'] == 1]
        plt.scatter(buy_signals.index, buy_signals['close'], 
                   marker='^', color='red', label='Buy Signal', s=100)
        
        # 绘制卖出信号
        sell_signals = data[data['signal'] == -1]
        plt.scatter(sell_signals.index, sell_signals['close'], 
                   marker='v', color='green', label='Sell Signal', s=100)
        
        plt.title(title)
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        plt.show()

    def plot_monthly_returns(self, strategy_returns: pd.Series, title: str = "Monthly Returns"):
        """
        绘制月度收益热力图
        Args:
            strategy_returns: 策略收益率序列
            title: 图表标题
        """
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
        # 修正：使用列名而不是0
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

    def plot_all(self, backtest_result: dict):
        """
        绘制所有回测结果图表
        Args:
            backtest_result: 回测结果字典
        """
        df = backtest_result['df']
        equity_curve = backtest_result['equity_curve']
        strategy_returns = df['strategy_ret']
        total_return = backtest_result.get('total_return')
        max_drawdown = backtest_result.get('max_drawdown')
        sharpe = backtest_result.get('sharpe')

        # 确保索引是datetime类型
        if not isinstance(equity_curve.index, pd.DatetimeIndex):
            equity_curve.index = pd.to_datetime(equity_curve.index)
        if not isinstance(strategy_returns.index, pd.DatetimeIndex):
            strategy_returns.index = pd.to_datetime(strategy_returns.index)

        # 绘制资金曲线
        self.plot_equity_curve(equity_curve, total_return=total_return)
        
        # 绘制回撤分析
        self.plot_drawdown(equity_curve, max_drawdown=max_drawdown)
        
        # 绘制交易信号
        self.plot_signals(df)
        
        # 绘制月度收益热力图
        self.plot_monthly_returns(strategy_returns)

        print(f"总收益率: {total_return:.2%}, 最大回撤: {max_drawdown:.2%}, 夏普比率: {sharpe:.2f}") 