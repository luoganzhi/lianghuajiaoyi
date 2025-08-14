from math import tanh
from typing import Dict, Tuple


def score_strategy(metrics: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    """
    根据回测指标计算策略评分，范围 [0, 100]，越高越好。

    期望输入的 metrics 至少包含：
      - total_return: 总收益率 (e.g. 0.12 表示 12%)
      - max_drawdown: 最大回撤 (0~1)
      - sharpe: 夏普比率

    评分思想：
      - 奖励高收益和高夏普
      - 惩罚高回撤
      - 使用平滑的双曲正切进行归一化，避免极端值“爆分”
    """
    total_return = float(metrics.get("total_return", 0.0))
    max_drawdown = float(metrics.get("max_drawdown", 0.0))
    sharpe = float(metrics.get("sharpe", 0.0))

    # 归一化到 [-1, 1]
    # 收益：放大系数 4 → 25% 左右收益基本拉满该项
    ret_comp = tanh(total_return * 4.0)

    # 夏普：除以 2 → 夏普在 2 左右基本拉满该项
    sharpe_comp = tanh(sharpe / 2.0)

    # 回撤：希望越小越好，将 (0.5 - mdd) 放大 → mdd < 20% 时接近拉满
    mdd_comp = tanh((0.5 - max_drawdown) * 3.0)

    # 权重可调：收益 50%，夏普 30%，回撤 20%
    score_raw = 0.5 * ret_comp + 0.3 * sharpe_comp + 0.2 * mdd_comp  # [-1,1]

    # 映射到 [0, 100]
    score = round((score_raw + 1.0) / 2.0 * 100.0, 2)

    components = {
        "ret_component": round((ret_comp + 1.0) / 2.0 * 100.0, 2),
        "sharpe_component": round((sharpe_comp + 1.0) / 2.0 * 100.0, 2),
        "mdd_component": round((mdd_comp + 1.0) / 2.0 * 100.0, 2),
    }

    return score, components


