#!/usr/bin/env bash
# 调度器部署脚本：同步依赖、启动服务。
# 有 systemd 时注册开机自启；无 systemd（容器 / Linux Deploy chroot）时退回 PID 文件进程模式。
set -euo pipefail

APP_NAME="various-data-scheduler"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$APP_DIR/src/backend"
SERVICE_PATH="/etc/systemd/system/${APP_NAME}.service"
ENV_PATH="/etc/default/${APP_NAME}"
PID_FILE="$APP_DIR/log/scheduler.pid"
LOG_FILE="$APP_DIR/log/scheduler.log"
STDOUT_FILE="$APP_DIR/log/stdout.log"
RUN_USER="${APP_USER:-${SUDO_USER:-$(id -un)}}"
RUN_GROUP="$(id -gn "$RUN_USER" 2>/dev/null || echo "$RUN_USER")"

detect_mode() {
    if command -v systemctl >/dev/null 2>&1; then
        local state
        state="$(systemctl is-system-running 2>/dev/null || true)"
        case "$state" in
            running|degraded|starting)
                echo "systemd"
                return 0
                ;;
        esac
    fi
    echo "process"
}

MODE="${SERVICE_MODE:-$(detect_mode)}"

usage() {
    cat <<EOF
用法: bash deploy/install.sh <命令>

当前模式: $MODE（有可用的 systemd 时为 systemd，否则为进程模式）

命令:
  install        同步依赖、生成配置、启动服务（默认）
  start          启动服务
  stop           停止服务
  restart        重启服务
  status         查看服务状态
  logs [行数]    查看最近日志（默认 200 行）；logs -f 持续跟踪
  upgrade        重新同步依赖并重启（重新上传代码后使用）
  uninstall      停止服务；systemd 模式下同时移除单元（保留 data/log/backup）

环境变量:
  APP_USER=xxx     指定运行服务的用户（默认 sudo 发起者）
  UV_BIN=/path     指定 uv 可执行文件路径
  SERVICE_MODE=x   强制模式：systemd 或 process
EOF
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "该命令需要 root 权限，请使用 sudo 执行" >&2
        exit 1
    fi
}

require_systemd() {
    if ! command -v systemctl >/dev/null 2>&1; then
        echo "当前系统没有 systemctl" >&2
        exit 1
    fi
}

find_uv() {
    if [[ -n "${UV_BIN:-}" && -x "${UV_BIN}" ]]; then
        echo "${UV_BIN}"
        return 0
    fi
    if command -v uv >/dev/null 2>&1; then
        command -v uv
        return 0
    fi
    if [[ -x "${HOME}/.local/bin/uv" ]]; then
        echo "${HOME}/.local/bin/uv"
        return 0
    fi
    # sudo 场景下 uv 通常装在发起用户的家目录
    if [[ -n "${SUDO_USER:-}" && -x "/home/${SUDO_USER}/.local/bin/uv" ]]; then
        echo "/home/${SUDO_USER}/.local/bin/uv"
        return 0
    fi
    return 1
}

sync_deps() {
    local uv_bin
    if ! uv_bin="$(find_uv)"; then
        echo "未找到 uv。请先安装后重试：" >&2
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
        echo "或通过 UV_BIN 指定 uv 路径" >&2
        exit 1
    fi
    echo "==> 同步 Python 依赖（uv sync --frozen --no-dev）"
    "$uv_bin" sync --frozen --no-dev --project "$PROJECT_DIR"
    # 服务以普通用户运行时，确保它能读取 root 创建的虚拟环境
    chmod -R a+rX "$PROJECT_DIR/.venv"
}

prepare_runtime() {
    echo "==> 准备运行目录与配置"
    mkdir -p "$APP_DIR/data" "$APP_DIR/log" "$APP_DIR/backup"
    chown -R "$RUN_USER:$RUN_GROUP" "$APP_DIR/data" "$APP_DIR/log" "$APP_DIR/backup"
    chmod +x "$SCRIPT_DIR/run.sh"

    if [[ ! -f "$PROJECT_DIR/scheduler/config.local.yaml" ]]; then
        cp "$PROJECT_DIR/scheduler/config.local.example.yaml" "$PROJECT_DIR/scheduler/config.local.yaml"
        chown "$RUN_USER:$RUN_GROUP" "$PROJECT_DIR/scheduler/config.local.yaml"
        echo "    已生成 src/backend/scheduler/config.local.yaml；SMTP 未配置时不会发送邮件，"
        echo "    需要邮件告警请补充后执行 restart"
    fi
}

