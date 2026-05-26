try:
    from src.runtime.app_runtime import bootstrap_project_path, setup_logging
except ModuleNotFoundError:
    from runtime.app_runtime import bootstrap_project_path, setup_logging


bootstrap_project_path()
setup_logging()

from src.config.config import TRADING_CONFIG
from src.trading.futures_runner import futures_trading_main


def main(mode=None):
    """按配置启动交易模式。"""
    trading_mode = (mode or TRADING_CONFIG.get('mode') or 'futures').lower()
    if trading_mode in ('futures', 'future', 'contract', 'swap'):
        return futures_trading_main()

    if trading_mode == 'spot':
        return spot_main()

    raise ValueError("不支持的交易模式: "
                     f"{trading_mode}. 支持: futures, spot")


def spot_main():
    """兼容旧的现货入口。"""
    from src.trading.spot_runner import spot_trading_main

    return spot_trading_main()


if __name__ == "__main__":
    main()
