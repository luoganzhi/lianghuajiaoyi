import pytest
from datetime import datetime, timedelta
import os
import json
import pandas as pd
from pathlib import Path
from monitor.trade_monitor import TradeMonitor
from monitor.report_generator import ReportGenerator

@pytest.fixture
def setup_monitor():
    """设置测试环境"""
    # 创建临时目录
    test_log_dir = "test_logs"
    test_report_dir = "test_reports"
    test_template_dir = "test_templates"
    
    # 初始化监控器和报告生成器
    monitor = TradeMonitor(log_dir=test_log_dir, report_dir=test_report_dir)
    generator = ReportGenerator(template_dir=test_template_dir)
    
    yield monitor, generator
    
    # 清理测试文件
    for dir_path in [test_log_dir, test_report_dir, test_template_dir]:
        if os.path.exists(dir_path):
            for file in os.listdir(dir_path):
                os.remove(os.path.join(dir_path, file))
            os.rmdir(dir_path)

def test_record_trade(setup_monitor):
    """测试交易记录功能"""
    monitor, _ = setup_monitor
    
    # 测试记录买入交易
    buy_trade = {
        "symbol": "BTC-USDT",
        "side": "buy",
        "size": 0.1,
        "price": 50000,
        "value": 5000,
        "type": "entry"
    }
    monitor.record_trade(buy_trade)
    
    # 测试记录卖出交易（盈利）
    sell_trade = {
        "symbol": "BTC-USDT",
        "side": "sell",
        "size": 0.1,
        "price": 51000,
        "profit": 100,
        "type": "exit"
    }
    monitor.record_trade(sell_trade)
    
    # 验证交易记录
    assert len(monitor.trades) == 2
    assert monitor.trades[0]["side"] == "buy"
    assert monitor.trades[1]["side"] == "sell"
    
    # 验证每日统计
    today = datetime.now().date().isoformat()
    assert today in monitor.daily_stats
    assert monitor.daily_stats[today]["total_trades"] == 2
    assert monitor.daily_stats[today]["winning_trades"] == 1

def test_position_update(setup_monitor):
    """测试持仓更新功能"""
    monitor, _ = setup_monitor
    
    position_data = {
        "size": 0.1,
        "entry_price": 50000,
        "current_price": 51000,
        "unrealized_pnl": 100
    }
    
    monitor.update_position("BTC-USDT", position_data)
    assert "BTC-USDT" in monitor.positions
    assert monitor.positions["BTC-USDT"]["size"] == 0.1

def test_system_metrics_update(setup_monitor):
    """测试系统指标更新功能"""
    monitor, _ = setup_monitor
    
    metrics = {
        "drawdown": 0.05,
        "volatility": 0.02,
        "sharpe_ratio": 1.5
    }
    
    monitor.update_system_metrics(metrics)
    assert monitor.system_metrics["drawdown"] == 0.05
    assert monitor.system_metrics["sharpe_ratio"] == 1.5

def test_daily_report_generation(setup_monitor):
    """测试每日报告生成功能"""
    monitor, _ = setup_monitor
    
    # 添加测试数据
    trades = [
        {
            "symbol": "BTC-USDT",
            "side": "buy",
            "size": 0.1,
            "price": 50000,
            "value": 5000,
            "type": "entry"
        },
        {
            "symbol": "BTC-USDT",
            "side": "sell",
            "size": 0.1,
            "price": 51000,
            "profit": 100,
            "type": "exit"
        }
    ]
    
    for trade in trades:
        monitor.record_trade(trade)
    
    # 生成报告
    today = datetime.now().date().isoformat()
    report = monitor.generate_daily_report(today)
    
    # 验证报告内容
    assert report["total_trades"] == 2
    assert report["winning_trades"] == 1
    assert report["total_profit"] == 100
    
    # 验证报告文件
    report_file = Path(monitor.report_dir) / f"daily_report_{today}.json"
    assert report_file.exists()

