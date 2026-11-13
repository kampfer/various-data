"""用 data/omo/html 的历史样本回归 OMO 解析规则。

用法：``uv run python scripts/check_omo_parser.py``；存在零漏解析的样本时退出码非 0。
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from scheduler.tasks.omo import extract  # noqa: E402

SAMPLE_DIR = REPO_ROOT / "data" / "omo" / "html"


def main() -> int:
    if not SAMPLE_DIR.exists():
        print(f"样本目录不存在: {SAMPLE_DIR}")
        return 2

    files = sorted(SAMPLE_DIR.glob("*.html"))
    if not files:
        print(f"样本目录为空: {SAMPLE_DIR}")
        return 2

    failed: list[tuple[str, str]] = []
    total_deals = 0
    for path in files:
        try:
            deals = extract(path.read_text(encoding="utf-8"))
        except Exception as exc:  # 解析异常也视为失败
            failed.append((path.name, f"{type(exc).__name__}: {exc}"))
            continue
        total_deals += len(deals)
        if not deals:
            failed.append((path.name, "解析结果为空"))

    print(f"样本 {len(files)} 份，解析交易 {total_deals} 条，失败 {len(failed)} 份")
    for name, reason in failed:
        print(f"  {name}: {reason}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
