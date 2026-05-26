from src.config.config import (
    ALLOW_REAL_TRADING,
    IS_SIMULATED,
    REAL_API_KEY,
    REAL_API_PASSWORD,
    REAL_API_SECRET,
    SIM_API_KEY,
    SIM_API_PASSWORD,
    SIM_API_SECRET,
)


def get_trading_credentials(is_simulated=None):
    """按当前交易环境返回 API 凭证。"""
    if is_simulated is None:
        is_simulated = IS_SIMULATED

    if is_simulated:
        return SIM_API_KEY, SIM_API_SECRET, SIM_API_PASSWORD

    return REAL_API_KEY, REAL_API_SECRET, REAL_API_PASSWORD


def _missing_credential_names(credentials):
    names = ("API_KEY", "API_SECRET", "API_PASSWORD")
    return [name for name, value in zip(names, credentials) if not value]


def validate_trading_environment(
    is_simulated=None,
    allow_real_trading=None,
    credentials=None,
    require_credentials=True,
):
    """校验交易环境，阻止未确认实盘和缺少 API 凭证的启动。"""
    if is_simulated is None:
        is_simulated = IS_SIMULATED
    if allow_real_trading is None:
        allow_real_trading = ALLOW_REAL_TRADING

    if not is_simulated and not allow_real_trading:
        print("❌ 已配置为实盘模式，但未设置 ALLOW_REAL_TRADING=true")
        print("💡 请先使用 IS_SIMULATED=true 完成模拟验证；确需实盘时再显式开启 ALLOW_REAL_TRADING")
        return False

    if require_credentials:
        selected_credentials = credentials
        if selected_credentials is None:
            selected_credentials = get_trading_credentials(is_simulated)

        missing_names = _missing_credential_names(selected_credentials)
        if missing_names:
            env_prefix = "SIM" if is_simulated else "REAL"
            missing_env_names = [f"{env_prefix}_{name}" for name in missing_names]
            print(f"❌ 缺少{'模拟盘' if is_simulated else '实盘'}API配置: {', '.join(missing_env_names)}")
            print("💡 请在 .env 中补齐对应 API_KEY/API_SECRET/API_PASSWORD 后再启动交易")
            return False

    if not is_simulated:
        print("⚠️ 实盘交易已启用，请确认账户、杠杆和仓位配置")

    return True
