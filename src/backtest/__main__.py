import argparse

from src.backtest.runner import run_configured_backtest
from src.config.config import CONTRACT_CONFIG


def build_parser():
    parser = argparse.ArgumentParser(description="统一回测入口")
    parser.add_argument('--mode', choices=['futures', 'spot'], help='交易模式；默认读取 TRADING_MODE')
    parser.add_argument('--strategy', help='策略名；默认读取 STRATEGY，留空按模式选择默认策略')
    parser.add_argument('--symbol', help='交易对；默认读取 SYMBOL，留空按模式选择默认交易对')
    parser.add_argument('--timeframe', help='K线周期，例如 1m, 15m, 1h')
    parser.add_argument('--data-source', choices=['mock', 'okx'], default='mock', help='数据源，默认 mock')
    parser.add_argument('--days', type=int, default=30, help='回测天数')
    parser.add_argument('--start-date', help='开始日期 YYYY-MM-DD；仅 okx 数据源使用')
    parser.add_argument('--end-date', help='结束日期 YYYY-MM-DD；仅 okx 数据源使用')
    parser.add_argument('--initial-cash', type=float, default=100000.0, help='初始资金')
    parser.add_argument('--fee', type=float, default=0.001, help='单边手续费率')
    parser.add_argument('--leverage', type=float, default=CONTRACT_CONFIG.get('leverage', 1), help='合约杠杆')
    parser.add_argument('--fixed-margin', type=float, default=CONTRACT_CONFIG.get('fixed_margin', 100), help='合约每次开仓保证金')
    parser.add_argument('--position-fraction', type=float, default=1.0, help='现货每次开仓资金比例')
    parser.add_argument('--output-dir', default='reports/backtests', help='输出目录；为空字符串则不保存')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.output_dir == '':
        args.output_dir = None
    run_configured_backtest(args)


if __name__ == '__main__':
    main()
