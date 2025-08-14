import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from risk.risk_manager import RiskManager
from risk.position_manager import PositionManager
from risk.stop_manager import StopManager
from risk.risk_calculator import RiskCalculator
from risk.risk_monitor import RiskMonitor
from data.market_data import MarketDataFetcher
from execution.okx_executor import OKXExecutor
from config.config import PROXY, IS_SIMULATED, SIM_API_KEY, SIM_API_SECRET, SIM_API_PASSWORD, REAL_API_KEY, REAL_API_SECRET, REAL_API_PASSWORD

def test_risk_manager(market_data, account):
    print("\n测试风险管理器...")

    # 初始化风险管理器,设置各项风控参数:
    # max_position_size: 最大仓位比例,占总资金的0.9(90%)
    # max_drawdown: 最大回撤限制,允许的最大回撤为0.1(10%) 
    # stop_loss_pct: 止损百分比,亏损达到0.02(2%)时止损
    # take_profit_pct: 止盈百分比,盈利达到0.05(5%)时止盈
    # max_daily_trades: 每日最大交易次数限制为5次
    risk_manager = RiskManager(
        max_position_size=0.9,  # 最大仓位比例90%
        max_drawdown=0.1,       # 最大回撤10% - 账户总资金的最大亏损幅度,达到后暂停新开仓,已有仓位继续持有
        stop_loss_pct=0.02,     # 止损2% - 单笔交易的止损线,达到即平仓
        take_profit_pct=0.05,   # 止盈5% - 单笔交易的止盈线,达到即平仓  
        max_daily_trades=50      # 每日最大交易次数50次
    )

    symbol = "BTC-USDT"
    # 用账户API获取真实资金
    total_capital = float(account.get_balance("USDT"))  # 假设主币种为USDT
    # 用行情API获取真实价格
    current_price = float(market_data.get_ticker(symbol)['last'])

    # 计算一个合理的测试仓位（比如20%资金买入）
    valid_size = 0.2 * total_capital / current_price
    is_valid = risk_manager.check_position_limit(symbol, valid_size, total_capital)
    print(f"正常仓位检查: {'通过' if is_valid else '未通过'}")

    # 计算超大仓位（比如40%资金买入）
    invalid_size = 0.4 * total_capital / current_price
    is_valid = risk_manager.check_position_limit(symbol, invalid_size, total_capital)
    print(f"过大仓位检查: {'未通过' if not is_valid else '异常'}")

def test_position_manager(market_data, account):
    print("\n测试仓位管理器...")

    position_manager = PositionManager(
        market_data_fetcher=market_data,
        account_manager=account,
        max_leverage=1.0,
        position_sizing_method="fixed_fraction",
        risk_per_trade=0.02
    )

    symbol = "BTC-USDT"
    entry_price = float(market_data.get_ticker(symbol)['last'])
    stop_loss = entry_price * 0.98  # 2%止损

    # 计算建议仓位
    position_size = position_manager.calculate_position_size(symbol, stop_loss)
    print(f"建议仓位大小: {position_size:.4f} BTC")

    # 添加持仓
    position_manager.add_position(symbol, position_size, entry_price, stop_loss, take_profit=entry_price*1.05)
    print("已添加持仓。")

    # 更新持仓盈亏
    position_manager.update_position(symbol)
    metrics = position_manager.get_position_metrics()
    print(f"持仓指标: {metrics}")

    # 平仓
    realized_pnl = position_manager.close_position(symbol)
    print(f"平仓实现盈亏: {realized_pnl}")

