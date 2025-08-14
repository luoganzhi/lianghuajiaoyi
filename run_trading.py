#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易启动脚本 - 支持现货和合约交易
"""

import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def show_menu():
    """显示交易模式选择菜单"""
    print("=" * 60)
    print("🚀 量化交易系统启动")
    print("=" * 60)
    print("请选择交易模式:")
    print("1. 📈 现货交易 (Spot Trading)")
    print("2. ⚡ 合约交易 (Futures Trading)")
    print("3. 🔍 查看策略配置")
    print("4. ❌ 退出")
    print("=" * 60)

def show_strategy_config():
    """显示策略配置信息"""
    print("\n📋 策略配置信息:")
    print("-" * 40)
    print("策略类型: DailyTradingStrategy")
    print("止盈设置: 1.0%")
    print("止损设置: 0.5%")
    print("RSI周期: 21")
    print("MA设置: 5/20")
    print("交易时间: 0:00-24:00")
    print("每日交易限制: 1次")
    print("-" * 40)
    
    print("\n📊 合约交易参数:")
    print("-" * 40)
    print("杠杆倍数: 10x")
    print("交易对: BTC-USDT-SWAP")
    print("保证金模式: 全仓")
    print("风险比例: 2%")
    print("-" * 40)

def clear_data_before_start():
    """启动前清理数据"""
    import os
    import shutil
    
    print("🧹 启动前清理数据...")
    
    # 清理日志文件
    log_dirs = ["src/logs", "src/reports", "logs", "reports"]
    for log_dir in log_dirs:
        if os.path.exists(log_dir):
            try:
                shutil.rmtree(log_dir)
                print(f"✅ 清理 {log_dir} 目录完成")
            except Exception as e:
                print(f"⚠️ 清理 {log_dir} 目录失败: {e}")
        
        # 重新创建目录
        try:
            os.makedirs(log_dir, exist_ok=True)
            print(f"✅ 重建 {log_dir} 目录完成")
        except Exception as e:
            print(f"⚠️ 重建 {log_dir} 目录失败: {e}")
    
    # 清理临时文件
    temp_files = ["*.log", "*.tmp", "*.cache"]
    for pattern in temp_files:
        try:
            import glob
            for file in glob.glob(pattern):
                os.remove(file)
                print(f"✅ 删除临时文件: {file}")
        except Exception as e:
            pass
    
    print("🧹 数据清理完成\n")

def main():
    """主函数"""
    # 启动前清理数据
    clear_data_before_start()
    
    while True:
        show_menu()
        
        try:
            choice = input("请输入选择 (1-4): ").strip()
            
            if choice == "1":
                print("\n🚀 启动现货交易模式...")
                print("正在导入现货交易模块...")
                
                try:
                    from src.main import main as spot_main
                    print("✅ 现货交易模块导入成功")
                    print("正在启动现货交易...")
                    spot_main()
                except Exception as e:
                    print(f"❌ 现货交易启动失败: {e}")
                    print("请检查配置和网络连接")
                
            elif choice == "2":
                print("\n⚡ 启动合约交易模式...")
                print("正在导入合约交易模块...")
                
                try:
                    from src.main import futures_trading_main
                    print("✅ 合约交易模块导入成功")
                    print("正在启动合约交易...")
                    futures_trading_main()
                except Exception as e:
                    print(f"❌ 合约交易启动失败: {e}")
                    print("请检查配置和网络连接")
                
            elif choice == "3":
                show_strategy_config()
                input("\n按回车键返回主菜单...")
                
            elif choice == "4":
                print("\n👋 感谢使用量化交易系统！")
                print("再见！")
                break
                
            else:
                print("\n❌ 无效选择，请输入 1-4")
                input("按回车键继续...")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，正在退出...")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            input("按回车键继续...")

if __name__ == "__main__":
    main()
