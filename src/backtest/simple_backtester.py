from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.backtest.base_backtester import BaseBacktester
from src.evaluation.strategy_scorer import score_strategy
from src.strategies.signal import normalize_signal_series


@dataclass
class BacktestConfig:
    mode: str = 'spot'
    initial_cash: float = 100000.0
    fee: float = 0.001
    leverage: float = 1.0
    fixed_margin: float = 100.0
    position_fraction: float = 1.0


class SimpleBacktester(BaseBacktester):
    """Small long/short backtester used by examples and the unified CLI."""

    def __init__(
        self,
        initial_cash=100000,
        fee=0.001,
        mode='spot',
        leverage=1.0,
        fixed_margin=100.0,
        position_fraction=1.0,
    ):
        super().__init__(initial_cash=initial_cash)
        self.config = BacktestConfig(
            mode=mode,
            initial_cash=float(initial_cash),
            fee=float(fee),
            leverage=float(leverage),
            fixed_margin=float(fixed_margin),
            position_fraction=float(position_fraction),
        )

    def run_backtest(self, data: pd.DataFrame, signals, strategy=None) -> dict:
        data = self._prepare_data(data)
        signal_frame = self._prepare_signals(signals, data.index)

        cash = self.config.initial_cash
        position_size = 0.0
        position_side: Optional[str] = None
        entry_price = 0.0
        entry_time = None
        margin_used = 0.0
        trades = []
        equity_rows = []

        for timestamp, row in data.iterrows():
            price = float(row['close'])
            signal_row = signal_frame.loc[timestamp]
            signal = int(signal_row['signal'])

            exit_reason = None
            if position_side:
                exit_reason = self._exit_reason(strategy, position_side, entry_price, price, signal)

            if position_side and exit_reason:
                pnl = self._position_pnl(position_side, position_size, entry_price, price)
                exit_value = abs(position_size) * price
                fee = exit_value * self.config.fee
                if self.config.mode == 'futures':
                    cash += margin_used + pnl - fee
                else:
                    cash += exit_value - fee

                trades.append({
                    'timestamp': timestamp,
                    'type': 'sell' if position_side == 'long' else 'buy',
                    'entry_time': entry_time,
                    'exit_time': timestamp,
                    'side': position_side,
                    'price': price,
                    'entry_price': entry_price,
                    'exit_price': price,
                    'size': abs(position_size),
                    'value': exit_value,
                    'pnl': pnl - fee,
                    'pnl_pct': self._trade_return(position_side, entry_price, price) * 100,
                    'fee': fee,
                    'equity': cash,
                    'buy_price': entry_price,
                    'buy_timestamp': entry_time,
                    'return_pct': self._trade_return(position_side, entry_price, price),
                    'exit_reason': exit_reason,
                })
                self._notify_exit(strategy, position_side, price, abs(position_size), pnl - fee)

                position_size = 0.0
                position_side = None
                entry_price = 0.0
                entry_time = None
                margin_used = 0.0

            if not position_side and signal in (1, -1):
                opened = self._open_position(cash, price, signal)
                if opened:
                    margin_used, position_size, entry_fee = opened
                    cash -= margin_used + entry_fee
                    position_side = 'long' if signal == 1 else 'short'
                    entry_price = price
                    entry_time = timestamp
                    self._notify_entry(strategy, position_side, price, abs(position_size), timestamp)

            equity = cash
            unrealized_pnl = 0.0
            if position_side:
                unrealized_pnl = self._position_pnl(position_side, position_size, entry_price, price)
                if self.config.mode == 'futures':
                    equity += margin_used + unrealized_pnl
                else:
                    equity += abs(position_size) * price

            equity_rows.append({
                'timestamp': timestamp,
                'equity': equity,
                'cash': cash,
                'price': price,
                'position_side': position_side or '',
                'position_size': abs(position_size),
                'unrealized_pnl': unrealized_pnl,
                'signal': signal,
                'signal_action': signal_row['action'],
                'signal_side': signal_row['side'],
                'signal_reason': signal_row['reason'],
                'signal_confidence': signal_row['confidence'],
            })

        if position_side:
            last_time = data.index[-1]
            last_price = float(data.iloc[-1]['close'])
            pnl = self._position_pnl(position_side, position_size, entry_price, last_price)
            exit_value = abs(position_size) * last_price
            fee = exit_value * self.config.fee
            if self.config.mode == 'futures':
                cash += margin_used + pnl - fee
            else:
                cash += exit_value - fee
            trades.append({
                'timestamp': last_time,
                'type': 'sell' if position_side == 'long' else 'buy',
                'entry_time': entry_time,
                'exit_time': last_time,
                'side': position_side,
                'price': last_price,
                'entry_price': entry_price,
                'exit_price': last_price,
                'size': abs(position_size),
                'value': exit_value,
                'pnl': pnl - fee,
                'pnl_pct': self._trade_return(position_side, entry_price, last_price) * 100,
                'fee': fee,
                'equity': cash,
                'buy_price': entry_price,
                'buy_timestamp': entry_time,
                'return_pct': self._trade_return(position_side, entry_price, last_price),
                'exit_reason': 'end_of_data',
            })
            self._notify_exit(strategy, position_side, last_price, abs(position_size), pnl - fee)
            if equity_rows:
                equity_rows[-1].update({
                    'equity': cash,
                    'cash': cash,
                    'position_side': '',
                    'position_size': 0.0,
                    'unrealized_pnl': 0.0,
                })

        equity_curve = pd.DataFrame(equity_rows).set_index('timestamp')
        trades_df = pd.DataFrame(trades)
        metrics = self._metrics(equity_curve, trades_df)
        score, score_components = score_strategy({
            'total_return': metrics.get('total_return', 0.0),
            'max_drawdown': metrics.get('max_drawdown', 0.0),
            'sharpe': metrics.get('sharpe_ratio', 0.0),
        })

        return {
            'metrics': metrics,
            'total_return': metrics.get('total_return', 0.0),
            'max_drawdown': metrics.get('max_drawdown', 0.0),
            'sharpe': metrics.get('sharpe_ratio', 0.0),
            'score': score,
            'score_components': score_components,
            'trades': trades,
            'trades_df': trades_df,
            'equity_curve': equity_curve,
        }

    def _prepare_data(self, data):
        required = {'open', 'high', 'low', 'close', 'volume'}
        missing = required - set(data.columns)
        if missing:
            raise ValueError(f"回测数据缺少必要列: {sorted(missing)}")

        result = data.copy().dropna(subset=list(required))
        if 'timestamp' in result.columns:
            result['timestamp'] = pd.to_datetime(result['timestamp'])
            result = result.set_index('timestamp')
        if not isinstance(result.index, pd.DatetimeIndex):
            result.index = pd.to_datetime(result.index)
        return result.sort_index()

    def _prepare_signals(self, signals, index):
        return normalize_signal_series(signals, index)

    def _open_position(self, cash, price, signal):
        if self.config.mode == 'futures':
            margin = min(self.config.fixed_margin, cash)
            if margin <= 0:
                return None
            notional = margin * self.config.leverage
        else:
            margin = cash * self.config.position_fraction
            if margin <= 0:
                return None
            notional = margin

        size = notional / price
        if signal == -1:
            size = -size
        fee = notional * self.config.fee
        if margin + fee > cash:
            margin = max(cash / (1 + self.config.fee), 0)
            notional = margin * (self.config.leverage if self.config.mode == 'futures' else 1)
            size = notional / price
            if signal == -1:
                size = -size
            fee = notional * self.config.fee
        return margin, size, fee

    def _exit_reason(self, strategy, position_side, entry_price, price, signal):
        if position_side == 'long' and signal == -1:
            return 'opposite_signal'
        if position_side == 'short' and signal == 1:
            return 'opposite_signal'

        take_profit = getattr(strategy, 'take_profit', None)
        if take_profit is not None and self._trade_return(position_side, entry_price, price) >= take_profit:
            return 'take_profit'

        stop_loss = getattr(strategy, 'stop_loss', None)
        if stop_loss is not None and self._trade_return(position_side, entry_price, price) <= -stop_loss:
            return 'stop_loss'

        return None

    def _position_pnl(self, side, size, entry_price, price):
        quantity = abs(size)
        if side == 'long':
            return (price - entry_price) * quantity
        return (entry_price - price) * quantity

    def _trade_return(self, side, entry_price, price):
        if entry_price <= 0:
            return 0.0
        if side == 'long':
            return (price - entry_price) / entry_price
        return (entry_price - price) / entry_price

    def _notify_entry(self, strategy, side, price, size, timestamp):
        if strategy and hasattr(strategy, 'on_position_entry'):
            strategy.on_position_entry('buy' if side == 'long' else 'sell', price, size, timestamp)

    def _notify_exit(self, strategy, side, price, size, pnl):
        if strategy and hasattr(strategy, 'on_position_exit'):
            strategy.on_position_exit('sell' if side == 'long' else 'buy', price, size, pnl)

    def _metrics(self, equity_curve, trades_df):
        if equity_curve.empty:
            return {}

        initial = self.config.initial_cash
        final = float(equity_curve['equity'].iloc[-1])
        returns = equity_curve['equity'].pct_change().dropna()
        rolling_peak = equity_curve['equity'].cummax()
        drawdown = (rolling_peak - equity_curve['equity']) / rolling_peak

        total_trades = int(len(trades_df))
        winning = int((trades_df['pnl'] > 0).sum()) if total_trades else 0
        losing = int((trades_df['pnl'] < 0).sum()) if total_trades else 0
        gross_profit = float(trades_df.loc[trades_df['pnl'] > 0, 'pnl'].sum()) if total_trades else 0.0
        gross_loss = float(trades_df.loc[trades_df['pnl'] < 0, 'pnl'].sum()) if total_trades else 0.0

        return {
            'initial_cash': initial,
            'final_equity': final,
            'total_return': (final - initial) / initial if initial else 0.0,
            'max_drawdown': float(drawdown.max()) if not drawdown.empty else 0.0,
            'sharpe_ratio': float((returns.mean() / returns.std()) * (252 ** 0.5)) if len(returns) > 1 and returns.std() else 0.0,
            'total_trades': total_trades,
            'winning_trades': winning,
            'losing_trades': losing,
            'win_rate': winning / total_trades if total_trades else 0.0,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': abs(gross_profit / gross_loss) if gross_loss else 0.0,
        }
