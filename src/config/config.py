import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 交易所配置
EXCHANGE_CONFIG = {
    'binance': {
        'api_key': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET'),
    },
    'okex': {
        'api_key': os.getenv('OKEX_API_KEY'),
        'secret': os.getenv('OKEX_SECRET'),
    }
}

# 风控配置
RISK_CONFIG = {
    'position': {
        'max_size': 0.9,        # 最大仓位比例
        'min_size': 0.01       # 最小仓位比例
    },
    'stop_loss': {
        'fixed_pct': 0.02,     # 固定止损比例
        'trailing_pct': 0.01   # 追踪止损比例
    },
    'take_profit': {
        'fixed_pct': 0.05      # 固定止盈比例
    },
    'risk_limits': {
        'max_drawdown': 0.1,   # 最大回撤限制
        'daily_loss': 1000,    # 每日最大亏损
        'max_positions': 50,    # 最大同时持仓数
        'max_daily_trades': 50  # 每日最大交易次数
    }
}

# 交易配置
TRADING_CONFIG = {
    'default_symbol': 'BTC/USDT',
    'default_timeframe': '1m',
    'max_position_size': RISK_CONFIG['position']['max_size'],  # 使用风控配置
    'stop_loss_pct': RISK_CONFIG['stop_loss']['fixed_pct'],   # 使用风控配置
    'take_profit_pct': RISK_CONFIG['take_profit']['fixed_pct'] # 使用风控配置
}

# 数据存储配置
DATA_CONFIG = {
    'data_dir': 'data',
    'ohlcv_dir': 'data/ohlcv',
    'trades_dir': 'data/trades',
}

# 日志配置
LOG_CONFIG = {
    'log_dir': 'logs',
    'log_level': 'INFO',
}

# 监控模块配置
MONITOR_CONFIG = {
    'log_dir': 'logs',
    'report_dir': 'reports',
    'template_dir': 'templates',
    'report_schedule': {
        'daily_report': '23:59',
        'performance_report': '23:59',
        'metrics_reset': '00:00'
    },
    'alert_thresholds': {
        'drawdown': RISK_CONFIG['risk_limits']['max_drawdown'],    # 使用风控配置
        'loss_limit': RISK_CONFIG['risk_limits']['daily_loss'],    # 使用风控配置
        'profit_target': 500,   # 单日盈利目标
        'position_limit': RISK_CONFIG['position']['max_size']  # 直接引用风控配置
    }
}

# 交易环境切换 - 从环境变量读取；默认使用模拟盘，避免未配置 .env 时误连实盘
IS_SIMULATED = os.getenv('IS_SIMULATED', 'true').lower() == 'true'  # True=模拟盘, False=实盘
ALLOW_REAL_TRADING = os.getenv('ALLOW_REAL_TRADING', 'false').lower() == 'true'  # 实盘二次确认开关

# 模拟盘API - 从环境变量读取
SIM_API_KEY = os.getenv('SIM_API_KEY')
SIM_API_SECRET = os.getenv('SIM_API_SECRET')
SIM_API_PASSWORD = os.getenv('SIM_API_PASSWORD')

# 实盘API - 从环境变量读取
REAL_API_KEY = os.getenv('REAL_API_KEY')
REAL_API_SECRET = os.getenv('REAL_API_SECRET')
REAL_API_PASSWORD = os.getenv('REAL_API_PASSWORD')

# 代理设置 - 从环境变量读取；留空时自动尝试直连
PROXY = os.getenv('PROXY')

# 现货交易配置
SPOT_CONFIG = {
    'default_symbol': 'BTC/USDT',
    'timeframe': '1m',
    'take_profit_pct': 0.01,  # 现货止盈比例：1%
    'stop_loss_pct': 0.005,   # 现货止损比例：0.5%
}

# 合约交易配置
CONTRACT_CONFIG = {
    'fixed_margin': 10,   # 固定保证金金额（USDT）
    'leverage': 50,      # 杠杆倍数
    'kline_interval': '1m',  # K线周期：1m(1分钟), 5m(5分钟), 15m(15分钟), 1h(1小时), 4h(4小时), 1d(1天)
    'take_profit_pct': 0.1,  # 保证金止盈比例：10%
    'debug_mode': os.getenv('CONTRACT_DEBUG_MODE', 'false').lower() == 'true',
}
