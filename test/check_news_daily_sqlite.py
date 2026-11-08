#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_news_daily_sqlite.py
检查 SQLite 表 sf_news 按天数据是否连续，按工作日/周末分组做统计异常检测 + 可视化。


==================================================================
一、使用方法
==================================================================
1) 安装依赖
     pip install pandas numpy matplotlib

2) 基本运行（默认输出到 ./report/）
     python check_news_daily_sqlite.py --db /path/to/your.db

3) 指定输出目录与表名
     python check_news_daily_sqlite.py --db your.db --outdir ./out --table sf_news

4) 指定归日时区（默认 local）
     python check_news_daily_sqlite.py --db your.db --tz utc

5) 调整统计阈值
     python check_news_daily_sqlite.py --db your.db \
         --mad-k 4.0 --sigma-k 3.0 --chg-thr 0.8 --min-group-size 20

6) 查看帮助
     python check_news_daily_sqlite.py -h


==================================================================
二、参数说明
==================================================================
--db            必填，SQLite 数据库文件路径
--table         表名，默认 sf_news
--outdir        输出目录，默认 ./report
--tz            归日时区，local（默认）或 utc
--mad-k         MAD 稳健 z 阈值，默认 3.5（越大越不敏感）
--sigma-k       3σ 阈值，默认 3.0
--chg-thr       同组环比突变阈值（绝对值），默认 0.5，即 ±50%
--min-group-size 组内有效样本(cnt>0)下限，默认 10；
                 不足则退回全样本基线，并在 sample_summary.csv 标注


==================================================================
三、结果含义（输出文件）
==================================================================
1) sample_summary.csv —— 样本说明（建议第 1 步查看）
   group            分组：weekday / weekend / overall
   calendar_days    该组覆盖的自然日数（含 cnt=0 的断档日）
   days_with_data   该组有数据的天数（cnt>0）
   zero_days        该组零值断档天数（cnt=0）
   baseline_n       实际参与基线统计的有效样本数（cnt>0）
   baseline_source  基线来源：group=用组内基线；overall=样本不足退回全样本
   min_group_size   本次运行使用的组样本下限
   median/mean/std  该组计数（cnt>0）的中位数/均值/标准差
   mad / mad_scale  该组的中位数绝对偏差及其 1.4826 缩放值（≈σ）
   anomalies        该组被判为异常的天数
   >> 判读：若 weekend 的 baseline_source=overall，说明周末样本不足，
            此时周末异常结果不可靠，需谨慎对待。

2) daily_count.csv —— 每日明细
   day                  日期（自然日）
   cnt                  当日新闻条数
   is_weekend           是否周末（周六/周日）
   group                weekday / weekend
   baseline_source      该行所用基线来源（group / overall）
   group_n              该行所用基线的有效样本量
   base_med             该组基线中位数
   base_mad_scale       该组基线 MAD 缩放值（≈σ）
   z                    3σ 检验的标准化值 (cnt-μ)/σ
   robust_z             MAD 稳健标准化值 0.6745*(cnt-median)/MAD
   cnt_vs_group_median  相对组中位数的偏离比例 (cnt-median)/median
   chg_ratio            同组相邻日环比变化率；跨工作日↔周末过渡为 NaN
   reason               命中原因，逗号分隔：zero / MAD / 3sigma / jump
   is_anomaly           是否异常（任一策略命中）

3) anomalies.csv —— 异常日清单
   字段同 daily_count.csv 的异常相关列，便于逐条核对。
   >> 判读：reason 列标明异常类型；group_n 与 baseline_source 表明该异常
            所依据的样本量与基线是否充足。

4) timeseries.png —— 时序图
   蓝线=工作日，绿线=周末；虚线为各组中位数基线；
   红点=零值断档，橙点=MAD 异常，紫三角=3σ 异常，棕叉=同组环比突变。

5) distribution.png —— 分布图
   工作日/周末计数分布叠加直方图，虚线为各组中位数，便于观察两组量级差异。


