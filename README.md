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
│   ├── main.py              # OKX合约交易主入口
│   ├── data/                # 市场数据获取与预处理
│   ├── strategies/          # LSTM、均线、RSI、网格、趋势等策略
│   ├── execution/           # 交易执行器
│   ├── risk/                # 风控、仓位、止盈止损与风险监控
│   ├── monitor/             # 交易监控与报告
│   ├── scripts/             # LSTM训练、回测、实盘脚本
│   ├── examples/            # 示例和简单回测脚本
│   └── tests/               # 自动化测试
├── models/                  # 模型存储
├── test_models/             # 测试模型存储
├── data/                    # 数据缓存
├── templates/               # 报告模板
└── logs/                    # 运行日志
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
pandas>=1.5.0
numpy>=1.21.0
tensorflow>=2.10.0
scikit-learn>=1.0.0
ccxt>=2.0.0
plotly>=5.10.0
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
from src.scripts.backtest_lstm import LSTMBacktester

backtester = LSTMBacktester(
    exchange_id='okx',
    symbol='BTC/USDT',
    timeframe='4h',
    start_date='2023-10-01',
    end_date='2023-12-31',
    sequence_length=12,
    prediction_length=3,
    use_cached_data=True
)
results = backtester.run()
```

### 2. 实盘交易
先复制环境变量模板，并建议先使用模拟盘：

```bash
cp env_template.txt .env
# 编辑 .env，填写 OKX API 配置，并保持 IS_SIMULATED=true 完成模拟验证
python src/main.py
```

实盘运行需要二次确认：`.env` 中必须同时设置 `IS_SIMULATED=false` 和 `ALLOW_REAL_TRADING=true`，否则主程序会拒绝启动实盘模式。

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
1. 请按 `requirements.txt` 安装依赖，避免 NumPy、TensorFlow 等版本不兼容
2. 回测时注意数据时间范围的选择
3. 实盘交易前必须进行充分的回测验证
4. 建议先使用小资金进行实盘测试
5. 定期检查和更新模型参数
