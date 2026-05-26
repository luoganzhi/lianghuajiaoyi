import logging
from dataclasses import dataclass

from src.config.config import CONTRACT_CONFIG, IS_SIMULATED, PROXY, TRADING_CONFIG
from src.data.market_data import MarketDataFetcher
from src.execution.okx_executor import OKXExecutor
from src.monitor.trade_monitor import TradeMonitor
from src.trading.environment import get_trading_credentials
from src.trading.strategy_factory import create_futures_strategy
from src.trading.symbols import normalize_futures_symbol


@dataclass
class FuturesComponents:
    market_data: MarketDataFetcher
    account: OKXExecutor
    trade_monitor: TradeMonitor
    strategy: object


def initialize_futures_components(symbol=None, strategy_name=None):
    """初始化合约交易所需组件。"""
    print("正在初始化交易组件...")
    api_key, api_secret, api_password = get_trading_credentials()
    symbol = normalize_futures_symbol(symbol or TRADING_CONFIG.get('symbol') or CONTRACT_CONFIG['default_symbol'])
    strategy_name = strategy_name or TRADING_CONFIG.get('strategy') or 'contract_daily'

    proxy_configs = _proxy_candidates()

    market_data = _connect_market_data(proxy_configs, api_key, api_secret, symbol)
    if not market_data:
        print("❌ 所有代理都无法连接，请检查网络设置")
        return None

    account = _connect_account(proxy_configs, api_key, api_secret, api_password)
    if not account:
        print("❌ 所有代理都无法连接交易账户，请检查API配置")
        return None

    trade_monitor = TradeMonitor()
    strategy = create_futures_strategy(strategy_name)

    # 🎯 启用高精度模式 - 25%保证金止盈
    # strategy.enable_high_precision_mode()

    log_strategy_initialization(strategy)
    print("✅ 所有组件初始化成功！")

    return FuturesComponents(
        market_data=market_data,
        account=account,
        trade_monitor=trade_monitor,
        strategy=strategy,
    )


def _proxy_candidates():
    """返回代理候选：优先使用配置代理，再尝试直连。"""
    candidates = []
    configured_proxy = PROXY.strip() if PROXY else None
    if configured_proxy:
        candidates.append(configured_proxy)
    candidates.append(None)
    return list(dict.fromkeys(candidates))


def _connect_market_data(proxy_configs, api_key, api_secret, symbol):
    for proxy in proxy_configs:
        try:
            print(f"尝试使用代理: {proxy or '无代理'}")
            market_data = MarketDataFetcher(
                exchange_id='okx',
                api_key=api_key,
                secret=api_secret,
                proxy=proxy
            )

            test_ticker = market_data.get_ticker(symbol)
            if test_ticker:
                print(f"✅ 市场数据连接成功 (代理: {proxy or '无代理'})")
                return market_data
        except Exception as exc:
            print(f"❌ 代理 {proxy or '无代理'} 连接失败: {str(exc)[:100]}")

    return None


def _connect_account(proxy_configs, api_key, api_secret, api_password):
    for proxy in proxy_configs:
        try:
            account = OKXExecutor(
                api_key=api_key,
                api_secret=api_secret,
                api_password=api_password,
                proxy=proxy,
                is_simulated=IS_SIMULATED
            )

            test_balance = account.get_balance("USDT")
            if test_balance is not None:
                print(f"✅ 交易账户连接成功 (代理: {proxy or '无代理'})")
                return account
            print(f"❌ 代理 {proxy or '无代理'} 账户余额验证失败")
        except Exception as exc:
            print(f"❌ 代理 {proxy or '无代理'} 账户连接失败: {str(exc)[:100]}")

    return None


def log_strategy_initialization(strategy):
    logging.info("📊 策略初始化完成:")
    logging.info(f"  - 策略类型: {strategy.__class__.__name__}")
    logging.info(f"  - 策略模式: {strategy.get_strategy_mode()}")
    logging.info(f"  - 调试模式: {strategy.debug_mode}")
    logging.info(f"  - 止盈比例: {strategy.take_profit*100:.3f}%")
    logging.info(f"  - 杠杆倍数: {strategy.leverage}x")
    logging.info(f"  - 保证金模式: {strategy.margin_mode}")
    logging.info(f"  - K线间隔: {strategy.kline_interval}")


def print_futures_strategy_config(strategy, leverage):
    """打印合约交易策略配置。"""
    print("=" * 50)
    print("🚀 合约每日交易策略 - 高杠杆版本")
    print("=" * 50)
    print(f"策略类型: {strategy.__class__.__name__}")
    print(f"策略模式: {strategy.get_strategy_mode()}")
    print(f"止盈设置: {strategy.take_profit * 100:.3f}% (基于保证金)")
    print("止损设置: 无止损 (强制平仓: -100%保证金)")
    print(f"杠杆倍数: {leverage}x")
    print(f"保证金模式: {strategy.margin_mode}")
    print(f"交易时间: {strategy.start_hour}:00-{strategy.end_hour}:00")
    print(f"K线间隔: {strategy.kline_interval}")
    print(f"固定保证金: {CONTRACT_CONFIG['fixed_margin']} USDT")
    print(f"调试模式: {'🔧 已启用' if strategy.debug_mode else '📊 生产模式'}")
    if strategy.debug_mode:
        print("🔧 调试参数调整:")
        print(f"  RSI超卖阈值: 30.0 → {strategy.rsi_oversold}")
        print(f"  RSI超买阈值: 70.0 → {strategy.rsi_overbought}")
        print(f"  最小成交量比例: 1.5 → {strategy.min_volume_ratio}")
        print(f"  价格回调比例: 1.0% → {strategy.price_pullback*100:.1f}%")
        print(f"  短期MA: 5 → {strategy.ma_short}")
        print(f"  长期MA: 20 → {strategy.ma_long}")
        print(f"  K线间隔: 15m → {strategy.kline_interval}")
    print("=" * 50)