==================================================================
四、技术指标解释
==================================================================
1) 样本单位与分组
   样本单位为自然日（按 --tz 归日），区间为 [最小日, 最大日]，
   缺失日补 cnt=0。分组：工作日(周一~周五) / 周末(周六~周日)。
   cnt=0 的断档日不参与基线统计，但始终计入连续性检查。

2) 中位数 median 与 MAD
   median：组内计数（cnt>0）的中位数，抗极端值。
   MAD（Median Absolute Deviation）：median(|x - median|)，衡量离散度。
   mad_scale = 1.4826 * MAD：在正态假设下 MAD 偏小，乘 1.4826 使其
   近似标准差 σ，便于与 3σ 口径对比。

3) 3σ 检验（is_sigma）
   z = (x - μ) / σ，|z| > --sigma-k（默认 3）判为异常。
   假设近似正态；对偏态/重尾计数数据较敏感，作为补充策略。

4) MAD 稳健 z（is_mad）
   robust_z = 0.6745 * (x - median) / MAD，|robust_z| > --mad-k（默认 3.5）
   判为异常。0.6745 使 MAD 在正态下与 σ 对齐；对极端值更稳健，
   是计数类数据的首选策略。

5) 环比突变（is_jump）
   chg_ratio = (今日 - 昨日) / 昨日，|chg_ratio| > --chg-thr（默认 0.5）
   判为异常。仅在同组相邻日之间比较，工作日↔周末过渡不参与，
   避免把正常的周末低谷/周一回升误报为突变。

6) 零值断档（is_zero）
   cnt=0 即判为异常。周末也应有数据（只是量少），零值代表采集中断。

7) 基线来源（baseline_source）
   组内有效样本 >= --min-group-size 时用组内基线（group）；
   否则退回全样本基线（overall），并在 sample_summary.csv 标注。
   周末样本通常约为工作日的 2/5，n 小时 MAD/σ 不稳定，
   建议 --min-group-size 不低于 10；覆盖不足 2 周时分组基线可信度低。

8) 异常判定（is_anomaly）
   上述 zero / MAD / 3sigma / jump 任一命中即为异常；reason 列记录命中项。


==================================================================
五、结果判读建议
==================================================================
第 1 步：先看 sample_summary.csv（控制台也会打印摘要表），
        确认 weekday/weekend 的 baseline_n 与 baseline_source；
        若 weekend 为 overall，则周末异常不可靠。
