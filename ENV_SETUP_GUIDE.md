# 🔐 环境变量设置指南

## 📋 为什么使用环境变量？

### **🔒 安全性**
- **防止意外提交**: `.env` 文件被 `.gitignore` 忽略，不会意外提交到Git
- **避免历史暴露**: 即使代码被提交，敏感信息也不会被暴露
- **降低风险**: 减少API密钥泄露的可能性

### **🔄 灵活性**
- **环境隔离**: 开发、测试、生产环境可以使用不同的配置
- **团队协作**: 每个开发者可以有自己的配置，不会相互冲突
- **部署便利**: 不同服务器可以使用不同的配置

### **🚀 最佳实践**
- **12-Factor App**: 符合现代应用开发的最佳实践
- **配置管理**: 将配置与代码分离
- **安全标准**: 符合安全开发标准

## 🛠️ 设置步骤

### **1. 创建环境变量文件**
```bash
# 复制模板文件
cp env_template.txt .env

# 编辑 .env 文件，填入真实API密钥
nano .env
```

### **2. 配置API密钥**
```bash
# .env 文件内容示例
SIM_API_KEY=your_sim_api_key_here
SIM_API_SECRET=your_sim_api_secret_here
SIM_API_PASSWORD=your_sim_api_password_here

REAL_API_KEY=your_real_api_key_here
REAL_API_SECRET=your_real_api_secret_here
REAL_API_PASSWORD=your_real_api_password_here

PROXY=http://127.0.0.1:7890
IS_SIMULATED=true
ALLOW_REAL_TRADING=false
```

### **3. 验证配置**
```python
# 在Python中测试
import os
from dotenv import load_dotenv

load_dotenv()
print(f"API Key: {os.getenv('SIM_API_KEY')}")
```

## 📁 文件结构

```
项目根目录/
├── .env                    # 环境变量文件（不提交到Git）
├── env_template.txt        # 环境变量模板（提交到Git）
├── .gitignore             # Git忽略文件
├── src/
│   └── config/
│       └── config.py      # 配置文件（使用环境变量）
└── ENV_SETUP_GUIDE.md     # 本指南
```

## 🔧 代码示例

### **修改前（不安全）**
```python
# 直接硬编码API密钥
SIM_API_KEY = "48b64404-aff0-415e-9820-f9a55a3d8690"
SIM_API_SECRET = "83B2A5C7AEB8DB8EA71BF72C4AB886C5"
```

### **修改后（安全）**
```python
# 从环境变量读取
import os
from dotenv import load_dotenv

load_dotenv()
SIM_API_KEY = os.getenv('SIM_API_KEY')
SIM_API_SECRET = os.getenv('SIM_API_SECRET')
```

## ⚠️ 安全注意事项

### **1. 文件保护**
- ✅ 确保 `.env` 文件在 `.gitignore` 中
- ✅ 不要将 `.env` 文件提交到Git
- ✅ 定期检查Git状态，确保没有敏感文件

### **2. 密钥管理**
- ✅ 定期更换API密钥
- ✅ 使用最小权限原则
- ✅ 监控API使用情况

### **3. 团队协作**
- ✅ 共享 `env_template.txt` 模板
- ✅ 不要共享真实的 `.env` 文件
- ✅ 在文档中说明配置要求

## 🚀 部署建议

### **本地开发**
```bash
# 使用本地 .env 文件
python src/main.py
```

默认情况下项目只允许模拟盘启动。确需实盘时，需要同时设置：

```bash
IS_SIMULATED=false
ALLOW_REAL_TRADING=true
```

### **服务器部署**
```bash
# 在服务器上设置环境变量
export SIM_API_KEY="your_api_key"
export SIM_API_SECRET="your_api_secret"
python src/main.py
```

### **Docker部署**
```dockerfile
# 使用Docker环境变量
ENV SIM_API_KEY=your_api_key
ENV SIM_API_SECRET=your_api_secret
```

## 📝 故障排除

### **常见问题**

1. **环境变量未加载**
   ```python
   # 确保在文件开头加载
   from dotenv import load_dotenv
   load_dotenv()
   ```

2. **文件路径问题**
   ```python
   # 使用绝对路径
   load_dotenv('/path/to/.env')
   ```

3. **权限问题**
   ```bash
   # 确保 .env 文件权限正确
   chmod 600 .env
   ```

## 🎯 总结

使用环境变量管理API密钥是安全开发的最佳实践：

- ✅ **提高安全性**: 避免敏感信息泄露
- ✅ **增强灵活性**: 支持多环境配置
- ✅ **便于维护**: 配置与代码分离
- ✅ **符合标准**: 遵循现代开发规范

**记住：安全永远是第一位的！** 🛡️
