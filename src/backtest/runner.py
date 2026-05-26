from pathlib import Path

import pandas as pd

from src.backtest.data_loader import load_backtest_data
from src.backtest.simple_backtester import SimpleBacktester
from src.config.config import CONTRACT_CONFIG, SPOT_CONFIG, TRADING_CONFIG
from src.trading.strategy_factory import create_futures_strategy, create_spot_strategy
from src.trading.symbols import normalize_futures_symbol, normalize_spot_symbol


def run_configured_backtest(args):
    mode = (args.mode or TRADING_CONFIG.get('mode') or 'futures').lower()
    if mode in ('future', 'contract', 'swap'):
        mode = 'futures'
    if mode not in ('spot', 'futures'):
        raise ValueError(f"不支持的交易模式: {mode}")

    strategy_name = args.strategy or TRADING_CONFIG.get('strategy')
    symbol = _resolve_symbol(mode, args.symbol or TRADING_CONFIG.get('symbol'))
    timeframe = args.timeframe or _default_timeframe(mode)

    strategy = _create_strategy(mode, strategy_name)
    data = load_backtest_data(
        data_source=args.data_source,
        symbol=symbol,
        timeframe=timeframe,
        days=args.days,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    signals = _generate_signals(strategy, data)
    backtester = SimpleBacktester(
        initial_cash=args.initial_cash,
        fee=args.fee,
        mode=mode,
        leverage=args.leverage,
        fixed_margin=args.fixed_margin,
        position_fraction=args.position_fraction,
    )
    result = backtester.run_backtest(data, signals, strategy=strategy)

    _print_summary(result, mode, strategy, symbol, timeframe, args.data_source)
    if args.output_dir:
        _save_outputs(result, args.output_dir, mode, strategy, symbol, timeframe)

    return result


def _resolve_symbol(mode, symbol):
    if mode == 'futures':
        return normalize_futures_symbol(symbol or CONTRACT_CONFIG['default_symbol'])
    return normalize_spot_symbol(symbol or SPOT_CONFIG['default_symbol'])


def _default_timeframe(mode):
    if mode == 'futures':
        return CONTRACT_CONFIG.get('kline_interval', '1m')
    return SPOT_CONFIG.get('timeframe', '1m')


def _create_strategy(mode, strategy_name):
    if mode == 'futures':
        return create_futures_strategy(strategy_name)
    return create_spot_strategy(strategy_name)


def _generate_signals(strategy, data):
    generated = strategy.generate_signals(data.copy())
    if isinstance(generated, pd.DataFrame):
        if 'signal' not in generated.columns:
            raise ValueError("策略返回的 DataFrame 缺少 signal 列")
        return generated['signal']
    return pd.Series(list(generated), index=data.index[:len(generated)])


def _print_summary(result, mode, strategy, symbol, timeframe, data_source):
    metrics = result['metrics']
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"模式: {mode}")
    print(f"策略: {strategy.__class__.__name__}")
    print(f"交易对: {symbol}")
    print(f"周期: {timeframe}")
    print(f"数据源: {data_source}")
    print(f"初始资金: {metrics.get('initial_cash', 0):,.2f} USDT")
    print(f"最终权益: {metrics.get('final_equity', 0):,.2f} USDT")
    print(f"总收益率: {metrics.get('total_return', 0) * 100:.2f}%")
    print(f"最大回撤: {metrics.get('max_drawdown', 0) * 100:.2f}%")
    print(f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"交易次数: {metrics.get('total_trades', 0)}")
    print(f"胜率: {metrics.get('win_rate', 0) * 100:.2f}%")
    print(f"盈利因子: {metrics.get('profit_factor', 0):.2f}")
    print(f"策略评分: {result.get('score', 0):.2f} / 100")


def _save_outputs(result, output_dir, mode, strategy, symbol, timeframe):
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    safe_symbol = symbol.replace('/', '-').replace(':', '-')
    prefix = f"{mode}_{strategy.__class__.__name__}_{safe_symbol}_{timeframe}"

    equity_file = path / f"{prefix}_equity.csv"
    trades_file = path / f"{prefix}_trades.csv"
    metrics_file = path / f"{prefix}_metrics.csv"

    result['equity_curve'].to_csv(equity_file)
    result['trades_df'].to_csv(trades_file, index=False)
    metrics = dict(result['metrics'])
    metrics['score'] = result.get('score', 0)
    pd.DataFrame([metrics]).to_csv(metrics_file, index=False)

    print("\n已保存回测输出:")
    print(f"- {equity_file}")
    print(f"- {trades_file}")
    print(f"- {metrics_file}")