write_env_file() {
    if [[ -f "$ENV_PATH" ]]; then
        echo "==> 保留已有配置: $ENV_PATH"
        return
    fi
    cat >"$ENV_PATH" <<'EOF'
# various-data scheduler 运行参数
VD_MODE=pro
VD_ADMIN_ENABLED=1
VD_ADMIN_HOST=0.0.0.0
VD_ADMIN_PORT=8787
EOF
    chmod 644 "$ENV_PATH"
}

install_unit() {
    echo "==> 写入 systemd 单元: $SERVICE_PATH"
    sed \
        -e "s|__APP_DIR__|$APP_DIR|g" \
        -e "s|__APP_USER__|$RUN_USER|g" \
        -e "s|__APP_GROUP__|$RUN_GROUP|g" \
        -e "s|__ENV_FILE__|$ENV_PATH|g" \
        "$SCRIPT_DIR/various-data-scheduler.service.template" >"$SERVICE_PATH"
    chmod 644 "$SERVICE_PATH"
    systemctl daemon-reload
    systemctl enable "$APP_NAME"
}

process_pid() {
    [[ -f "$PID_FILE" ]] || return 1
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null || return 1
    echo "$pid"
}

process_start() {
    local pid
    if pid="$(process_pid)"; then
        echo "服务已在运行: PID $pid"
        return 0
    fi
    mkdir -p "$APP_DIR/log" "$APP_DIR/data" "$APP_DIR/backup"
    chmod +x "$SCRIPT_DIR/run.sh"
    echo "==> 启动服务（进程模式）"
    (
        set -a
        [[ -f "$ENV_PATH" ]] && . "$ENV_PATH"
        set +a
        exec nohup "$SCRIPT_DIR/run.sh"
    ) >>"$STDOUT_FILE" 2>&1 &
    echo $! >"$PID_FILE"

    sleep 2
    if pid="$(process_pid)"; then
        echo "已启动: PID $pid"
        echo "应用日志: $LOG_FILE"
        echo "标准输出: $STDOUT_FILE"
        return 0
    fi
    echo "启动失败，最近输出：" >&2
    tail -n 20 "$STDOUT_FILE" >&2 || true
    rm -f "$PID_FILE"
    return 1
}

process_stop() {
    local pid
    if ! pid="$(process_pid)"; then
        echo "服务未在运行"
        rm -f "$PID_FILE"
        return 0
    fi
    echo "==> 停止 PID $pid（等待优雅退出）"
    kill -TERM "$pid" 2>/dev/null || true
    local i
    for ((i = 0; i < 30; i++)); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done
    if kill -0 "$pid" 2>/dev/null; then
        echo "优雅退出超时，强制结束" >&2
        kill -KILL "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
}

process_status() {
    local pid
    if ! pid="$(process_pid)"; then
        echo "服务未在运行（进程模式）"
        return 1
    fi
    echo "服务运行中（进程模式）"
    echo "  PID: $pid"
    ps -o pid,etime,cmd -p "$pid" 2>/dev/null || true
}

process_logs() {
    local target="${1:-200}"
    local file="$LOG_FILE"
    [[ -f "$file" ]] || file="$STDOUT_FILE"
    if [[ ! -f "$file" ]]; then
        echo "日志文件不存在: $LOG_FILE" >&2
        return 1
    fi
    if [[ "$target" == "-f" ]]; then
        tail -f "$file"
    else
        tail -n "$target" "$file"
    fi
}

