# 数字货币量化交易系统 - LSTM策略框架

## 项目概述
这是一个基于Python的数字货币量化交易系统，核心使用LSTM深度学习模型进行市场预测和交易决策。系统支持回测和实盘交易，并包含完整的风险控制和监控功能。

## 最新更新
- 优化LSTM模型结构：简化网络层数，改进损失函数
- 调整数据周期：从1h改为4h，优化预测效果
- 环境配置修复：解决NumPy版本冲突，优化TensorFlow加载
- 参数优化：缩短回测期间，优化序列长度和预测长度

## 项目结构
```
lianghuajiaoyi/
├── src/                    # 源代码目录
│   ├── models/            # 模型实现
│   │   ├── lstm_base.py      # LSTM基础模型
│   │   └── lstm_improved.py  # 改进版LSTM模型
│   ├── data/              # 数据处理模块
│   │   ├── market_data.py    # 市场数据获取
│   │   └── preprocessor.py   # 数据预处理
│   ├── backtest/          # 回测模块
│   │   ├── engine.py         # 回测引擎
│   │   └── analyzer.py       # 回测分析
│   ├── trading/           # 交易模块
│   │   ├── executor.py       # 交易执行
│   │   └── position.py       # 仓位管理
│   ├── risk/              # 风险控制
│   └── utils/             # 工具函数
├── models/                # 模型存储
├── data/                 # 数据存储
├── reports/              # 回测报告
└── logs/                 # 日志文件
```

## 模块功能与开发状态

### 1. 核心模型模块
| 功能 | 状态 | 说明 |
|-----|------|-----|
| LSTM基础模型 | ✅ | 完成基础预测功能 |
| 模型优化 | ✅ | 完成网络结构简化 |
| Huber Loss实现 | ✅ | 改进损失函数 |
| 参数自动调优 | 🚧 | 开发中 |

### 2. 数据处理模块
| 功能 | 状态 | 说明 |
|-----|------|-----|
| 4h周期数据获取 | ✅ | 已完成 |
| 实时数据接入 | ✅ | 已完成 |
| 数据预处理流程 | ✅ | 已完成 |
| 特征工程 | 🚧 | 优化中 |

### 3. 回测系统
| 功能 | 状态 | 说明 |
|-----|------|-----|
| 基础回测框架 | ✅ | 已完成 |
| 性能分析 | ✅ | 已完成 |
| 可视化报告 | ✅ | 已完成 |
| 多周期回测 | 🚧 | 开发中 |

### 4. 实盘交易
| 功能 | 状态 | 说明 |
|-----|------|-----|
| 交易信号生成 | ✅ | 已完成 |
| 订单执行 | ✅ | 已完成 |
| 仓位管理 | 🚧 | 优化中 |
| 风险控制 | 🚧 | 开发中 |

## 环境配置

### 依赖要求
```
numpy==1.21.0  # 降级解决兼容性问题
tensorflow==2.10.0
pandas>=1.3.0
scikit-learn>=0.24.2
matplotlib>=3.4.0
```

### 安装步骤
```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt
```

## 使用说明

### 1. 回测系统
```python
from src.backtest.engine import LSTMBacktester

config = {
    'symbol': 'BTC/USDT',
    'timeframe': '4h',
    'start_date': '2023-10-01',
    'end_date': '2023-12-31',
    'sequence_length': 12,
    'prediction_length': 3
}

backtester = LSTMBacktester(config)
results = backtester.run()
```

### 2. 实盘交易
```python
from src.trading.executor import LSTMTrader

trader = LSTMTrader(
    symbol='BTC/USDT',
    timeframe='4h',
    model_path='models/lstm_latest'
)
trader.run()
```

## 开发进展

### 已完成
- [x] LSTM模型结构优化
- [x] 数据周期调整（1h→4h）
- [x] 环境配置问题修复
- [x] 回测框架搭建

### 进行中
- [ ] 回测性能验证
- [ ] 交易信号生成优化
- [ ] 模型训练过程监控
- [ ] 风险控制系统完善

### 待优化
1. 模型预测准确性
2. 回测系统性能
3. 实时数据处理效率
4. 风险控制策略

## 注意事项
1. 请确保使用正确版本的NumPy（1.21.0）
2. 回测时注意数据时间范围的选择
3. 实盘交易前必须进行充分的回测验证
4. 建议先使用小资金进行实盘测试
5. 定期检查和更新模型参数 