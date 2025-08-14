#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日交易策略启动脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """启动每日交易策略"""
    print("🚀 启动每日交易策略...")
    
    try:
        # 导入并运行主程序
        from src.main import main as run_strategy
        run_strategy()
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断，程序退出")
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