def test_stop_manager(market_data, account):
    print("\n测试止损止盈管理器...")

    # 初始化止损止盈管理器
    stop_manager = StopManager(
        default_stop_loss_pct=0.02,
        default_take_profit_pct=0.05,
        trailing_stop_pct=0.01
    )

    symbol = "BTC-USDT"
    # 用行情API获取真实价格
    entry_price = float(market_data.get_ticker(symbol)['last'])
    # 用账户API或仓位管理器获取建议持仓量（这里举例用20%资金买入）
    total_capital = float(account.get_balance("USDT"))
    position_size = 0.2 * total_capital / entry_price

    # 添加止损止盈订单
    stop_manager.add_stop_orders(
        symbol=symbol,
        entry_price=entry_price,
        position_size=position_size
    )

    # 用行情API获取最新价格
    current_price = float(market_data.get_ticker(symbol)['last'])
    result = stop_manager.update_stops(symbol, current_price)
    print(f"止损止盈检查结果: {result}")

    metrics = stop_manager.get_stop_metrics(symbol)
    print(f"止损止盈指标: {metrics}")

def test_risk_calculator(account):
    print("\n测试风险计算器...")

    calculator = RiskCalculator()

    # 获取真实历史成交记录（假设OKXExecutor有get_orders方法）
    symbol = "BTC-USDT"
    orders = account.get_orders(symbol, status="closed")  # 获取已成交订单

    for order in orders:
        # 这里只是示例，需根据你的订单结构调整字段
        entry_price = float(order["average"]) if "average" in order else float(order["price"])
        exit_price = float(order["filled_price"]) if "filled_price" in order else float(order["price"])
        position_size = float(order["amount"])
        entry_time = datetime.fromtimestamp(order["timestamp"] / 1000)
        exit_time = datetime.fromtimestamp(order["lastTradeTimestamp"] / 1000) if "lastTradeTimestamp" in order else entry_time
        trade_type = order["side"]  # "buy" or "sell"

        calculator.add_trade(
            symbol=symbol,
            entry_price=entry_price,
            exit_price=exit_price,
            position_size=position_size,
            entry_time=entry_time,
            exit_time=exit_time,
            trade_type=trade_type
        )

    # 计算风险指标
    metrics = calculator.get_risk_metrics(lookback_days=7)
    print(f"风险指标: {metrics}")

def test_risk_monitor(market_data, account):
    print("\n测试风险监控器...")

    # 初始化风险监控器
    monitor = RiskMonitor(
        capital_threshold=0.1,
        daily_loss_limit=1000,
        max_positions=5,
        volatility_threshold=0.03
    )

    symbol = "BTC-USDT"
    # 获取真实资金
    current_capital = float(account.get_balance("USDT"))
    monitor.update_capital(current_capital)

    # 获取真实持仓（假设OKXExecutor有get_position方法，返回持仓信息）
    position_info = account.get_position(symbol)
    if position_info and position_info.get("contracts", 0) > 0:
        size = float(position_info["contracts"])
        entry_price = float(position_info["entryPrice"])
        current_price = float(market_data.get_ticker(symbol)['last'])
        monitor.update_position(
            symbol=symbol,
            size=size,
            entry_price=entry_price,
            current_price=current_price
        )

    # 获取最新价格序列（如最近6个1分钟K线收盘价）
    ohlcv = market_data.get_ohlcv(symbol, timeframe="1m", limit=6)
    for price in ohlcv["close"]:
        monitor.update_price(symbol, price)

    # 获取监控指标
    metrics = monitor.get_monitoring_metrics()
    print(f"监控指标: {metrics}")

def main():
    print("开始测试风险控制模块...")
    
    # 选择API信息
    if IS_SIMULATED:
        api_key = SIM_API_KEY
        api_secret = SIM_API_SECRET
        api_password = SIM_API_PASSWORD
    else:
        api_key = REAL_API_KEY
        api_secret = REAL_API_SECRET
        api_password = REAL_API_PASSWORD

    market_data = MarketDataFetcher(exchange_id='okx', proxy=PROXY)
    account = OKXExecutor(api_key, api_secret, api_password, proxy=PROXY, is_simulated=IS_SIMULATED)

    test_risk_manager(market_data, account)
    test_position_manager(market_data, account)
    test_stop_manager(market_data, account)
    test_risk_calculator(account)
    test_risk_monitor(market_data, account)
    
    print("\n风险控制模块测试完成!")

if __name__ == "__main__":
    main()