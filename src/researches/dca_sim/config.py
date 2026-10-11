"""参数配置模块。

提供 ``SimConfig`` 数据类以及 YAML / 命令行 / 代码三种配置来源的解析与合并。
优先级：命令行 > 配置文件 > 默认值。

本模块只负责配置的加载、合并与校验，不涉及任何业务逻辑，保持高内聚低耦合。

免责声明：本项目所有结果仅用于逻辑验证，不构成投资建议。
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field, fields, replace
from datetime import date
from typing import Any, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - 可选依赖
    yaml = None  # type: ignore


def _parse_date(value: str | date) -> date:
    """把字符串或 ``date`` 统一转成 ``date``。"""
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _normalize_symbol_list(value) -> list[str]:
    """把标的配置统一成去空去重的字符串列表（保序）。

    接受：列表/元组、单个字符串、逗号或空格分隔的字符串。
    """
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = [value]
    else:
        raw_items = [str(v) for v in value]
    # 对每个元素再按分隔符拆分，兼容“列表里塞了分隔串”的情况，
    # 并容忍半角逗号、全角逗号“，”、中文顿号“、”等常见误用：
    # 例如 ['510300，159361、512100'] -> ['510300', '159361', '512100']
    def _split(raw: str) -> list[str]:
        for sep in (",", "，", "、", ";", "；"):
            raw = raw.replace(sep, " ")
        return raw.split()

    items = [token for raw in raw_items for token in _split(raw)]
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        s = item.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result


def _subtract_years(d: date, years: int) -> date:
    """从日期减去若干年，正确处理闰年 2月29日（回退到 2月28日）。"""
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        # 仅发生在 d 为 2月29日而目标年非闰年时
        return d.replace(year=d.year - years, day=28)

@dataclass
class SimConfig:
    """模拟器的全部可配置参数。

    字段与 ``config.yaml`` 一一对应。嵌套的 YAML 结构在此被展平，
    便于命令行与代码传参统一处理。
    """

    # 本金与投入
    initial_capital: float = 0
    monthly_invest: float = 5000

    # 提取设置
    withdrawal_enabled: bool = False  # 提取总开关，关闭时完全不提取
    withdrawal_mode: str = "amount"  # "rate" | "amount"
    withdrawal_rate: float = 0.04
    withdrawal_amount: float = 6000.0
    withdrawal_start: str = "2021-08-02"
    withdrawal_inflation_adjust: float = 0.0
    withdrawal_dynamic: bool = False
    withdrawal_dynamic_strength: float = 2.0
    withdrawal_dynamic_min: float = 0.5
    withdrawal_dynamic_max: float = 1.5

    # 资产配置
    equity_ratio: float = 0.3
    rebalance_band: float = 0.05
    fee_rate: float = 0.0

    # 清仓设置
    liquidation_enabled: bool = False
    liquidation_mode: str = "lump"  # "lump" | "glide"
    liquidation_date: str = "2030-01-01"
    liquidation_glide_years: int = 5
    liquidation_glide_equity_target: float = 0.0
    liquidation_glide_start_ratio: Optional[float] = None

    # 数据
    data_source: str = "real"  # "simulated" | "real"
    data_start: str = "2021-08-02"
    data_end: str = "2025-12-31"
    data_seed: int = 42
    # 真实数据标的（source=real 时生效），股/债各为一篮子，等权合成为一条净值。
    # 默认股票篮子=沪深300ETF，债券篮子=国债ETF。
    data_equity_symbols: list[str] = field(default_factory=lambda: ["510300", "512100", "510050", "510300", "510500", "512100"])
    data_bond_symbols: list[str] = field(default_factory=lambda: ["511010"])

    # 趋势过滤
    trend_filter_enabled: bool = False
    trend_filter_ma_window: int = 200
    trend_filter_reduce_to: float = 0.5

    # 输出
    output_print_table: bool = True
    output_save_csv: bool = False
    output_plot: bool = True
    output_plot_path: str = "output/"

    # ------------------------------------------------------------------
    # 规整
    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        """把标的字段统一成去空、去重后的字符串列表。

        容忍三种输入：列表、单个字符串、逗号/空格分隔的字符串。
        """
        self.data_equity_symbols = _normalize_symbol_list(self.data_equity_symbols)
        self.data_bond_symbols = _normalize_symbol_list(self.data_bond_symbols)

    # ------------------------------------------------------------------
    # 便捷属性
    # ------------------------------------------------------------------
    @property
    def start_date(self) -> date:
        return _parse_date(self.data_start)

    @property
    def end_date(self) -> date:
        return _parse_date(self.data_end)

    @property
    def withdrawal_start_date(self) -> date:
        return _parse_date(self.withdrawal_start)

    @property
    def liquidation_date_obj(self) -> date:
        return _parse_date(self.liquidation_date)

    # ------------------------------------------------------------------
    # 构造与合并
    # ------------------------------------------------------------------
    @classmethod
    def from_yaml(cls, path: str) -> "SimConfig":
        """从 YAML 文件加载配置（嵌套结构会被展平）。"""
        if yaml is None:
            raise ImportError("需要安装 pyyaml 才能读取 YAML 配置文件")
        with open(path, "r", encoding="utf-8") as fp:
            raw = yaml.safe_load(fp) or {}
        return cls.from_dict(cls._flatten_yaml(raw))

    @staticmethod
    def _flatten_yaml(raw: dict[str, Any]) -> dict[str, Any]:
        """把嵌套的 YAML 结构展平成 ``SimConfig`` 的扁平字段名。"""
        flat: dict[str, Any] = {}

        def take(key: str, target: str, container: dict[str, Any]) -> None:
            if key in container:
                flat[target] = container[key]

        take("initial_capital", "initial_capital", raw)
        take("monthly_invest", "monthly_invest", raw)

        w = raw.get("withdrawal", {}) or {}
        take("enabled", "withdrawal_enabled", w)
        take("mode", "withdrawal_mode", w)
        take("rate", "withdrawal_rate", w)
        take("amount", "withdrawal_amount", w)
        take("start_date", "withdrawal_start", w)
        take("inflation_adjust", "withdrawal_inflation_adjust", w)
        take("dynamic", "withdrawal_dynamic", w)
        take("dynamic_strength", "withdrawal_dynamic_strength", w)
        take("dynamic_min", "withdrawal_dynamic_min", w)
        take("dynamic_max", "withdrawal_dynamic_max", w)

        p = raw.get("portfolio", {}) or {}
        take("equity_ratio", "equity_ratio", p)
        take("rebalance_band", "rebalance_band", p)
        take("fee_rate", "fee_rate", p)

        liq = raw.get("liquidation", {}) or {}
        take("enabled", "liquidation_enabled", liq)
        take("mode", "liquidation_mode", liq)
        take("date", "liquidation_date", liq)
        take("glide_years", "liquidation_glide_years", liq)
        take("glide_equity_target", "liquidation_glide_equity_target", liq)
        take("glide_start_ratio", "liquidation_glide_start_ratio", liq)

        d = raw.get("data", {}) or {}
        take("source", "data_source", d)
        take("start", "data_start", d)
        take("end", "data_end", d)
        take("seed", "data_seed", d)
        # 兼容单数 key（单只）与复数 key（一篮子），复数优先
        take("equity_symbol", "data_equity_symbols", d)
        take("equity_symbols", "data_equity_symbols", d)
        take("bond_symbol", "data_bond_symbols", d)
        take("bond_symbols", "data_bond_symbols", d)

        tf = raw.get("trend_filter", {}) or {}
        take("enabled", "trend_filter_enabled", tf)
        take("ma_window", "trend_filter_ma_window", tf)
        take("reduce_to", "trend_filter_reduce_to", tf)

        o = raw.get("output", {}) or {}
        take("print_table", "output_print_table", o)
        take("save_csv", "output_save_csv", o)
        take("plot", "output_plot", o)
        take("plot_path", "output_plot_path", o)

        return flat

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimConfig":
        """从扁平字典构造，忽略未知字段。"""
        valid = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in valid and v is not None}
        return cls(**kwargs)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "SimConfig":
        """从 ``argparse`` 的命名空间构造，仅取显式提供的参数。"""
        return cls.from_dict(cls._args_to_dict(args))

    @staticmethod
    def _args_to_dict(args: argparse.Namespace) -> dict[str, Any]:
        """把命令行参数映射到 ``SimConfig`` 字段，过滤掉未提供（None）的项。"""
        mapping = {
            "initial_capital": "initial_capital",
            "monthly_invest": "monthly_invest",
            "withdrawal_enabled": "withdrawal_enabled",
            "withdrawal_mode": "withdrawal_mode",
            "withdrawal_rate": "withdrawal_rate",
            "withdrawal_amount": "withdrawal_amount",
            "withdrawal_start": "withdrawal_start",
            "equity_ratio": "equity_ratio",
            "rebalance_band": "rebalance_band",
            "fee_rate": "fee_rate",
            "liquidation_enabled": "liquidation_enabled",
            "liquidation_mode": "liquidation_mode",
            "liquidation_date": "liquidation_date",
            "liquidation_glide_years": "liquidation_glide_years",
            "liquidation_glide_equity_target": "liquidation_glide_equity_target",
            "output_plot": "output_plot",
            "data_source": "data_source",
            "start": "data_start",
            "end": "data_end",
            "seed": "data_seed",
            "data_equity_symbols": "data_equity_symbols",
            "data_bond_symbols": "data_bond_symbols",
        }
        result: dict[str, Any] = {}
        for arg_name, field_name in mapping.items():
            value = getattr(args, arg_name, None)
            if value is not None:
                result[field_name] = value
        return result

    @staticmethod
    def merge(base: "SimConfig", override: dict[str, Any]) -> "SimConfig":
        """用 ``override`` 中的非 None 字段覆盖 ``base``，返回新实例。"""
        valid = {f.name for f in fields(SimConfig)}
        changes = {k: v for k, v in override.items() if k in valid and v is not None}
        return replace(base, **changes)

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------
    def validate(self) -> "SimConfig":
        """校验参数合法性，失败时抛出 ``ValueError`` 并一次性列出所有问题。

        校验分三类：单字段取值范围、字段间的交叉关系、以及日期区间关系。
        所有错误会汇总后一次抛出，而非遇到第一个就中断。
        """
        errors: list[str] = []
        self._validate_ranges(errors)
        start_dt, end_dt = self._validate_date_range(errors)
        self._validate_withdrawal(errors, start_dt, end_dt)
        self._validate_liquidation(errors, start_dt, end_dt)
        self._validate_funding_semantics(errors)

        if errors:
            raise ValueError("配置校验失败：\n  - " + "\n  - ".join(errors))
        return self

    # ------------------------------------------------------------------
    # 校验子项（高内聚：每个方法只管一类校验）
    # ------------------------------------------------------------------
    def _validate_ranges(self, errors: list[str]) -> None:
        """单字段取值范围校验。"""
        if self.initial_capital < 0:
            errors.append("initial_capital 必须 >= 0")
        if self.monthly_invest < 0:
            errors.append("monthly_invest 必须 >= 0")
        if not (0.0 <= self.equity_ratio <= 1.0):
            errors.append("equity_ratio 必须在 0 到 1 之间")
        if not (0.0 <= self.withdrawal_rate <= 0.15):
            errors.append("withdrawal_rate 必须在 0 到 0.15 之间")
        if not (0.0 <= self.rebalance_band <= 1.0):
            errors.append("rebalance_band 必须在 0 到 1 之间")
        if not (0.0 <= self.fee_rate <= 1.0):
            errors.append("fee_rate 必须在 0 到 1 之间")
        if self.withdrawal_inflation_adjust < 0:
            errors.append("withdrawal_inflation_adjust（通胀率）必须 >= 0")

    def _parse_date_safe(
        self, value: str, field_name: str, errors: list[str]
    ):
        """安全解析日期，格式非法时记录错误并返回 None。"""
        try:
            return _parse_date(value)
        except ValueError:
            errors.append(f"{field_name} 日期格式非法（应为 YYYY-MM-DD）：{value!r}")
            return None

    def _validate_date_range(self, errors: list[str]):
        """校验 start/end 本身及其先后关系，返回 (start_dt, end_dt)（可能为 None）。"""
        start_dt = self._parse_date_safe(self.data_start, "start", errors)
        end_dt = self._parse_date_safe(self.data_end, "end", errors)
        if start_dt and end_dt and start_dt >= end_dt:
            errors.append(f"start 必须早于 end（start={start_dt}, end={end_dt}）")
        return start_dt, end_dt

    def _validate_withdrawal(self, errors: list[str], start_dt, end_dt) -> None:
        """提取相关校验，含提取日期与模拟区间的交叉关系。"""
        if self.withdrawal_mode not in ("rate", "amount"):
            errors.append("withdrawal_mode 只能是 rate 或 amount")
        if self.withdrawal_mode == "amount" and self.withdrawal_amount <= 0:
            errors.append("withdrawal_mode=amount 时 amount 必须 > 0")

        # 动态提取参数
        if self.withdrawal_dynamic:
            if self.withdrawal_dynamic_strength <= 0:
                errors.append("withdrawal_dynamic_strength 必须 > 0")
            if self.withdrawal_dynamic_min > self.withdrawal_dynamic_max:
                errors.append(
                    "withdrawal_dynamic_min 不能大于 withdrawal_dynamic_max"
                )

        # 提取未启用则不校验提取日期
        if not self.withdrawal_enabled:
            return

        wd_dt = self._parse_date_safe(
            self.withdrawal_start, "withdrawal.start_date", errors
        )
        if wd_dt is None or start_dt is None or end_dt is None:
            return
        # 提取日期必须落在模拟区间内，否则要么提没数据的日子、要么永远提不到
        if wd_dt < start_dt:
            errors.append(
                f"提取起始日 {wd_dt} 早于模拟起点 {start_dt}："
                "无法在没有数据的区间提取，请把 withdrawal.start_date 调到 start 之后"
            )
        if wd_dt > end_dt:
            errors.append(
                f"提取起始日 {wd_dt} 晚于模拟终点 {end_dt}："
                "整个模拟区间内都不会发生提取，请检查 withdrawal.start_date 或延长 end"
            )

    def _validate_liquidation(self, errors: list[str], start_dt, end_dt) -> None:
        """清仓相关校验，含清仓日期、降仓窗口与模拟区间的交叉关系。"""
        if not self.liquidation_enabled:
            return

        if self.liquidation_mode not in ("lump", "glide"):
            errors.append("liquidation_mode 只能是 lump 或 glide")

        liq_dt = self._parse_date_safe(
            self.liquidation_date, "liquidation.date", errors
        )
        if liq_dt is not None and start_dt is not None and end_dt is not None:
            if not (start_dt <= liq_dt <= end_dt):
                errors.append(
                    f"清仓日 {liq_dt} 必须在 start({start_dt}) 和 end({end_dt}) 之间"
                )

        if self.liquidation_mode == "glide":
            if self.liquidation_glide_years <= 0:
                errors.append("glide 模式下 liquidation_glide_years 必须 > 0")
            if not (0.0 <= self.liquidation_glide_equity_target <= 1.0):
                errors.append("glide_equity_target 必须在 0 到 1 之间")
            if self.liquidation_glide_start_ratio is not None and not (
                0.0 <= self.liquidation_glide_start_ratio <= 1.0
            ):
                errors.append("glide_start_ratio 必须在 0 到 1 之间")
            # 降仓窗口起点不能早于模拟起点，否则降仓期落在无数据区间
            if (
                liq_dt is not None
                and start_dt is not None
                and self.liquidation_glide_years > 0
            ):
                glide_start = _subtract_years(liq_dt, self.liquidation_glide_years)
                if glide_start < start_dt:
                    errors.append(
                        f"glide 降仓窗口起点 {glide_start}（清仓日前 "
                        f"{self.liquidation_glide_years} 年）早于模拟起点 {start_dt}："
                        "请缩短 glide_years 或提前 start"
                    )

    def _validate_funding_semantics(self, errors: list[str]) -> None:
        """资金来源语义校验：既无本金也无定投却要提取，没有意义。"""
        if (
            self.withdrawal_enabled
            and self.initial_capital <= 0
            and self.monthly_invest <= 0
        ):
            errors.append(
                "既无初始本金也无月定投，却启用了提取：没有资金来源可供提取，"
                "请设置 initial_capital/monthly_invest 或关闭提取"
            )
