"""回归校验：新 OMO 解析器与旧实现（app/tasks/crawlOMO.py）结果一致。

用法（仓库根）：pipenv run python scripts/check_omo_parser.py [样本目录]
默认样本目录为 data/omo/html。
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "web" / "backEnd"))
sys.path.insert(0, str(REPO_ROOT / "src" / "dagu"))

from app.tasks.crawlOMO import OMOExtOMOractor  # noqa: E402
from tasks.omo import OMOExtractor  # noqa: E402


def main() -> int:
    sampleDir = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else REPO_ROOT / "data" / "omo" / "html"
    )
    files = sorted(sampleDir.glob("*.html"))
    if not files:
        print(f"未找到样本: {sampleDir}")
        return 2

    oldExtractor = OMOExtOMOractor()
    newExtractor = OMOExtractor()

    same = 0
    oldErrors = 0
    mismatches = 0

    for path in files:
        html = path.read_text(encoding="utf-8")
        try:
            oldDeals = oldExtractor.extract(html)
        except Exception as error:  # 旧实现自身会抛错的情况单独计数
            oldErrors += 1
            print(f"[旧实现异常] {path.name}: {error}")
            continue

        newDeals = newExtractor.extract(html)
        if oldDeals == newDeals:
            same += 1
        else:
            mismatches += 1
            print(f"[不一致] {path.name}")
            print(f"  旧: {len(oldDeals)} 条 {oldDeals[:2]}")
            print(f"  新: {len(newDeals)} 条 {newDeals[:2]}")

    print(
        f"样本 {len(files)} 份：一致 {same}，不一致 {mismatches}，旧实现异常 {oldErrors}"
    )
    return 0 if mismatches == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
