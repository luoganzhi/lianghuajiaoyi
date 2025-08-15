# 🧹 项目整理计划

## 📋 当前问题分析

项目根目录存在大量乱七八糟的文件：
- 各种 `*_SUMMARY.md` 文档
- 各种 `*_FIX.md` 文档
- 测试和示例文件散布在根目录
- 配置文件备份散布在 config 目录
- 日志文件散布在不同位置

## 🎯 整理目标

1. **清理根目录** - 只保留核心文件
2. **整理文档** - 将相关文档归类到 `docs/` 目录
3. **整理工具** - 将工具脚本归类到 `tools/` 目录
4. **清理备份** - 删除或归档配置文件备份
5. **整理日志** - 统一日志文件位置

## 📁 目标项目结构

```
lianghuajiaoyi/
├── README.md                    # 项目主说明
├── requirements.txt             # 依赖列表
├── setup.py                    # 安装配置
├── .gitignore                  # Git 忽略规则
├── src/                        # 源代码目录
│   ├── main.py                # 主程序
│   ├── config/                # 配置目录
│   ├── strategies/            # 策略目录
│   ├── execution/             # 执行目录
│   ├── data/                  # 数据目录
│   ├── risk/                  # 风控目录
│   ├── monitor/               # 监控目录
│   ├── examples/              # 示例目录
│   ├── tests/                 # 测试目录
│   └── ...
├── docs/                       # 文档目录
│   ├── README.md              # 项目说明
│   ├── guides/                # 使用指南
│   ├── fixes/                 # 问题修复记录
│   └── summaries/             # 功能总结
├── tools/                      # 工具目录
│   ├── adjust_kline_interval.py
│   └── config_template.py
├── logs/                       # 日志目录
│   ├── main.log
│   ├── trade_monitor.log
│   └── risk_monitor.log
└── data/                       # 数据目录
    ├── ohlcv/                 # K线数据
    └── trades/                # 交易数据
```

## 🔧 整理步骤

### **第一步：创建目录结构**
```bash
mkdir -p docs/guides docs/fixes docs/summaries
mkdir -p tools
mkdir -p data/ohlcv data/trades
```

### **第二步：整理文档文件**
- 将 `*_SUMMARY.md` 移动到 `docs/summaries/`
- 将 `*_FIX.md` 移动到 `docs/fixes/`
- 将 `*_USAGE.md` 移动到 `docs/guides/`
- 将 `*_GUIDE.md` 移动到 `docs/guides/`

### **第三步：整理工具文件**
- 将 `adjust_kline_interval.py` 移动到 `tools/`
- 将 `config_template.py` 移动到 `tools/`
- 将 `high_precision_mode_example.py` 移动到 `tools/`

### **第四步：整理测试文件**
- 将根目录的测试文件移动到 `src/tests/`
- 将示例文件移动到 `src/examples/`

### **第五步：清理备份文件**
- 删除或归档配置文件备份
- 清理散布的日志文件

### **第六步：更新 .gitignore**
- 确保新目录结构被正确忽略
- 更新忽略规则

## 📝 具体操作清单

### **需要移动的文件**
- [ ] `*_SUMMARY.md` → `docs/summaries/`
- [ ] `*_FIX.md` → `docs/fixes/`
- [ ] `*_USAGE.md` → `docs/guides/`
- [ ] `*_GUIDE.md` → `docs/guides/`
- [ ] `adjust_kline_interval.py` → `tools/`
- [ ] `config_template.py` → `tools/`
- [ ] `high_precision_mode_example.py` → `tools/`
- [ ] `test_strategy_integration.py` → `src/tests/`

### **需要删除的文件**
- [ ] 配置文件备份（`config_backup_*.py`）
- [ ] 散布的日志文件
- [ ] 重复的文档文件

### **需要保留在根目录的文件**
- [ ] `README.md`
- [ ] `requirements.txt`
- [ ] `setup.py`
- [ ] `.gitignore`
- [ ] `src/` 目录

## ⚠️ 注意事项

1. **备份重要文件** - 整理前先备份
2. **检查依赖关系** - 确保移动文件后不影响导入
3. **更新导入路径** - 修改相关的 import 语句
4. **测试功能** - 整理后测试主要功能是否正常

## 🎉 预期效果

整理完成后：
- 项目根目录干净整洁
- 文档分类清晰，易于查找
- 工具脚本集中管理
- 代码结构更加专业
- 便于团队协作和维护
