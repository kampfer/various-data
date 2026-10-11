"""入口：解析命令行 / YAML，运行单场景或批量场景，打印绩效指标。

用法示例：
    python -m dca_sim.main --scenario E_300万_4%_股3债7_2025清仓_前5年降仓
    python -m dca_sim.main --all-scenarios
    python -m dca_sim.main --config config.yaml
    python -m dca_sim.main --initial-capital 3000000 --withdrawal-rate 0.04 \
        --liquidation-enabled --liquidation-mode glide --liquidation-date 2025-01-01

免责声明：所有结果仅用于逻辑验证，不构成投资建议。
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

# 支持直接 `python main.py` 运行（补足包导入路径）
if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dca_sim.config import SimConfig
    from dca_sim.engine import DCASimulator
    from dca_sim.metrics import performance
    from dca_sim.scenarios import SCENARIOS
else:
    from .config import SimConfig
    from .engine import DCASimulator
    from .metrics import performance
    from .scenarios import SCENARIOS


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器。所有参数默认 None，便于与 YAML/默认值合并。"""
    p = argparse.ArgumentParser(description="定投-股债配置-清仓模拟器")
    p.add_argument("--config", type=str, help="YAML 配置文件路径")
    p.add_argument("--scenario", type=str, help="运行单个预设场景")
    p.add_argument("--all-scenarios", action="store_true", help="批量运行所有预设场景")
    p.add_argument(
        "--validate",
        action="store_true",
        help="用开源库 QuantStats 对比校验手写指标（有差异则手写视为 BUG）",
    )
    p.add_argument(
        "--validate-tolerance",
        dest="validate_tolerance",
        type=float,
        default=1e-6,
        help="校验容差，默认 1e-6",
    )

    p.add_argument("--initial-capital", dest="initial_capital", type=float)
    p.add_argument("--monthly-invest", dest="monthly_invest", type=float)
    p.add_argument(
        "--withdrawal-enabled",
        dest="withdrawal_enabled",
        action="store_const",
        const=True,
        default=None,
        help="启用提取（默认启用）",
    )
    p.add_argument(
        "--no-withdrawal",
        dest="withdrawal_enabled",
        action="store_const",
        const=False,
        help="关闭提取（完全不提取）",
    )
    p.add_argument("--withdrawal-mode", dest="withdrawal_mode", choices=["rate", "amount"])
    p.add_argument("--withdrawal-rate", dest="withdrawal_rate", type=float)
    p.add_argument("--withdrawal-amount", dest="withdrawal_amount", type=float)
    p.add_argument("--withdrawal-start", dest="withdrawal_start", type=str)
    p.add_argument("--equity-ratio", dest="equity_ratio", type=float)
    p.add_argument("--rebalance-band", dest="rebalance_band", type=float)
    p.add_argument("--fee-rate", dest="fee_rate", type=float)

    p.add_argument(
        "--liquidation-enabled",
        dest="liquidation_enabled",
        action="store_const",
        const=True,
        default=None,
        help="启用清仓",
    )
    p.add_argument("--liquidation-mode", dest="liquidation_mode", choices=["lump", "glide"])
    p.add_argument("--liquidation-date", dest="liquidation_date", type=str)
    p.add_argument("--liquidation-glide-years", dest="liquidation_glide_years", type=int)
    p.add_argument(
        "--liquidation-glide-equity-target",
        dest="liquidation_glide_equity_target",
        type=float,
    )

    p.add_argument(
        "--plot",
        dest="output_plot",
        action="store_const",
        const=True,
        default=None,
        help="生成并保存盈亏曲线 PNG",
    )
    p.add_argument("--data-source", dest="data_source", choices=["simulated", "real"])
    p.add_argument(
        "--equity-symbol",
        "--equity-symbols",
        dest="data_equity_symbols",
        nargs="+",
        help="股票篮子 ETF 代码，可多只等权（如 510300 159915）",
    )
    p.add_argument(
        "--bond-symbol",
        "--bond-symbols",
        dest="data_bond_symbols",
        nargs="+",
        help="债券篮子 ETF 代码，可多只等权（如 511010 511260）",
    )
    p.add_argument("--start", dest="start", type=str)
    p.add_argument("--end", dest="end", type=str)
    p.add_argument("--seed", dest="seed", type=int)
    return p


def resolve_config(args: argparse.Namespace) -> SimConfig:
    """按优先级（命令行 > YAML > 默认）合并出最终配置。"""
    base = SimConfig()
    if args.config:
        base = SimConfig.from_yaml(args.config)
    cli = SimConfig._args_to_dict(args)
    return SimConfig.merge(base, cli)


