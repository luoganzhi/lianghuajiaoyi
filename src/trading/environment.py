from src.config.config import ALLOW_REAL_TRADING, IS_SIMULATED


def validate_trading_environment():
    """阻止未显式确认的实盘交易启动。"""
    if IS_SIMULATED:
        return True

    if ALLOW_REAL_TRADING:
        print("⚠️ 实盘交易已启用，请确认账户、杠杆和仓位配置")
        return True

    print("❌ 已配置为实盘模式，但未设置 ALLOW_REAL_TRADING=true")
    print("💡 请先使用 IS_SIMULATED=true 完成模拟验证；确需实盘时再显式开启 ALLOW_REAL_TRADING")
    return False
