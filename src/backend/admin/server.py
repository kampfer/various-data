"""管理服务的进程内 uvicorn 封装：线程启动、端口预检与优雅停止。"""

from __future__ import annotations

import logging
import socket
import threading
import time

import uvicorn
from fastapi import FastAPI

from scheduler.config import AdminSettings

STARTUP_TIMEOUT_SECONDS = 10.0
SHUTDOWN_TIMEOUT_SECONDS = 10.0


class AdminServerError(RuntimeError):
    """管理服务无法启动；``kind`` 区分端口占用与其它启动失败。"""

    def __init__(self, message: str, kind: str = "startup"):
        super().__init__(message)
        self.kind = kind


def _ensure_port_available(host: str, port: int) -> None:
    """预检端口，避免 uvicorn 在子线程里静默退出只剩调度器在跑。"""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError as exc:
            raise AdminServerError(
                f"管理服务端口 {host}:{port} 不可用: {exc}", kind="port"
            ) from exc


class AdminServer:
    def __init__(
        self,
        app: FastAPI,
        settings: AdminSettings,
        logger: logging.Logger,
    ):
        self.app = app
        self.settings = settings
        self.logger = logger
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.settings.enabled:
            return

        _ensure_port_available(self.settings.host, self.settings.port)

        config = uvicorn.Config(
            self.app,
            host=self.settings.host,
            port=self.settings.port,
            log_level="warning",
            access_log=False,
            lifespan="off",
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run, name="scheduler-admin", daemon=True
        )
        self._thread.start()

        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self._server.started:
                return
            if not self._thread.is_alive():
                break
            time.sleep(0.05)

        self._thread = None
        self._server = None
        raise AdminServerError(
            f"管理服务启动失败（{self.settings.host}:{self.settings.port}），详见上方日志",
            kind="startup",
        )

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None
        if server is None:
            return
        server.should_exit = True
        if thread is not None:
            thread.join(timeout=SHUTDOWN_TIMEOUT_SECONDS)
            if thread.is_alive():
                self.logger.warning("管理服务线程未在 %.0f 秒内退出", SHUTDOWN_TIMEOUT_SECONDS)
