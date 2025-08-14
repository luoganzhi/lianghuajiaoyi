from monitor import TradeMonitor, ReportGenerator
from datetime import datetime
import pandas as pd

def main():
    # 创建交易监控实例
    monitor = TradeMonitor(log_dir="logs", report_dir="reports")
    
    # 模拟交易数据
    trade_data = {
        'timestamp': datetime.now(),
        'symbol': 'BTC-USDT',
        'side': 'buy',
        'size': 0.1,
        'price': 50000,
        'value': 5000,
        'type': 'entry',
        'profit': 0
    }
    
    # 记录交易
    monitor.record_trade(trade_data)
    
    # 更新持仓信息
    position_data = {
        'size': 0.1,
        'entry_price': 50000,
        'current_price': 51000,
        'unrealized_pnl': 100
    }
    monitor.update_position('BTC-USDT', position_data)
    
    # 更新系统指标
    metrics = {
        'drawdown': 0.05,
        'volatility': 0.02,
        'sharpe_ratio': 1.5
    }
    monitor.update_system_metrics(metrics)
    
    # 生成每日报告
    daily_report = monitor.generate_daily_report()
    print("每日报告生成完成:", daily_report)
    
    # 生成绩效报告
    performance_report = monitor.generate_performance_report(days=30)
    print("绩效报告生成完成:", performance_report)
    
    # 创建报告生成器
    report_gen = ReportGenerator(template_dir="templates")
    
    # 格式化指标数据
    metrics_data = report_gen.format_metrics(daily_report)
    
    # 生成HTML报告
    report_gen.generate_html_report(
        title="交易监控报告",
        metrics=metrics_data,
        trades=monitor.trades,
        stats=daily_report,
        output_file="reports/monitor_report.html"
    )
    print("HTML报告生成完成")
    
    # 导出交易历史
    monitor.export_trade_history(format="csv")
    print("交易历史导出完成")

if __name__ == "__main__":
    main() 