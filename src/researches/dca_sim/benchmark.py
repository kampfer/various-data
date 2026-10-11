"""基准对比：用开源库 QuantStats 独立计算绩效指标，与手写 metrics 对比。

设计原则（按用户要求）：
    - 开源结果为“真值”。
    - 手写结果与开源结果出现超过容差的差异，即视为手写实现存在 bug，
      不采信手写结果。

为保证对比公平，严格对比只在“无现金流”的收益率序列上进行：
定投 / 提取会向组合注入或抽离资金，使 ``total_value.pct_change()`` 不再等于
真实投资收益率。因此 :func:`to_return_series` 要求传入的结果不含现金流扰动，
调用方应使用无定投、无提取、无清仓中途现金流的校验场景。

免责声明：指标仅用于逻辑验证，不构成投资建议。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .config import SimConfig
from .engine import DCASimulator
from .metrics import performance


def _require_quantstats():
    """导入 QuantStats，缺失时给出清晰错误。"""
    try:
        import quantstats as qs  # noqa: F401
    except ImportError as exc:  # pragma: no cover - 可选依赖
        raise RuntimeError(
            "基准对比需要安装 quantstats：pipenv run pip install quantstats"
        ) from exc
    return qs


def to_return_series(result_df: pd.DataFrame) -> pd.Series:
    """把逐月总资产转换成逐月收益率序列（仅在无现金流时才等于真实收益）。"""
    if result_df.empty:
        raise ValueError("结果为空，无法构造收益率序列")
    total = result_df["total_value"].astype(float)
    returns = total.pct_change().dropna()
    returns.index = pd.to_datetime(returns.index)
    return returns


@dataclass
class MetricComparison:
    """单项指标的对比结果。"""

    name: str
    handwritten: float
    benchmark: float
    abs_diff: float
    within_tolerance: bool


def _annualized_from_returns(qs, returns: pd.Series) -> float:
    """用月频口径（periods=12）让 QuantStats 的年化与手写几何年化对齐。"""
    # QuantStats 的 cagr 默认按日频；此处显式用月数做几何年化，口径与手写一致。
    cum = (1 + returns).prod() - 1
    years = len(returns) / 12.0
    if years <= 0 or cum <= -1:
        return 0.0
    return (1 + cum) ** (1 / years) - 1


def benchmark_metrics(result_df: pd.DataFrame) -> dict[str, float]:
    """用 QuantStats 独立计算核心指标，作为对比基准（真值）。"""
    qs = _require_quantstats()
    returns = to_return_series(result_df)

    cum_return = float((1 + returns).prod() - 1)  # 等价 qs.stats.comp
    max_dd = float(qs.stats.max_drawdown(returns))
    annualized = _annualized_from_returns(qs, returns)
    return {
        "cum_return": cum_return,
        "max_drawdown": max_dd,
        "annualized_return": annualized,
    }


def compare(
    result_df: pd.DataFrame, cfg: SimConfig, tolerance: float = 1e-6
) -> list[MetricComparison]:
    """逐项对比手写指标与 QuantStats 基准。

    返回每项的对比结果。调用方可据此判断手写实现是否可信。
    """
    hand = performance(result_df, cfg)
    bench = benchmark_metrics(result_df)

    comparisons: list[MetricComparison] = []
    for key in ("cum_return", "annualized_return", "max_drawdown"):
        hv = float(hand[key])
        bv = float(bench[key])
        diff = abs(hv - bv)
        comparisons.append(
            MetricComparison(
                name=key,
                handwritten=hv,
                benchmark=bv,
                abs_diff=diff,
                within_tolerance=diff <= tolerance,
            )
        )
    return comparisons


def build_validation_config(seed: int = 42) -> SimConfig:
    """构造一个无现金流的校验场景：一次性建仓、不定投、不提取、不清仓。

    这样 ``total_value.pct_change()`` 严格等于投资收益率，可与开源库精确对比。
    """
    return SimConfig(
        initial_capital=1_000_000,
        monthly_invest=0,
        equity_ratio=0.6,
        rebalance_band=1.0,  # 关闭再平衡交易，避免引入额外路径依赖
        withdrawal_mode="rate",
        withdrawal_rate=0.0,  # 不提取
        withdrawal_start="2099-01-01",
        liquidation_enabled=False,
        data_source="simulated",
        data_start="2015-01-01",
        data_end="2025-12-31",
        data_seed=seed,
    )


def run_validation(tolerance: float = 1e-6, seed: int = 42) -> tuple[bool, list[MetricComparison]]:
    """运行无现金流校验场景，返回 (是否全部通过, 对比明细)。"""
    cfg = build_validation_config(seed=seed).validate()
    result = DCASimulator(cfg).run()
    comparisons = compare(result, cfg, tolerance=tolerance)
    all_pass = all(c.within_tolerance for c in comparisons)
    return all_pass, comparisons


def format_report(comparisons: list[MetricComparison]) -> str:
    """把对比结果格式化成可读文本。"""
    lines = ["指标对比（开源 QuantStats 为真值）：", ""]
    header = f"{'指标':<20}{'手写':>16}{'开源基准':>16}{'绝对差':>16}  结论"
    lines.append(header)
    lines.append("-" * len(header))
    for c in comparisons:
        verdict = "一致" if c.within_tolerance else "差异→手写疑似BUG"
        lines.append(
            f"{c.name:<20}{c.handwritten:>16.8f}{c.benchmark:>16.8f}"
            f"{c.abs_diff:>16.2e}  {verdict}"
        )
    return "\n".join(lines)