show_summary() {
    local host
    host="$(hostname -I 2>/dev/null | awk '{print $1}')"
    echo
    echo "服务已配置完成："
    echo "  模式: $MODE"
    echo "  运行用户: $RUN_USER"
    echo "  安装目录: $APP_DIR"
    echo "  环境变量: $ENV_PATH"
    echo "  管理页面: http://${host:-<服务器IP>}:8787"
    if grep -q '^VD_ADMIN_HOST=0\.0\.0\.0' "$ENV_PATH" 2>/dev/null; then
        echo "  注意: 页面未提供登录鉴权，请用防火墙限制来源 IP"
    fi
    echo
    if [[ "$MODE" == "systemd" ]]; then
        systemctl --no-pager --full status "$APP_NAME" || true
    else
        process_status || true
    fi
}

print_autostart_hint() {
    cat <<EOF

当前环境没有可用的 systemd，无法自动注册开机自启。可选做法：
  1. Linux Deploy 设置里启用 Autostart，并把 Init 类型切换为 systemd（切换后重新执行 install）
  2. 在当前 init 的启动脚本（如 /etc/rc.local）末尾加入：
       bash $SCRIPT_DIR/install.sh start
  3. Android 侧把 Linux Deploy 加入电池优化白名单，避免后台被系统清理
EOF
}

cmd_install() {
    require_root
    sync_deps
    prepare_runtime
    write_env_file
    if [[ "$MODE" == "systemd" ]]; then
        require_systemd
        install_unit
        echo "==> 启动服务"
        systemctl restart "$APP_NAME"
    else
        echo "==> 未检测到可用的 systemd，使用进程模式"
        # 已存在旧进程时先停再起，保证重新部署后运行的是新代码
        process_stop || true
        process_start
    fi
    show_summary
    if [[ "$MODE" != "systemd" ]]; then
        print_autostart_hint
    fi
}

cmd_upgrade() {
    require_root
    sync_deps
    prepare_runtime
    if [[ "$MODE" == "systemd" ]]; then
        require_systemd
        systemctl restart "$APP_NAME"
        systemctl --no-pager --full status "$APP_NAME" || true
    else
        process_stop
        process_start
        process_status || true
    fi
}

cmd_start() {
    if [[ "$MODE" == "systemd" ]]; then
        require_root
        require_systemd
        systemctl start "$APP_NAME"
        systemctl --no-pager --full status "$APP_NAME" || true
    else
        process_start
    fi
}

cmd_stop() {
    if [[ "$MODE" == "systemd" ]]; then
        require_root
        require_systemd
        systemctl stop "$APP_NAME"
        echo "已停止 $APP_NAME"
    else
        process_stop
    fi
}

cmd_restart() {
    if [[ "$MODE" == "systemd" ]]; then
        require_root
        require_systemd
        systemctl restart "$APP_NAME"
        systemctl --no-pager --full status "$APP_NAME" || true
    else
        process_stop
        process_start
    fi
}

cmd_status() {
    if [[ "$MODE" == "systemd" ]]; then
        require_systemd
        systemctl --no-pager --full status "$APP_NAME" || true
    else
        process_status
    fi
}

cmd_logs() {
    if [[ "$MODE" == "systemd" ]]; then
        require_systemd
        local target="${1:-200}"
        if [[ "$target" == "-f" ]]; then
            journalctl -u "$APP_NAME" -f
        else
            journalctl -u "$APP_NAME" -n "$target" --no-pager
        fi
    else
        process_logs "$@"
    fi
}

cmd_uninstall() {
    if [[ "$MODE" == "systemd" ]]; then
        require_root
        require_systemd
        systemctl disable --now "$APP_NAME" || true
        rm -f "$SERVICE_PATH"
        systemctl daemon-reload
        echo "已移除 systemd 单元；data/log/backup 与代码目录保留，如需彻底清理请手动删除"
    else
        process_stop
        echo "已停止进程；data/log/backup 与代码目录保留，如需彻底清理请手动删除"
    fi
}

command="${1:-install}"
if [[ $# -gt 0 ]]; then
    shift
fi

case "$command" in
    install) cmd_install ;;
    upgrade) cmd_upgrade ;;
    start) cmd_start ;;
    stop) cmd_stop ;;
    restart) cmd_restart ;;
    status) cmd_status ;;
    logs) cmd_logs "$@" ;;
    uninstall) cmd_uninstall ;;
    -h|--help|help) usage ;;
    *)
        echo "未知命令: $command" >&2
        usage
        exit 1
        ;;
esac
