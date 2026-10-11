"""预设场景：覆盖不同清仓时点与降仓策略，便于横向对比。

免责声明：场景仅用于逻辑验证，不构成投资建议。
"""

from __future__ import annotations

from .config import SimConfig

SCENARIOS: dict[str, SimConfig] = {
    "A_纯定投_不清仓": SimConfig(
        initial_capital=0,
        monthly_invest=1000,
        equity_ratio=0.6,
        data_start="2015-01-01",
        data_end="2025-12-31",
    ),
    "B_300万_4%_股3债7_不清仓": SimConfig(
        initial_capital=3_000_000,
        equity_ratio=0.3,
        withdrawal_mode="rate",
        withdrawal_rate=0.04,
        withdrawal_start="2015-02-01",
        data_start="2015-01-01",
        data_end="2025-12-31",
    ),
    "C_300万_4%_股3债7_2022清仓": SimConfig(
        initial_capital=3_000_000,
        equity_ratio=0.3,
        withdrawal_mode="rate",
        withdrawal_rate=0.04,
        withdrawal_start="2015-02-01",
        liquidation_enabled=True,
        liquidation_mode="lump",
        liquidation_date="2022-01-01",
        data_start="2015-01-01",
        data_end="2025-12-31",
    ),
    "D_300万_4%_股3债7_2025清仓": SimConfig(
        initial_capital=3_000_000,
        equity_ratio=0.3,
        withdrawal_mode="rate",
        withdrawal_rate=0.04,
        withdrawal_start="2015-02-01",
        liquidation_enabled=True,
        liquidation_mode="lump",
        liquidation_date="2025-01-01",
        data_start="2015-01-01",
        data_end="2025-12-31",
    ),
    "E_300万_4%_股3债7_2025清仓_前5年降仓": SimConfig(
        initial_capital=3_000_000,
        equity_ratio=0.3,
        withdrawal_mode="rate",
        withdrawal_rate=0.04,
        withdrawal_start="2015-02-01",
        liquidation_enabled=True,
        liquidation_mode="glide",
        liquidation_date="2025-01-01",
        liquidation_glide_years=5,
        liquidation_glide_equity_target=0.0,
        data_start="2015-01-01",
        data_end="2025-12-31",
    ),
    "F_300万_4%_股6债4_2025清仓": SimConfig(
        initial_capital=3_000_000,
        equity_ratio=0.6,
        withdrawal_mode="rate",
        withdrawal_rate=0.04,
        withdrawal_start="2015-02-01",
        liquidation_enabled=True,
        liquidation_mode="lump",
        liquidation_date="2025-01-01",
        data_start="2015-01-01",
        data_end="2025-12-31",
    ),
    "G_350万_3.43%_股3债7_2025清仓_前5年降仓": SimConfig(
        initial_capital=3_500_000,
        equity_ratio=0.3,
        withdrawal_mode="rate",
        withdrawal_rate=0.0343,
        withdrawal_start="2015-02-01",
        liquidation_enabled=True,
        liquidation_mode="glide",
        liquidation_date="2025-01-01",
        liquidation_glide_years=5,
        liquidation_glide_equity_target=0.0,
        data_start="2015-01-01",
        data_end="2025-12-31",
    ),
}
