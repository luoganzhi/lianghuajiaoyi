import logging
import time
from dataclasses import dataclass
from datetime import datetime

from src.config.config import CONTRACT_CONFIG
from src.trading.futures_helpers import get_futures_position


@dataclass
class FuturesSignalResult:
    price: float = 0
    current_position: dict = None
    in_position: bool = False
    signal: int = 0
    last_signal: int = 0
    last_signal_time: float = 0
    skip_cycle: bool = False


def generate_no_position_signal(
    market_data,
    account,
    symbol,
    strategy,
    in_position,
    last_signal,
    last_signal_time,
    signal_cooldown,
    interval,
):
    """无持仓时获取行情、同步持仓并生成开仓信号。"""
    price = _fetch_current_price(market_data, symbol, interval)
    if price is None:
        return FuturesSignalResult(skip_cycle=True)

    current_position, in_position, skip_cycle = _sync_current_position(
        account,
        symbol,
        strategy,
        price,
        in_position,
        interval,
    )
    if skip_cycle:
        return FuturesSignalResult(skip_cycle=True)

    signal, last_signal, last_signal_time = _generate_entry_signal(
        market_data,
        symbol,
        strategy,
        price,
        last_signal,
        last_signal_time,
        signal_cooldown,
    )

    return FuturesSignalResult(
        price=price,
        current_position=current_position,
        in_position=in_position,
        signal=signal,
        last_signal=last_signal,
        last_signal_time=last_signal_time,
    )


def log_generated_signal(signal, price, loop_count):
    if signal != 0:
        signal_type = "做多" if signal == 1 else "做空"
        logging.info(f"🎯 合约交易信号生成 - 类型: {signal_type}, 价格: {price:.2f}, 时间: {datetime.now().strftime('%H:%M:%S')}")
    elif loop_count % 100 == 0:
        logging.debug(f"📊 合约交易无信号 - 价格: {price:.2f}, 时间: {datetime.now().strftime('%H:%M:%S')}")


def _fetch_current_price(market_data, symbol, interval):
    try:
        ticker_data = market_data.get_ticker(symbol)
        if not ticker_data or 'last' not in ticker_data:
            print("⚠️ 获取行情数据失败，跳过本次循环")
            logging.warning("⚠️ 获取行情数据失败 - 数据为空或格式错误")
            time.sleep(interval)
            return None
        return float(ticker_data['last'])
    except Exception as exc:
        print(f"⚠️ 获取行情数据失败: {str(exc)[:100]}，跳过本次循环")
        logging.error(f"⚠️ 获取行情数据异常 - 错误: {str(exc)}")
        time.sleep(interval)
        return None


def _sync_current_position(account, symbol, strategy, price, in_position, interval):
    try:
        current_position = get_futures_position(account, symbol, strategy)
        previous_in_position = in_position
        in_position = current_position is not None

        if previous_in_position and not in_position:
            print("⚠️ 检测到仓位被强平")
            strategy.on_position_exit('unknown', price, 0, 0)
            print("✅ 仓位强平处理完成")
            print(f"🔍 策略持仓状态: {strategy.current_position}")

        return current_position, in_position, False
    except Exception as exc:
        print(f"⚠️ 获取合约持仓失败: {str(exc)[:100]}，跳过本次循环")
        logging.error(f"⚠️ 获取合约持仓异常 - 错误: {str(exc)}")
        time.sleep(interval)
        return None, in_position, True


def _generate_entry_signal(market_data, symbol, strategy, price, last_signal, last_signal_time, signal_cooldown):
    ohlcv_symbol = symbol.replace('-SWAP', '') if symbol.endswith('-SWAP') else symbol
    ohlcv_data = market_data.get_ohlcv(ohlcv_symbol, timeframe=CONTRACT_CONFIG.get('kline_interval', '1m'))
    raw_signal = strategy.generate_signal(ohlcv_data)

    logging.info("🔍 策略信号生成详情:")
    logging.info(f"  - 原始信号: {raw_signal}")
    logging.info(f"  - 信号类型: {'做多' if raw_signal == 1 else '做空' if raw_signal == -1 else '平仓' if raw_signal == 0 else '未知'}")
    logging.info(f"  - 当前价格: {price:.2f} USDT")
    logging.info(f"  - 策略类型: {strategy.__class__.__name__}")
    logging.info(f"  - 调试模式: {strategy.debug_mode}")
    logging.info(f"  - 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if raw_signal == 0:
        signal = 0
        print(f"ℹ️ 策略生成平仓信号，已禁用 (raw_signal={raw_signal})")
        logging.info(f"ℹ️ 策略生成平仓信号，已禁用 (raw_signal={raw_signal})")
    else:
        signal = raw_signal
        logging.info(f"✅ 策略信号有效，允许执行: {signal}")

    current_time = time.time()
    if signal != 0:
        if signal == last_signal and current_time - last_signal_time < signal_cooldown:
            print(f"⚠️ 重复信号被忽略: {signal} (冷却中)")
            signal = 0
        else:
            last_signal = signal
            last_signal_time = current_time

    if len(ohlcv_data) > 0:
        current_price = ohlcv_data['close'].iloc[-1]
        print(f"🔍 策略计算: 价格={current_price:.2f}, 信号={signal}, 时间={datetime.now().strftime('%H:%M:%S')}")

    return signal, last_signal, last_signal_time
