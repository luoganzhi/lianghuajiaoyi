try:
    from src.runtime.app_runtime import bootstrap_project_path, setup_logging
except ModuleNotFoundError:
    from runtime.app_runtime import bootstrap_project_path, setup_logging


bootstrap_project_path()
setup_logging()

from src.trading.futures_runner import futures_trading_main


def main():
    """兼容旧的现货入口。"""
    from src.trading.spot_runner import spot_trading_main

    return spot_trading_main()


if __name__ == "__main__":
    # main()
    futures_trading_main()