def test_performance_report_generation(setup_monitor):
    """测试绩效报告生成功能"""
    monitor, _ = setup_monitor
    
    # 添加测试数据（包括历史数据）
    yesterday = datetime.now() - timedelta(days=1)
    trades = [
        {
            "symbol": "BTC-USDT",
            "side": "buy",
            "size": 0.1,
            "price": 50000,
            "value": 5000,
            "type": "entry",
            "timestamp": yesterday
        },
        {
            "symbol": "BTC-USDT",
            "side": "sell",
            "size": 0.1,
            "price": 51000,
            "profit": 100,
            "type": "exit",
            "timestamp": datetime.now()
        }
    ]
    
    for trade in trades:
        monitor.trades.append(trade)
    
    # 生成报告
    report = monitor.generate_performance_report(days=30)
    
    # 验证报告内容
    assert report["total_trades"] == 2
    assert report["winning_trades"] == 1
    assert report["profit_factor"] > 0

def test_trade_history_export(setup_monitor):
    """测试交易历史导出功能"""
    monitor, _ = setup_monitor
    
    # 添加测试数据
    trades = [
        {
            "symbol": "BTC-USDT",
            "side": "buy",
            "size": 0.1,
            "price": 50000,
            "value": 5000,
            "type": "entry"
        },
        {
            "symbol": "BTC-USDT",
            "side": "sell",
            "size": 0.1,
            "price": 51000,
            "profit": 100,
            "type": "exit"
        }
    ]
    
    for trade in trades:
        monitor.record_trade(trade)
    
    # 测试CSV导出
    monitor.export_trade_history(format="csv")
    csv_file = Path(monitor.report_dir) / "trade_history.csv"
    assert csv_file.exists()
    
    # 验证CSV内容
    df = pd.read_csv(csv_file)
    assert len(df) == 2
    assert "symbol" in df.columns
    assert "profit" in df.columns

def test_html_report_generation(setup_monitor):
    """测试HTML报告生成功能"""
    monitor, generator = setup_monitor
    
    # 添加测试数据
    trades = [
        {
            "symbol": "BTC-USDT",
            "side": "buy",
            "size": 0.1,
            "price": 50000,
            "value": 5000,
            "type": "entry"
        },
        {
            "symbol": "BTC-USDT",
            "side": "sell",
            "size": 0.1,
            "price": 51000,
            "profit": 100,
            "type": "exit"
        }
    ]
    
    for trade in trades:
        monitor.record_trade(trade)
    
    # 生成每日报告数据
    today = datetime.now().date().isoformat()
    stats = monitor.generate_daily_report(today)
    
    # 格式化指标
    metrics = generator.format_metrics(stats)
    
    # 生成HTML报告
    output_file = Path(monitor.report_dir) / "test_report.html"
    generator.generate_html_report(
        title="测试报告",
        metrics=metrics,
        trades=monitor.trades,
        stats=stats,
        output_file=str(output_file)
    )
    
    # 验证HTML文件
    assert output_file.exists()
    with open(output_file, "r") as f:
        content = f.read()
        assert "测试报告" in content
        assert "交易统计" in content
        assert "资金曲线" in content

def test_alert_callback(setup_monitor):
    """测试预警回调功能"""
    alert_messages = []
    
    def test_alert_callback(alert_type: str, message: str):
        alert_messages.append((alert_type, message))
    
    # 创建带自定义回调的监控器
    monitor = TradeMonitor(
        log_dir="test_logs",
        report_dir="test_reports",
        alert_callback=test_alert_callback
    )
    
    # 触发预警
    monitor._default_alert("TEST_ALERT", "测试预警消息")
    
    # 验证预警消息
    assert len(alert_messages) == 1
    assert alert_messages[0][0] == "TEST_ALERT"
    assert alert_messages[0][1] == "测试预警消息" 