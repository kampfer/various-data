"""绩效指标：从引擎输出的月度结果计算收益与风险指标。

清仓后不再计算收益与回撤，所有指标以清仓时点（结果序列末行）为准。

免责声明：指标仅用于逻辑验证，不构成投资建议。
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .config import SimConfig


def _require_quantstats():
    """导入 QuantStats，缺失时给出清晰错误。"""
    try:
        import quantstats as qs
    except ImportError as exc:  # pragma: no cover - 必需依赖
        raise RuntimeError(
            "绩效指标依赖开源库 quantstats：pipenv run pip install quantstats"
        ) from exc
    return qs


def _to_returns(series: pd.Series) -> pd.Series:
    """把净值/总资产序列转成逐月收益率序列。"""
    returns = series.astype(float).pct_change().dropna()
    returns.index = pd.to_datetime(returns.index)
    return returns


def _max_drawdown(series: pd.Series) -> float:
    """用开源 QuantStats 计算最大回撤（返回负值，如 -0.1245 表示 -12.45%）。

    回撤是纯路径指标，只看总资产波动，与现金流无关，故直接采用开源实现。
    """
    if len(series) < 2:
        return 0.0
    qs = _require_quantstats()
    return float(qs.stats.max_drawdown(_to_returns(series)))


def performance(result_df: pd.DataFrame, cfg: SimConfig) -> dict[str, Any]:
    """根据月度结果计算全部绩效指标。"""
    if result_df.empty:
        raise ValueError("结果为空，无法计算绩效指标")

    final_total = float(result_df["total_value"].iloc[-1])
    net_invested = float(result_df["net_invested"].iloc[-1])
    invested_total = float(result_df["invested_total"].iloc[-1])
    withdrawn_total = float(result_df["withdrawn_total"].iloc[-1])

    # 累计收益率：(终值 + 累计提取 - 累计投入) / 累计投入
    # 这是“投入产出比”业务口径，考虑了定投与提取现金流，不等同于开源库的纯价格复利，
    # 因此保留本地实现；其几何年化公式已与 QuantStats 基准对齐验证。
    cum_return = (
        (final_total + withdrawn_total - invested_total) / invested_total
        if invested_total > 0
        else 0.0
    )

    # 年化收益率（基于业务 cum_return 的几何年化）
    # 持有年数以“收益区间数”为准：N 个月末观测点之间只有 N-1 个月的收益区间。
    # 用 len/12 会高估持有期、低估年化（已与开源 QuantStats 基准对齐验证）。
    n_periods = max(len(result_df) - 1, 1)
    years = n_periods / 12.0
    annualized = (1 + cum_return) ** (1 / years) - 1 if years > 0 and cum_return > -1 else 0.0

    # 提取相关
    withdrawal_months = int((result_df["withdrawal_amount"] > 0).sum())

    metrics: dict[str, Any] = {
        "final_total_value": final_total,
        "net_invested": net_invested,
        "invested_total": invested_total,
        "cum_return": cum_return,
        "annualized_return": annualized,
        "max_drawdown": _max_drawdown(result_df["total_value"]),
        "withdrawn_total": withdrawn_total,
        "withdrawal_months": withdrawal_months,
        "depleted": bool(result_df.attrs.get("depleted", False)),
        "depleted_date": result_df.attrs.get("depleted_date"),
        "equity_ratio_mean": float(result_df["equity_ratio"].mean()),
        "equity_ratio_max": float(result_df["equity_ratio"].max()),
        "equity_ratio_min": float(result_df["equity_ratio"].min()),
        "rebalance_count": int(result_df.attrs.get("rebalance_count", 0)),
    }

    # 实际年提取额 / 初始本金
    if cfg.initial_capital > 0 and withdrawal_months > 0:
        annual_withdraw = withdrawn_total / (withdrawal_months / 12.0)
        metrics["annual_withdraw_over_capital"] = annual_withdraw / cfg.initial_capital
    else:
        metrics["annual_withdraw_over_capital"] = 0.0

    # 清仓详情
    liq = result_df.attrs.get("liquidation_record")
    if liq:
        metrics.update(
            {
                "liquidation_date": liq["liquidation_date"],
                "liquidation_total_value": liq["liquidation_total_value"],
                "liquidation_equity_ratio": liq["liquidation_equity_ratio"],
                "liquidation_amount": liq["liquidation_amount"],
                "liquidation_cum_return": liq["liquidation_cum_return"],
                "remaining_after_liquidation": liq["remaining_after_liquidation"],
            }
        )

    # glide 降仓时记录清仓前股票比例变化
    if cfg.liquidation_enabled and cfg.liquidation_mode == "glide":
        glide_months = cfg.liquidation_glide_years * 12
        tail = result_df["target_equity_ratio"].tail(glide_months)
        metrics["glide_equity_ratio_path"] = tail.round(4).tolist()

    return metrics
