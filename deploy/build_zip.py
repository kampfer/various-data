#!/usr/bin/env python3
"""打包调度器部署包（zip）。

用法（在仓库任意位置执行均可）:

    python deploy/build_zip.py                  # 先构建前端，再打包
    python deploy/build_zip.py --skip-frontend  # 直接使用现有 src/frontEnd/dist
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "various-data-scheduler"
OUTPUT_DIR = ROOT / "dist"
FRONTEND_DIR = ROOT / "src" / "frontEnd"

INCLUDE_PATHS = [
    "src/backend",
    "src/frontEnd/dist",
    "deploy/install.sh",
    "deploy/run.sh",
    "deploy/various-data-scheduler.service.template",
]

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".hypothesis",
}
EXCLUDED_FILE_NAMES = {
    # 线上配置与密钥不进包，由安装脚本在服务器生成
    "config.local.yaml",
    # 旧的手工样例单元，部署使用 deploy/ 下的模板
    "various-data-scheduler.service",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成调度器部署 zip")
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="跳过前端构建，直接使用现有的 src/frontEnd/dist",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 zip 路径（默认 dist/various-data-scheduler-<时间>.zip）",
    )
    return parser.parse_args(argv)


def ensure_frontend(skip: bool) -> None:
    index_file = FRONTEND_DIR / "dist" / "index.html"
    if skip:
        if not index_file.exists():
            raise SystemExit("src/frontEnd/dist 不存在，去掉 --skip-frontend 或先构建前端")
        print(f"==> 跳过前端构建，使用现有产物: {index_file}")
        return

    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("未找到 npm，无法构建前端；请安装 Node.js 或使用 --skip-frontend")

    if not (FRONTEND_DIR / "node_modules").exists():
        print("==> 安装前端依赖")
        subprocess.run([npm, "install"], cwd=FRONTEND_DIR, check=True)
    print("==> 构建前端")
    subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR, check=True)
    if not index_file.exists():
        raise SystemExit("前端构建完成但未找到 dist/index.html")


def iter_files(path: Path):
    if path.is_file():
        yield path
        return
    for child in sorted(path.rglob("*")):
        if not child.is_file():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in child.parts):
            continue
        if child.name in EXCLUDED_FILE_NAMES:
            continue
        yield child


def add_file(archive: zipfile.ZipFile, path: Path) -> None:
    arcname = f"{PACKAGE_NAME}/{path.relative_to(ROOT).as_posix()}"
    info = zipfile.ZipInfo(arcname, date_time=time.localtime(path.stat().st_mtime)[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    mode = 0o755 if path.suffix == ".sh" else 0o644
    info.external_attr = (mode | 0o100000) << 16
    archive.writestr(info, path.read_bytes())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_frontend(args.skip_frontend)

    required = [
        ROOT / "src" / "backend" / "pyproject.toml",
        ROOT / "src" / "backend" / "uv.lock",
        ROOT / "src" / "frontEnd" / "dist" / "index.html",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"缺少必要文件: {', '.join(missing)}")

    for relative in INCLUDE_PATHS:
        if not (ROOT / relative).exists():
            raise SystemExit(f"打包清单中的路径不存在: {relative}")

    if args.output is not None:
        output = args.output.resolve()
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        output = OUTPUT_DIR / f"{PACKAGE_NAME}-{stamp}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in INCLUDE_PATHS:
            for file_path in iter_files(ROOT / relative):
                add_file(archive, file_path)
                count += 1

    size_mb = output.stat().st_size / 1024 / 1024
    print(f"==> 已生成 {output}")
    print(f"    文件数 {count}，大小 {size_mb:.2f} MB")
    print()
    print("服务器上执行：")
    print(f"  sudo unzip {output.name} -d /srv")
    print(f"  cd /srv/{PACKAGE_NAME}")
    print("  sudo bash deploy/install.sh install")
    print()
    print("之后可用：sudo bash deploy/install.sh start|stop|restart|status|logs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
