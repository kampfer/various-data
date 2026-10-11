"""数据层：提供股票与债券的月度价格序列。

两个来源：
    - ``simulated``：几何布朗运动模拟，仅用于逻辑验证。
    - ``real``：通过 tdx（迅投）获取可配置的股票/债券前复权净值，失败或数据不足时抛异常。

返回的 DataFrame 以月末日期为索引，包含 ``equity`` 和 ``bond`` 两列净值。

免责声明：模拟数据不构成投资建议。
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from .config import _normalize_symbol_list

# 模拟参数（年化）
_EQUITY_MU = 0.08
_EQUITY_SIGMA = 0.22
_BOND_MU = 0.035
_BOND_SIGMA = 0.04
_MONTHS_PER_YEAR = 12


def _month_ends(start: date, end: date) -> pd.DatetimeIndex:
    """生成从 start 到 end 的月末日期索引。"""
    return pd.date_range(start=start, end=end, freq="ME")


def _gbm_path(
    n: int, mu: float, sigma: float, rng: np.random.Generator
) -> np.ndarray:
    """生成几何布朗运动的净值路径（起点为 1.0），长度为 n。"""
    dt = 1.0 / _MONTHS_PER_YEAR
    drift = (mu - 0.5 * sigma**2) * dt
    shock = sigma * np.sqrt(dt) * rng.standard_normal(n)
    log_returns = drift + shock
    nav = np.empty(n)
    nav[0] = 1.0
    nav[1:] = np.exp(np.cumsum(log_returns[1:]))
    return nav


def get_simulated_data(start: date, end: date, seed: int) -> pd.DataFrame:
    """用几何布朗运动模拟股票与债券的月度净值。

    股票年化 8% / 波动 22%；债券年化 3.5% / 波动 4%。
    """
    idx = _month_ends(start, end)
    n = len(idx)
    if n == 0:
        raise ValueError("模拟区间内没有月末交易点，请检查 start/end")
    rng = np.random.default_rng(seed)
    equity = _gbm_path(n, _EQUITY_MU, _EQUITY_SIGMA, rng)
    bond = _gbm_path(n, _BOND_MU, _BOND_SIGMA, rng)
    return pd.DataFrame({"equity": equity, "bond": bond}, index=idx)


# 日期容差：请求区间两端允许的偏差（自然日）。
# ETF/股票首个交易日通常不是 1 号，月末也可能逢节假日，留一点缓冲避免误报。
_DATE_TOLERANCE_DAYS = 10
# 月末采样点允许缺失的比例（如个别月停牌），超过则判定数据不足。
_MONTH_COVERAGE_MIN = 0.98


def _infer_market(code: str) -> str:
    """根据 6 位裸代码推断交易所后缀（SH / SZ）。

    判断依据为上交所/深交所的代码段划分（覆盖股票、ETF/基金、可转债）：
      - 沪市(SH)：5xxxxx(基金/ETF)、6xxxxx(股票)、688xxx(科创板)、
        11xxxx/113xxx(可转债)、56/58(ETF)
      - 深市(SZ)：0xxxxx(主板)、2xxxxx(B股)、3xxxxx(创业板)、
        15/16/18xxxx(基金/ETF/LOF，如 159xxx)、12xxxx(可转债)

    规则无法覆盖的（如港股/北交所）请直接在配置里写全后缀。
    """
    if code[:1] in ("5", "6"):
        return "SH"
    if code[:2] in ("11", "13"):
        return "SH"
    if code[:1] in ("0", "2", "3"):
        return "SZ"
    if code[:2] in ("15", "16", "18", "12"):
        return "SZ"
    # 其余无法可靠判断，默认按深市（并由上层数据校验兜底）
    return "SZ"


def _normalize_symbol(symbol: str) -> str:
    """把单个裸代码补成带市场后缀的 tdx 代码（如 510300 -> 510300.SH）。

    已带后缀（含 ``.``）的原样返回；仅对纯数字裸代码推断市场。
    """
    s = symbol.strip().upper()
    if "." in s:
        return s
    return f"{s}.{_infer_market(s)}"


def _expected_month_count(start: date, end: date) -> int:
    """请求区间内应有的月末观测点数量。"""
    return len(pd.date_range(start=start, end=end, freq="ME"))


def _fetch_close_frame(codes: list[str], start: date, end: date) -> pd.DataFrame:
    """用 tdx 一次性批量拉取多只标的的前复权日收盘价宽表。

    tdx 的 ``stock_list`` 支持批量传入，一次请求即可取回全部标的，
    避免逐只调用。返回 index=日期、columns=标的代码的收盘价 DataFrame。
    任一步失败都抛异常。
    """
    from tdx.client import tq

    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    try:
        result = tq.get_market_data(
            field_list=["Close"],
            stock_list=codes,
            start_time=start_str,
            end_time=end_str,
            dividend_type="front",
            period="1d",
        )
    except Exception as exc:  # noqa: BLE001 - 行情接口异常统一上抛
        raise RuntimeError(f"tdx 批量获取 {codes} 失败：{exc}") from exc

    if not result or "Close" not in result:
        raise RuntimeError(f"tdx 返回缺少 Close 字段：{codes}")

    close_df = result["Close"]
    if close_df is None or close_df.empty:
        raise RuntimeError(f"tdx 返回收盘数据为空：{codes}")
    return close_df


def _series_from_frame(
    close_df: pd.DataFrame, code: str, start: date, end: date
) -> pd.Series:
    """从收盘宽表中取出单只标的那一列，清洗成以日期为索引的 Series。

    实测 ``close_df`` 为 index=日期（Timestamp）、columns=标的代码。
    """
    if code not in close_df.columns:
        raise RuntimeError(f"tdx 返回不含标的 {code} 的收盘数据")

    series = close_df[code]
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index)
    series = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    if series.empty:
        start_str = start.strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")
        raise RuntimeError(f"标的 {code} 在 {start_str}~{end_str} 无有效收盘数据")
    return series


def _validate_coverage(symbol: str, series: pd.Series, start: date, end: date) -> None:
    """校验返回数据是否覆盖了请求区间，不足则报错。

    三类不足都会报错：
      1. 实际起点明显晚于请求起点（如标的上市晚、区间无数据）；
      2. 实际终点明显早于请求终点（如数据未更新到位）；
      3. 月末观测点数量少于请求区间应有月数（中间大面积缺失）。
    """
    actual_start = series.index.min().date()
    actual_end = series.index.max().date()

    gap_start = (actual_start - start).days
    if gap_start > _DATE_TOLERANCE_DAYS:
        raise RuntimeError(
            f"{symbol} 数据起点不足：请求 {start}，实际最早 {actual_start}"
            f"（晚 {gap_start} 天）。该标的在请求区间起点可能尚未上市或无数据。"
        )

    gap_end = (end - actual_end).days
    if gap_end > _DATE_TOLERANCE_DAYS:
        raise RuntimeError(
            f"{symbol} 数据终点不足：请求 {end}，实际最新 {actual_end}"
            f"（早 {gap_end} 天）。数据可能未更新到请求区间末尾。"
        )

    monthly = series.resample("ME").last().dropna()
    expected = _expected_month_count(start, end)
    actual = len(monthly)
    if expected > 0 and actual < expected * _MONTH_COVERAGE_MIN:
        raise RuntimeError(
            f"{symbol} 月度数据量不足：请求区间应有约 {expected} 个月末点，"
            f"实际仅 {actual} 个。中间可能存在大面积停牌或缺失。"
        )


def _build_basket_nav(
    symbols: list[str], start: date, end: date, basket_name: str
) -> pd.Series:
    """把一篮子标的等权合成为一条月末净值序列。

    每只标的先各自月末采样并归一化到起点 1.0（消除价格量级差异），
    再在共同月份上取等权平均。多只标的的月末点取交集，交集不足则报错。
    """
    # 防御性规整：无论上游传列表、单字符串还是逗号/空格分隔串，都拆成列表，
    # 再把每一只各自补上市场后缀（而非只处理最后一只）。
    raw_list = _normalize_symbol_list(symbols)
    codes = [_normalize_symbol(sym) for sym in raw_list]
    if not codes:
        raise RuntimeError(f"{basket_name}篮子为空，请至少配置一只标的")

    # 一次批量请求取回整篮子的收盘宽表，再逐列各自校验、月末采样并归一化。
    close_df = _fetch_close_frame(codes, start, end)
    normalized: dict[str, pd.Series] = {}
    for code in codes:
        series = _series_from_frame(close_df, code, start, end)
        _validate_coverage(code, series, start, end)
        nav = series.resample("ME").last().dropna()
        normalized[code] = nav / nav.iloc[0]  # 各自归一化到 1.0

    basket_df = pd.concat(normalized, axis=1).dropna()
    if basket_df.empty:
        raise RuntimeError(
            f"{basket_name}篮子 {symbols} 对齐后为空：各标的的月末交易日可能无交集"
        )

    # 等权平均合成篮子净值
    basket = basket_df.mean(axis=1)

    # 篮子内多标的取交集后，月末点数不应明显少于请求月数
    expected = _expected_month_count(start, end)
    if expected > 0 and len(basket) < expected * _MONTH_COVERAGE_MIN:
        raise RuntimeError(
            f"{basket_name}篮子 {symbols} 对齐后月度点不足：应有约 {expected} 个，"
            f"实际仅 {len(basket)} 个。篮子内各标的上市时间或交易日历可能不一致。"
        )
    return basket


def get_real_data(
    start: date,
    end: date,
    equity_symbols: list[str],
    bond_symbols: list[str],
) -> pd.DataFrame:
    """通过 tdx 获取股票与债券两类篮子的月度净值，并校验数据完整性。

    股票、债券各为一篮子标的（可多只），每类内部等权合成为一条净值；
    整体仍是股/债两类参与配置。统一使用前复权收盘价，口径一致。
    任一标的数据缺失或覆盖不足都抛异常，不静默降级。
    """
    try:
        from tdx.client import tq  # noqa: F401
    except ImportError as exc:  # pragma: no cover - 可选依赖
        raise RuntimeError("使用真实数据需要可导入 tdx.client（迅投客户端）") from exc

    equity = _build_basket_nav(equity_symbols, start, end, "股票")
    bond = _build_basket_nav(bond_symbols, start, end, "债券")

    df = pd.DataFrame({"equity": equity, "bond": bond}).dropna()
    if df.empty:
        raise RuntimeError("真实数据对齐后为空，请检查区间或标的代码")

    # 股债对齐后再校验一次月度点数
    expected = _expected_month_count(start, end)
    if expected > 0 and len(df) < expected * _MONTH_COVERAGE_MIN:
        raise RuntimeError(
            f"股债数据对齐后月度点不足：应有约 {expected} 个，实际仅 {len(df)} 个。"
            f"可能股票篮子与债券篮子的交易日历或上市时间不一致。"
        )

    # 归一化到起点为 1.0，与模拟数据口径一致
    df = df / df.iloc[0]
    return df


def load_data(cfg) -> pd.DataFrame:
    """按配置选择数据源，返回含 ``equity`` 与 ``bond`` 的月度净值 DataFrame。"""
    if cfg.data_source == "simulated":
        return get_simulated_data(cfg.start_date, cfg.end_date, cfg.data_seed)
    if cfg.data_source == "real":
        return get_real_data(
            cfg.start_date,
            cfg.end_date,
            cfg.data_equity_symbols,
            cfg.data_bond_symbols,
        )
    raise ValueError(f"未知的数据源：{cfg.data_source}")
