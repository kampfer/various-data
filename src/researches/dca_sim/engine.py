"""核心引擎：按月模拟定投、再平衡、动态提取与最终清仓。

``DCASimulator`` 封装一次完整模拟。调用 ``run()`` 返回逐月结果 DataFrame。
引擎只依赖价格序列（份额法记账），与数据来源解耦。

免责声明：模拟结果不构成投资建议。
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from .config import SimConfig
from .data import load_data


class DCASimulator:
    """定投 + 股债配置 + 提取 + 清仓的月度模拟引擎。

    记账采用份额法：持有股票份额与债券份额，市值 = 份额 × 当月净值。
    这样买卖只影响份额，净值波动自然反映在市值上。
    """

    def __init__(self, cfg: SimConfig, prices: pd.DataFrame | None = None) -> None:
        self.cfg = cfg.validate()
        self.prices = prices if prices is not None else load_data(self.cfg)

        # 持仓份额
        self._equity_shares = 0.0
        self._bond_shares = 0.0

        # 累计统计
        self._invested_total = 0.0  # 本金 + 定投累计投入
        self._withdrawn_total = 0.0  # 累计提取
        self._rebalance_count = 0

        # 状态
        self._depleted = False
        self._depleted_date: date | None = None
        self._liquidated = False
        self._liquidation_record: dict | None = None

    # ------------------------------------------------------------------
    # 市值辅助
    # ------------------------------------------------------------------
    def _equity_value(self, eq_price: float) -> float:
        return self._equity_shares * eq_price

    def _bond_value(self, bond_price: float) -> float:
        return self._bond_shares * bond_price

    def _total_value(self, eq_price: float, bond_price: float) -> float:
        return self._equity_value(eq_price) + self._bond_value(bond_price)

    def _buy_equity(self, amount: float, eq_price: float) -> None:
        """买入股票，扣手续费后换算成份额。amount 可为负表示卖出。"""
        if amount == 0:
            return
        fee = abs(amount) * self.cfg.fee_rate
        net = amount - fee if amount > 0 else amount + fee
        self._equity_shares = max(0.0, self._equity_shares + net / eq_price)

    def _buy_bond(self, amount: float, bond_price: float) -> None:
        if amount == 0:
            return
        fee = abs(amount) * self.cfg.fee_rate
        net = amount - fee if amount > 0 else amount + fee
        self._bond_shares = max(0.0, self._bond_shares + net / bond_price)

    # ------------------------------------------------------------------
    # 目标股票比例（含降仓逻辑）
    # ------------------------------------------------------------------
    def _target_equity_ratio(self, current: date) -> float:
        """返回当月目标股票比例，考虑 glide 降仓。"""
        base = self.cfg.equity_ratio
        if not (self.cfg.liquidation_enabled and self.cfg.liquidation_mode == "glide"):
            return base

        liq_date = self.cfg.liquidation_date_obj
        months_left = (liq_date.year - current.year) * 12 + (
            liq_date.month - current.month
        )
        glide_months = self.cfg.liquidation_glide_years * 12
        if months_left >= glide_months:
            return base  # 还没进入降仓窗口
        if months_left <= 0:
            return self.cfg.liquidation_glide_equity_target

        start_ratio = (
            self.cfg.liquidation_glide_start_ratio
            if self.cfg.liquidation_glide_start_ratio is not None
            else base
        )
        target = self.cfg.liquidation_glide_equity_target
        # 线性插值：进入窗口时 = start_ratio，到期时 = target
        progress = (glide_months - months_left) / glide_months
        return start_ratio + (target - start_ratio) * progress

    # ------------------------------------------------------------------
    # 提取金额
    # ------------------------------------------------------------------
    def _withdrawal_amount(
        self, current: date, total: float, elapsed_years: float
    ) -> float:
        """计算当月提取额（基础额 + 通胀调整 + 动态调整）。

        提取总开关关闭时直接返回 0，不做任何提取。
        """
        if not self.cfg.withdrawal_enabled:
            return 0.0
        if current < self.cfg.withdrawal_start_date or total <= 0:
            return 0.0

        if self.cfg.withdrawal_mode == "amount":
            base = self.cfg.withdrawal_amount
        else:
            base = self.cfg.initial_capital * self.cfg.withdrawal_rate / 12.0

        # 通胀调整
        if self.cfg.withdrawal_inflation_adjust:
            base *= (1 + self.cfg.withdrawal_inflation_adjust) ** elapsed_years

        # 动态调整：资产相对初始本金的表现影响提取额
        if self.cfg.withdrawal_dynamic and self.cfg.initial_capital > 0:
            ratio = total / self.cfg.initial_capital
            factor = ratio ** (1.0 / self.cfg.withdrawal_dynamic_strength)
            factor = max(
                self.cfg.withdrawal_dynamic_min,
                min(self.cfg.withdrawal_dynamic_max, factor),
            )
            base *= factor

        return min(base, total)

    # ------------------------------------------------------------------
    # 再平衡
    # ------------------------------------------------------------------
    def _rebalance(
        self, target_ratio: float, eq_price: float, bond_price: float, force: bool
    ) -> None:
        """把股票比例恢复到 target_ratio。force=True 时忽略阈值强制执行。"""
        total = self._total_value(eq_price, bond_price)
        if total <= 0:
            return
        current_ratio = self._equity_value(eq_price) / total
        if not force and abs(current_ratio - target_ratio) <= self.cfg.rebalance_band:
            return
        desired_equity = total * target_ratio
        delta = desired_equity - self._equity_value(eq_price)
        self._buy_equity(delta, eq_price)
        self._buy_bond(-delta, bond_price)
        self._rebalance_count += 1

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    def run(self) -> pd.DataFrame:
        """执行逐月模拟，返回结果 DataFrame。"""
        cfg = self.cfg
        rows: list[dict] = []
        first_date = self.prices.index[0].date()

        # 1. 初始建仓
        if cfg.initial_capital > 0:
            eq0 = float(self.prices.iloc[0]["equity"])
            bond0 = float(self.prices.iloc[0]["bond"])
            self._buy_equity(cfg.initial_capital * cfg.equity_ratio, eq0)
            self._buy_bond(cfg.initial_capital * (1 - cfg.equity_ratio), bond0)
            self._invested_total += cfg.initial_capital

        for ts, row in self.prices.iterrows():
            current: date = ts.date()
            eq_price = float(row["equity"])
            bond_price = float(row["bond"])
            elapsed_years = (current - first_date).days / 365.25

            # 若已清仓，不再有任何交易
            if self._liquidated:
                break

            # 2. 定投
            if cfg.monthly_invest > 0 and not self._depleted:
                self._buy_equity(cfg.monthly_invest * cfg.equity_ratio, eq_price)
                self._buy_bond(
                    cfg.monthly_invest * (1 - cfg.equity_ratio), bond_price
                )
                self._invested_total += cfg.monthly_invest

            # 3. 趋势过滤：股价低于均线则减仓
            if cfg.trend_filter_enabled:
                self._apply_trend_filter(ts, eq_price, bond_price)

            target_ratio = self._target_equity_ratio(current)

            # 4. glide 降仓（强制再平衡到降仓目标比例）
            if (
                cfg.liquidation_enabled
                and cfg.liquidation_mode == "glide"
                and target_ratio != cfg.equity_ratio
            ):
                self._rebalance(target_ratio, eq_price, bond_price, force=True)

            # 5. 提取
            total_before_wd = self._total_value(eq_price, bond_price)
            wd = self._withdrawal_amount(current, total_before_wd, elapsed_years)
            if wd > 0:
                self._withdraw(wd, eq_price, bond_price)
                self._withdrawn_total += wd

            # 耗尽检查
            total_now = self._total_value(eq_price, bond_price)
            if total_now <= 0 and not self._depleted:
                self._depleted = True
                self._depleted_date = current

            # 6. 再平衡（非 glide 窗口才按阈值常规再平衡）
            if not self._depleted:
                self._rebalance(target_ratio, eq_price, bond_price, force=False)

            # 7. 清仓
            liquidated_flag = False
            if (
                cfg.liquidation_enabled
                and current >= cfg.liquidation_date_obj
                and not self._liquidated
            ):
                liquidated_flag = self._liquidate(current, eq_price, bond_price)

            # 9. 记录
            # 清仓当行：资产已被清零，但指标须以“清仓时点”为准，
            # 因此记录清仓前的市值快照（保存在 _liquidation_record 中）。
            if liquidated_flag and self._liquidation_record is not None:
                rec = self._liquidation_record
                equity_value = rec["liquidation_equity_value"]
                bond_value = rec["liquidation_bond_value"]
                total_value = rec["liquidation_total_value"]
                equity_ratio = rec["liquidation_equity_ratio"]
            else:
                equity_value = self._equity_value(eq_price)
                bond_value = self._bond_value(bond_price)
                total_value = equity_value + bond_value
                equity_ratio = equity_value / total_value if total_value > 0 else 0.0

            rows.append(
                {
                    "date": current,
                    "equity_value": equity_value,
                    "bond_value": bond_value,
                    "total_value": total_value,
                    "invested_total": self._invested_total,
                    "withdrawn_total": self._withdrawn_total,
                    "net_invested": self._invested_total - self._withdrawn_total,
                    "equity_ratio": equity_ratio,
                    "withdrawal_amount": wd,
                    "target_equity_ratio": target_ratio,
                    "liquidated": liquidated_flag,
                }
            )

            if liquidated_flag:
                break

        result = pd.DataFrame(rows).set_index("date")
        result.attrs["depleted"] = self._depleted
        result.attrs["depleted_date"] = self._depleted_date
        result.attrs["rebalance_count"] = self._rebalance_count
        result.attrs["liquidation_record"] = self._liquidation_record
        return result

    # ------------------------------------------------------------------
    # 子操作
    # ------------------------------------------------------------------
    def _apply_trend_filter(self, ts, eq_price: float, bond_price: float) -> None:
        """当股价低于 N 日（此处为月）均线时，把股票仓位乘以 reduce_to。"""
        window = max(1, self.cfg.trend_filter_ma_window // 21)  # 近似月窗口
        hist = self.prices.loc[:ts, "equity"]
        if len(hist) < window:
            return
        ma = hist.tail(window).mean()
        if eq_price < ma:
            total = self._total_value(eq_price, bond_price)
            target_eq_value = self._equity_value(eq_price) * self.cfg.trend_filter_reduce_to
            delta = target_eq_value - self._equity_value(eq_price)
            self._buy_equity(delta, eq_price)
            self._buy_bond(-delta, bond_price)

    def _withdraw(self, amount: float, eq_price: float, bond_price: float) -> None:
        """按当前股债市值比例卖出以满足提取额。"""
        total = self._total_value(eq_price, bond_price)
        if total <= 0:
            return
        eq_share = self._equity_value(eq_price) / total
        self._buy_equity(-amount * eq_share, eq_price)
        self._buy_bond(-amount * (1 - eq_share), bond_price)

    def _liquidate(self, current: date, eq_price: float, bond_price: float) -> bool:
        """一次性卖出全部资产，记录清仓详情。"""
        equity_value = self._equity_value(eq_price)
        bond_value = self._bond_value(bond_price)
        total = equity_value + bond_value
        eq_ratio_at_liq = equity_value / total if total > 0 else 0.0
        cum_return = (
            (total + self._withdrawn_total - self._invested_total) / self._invested_total
            if self._invested_total > 0
            else 0.0
        )
        self._equity_shares = 0.0
        self._bond_shares = 0.0
        self._liquidated = True
        self._liquidation_record = {
            "liquidation_date": current,
            "liquidation_equity_value": equity_value,
            "liquidation_bond_value": bond_value,
            "liquidation_total_value": total,
            "liquidation_equity_ratio": eq_ratio_at_liq,
            "liquidation_amount": total,
            "liquidation_cum_return": cum_return,
            "remaining_after_liquidation": 0.0,
        }
        return True
