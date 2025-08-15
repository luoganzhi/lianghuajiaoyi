#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合约每日交易策略 - 高杠杆版本
基于DailyTradingStrategy，调整为50倍杠杆、50%止盈、逐仓模式、15分钟K线
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class ContractDailyTradingStrategy:
    """
    合约每日交易策略 - 高杠杆版本
    
    特点:
    - 50倍杠杆
    - 50%止盈，无止损
    - 逐仓模式
    - 15分钟K线
    - 每日最多交易一次
    - 支持做多和做空
    """
    
    def __init__(self, 
                 take_profit=0.50,           # 止盈比例 50%
                 rsi_period=14,              # RSI周期
                 rsi_oversold=30.0,          # RSI超卖阈值
                 rsi_overbought=70.0,        # RSI超买阈值
                 ma_short=5,                 # 短期MA
                 ma_long=20,                 # 长期MA
                 min_volume_ratio=1.5,       # 最小成交量比例
                 price_pullback=0.01,        # 价格回调比例
                 start_hour=0,               # 开始交易时间
                 end_hour=24,                # 结束交易时间
                 kline_interval='1s',        # K线间隔 1秒（调试模式）
                 debug_mode=False):          # 调试模式：降低信号生成条件
        
        # 策略参数
        self.take_profit = take_profit
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.min_volume_ratio = min_volume_ratio
        self.price_pullback = price_pullback
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.kline_interval = kline_interval
        self.debug_mode = debug_mode
        
        # 保存原始参数（用于调试完成后恢复）
        self.original_params = {
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'min_volume_ratio': min_volume_ratio,
            'price_pullback': price_pullback
        }
        
        # 如果启用调试模式，调整参数以降低信号生成条件
        if self.debug_mode:
            self._enable_debug_mode()
        
        # 交易状态管理
        self.daily_traded = {}  # 记录每日交易状态
        self.current_position = 0  # 当前持仓数量
        self.entry_price = 0  # 入场价格
        self.entry_time = None  # 入场时间
        self.position_type = None  # 持仓类型: 'long' 或 'short'
        self.entry_date = None  # 入场日期
        self.carry_over = False  # 是否跨日持仓
        
        # 合约交易特定参数
        self.leverage = 50  # 50倍杠杆
        self.margin_mode = 'isolated'  # 逐仓模式
        
        logger.info(f"合约每日交易策略初始化完成")
        logger.info(f"杠杆倍数: {self.leverage}x")
        logger.info(f"止盈设置: {self.take_profit * 100:.1f}%")
        logger.info(f"保证金模式: {self.margin_mode}")
        logger.info(f"K线间隔: {self.kline_interval}")
        if self.debug_mode:
            logger.info(f"🔧 调试模式已启用 - 信号生成条件已降低")
        else:
            logger.info(f"📊 生产模式 - 使用标准信号生成条件")
    
    def _enable_debug_mode(self):
        """启用调试模式，极大降低信号生成条件"""
        # 调整RSI阈值，极大扩大交易区间
        self.rsi_oversold = 5.0       # 从30.0降低到5.0
        self.rsi_overbought = 95.0    # 从70.0提高到95.0
        
        # 极大降低成交量要求
        self.min_volume_ratio = 0.01  # 从1.5降低到0.01
        
        # 极大降低价格回调要求
        self.price_pullback = 0.0001  # 从0.01降低到0.0001
        
        # 极大缩短MA周期，让信号更敏感
        self.ma_short = 2             # 从5降低到2
        self.ma_long = 5              # 从20降低到5
        
        logger.info(f"🔧 调试模式参数调整:")
        logger.info(f"  RSI超卖阈值: {self.original_params['rsi_oversold']} → {self.rsi_oversold}")
        logger.info(f"  RSI超买阈值: {self.original_params['rsi_overbought']} → {self.rsi_overbought}")
        logger.info(f"  最小成交量比例: {self.original_params['min_volume_ratio']} → {self.min_volume_ratio}")
        logger.info(f"  价格回调比例: {self.original_params['price_pullback']} → {self.price_pullback}")
        logger.info(f"  短期MA: {self.original_params.get('ma_short', 5)} → {self.ma_short}")
        logger.info(f"  长期MA: {self.original_params.get('ma_long', 20)} → {self.ma_long}")
    
    def restore_original_params(self):
        """恢复原始参数配置"""
        self.rsi_oversold = self.original_params['rsi_oversold']
        self.rsi_overbought = self.original_params['rsi_overbought']
        self.min_volume_ratio = self.original_params['min_volume_ratio']
        self.price_pullback = self.original_params['price_pullback']
        
        logger.info(f"📊 已恢复原始参数配置:")
        logger.info(f"  RSI超卖阈值: {self.rsi_oversold}")
        logger.info(f"  RSI超买阈值: {self.rsi_overbought}")
        logger.info(f"  最小成交量比例: {self.min_volume_ratio}")
        logger.info(f"  价格回调比例: {self.price_pullback}")
        logger.info(f"🔧 调试模式已关闭")
    
    def _calculate_rsi(self, data, period=14):
        """计算RSI指标"""
        try:
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.error(f"RSI计算失败: {e}")
            return pd.Series([50] * len(data))
    
    def _calculate_ma(self, data, period):
        """计算移动平均线"""
        try:
            return data['close'].rolling(window=period).mean()
        except Exception as e:
            logger.error(f"MA计算失败: {e}")
            return pd.Series([0] * len(data))
    
    def _is_trading_time(self, timestamp):
        """检查是否为交易时间"""
        try:
            if hasattr(timestamp, 'strftime'):
                hour = timestamp.hour
                return self.start_hour <= hour <= self.end_hour
            else:
                return True  # 如果不是datetime对象，默认允许交易
        except Exception as e:
            logger.warning(f"时间检查错误: {e}")
            return True
    
    def _mark_daily_traded(self, date):
        """标记今日已交易"""
        try:
            if hasattr(date, 'strftime'):
                date_str = date.strftime('%Y-%m-%d')
                self.daily_traded[date_str] = True
                logger.info(f"标记 {date_str} 为已交易")
        except Exception as e:
            logger.warning(f"标记交易日期错误: {e}")
    
    def _can_trade_today(self, timestamp):
        """检查今日是否可以交易"""
        try:
            if hasattr(timestamp, 'strftime'):
                today = timestamp.strftime('%Y-%m-%d')
                # 如果跨日持仓，今日不能开新仓
                if self.carry_over and today != self.entry_date:
                    return False
                # 检查当前是否有持仓（改为基于持仓状态而不是日期）
                return self.current_position == 0
            else:
                return True
        except Exception as e:
            logger.warning(f"检查交易日期错误: {e}")
            return True
    
    def _should_take_profit(self, current_price):
        """检查是否应该止盈"""
        if self.entry_price <= 0 or self.current_position == 0:
            return False
        
        if self.position_type == 'long':
            # 做多止盈
            profit_pct = (current_price - self.entry_price) / self.entry_price
            return profit_pct >= self.take_profit
        elif self.position_type == 'short':
            # 做空止盈
            profit_pct = (self.entry_price - current_price) / self.entry_price
            return profit_pct >= self.take_profit
        
        return False
    
    def _should_close_position(self, timestamp, current_data):
        """检查是否应该平仓"""
        if self.current_position == 0:
            return False
        
        # 检查止盈
        current_price = current_data['close'].iloc[-1]
        if self._should_take_profit(current_price):
            logger.info(f"触发止盈: 当前价格 {current_price:.2f}, 入场价格 {self.entry_price:.2f}")
            return True
        
        # 检查跨日持仓
        if self.entry_time and timestamp:
            try:
                if hasattr(timestamp, 'strftime'):
                    entry_date = self.entry_time.strftime('%Y-%m-%d')
                    current_date = timestamp.strftime('%Y-%m-%d')
                    if entry_date != current_date:
                        if not self.carry_over:
                            logger.info(f"跨日持仓: 从 {entry_date} 到 {current_date}")
                            self.carry_over = True
                            self.entry_date = entry_date
                        return False  # 跨日持仓不自动平仓
                else:
                    return False
            except Exception as e:
                logger.warning(f"时间戳处理错误: {e}")
                return False
        
        return False
    
    def _check_buy_opportunity(self, data):
        """检查买入机会（做多）"""
        if len(data) < self.ma_long:
            return False
        
        current_data = data.iloc[-1]
        recent_data = data.iloc[-20:]  # 获取最近20根K线
        
        # 计算技术指标
        rsi = self._calculate_rsi(recent_data, self.rsi_period).iloc[-1]
        ma_short = self._calculate_ma(recent_data, self.ma_short).iloc[-1]
        ma_long = self._calculate_ma(recent_data, self.ma_long).iloc[-1]
        
        # 计算成交量比例
        current_volume = current_data['volume']
        avg_volume = recent_data['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        # 计算价格回调
        high_price = recent_data['high'].max()
        current_price = current_data['close']
        price_pullback_ratio = (high_price - current_price) / high_price if high_price > 0 else 0
        
        # 买入条件（调试模式：极大简化）
        rsi_condition = self.rsi_oversold < rsi < self.rsi_overbought
        ma_condition = ma_short > ma_long
        volume_condition = volume_ratio >= self.min_volume_ratio
        # 调试模式：移除价格回调条件，让信号更容易触发
        # pullback_condition = self.price_pullback <= price_pullback_ratio <= 0.03
        
        # 调试模式：显示详细的条件检查
        if self.debug_mode:
            logger.info(f"🔍 做多条件检查: RSI={rsi:.1f}({rsi_condition}), MA短期={ma_short:.2f} > MA长期={ma_long:.2f}({ma_condition}), 成交量比例={volume_ratio:.3f}({volume_condition})")
        
        if rsi_condition and ma_condition and volume_condition:  # 移除pullback_condition
            logger.info(f"做多信号触发: RSI={rsi:.1f}, MA短期={ma_short:.2f}, MA长期={ma_long:.2f}")
            return True
        
        return False
    
    def _check_sell_opportunity(self, data):
        """检查卖出机会（做空）"""
        if len(data) < self.ma_long:
            return False
        
        current_data = data.iloc[-1]
        recent_data = data.iloc[-20:]  # 获取最近20根K线
        
        # 计算技术指标
        rsi = self._calculate_rsi(recent_data, self.rsi_period).iloc[-1]
        ma_short = self._calculate_ma(recent_data, self.ma_short).iloc[-1]
        ma_long = self._calculate_ma(recent_data, self.ma_long).iloc[-1]
        
        # 计算成交量比例
        current_volume = current_data['volume']
        avg_volume = recent_data['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        # 计算价格反弹
        low_price = recent_data['low'].min()
        current_price = current_data['close']
        price_bounce_ratio = (current_price - low_price) / low_price if low_price > 0 else 0
        
        # 做空条件（调试模式：极大简化）
        rsi_condition = self.rsi_oversold < rsi < self.rsi_overbought
        ma_condition = ma_short < ma_long  # 短期MA < 长期MA
        volume_condition = volume_ratio >= self.min_volume_ratio
        # 调试模式：移除价格反弹条件，让信号更容易触发
        # bounce_condition = self.price_pullback <= price_bounce_ratio <= 0.03
        
        # 调试模式：显示详细的条件检查
        if self.debug_mode:
            logger.info(f"🔍 做空条件检查: RSI={rsi:.1f}({rsi_condition}), MA短期={ma_short:.2f} < MA长期={ma_long:.2f}({ma_condition}), 成交量比例={volume_ratio:.3f}({volume_condition})")
        
        if rsi_condition and ma_condition and volume_condition:  # 移除bounce_condition
            logger.info(f"做空信号触发: RSI={rsi:.1f}, MA短期={ma_short:.2f}, MA长期={ma_long:.2f}")
            return True
        
        return False
    
    def _prepare(self, data):
        """准备数据"""
        if data is None or len(data) == 0:
            return None
        
        # 确保数据包含必要的列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required_columns):
            logger.error(f"数据缺少必要列: {required_columns}")
            return None
        
        # 数据预处理
        data = data.copy()
        data = data.dropna()
        
        if len(data) < self.ma_long:
            logger.warning(f"数据不足: {len(data)} < {self.ma_long}")
            return None
        
        return data
    
    def generate_signal(self, data):
        """
        生成交易信号
        
        Returns:
            1: 做多信号
            -1: 做空信号
            0: 无信号
        """
        try:
            # 准备数据
            data = self._prepare(data)
            if data is None:
                return 0
            
            current_timestamp = data.index[-1]
            
            # 检查交易时间
            if not self._is_trading_time(current_timestamp):
                if self.debug_mode:
                    logger.info(f"🔍 不在交易时间内")
                return 0
            
            # 检查今日是否可以交易
            if not self._can_trade_today(current_timestamp):
                if self.debug_mode:
                    logger.info(f"🔍 当前不能交易: 持仓状态={self.current_position}")
                return 0
            
            # 检查是否应该平仓
            if self._should_close_position(current_timestamp, data):
                if self.debug_mode:
                    logger.info(f"🔍 应该平仓")
                return 0
            
            # 无持仓时，检查开仓机会
            if self.current_position == 0:
                # 检查做多机会
                if self._check_buy_opportunity(data):
                    return 1
                # 检查做空机会
                elif self._check_sell_opportunity(data):
                    return -1
                else:
                    if self.debug_mode:
                        logger.info(f"🔍 无开仓机会")
            else:
                if self.debug_mode:
                    logger.info(f"🔍 当前有持仓，不检查开仓机会")
            
            return 0
            
        except Exception as e:
            logger.error(f"生成信号失败: {e}")
            return 0
    
    def generate_signals(self, data):
        """生成多个时间点的信号（用于回测）"""
        signals = []
        
        for i in range(len(data)):
            current_data = data.iloc[:i+1]
            if len(current_data) >= self.ma_long:
                signal = self.generate_signal(current_data)
                signals.append(signal)
            else:
                signals.append(0)
        
        return signals
    
    def on_position_entry(self, side, price, size, timestamp):
        """持仓入场回调"""
        self.current_position = size
        self.entry_price = price
        self.entry_time = timestamp
        self.position_type = 'long' if side == 'buy' else 'short'
        
        if hasattr(timestamp, 'strftime'):
            self.entry_date = timestamp.strftime('%Y-%m-%d')
            self.carry_over = False
        
        logger.info(f"持仓入场: {side} {size} @ {price}, 类型: {self.position_type}")
    
    def on_position_exit(self, side, price, size, pnl):
        """持仓出场回调"""
        logger.info(f"持仓出场: {side} {size} @ {price}, PnL: {pnl}")
        logger.info(f"重置前持仓状态: {self.current_position}")
        
        self.current_position = 0
        self.entry_price = 0
        self.entry_time = None
        self.position_type = None
        self.entry_date = None
        self.carry_over = False
        
        logger.info(f"重置后持仓状态: {self.current_position}")
        logger.info(f"策略状态已重置，可以重新开仓")
    
    def get_strategy_info(self):
        """获取策略信息"""
        info = {
            "策略名称": "合约每日交易策略 - 高杠杆版本",
            "策略类型": "趋势跟踪 + 均值回归",
            "杠杆倍数": f"{self.leverage}x",
            "保证金模式": self.margin_mode,
            "止盈设置": f"{self.take_profit * 100:.1f}%",
            "止损设置": "无止损",
            "调试模式": "🔧 已启用" if self.debug_mode else "📊 生产模式",
            "RSI周期": self.rsi_period,
            "RSI超卖阈值": self.rsi_oversold,
            "RSI超买阈值": self.rsi_overbought,
            "短期MA": self.ma_short,
            "长期MA": self.ma_long,
            "最小成交量比例": self.min_volume_ratio,
            "价格回调比例": f"{self.price_pullback * 100:.1f}%",
            "交易时间": f"{self.start_hour}:00-{self.end_hour}:00",
            "K线间隔": self.kline_interval,
            "当前持仓": self.current_position,
            "持仓类型": self.position_type,
            "入场价格": self.entry_price,
            "跨日持仓": self.carry_over
        }
        return info
    
    def reset_daily_state(self, date):
        """重置每日状态"""
        if hasattr(date, 'strftime'):
            date_str = date.strftime('%Y-%m-%d')
            if date_str in self.daily_traded:
                del self.daily_traded[date_str]
            logger.info(f"重置 {date_str} 的交易状态")
    
    def get_position_info(self):
        """获取当前持仓信息"""
        if self.current_position == 0:
            return None
        
        return {
            "position_type": self.position_type,
            "size": self.current_position,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time,
            "leverage": self.leverage,
            "margin_mode": self.margin_mode
        }
    
    def enable_high_precision_mode(self):
        """
        启用高精度模式 - 适配25%保证金止盈目标
        
        在50倍杠杆下，25%的保证金止盈 = 0.5%的价格止盈
        需要更精确的信号生成条件来避免误开仓
        """
        # 保存当前参数（用于后续恢复）
        if not hasattr(self, 'high_precision_params'):
            self.high_precision_params = {
                'rsi_oversold': self.rsi_oversold,
                'rsi_overbought': self.rsi_overbought,
                'min_volume_ratio': self.min_volume_ratio,
                'price_pullback': self.price_pullback,
                'ma_short': self.ma_short,
                'ma_long': self.ma_long,
                'take_profit': self.take_profit
            }
        
        # 调整RSI阈值，提高信号精度
        self.rsi_oversold = 35.0      # 从30.0提高到35.0（更保守）
        self.rsi_overbought = 65.0    # 从70.0降低到65.0（更保守）
        
        # 提高成交量要求，确保趋势明确
        self.min_volume_ratio = 2.0   # 从1.5提高到2.0
        
        # 提高价格回调要求，避免假突破
        self.price_pullback = 0.02    # 从0.01提高到0.02（2%回调）
        
        # 调整MA周期，提高趋势判断准确性
        self.ma_short = 8             # 从5提高到8
        self.ma_long = 25             # 从20提高到25
        
        # 设置止盈为0.5%（50倍杠杆 = 25%保证金止盈）
        self.take_profit = 0.005      # 0.5%
        
        logger.info(f"🎯 高精度模式已启用 - 适配25%保证金止盈目标")
        logger.info(f"📊 参数调整详情:")
        logger.info(f"  RSI超卖阈值: {self.high_precision_params['rsi_oversold']} → {self.rsi_oversold} (更保守)")
        logger.info(f"  RSI超买阈值: {self.high_precision_params['rsi_overbought']} → {self.rsi_overbought} (更保守)")
        logger.info(f"  最小成交量比例: {self.high_precision_params['min_volume_ratio']} → {self.min_volume_ratio} (更严格)")
        logger.info(f"  价格回调比例: {self.high_precision_params['price_pullback']*100:.1f}% → {self.price_pullback*100:.1f}% (更严格)")
        logger.info(f"  短期MA: {self.high_precision_params['ma_short']} → {self.ma_long} (更稳定)")
        logger.info(f"  长期MA: {self.high_precision_params['ma_long']} → {self.ma_long} (更稳定)")
        logger.info(f"  止盈设置: {self.take_profit*100:.3f}% (50倍杠杆 = 25%保证金止盈)")
        logger.info(f"🎯 目标: 在50倍杠杆下实现25%的保证金盈利目标")
    
    def restore_high_precision_params(self):
        """恢复高精度模式前的参数配置"""
        if hasattr(self, 'high_precision_params'):
            self.rsi_oversold = self.high_precision_params['rsi_oversold']
            self.rsi_overbought = self.high_precision_params['rsi_overbought']
            self.min_volume_ratio = self.high_precision_params['min_volume_ratio']
            self.price_pullback = self.high_precision_params['price_pullback']
            self.ma_short = self.high_precision_params['ma_short']
            self.ma_long = self.high_precision_params['ma_long']
            self.take_profit = self.high_precision_params['take_profit']
            
            logger.info(f"📊 已恢复高精度模式前的参数配置:")
            logger.info(f"  RSI超卖阈值: {self.rsi_oversold}")
            logger.info(f"  RSI超买阈值: {self.rsi_overbought}")
            logger.info(f"  最小成交量比例: {self.min_volume_ratio}")
            logger.info(f"  价格回调比例: {self.price_pullback*100:.1f}%")
            logger.info(f"  短期MA: {self.ma_short}")
            logger.info(f"  长期MA: {self.ma_long}")
            logger.info(f"  止盈设置: {self.take_profit*100:.1f}%")
        else:
            logger.warning(f"⚠️ 未找到高精度模式参数，无法恢复")
    
    def get_strategy_mode(self):
        """获取当前策略模式"""
        if hasattr(self, 'high_precision_params') and self.take_profit == 0.005:
            return "高精度模式 (25%保证金止盈)"
        elif self.debug_mode:
            return "调试模式"
        else:
            return "标准模式"