def _fmt_money(value: float) -> str:
    return f"{value:,.2f}"


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def print_report(name: str, cfg: SimConfig, metrics: dict[str, Any]) -> None:
    """按规格说明书格式打印单场景报告。"""
    print(f"\n===== 场景: {name} =====")
    print(f"初始本金:        {_fmt_money(cfg.initial_capital)}")
    if not cfg.withdrawal_enabled:
        print("提取设置:        不提取")
    elif cfg.withdrawal_mode == "rate":
        print(f"年提取率:        {_fmt_pct(cfg.withdrawal_rate)}")
        print(f"月提取额:        {_fmt_money(cfg.initial_capital * cfg.withdrawal_rate / 12)}")
    else:
        print(f"月提取额(固定):  {_fmt_money(cfg.withdrawal_amount)}")
    print(
        f"目标股债比:      {cfg.equity_ratio * 100:.0f}% / "
        f"{(1 - cfg.equity_ratio) * 100:.0f}%"
    )
    if cfg.liquidation_enabled:
        if cfg.liquidation_mode == "glide":
            print(
                f"清仓模式:        glide（前{cfg.liquidation_glide_years}年降仓至"
                f"{cfg.liquidation_glide_equity_target * 100:.0f}%）"
            )
        else:
            print("清仓模式:        lump（一次性清仓）")
        print(f"清仓日期:        {cfg.liquidation_date}")
    else:
        print("清仓模式:        不清仓")
    print(f"模拟区间:        {cfg.data_start} ~ {cfg.data_end}")

    print(f"最终总资产:      {_fmt_money(metrics['final_total_value'])}")
    print(f"累计提取:        {_fmt_money(metrics['withdrawn_total'])}")
    print(f"累计收益率:      {_fmt_pct(metrics['cum_return'])}")
    print(f"年化收益率:      {_fmt_pct(metrics['annualized_return'])}")
    print(f"最大回撤:        {_fmt_pct(metrics['max_drawdown'])}")
    depleted = "是" if metrics["depleted"] else "否"
    print(f"是否耗尽:        {depleted}")
    if metrics["depleted"]:
        print(f"耗尽日期:        {metrics['depleted_date']}")
    print(f"股票占比均值:    {_fmt_pct(metrics['equity_ratio_mean'])}")
    print(f"再平衡次数:      {metrics['rebalance_count']}")

    if "liquidation_date" in metrics:
        print("--- 清仓详情 ---")
        print(f"清仓日期:        {metrics['liquidation_date']}")
        print(f"清仓时总资产:    {_fmt_money(metrics['liquidation_total_value'])}")
        print(f"清仓时股票占比:  {_fmt_pct(metrics['liquidation_equity_ratio'])}")
        print(f"清仓金额:        {_fmt_money(metrics['liquidation_amount'])}")
        print(f"清仓时累计收益:  {_fmt_pct(metrics['liquidation_cum_return'])}")
        print(f"清仓后剩余:      {_fmt_money(metrics['remaining_after_liquidation'])}")

    print("\n（本结果仅用于逻辑验证，不构成投资建议）")


def run_one(name: str, cfg: SimConfig) -> dict[str, Any]:
    """运行单个场景并打印报告，返回绩效指标。"""
    sim = DCASimulator(cfg)
    result = sim.run()
    metrics = performance(result, cfg)
    if cfg.output_print_table:
        print_report(name, cfg, metrics)
    if cfg.output_save_csv:
        os.makedirs(cfg.output_plot_path, exist_ok=True)
        result.to_csv(os.path.join(cfg.output_plot_path, f"{name}.csv"))
    if cfg.output_plot:
        # 延迟导入，避免未启用绘图时强依赖 matplotlib
        if __package__ in (None, ""):
            from dca_sim.plotting import plot_pnl
        else:
            from .plotting import plot_pnl
        out = plot_pnl(result, cfg, name=name, save_path=cfg.output_plot_path)
        if out:
            print(f"盈亏曲线已保存:  {out}")
    return metrics


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.validate:
        if __package__ in (None, ""):
            from dca_sim.benchmark import run_validation, format_report
        else:
            from .benchmark import run_validation, format_report
        all_pass, comparisons = run_validation(tolerance=args.validate_tolerance)
        print(format_report(comparisons))
        if all_pass:
            print("\n✅ 全部指标与开源基准一致，手写实现可采信。")
        else:
            print("\n❌ 存在差异：手写实现疑似 BUG，不采信手写结果，以开源基准为准。")
            raise SystemExit(1)
        return

    if args.all_scenarios:
        for name, cfg in SCENARIOS.items():
            run_one(name, cfg)
        return

    if args.scenario:
        if args.scenario not in SCENARIOS:
            raise SystemExit(
                f"未知场景：{args.scenario}。可选：{', '.join(SCENARIOS)}"
            )
        run_one(args.scenario, SCENARIOS[args.scenario])
        return

    cfg = resolve_config(args)
    run_one("自定义", cfg)


if __name__ == "__main__":
    main()
