#!/usr/bin/env bash
# 调度器启动入口：由 systemd 调用，读取 /etc/default/various-data-scheduler 中的变量。
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$APP_DIR/src/backend/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "未找到虚拟环境: $PYTHON_BIN（请先执行 sudo bash deploy/install.sh install）" >&2
    exit 1
fi

ARGS=(--mode "${VD_MODE:-pro}")

if [[ "${VD_ADMIN_ENABLED:-1}" == "0" ]]; then
    ARGS+=(--no-admin)
else
    ARGS+=(--admin-host "${VD_ADMIN_HOST:-0.0.0.0}" --admin-port "${VD_ADMIN_PORT:-8787}")
fi

exec "$PYTHON_BIN" "$APP_DIR/src/backend/scheduler/main.py" "${ARGS[@]}"
