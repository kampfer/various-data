import os
import subprocess
import platform
import sys

def main():
    env = os.getenv("APP_ENV", "development")
    is_win = platform.system() == "Windows"
    shell = is_win

    # 后端公共参数（入口和目录）
    uv_args = "main:app --app-dir ./src/web/backEnd"

    if env == "development":
        print("[DEV] 开发模式启动 (前端端口3000 + 后端端口8000)")
        cmd = (
            "npx concurrently "
            f"\"npm run dev:web\" "
            f"\"python -m uvicorn {uv_args} --reload --port 8000\" "
            "--names frontend,backend --prefix-colors green,blue"
        )
        subprocess.run(cmd, shell=shell, check=True)
    else:
        print("[PROD] 生产模式启动 (构建 + 后端托管)")
        subprocess.run("npm run build:web", shell=shell, check=True)
        subprocess.run(
            f"python -m uvicorn {uv_args} --host 0.0.0.0 --port 8000 --workers 4",
            shell=shell,
            check=True
        )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[EXIT] 已退出")
        sys.exit(0)