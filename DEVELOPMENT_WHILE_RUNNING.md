# 🔄 运行时开发指南

## 📋 问题描述

当交易程序正在运行时，如何继续开发新功能？

## 🎯 解决方案

### **方案一：多终端开发（推荐）**

#### **1. 打开新终端**
```bash
# 方法1：在现有终端中打开新标签页
# 方法2：打开新的终端窗口
# 方法3：使用 tmux 或 screen 会话管理
```

#### **2. 在新终端中开发**
```bash
# 切换到项目目录
cd /Users/lgzyy/PycharmProjects/lianghuajiaoyi

# 创建新功能分支（如果使用Git）
git checkout -b feature/new-functionality

# 开始开发新功能
```

#### **3. 使用IDE开发**
- 在PyCharm、VSCode等IDE中打开项目
- 可以同时编辑代码和查看运行日志
- 支持实时语法检查和调试

### **方案二：热重载开发**

#### **1. 修改代码后重启**
```bash
# 停止当前运行的程序
# 方法1：Ctrl+C
# 方法2：找到进程ID并杀死
ps aux | grep python
kill -9 <进程ID>

# 重新启动程序
python src/main.py
```

#### **2. 使用开发模式**
```bash
# 创建开发版本的主程序
cp src/main.py src/main_dev.py

# 在开发版本中添加热重载功能
```

### **方案三：模块化开发**

#### **1. 独立模块开发**
```bash
# 开发独立的功能模块
# 例如：新的策略、新的分析工具等
# 这些模块可以独立测试，不影响主程序
```

#### **2. 配置文件驱动**
```bash
# 通过修改配置文件来调整功能
# 主程序会读取配置变化
# 无需重启程序
```

## 🛠️ 具体操作步骤

### **步骤1：准备开发环境**

#### **打开新终端**
```bash
# 在macOS中
# 1. Cmd+T 打开新标签页
# 2. 或者 Cmd+N 打开新窗口
# 3. 或者使用 iTerm2 的分屏功能
```

#### **设置开发环境**
```bash
# 激活虚拟环境（如果有）
source venv/bin/activate

# 确认Python环境
python --version
which python
```

### **步骤2：开始开发**

#### **创建新功能文件**
```bash
# 在合适的目录中创建新文件
# 例如：新的策略
touch src/strategies/new_strategy.py

# 或者新的工具
touch tools/new_tool.py
```

#### **编辑代码**
```bash
# 使用你喜欢的编辑器
# VSCode
code src/strategies/new_strategy.py

# 或者 vim
vim src/strategies/new_strategy.py
```

### **步骤3：测试新功能**

#### **独立测试**
```bash
# 创建测试脚本
touch test_new_feature.py

# 运行测试
python test_new_feature.py
```

#### **集成测试**
```bash
# 在主程序中导入新功能
# 测试集成效果
```

## 📁 推荐的开发目录结构

```
lianghuajiaoyi/
├── src/                    # 源代码
│   ├── strategies/        # 策略模块
│   │   ├── new_strategy.py  # 新策略
│   │   └── ...
│   ├── tools/             # 工具模块
│   │   ├── new_tool.py    # 新工具
│   │   └── ...
│   └── ...
├── tests/                 # 测试文件
│   ├── test_new_feature.py
│   └── ...
├── development/           # 开发相关
│   ├── drafts/           # 草稿文件
│   ├── experiments/      # 实验代码
│   └── ...
└── ...
```

## 🔧 开发工具推荐

### **1. 终端管理**
- **tmux**: 会话管理，可以分屏
- **screen**: 类似tmux，更轻量
- **iTerm2**: macOS终端，支持分屏

### **2. 代码编辑**
- **VSCode**: 轻量级，插件丰富
- **PyCharm**: 专业Python IDE
- **vim/emacs**: 命令行编辑器

### **3. 版本控制**
- **Git**: 代码版本管理
- **GitHub Desktop**: 图形化Git工具

## ⚠️ 注意事项

### **1. 避免冲突**
- 不要同时修改主程序正在使用的文件
- 新功能先在独立文件中开发
- 测试完成后再集成到主程序

### **2. 备份重要文件**
```bash
# 修改前备份
cp src/main.py src/main_backup.py
cp src/config/config.py src/config/config_backup.py
```

### **3. 测试策略**
- 新功能先在测试环境中验证
- 使用模拟数据进行测试
- 确认无误后再应用到实盘

### **4. 日志监控**
- 保持对运行程序的日志监控
- 确保新功能不影响现有功能
- 及时发现问题并修复

## 🚀 快速开始

### **立即开始开发**
```bash
# 1. 打开新终端
# 2. 切换到项目目录
cd /Users/lgzyy/PycharmProjects/lianghuajiaoyi

# 3. 创建新功能
mkdir -p development/experiments
touch development/experiments/new_feature.py

# 4. 开始编码
code development/experiments/new_feature.py
```

### **测试新功能**
```bash
# 创建测试脚本
echo 'print("Hello from new feature!")' > test_new.py

# 运行测试
python test_new.py
```

## 📝 开发流程建议

### **1. 功能规划**
- 明确新功能需求
- 设计实现方案
- 确定测试策略

### **2. 独立开发**
- 在独立文件中开发
- 使用模拟数据测试
- 确保功能正确

### **3. 集成测试**
- 集成到主程序
- 进行完整测试
- 验证无副作用

### **4. 部署上线**
- 备份原文件
- 部署新功能
- 监控运行状态

---

**💡 提示**: 推荐使用多终端开发方案，这样既不影响现有程序运行，又能高效开发新功能！