第 2 步：再看 anomalies.csv 的 reason 列定位异常类型。
第 3 步：周末异常优先核对节假日/长假；工作日异常优先核对采集故障/源站事件。
第 4 步：长期缓慢漂移用 timeseries.png 判断，不要只看单日异常。
==================================================================
"""

import argparse
import os
import sqlite3
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # 无界面环境也能出图
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# ==================================================================
# SQLite 连接与数据读取
# ==================================================================

def open_sqlite(db_path: str) -> sqlite3.Connection:
    """只读打开 SQLite，避免误写；兼容 WAL 模式。"""
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"数据库不存在: {db_path}")
    uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=30)


def load_daily_counts(db_path: str, table: str, tz: str) -> pd.DataFrame:
    """
    读取每天计数，并用递归 CTE 补齐缺失日期（cnt=0）。

    create_time 为 Unix 毫秒级时间戳，SQLite 的 'unixepoch' 只认秒，
    故先 /1000。tz='local' 按本地时区归日，'utc' 按 UTC 归日。
    """
    tz_mod = "'localtime'" if tz == "local" else "'utc'"
    sql = f"""
    WITH RECURSIVE
    bounds AS (
        SELECT date(MIN(create_time)/1000, 'unixepoch', {tz_mod}) AS mn,
               date(MAX(create_time)/1000, 'unixepoch', {tz_mod}) AS mx
        FROM {table}
    ),
    days(day) AS (
        SELECT mn FROM bounds
        UNION ALL
        SELECT date(day, '+1 day') FROM days, bounds WHERE day < bounds.mx
    ),
    actual AS (
        SELECT date(create_time/1000, 'unixepoch', {tz_mod}) AS day,
               COUNT(*) AS cnt
        FROM {table}
        GROUP BY day
    )
    SELECT d.day AS day, COALESCE(a.cnt, 0) AS cnt
    FROM days d
    LEFT JOIN actual a ON a.day = d.day
    ORDER BY d.day;
    """
    con = open_sqlite(db_path)
    try:
        df = pd.read_sql_query(sql, con)
    finally:
        con.close()
    df["day"] = pd.to_datetime(df["day"])
    return df.sort_values("day").reset_index(drop=True)


# ==================================================================
# 统计检测（按工作日/周末分组建立基线）
# ==================================================================

def _group_stats(cnt: pd.Series) -> dict:
    """
    计算一组计数的基线统计量。
    - n        : 有效样本数（cnt>0）
    - mu/sd    : 均值 / 标准差（3σ 用）
    - med/mad  : 中位数 / 中位数绝对偏差（MAD 稳健 z 用）
    - mad_scale: 1.4826*MAD，正态下近似 σ
    """
    mu = cnt.mean()
    sd = cnt.std(ddof=0)
    med = cnt.median()
    mad = (cnt - med).abs().median()
    return {
        "n": int(len(cnt)),
        "mu": mu, "sd": sd, "med": med, "mad": mad,
        "mad_scale": mad * 1.4826 if mad > 0 else 0.0,
    }


def detect_anomalies(df: pd.DataFrame, mad_k: float, sigma_k: float,
                     chg_thr: float, min_group_size: int):
    """
    在每日计数上做四类异常检测并标注来源。

    返回:
      d       : 带异常标记与基线信息的数据框
      stats   : 各组基线统计量 {group: {...}}，样本不足的组为 None
      overall : 全样本基线统计量（组样本不足时的回退基线）
    """
    d = df.copy()
    d["cnt"] = d["cnt"].astype(float)

    # 周末标记：pandas dayofweek 0=周一 ... 5=周六, 6=周日
    d["is_weekend"] = d["day"].dt.dayofweek >= 5
    d["group"] = np.where(d["is_weekend"], "weekend", "weekday")

    # 零值断档：cnt=0 即异常（周末也应有数据，只是量少）
    d["is_zero"] = d["cnt"] == 0

    # 分组基线：仅用 cnt>0 的有效样本；不足 min_group_size 的组回退全样本
    stats = {}
    for g, sub in d.groupby("group"):
        valid = sub.loc[sub["cnt"] > 0, "cnt"]
        if len(valid) >= min_group_size:
            stats[g] = _group_stats(valid)
            stats[g]["source"] = "group"
        else:
            stats[g] = None
    overall_valid = d.loc[d["cnt"] > 0, "cnt"]
    overall = _group_stats(overall_valid)
    overall["source"] = "overall"

    def st_for(g):
        """取某组基线；样本不足则回退全样本基线。"""
        s = stats.get(g)
        return s if s is not None else overall

    # 把该行实际使用的基线来源/样本量/统计量映射到每一行
    d["baseline_source"] = d["group"].map(lambda g: st_for(g)["source"])
    d["group_n"] = d["group"].map(lambda g: st_for(g)["n"])
    d["base_med"] = d["group"].map(lambda g: st_for(g)["med"])
    d["base_mu"] = d["group"].map(lambda g: st_for(g)["mu"])
    d["base_sd"] = d["group"].map(lambda g: st_for(g)["sd"])
    d["base_mad_scale"] = d["group"].map(lambda g: st_for(g)["mad_scale"])

    # 3σ：z=(x-μ)/σ，|z|>sigma_k
    d["z"] = np.where(d["base_sd"] > 0,
                      (d["cnt"] - d["base_mu"]) / d["base_sd"], 0.0)
    d["is_sigma"] = d["z"].abs() > sigma_k

    # MAD 稳健 z：0.6745*(x-median)/MAD，|robust_z|>mad_k
    d["robust_z"] = np.where(d["base_mad_scale"] > 0,
                             0.6745 * (d["cnt"] - d["base_med"]) / d["base_mad_scale"], 0.0)
    d["is_mad"] = d["robust_z"].abs() > mad_k

    # 环比突变：仅同组相邻日比较，工作日↔周末过渡置 NaN 不参与
    d["prev"] = d["cnt"].shift(1)
    d["prev_group"] = d["group"].shift(1)
    same_group = d["group"] == d["prev_group"]
    d["chg_ratio"] = np.where(
        same_group,
        (d["cnt"] - d["prev"]) / d["prev"].replace(0, np.nan),
        np.nan,
    )
    d["is_jump"] = d["chg_ratio"].abs() > chg_thr

    # 汇总异常：任一策略命中
    d["is_anomaly"] = d[["is_zero", "is_sigma", "is_mad", "is_jump"]].any(axis=1)

    # 相对组中位数的偏离比例，便于快速判断异常幅度
    d["cnt_vs_group_median"] = np.where(
        d["base_med"] > 0, (d["cnt"] - d["base_med"]) / d["base_med"], np.nan
    )

    def reason(row):
        """拼装命中原因标签。"""
        tags = []
        if row["is_zero"]:  tags.append("zero")
        if row["is_mad"]:   tags.append("MAD")
        if row["is_sigma"]: tags.append("3sigma")
        if row["is_jump"]:  tags.append("jump")
        return ",".join(tags)

    d["reason"] = d.apply(reason, axis=1)
    return d, stats, overall


def summarize_continuity(df: pd.DataFrame) -> dict:
    """
    连续性摘要：
    - zero_days: cnt=0 的日期列表
    - gaps     : 有数据日之间间隔 >1 天的断点
    """
    days = df["day"]
    zero_days = df.loc[df["cnt"] == 0, "day"].tolist()
    active = df.loc[df["cnt"] > 0, "day"].reset_index(drop=True)
    gaps = []
    for i in range(1, len(active)):
        diff = (active[i] - active[i - 1]).days
        if diff > 1:
            gaps.append({
                "prev_day": active[i - 1].date().isoformat(),
                "next_day": active[i].date().isoformat(),
                "missing_days": diff - 1,
            })
    return {
        "start": days.min().date().isoformat(),
        "end": days.max().date().isoformat(),
        "total_days": (days.max() - days.min()).days + 1,
        "days_with_data": int((df["cnt"] > 0).sum()),
        "zero_days_count": len(zero_days),
        "zero_days": [x.date().isoformat() for x in zero_days],
        "gaps": gaps,
        "continuous": len(zero_days) == 0,
    }


# ==================================================================
# 样本说明
# ==================================================================

def build_sample_summary(d: pd.DataFrame, stats: dict, overall: dict,
                         min_group_size: int) -> pd.DataFrame:
    """生成 sample_summary.csv：每组样本量、基线统计量、基线来源、异常数。"""
    rows = []
    for g in ["weekday", "weekend"]:
        sub = d[d["group"] == g]
        s = stats.get(g) or overall
        rows.append({
            "group": g,
            "calendar_days": len(sub),
            "days_with_data": int((sub["cnt"] > 0).sum()),
            "zero_days": int((sub["cnt"] == 0).sum()),
            "baseline_n": s["n"],
            "baseline_source": s["source"],
            "min_group_size": min_group_size,
            "median": round(float(s["med"]), 2),
            "mean": round(float(s["mu"]), 2),
            "std": round(float(s["sd"]), 2),
            "mad": round(float(s["mad"]), 2),
            "mad_scale": round(float(s["mad_scale"]), 2),
            "anomalies": int(sub["is_anomaly"].sum()),
        })
    rows.append({
        "group": "overall",
        "calendar_days": len(d),
        "days_with_data": int((d["cnt"] > 0).sum()),
        "zero_days": int((d["cnt"] == 0).sum()),
        "baseline_n": overall["n"],
        "baseline_source": "overall",
        "min_group_size": min_group_size,
        "median": round(float(overall["med"]), 2),
        "mean": round(float(overall["mu"]), 2),
        "std": round(float(overall["sd"]), 2),
        "mad": round(float(overall["mad"]), 2),
        "mad_scale": round(float(overall["mad_scale"]), 2),
        "anomalies": int(d["is_anomaly"].sum()),
    })
    return pd.DataFrame(rows)


def print_sample_overview(summary: dict, d: pd.DataFrame, stats: dict,
                          overall: dict, min_group_size: int):
    """控制台打印样本概况与基线来源提示。"""
    wd_days = int((~d["is_weekend"]).sum())
    we_days = int(d["is_weekend"].sum())
    weeks = summary["total_days"] / 7.0

    print("=" * 64)
    print("样本说明")
    print("=" * 64)
    print("样本单位    : 自然日（按 --tz 归日，缺失补 cnt=0）")
    print(f"覆盖区间    : {summary['start']} ~ {summary['end']}")
    print(f"总天数      : {summary['total_days']}  (~{weeks:.1f} 周)")
    print(f"有数据天数  : {summary['days_with_data']}   零值断档: {summary['zero_days_count']}")
    print(f"分组样本    : 工作日 {wd_days} 天 / 周末 {we_days} 天")
    print(f"基线样本    : 仅使用 cnt>0 的日子参与统计；min_group_size={min_group_size}")
    for g in ["weekday", "weekend"]:
        s = stats.get(g)
        if s is None:
            print(f"  - {g:7s}: 样本不足 -> 退回全样本基线 "
                  f"(n={overall['n']}, median={overall['med']:.1f})")
        else:
            print(f"  - {g:7s}: n={s['n']:4d}  median={s['med']:.1f}  "
                  f"mean={s['mu']:.1f}  std={s['sd']:.2f}  MAD={s['mad']:.2f}")
    if weeks < 2:
        print("  [!] 覆盖不足 2 周，分组基线可信度低，异常结果仅供参考。")
    if we_days < 10:
        print("  [!] 周末样本很少，建议调大 --min-group-size 或放宽 --mad-k。")


def print_sample_summary_table(sample_df: pd.DataFrame):
    """把 sample_summary 关键列直接打印到控制台，避免必须先打开 CSV。"""
    print("=" * 64)
    print("样本说明（sample_summary.csv 摘要）")
    print("=" * 64)
    show_cols = ["group", "calendar_days", "days_with_data", "zero_days",
                 "baseline_n", "baseline_source", "median", "mean", "std",
                 "mad", "anomalies"]
    print(sample_df[show_cols].to_string(index=False))
    if sample_df.loc[sample_df["group"] == "weekend", "baseline_source"].eq("overall").any():
        print("[!] 周末样本不足，已退回全样本基线；周末异常请谨慎判读。")


# ==================================================================
# 可视化
# ==================================================================

def plot_timeseries(d: pd.DataFrame, out_path: str):
    """
    时序图：工作日/周末双色折线 + 双基线 + 异常标记。
    红=零值断档，橙=MAD，紫三角=3σ，棕叉=同组环比突变。
    """
    wd_med = d.loc[~d["is_weekend"], "cnt"].median()
    we_med = d.loc[d["is_weekend"], "cnt"].median()

    fig, ax = plt.subplots(figsize=(15, 5))
    wd = d[~d["is_weekend"]]
    we = d[d["is_weekend"]]
    ax.plot(wd["day"], wd["cnt"], lw=0.9, color="#1f77b4", label="weekday")
    ax.plot(we["day"], we["cnt"], lw=0.9, color="#2ca02c", label="weekend")
    ax.axhline(wd_med, color="#1f77b4", ls="--", lw=0.8, label=f"weekday median={wd_med:.0f}")
    ax.axhline(we_med, color="#2ca02c", ls="--", lw=0.8, label=f"weekend median={we_med:.0f}")

    zero = d[d["is_zero"]]
    mad = d[d["is_mad"] & ~d["is_zero"]]
    sigma = d[d["is_sigma"] & ~d["is_mad"] & ~d["is_zero"]]
    jump = d[d["is_jump"] & ~d["is_zero"] & ~d["is_mad"] & ~d["is_sigma"]]

    ax.scatter(zero["day"], zero["cnt"], color="red", s=30, zorder=4, label="zero (gap)")
    ax.scatter(mad["day"], mad["cnt"], color="orange", s=30, zorder=4, label="MAD outlier")
    ax.scatter(sigma["day"], sigma["cnt"], color="purple", s=25, marker="^", zorder=4, label="3σ outlier")
    ax.scatter(jump["day"], jump["cnt"], color="brown", s=25, marker="x", zorder=4, label="jump (same group)")

    ax.set_title("Daily news count (weekday/weekend baselines) with anomalies")
    ax.set_xlabel("date"); ax.set_ylabel("count")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    ax.legend(loc="upper right", fontsize=9, ncol=2)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_distribution(d: pd.DataFrame, out_path: str):
    """
    分布图：工作日/周末计数叠加直方图，虚线为各组中位数。
    用于直观对比两组量级差异，解释为何要分组建基线。
    """
    wd = d.loc[~d["is_weekend"], "cnt"]
    we = d.loc[d["is_weekend"], "cnt"]
    fig, ax = plt.subplots(figsize=(9, 4))
    bins = np.histogram_bin_edges(d["cnt"], bins=50)
    ax.hist(wd, bins=bins, alpha=0.65, color="#1f77b4", label=f"weekday (n={len(wd)})")
    ax.hist(we, bins=bins, alpha=0.65, color="#2ca02c", label=f"weekend (n={len(we)})")
    ax.axvline(wd.median(), color="#1f77b4", ls="--", lw=1, label=f"wd median={wd.median():.0f}")
    ax.axvline(we.median(), color="#2ca02c", ls="--", lw=1, label=f"we median={we.median():.0f}")
    ax.set_title("Distribution of daily counts (weekday vs weekend)")
    ax.set_xlabel("count"); ax.set_ylabel("days")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


# ==================================================================
# 主流程
# ==================================================================

def main():
    ap = argparse.ArgumentParser(description="检查 SQLite sf_news 连续性 + 工作日/周末分组异常检测")
    ap.add_argument("--db", required=True, help="SQLite 数据库路径")
    ap.add_argument("--table", default="sf_news", help="表名，默认 sf_news")
    ap.add_argument("--outdir", default="./report", help="输出目录，默认 ./report")
    ap.add_argument("--tz", choices=["local", "utc"], default="local", help="归日时区")
    ap.add_argument("--mad-k", type=float, default=3.5, help="MAD 稳健 z 阈值")
    ap.add_argument("--sigma-k", type=float, default=3.0, help="3σ 阈值")
    ap.add_argument("--chg-thr", type=float, default=0.5, help="同组环比突变阈值")
    ap.add_argument("--min-group-size", type=int, default=10,
                    help="组内有效样本(cnt>0)少于此值退回全样本基线")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # 1) 读取并补零
    df = load_daily_counts(args.db, args.table, args.tz)
    if df.empty:
        print("[ERROR] 未读到数据。", file=sys.stderr)
        sys.exit(1)

    # 2) 统计检测 + 连续性摘要 + 样本说明
    d, stats, overall = detect_anomalies(
        df, args.mad_k, args.sigma_k, args.chg_thr, args.min_group_size
    )
    summary = summarize_continuity(d)
    sample_df = build_sample_summary(d, stats, overall, args.min_group_size)

    # 3) 导出 CSV
    daily_csv = os.path.join(args.outdir, "daily_count.csv")
    d[["day", "cnt", "is_weekend", "group", "baseline_source", "group_n",
       "base_med", "base_mad_scale", "z", "robust_z",
       "cnt_vs_group_median", "chg_ratio", "reason", "is_anomaly"]].to_csv(
        daily_csv, index=False, date_format="%Y-%m-%d"
    )

    anomalies = d[d["is_anomaly"]][
        ["day", "cnt", "is_weekend", "group", "group_n", "baseline_source",
         "base_med", "cnt_vs_group_median", "reason", "z", "robust_z", "chg_ratio"]
    ]
    anomaly_csv = os.path.join(args.outdir, "anomalies.csv")
    anomalies.to_csv(anomaly_csv, index=False, date_format="%Y-%m-%d")

    sample_csv = os.path.join(args.outdir, "sample_summary.csv")
    sample_df.to_csv(sample_csv, index=False)

    # 4) 出图
    ts_png = os.path.join(args.outdir, "timeseries.png")
    dist_png = os.path.join(args.outdir, "distribution.png")
    plot_timeseries(d, ts_png)
    plot_distribution(d, dist_png)

    # 5) 控制台输出：样本说明 -> 摘要表 -> 连续性 -> 异常 -> 文件 -> 提示
    print_sample_overview(summary, d, stats, overall, args.min_group_size)
    print_sample_summary_table(sample_df)

    print("=" * 64)
    print("连续性摘要")
    print("=" * 64)
    print(f"区间        : {summary['start']} ~ {summary['end']}")
    print(f"总天数      : {summary['total_days']}")
    print(f"有数据天数  : {summary['days_with_data']}")
    print(f"零值(断档)  : {summary['zero_days_count']}")
    print(f"是否连续    : {'是' if summary['continuous'] else '否'}")
    if summary["zero_days"]:
        print(f"缺失日期    : {', '.join(summary['zero_days'][:30])}"
              + (" ..." if len(summary["zero_days"]) > 30 else ""))
    if summary["gaps"]:
        print("断点(有数据日之间):")
        for g in summary["gaps"][:20]:
            print(f"  {g['prev_day']} -> {g['next_day']}  缺 {g['missing_days']} 天")
        if len(summary["gaps"]) > 20:
            print(f"  ... 共 {len(summary['gaps'])} 个断点")

    wd_anom = int((d["is_anomaly"] & ~d["is_weekend"]).sum())
    we_anom = int((d["is_anomaly"] & d["is_weekend"]).sum())
    print("-" * 64)
    print(f"异常日期数  : {len(anomalies)}  (工作日 {wd_anom} / 周末 {we_anom})")
    if not anomalies.empty:
        print(anomalies.head(30).to_string(index=False))
        if len(anomalies) > 30:
            print(f"... 共 {len(anomalies)} 行，详见 {anomaly_csv}")
    print("-" * 64)
    print(f"输出目录    : {os.path.abspath(args.outdir)}")
    print(f"  每日计数  : {daily_csv}")
    print(f"  异常清单  : {anomaly_csv}")
    print(f"  样本说明  : {sample_csv}")
    print(f"  时序图    : {ts_png}")
    print(f"  分布图    : {dist_png}")
    print("-" * 64)
    print("下一步：请先打开 sample_summary.csv，确认各组样本量与基线来源")
    print("  - 若 weekend 的 baseline_source=overall，说明周末样本不足，")
    print("    anomalies.csv 中周末行的异常需谨慎对待。")
    print("  - 再看 anomalies.csv 的 reason 列（zero/MAD/3sigma/jump）定位原因。")
    print("-" * 64)
    print("使用方法速查")
    print("-" * 64)
    print("  基本运行 : python check_news_daily_sqlite.py --db your.db")
    print("  指定输出 : ... --outdir ./out")
    print("  时区     : ... --tz utc")
    print("  调阈值   : ... --mad-k 4.0 --sigma-k 3.0 --chg-thr 0.8")
    print("  样本门槛 : ... --min-group-size 20")
    print("  帮助     : python check_news_daily_sqlite.py -h")
    print("=" * 64)


if __name__ == "__main__":
    main()