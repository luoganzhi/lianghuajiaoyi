from src.config.config import CONTRACT_CONFIG
from src.strategies.contract_daily_trading_strategy import ContractDailyTradingStrategy
from src.strategies.daily_trading_strategy import DailyTradingStrategy
from src.strategies.ma_curve_strategy import MACurveStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.simple_ma_strategy import SimpleMAStrategy
from src.strategies.trend_following_strategy import TrendFollowingStrategy


SPOT_STRATEGIES = {
    'daily': DailyTradingStrategy,
    'daily_trading': DailyTradingStrategy,
    'ma': SimpleMAStrategy,
    'simple_ma': SimpleMAStrategy,
    'rsi': RSIStrategy,
    'ma_curve': MACurveStrategy,
    'trend': TrendFollowingStrategy,
    'trend_following': TrendFollowingStrategy,
}

FUTURES_STRATEGIES = {
    'contract_daily': ContractDailyTradingStrategy,
}


def create_spot_strategy(strategy_name: str):
    """Create a strategy compatible with the spot trading loop."""
    normalized_name = (strategy_name or 'daily').lower()
    strategy_class = SPOT_STRATEGIES.get(normalized_name)
    if strategy_class is None:
        supported = ', '.join(sorted(SPOT_STRATEGIES))
        raise ValueError(f"不支持的现货策略: {strategy_name}. 支持: {supported}")

    if strategy_class is DailyTradingStrategy:
        return DailyTradingStrategy(
            take_profit=0.01,
            stop_loss=0.005,
            rsi_period=21,
            rsi_oversold=30.0,
            ma_short=5,
            ma_long=20,
            start_hour=0,
            end_hour=24,
            min_volume_ratio=1.2,
            price_pullback=0.01,
            atr_period=14,
            atr_multiplier=1.5,
            use_dynamic_stop=False,
            use_macd=False,
            avoid_hours=[],
            best_hours=[],
        )

    return strategy_class()


def create_futures_strategy(strategy_name: str):
    """Create a strategy compatible with the futures trading loop."""
    normalized_name = (strategy_name or 'contract_daily').lower()
    strategy_class = FUTURES_STRATEGIES.get(normalized_name)
    if strategy_class is None:
        supported = ', '.join(sorted(FUTURES_STRATEGIES))
        raise ValueError(f"不支持的合约策略: {strategy_name}. 支持: {supported}")

    return strategy_class(
        debug_mode=CONTRACT_CONFIG.get('debug_mode', False),
        kline_interval=CONTRACT_CONFIG.get('kline_interval', '1m'),
    )
