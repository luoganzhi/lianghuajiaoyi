from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import logging
import json
from pathlib import Path

class TradeMonitor:
    def __init__(self,
                 log_dir: str = "logs",
                 report_dir: str = "reports",
                 alert_callback = None):
        """
        交易监控器
        
        Args:
            log_dir: 日志存储目录
            report_dir: 报告存储目录
            alert_callback: 预警回调函数
        """
        self.log_dir = Path(log_dir)
        self.report_dir = Path(report_dir)
        self.alert_callback = alert_callback or self._default_alert
        
        # 创建必要的目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据存储
        self.trades: List[Dict] = []          # 交易记录
        self.positions: Dict[str, Dict] = {}  # 当前持仓
        self.daily_stats: Dict[str, Dict] = {}  # 每日统计
        self.system_metrics: Dict[str, float] = {}  # 系统指标
        
        # 配置日志
        self._setup_logging()
        
    def _setup_logging(self):
        """配置日志系统"""
        self.logger = logging.getLogger("trade_monitor")
        self.logger.setLevel(logging.INFO)
        
        # 清除现有处理器，避免重复
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 文件处理器
        fh = logging.FileHandler(self.log_dir / "trade_monitor.log")
        fh.setLevel(logging.INFO)
        
        # 控制台处理器
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def _default_alert(self, alert_type: str, message: str):
        """默认预警处理"""
        self.logger.warning(f"{alert_type}: {message}")
        if self.alert_callback and self.alert_callback != self._default_alert:
            self.alert_callback(alert_type, message)
        
    def record_trade(self, trade: Dict):
        """记录交易"""
        try:
            # 添加时间戳
            if "timestamp" not in trade:
                trade["timestamp"] = datetime.now()
            
            # 验证必要字段
            required_fields = ["symbol", "side", "size", "price", "type"]
            for field in required_fields:
                if field not in trade:
                    raise ValueError(f"交易记录缺少必要字段: {field}")
                
            # 添加到交易列表
            self.trades.append(trade)
            self.logger.info(f"新交易记录: {json.dumps(trade, default=str, ensure_ascii=False)}")
            
            # 更新每日统计
            date = trade["timestamp"].date().isoformat()
            if date not in self.daily_stats:
                self.daily_stats[date] = {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_profit": 0.0,
                    "total_loss": 0.0
                }
            
            stats = self.daily_stats[date]
            stats["total_trades"] += 1
            
            if trade.get("profit", 0) > 0:
                stats["winning_trades"] += 1
                stats["total_profit"] += trade["profit"]
            elif trade.get("loss", 0) > 0:
                stats["losing_trades"] += 1
                stats["total_loss"] += trade["loss"]
            
            self.logger.info(f"每日统计更新 - {date}: {json.dumps(stats, ensure_ascii=False)}")
            
        except Exception as e:
            self.logger.error(f"记录交易失败: {str(e)}")
            raise
        
    def update_position(self, symbol: str, position_data: Dict):
        """更新持仓信息"""
        self.positions[symbol] = position_data
        self.logger.info(f"持仓更新 - {symbol}: {position_data}")
        
    def update_system_metrics(self, metrics: Dict[str, float]):
        """更新系统指标"""
        self.system_metrics.update(metrics)
        # 转换为中文显示
        chinese_metrics = {
            "当前资金": f"{metrics.get('current_capital', 0):.2f} USDT",
            "初始资金": f"{metrics.get('initial_capital', 0):.2f} USDT",
            "回撤比例": f"{metrics.get('drawdown', 0) * 100:.2f}%",
            "当日盈亏": f"{metrics.get('daily_pnl', 0):.2f} USDT",
            "持仓数量": metrics.get('position_count', 0),
            "总敞口": f"{metrics.get('total_exposure', 0):.2f} USDT"
        }
        self.logger.info(f"系统指标更新: {chinese_metrics}")
        
    def generate_daily_report(self, date: Optional[str] = None) -> Dict:
        """生成每日报告"""
        date = date or datetime.now().date().isoformat()
        if date not in self.daily_stats:
            return {}
            
        stats = self.daily_stats[date]
        total_trades = stats["total_trades"]
        win_rate = stats["winning_trades"] / total_trades if total_trades > 0 else 0
        
        report = {
            "date": date,
            "total_trades": total_trades,
            "winning_trades": stats["winning_trades"],
            "losing_trades": stats["losing_trades"],
            "win_rate": win_rate,
            "total_profit": stats["total_profit"],
            "total_loss": stats["total_loss"],
            "net_profit": stats["total_profit"] - stats["total_loss"],
            "system_metrics": self.system_metrics.copy()
        }
        
        # 保存报告
        report_file = self.report_dir / f"daily_report_{date}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=4)
            
        self.logger.info(f"已生成每日报告: {report_file}")
        return report
        
    def generate_performance_report(self, days: int = 30) -> Dict:
        """生成绩效报告"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # 收集日期范围内的数据
        period_trades = [
            trade for trade in self.trades
            if start_date <= trade["timestamp"].date() <= end_date
        ]
        
        # 计算关键指标
        total_trades = len(period_trades)
        winning_trades = len([t for t in period_trades if t.get("profit", 0) > 0])
        total_profit = sum(t.get("profit", 0) for t in period_trades)
        total_loss = sum(abs(t.get("loss", 0)) for t in period_trades)
        
        # 计算其他指标
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
        
        report = {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "net_profit": total_profit - total_loss,
            "profit_factor": profit_factor,
            "average_profit": total_profit / winning_trades if winning_trades > 0 else 0,
            "average_loss": total_loss / (total_trades - winning_trades) if (total_trades - winning_trades) > 0 else 0
        }
        
        # 保存报告
        report_file = self.report_dir / f"performance_report_{end_date.isoformat()}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=4)
            
        self.logger.info(f"已生成绩效报告: {report_file}")
        return report
        
    def export_trade_history(self, format: str = "csv"):
        """导出交易历史"""
        if not self.trades:
            self.logger.warning("没有交易记录可导出")
            return
            
        df = pd.DataFrame(self.trades)
        
        if format == "csv":
            output_file = self.report_dir / "trade_history.csv"
            df.to_csv(output_file, index=False)
        elif format == "excel":
            output_file = self.report_dir / "trade_history.xlsx"
            df.to_excel(output_file, index=False)
            
        self.logger.info(f"已导出交易历史: {output_file}")

    def reset_daily_metrics(self):
        """重置每日指标"""
        today = datetime.now().date().isoformat()
        if today in self.daily_stats:
            self.daily_stats[today] = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0
            }
        self.logger.info("已重置每日指标") 