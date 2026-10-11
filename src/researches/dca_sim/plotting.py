"""绘图层：根据引擎输出的月度结果绘制盈亏曲线。

与引擎、指标解耦，只消费结果 DataFrame。matplotlib 为可选依赖，
缺失时抛出清晰错误而非静默失败。

免责声明：图表仅用于逻辑验证，不构成投资建议。
"""

from __future__ import annotations

import os

import pandas as pd

from .config import SimConfig

# 常用中文字体，避免图中中文乱码（按可用性回退）
_CJK_FONTS = ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC", "sans-serif"]


def _prepare_matplotlib():
    """导入并配置 matplotlib，返回 pyplot 模块。"""
    try:
        import matplotlib
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - 可选依赖
        raise RuntimeError("绘图需要安装 matplotlib") from exc

    matplotlib.rcParams["font.sans-serif"] = _CJK_FONTS
    matplotlib.rcParams["axes.unicode_minus"] = False
    return plt


def plot_pnl(
    result_df: pd.DataFrame,
    cfg: SimConfig,
    name: str = "",
    save_path: str | None = None,
    show: bool = False,
):
    """绘制盈亏曲线。

    上图：总资产 vs 累计净投入（成本线），填充盈亏区域并标注清仓点。
    下图：累计收益率曲线。

    参数
    ------
    result_df : 引擎 ``run()`` 的输出
    cfg       : 对应的配置，用于标题与清仓标注
    name      : 场景名，用于标题与文件名
    save_path : 若提供则把图保存到该目录
    show      : 是否弹窗显示（服务器/批处理环境应为 False）

    返回保存的文件路径（未保存时返回 None）。
    """
    if result_df.empty:
        raise ValueError("结果为空，无法绘图")

    plt = _prepare_matplotlib()

    dates = pd.to_datetime(result_df.index)
    total = result_df["total_value"]
    net_invested = result_df["net_invested"]
    # 累计收益率（逐月）：(当前总资产 + 已提取 - 已投入) / 已投入
    cum_return = (
        (total + result_df["withdrawn_total"] - result_df["invested_total"])
        / result_df["invested_total"].replace(0, pd.NA)
    ).fillna(0.0)

    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(11, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )

    # 上图：资产 vs 成本
    ax_top.plot(dates, total, label="总资产", color="#1f77b4", linewidth=1.8)
    ax_top.plot(
        dates, net_invested, label="累计净投入", color="#888888",
        linewidth=1.2, linestyle="--",
    )
    # 盈亏填充：盈利绿、亏损红
    ax_top.fill_between(
        dates, total, net_invested, where=(total >= net_invested),
        color="#2ca02c", alpha=0.2, interpolate=True, label="盈利区",
    )
    ax_top.fill_between(
        dates, total, net_invested, where=(total < net_invested),
        color="#d62728", alpha=0.2, interpolate=True, label="亏损区",
    )

    # 清仓点标注
    if cfg.liquidation_enabled and bool(result_df["liquidated"].any()):
        liq_date = pd.to_datetime(result_df.index[result_df["liquidated"]][0])
        ax_top.axvline(liq_date, color="#ff7f0e", linestyle=":", linewidth=1.5)
        ax_top.annotate(
            "清仓",
            xy=(liq_date, total.iloc[-1]),
            xytext=(6, 10),
            textcoords="offset points",
            color="#ff7f0e",
        )

    title = f"盈亏曲线 - {name}" if name else "盈亏曲线"
    ax_top.set_title(title)
    ax_top.set_ylabel("金额")
    ax_top.legend(loc="best")
    ax_top.grid(True, alpha=0.3)

    # 下图：累计收益率
    ax_bot.plot(dates, cum_return * 100, color="#9467bd", linewidth=1.4)
    ax_bot.axhline(0, color="#888888", linewidth=0.8)
    ax_bot.set_ylabel("累计收益率 %")
    ax_bot.set_xlabel("日期")
    ax_bot.grid(True, alpha=0.3)

    fig.text(
        0.99, 0.01, "仅用于逻辑验证，不构成投资建议",
        ha="right", va="bottom", fontsize=8, color="#999999",
    )
    fig.tight_layout()

    out_path = None
    if save_path:
        os.makedirs(save_path, exist_ok=True)
        safe_name = name.replace("/", "_") or "pnl"
        out_path = os.path.join(save_path, f"{safe_name}.png")
        fig.savefig(out_path, dpi=120)

    if show:
        plt.show()
    else:
        plt.close(fig)

    return out_path
