from typing import Dict, List
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import json
from pathlib import Path
import jinja2

class ReportGenerator:
    def __init__(self, template_dir: str = "templates"):
        """
        报告生成器
        
        Args:
            template_dir: HTML模板目录
        """
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self._setup_templates()
        
    def _setup_templates(self):
        """设置HTML模板"""
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir)
        )
        
        # 创建默认模板如果不存在
        default_template = self.template_dir / "report_template.html"
        if not default_template.exists():
            template_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>{{ title }}</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .section { margin-bottom: 30px; }
                    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
                    .metric-card {
                        padding: 15px;
                        border-radius: 8px;
                        background: #f5f5f5;
                        text-align: center;
                    }
                    .chart { margin: 20px 0; }
                    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                    th, td { padding: 10px; border: 1px solid #ddd; text-align: left; }
                    th { background: #f5f5f5; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>{{ title }}</h1>
                    
                    <div class="section">
                        <h2>交易统计</h2>
                        <div class="metrics">
                            {% for metric in metrics %}
                            <div class="metric-card">
                                <h3>{{ metric.name }}</h3>
                                <p>{{ metric.value }}</p>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>图表</h2>
                        {% for chart in charts %}
                        <div class="chart" id="{{ chart.id }}"></div>
                        <script>
                            var data = {{ chart.data | safe }};
                            var layout = {{ chart.layout | safe }};
                            Plotly.newPlot('{{ chart.id }}', data, layout);
                        </script>
                        {% endfor %}
                    </div>
                    
                    {% if trades %}
                    <div class="section">
                        <h2>最近交易</h2>
                        <table>
                            <tr>
                                {% for header in trades[0].keys() %}
                                <th>{{ header }}</th>
                                {% endfor %}
                            </tr>
                            {% for trade in trades %}
                            <tr>
                                {% for value in trade.values() %}
                                <td>{{ value }}</td>
                                {% endfor %}
                            </tr>
                            {% endfor %}
                        </table>
                    </div>
                    {% endif %}
                </div>
            </body>
            </html>
            """
            with open(default_template, "w") as f:
                f.write(template_content)
                
    def generate_equity_chart(self, trades: List[Dict]) -> Dict:
        """生成资金曲线图"""
        if not trades:
            return None
            
        # 计算累计收益
        df = pd.DataFrame(trades)
        # 确保profit和loss列存在
        if "profit" not in df.columns:
            df["profit"] = 0.0
        if "loss" not in df.columns:
            df["loss"] = 0.0
            
        df["cumulative_profit"] = (df["profit"].fillna(0) - df["loss"].fillna(0)).cumsum()
        
        # 创建图表
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["cumulative_profit"],
            mode="lines",
            name="资金曲线"
        ))
        
        layout = {
            "title": "资金曲线",
            "xaxis_title": "时间",
            "yaxis_title": "累计收益"
        }
        
        return {
            "id": "equity_chart",
            "data": fig.data,
            "layout": layout
        }
        
    def generate_win_loss_chart(self, stats: Dict) -> Dict:
        """生成胜负分布图"""
        labels = ["盈利交易", "亏损交易"]
        values = [stats["winning_trades"], stats["losing_trades"]]
        
        fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
        layout = {"title": "交易胜负分布"}
        
        return {
            "id": "win_loss_chart",
            "data": fig.data,
            "layout": layout
        }
        
    def generate_html_report(self,
                           title: str,
                           metrics: List[Dict],
                           trades: List[Dict],
                           stats: Dict,
                           output_file: str):
        """生成HTML格式报告"""
        # 生成图表
        charts = []
        equity_chart = self.generate_equity_chart(trades)
        if equity_chart:
            charts.append(equity_chart)
            
        win_loss_chart = self.generate_win_loss_chart(stats)
        if win_loss_chart:
            charts.append(win_loss_chart)
            
        # 准备模板数据
        template_data = {
            "title": title,
            "metrics": metrics,
            "charts": charts,
            "trades": trades[-10:] if trades else []  # 只显示最近10笔交易
        }
        
        # 渲染模板
        template = self.env.get_template("report_template.html")
        html_content = template.render(**template_data)
        
        # 保存报告
        with open(output_file, "w") as f:
            f.write(html_content)
            
    def format_metrics(self, stats: Dict) -> List[Dict]:
        """格式化指标数据"""
        return [
            {"name": "总交易次数", "value": stats["total_trades"]},
            {"name": "胜率", "value": f"{stats['win_rate']*100:.2f}%"},
            {"name": "净收益", "value": f"{stats['net_profit']:.2f}"},
            {"name": "收益因子", "value": f"{stats.get('profit_factor', 0):.2f}"},
            {"name": "平均盈利", "value": f"{stats.get('average_profit', 0):.2f}"},
            {"name": "平均亏损", "value": f"{stats.get('average_loss', 0):.2f}"}
        ] 