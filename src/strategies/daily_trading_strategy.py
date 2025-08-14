import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .base_strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)

class DailyTradingStrategy(BaseStrategy):
    """每日交易策略 - 每天找一个合适的机会买入，等盈利2%时卖出"""
    
    def __init__(
        self,
        take_profit: float = 0.02,  # 2%止盈
        stop_loss: float = 0.01,    # 1%止损
        rsi_period: int = 14,        # RSI周期
        rsi_oversold: float = 30.0,  # RSI超卖阈值
        ma_short: int = 5,           # 短期MA
        ma_long: int = 20,           # 长期MA
        start_hour: int = 0,         # 开始交易时间（0点）
        end_hour: int = 24,          # 结束交易时间（24点）
        min_volume_ratio: float = 1.5,  # 最小成交量比率
        price_pullback: float = 0.01,   # 价格回调阈值
        
        # 新增优化参数
        atr_period: int = 14,        # ATR周期
        atr_multiplier: float = 2.0, # ATR倍数（用于动态止损）
        use_dynamic_stop: bool = True, # 是否使用动态止损
        use_macd: bool = True,       # 是否使用MACD确认
        avoid_hours: list = None,    # 避开的高波动时段
        best_hours: list = None,     # 最佳交易时段
    ):
        super().__init__({
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "rsi_period": rsi_period,
            "rsi_oversold": rsi_oversold,
            "ma_short": ma_short,
            "ma_long": ma_long,
            "start_hour": start_hour,
            "end_hour": end_hour,
            "min_volume_ratio": min_volume_ratio,
            "price_pullback": price_pullback,
            "atr_period": atr_period,
            "atr_multiplier": atr_multiplier,
            "use_dynamic_stop": use_dynamic_stop,
            "use_macd": use_macd,
            "avoid_hours": avoid_hours or [2, 3, 4, 5],  # 默认避开凌晨2-5点
            "best_hours": best_hours or [9, 10, 14, 15, 20, 21],  # 默认最佳交易时间
        })
        
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.min_volume_ratio = min_volume_ratio
        self.price_pullback = price_pullback
        
        # 新增优化参数
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.use_dynamic_stop = use_dynamic_stop
        self.use_macd = use_macd
        self.avoid_hours = avoid_hours or [2, 3, 4, 5]
        self.best_hours = best_hours or [9, 10, 14, 15, 20, 21]
        
        # 交易状态管理
        self.daily_traded = {}  # 记录每日交易状态
        self.current_position = 0  # 当前持仓状态
        self.entry_price = 0  # 入场价格
        self.entry_time = None  # 入场时间
        self.entry_date = None  # 入场日期
        self.carry_over = False  # 是否跨日持仓

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
        
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算ATR（平均真实波幅）"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
        
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _is_trading_time(self, timestamp: pd.Timestamp) -> bool:
        """判断是否在交易时间内"""
        if hasattr(timestamp, 'hour'):
            hour = timestamp.hour
            
            # 避开高波动时段
            if hour in self.avoid_hours:
                return False
                
            # 优先选择最佳交易时段
            if hour in self.best_hours:
                return True
                
            # 其他时间也允许交易
            return self.start_hour <= hour <= self.end_hour
        else:
            # 如果没有小时信息，默认允许交易
            return True

    def _can_trade_today(self, timestamp: pd.Timestamp) -> bool:
        """判断今天是否可以交易"""
        try:
            if hasattr(timestamp, 'strftime'):
                date_str = timestamp.strftime('%Y-%m-%d')
            else:
                # 如果不是datetime对象，默认允许交易
                return True
            
            # 如果今天已经交易过，不能交易
            if self.daily_traded.get(date_str, False):
                return False
                
            # 如果是跨日持仓，不能交易（等待卖出）
            if self.carry_over:
                return False
                
            return True
        except Exception as e:
            logger.warning(f"日期处理错误: {e}")
            return True

    def _mark_daily_traded(self, timestamp: pd.Timestamp):
        """标记今天已交易"""
        try:
            if hasattr(timestamp, 'strftime'):
                date_str = timestamp.strftime('%Y-%m-%d')
                self.daily_traded[date_str] = True
            else:
                logger.warning("无法标记交易日期：时间戳格式错误")
        except Exception as e:
            logger.warning(f"标记交易日期错误: {e}")

    def _should_take_profit(self, current_price: float) -> bool:
        """判断是否应该止盈"""
        if self.current_position > 0 and self.entry_price > 0:
            profit_ratio = (current_price - self.entry_price) / self.entry_price
            return profit_ratio >= self.take_profit
        return False

    def _should_stop_loss(self, current_price: float, current_data: pd.Series = None) -> bool:
        """判断是否应该止损"""
        if self.current_position > 0 and self.entry_price > 0:
            loss_ratio = (self.entry_price - current_price) / self.entry_price
            
            if self.use_dynamic_stop and current_data is not None:
                # 使用动态止损（基于ATR）
                atr = self._calculate_atr(current_data.to_frame().T, self.atr_period).iloc[-1]
                dynamic_stop_loss = (atr * self.atr_multiplier) / current_price
                return loss_ratio >= dynamic_stop_loss
            else:
                # 使用固定止损
                return loss_ratio >= self.stop_loss
        return False

    def _should_close_position(self, current_price: float, timestamp: pd.Timestamp, current_data: pd.Series = None) -> bool:
        """判断是否应该平仓"""
        if self.current_position <= 0:
            return False
            
        # 检查止盈
        if self._should_take_profit(current_price):
            profit_ratio = (current_price - self.entry_price) / self.entry_price
            logger.info(f"止盈触发: 盈利 {profit_ratio:.2%}")
            return True
            
        # 检查止损
        if self._should_stop_loss(current_price, current_data):
            loss_ratio = (self.entry_price - current_price) / self.entry_price
            logger.info(f"止损触发: 亏损 {loss_ratio:.2%}")
            return True
            
        # 检查是否到了24点（跨日持仓）
        if self.entry_time and timestamp:
            try:
                # 确保timestamp是datetime对象
                if hasattr(timestamp, 'strftime'):
                    entry_date = self.entry_time.strftime('%Y-%m-%d')
                    current_date = timestamp.strftime('%Y-%m-%d')
                else:
                    # 如果不是datetime对象，跳过跨日检查
                    return False
                
                # 如果日期不同，说明跨日了
                if entry_date != current_date:
                    if not self.carry_over:
                        logger.info(f"跨日持仓: 从 {entry_date} 到 {current_date}")
                        self.carry_over = True
                        self.entry_date = entry_date
                    return False  # 跨日持仓不自动平仓，等待合适时机
            except Exception as e:
                logger.warning(f"时间戳处理错误: {e}")
                return False
                
        return False

    def _check_buy_opportunity(self, df: pd.DataFrame, current_idx: int) -> bool:
        """检查买入机会"""
        if current_idx < max(self.ma_long, self.rsi_period):
            return False
            
        current_data = df.iloc[current_idx]
        recent_data = df.iloc[:current_idx+1]
        
        # 检查交易时间和每日限制
        if not self._is_trading_time(current_data.name) or not self._can_trade_today(current_data.name):
            return False
            

            
        # 技术指标判断
        rsi = self._calculate_rsi(recent_data['close'], self.rsi_period)
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else 50
        
        # 检查NaN值
        if pd.isna(current_rsi) or pd.isna(prev_rsi):
            return False
        
        ma_short = recent_data['close'].rolling(self.ma_short).mean()
        ma_long = recent_data['close'].rolling(self.ma_long).mean()
        current_ma_short = ma_short.iloc[-1]
        current_ma_long = ma_long.iloc[-1]
        
        high_20 = recent_data['high'].rolling(20).max()
        current_high_20 = high_20.iloc[-1]
        price_pullback_ratio = (current_high_20 - current_data['close']) / current_high_20
        
        volume_ma = recent_data['volume'].rolling(20).mean()
        current_volume_ratio = current_data['volume'] / volume_ma.iloc[-1]
        
        # MACD指标判断
        if self.use_macd:
            macd_line, signal_line, histogram = self._calculate_macd(recent_data['close'])
            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]
            prev_macd = macd_line.iloc[-2] if len(macd_line) > 1 else 0
            prev_signal = signal_line.iloc[-2] if len(signal_line) > 1 else 0
            
            # MACD条件：MACD金叉且在零轴上方
            macd_condition = ((current_macd > current_signal) and 
                             (prev_macd <= prev_signal) and  # 金叉
                             (current_macd > 0))  # 在零轴上方
        else:
            macd_condition = True
        
        # 买入条件（恢复到50%胜率版本）
        # 1. RSI条件：RSI在合理区间且反弹
        rsi_condition = (current_rsi > prev_rsi and 
                        35 < current_rsi < 65)  # RSI在35-65之间，更宽松
        
        # 2. MA条件：价格在长期MA之上
        ma_condition = current_data['close'] > current_ma_long
        
        # 3. 价格回调条件：适度回调
        pullback_condition = (price_pullback_ratio >= 0.005 and 
                             price_pullback_ratio <= 0.03)  # 回调0.5%-3%，更宽松
        
        # 4. 成交量条件：成交量放大
        volume_condition = current_volume_ratio >= 1.1  # 降低成交量要求
        
        # 综合判断：满足主要条件即可
        buy_signal = (rsi_condition and ma_condition and 
                     pullback_condition and volume_condition and macd_condition)
        
        if buy_signal:
            logger.info(f"买入信号: RSI={current_rsi:.1f}, 价格={current_data['close']:.1f}")
        
        return buy_signal

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据"""
        data = df.copy()
        data['rsi'] = self._calculate_rsi(data['close'], self.rsi_period)
        data['ma_short'] = data['close'].rolling(self.ma_short).mean()
        data['ma_long'] = data['close'].rolling(self.ma_long).mean()
        data['volume_ma'] = data['volume'].rolling(20).mean()
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        data['high_20'] = data['high'].rolling(20).max()
        data['price_pullback'] = (data['high_20'] - data['close']) / data['high_20']
        
        # 新增指标
        data['atr'] = self._calculate_atr(data, self.atr_period)
        macd_line, signal_line, histogram = self._calculate_macd(data['close'])
        data['macd'] = macd_line
        data['macd_signal'] = signal_line
        data['macd_histogram'] = histogram
        
        return data

    def generate_signal(self, df: pd.DataFrame) -> int:
        """生成单个信号"""
        data = self._prepare(df)
        
        if len(data) < max(self.ma_long, self.rsi_period) + 5:
            return 0
            
        current_idx = len(data) - 1
        current_data = data.iloc[current_idx]
        current_price = current_data['close']
        timestamp = current_data.name
        
        # 检查平仓
        if self.current_position > 0:
            if self._should_close_position(current_price, timestamp, current_data):
                self.current_position = 0
                self.entry_price = 0
                self.entry_time = None
                self.entry_date = None
                self.carry_over = False
                return -1
            
        # 检查买入
        if self.current_position == 0:
            if self._check_buy_opportunity(data, current_idx):
                self.current_position = 1
                self.entry_price = current_price
                self.entry_time = timestamp
                if hasattr(timestamp, 'strftime'):
                    self.entry_date = timestamp.strftime('%Y-%m-%d')
                else:
                    self.entry_date = None
                self.carry_over = False
                self._mark_daily_traded(timestamp)
                return 1
            
        return 0

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成信号序列"""
        df = self._prepare(data)
        df['signal'] = 0
        
        min_periods = max(self.ma_long, self.rsi_period) + 5
        
        if len(df) < min_periods:
            return df
            
        # 重置状态
        self.daily_traded = {}
        self.current_position = 0
        self.entry_price = 0
        self.entry_time = None
        self.entry_date = None
        self.carry_over = False
        
        # 生成信号
        for i in range(min_periods, len(df)):
            df_subset = df.iloc[:i+1]
            signal = self.generate_signal(df_subset)
            df.iloc[i, df.columns.get_loc('signal')] = signal
            

            
        return df

    def get_strategy_info(self) -> dict:
        """获取策略信息"""
        return {
            "name": "Daily Trading Strategy",
            "description": "每日交易策略 - 每天找一个合适的机会买入，等盈利2%时卖出",
            "parameters": {
                "take_profit": f"止盈: {self.take_profit*100:.1f}%",
                "strategy": f"止损: {self.stop_loss*100:.1f}%",
                "rsi_period": f"RSI周期: {self.rsi_period}",
                "ma_short": f"短期MA: {self.ma_short}",
                "ma_long": f"长期MA: {self.ma_long}",
                "trading_hours": f"交易时间: {self.start_hour}:00-{self.end_hour}:00",
                "start_hour": f"开始时间: {self.start_hour}:00",
                "end_hour": f"结束时间: {self.end_hour}:00",
                "atr_period": f"ATR周期: {self.atr_period}",
                "atr_multiplier": f"ATR倍数: {self.atr_multiplier}",
                "use_dynamic_stop": f"动态止损: {'是' if self.use_dynamic_stop else '否'}",
                "use_macd": f"MACD确认: {'是' if self.use_macd else '否'}",
                "avoid_hours": f"避开时段: {self.avoid_hours}",
                "best_hours": f"最佳时段: {self.best_hours}",
            }
        }
